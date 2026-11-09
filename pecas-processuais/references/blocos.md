# Blocos do plano e marcação de texto

O plano é um JSON:

```json
{
  "saida": "Contestacao_Cliente_x_Parte.docx",
  "blocos": [ { "t": "enderecamento", "texto": "..." }, ... ]
}
```

Caminhos relativos (saída e imagens) são resolvidos a partir da pasta do plano.
`python3 scripts/peca.py exemplo` imprime um plano mínimo de petição; `python3 scripts/peca.py exemplo procuracao`, um de procuração.

## Marcação dentro de qualquer texto

| Marcação | Resultado |
| --- | --- |
| `**texto**` | negrito |
| `*texto*` | itálico (use para expressões latinas: *ad judicia et extra*) |
| `++texto++` | sublinhado |
| `==texto==` | destaque: negrito + fundo cinza-claro. Use com parcimônia, no trecho decisivo de um parágrafo ou ementa |
| `[[fls. 708/709]]` | referência aos autos, em negrito. Escreva os parênteses dentro quando a frase pedir: `[[(fls. 10)]]` |
| `{{nota: texto}}` | nota de rodapé no ponto exato (Calibri 9, número sobrescrito). Use `\n` para quebrar parágrafos dentro da nota |
| `[texto]` | pendência: sai grifada em amarelo e é listada pelo script no final. Não são pendências os colchetes editoriais de citação: `[...]`, `[sic]`, `[grifo nosso]`, `[grifos nossos]`, `[g.n.]`, `[destaque nosso]`, `[grifo no original]`, `[sem grifo no original]`, `[grifei]` |
| `\t` | tabulação |
| `\*` | asterisco literal |

## Blocos

| `t` | Campos | Uso |
| --- | --- | --- |
| `enderecamento` | `texto`, `espaco` (linhas em branco depois; padrão 3) | Primeira linha da peça, sem negrito |
| `processo` | `linhas` (lista), `espaco` | "Processo nº ...", ou número do recurso + autos de origem |
| `qualificacao` | `texto` | Parágrafo de abertura (nome da parte em negrito e caixa alta) |
| `titulo` | `texto`, `antes`, `nova_pagina` | Nome da peça centralizado (DEFESA PRÉVIA, CONTESTAÇÃO, RAZÕES DE APELAÇÃO) |
| `secao` | `num` ("I."), `texto` | Tópico principal, centralizado e em negrito. Aceita a marcação de texto |
| `subsecao` | `num` ("III.1."), `texto` | Subtítulo centralizado, em itálico, sem negrito. Aceita a marcação de texto |
| `p` | `texto`, `sem_recuo`, `alinhamento` | Parágrafo de texto corrido (recuo de 1ª linha, justificado, 1,5) |
| `citacao` | `linhas` (lista) ou `texto`, `italico`, `fonte` | Recuo de 4 cm, entrelinha 1,15: artigos de lei transcritos, trechos de decisão ou da peça adversária |
| `ementa` | `tribunal` ("TJSP", "STJ"), `texto` (com aspas), `referencia` | Ementa recuada em itálico, com a referência completa embaixo em cinza |
| `imagem` | `arquivo`, `largura_cm` (padrão 14,5), `legenda`, `borda` | Print centralizado, com legenda em itálico; a legenda deve terminar com a referência `[[fls. X]]` |
| `tabela` | `colunas`, `linhas`, `titulo` (faixa preta; cabeçalho das colunas em amarelo), `larguras` (pesos), `alinhamento` (por coluna; o que faltar usa o padrão), `destaque` (linhas, contando de 1), `legenda` | Linha do tempo em tabela, quadro comparativo, lista de documentos |
| `quadro` | `itens` ([[rótulo, texto], ...]), `titulo` (padrão "Em síntese") | Quadro-resumo: caixa cinza-clara com fio amarelo à esquerda |
| `partes` | `linhas` ([[rótulo, texto], ...]) | Cabeçalho das razões recursais (AGRAVANTE:, AGRAVADA:, AUTOS DE ORIGEM:) |
| `vocativo` | `linhas` | "EGRÉGIO TRIBUNAL, / COLENDA CÂMARA, / ÍNCLITOS JULGADORES," |
| `pedidos` | `intro`, `itens` | Alíneas a), b), c)... com recuo deslocado. Cada item termina em ";" e o último em "." |
| `intimacao` | `texto` (opcional) | Pedido de intimação exclusiva. Sem `texto`, usa o padrão (Rubens e Carla, "sob pena de nulidade") |
| `fecho` | `data` ("hoje" — data do dia em que a skill é usada, horário de Brasília, no formato "3 de novembro de 2026" — ou uma data escrita), `cidade`, `abertura`, `assinatura` (false para omitir), `advogados` ([[nome, OAB], ...]) | "Termos em que, / pede deferimento.", local e data, e assinatura (Rubens e Carla lado a lado) |
| `procuracao` | `outorgante` (qualificação completa, nome em `**negrito**`), `o_a` ("a" ou "o": representá-la/representá-lo), `especiais` (opcional: o que vem depois de "especialmente para"), `nome` (assinatura; padrão: o nome em negrito do outorgante), `outorgados` (opcional: substitui o trecho dos advogados), `data`, `cidade` | Procuração inteira, no texto e no formato do modelo do escritório: título, parágrafo único com os poderes *ad judicia et extra*, local e data, linha de assinatura. Sozinho no plano, sem `fecho` |
| `quebra` | — | Começa o próximo bloco (parágrafo, tabela, quadro ou imagem) em página nova, sem gerar página em branco |
| `espaco` | `n` | Linhas em branco |

## Linha do tempo em gráfico

Para a linha do tempo horizontal (datas no alto, marcos sobre um trilho, descrição e referência
embaixo), gere o PNG com `scripts/linha_tempo.py` (requer `matplotlib`) e insira com um bloco `imagem`. O formato do
JSON está no cabeçalho do script. Funciona bem com até 6 marcos; com mais eventos, use `tabela`
com as colunas Data | Evento | Fls. e `destaque` nas linhas decisivas.
