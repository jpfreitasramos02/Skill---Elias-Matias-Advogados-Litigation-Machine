# Banco de teses do escritório

Um arquivo JSON por tese. Os desta pasta acompanham a skill; os conferidos/novos são gravados em
`banco-em/teses/` na pasta de trabalho (o arquivo local com o mesmo `id` prevalece).

```json
{
  "id": "slug-da-tese",
  "titulo": "Frase que já diz a conclusão",
  "clientes": ["AREPC"],
  "tags": ["palavras", "de", "busca"],
  "resumo": "A tese em 2 ou 3 linhas, com os dispositivos.",
  "uso": "Frase de introdução das ementas na peça (opcional).",
  "dispositivos": [{"lei": "CPC", "artigo": "507", "texto": "“Art. 507. ...”",
                    "fonte": "https://www.planalto.gov.br/...", "status": "conferido",
                    "conferido_em": "03/11/2026"}],
  "precedentes": [{"tipo": "Tema", "numero": "492", "tribunal": "STF", "leading_case": "RE 695.911",
                   "tese": "texto da tese fixada", "url": "https://portal.stf.jus.br/...",
                   "status": "conferido", "conferido_em": "03/11/2026"}],
  "julgados": [{"tribunal": "TJSP", "orgao": "6ª Câmara de Direito Privado",
                "classe": "Agravo de Instrumento", "numero": "0000000-00.0000.8.26.0000",
                "relator": "Fulano", "julgamento": "dd/mm/aaaa", "registro": "dd/mm/aaaa",
                "ementa": "“Texto integral, com ==trecho decisivo== marcado”",
                "url": "https://esaj.tjsp.jus.br/...", "print": "caminho/do/print.png",
                "status": "conferido", "conferido_em": "dd/mm/aaaa", "conferido_por": "...",
                "origem": "peça ou pesquisa de onde veio"}],
  "observacoes": ""
}
```

Regras:
- `status: "conferido"` só com `url` de fonte oficial (`*.jus.br`, `planalto.gov.br`, `*.leg.br`)
  e `conferido_em`. JusBrasil não vale como conferência.
- Conferências com mais de 12 meses são sinalizadas para reconferir.
- Os itens extraídos das peças do escritório estão `a_conferir`: estavam em peças protocoladas,
  mas ainda não foram vistos na fonte oficial por esta skill.
