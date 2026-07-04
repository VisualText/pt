# NLP++ python pass: OOVMerge
# Invoked as:  python "<appdir>/spec/OOVMerge.py" "<appdir>" "<inputfile>" <pre|post>
#
# O QUE FAZ
#   Funde as palavras preenchidas pelo OOV.py (kb/user/missing.kbb, e como
#   alternativa missing.dict) DENTRO do dicionário principal:
#         kb/user/pt-full.dict
#         kb/user/pt-full.kbb
#   Cada palavra nova é inserida em ORDEM ALFABÉTICA (mesma chave de ordenação
#   do dicionário: (palavra.minúscula, palavra)) e recebe, por cima, um
#   comentário de proveniência dizendo QUANDO e POR QUEM foi adicionada, p. ex.:
#         # adicionado em 2026-07-03 por OOV.py (modelo claude-opus-4-8)
#         ao pos=prep
#
#   É idempotente: numa nova execução as palavras já presentes são ignoradas e
#   os comentários de proveniência já existentes são preservados (não duplica).
#   No fim, arquiva missing.dict/missing.kbb como *.merged para não voltarem a
#   ser fundidos nem carregados em duplicado.
#
#   Qualquer falha é não-fatal: o pipeline do analisador continua.
import sys, io, os, re

try:
    import datetime
    TODAY = datetime.date.today().isoformat()
except Exception:
    TODAY = "data desconhecida"

appdir    = sys.argv[1] if len(sys.argv) > 1 else "."
inputfile = sys.argv[2] if len(sys.argv) > 2 else ""
phase     = sys.argv[3] if len(sys.argv) > 3 else "post"

USER      = os.path.join(appdir, "kb", "user")
FULL_DICT = os.path.join(USER, "pt-full.dict")
FULL_KBB  = os.path.join(USER, "pt-full.kbb")
MISS_DICT = os.path.join(USER, "missing.dict")
MISS_KBB  = os.path.join(USER, "missing.kbb")

MODEL      = os.environ.get("OOV_MODEL", "claude-opus-4-8")
ATTR_ORDER = ["pos", "raiz", "gen", "num", "pes", "tem"]
# ordem de bytes UTF-8 (= ponto de código Unicode), exigida pela carga
# preguiçosa do dicionário (busca binária) — NÃO usar (minúscula, palavra).
SORT       = lambda w: w.encode("utf-8")
STAMP      = "# adicionado em %s por OOV.py (modelo %s)" % (TODAY, MODEL)
EOL        = "\r\n"      # mantém o final de linha CRLF do dicionário


# ---------------------------------------------------------------------------
# leitura
# ---------------------------------------------------------------------------
def parse_kbb(path):
    """Devolve (palavras {w:[sentidos]}, notas {w:[linhas de comentário]}, header).
    As linhas de comentário que precedem uma entrada são a sua proveniência."""
    words, notes, header = {}, {}, None
    if not os.path.isfile(path):
        return words, notes, header
    pending, cur, seen_dict = [], None, False
    for line in io.open(path, encoding="utf-8"):
        raw = line.rstrip("\n").rstrip("\r")
        st = raw.strip()
        if st.startswith("#"):
            if header is None and not seen_dict:
                header = raw            # comentário-cabeçalho do ficheiro
            else:
                pending.append(raw)     # proveniência da próxima palavra
            continue
        if st == "dictionary":
            seen_dict = True
            continue
        mw = re.match(r"^  (.+):$", raw)
        if mw:
            cur = mw.group(1).strip()
            words.setdefault(cur, [])
            if pending:
                notes[cur] = pending
                pending = []
            continue
        ms = re.match(r"^    m\d+:\s*(.*)$", raw)
        if ms and cur is not None:
            sense = {}
            for p in ms.group(1).split(","):
                p = p.strip()
                if "=" in p:
                    k, v = p.split("=", 1)
                    sense[k.strip()] = v.strip()
            if sense:
                words[cur].append(sense)
    return words, notes, header


def parse_dict(path):
    """Alternativa quando não há missing.kbb: lê 'palavra pos=X' -> {w:[{pos}]}."""
    words = {}
    if not os.path.isfile(path):
        return words
    for line in io.open(path, encoding="utf-8"):
        raw = line.strip()
        if not raw or raw.startswith("#"):
            continue
        m = re.match(r"^(\S+)\s+pos=(\S+)", raw)
        if m:
            w, pos = m.group(1), m.group(2)
            words.setdefault(w, [])
            if {"pos": pos} not in words[w]:
                words[w].append({"pos": pos})
    return words


# ---------------------------------------------------------------------------
# escrita
# ---------------------------------------------------------------------------
def dedup(metas):
    """Remove sentidos redundantes (um sentido contido noutro mais específico)."""
    out = []
    for m in metas:
        it = set(m.items())
        if any(n is not m and it < set(n.items()) for n in metas):
            continue
        if m not in out:
            out.append(m)
    return out


def fmt(m):
    return ", ".join("%s=%s" % (k, m[k]) for k in ATTR_ORDER if m.get(k))


def write(full, notes, header):
    ndict = 0
    with io.open(FULL_DICT, "w", encoding="utf-8", newline="") as fd, \
         io.open(FULL_KBB,  "w", encoding="utf-8", newline="") as fk:
        fd.write(header + EOL)
        fk.write(header + EOL)
        fk.write("dictionary" + EOL)
        for w in sorted(full, key=SORT):
            for c in notes.get(w, []):          # comentário(s) de proveniência
                fd.write(c + EOL)
                fk.write(c + EOL)
            metas = dedup(full[w])
            seen = []
            for m in metas:                     # .dict: uma linha por (palavra,pos)
                if m.get("pos") and m["pos"] not in seen:
                    seen.append(m["pos"])
                    fd.write("%s pos=%s%s" % (w, m["pos"], EOL))
                    ndict += 1
            fk.write("  %s:%s" % (w, EOL))
            for i, m in enumerate(metas, 1):
                fk.write("    m%02d: %s%s" % (i, fmt(m), EOL))
    return ndict


# ---------------------------------------------------------------------------
# principal
# ---------------------------------------------------------------------------
def main():
    if not os.path.isfile(FULL_KBB):
        print("[OOVMerge] pt-full.kbb não encontrado em %s; nada a fazer" % USER)
        return 0

    # fonte das palavras ausentes: missing.kbb (com atributos) ou missing.dict
    miss, _, _ = parse_kbb(MISS_KBB)
    if not miss:
        miss = parse_dict(MISS_DICT)
    if not miss:
        print("[OOVMerge] sem missing.kbb/missing.dict; nada a fundir")
        return 0

    full, notes, header = parse_kbb(FULL_KBB)
    if header is None:
        header = "# Dicionário Português"

    added = []
    for w in miss:
        if w in full:                 # já presente -> não duplica
            continue
        full[w] = miss[w]
        notes[w] = [STAMP]
        added.append(w)

    ndict = write(full, notes, header)

    # arquiva os ficheiros de ausentes já fundidos (não-fatal)
    for src in (MISS_DICT, MISS_KBB):
        if os.path.isfile(src):
            try:
                os.replace(src, src + ".merged")
            except OSError:
                pass

    print("[OOVMerge] %d palavra(s) nova(s) fundida(s) em pt-full.* "
          "(%d linhas .dict)" % (len(added), ndict))
    if added:
        added.sort(key=SORT)
        print("[OOVMerge] adicionadas: %s" % " ".join(added))
    return 0


if __name__ == "__main__":
    try:
        sys.exit(main())
    except Exception as e:            # nunca quebra o pipeline
        print("[OOVMerge] falhou (%s); pt-full.* inalterado" % e)
        sys.exit(0)
