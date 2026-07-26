# -*- coding: utf-8 -*-
"""
contracoes.py — tabela das contrações do português (preposição + determinante).

Uma contração é UMA palavra que carrega DUAS classes: uma preposição e o
determinante do sintagma nominal seguinte.

    no    = em + o        naquele = em + aquele
    da    = de + a        pelos   = por + os
    ao    = a  + o        numa    = em + uma

O despejo do Wiktionary não conhece esta fusão: marca "no" como pronome e
"do"/"da" como formas do verbo "dar".  Esta tabela é a fonte única usada
para corrigir o dicionário (`fix_contracoes.py`, `regen_pt_dict.py`); o
analisador tem a mesma lista em `spec/funcoes.nlp`.

NÃO inclui as contrações com PRONOME (dele, nisso, àquilo, ...): essas não
introduzem um determinante e são tratadas à parte.
"""

# preposição -> prefixo da contração
PREPS = [('de', 'd'), ('em', 'n'), ('por', 'pel'), ('a', 'a')]

# família do determinante -> (masc.sing, fem.sing, masc.plur, fem.plur)
FAMILIAS = {
    'o':      ('o',      'a',       'os',       'as'),
    'um':     ('um',     'uma',     'uns',      'umas'),
    'este':   ('este',   'esta',    'estes',    'estas'),
    'esse':   ('esse',   'essa',    'esses',    'essas'),
    'aquele': ('aquele', 'aquela',  'aqueles',  'aquelas'),
    'outro':  ('outro',  'outra',   'outros',   'outras'),
}

# (prep, família) -> (masc.sing, fem.sing, masc.plur, fem.plur) da contração
CONTRACOES = {
    ('de', 'o'):      ('do',      'da',      'dos',      'das'),
    ('em', 'o'):      ('no',      'na',      'nos',      'nas'),
    ('a',  'o'):      ('ao',      'à',       'aos',      'às'),
    ('por', 'o'):     ('pelo',    'pela',    'pelos',    'pelas'),
    ('de', 'um'):     ('dum',     'duma',    'duns',     'dumas'),
    ('em', 'um'):     ('num',     'numa',    'nuns',     'numas'),
    ('de', 'este'):   ('deste',   'desta',   'destes',   'destas'),
    ('em', 'este'):   ('neste',   'nesta',   'nestes',   'nestas'),
    ('de', 'esse'):   ('desse',   'dessa',   'desses',   'dessas'),
    ('em', 'esse'):   ('nesse',   'nessa',   'nesses',   'nessas'),
    ('de', 'aquele'): ('daquele', 'daquela', 'daqueles', 'daquelas'),
    ('em', 'aquele'): ('naquele', 'naquela', 'naqueles', 'naquelas'),
    ('a',  'aquele'): ('àquele',  'àquela',  'àqueles',  'àquelas'),
    ('de', 'outro'):  ('doutro',  'doutra',  'doutros',  'doutras'),
    ('em', 'outro'):  ('noutro',  'noutra',  'noutros',  'noutras'),
}

_FLEX = [('m', 's'), ('f', 's'), ('m', 'p'), ('f', 'p')]


def tabela():
    """[(palavra, prep, determinante, gen, num)] para todas as contrações."""
    linhas = []
    for (prep, fam), formas in CONTRACOES.items():
        dets = FAMILIAS[fam]
        for i, palavra in enumerate(formas):
            gen, num = _FLEX[i]
            linhas.append((palavra, prep, dets[i], gen, num))
    linhas.sort(key=lambda r: r[0].encode('utf-8'))
    return linhas


def por_palavra():
    """palavra -> (prep, determinante, gen, num)"""
    return dict((r[0], r[1:]) for r in tabela())


# Contrações homógrafas de PRONOME PROCLÍTICO.
#
# Os alomorfes de 3ª pessoa "-no/-na/-nos/-nas" são sempre ENCLÍTICOS, isto é,
# aparecem ligados ao verbo por hífen ("viram-no", "põe-na", "disseram-nos").
# Como o hífen é um token à parte, o analisador reconhece-os pelo contexto.
#
# Já "nos" é também o pronome oblíquo de 1ª pessoa do plural ("nós" -> "nos"),
# e esse é PROCLÍTICO: vem antes do verbo, sem hífen.  É por isso a única
# contração que continua ambígua depois de descontada a ênclise:
#
#     Ele nos viu.              -> pronome  (nos = a nós)
#     Pousaram nos jardins.     -> contração (nos = em + os)
#
# A marca "procl=1" no dicionário assinala essa leitura, e o passo
# "contracoes" desempata pela concordância com o determinante fundido.
PROCLITICOS = ('nos',)

# Contrações homógrafas de PRONOME ENCLÍTICO (alomorfes de 3ª pessoa).
#
# "viram-no", "põe-na", "disseram-nos", "levaram-nas": ligados ao verbo por
# hífen.  A marca "encl=1" diz ao passo "contracoes" que vale a pena olhar
# para trás — se houver hífen, é pronome.  Não basta ver se o dicionário dá
# a palavra como pronome: "na" e "nas" só lá constam como preposição.
#
# Note-se que a verificação NÃO pode valer para todas as contrações, porque
# há compostos legítimos com contração depois de hífen: "estrela-do-mar",
# "arco-da-velha", "pé-de-moleque".
ENCLITICOS = ('no', 'na', 'nos', 'nas')


if __name__ == '__main__':
    for palavra, prep, det, gen, num in tabela():
        print("%-9s = %-4s + %-8s (%s%s)" % (palavra, prep, det, gen, num))
