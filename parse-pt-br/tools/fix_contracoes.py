# -*- coding: utf-8 -*-
"""
fix_contracoes.py — garante que as contrações do português têm leitura de
PREPOSIÇÃO no dicionário do analisador.

O `pt-full.dict` / `pt-full.kbb` vêm do Wiktionary, que trata cada contração
como uma palavra qualquer: "no" sai como pronome, "do"/"da" como formas do
verbo "dar".  Sem uma leitura `pos=prep` o passo `significado` não consegue
casar o nó `_preposicao` da árvore com um significado do dicionário.

Este script acrescenta (sem apagar nada) uma leitura `pos=prep, gen=, num=`
a cada contração de `tools/contracoes.py`, mantendo a ordem de bytes UTF-8
que a carga preguiçosa do motor exige.

Uso:  python tools/fix_contracoes.py
"""
import io
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from contracoes import tabela, PROCLITICOS, ENCLITICOS        # noqa: E402

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
KBDIR = os.path.join(ROOT, 'kb', 'user')
DICT = os.path.join(KBDIR, 'pt-full.dict')
KBB = os.path.join(KBDIR, 'pt-full.kbb')


def _key(w):
    return w.encode('utf-8')


def _ler(path):
    """Lê preservando as terminações de linha originais (os ficheiros do
    dicionário estão em CRLF; reescrevê-los em LF criaria um diff gigante)."""
    with io.open(path, encoding='utf-8', newline='') as f:
        linhas = f.readlines()
    fim = '\r\n' if linhas and linhas[0].endswith('\r\n') else '\n'
    return linhas, fim


def _escrever(path, linhas):
    with io.open(path, 'w', encoding='utf-8', newline='') as f:
        f.writelines(linhas)


def linha_dict(entrada, fim):
    """A linha de dicionário da contração.  O tokenizador marca o token com
    TODOS estes atributos, de modo que as regras reconhecem a contração sem
    precisar de listas de palavras no NLP++:

        no pos=prep contracao=1 contrprep=em contrdet=o gen=m num=s
    """
    palavra, prep, det, gen, num = entrada
    extra = u" encl=1" if palavra in ENCLITICOS else u""
    return u"%s pos=prep contracao=1 contrprep=%s contrdet=%s gen=%s num=%s%s%s" \
        % (palavra, prep, det, gen, num, extra, fim)


def corrigir_dict(linhas, entradas, fim):
    """Garante a linha de preposição de cada contração, na posição ordenada."""
    saida, add = [], 0
    pendentes = sorted(entradas, key=lambda r: _key(r[0]))
    i = 0                                   # índice na lista de pendentes

    # agrupa as linhas existentes por palavra, preservando a ordem do ficheiro
    blocos = []                             # [(palavra ou None, [linhas])]
    for ln in linhas:
        m = re.match(r'^(\S+) pos=', ln)
        palavra = m.group(1) if m else None
        if blocos and blocos[-1][0] == palavra and palavra is not None:
            blocos[-1][1].append(ln)
        else:
            blocos.append((palavra, [ln]))

    for palavra, bloco in blocos:
        # insere as contrações ainda inexistentes que vêm antes desta palavra
        while i < len(pendentes) and palavra is not None \
                and _key(pendentes[i][0]) < _key(palavra):
            saida.append(linha_dict(pendentes[i], fim))
            add += 1
            i += 1
        if i < len(pendentes) and pendentes[i][0] == palavra:
            # marca a leitura de pronome PROCLÍTICO ("nos" = a nós), a única
            # que continua a competir com a contração fora da ênclise
            if palavra in PROCLITICOS:
                bloco = [ln.rstrip('\r\n') + u' procl=1' + fim
                         if re.match(r'^\S+ pos=pron\s*$', ln) else ln
                         for ln in bloco]
            nova = linha_dict(pendentes[i], fim)
            # substitui a leitura de preposição existente (que vem do
            # Wiktionary sem os atributos da contração), ou acrescenta-a
            antigas = [j for j, ln in enumerate(bloco)
                       if re.match(r'^\S+ pos=prep\b', ln)]
            if antigas:
                bloco = list(bloco)
                bloco[antigas[0]] = nova
            else:
                bloco = bloco + [nova]
            add += 1
            i += 1
        saida.extend(bloco)

    while i < len(pendentes):               # contrações depois da última palavra
        saida.append(linha_dict(pendentes[i], fim))
        add += 1
        i += 1
    return saida, add


def corrigir_kbb(linhas, entradas, fim):
    """Acrescenta 'mNN: pos=prep, gen=, num=' ao conceito de cada contração."""
    info = dict((r[0], r) for r in entradas)
    pendentes = sorted(entradas, key=lambda r: _key(r[0]))
    saida, add = [], 0
    i = 0

    blocos = []                             # [(palavra ou None, [linhas])]
    for ln in linhas:
        m = re.match(r'^  (\S+):\s*$', ln)
        if m:
            blocos.append((m.group(1), [ln]))
        elif blocos and blocos[-1][0] is not None and ln.startswith('    '):
            blocos[-1][1].append(ln)
        else:
            blocos.append((None, [ln]))

    def novo_bloco(palavra, n):
        _, prep, det, gen, num = info[palavra]
        return [u"  %s:%s" % (palavra, fim),
                u"    m%02d: pos=prep, gen=%s, num=%s%s" % (n, gen, num, fim)]

    for palavra, bloco in blocos:
        while i < len(pendentes) and palavra is not None \
                and _key(pendentes[i][0]) < _key(palavra):
            saida.extend(novo_bloco(pendentes[i][0], 1))
            add += 1
            i += 1
        if i < len(pendentes) and pendentes[i][0] == palavra:
            _, prep, det, gen, num = info[palavra]
            if not any('pos=prep' in ln for ln in bloco[1:]):
                bloco = bloco + [u"    m%02d: pos=prep, gen=%s, num=%s%s"
                                 % (len(bloco), gen, num, fim)]
                add += 1
            else:
                # leitura de preposição já existente, mas sem gênero/número:
                # o determinante fundido traz-lhos.
                for j, ln in enumerate(bloco[1:], 1):
                    if ln.strip().endswith('pos=prep'):
                        bloco = list(bloco)
                        bloco[j] = ln.rstrip('\r\n') + \
                            u", gen=%s, num=%s%s" % (gen, num, fim)
                        add += 1
            i += 1
        saida.extend(bloco)

    while i < len(pendentes):
        saida.extend(novo_bloco(pendentes[i][0], 1))
        add += 1
        i += 1
    return saida, add


def main():
    entradas = tabela()
    for path, fn in ((DICT, corrigir_dict), (KBB, corrigir_kbb)):
        linhas, fim = _ler(path)
        novas, add = fn(linhas, entradas, fim)
        if add:
            _escrever(path, novas)
        print("%s: %d leitura(s) pos=prep acrescentada(s)"
              % (os.path.basename(path), add))


if __name__ == '__main__':
    main()
