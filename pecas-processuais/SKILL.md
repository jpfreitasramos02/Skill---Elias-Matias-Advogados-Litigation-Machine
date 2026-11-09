---
name: pecas-processuais
description: Redige peças processuais da Elias, Matias Advogados em .docx, no papel timbrado e no padrão de redação do escritório (Calibri, títulos e subtítulos centralizados, tabelas e quadros em preto e cinza, intimação e assinatura de Rubens Carmo Elias Filho e Carla Maluf Elias), cobrindo petições iniciais, contestações e defesas (inclusive administrativas), recursos e contrarrazões (apelação, agravo, contraminuta, REsp, embargos), manifestações, réplicas, alegações finais, petições simples nos autos e procurações *ad judicia et extra* — inclusive nos casos da AREPC e da Hubert. Calcula a tempestividade em dias úteis, recorta prints dos autos do e-SAJ pela folha, reaproveita o banco de teses e julgados conferidos do escritório e revisa a peça ao gerar. Use sempre que pedirem para fazer, redigir, minutar ou montar qualquer peça ou petição, mesmo sem dizer "skill" nem o formato.
---

# Peças processuais — Elias, Matias Advogados

Transforma o material do caso (fatos contados na conversa, autos em PDF, decisão a impugnar, peça
adversária) numa peça pronta para revisão, com o cabeçalho, o rodapé, a fonte e a forma de
redigir da Elias, Matias Advogados.

Arquivos:
- `assets/modelo_em.docx`: papel timbrado do escritório. O script escreve o corpo dentro dele.
- `scripts/peca.py`: gera o .docx a partir de um plano JSON e, ao final, roda o revisor.
  `peca.py data` dá a data de hoje ("3 de novembro de 2026"); `peca.py exemplo` imprime um plano
  mínimo de petição e `exemplo procuracao`, um de procuração.
- `scripts/revisar.py`: revisor automático (também roda sozinho no `gerar`).
- `scripts/autos.py`: índice de folhas, busca e recorte de prints nos PDFs do e-SAJ.
- `scripts/prazo.py`: cálculo de prazo em dias úteis e blocos de tempestividade prontos.
- `scripts/teses.py`: banco de teses, dispositivos e julgados conferidos do escritório.
- `scripts/linha_tempo.py`: linha do tempo em gráfico (requer `matplotlib`; sem ele, use `tabela`).
- `references/blocos.md`: os blocos do plano e a marcação de texto. **Leia antes de montar o plano.**
- `references/estilo.md`: estrutura de cada tipo de peça, regras de redação, particularidades dos
  clientes. **Leia antes de redigir.**
- `references/exemplos/`: três peças reais, para calibrar tom e nível de detalhe.
- `references/teses/` e `references/feriados/`: banco de teses e calendários que acompanham a skill.

**Pasta local do escritório (`banco-em/`).** A skill instalada é somente leitura. O que for
conferido (julgados, calendário do TJSP) é gravado em `banco-em/` na pasta de trabalho — no Cowork,
a pasta escolhida pelo usuário — e lido junto com o que vem na skill. Rode os scripts a partir da
pasta de trabalho (ou defina `BANCO_EM`) para que o banco local seja encontrado e preservado.

## Regra de ouro

Nunca invente fatos, folhas, datas, valores, ementas, números de processo, relatores ou textos de
lei. O que não veio no material e não pode ser conferido em fonte fica em [colchetes] — o script
grifa em amarelo e lista tudo no final. Uma peça com lacunas honestas é útil; uma com um julgado
inventado é perigosa para o advogado que assina.

Colchetes editoriais de citação — `[...]`, `[sic]`, `[grifo nosso]`, `[g.n.]`,
`[destaque nosso]`, `[grifo no original]` — não são pendências e saem sem grifo.

## Passo 1. Reunir e ler o material

Leia tudo o que foi enviado antes de escrever. Dos autos, extraia: partes e qualificação, juízo e
número, a decisão ou peça a responder, datas dos atos (para a tempestividade), valores, e a folha
de cada documento relevante.

**Autos do e-SAJ em PDF** — use `scripts/autos.py` em vez de calcular folhas à mão:
```bash
python3 scripts/autos.py indexar autos.pdf             # página do PDF -> folha (carimbo "fls.")
python3 scripts/autos.py buscar autos.pdf "trecho"     # em que folha está
python3 scripts/autos.py recortar autos.pdf --fls 387 --de "Homologo o laudo" --ate "fls. 387." \
        --legenda "Trecho da r. decisão que homologou o laudo" --saida print_fls387.png
```
O `recortar` corta só o trecho (do texto inicial ao final; sem `--ate`, até o fim do parágrafo) e
imprime o bloco `imagem` pronto, com a legenda terminando em `[[(fls. N)]]`. Folha "inferida"
(página sem carimbo) sai com aviso em [colchetes]. Página digitalizada sem texto: recorte por área
(`--area esq,topo,dir,base` em % da página). No eproc não há folhas: use Evento + documento.

## Passo 2. Perguntar o que for imprescindível

Pergunte antes de redigir, numa única rodada (use a ferramenta de perguntas com opções clicáveis
quando existir, com a sua sugestão como primeira opção), só quando faltar:
- **o tipo de peça** ou o ato a que ela responde, se não der para inferir;
- **a tese ou o resultado pretendido**, quando o material admitir caminhos diferentes;
- **o material essencial**: a decisão recorrida, a inicial a contestar ou os documentos dos fatos.

Não pergunte por dados secundários (CPF, endereço, número da vara, data de intimação): ficam em
[colchetes]. Se nada imprescindível faltar, vá direto ao passo 3.

## Passo 3. Tempestividade

Sempre que houver prazo, calcule com `scripts/prazo.py` (dias úteis, CPC, arts. 219, 220 e 224):
```bash
python3 scripts/prazo.py --tipo dje --data 21/10/2026 --dias 15 --ato "O r. despacho" \
        --fls "fls. 21" --peca contraminuta --fundamento "CPC, art. 1.019, II" --plano tempest.json
```
`--tipo`: `dje` (data de disponibilização no DJEN), `portal` (consulta à intimação eletrônica;
`--sem-consulta` para ciência tácita), `juntada` (AR/mandado juntado) ou `ciencia`. Use
`--comarca` para feriados municipais e `--dobro` quando couber. O `--plano` grava o parágrafo e a
tabela (Data | Ato | Fundamento, com a fonte de cada feriado) para colar na seção de tempestividade.

Feriados de lei federal ou estadual saem como conferidos. Carnaval, Semana Santa, Corpus Christi,
Dia do Servidor, Dia da Justiça e feriados municipais dependem do calendário anual do TJSP e saem
**a conferir**; quando isso muda o resultado, o script dá o termo final **conservador** (use este)
e o termo **considerando as suspensões**. Para resolver, consulte o calendário oficial do TJSP
(Provimento do CSM do ano, comunicados de suspensão) e registre o que for confirmado em
`banco-em/feriados/tjsp_AAAA.json` (formato em `references/feriados/README.md`), com a fonte.
Nunca registre como conferido o que não foi visto na fonte oficial.

## Passo 4. Teses, lei e jurisprudência

1. **Comece pelo banco de teses** do escritório:
   ```bash
   python3 scripts/teses.py buscar "palavras da tese"
   python3 scripts/teses.py mostrar <id>
   python3 scripts/teses.py blocos <id> --saida tese.json     # ementas conferidas + notas prontas
   ```
   Julgados e dispositivos **conferidos** (há menos de 12 meses) podem ir direto para a peça.
   Os **a conferir** (vindos de peças anteriores) só entram depois de conferidos na fonte oficial.
2. **Artigos citados são transcritos na íntegra**, em nota de rodapé, com o texto vigente da fonte
   oficial (planalto.gov.br), não de memória.
3. **Julgados sempre com ementa e referência completa**, conferidos em fonte oficial (e-SAJ/TJSP,
   STJ, STF). JusBrasil e buscadores servem só para achar o julgado; a conferência é no site do
   tribunal. Prefira a Câmara/Turma que julgará o caso e precedentes vinculantes. O que não for
   encontrado vira `[ementa a localizar: ...]`.
4. **Alimente o banco** com o que você conferir:
   `teses.py conferir <id> --numero N --url <link oficial> [--ementa ementa.txt]` para um julgado
   do banco; `teses.py adicionar <id> --julgado j.json` ou `teses.py nova --arquivo tese.json` para
   julgados e teses novos (formato: qualquer arquivo de `references/teses/`). O script recusa
   "conferido" sem link oficial e número CNJ com dígito inválido.
5. Mantenha uma lista do que foi conferido e do que não foi, para o resumo final.

## Passo 5. Redigir e montar o plano

1. Siga a estrutura do tipo de peça em `references/estilo.md` e o tom do exemplo correspondente.
2. Escreva o plano JSON conforme `references/blocos.md`, aproveitando os blocos gerados por
   `prazo.py`, `teses.py` e `autos.py`.
3. Linha do tempo com até 6 marcos: `scripts/linha_tempo.py` + bloco `imagem`; com mais marcos
   (ou sem matplotlib), `tabela` (Data | Evento | Fls.).
4. Nome do arquivo: `<Peça>_<Cliente>x<ParteContrária>.docx`
   (ex.: `Contestacao_HubertxGustavoCapela.docx`, `Manif_Excecao_AREPCxBentoHuzak.docx`).
5. No fecho, use sempre `"data": "hoje"`. Assinatura padrão: Rubens Carmo Elias Filho e Carla Maluf
   Elias (outra só se for pedido).
6. Gere: `python3 scripts/peca.py gerar plano.json`.

Procuração: basta um bloco `procuracao` com a qualificação do outorgante (veja
`references/estilo.md`). Não pergunte pelos dados que faltarem; deixe em [colchetes].

## Passo 6. Revisar e conferir antes de entregar

O `gerar` termina com a **REVISÃO** automática, que aponta:
- número CNJ com dígito verificador inválido;
- valor em R$ sem extenso no corpo, ou extenso que não confere (com a sugestão correta);
- artigo citado sem transcrição em nota de rodapé;
- julgado citado sem bloco `ementa`, ementa pendente ou com referência incompleta, Tema/Súmula sem
  a tese transcrita;
- parágrafo que narra fato dos autos (data, ato processual) sem `[[fls.]]`, Evento ou doc.

São heurísticas: corrija o plano e gere de novo, ou justifique no resumo o que ficar (ex.: um
precedente da parte contrária mencionado só para distinguir). Para revisar sem gerar:
`python3 scripts/revisar.py plano.json`.

Depois, converta para PDF e olhe todas as páginas (`soffice --headless --convert-to pdf` e
`pdftoppm -jpeg -r 70`): quebras de página, tabelas cortadas, prints legíveis, legenda junto do
print, assinatura não isolada no topo de página.

## Passo 7. Entregar

Envie o .docx e um resumo curto:
- tipo de peça;
- teses desenvolvidas, em uma linha cada;
- tempestividade: termo final e se depende de dia a conferir;
- o que ficou em [colchetes], agrupado (dados das partes, folhas, jurisprudência a localizar);
- alertas do revisor que ficaram, com o motivo;
- artigos e julgados que não puderam ser conferidos em fonte, e o que foi gravado no banco local;
- qualquer suposição feita sobre os fatos.
