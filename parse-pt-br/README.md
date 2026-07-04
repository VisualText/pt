# Analisador de Sintagmas do Português

Um analisador ascendente (bottom-up) que quebra a prosa em português em
sintagmas (sintagmas nominais, verbais e preposicionais) e em orações,
desambiguando as palavras que têm mais de uma classe gramatical.

Todas as regras, nós e funções têm nomes em português.

## Como funciona

O `dicttokz` consulta o `kb/user/pt-full.dict` (carregado preguiçosamente)
e marca cada token com as suas classes gramaticais candidatas
(`s` substantivo, `v` verbo, `adj` adjetivo, `adv` advérbio, `prep`
preposição, `pron` pronome, `art` artigo, `conj` conjunção, `int`
interjeição) e o número de classes (`pos num`). Os passos seguintes
constroem a estrutura de baixo para cima:

| Passo | Função |
|-------|--------|
| `iniciarKB` | Cria o conceito raiz `frases` na base de conhecimento. |
| `funcoes` | Funções auxiliares (`EhNominal`, `EhTipo`, `EhPalavra`, ...) e as listas de palavras de classe fechada. |
| `lexico` | Fixa as classes fechadas (determinantes, auxiliares, preposições, pronomes, conjunções) e marca a ambiguidade de classe aberta como `_ambiguo`. |
| `desambiguar` | Resolve `_ambiguo` pelo contexto, com princípios da gramática portuguesa (roda recursivamente — `rec`). |
| `padroes` | Dá a classe mais provável ao que sobrar ambíguo. |
| `pronrelativo` / `subordinada` | Marcam pronomes relativos e conjunções subordinativas. |
| `predicado` | Garante um verbo em cada oração (reparo do predicado). |
| `sintagmaNominal` / `sintagmaPreposicional` / `sintagmaVerbal` | Constroem `_SN`, `_SP` e `_SV`. |
| `oracaoRelativa` / `oracaoSubordinada` | Agrupam `_ORACAOREL` e `_ORACAOSUB`. |
| `coordTag` / `coordenacao` | Identificam e agrupam orações coordenadas (`_ORACAO`). |
| `frase` | Agrupa tudo de cada frase sob um nó `_FRASE`. |
| `construirKB` | Espelha a árvore na base de conhecimento sob `frases`. |
| `mostrarKB` / `saida` | Salvam `frases.kbb`, escrevem `sintagmas.txt` e `output.json`. |

## Princípios de desambiguação (em `desambiguar`)

* Palavra ambígua capaz de ser **preposição** seguida de determinante/pronome
  encabeça um sintagma preposicional ("sobre os telhados").
* Após **preposição**, a palavra ambígua nominal é o **substantivo** objeto
  ("pelas ruas").
* **Auxiliar/cópula** ou **pronome sujeito** antes de um ambíguo-verbo forçam
  a leitura de **verbo** ("tinha amassado", "ele viu").
* Sujeito + ambíguo-verbo + complemento é o **verbo** da oração
  ("o sol lança luz").
* Adjetivo capaz, antes de um nominal, é **adjetivo anteposto** ("bela manhã");
  depois de um substantivo, é **adjetivo posposto** ("homem velho").
* Após determinante/adjetivo, o ambíguo nominal é o **núcleo substantivo**
  (uma palavra capaz de ser preposição nunca é núcleo).

## Saída

* `sintagmas.txt` — detalhamento legível e indentado, com cada palavra e a
  sua classe.
* `output.json` — a mesma estrutura em JSON:
  `frases → frase[] → sintagma[] (tipo) → palavra[] (texto, classe)`.
* `frases.kbb` — despejo da base de conhecimento.

## Como executar

Pela extensão VSCode NLP++, ou pela linha de comando:

```
nlp.exe -ANA <dir-do-analisador> -WORK <dir-do-motor> input/text.txt
```
