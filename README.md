# Skill — Elias, Matias Advogados — Litigation Machine

Skill do Claude (Desktop e Cowork) que redige peças processuais da **Elias, Matias Advogados** em
`.docx`, no papel timbrado e no padrão de redação do escritório.

## O que ela faz

- **Peças**: petições iniciais, contestações e defesas, recursos e contrarrazões (apelação, agravo,
  contraminuta, REsp, embargos), manifestações, réplicas, alegações finais, petições simples e
  procurações *ad judicia et extra*. Data do dia ("3 de novembro de 2026") e assinatura padrão de
  Rubens Carmo Elias Filho e Carla Maluf Elias.
- **Revisor automático** (`scripts/revisar.py`), que roda a cada peça gerada: número CNJ com dígito
  verificador inválido, valor sem extenso ou com extenso errado, artigo citado sem transcrição,
  julgado sem ementa, Tema/Súmula sem tese, fato dos autos sem folha.
- **Banco de teses** (`scripts/teses.py`): teses recorrentes com dispositivos, precedentes e
  julgados. Só julgados conferidos em fonte oficial (`*.jus.br`, Planalto) vão direto para a peça.
- **Tempestividade** (`scripts/prazo.py`): prazo em dias úteis (CPC, arts. 219, 220 e 224), com a
  fonte de cada feriado, termo final conservador quando há dia dependente do calendário do TJSP, e
  parágrafo + quadro prontos para a peça.
- **Prints dos autos do e-SAJ** (`scripts/autos.py`): lê o carimbo "fls." de cada página do PDF,
  localiza o trecho e recorta o print com a legenda `(fls. N)`.

## Estrutura

```
pecas-processuais/
├── SKILL.md                    instruções que o Claude segue
├── assets/modelo_em.docx       papel timbrado do escritório
├── scripts/                    peca, revisar, teses, prazo, autos, linha_tempo, extenso, banco
└── references/
    ├── blocos.md, estilo.md    blocos do plano e padrão de redação
    ├── exemplos/               peças reais para calibrar tom e detalhe
    ├── teses/                  banco de teses que acompanha a skill
    └── feriados/               formato dos calendários conferidos do TJSP
```

## Instalar

Baixe **[`dist/pecas-processuais.skill.zip`](dist/pecas-processuais.skill.zip)** (botão "Download raw
file") e envie esse arquivo em **Configurações → Capacidades → Skills → Fazer upload** no Claude.

> Não use o "Code → Download ZIP" do GitHub: esse zip traz o repositório inteiro, com o
> `SKILL.md` dois níveis abaixo da raiz, e o Claude recusa o upload.

Antes, no Claude que vai receber a skill:
- ative **Execução de código e criação de arquivos** (Configurações → Capacidades) — sem isso as
  skills não aparecem;
- se já existir uma skill chamada `pecas-processuais` (por exemplo, a versão antiga, da LSP),
  remova-a ou desative-a antes de enviar esta, que tem o mesmo nome;
- em conta Team/Enterprise, um administrador precisa ter liberado skills para a organização.

Para gerar o zip de novo depois de alterar a skill:

```bash
zip -r dist/pecas-processuais.skill.zip pecas-processuais -x '*__pycache__*'
```

Dependências: Python 3, poppler (`pdftotext`, `pdftoppm`), Pillow e LibreOffice (para conferir o
PDF). `matplotlib` é opcional (linha do tempo em gráfico).

## Banco local (`banco-em/`)

A skill instalada é somente leitura. O que for conferido no uso (julgados, calendário do TJSP) é
gravado em `banco-em/` na pasta de trabalho do Cowork (ou na pasta da variável `BANCO_EM`). Para
incorporar ao repositório, copie os arquivos de `banco-em/teses/` para
`pecas-processuais/references/teses/` e os de `banco-em/feriados/` para
`pecas-processuais/references/feriados/`.
