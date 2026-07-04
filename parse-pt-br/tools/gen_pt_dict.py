# -*- coding: utf-8 -*-
"""
Gera pt-full.dict e pt-full.kbb (dicionário português) no mesmo formato que
es-full / it-full.

  .dict :  uma linha "palavra pos=X" por cada leitura
  .kbb  :  dictionary -> palavra: -> mXX: pos=..., raiz=..., gen=..., num=...

PROVENIÊNCIA / LICENÇA
----------------------
Todas as formas verbais aqui são CALCULADAS a partir das regras de conjugação
do português (ver `conjugar`), nunca copiadas de um serviço de terceiros.  As
flexões de substantivos e adjetivos também são geradas por regra
(`pluralizar` / `feminino`).  Por isso o dicionário resultante é composto só de
factos linguísticos derivados mecanicamente das regras gramaticais — sem o
conteúdo proprietário do dicionário antigo (que misturava um despejo de
Wiktionary, CC BY-SA, com conjugações da Reverso, proprietárias).  É, portanto,
seguro para distribuição aberta.

COMO AMPLIAR PARA UM LÉXICO COMPLETO
------------------------------------
Os lemas vivem em listas no código (VERBOS_REG, IRREGULARES, SUBST, ADJ, ...).
Para escalar até um léxico completo, coloque uma lista de lemas de origem limpa
em `tools/lemas/`:

  tools/lemas/verbos.txt      -> um infinitivo por linha
  tools/lemas/substantivos.txt-> "palavra<TAB>m|f"  por linha
  tools/lemas/adjetivos.txt   -> um adjetivo (masc. sing.) por linha
  tools/lemas/adverbios.txt   -> um advérbio por linha

Se existirem, são carregadas e flexionadas pelas mesmas regras.  Use uma fonte
de lemas com licença compatível (p. ex. um despejo só de lemas do Wiktionary,
com a devida atribuição CC BY-SA) e o resultado mantém-se distribuível.

Uso:  python tools/gen_pt_dict.py
"""
import os, re, glob, collections

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
LEMAS = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'lemas')

# palavra -> lista de significados; cada significado é um dict de atributos
# (sempre com 'pos').  Ordem de inserção = ordem de m01, m02, ...
ENTRIES = collections.OrderedDict()

def add(word, pos, **attrs):
    m = {'pos': pos}
    m.update({k: v for k, v in attrs.items() if v is not None and v != ''})
    ENTRIES.setdefault(word, [])
    if m not in ENTRIES[word]:          # evita duplicar exatamente o mesmo significado
        ENTRIES[word].append(m)

def noun(word, gen, num, raiz=None):  add(word, 's',   raiz=raiz, gen=gen, num=num)
def adje(word, gen, num, raiz=None):  add(word, 'adj', raiz=raiz, gen=gen, num=num)
def adv(word):                        add(word, 'adv')

# ============================================================================
# 1. MORFOLOGIA NOMINAL  (regras de plural / feminino do português)
# ============================================================================

# exceções de plural (singular -> plural) onde a regra geral falha
PLURAL_EXC = {
    'pão':'pães', 'cão':'cães', 'alemão':'alemães', 'capitão':'capitães',
    'mão':'mãos', 'irmão':'irmãos', 'cidadão':'cidadãos', 'cristão':'cristãos',
    'país':'países', 'mês':'meses', 'gás':'gases', 'ás':'ases', 'lápis':'lápis',
    'fácil':'fáceis', 'difícil':'difíceis', 'fóssil':'fósseis', 'útil':'úteis',
    'mal':'males', 'cônsul':'cônsules', 'fel':'feles',
    'tórax':'tórax', 'fênix':'fênix',
    'qualquer':'quaisquer',
}

def pluralizar(w):
    if w in PLURAL_EXC:
        return PLURAL_EXC[w]
    # vogais (orais e nasais escritas com til) + ditongos -> +s
    if w[-1] in 'aeiouáéíóúâêôãõ':
        if w.endswith('ão'):            # regra geral dos -ão
            return w[:-2] + 'ões'
        return w + 's'
    if w.endswith('m'):                  # -m -> -ns
        return w[:-1] + 'ns'
    if w.endswith('r') or w.endswith('z'):
        return w + 'es'
    if w.endswith('s'):                  # paroxítonas em -s: invariáveis
        return w
    if w.endswith('x'):                  # invariáveis
        return w
    if w.endswith('l'):                  # -al/-el/-ol/-ul -> -is ; -il -> -is
        if w.endswith('el'):
            return w[:-2] + 'éis'
        if w.endswith('ol'):
            return w[:-2] + 'óis'
        if w.endswith('il'):
            return w[:-2] + 'is'
        return w[:-1] + 'is'            # -al, -ul
    if w.endswith('n'):
        return w + 's'
    return w + 's'

# exceções de feminino (masc. -> fem.)
FEM_EXC = {
    'bom':'boa', 'mau':'má', 'são':'sã', 'cristão':'cristã', 'alemão':'alemã',
    'europeu':'europeia', 'ateu':'ateia', 'judeu':'judia', 'cru':'crua', 'nu':'nua',
    'bom':'boa',
}
# adjetivos de 2 terminações invariáveis em género (uniformes)
def feminino(w):
    if w in FEM_EXC:
        return FEM_EXC[w]
    if w.endswith('o'):
        return w[:-1] + 'a'
    if w.endswith('or') and w not in ('melhor','pior','maior','menor','superior','inferior'):
        return w + 'a'
    if w.endswith('ês'):
        return w[:-2] + 'esa'
    if w.endswith('ão'):
        return w[:-2] + 'ã'
    return w                             # -e, -l, -z, -m, -ar, -al, etc.: invariável

def subst(w, gen):
    """Gera singular + plural de um substantivo a partir do lema (sing.)."""
    noun(w, gen, 's')
    pl = pluralizar(w)
    if pl != w:
        noun(pl, gen, 'p', raiz=w)
    else:
        noun(pl, gen, 'p', raiz=w)      # invariável: regista na mesma como plural

def adjetivo(w):
    """Gera masc/fem x sing/plural de um adjetivo a partir do lema (masc. sing.)."""
    fem = feminino(w)
    formas = []
    if fem == w:                        # uniforme (uma só forma de género)
        formas.append((w, 'c', 's'))
        formas.append((pluralizar(w), 'c', 'p'))
    else:
        formas.append((w, 'm', 's'))
        formas.append((pluralizar(w), 'm', 'p'))
        formas.append((fem, 'f', 's'))
        formas.append((pluralizar(fem), 'f', 'p'))
    for f, g, n in formas:
        adje(f, g, n, raiz=(None if f == w else w))

# ============================================================================
# 2. CONJUGAÇÃO VERBAL  (regular: regras puras; irregular: tabela de factos)
# ============================================================================

# Terminações regulares por conjugação.  Cada tempo = 6 pessoas
# (eu, tu, ele, nós, vós, eles).  Tempos não-finitos à parte.
ENDINGS = {
 'ar': {
   'pres_ind': ['o','as','a','amos','ais','am'],
   'pret_perf':['ei','aste','ou','amos','astes','aram'],
   'pret_imp': ['ava','avas','ava','ávamos','áveis','avam'],
   'mqp':      ['ara','aras','ara','áramos','áreis','aram'],
   'fut_ind':  ['arei','arás','ará','aremos','areis','arão'],
   'cond':     ['aria','arias','aria','aríamos','aríeis','ariam'],
   'pres_subj':['e','es','e','emos','eis','em'],
   'imp_subj': ['asse','asses','asse','ássemos','ásseis','assem'],
   'fut_subj': ['ar','ares','ar','armos','ardes','arem'],
   'inf_pess': ['ar','ares','ar','armos','ardes','arem'],
   'imper':    ['ai'],          # imperativo vós (tu/você já saem de ind/subj)
   'ger': 'ando', 'part': 'ado',
 },
 'er': {
   'pres_ind': ['o','es','e','emos','eis','em'],
   'pret_perf':['i','este','eu','emos','estes','eram'],
   'pret_imp': ['ia','ias','ia','íamos','íeis','iam'],
   'mqp':      ['era','eras','era','êramos','êreis','eram'],
   'fut_ind':  ['erei','erás','erá','eremos','ereis','erão'],
   'cond':     ['eria','erias','eria','eríamos','eríeis','eriam'],
   'pres_subj':['a','as','a','amos','ais','am'],
   'imp_subj': ['esse','esses','esse','êssemos','êsseis','essem'],
   'fut_subj': ['er','eres','er','ermos','erdes','erem'],
   'inf_pess': ['er','eres','er','ermos','erdes','erem'],
   'imper':    ['ei'],
   'ger': 'endo', 'part': 'ido',
 },
 'ir': {
   'pres_ind': ['o','es','e','imos','is','em'],
   'pret_perf':['i','iste','iu','imos','istes','iram'],
   'pret_imp': ['ia','ias','ia','íamos','íeis','iam'],
   'mqp':      ['ira','iras','ira','íramos','íreis','iram'],
   'fut_ind':  ['irei','irás','irá','iremos','ireis','irão'],
   'cond':     ['iria','irias','iria','iríamos','iríeis','iriam'],
   'pres_subj':['a','as','a','amos','ais','am'],
   'imp_subj': ['isse','isses','isse','íssemos','ísseis','issem'],
   'fut_subj': ['ir','ires','ir','irmos','irdes','irem'],
   'inf_pess': ['ir','ires','ir','irmos','irdes','irem'],
   'imper':    ['i'],
   'ger': 'indo', 'part': 'ido',
 },
}

def _attach(stem, ending, conj):
    """Junta radical + terminação aplicando as regras ortográficas do
    português (preservação do som de c/g/ç/gu na fronteira)."""
    if not ending:
        return stem
    front = ending[0] in 'eéêi'         # vogal anterior
    back  = ending[0] in 'aãáâoóôu'     # vogal posterior
    if conj == 'ar' and front:
        if stem.endswith('c'):  return stem[:-1] + 'qu' + ending   # ficar -> fique
        if stem.endswith('g'):  return stem[:-1] + 'gu' + ending   # chegar -> chegue
        if stem.endswith('ç'):  return stem[:-1] + 'c'  + ending   # começar -> comece
    if conj in ('er', 'ir') and back:
        if stem.endswith('gu'): return stem[:-2] + 'g'  + ending   # distinguir -> distingo
        if stem.endswith('c'):  return stem[:-1] + 'ç'  + ending   # vencer -> venço
        if stem.endswith('g'):  return stem[:-1] + 'j'  + ending   # dirigir -> dirijo
    return stem + ending

def conjugar(inf):
    """Devolve o conjunto de TODAS as formas flexionadas de um verbo regular,
    calculadas a partir do infinitivo.  Só regras — nada copiado."""
    conj = inf[-2:]
    if conj not in ENDINGS:
        raise ValueError("infinitivo não termina em -ar/-er/-ir: %r" % inf)
    stem = inf[:-2]
    e = ENDINGS[conj]
    formas = set()
    for tempo in ('pres_ind','pret_perf','pret_imp','mqp','fut_ind','cond',
                  'pres_subj','imp_subj','fut_subj','inf_pess'):
        for end in e[tempo]:
            formas.add(_attach(stem, end, conj))
    for end in e['imper']:
        formas.add(_attach(stem, end, conj))
    formas.add(_attach(stem, e['ger'],  conj))
    formas.add(_attach(stem, e['part'], conj))
    formas.add(inf)
    return formas

def verbo_regular(inf):
    formas = conjugar(inf)
    if inf in PART_IRREG:                # troca o particípio regular pelo irregular
        conj = inf[-2:]; stem = inf[:-2]
        formas.discard(_attach(stem, ENDINGS[conj]['part'], conj))
        formas.add(PART_IRREG[inf])
    for f in formas:
        add(f, 'v', raiz=inf)

# --- Verbos irregulares: formas listadas como factos gramaticais -------------
# (paradigmas conhecidos do português; não há criatividade autoral a proteger).
IRREGULARES = {
 'ser':"ser sou és é somos sois são era eras éramos éreis eram fui foste foi fomos "
       "fostes foram fora foras fôramos fôreis serei serás será seremos sereis serão "
       "seria serias seríamos seríeis seriam seja sejas sejamos sejais sejam fosse "
       "fosses fôssemos fôsseis fossem for fores formos fordes forem seres sermos "
       "serdes serem sendo sido",
 'estar':"estar estou estás está estamos estais estão estava estavas estávamos estáveis "
       "estavam estive estiveste esteve estivemos estivestes estiveram estivera estiveras "
       "estivéramos estivéreis estarei estarás estará estaremos estareis estarão estaria "
       "estarias estaríamos estaríeis estariam esteja estejas estejamos estejais estejam "
       "estivesse estivesses estivéssemos estivésseis estivessem estiver estiveres "
       "estivermos estiverdes estiverem estando estado",
 'ter':"ter tenho tens tem temos tendes têm tinha tinhas tínhamos tínheis tinham tive "
       "tiveste teve tivemos tivestes tiveram tivera tiveras tivéramos tivéreis terei "
       "terás terá teremos tereis terão teria terias teríamos teríeis teriam tenha tenhas "
       "tenhamos tenhais tenham tivesse tivesses tivéssemos tivésseis tivessem tiver "
       "tiveres tivermos tiverdes tiverem teres termos terdes terem tendo tido",
 'haver':"haver hei hás há havemos haveis hão havia havias havíamos havíeis haviam houve "
       "houveste houvemos houvestes houveram houvera houveras houvéramos houvéreis haverei "
       "haverás haverá haveremos havereis haverão haveria haverias haveríamos haveríeis "
       "haveriam haja hajas hajamos hajais hajam houvesse houvesses houvéssemos houvésseis "
       "houvessem houver houveres houvermos houverdes houverem haveres havermos haverdes "
       "haverem havendo havido",
 'ir':"ir vou vais vai vamos ides vão ia ias íamos íeis iam fui foste foi fomos fostes "
       "foram fora foras fôramos fôreis irei irás irá iremos ireis irão iria irias iríamos "
       "iríeis iriam vá vás vamos vades vão fosse fosses fôssemos fôsseis fossem for fores "
       "formos fordes forem ires irmos irdes irem indo ido",
 'vir':"vir venho vens vem vimos vindes vêm vinha vinhas vínhamos vínheis vinham vim "
       "vieste veio viemos viestes vieram viera vieras viéramos viéreis virei virás virá "
       "viremos vireis virão viria virias viríamos viríeis viriam venha venhas venhamos "
       "venhais venham viesse viesses viéssemos viésseis viessem vier vieres viermos "
       "vierdes vierem vires virmos virdes virem vindo",
 'ver':"ver vejo vês vê vemos vedes veem via vias víamos víeis viam vi viste viu vimos "
       "vistes viram vira viras víramos víreis verei verás verá veremos vereis verão veria "
       "verias veríamos veríeis veriam veja vejas vejamos vejais vejam visse visses "
       "víssemos vísseis vissem vir vires virmos virdes virem veres vermos verdes verem "
       "vendo visto",
 'dar':"dar dou dás dá damos dais dão dava davas dávamos dáveis davam dei deste deu demos "
       "destes deram dera deras déramos déreis darei darás dará daremos dareis darão daria "
       "darias daríamos daríeis dariam dê dês demos deis deem desse desses déssemos désseis "
       "dessem der deres dermos derdes derem dares darmos dardes darem dando dado",
 'fazer':"fazer faço fazes faz fazemos fazeis fazem fazia fazias fazíamos fazíeis faziam "
       "fiz fizeste fez fizemos fizestes fizeram fizera fizeras fizéramos fizéreis farei "
       "farás fará faremos fareis farão faria farias faríamos faríeis fariam faça faças "
       "façamos façais façam fizesse fizesses fizéssemos fizésseis fizessem fizer fizeres "
       "fizermos fizerdes fizerem fazeres fazermos fazerdes fazerem fazendo feito",
 'dizer':"dizer digo dizes diz dizemos dizeis dizem dizia dizias dizíamos dizíeis diziam "
       "disse disseste dissemos dissestes disseram dissera disseras disséramos disséreis "
       "direi dirás dirá diremos direis dirão diria dirias diríamos diríeis diriam diga "
       "digas digamos digais digam dissesse dissesses disséssemos dissésseis dissessem "
       "disser disseres dissermos disserdes disserem dizeres dizermos dizerdes dizerem "
       "dizendo dito",
 'trazer':"trazer trago trazes traz trazemos trazeis trazem trazia trazias trazíamos "
       "trazíeis traziam trouxe trouxeste trouxemos trouxestes trouxeram trouxera trouxeras "
       "trouxéramos trouxéreis trarei trarás trará traremos trareis trarão traria trarias "
       "traríamos traríeis trariam traga tragas tragamos tragais tragam trouxesse "
       "trouxesses trouxéssemos trouxésseis trouxessem trouxer trouxeres trouxermos "
       "trouxerdes trouxerem trazeres trazermos trazerdes trazerem trazendo trazido",
 'poder':"poder posso podes pode podemos podeis podem podia podias podíamos podíeis podiam "
       "pude pudeste pôde pudemos pudestes puderam pudera puderas pudéramos pudéreis "
       "poderei poderás poderá poderemos podereis poderão poderia poderias poderíamos "
       "poderíeis poderiam possa possas possamos possais possam pudesse pudesses "
       "pudéssemos pudésseis pudessem puder puderes pudermos puderdes puderem poderes "
       "podermos poderdes poderem podendo podido",
 'querer':"querer quero queres quer queremos quereis querem queria querias queríamos "
       "queríeis queriam quis quiseste quisemos quisestes quiseram quisera quiseras "
       "quiséramos quiséreis quererei quererás quererá quereremos querereis quererão "
       "quereria quererias quereríamos quereríeis quereriam queira queiras queiramos "
       "queirais queiram quisesse quisesses quiséssemos quisésseis quisessem quiser "
       "quiseres quisermos quiserdes quiserem quereres querermos quererdes quererem "
       "querendo querido",
 'saber':"saber sei sabes sabe sabemos sabeis sabem sabia sabias sabíamos sabíeis sabiam "
       "soube soubeste soubemos soubestes souberam soubera souberas soubéramos soubéreis "
       "saberei saberás saberá saberemos sabereis saberão saberia saberias saberíamos "
       "saberíeis saberiam saiba saibas saibamos saibais saibam soubesse soubesses "
       "soubéssemos soubésseis soubessem souber souberes soubermos souberdes souberem "
       "saberes sabermos saberdes saberem sabendo sabido",
 'pôr':"pôr ponho pões põe pomos pondes põem punha punhas púnhamos púnheis punham pus "
       "puseste pôs pusemos pusestes puseram pusera puseras puséramos puséreis porei porás "
       "porá poremos poreis porão poria porias poríamos poríeis poriam ponha ponhas "
       "ponhamos ponhais ponham pusesse pusesses puséssemos pusésseis pusessem puser "
       "puseres pusermos puserdes puserem pores pormos pordes porem pondo posto",
 # -ir com alternância vocálica/consonântica no presente (resto regular)
 'dormir':"dormir durmo dormes dorme dormimos dormis dormem dormia dormias dormíamos "
       "dormíeis dormiam dormi dormiste dormiu dormistes dormiram dormira dormiras "
       "dormíramos dormíreis dormirei dormirás dormirá dormiremos dormireis dormirão "
       "dormiria dormirias dormiríamos dormiríeis dormiriam durma durmas durmamos durmais "
       "durmam dormisse dormisses dormíssemos dormísseis dormissem dormir dormires "
       "dormirmos dormirdes dormirem dormires dormindo dormido",
 'sentir':"sentir sinto sentes sente sentimos sentis sentem sentia sentias sentíamos "
       "sentíeis sentiam senti sentiste sentiu sentistes sentiram sentira sentiras "
       "sentíramos sentíreis sentirei sentirás sentirá sentiremos sentireis sentirão "
       "sentiria sentirias sentiríamos sentiríeis sentiriam sinta sintas sintamos sintais "
       "sintam sentisse sentisses sentíssemos sentísseis sentissem sentir sentires "
       "sentirmos sentirdes sentirem sentindo sentido",
 'seguir':"seguir sigo segues segue seguimos seguis seguem seguia seguias seguíamos "
       "seguíeis seguiam segui seguiste seguiu seguistes seguiram seguira seguiras "
       "seguíramos seguíreis seguirei seguirás seguirá seguiremos seguireis seguirão "
       "seguiria seguirias seguiríamos seguiríeis seguiriam siga sigas sigamos sigais "
       "sigam seguisse seguisses seguíssemos seguísseis seguissem seguir seguires "
       "seguirmos seguirdes seguirem seguindo seguido",
 'servir':"servir sirvo serves serve servimos servis servem servia servias servíamos "
       "servíeis serviam servi serviste serviu servistes serviram servira serviras "
       "servíramos servíreis servirei servirás servirá serviremos servireis servirão "
       "serviria servirias serviríamos serviríeis serviriam sirva sirvas sirvamos sirvais "
       "sirvam servisse servisses servíssemos servísseis servissem servir servires "
       "servirmos servirdes servirem servindo servido",
 'pedir':"pedir peço pedes pede pedimos pedis pedem pedia pedias pedíamos pedíeis pediam "
       "pedi pediste pediu pedistes pediram pedira pediras pedíramos pedíreis pedirei "
       "pedirás pedirá pediremos pedireis pedirão pediria pedirias pediríamos pediríeis "
       "pediriam peça peças peçamos peçais peçam pedisse pedisses pedíssemos pedísseis "
       "pedissem pedir pedires pedirmos pedirdes pedirem pedindo pedido",
 'ouvir':"ouvir ouço ouves ouve ouvimos ouvis ouvem ouvia ouvias ouvíamos ouvíeis ouviam "
       "ouvi ouviste ouviu ouvistes ouviram ouvira ouviras ouvíramos ouvíreis ouvirei "
       "ouvirás ouvirá ouviremos ouvireis ouvirão ouviria ouvirias ouviríamos ouviríeis "
       "ouviriam ouça ouças ouçamos ouçais ouçam ouvisse ouvisses ouvíssemos ouvísseis "
       "ouvissem ouvir ouvires ouvirmos ouvirdes ouvirem ouvindo ouvido",
 'sair':"sair saio sais sai saímos saís saem saía saías saíamos saíeis saíam saí saíste "
       "saiu saímos saístes saíram saíra saíras saíramos saíreis sairei sairás sairá "
       "sairemos saireis sairão sairia sairias sairíamos sairíeis sairiam saia saias "
       "saiamos saiais saiam saísse saísses saíssemos saísseis saíssem sair saíres sairmos "
       "sairdes saírem saindo saído",
 'ler':"ler leio lês lê lemos ledes leem lia lias líamos líeis liam li leste leu lemos "
       "lestes leram lera leras lêramos lêreis lerei lerás lerá leremos lereis lerão leria "
       "lerias leríamos leríeis leriam leia leias leiamos leiais leiam lesse lesses "
       "lêssemos lêsseis lessem ler leres lermos lerdes lerem lendo lido",
 'perder':"perder perco perdes perde perdemos perdeis perdem perdia perdias perdíamos "
       "perdíeis perdiam perdi perdeste perdeu perdemos perdestes perderam perdera perderas "
       "perdêramos perdêreis perderei perderás perderá perderemos perdereis perderão "
       "perderia perderias perderíamos perderíeis perderiam perca percas percamos percais "
       "percam perdesse perdesses perdêssemos perdêsseis perdessem perder perderes "
       "perdermos perderdes perderem perdendo perdido",
}

# Particípios irregulares de verbos regulares no resto (lema -> particípio).
PART_IRREG = {
 'abrir':'aberto', 'escrever':'escrito',
 'ganhar':'ganho', 'pagar':'pago', 'gastar':'gasto', 'aceitar':'aceito',
}
def verbo_irregular(lemma, formas):
    for f in formas.split():
        add(f, 'v', raiz=lemma)

# ============================================================================
# 3. CLASSES FECHADAS DO PORTUGUÊS
# ============================================================================

# artigos (definidos / indefinidos) + contrações com de/em/a/por
for w,g,n in [('o','m','s'),('os','m','p'),('a','f','s'),('as','f','p')]:
    add(w,'art',raiz='o',gen=g,num=n)
for w,g,n in [('um','m','s'),('uns','m','p'),('uma','f','s'),('umas','f','p')]:
    add(w,'art',raiz='um',gen=g,num=n)

# contrações preposição (+ artigo / pronome) — marcadas como prep
for w in ("do da dos das no na nos nas ao à aos às num numa nuns numas "
          "dum duma duns dumas pelo pela pelos pelas nele nela neles nelas "
          "dele dela deles delas neste nesta nestes nestas nesse nessa nesses "
          "nessas naquele naquela naqueles naquelas deste desta destes destas "
          "desse dessa desses dessas daquele daquela daqueles daquelas disto "
          "disso daquilo nisto nisso naquilo").split():
    add(w,'prep')

# preposições simples
for p in ("a ante após até com contra de desde em entre para perante por "
          "sem sob sobre trás após").split():
    add(p,'prep')

# pronomes pessoais / oblíquos / tónicos
PRON = {'eu':('m','s'),'tu':('c','s'),'ele':('m','s'),'ela':('f','s'),
        'nós':('c','p'),'vós':('c','p'),'eles':('m','p'),'elas':('f','p'),
        'você':('c','s'),'vocês':('c','p'),
        'me':('c','s'),'te':('c','s'),'se':('c','s'),'lhe':('c','s'),'lhes':('c','p'),
        'nos':('c','p'),'vos':('c','p'),'o':('m','s'),'a':('f','s'),
        'mim':('c','s'),'ti':('c','s'),'si':('c','s'),'comigo':('c','s'),
        'contigo':('c','s'),'connosco':('c','p'),'conosco':('c','p'),'convosco':('c','p'),
        'consigo':('c','s')}
for w,(g,n) in PRON.items(): add(w,'pron',gen=g,num=n)

# demonstrativos
DEM = {'este':('m','s'),'esta':('f','s'),'estes':('m','p'),'estas':('f','p'),
       'esse':('m','s'),'essa':('f','s'),'esses':('m','p'),'essas':('f','p'),
       'aquele':('m','s'),'aquela':('f','s'),'aqueles':('m','p'),'aquelas':('f','p'),
       'isto':('m','s'),'isso':('m','s'),'aquilo':('m','s')}
for w,(g,n) in DEM.items(): add(w,'pron',raiz='este',gen=g,num=n)

# possessivos
POSS = {'meu':('m','s'),'minha':('f','s'),'meus':('m','p'),'minhas':('f','p'),
        'teu':('m','s'),'tua':('f','s'),'teus':('m','p'),'tuas':('f','p'),
        'seu':('m','s'),'sua':('f','s'),'seus':('m','p'),'suas':('f','p'),
        'nosso':('m','s'),'nossa':('f','s'),'nossos':('m','p'),'nossas':('f','p'),
        'vosso':('m','s'),'vossa':('f','s'),'vossos':('m','p'),'vossas':('f','p')}
for w,(g,n) in POSS.items(): add(w,'pron',gen=g,num=n)

# relativos / interrogativos
for w in "que quem qual quais cujo cuja cujos cujas quanto quanta quantos quantas onde".split():
    add(w,'pron')
add('quê','pron')

# conjunções
for w in "e nem mas porém contudo todavia entretanto ou ora logo portanto".split():
    add(w,'conj')
for w in ("que porque pois porquanto como quando enquanto se embora conquanto "
          "conforme segundo consoante caso").split():
    add(w,'conj')

# quantificadores / indefinidos (tratados como art para POSDeterminante)
for w,g,n in [('cada','c','s'),
              ('todo','m','s'),('toda','f','s'),('todos','m','p'),('todas','f','p'),
              ('muito','m','s'),('muita','f','s'),('muitos','m','p'),('muitas','f','p'),
              ('pouco','m','s'),('pouca','f','s'),('poucos','m','p'),('poucas','f','p'),
              ('outro','m','s'),('outra','f','s'),('outros','m','p'),('outras','f','p'),
              ('vário','m','s'),('vária','f','s'),('vários','m','p'),('várias','f','p'),
              ('algum','m','s'),('alguma','f','s'),('alguns','m','p'),('algumas','f','p'),
              ('nenhum','m','s'),('nenhuma','f','s'),('nenhuns','m','p'),('nenhumas','f','p'),
              ('tanto','m','s'),('tanta','f','s'),('tantos','m','p'),('tantas','f','p'),
              ('certo','m','s'),('certa','f','s'),('certos','m','p'),('certas','f','p'),
              ('qualquer','c','s'),('ambos','m','p'),('ambas','f','p')]:
    add(w,'art',gen=g,num=n)

# numerais
for w in ("zero um dois três quatro cinco seis sete oito nove dez onze doze treze "
          "catorze quatorze quinze dezesseis dezessete dezoito dezenove vinte trinta "
          "quarenta cinquenta sessenta setenta oitenta noventa cem cento mil milhão "
          "milhões duas primeiro segundo terceiro").split():
    add(w,'num')

# advérbios comuns (classe fechada de uso)
for w in ("não sim talvez muito pouco mais menos bem mal já ainda sempre nunca jamais "
          "hoje ontem amanhã agora antes depois cedo tarde aqui ali aí lá cá acolá "
          "assim depressa devagar quase apenas também só somente bastante demais "
          "aliás certamente realmente").split():
    adv(w)

# ============================================================================
# 4. CLASSE ABERTA  (lemas — flexionados por regra)
# ============================================================================

# Substantivos: (lema_singular, género)
SUBST = [
 ('homem','m'),('mulher','f'),('menino','m'),('menina','f'),('criança','f'),
 ('amigo','m'),('amiga','f'),('pai','m'),('mãe','f'),('filho','m'),('filha','f'),
 ('irmão','m'),('irmã','f'),('rapaz','m'),('moça','f'),('senhor','m'),('senhora','f'),
 ('professor','m'),('professora','f'),('aluno','m'),('aluna','f'),('médico','m'),
 ('cão','m'),('gato','m'),('cavalo','m'),('pássaro','m'),('peixe','m'),('flor','f'),
 ('árvore','f'),('casa','f'),('porta','f'),('janela','f'),('mesa','f'),('cadeira','f'),
 ('livro','m'),('caderno','m'),('papel','m'),('caneta','f'),('lápis','m'),
 ('cidade','f'),('rua','f'),('praça','f'),('campo','m'),('mar','m'),('rio','m'),
 ('montanha','f'),('céu','m'),('sol','m'),('lua','f'),('estrela','f'),('chuva','f'),
 ('vento','m'),('luz','f'),('noite','f'),('dia','m'),('manhã','f'),('tarde','f'),
 ('hora','f'),('tempo','m'),('ano','m'),('mês','m'),('semana','f'),('mundo','m'),
 ('vida','f'),('água','f'),('terra','f'),('fogo','m'),('pedra','f'),('caminho','m'),
 ('trabalho','m'),('escola','f'),('palavra','f'),('história','f'),('música','f'),
 ('comida','f'),('pão','m'),('café','m'),('leite','m'),('fruta','f'),('carne','f'),
 ('mão','f'),('pé','m'),('olho','m'),('cabeça','f'),('coração','m'),('corpo','m'),
 ('rei','m'),('rainha','f'),('guerra','f'),('paz','f'),('amor','m'),('medo','m'),
 ('força','f'),('verdade','f'),('coisa','f'),('parte','f'),('lugar','m'),('nome','m'),
 ('número','m'),('cor','f'),('porta','f'),('jardim','m'),('animal','m'),
]
for w,g in SUBST: subst(w,g)

# Adjetivos (masc. sing. ou forma uniforme)
ADJ = ("bom mau grande pequeno alto baixo novo velho jovem antigo moderno belo bonito "
       "feio bom forte fraco rico pobre feliz triste alegre rápido lento quente frio "
       "claro escuro branco preto negro vermelho azul verde amarelo longo curto largo "
       "estreito cheio vazio limpo sujo certo errado fácil difícil bom inteligente "
       "amável gentil cansado tranquilo calmo nervoso doce amargo seco molhado "
       "português brasileiro primeiro último próximo mesmo bom outro").split()
for w in ADJ: adjetivo(w)

# Advérbios em -mente (derivados regulares de adjetivos)
for base in ("rápido lento certo claro feliz triste fácil difícil real provável "
             "simples normal final inicial total geral").split():
    fem = feminino(base)
    adv((fem if fem != base else base) + 'mente')

# Verbos regulares (lemas) — TODAS as formas calculadas por `conjugar`
VERBOS_REG = ("falar amar cantar dançar trabalhar estudar morar gostar chamar olhar "
       "encontrar achar deixar passar chegar entrar ficar levar tirar pegar começar "
       "acabar ganhar pagar gastar aceitar jogar brincar andar voltar mudar usar criar "
       "contar perguntar responder mostrar parar pensar lembrar esperar precisar tentar "
       "continuar comer beber correr aprender vender escrever dever receber "
       "conhecer parecer acontecer nascer crescer descer esquecer mexer viver "
       "abrir partir dividir decidir permitir existir assistir insistir discutir").split()
for inf in VERBOS_REG:
    verbo_regular(inf)

# Verbos irregulares (tabela de paradigmas)
for lemma, formas in IRREGULARES.items():
    verbo_irregular(lemma, formas)

# Homógrafos úteis (substantivo/verbo etc.) — desambiguação fica ao analisador
noun('canto','m','s'); add('canto','v',raiz='cantar')
noun('trabalho','m','s'); add('trabalho','v',raiz='trabalhar')
noun('estudo','m','s'); add('estudo','v',raiz='estudar')
add('como','adv'); add('como','v',raiz='comer')
add('era','s',gen='f',num='s')          # era (período) + era (ser/estar)

# ============================================================================
# 5. LEMAS EXTERNOS OPCIONAIS  (para escalar com fonte limpa)
# ============================================================================
def _ler(path):
    if not os.path.exists(path):
        return []
    out = []
    for line in open(path, encoding='utf-8'):
        line = line.strip()
        if line and not line.startswith('#'):
            out.append(line)
    return out

for inf in _ler(os.path.join(LEMAS,'verbos.txt')):
    try:
        verbo_regular(inf)
    except ValueError:
        pass
for line in _ler(os.path.join(LEMAS,'substantivos.txt')):
    parts = re.split(r'\t+', line)
    w = parts[0]; g = parts[1] if len(parts) > 1 else 'm'
    subst(w, g)
for w in _ler(os.path.join(LEMAS,'adjetivos.txt')):
    adjetivo(w)
for w in _ler(os.path.join(LEMAS,'adverbios.txt')):
    adv(w)

# ============================================================================
# 6. EMISSÃO  (.dict e .kbb — formato idêntico ao es/it)
# ============================================================================
def fmt_attrs(m):
    order = ['pos','raiz','gen','num','pes','tem']
    return ", ".join("%s=%s" % (k, m[k]) for k in order
                     if k in m and m[k] is not None and m[k] != '')

dict_lines = ["# Dicionário Português (gerado por regra — gen_pt_dict.py)"]
kbb_lines  = ["# Dicionário Português (gerado por regra — gen_pt_dict.py)", "dictionary"]
for word in sorted(ENTRIES):
    metas = ENTRIES[word]
    for m in metas:
        dict_lines.append("%s pos=%s" % (word, m['pos']))
    kbb_lines.append("  %s:" % word)
    for i, m in enumerate(metas, 1):
        kbb_lines.append("    m%02d: %s" % (i, fmt_attrs(m)))

# Escreve para ficheiros PRÓPRIOS (pt-gen.*) para nunca sobrescrever o
# dicionário do analisador (pt-full.*).  Trocar o analisador para usar este
# dicionário é uma decisão manual.
outdir = os.path.join(ROOT, 'kb', 'user')
os.makedirs(outdir, exist_ok=True)
with open(os.path.join(outdir,'pt-gen.dict'),'w',encoding='utf-8') as f:
    f.write("\n".join(dict_lines)+"\n")
with open(os.path.join(outdir,'pt-gen.kbb'),'w',encoding='utf-8') as f:
    f.write("\n".join(kbb_lines)+"\n")

# ============================================================================
# 7. VERIFICAÇÃO DE COBERTURA DO CORPUS
# ============================================================================
toks = set()
for fn in glob.glob(os.path.join(ROOT,'input','**','*.txt'),recursive=True):
    if '_log' in fn:                    # ignora ficheiros de saída do motor
        continue
    s = open(fn,encoding='utf-8').read().lower()
    toks.update(re.findall(r"[a-zàáâãéêíóôõúç]+", s))

missing = sorted(t for t in toks if t not in ENTRIES)
print("entradas:", len(ENTRIES), " linhas .dict:", len(dict_lines)-1)
print("tokens do corpus:", len(toks), " sem cobertura:", len(missing))
if missing:
    print("FALTAM (%d):" % len(missing), " ".join(missing[:120]),
          "..." if len(missing) > 120 else "")
