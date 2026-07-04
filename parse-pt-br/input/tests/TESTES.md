# Testes de Robustez — Analisador de Sintagmas do Português

30 textos curtos, cada um concentrado numa construção gramatical, para
exercitar e endurecer (hardening) o analisador. Use-os para detectar regressões
ao alterar os passos de desambiguação ou de construção de sintagmas.

| # | Arquivo | Construção alvo | O que estressa |
|---|---------|-----------------|----------------|
| 01 | `01_sn_simples.txt` | Sintagma nominal simples | determinante + substantivo, `_SN` mínimo |
| 02 | `02_adjetivo_posposto.txt` | Adjetivo posposto | `subst + adj` (ordem típica do PT) |
| 03 | `03_adjetivo_anteposto.txt` | Adjetivo anteposto | `adj + subst` ("bela manhã") |
| 04 | `04_sintagma_preposicional.txt` | Sintagma preposicional | `prep + SN`, várias preposições |
| 05 | `05_contracoes.txt` | Contrações | do/da/no/na/pelos/pelas/ao/num |
| 06 | `06_locucoes_verbais.txt` | Locuções verbais | auxiliar + particípio/gerúndio, `_SV` |
| 07 | `07_pronomes_sujeito.txt` | Pronomes sujeito | eu/tu/ele/nós/... + verbo |
| 08 | `08_enclise_proclise.txt` | Ênclise e próclise | pronomes oblíquos, hífen (`-se`, `-lo`, `-lhe`) |
| 09 | `09_oracao_relativa.txt` | Orações relativas | que/quem/cujo/onde, `_ORACAOREL` |
| 10 | `10_oracao_subordinada.txt` | Orações subordinadas | porque/quando/embora/se, `_ORACAOSUB` |
| 11 | `11_coordenacao_oracoes.txt` | Coordenação de orações | e/mas/ou entre orações, `_ORACAO` |
| 12 | `12_coordenacao_sintagmas.txt` | Coordenação de sintagmas | listas nominais com vírgula e "e" |
| 13 | `13_numerais_quantificadores.txt` | Numerais e quantificadores | três/cem/muitos/poucos/vários |
| 14 | `14_nomes_proprios.txt` | Nomes próprios | entidades, palavras fora do dicionário |
| 15 | `15_infinitivo_finalidade.txt` | Infinitivo / finalidade | "para + infinitivo", "de + infinitivo" |
| 16 | `16_negacao.txt` | Negação | não/nunca/ninguém/nem/nenhum |
| 17 | `17_comparativos.txt` | Comparativos | mais...que, tão...quanto |
| 18 | `18_superlativos.txt` | Superlativos | o mais..., sufixo -íssimo |
| 19 | `19_tempos_verbais.txt` | Tempos verbais | presente/pretérito/futuro/subjuntivo |
| 20 | `20_voz_passiva.txt` | Voz passiva | ser + particípio + "por" |
| 21 | `21_gerundio.txt` | Gerúndio | estar + gerúndio, gerúndio adverbial |
| 22 | `22_participio_adjetivo.txt` | Particípio como adjetivo | "telhados cobertos", "porta fechada" |
| 23 | `23_demonstrativos.txt` | Demonstrativos | este/esse/aquele/isto/aquilo |
| 24 | `24_possessivos.txt` | Possessivos | meu/teu/seu/nosso, "os meus amigos" |
| 25 | `25_adverbios_mente.txt` | Advérbios em -mente | calmamente, rapidamente, felizmente |
| 26 | `26_interrogativas.txt` | Interrogativas | quem/que/qual/quando/onde/como/por que |
| 27 | `27_imperativo.txt` | Imperativo | "Abra a janela", reparo do predicado |
| 28 | `28_datas_tempo.txt` | Datas e expressões de tempo | "quinze de março", "às quatro horas" |
| 29 | `29_dialogo.txt` | Diálogo / discurso direto | travessões, verbos dicendi |
| 30 | `30_complexo.txt` | Texto complexo | mistura de todas as construções acima |

## Como rodar todos os testes

Pela extensão VSCode NLP++ (um arquivo de cada vez), ou pela linha de comando:

```
nlp.exe -ANA <dir-do-analisador> -WORK <dir-do-motor> input/tests/01_sn_simples.txt
```

A saída de cada texto fica em `input/tests/<arquivo>_log/` (`sintagmas.txt`,
`output.json`, `final.tree`).
