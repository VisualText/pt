# -*- coding: utf-8 -*-
"""
regen_pt_dict.py  —  Reconstrói o dicionário grande do português (~1M entradas)
a partir das MESMAS fontes do pipeline original `dict-pt-br`:

  * o despejo do Wiktionary português, já dividido em uma página .xml por
    palavra em  <dict-pt-br>/Wiktionary/words/*.zip
  * as conjugações da Reverso em  <dict-pt-br>/reverso-verbs/diction/input/
    portverbs2000.txt

Porquê este script existir
--------------------------
O pipeline original usava analisadores NLP++ (Wiktionary/WiktionPage), mas o
motor nlp.exe desta máquina termina com violação de acesso a meio da geração.
Este script faz a mesma extração em Python (fluxo direto dos .zip, sem
descompactar), de forma fiável e inspecionável.

Como o Wiktionary tem UMA PÁGINA por forma flexionada (==Forma verbal==,
==Forma de substantivo==, ...), a reconstrução é essencialmente:
    título da página  +  secção de classe gramatical (pt)  ->  "palavra pos=X"

Saída (dicionário canónico do analisador — reexecutar regenera-o):
    kb/user/pt-full.dict
    kb/user/pt-full.kbb

Uso:  python tools/regen_pt_dict.py [caminho-para-dict-pt-br]
"""
import os, re, sys, glob, bz2, zipfile, collections, io

ROOT     = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
DICTPTBR = sys.argv[1] if len(sys.argv) > 1 else r"c:\git\dict-pt-br"
WORDS    = os.path.join(DICTPTBR, "Wiktionary", "words")
DUMP     = os.path.join(DICTPTBR, "Wiktionary", "ptwiktionary-latest-pages-meta-current.xml.bz2")
REVDIR   = os.path.join(DICTPTBR, "reverso-verbs", "diction", "input")

# --- conjugador regular (regras puras; mesma lógica de gen_pt_dict.py) --------
ENDINGS = {
 'ar': dict(t=[['o','as','a','amos','ais','am'],['ei','aste','ou','amos','astes','aram'],
   ['ava','avas','ava','ávamos','áveis','avam'],['ara','aras','ara','áramos','áreis','aram'],
   ['arei','arás','ará','aremos','areis','arão'],['aria','arias','aria','aríamos','aríeis','ariam'],
   ['e','es','e','emos','eis','em'],['asse','asses','asse','ássemos','ásseis','assem'],
   ['ar','ares','ar','armos','ardes','arem']], g='ando', p='ado', i='ai'),
 'er': dict(t=[['o','es','e','emos','eis','em'],['i','este','eu','emos','estes','eram'],
   ['ia','ias','ia','íamos','íeis','iam'],['era','eras','era','êramos','êreis','eram'],
   ['erei','erás','erá','eremos','ereis','erão'],['eria','erias','eria','eríamos','eríeis','eriam'],
   ['a','as','a','amos','ais','am'],['esse','esses','esse','êssemos','êsseis','essem'],
   ['er','eres','er','ermos','erdes','erem']], g='endo', p='ido', i='ei'),
 'ir': dict(t=[['o','es','e','imos','is','em'],['i','iste','iu','imos','istes','iram'],
   ['ia','ias','ia','íamos','íeis','iam'],['ira','iras','ira','íramos','íreis','iram'],
   ['irei','irás','irá','iremos','ireis','irão'],['iria','irias','iria','iríamos','iríeis','iriam'],
   ['a','as','a','amos','ais','am'],['isse','isses','isse','íssemos','ísseis','issem'],
   ['ir','ires','ir','irmos','irdes','irem']], g='indo', p='ido', i='i'),
}
def _attach(stem, end, conj):
    if not end: return stem
    front = end[0] in 'eéêi'; back = end[0] in 'aãáâoóôu'
    if conj == 'ar' and front:
        if stem.endswith('c'):  return stem[:-1]+'qu'+end
        if stem.endswith('g'):  return stem[:-1]+'gu'+end
        if stem.endswith('ç'):  return stem[:-1]+'c'+end
    if conj in ('er','ir') and back:
        if stem.endswith('gu'): return stem[:-2]+'g'+end
        if stem.endswith('c'):  return stem[:-1]+'ç'+end
        if stem.endswith('g'):  return stem[:-1]+'j'+end
    return stem+end
def conjugar(inf):
    conj = inf[-2:]
    if conj not in ENDINGS or len(inf) < 3: return set()
    stem = inf[:-2]; e = ENDINGS[conj]; out = {inf}
    for tempo in e['t']:
        for end in tempo:
            out.add(_attach(stem, end, conj))
    out.add(_attach(stem, e['g'], conj))
    out.add(_attach(stem, e['i'], conj))
    # particípio com as 4 formas de género/número (ado/ada/ados/adas)
    part = _attach(stem, e['p'], conj)
    out.add(part)
    if part.endswith('o'):
        fem = part[:-1] + 'a'
        out.update({fem, part + 's', fem + 's'})
    return out

PLURAL_EXC = {'pão':'pães','cão':'cães','mão':'mãos','irmão':'irmãos','alemão':'alemães',
 'capitão':'capitães','cidadão':'cidadãos','cristão':'cristãos','mal':'males',
 'país':'países','mês':'meses','fácil':'fáceis','difícil':'difíceis','útil':'úteis'}
def pluralizar(w):
    if w in PLURAL_EXC: return PLURAL_EXC[w]
    if w[-1] in 'aeiouáéíóúâêôãõ':
        return w[:-2]+'ões' if w.endswith('ão') else w+'s'
    if w.endswith('m'):  return w[:-1]+'ns'
    if w.endswith('r') or w.endswith('z'):  return w+'es'
    if w.endswith('s') or w.endswith('x'):  return w
    if w.endswith('l'):
        if w.endswith('el'): return w[:-2]+'éis'
        if w.endswith('ol'): return w[:-2]+'óis'
        if w.endswith('il'): return w[:-2]+'is'
        return w[:-1]+'is'
    return w+'s'

# ---- mapeamento cabeçalho de classe (pt.wiktionary) -> código pos -----------
POS_MAP = {
 'substantivo':'s', 'forma de substantivo':'s', 'substantivo próprio':'s',
 'substantivo comum':'s', 'locução substantiva':'s',
 'verbo':'v', 'forma verbal':'v', 'locução verbal':'v',
 'adjetivo':'adj', 'forma de adjetivo':'adj', 'locução adjetiva':'adj',
 'advérbio':'adv', 'locução adverbial':'adv',
 'pronome':'pron', 'forma de pronome':'pron',
 'artigo':'art',
 'preposição':'prep', 'locução prepositiva':'prep',
 'conjunção':'conj', 'locução conjuntiva':'conj',
 'interjeição':'int', 'locução interjectiva':'int',
 'numeral':'num',
}
# cabeçalhos a ignorar (não são classes de palavra)
SKIP = {'ver também','ligações externas','anagramas','anagrama','tradução',
        'traduções','pronúncia','etimologia','expressões','sinônimos',
        'antônimos','aumentativos','diminutivos','notas','referências',
        'sigla','abreviatura','acrônimo','símbolo','prefixo','sufixo'}

LANG_HDR = re.compile(r'^=\s*\{\{-([a-z-]+)-\}\}\s*=\s*$', re.M)   # ={{-pt-}}=
POS_HDR  = re.compile(r'^==\s*([A-Za-zÀ-ÿ ]+?)\s*==\s*$', re.M)    # ==Substantivo==
TITLE_RE = re.compile(r'<title>(.*?)</title>', re.S)
TEXT_RE  = re.compile(r'<text[^>]*>(.*?)</text>', re.S)
GRAM_RE  = re.compile(r'\{\{gramática\|([a-z0-9]+)')
FLEX_RE  = re.compile(r'\{\{flex\.pt\|([^}]*)\}\}')

ENTRIES = collections.OrderedDict()   # palavra -> lista de dicts (pos, gen, num, raiz)

RAIZ_OK = re.compile(r'^[a-zà-ÿ]+(-[a-zà-ÿ]+)*$')   # lema = uma só palavra (com hífen ok)
def add(word, pos, **attrs):
    r = attrs.get('raiz')
    if r is not None and not RAIZ_OK.match(r):        # descarta raiz multipalavra/inválida
        attrs = dict(attrs, raiz=None)
    m = {'pos': pos}
    m.update({k:v for k,v in attrs.items() if v})
    ENTRIES.setdefault(word, [])
    if m not in ENTRIES[word]:
        ENTRIES[word].append(m)

def pt_section(wikitext):
    """Devolve só o bloco da língua portuguesa da página."""
    langs = list(LANG_HDR.finditer(wikitext))
    for i, mo in enumerate(langs):
        if mo.group(1) == 'pt':
            start = mo.end()
            end = langs[i+1].start() if i+1 < len(langs) else len(wikitext)
            return wikitext[start:end]
    return None

def gender_number(block):
    gen = num = None
    g = GRAM_RE.search(block)
    if g:
        code = g.group(1)
        if code.startswith('m'): gen = 'm'
        elif code.startswith('f'): gen = 'f'
        if code.endswith('p'): num = 'p'
    return gen, num

def parse_page(xml):
    mt = TITLE_RE.search(xml); mx = TEXT_RE.search(xml)
    if not mt or not mx:
        return
    title = mt.group(1).strip()
    if not title or ':' in title or ' ' in title:   # ignora namespaces e locuções (multipalavra)
        return
    if re.search(r'[{}\[\]<>|=]', title):        # ignora títulos com marcação
        return
    body = pt_section(mx.group(1))
    if not body:
        return
    # divide o bloco pt em subsecções por cabeçalho de classe
    hdrs = list(POS_HDR.finditer(body))
    for i, h in enumerate(hdrs):
        name = h.group(1).strip().lower()
        if name in SKIP:
            continue
        pos = POS_MAP.get(name)
        if not pos:
            continue
        seg = body[h.end(): hdrs[i+1].start() if i+1 < len(hdrs) else len(body)]
        gen, num = gender_number(seg)
        add(title, pos, gen=gen, num=num)
        # formas de flexão explícitas do Wiktionary ({{flex.pt|fs=..|fp=..}})
        fm = FLEX_RE.search(seg)
        if fm and pos in ('s', 'adj'):
            params = {}
            for kv in fm.group(1).split('|'):
                if '=' not in kv:
                    continue
                k, v = kv.split('=', 1)
                k = k.strip(); v = v.strip().split()[0] if v.strip() else ''
                if k in ('ms','mp','fs','fp') and re.match(r'^[a-zà-ÿ-]+$', v):
                    params[k] = v
            base = params.get('ms') or params.get('fs')   # lema = masc sing, senão fem sing
            for k, v in params.items():
                add(v, pos, raiz=(base if v != base else None),
                    gen=('m' if k[0]=='m' else 'f'), num=('s' if k[1]=='s' else 'p'))
        # expande a conjugação de páginas de verbo (título = infinitivo)
        if pos == 'v' and name == 'verbo' and re.match(r'^[a-zà-ÿ]+(ar|er|ir)$', title):
            for f in conjugar(title):
                add(f, 'v', raiz=title)
        # plural por regra para lemas de substantivo/adjetivo (singular)
        if name in ('substantivo','adjetivo') and re.match(r'^[a-zà-ÿ-]+$', title) \
                and num != 'p':
            pl = pluralizar(title)
            if pl != title:
                add(pl, pos, raiz=title, gen=gen, num='p')
        # feminino (e seu plural) por regra para adjetivos masculinos em -o
        if name == 'adjetivo' and title.endswith('o') and re.match(r'^[a-zà-ÿ-]+$', title):
            fem = title[:-1] + 'a'
            add(fem, 'adj', raiz=title, gen='f', num='s')
            add(pluralizar(fem), 'adj', raiz=title, gen='f', num='p')

# ---- 1a) Wiktionary: fluxo direto do despejo completo (.bz2) ----------------
# Processa TODAS as ~395 mil páginas do despejo, não só as ~212 mil que o
# split.py guardou (ele descartava títulos com hífen, espaço, etc.).
def run_dump():
    npages = 0; buf = []; inpage = False
    with bz2.open(DUMP, 'rt', encoding='utf-8', errors='replace') as fh:
        for line in fh:
            s = line.lstrip()
            if not inpage:
                if s.startswith('<page>'):
                    inpage = True; buf = [line]
                continue
            buf.append(line)
            if s.startswith('</page>'):
                parse_page(''.join(buf))
                inpage = False; npages += 1
                if npages % 25000 == 0:
                    print("  %d páginas processadas" % npages)
    return npages

# ---- 1b) Wiktionary: fluxo dos .zip pré-divididos (alternativa) --------------
def run_wiktionary():
    npages = 0
    zips = sorted(f for f in os.listdir(WORDS) if f.endswith('.zip'))
    for zn in zips:
        with zipfile.ZipFile(os.path.join(WORDS, zn)) as z:
            for info in z.infolist():
                if not info.filename.endswith('.xml'):
                    continue
                try:
                    raw = z.read(info).decode('utf-8', 'replace')
                except Exception:
                    continue
                parse_page(raw)
                npages += 1
        print("  %s  (%d páginas acumuladas)" % (zn, npages))
    return npages

# ---- 2) Reverso: conjugações dos 2000 verbos mais comuns --------------------
REV_LINE = re.compile(r'^(\S+)\s+"[^"]*"\s+\S.*?\s(\S+)\s*$')
def run_reverso():
    files = sorted(glob.glob(os.path.join(REVDIR, "portverbs*.txt")))
    if not files:
        print("  (aviso: Reverso não encontrado em %s)" % REVDIR); return 0
    n = 0
    for path in files:
        for line in io.open(path, encoding='utf-8', errors='replace'):
            m = REV_LINE.match(line.strip())
            if not m:
                continue
            lemma, form = m.group(1), m.group(2).strip().lower()
            if not re.match(r'^[a-zà-ÿ-]+$', form):
                continue
            add(form, 'v', raiz=lemma)
            n += 1
        print("  %s" % os.path.basename(path))
    return n

# ---- emissão ----------------------------------------------------------------
def fmt(m):
    order = ['pos','raiz','gen','num']
    return ", ".join("%s=%s" % (k, m[k]) for k in order if m.get(k))

def dedup_metas(metas):
    """Remove significados redundantes: descarta um meta se outro, mais
    específico, o contém (mesmos atributos e mais alguns).  Ex.: {pos=s,gen=f}
    é descartado quando existe {pos=s,gen=f,num=s}."""
    out = []
    for m in metas:
        items = set(m.items())
        if any(n is not m and items < set(n.items()) for n in metas):
            continue
        if m not in out:
            out.append(m)
    return out

def emit():
    outdir = os.path.join(ROOT, 'kb', 'user')
    os.makedirs(outdir, exist_ok=True)
    dpath = os.path.join(outdir, 'pt-full.dict')
    kpath = os.path.join(outdir, 'pt-full.kbb')
    ndict = 0
    with io.open(dpath, 'w', encoding='utf-8') as fd, \
         io.open(kpath, 'w', encoding='utf-8') as fk:
        fd.write("# Dicionário Português (regenerado de Wiktionary + Reverso)\n")
        fk.write("# Dicionário Português (regenerado de Wiktionary + Reverso)\n")
        fk.write("dictionary\n")
        # ordem de bytes UTF-8 (= ponto de código), exigida pela carga preguiçosa
        for word in sorted(ENTRIES, key=lambda w: w.encode('utf-8')):
            metas = dedup_metas(ENTRIES[word])    # remove significados redundantes
            seen_pos = []
            for m in metas:                       # .dict: uma linha por (palavra,pos)
                if m['pos'] not in seen_pos:
                    seen_pos.append(m['pos'])
                    fd.write("%s pos=%s\n" % (word, m['pos'])); ndict += 1
            fk.write("  %s:\n" % word)
            for i, m in enumerate(metas, 1):      # .kbb: um significado por linha, sem redundância
                fk.write("    m%02d: %s\n" % (i, fmt(m)))
    return dpath, kpath, ndict

if __name__ == '__main__':
    if os.path.exists(DUMP):
        print("A processar o despejo completo do Wiktionary:", DUMP)
        pages = run_dump()
    else:
        print("A processar o Wiktionary a partir de", WORDS)
        pages = run_wiktionary()
    print("A processar as conjugações da Reverso...")
    rev = run_reverso()
    dpath, kpath, ndict = emit()
    print("\npáginas do Wiktionary:", pages, " | formas da Reverso:", rev)
    print("palavras distintas:", len(ENTRIES), " | linhas .dict:", ndict)
    print("escrito:", dpath)
    print("escrito:", kpath)
