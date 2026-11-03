# Calendários de dias sem expediente forense

O `prazo.py` já conhece, sem precisar de arquivo:
- feriados nacionais e o estadual de SP (com a lei de cada um) — tratados como **conferidos**;
- a suspensão de prazos de 20/12 a 20/01 (CPC, art. 220) — **conferida**;
- Carnaval, Quarta-feira de Cinzas, Quinta e Sexta-feira Santa, Corpus Christi, Dia do Servidor
  (28/10), Dia da Justiça (8/12) e alguns feriados municipais — tratados como **a conferir**.

Um dia "a conferir" só passa a suspender o prazo depois de confirmado no calendário oficial do
TJSP (Provimento do Conselho Superior da Magistratura do ano, ou comunicado de suspensão). Ao
confirmar, grave um arquivo `tjsp_AAAA.json` (o ano no nome) em `banco-em/feriados/` na pasta de
trabalho — a skill instalada é somente leitura. Arquivos com o ano no nome, nesta pasta ou na
local, são carregados automaticamente.

Formato (veja `modelo_calendario.json`):

```json
{
  "descricao": "Calendário forense TJSP 2026",
  "fonte_geral": "Provimento CSM nº ___/2025, DJE de __/__/2025",
  "dias": [
    {"data": "16/02/2026", "motivo": "Carnaval (segunda-feira)", "abrangencia": "TJSP",
     "fonte": "Provimento CSM nº ___/2025, art. __", "conferido": true},
    {"data": "28/10/2026", "motivo": "Dia do Servidor Público", "abrangencia": "TJSP",
     "fonte": "Provimento CSM nº ___/2025", "expediente_normal": true},
    {"data": "16/08/2026", "motivo": "Dia de São Roque", "abrangencia": "comarca:São Roque",
     "fonte": "Provimento CSM nº ___/2025", "conferido": true}
  ],
  "suspensoes": [
    {"de": "10/03/2026", "ate": "11/03/2026", "motivo": "Indisponibilidade do e-SAJ",
     "abrangencia": "TJSP", "fonte": "Comunicado SPI nº ___/2026", "conferido": true}
  ]
}
```

- `expediente_normal: true` registra que o dia, embora suspeito, **teve expediente normal**
  (remove a dúvida).
- `abrangencia`: `TJSP` (todo o Estado) ou `comarca:<nome>` (só quando `--comarca` for igual).
- Nunca marque `conferido: true` sem a fonte oficial preenchida.
