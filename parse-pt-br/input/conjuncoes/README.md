# Testes de Conjunções

Textos curtos focados na identificação de **conjunções**, agrupados por tipo.
Servem para verificar que o léxico fixa corretamente as conjunções (em especial
"e" e "mas", que arrastam leituras nominais espúrias no dicionário) e que os
passos de coordenação/subordinação as reconhecem.

| Arquivo | Tipo | Conjunções alvo |
|---------|------|-----------------|
| `01_aditivas.txt` | Coordenativas aditivas | e, nem |
| `02_adversativas.txt` | Coordenativas adversativas | mas, porém, contudo, todavia, entretanto |
| `03_alternativas.txt` | Coordenativas alternativas | ou |
| `04_conclusivas.txt` | Coordenativas conclusivas | logo, portanto |
| `05_subordinativas.txt` | Subordinativas | porque, embora, quando, se, enquanto, conforme |

## Como rodar

Pela extensão VSCode NLP++ (um arquivo de cada vez), ou pela linha de comando:

```
nlp.exe -ANA <dir-do-analisador> -WORK <dir-do-motor> input/conjuncoes/01_aditivas.txt -DEV
```

A saída de cada texto fica em `input/conjuncoes/<arquivo>_log/` (`sintagmas.txt`,
`output.json`, `final.tree`). Cada conjunção deve aparecer como
`palavra / conjuncao` (ou renomeada `_coordcl` quando coordena orações).
