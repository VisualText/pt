# OOV.py — Out-Of-Vocabulary gap-filler (NLP++ python pass)
#
# Invoked as:  python "<appdir>/spec/OOV.py" "<appdir>" "<inputfile>" <pre|post>
#
# What it does:
#   1. Looks for "<inputfile>_log/missing-words.log" (one OOV word per line,
#      written by the analyzer when a token isn't found in the dictionary).
#   2. For every word not already known, asks an LLM (Claude) to produce the
#      dictionary part-of-speech tags and knowledge-base attributes.
#   3. Writes/refreshes two files in <appdir>/kb/user/:
#         missing.dict   word pos=X            (one line per distinct pos)
#         missing.kbb    dictionary / word: / mNN: pos=..., raiz=..., ...
#      so the analyzer can lazy-load them on the next run.
#
# The two files are rebuilt from the union of everything seen so far, so the
# LLM is only queried for genuinely new words and the output stays sorted
# (Unicode codepoint order = UTF-8 byte order, required for lazy-load).
#
# Backends (auto-selected):
#   * anthropic  — Claude API. Requires `pip install anthropic pydantic` and
#                  ANTHROPIC_API_KEY in the env.  Used when the key is present.
#   * ollama     — a LOCAL open-source model (no key, no cost).  Used when there
#                  is no ANTHROPIC_API_KEY.  Requires Ollama running and a model
#                  pulled, e.g.:  `ollama pull qwen2.5:7b`  (or set OLLAMA_MODEL).
#                  Uses only the standard library (urllib) to reach the server.
# Force a backend with OOV_BACKEND=anthropic|ollama.
# Any failure (no key, no SDK, no server, API error) is non-fatal: the analyzer
# pipeline continues and the missing words are simply left unfilled this run.

import io
import os
import re
import sys
from typing import List, Optional

MODEL = os.environ.get("OOV_MODEL", "claude-opus-4-8")
BATCH = 50  # words per LLM request

# Backend: "anthropic" (Claude API) or "ollama" (local, open-source models).
# Default: anthropic when ANTHROPIC_API_KEY is set, else fall back to a local
# Ollama server so the pipeline still works with no API key / no cost.
OOV_BACKEND  = os.environ.get("OOV_BACKEND", "").strip().lower()
OLLAMA_HOST  = os.environ.get("OLLAMA_HOST", "http://localhost:11434").rstrip("/")
OLLAMA_MODEL = os.environ.get("OLLAMA_MODEL", "qwen2.5:7b")

# Shared part-of-speech tag set used by every language template in this repo.
POS_LEGEND = (
    "s=substantive/noun, adj=adjective, v=verb, adv=adverb, prep=preposition, "
    "pron=pronoun, art=article, conj=conjunction, num=numeral, interj=interjection"
)

# Map the analyzer-directory language code to a human-readable language name so
# the same script works for every parse-XX-YY analyzer (pt, es, it, ro, fr, zh).
LANG_NAMES = {
    "pt": "Brazilian Portuguese",
    "es": "Spanish",
    "it": "Italian",
    "ro": "Romanian",
    "fr": "French",
    "zh": "Chinese",
    "en": "English",
}


def language_from_appdir(appdir):
    base = os.path.basename(os.path.normpath(appdir))
    m = re.match(r"(?:parse-)?([a-z]{2})(?:-([a-z]{2}))?", base.lower())
    if m and m.group(1) in LANG_NAMES:
        return LANG_NAMES[m.group(1)]
    return "the target language"


# ---------------------------------------------------------------------------
# missing.kbb / missing.dict parsing and serialization
# ---------------------------------------------------------------------------

# A "sense" is a dict of attributes; we serialize them in this order so the
# output reads pos, raiz, gen, num, pes, tem like the hand-built kbb.
ATTR_ORDER = ["pos", "raiz", "gen", "pes", "num", "tem"]


def parse_existing_kbb(path):
    """Return {word: [sense_dict, ...]} from an existing missing.kbb (if any)."""
    words = {}
    if not os.path.isfile(path):
        return words
    current = None
    with io.open(path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.rstrip("\n")
            if not line.strip() or line.lstrip().startswith("#"):
                continue
            if line.strip() == "dictionary":
                continue
            m_word = re.match(r"^  (.+):$", line)
            if m_word:
                current = m_word.group(1)
                words.setdefault(current, [])
                continue
            m_sense = re.match(r"^    m\d+:\s*(.*)$", line)
            if m_sense and current is not None:
                sense = {}
                for pair in m_sense.group(1).split(","):
                    pair = pair.strip()
                    if "=" in pair:
                        k, v = pair.split("=", 1)
                        sense[k.strip()] = v.strip()
                if sense:
                    words[current].append(sense)
    return words


def serialize_sense(sense):
    parts = []
    for key in ATTR_ORDER:
        if sense.get(key):
            parts.append("%s=%s" % (key, sense[key]))
    # include any extra keys the LLM may have added, in stable order
    for key in sorted(k for k in sense if k not in ATTR_ORDER):
        if sense[key]:
            parts.append("%s=%s" % (key, sense[key]))
    return ", ".join(parts)


def write_kbb(path, words):
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Palavras ausentes preenchidas automaticamente (OOV.py)\n")
        f.write("dictionary\n")
        for word in sorted(words):
            senses = words[word]
            if not senses:
                continue
            f.write("  %s:\n" % word)
            for i, sense in enumerate(senses, 1):
                f.write("    m%02d: %s\n" % (i, serialize_sense(sense)))


def write_dict(path, words):
    with io.open(path, "w", encoding="utf-8", newline="\n") as f:
        f.write("# Palavras ausentes preenchidas automaticamente (OOV.py)\n")
        for word in sorted(words):
            seen = set()
            for sense in words[word]:
                pos = sense.get("pos")
                if pos and pos not in seen:
                    seen.add(pos)
                    f.write("%s pos=%s\n" % (word, pos))


# ---------------------------------------------------------------------------
# LLM lookup
# ---------------------------------------------------------------------------

def system_prompt(language):
    return (
        "You are a morphological lexicographer for %s. For each word you are "
        "given, return every common dictionary sense as a part-of-speech tag "
        "plus its grammatical attributes.\n"
        "Part-of-speech tags (use exactly these codes): %s.\n"
        "Attributes: raiz = canonical lemma (OMIT when it equals the word "
        "itself); gen = m or f; num = s (singular) or p (plural). For verbs "
        "also give pes (1/2/3), num, tem (a short tense code such as p, pp, "
        "fut, imp, part, ger) and raiz = the infinitive.\n"
        "Proper nouns are pos=s with gen and num=s. Give the most common "
        "senses, most frequent first. Do not invent rare or nonexistent "
        "readings." % (language, POS_LEGEND)
    )


# Accept only well-formed tag values; chatty local models sometimes stuff a
# whole explanation into an attribute, so anything that doesn't match is dropped
# (the pos itself is kept — that is what the .dict needs).
VALID_POS = {"s", "adj", "v", "adv", "prep", "pron", "art", "conj", "num", "int"}
ATTR_RE = {
    "gen": re.compile(r"^[mfc]$"),
    "num": re.compile(r"^[sp]$"),
    "pes": re.compile(r"^[123]$"),
    "tem": re.compile(r"^[a-zà-ÿ]{1,6}$", re.I),
    "raiz": re.compile(r"^[a-zà-ÿ]+(-[a-zà-ÿ]+)*$", re.I),
}


def normalize_entry(word, raw_senses):
    """Turn a list of sense-like objects/dicts into clean, validated [sense_dict]."""
    def get(s, key):
        return s.get(key) if isinstance(s, dict) else getattr(s, key, None)
    senses = []
    for s in raw_senses:
        pos = get(s, "pos")
        pos = str(pos).strip().lower() if pos else ""
        if pos == "interj":
            pos = "int"
        if pos not in VALID_POS:            # unusable sense -> skip
            continue
        sense = {"pos": pos}
        for key in ("raiz", "gen", "num", "pes", "tem"):
            val = get(s, key)
            if not val:
                continue
            val = str(val).strip()
            if key == "raiz":
                val = val.lower()
                if val == word:             # don't repeat the word
                    continue
            if ATTR_RE[key].match(val):     # keep only clean, short values
                sense[key] = val
        senses.append(sense)
    return senses


def llm_fill_anthropic(new_words, language):
    """Query the Claude API; return {word: [sense,...]}."""
    import anthropic
    from pydantic import BaseModel

    class Sense(BaseModel):
        pos: str
        raiz: Optional[str] = None
        gen: Optional[str] = None
        num: Optional[str] = None
        pes: Optional[str] = None
        tem: Optional[str] = None

    class Entry(BaseModel):
        word: str
        senses: List[Sense]

    class OOVResult(BaseModel):
        entries: List[Entry]

    system = system_prompt(language)
    client = anthropic.Anthropic()
    out = {}
    for start in range(0, len(new_words), BATCH):
        chunk = new_words[start:start + BATCH]
        user = "Provide dictionary entries for these %s words:\n%s" % (
            language, "\n".join(chunk))
        resp = client.messages.parse(
            model=MODEL, max_tokens=16000, system=system,
            messages=[{"role": "user", "content": user}],
            output_format=OOVResult,
        )
        result = resp.parsed_output
        if not result:
            continue
        for entry in result.entries:
            word = entry.word.strip()
            senses = normalize_entry(word, entry.senses)
            if word and senses:
                out[word] = senses
    return out


# JSON schema for the local (Ollama) structured output.
OLLAMA_SCHEMA = {
    "type": "object",
    "properties": {
        "entries": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "word": {"type": "string"},
                    "senses": {
                        "type": "array",
                        "items": {
                            "type": "object",
                            "properties": {
                                "pos": {"type": "string"},
                                "raiz": {"type": ["string", "null"]},
                                "gen": {"type": ["string", "null"]},
                                "num": {"type": ["string", "null"]},
                                "pes": {"type": ["string", "null"]},
                                "tem": {"type": ["string", "null"]},
                            },
                            "required": ["pos"],
                        },
                    },
                },
                "required": ["word", "senses"],
            },
        }
    },
    "required": ["entries"],
}


def llm_fill_ollama(new_words, language):
    """Query a local Ollama server (open-source model); return {word:[sense,...]}."""
    import json
    import urllib.request

    system = system_prompt(language)
    out = {}
    for start in range(0, len(new_words), BATCH):
        chunk = new_words[start:start + BATCH]
        user = "Provide dictionary entries for these %s words:\n%s" % (
            language, "\n".join(chunk))
        body = {
            "model": OLLAMA_MODEL,
            "stream": False,
            "format": OLLAMA_SCHEMA,          # structured output
            "options": {"temperature": 0},
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
        }
        req = urllib.request.Request(
            OLLAMA_HOST + "/api/chat",
            data=json.dumps(body).encode("utf-8"),
            headers={"Content-Type": "application/json"},
        )
        with urllib.request.urlopen(req, timeout=600) as r:
            data = json.loads(r.read().decode("utf-8"))
        content = (data.get("message") or {}).get("content", "")
        if not content:
            continue
        try:
            parsed = json.loads(content)
        except ValueError:
            continue
        for entry in parsed.get("entries", []):
            word = (entry.get("word") or "").strip()
            senses = normalize_entry(word, entry.get("senses", []))
            if word and senses:
                out[word] = senses
    return out


def llm_fill(new_words, language):
    """Dispatch to the configured backend; return {word: [sense,...]}."""
    backend = OOV_BACKEND
    if not backend:
        backend = "anthropic" if os.environ.get("ANTHROPIC_API_KEY") else "ollama"
    if backend == "ollama":
        print("[OOV] backend: ollama (%s @ %s)" % (OLLAMA_MODEL, OLLAMA_HOST))
        return llm_fill_ollama(new_words, language)
    print("[OOV] backend: anthropic (%s)" % MODEL)
    return llm_fill_anthropic(new_words, language)


# ---------------------------------------------------------------------------
# main
# ---------------------------------------------------------------------------

def main():
    appdir = sys.argv[1] if len(sys.argv) > 1 else "."
    inputfile = sys.argv[2] if len(sys.argv) > 2 else ""
    # phase (pre|post) is sys.argv[3] — not needed here.

    if not inputfile:
        print("[OOV] no input file given; nothing to do")
        return 0

    log_dir = inputfile + "_log"
    missing_log = os.path.join(log_dir, "missing-words.log")
    if not os.path.isfile(missing_log):
        print("[OOV] no missing-words.log found at %s" % missing_log)
        return 0

    with io.open(missing_log, "r", encoding="utf-8") as f:
        candidates = []
        seen = set()
        for line in f:
            w = line.strip()
            if w and w not in seen:
                seen.add(w)
                candidates.append(w)

    if not candidates:
        print("[OOV] missing-words.log is empty; nothing to do")
        return 0

    user_dir = os.path.join(appdir, "kb", "user")
    dict_path = os.path.join(user_dir, "missing.dict")
    kbb_path = os.path.join(user_dir, "missing.kbb")

    known = parse_existing_kbb(kbb_path)
    new_words = [w for w in candidates if w not in known]

    if not new_words:
        print("[OOV] all %d missing word(s) already filled" % len(candidates))
        return 0

    print("[OOV] filling %d new word(s)..." % len(new_words))
    try:
        filled = llm_fill(new_words, language_from_appdir(appdir))
    except Exception as e:  # never break the analyzer pipeline
        print("[OOV] LLM lookup failed (%s); leaving words unfilled" % e)
        return 0

    if not filled:
        print("[OOV] LLM returned no usable entries")
        return 0

    known.update(filled)

    if not os.path.isdir(user_dir):
        os.makedirs(user_dir)
    write_dict(dict_path, known)
    write_kbb(kbb_path, known)

    print("[OOV] wrote %d entries to %s and %s"
          % (len(known), dict_path, kbb_path))
    return 0


if __name__ == "__main__":
    sys.exit(main())
