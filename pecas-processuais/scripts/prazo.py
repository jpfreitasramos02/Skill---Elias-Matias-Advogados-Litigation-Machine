#!/usr/bin/env python3
"""Cálculo de prazo processual em dias úteis (CPC) e quadro de tempestividade pronto.

Uso:
  python3 prazo.py --tipo dje --data 20/10/2026 --dias 15 [opções]

  --tipo        dje      data de DISPONIBILIZAÇÃO no DJEN/DJe (publicação = 1º dia útil seguinte)
                portal   intimação eletrônica pelo portal: --data = data da CONSULTA; com
                         --sem-consulta, --data = data do ENVIO (ciência tácita em 10 dias corridos)
                juntada  data da JUNTADA do AR / mandado / carta (CPC, art. 231, I, II e VI)
                ciencia  qualquer outro termo inicial (ciência inequívoca, retirada dos autos etc.)
  --dias N      prazo em dias úteis (ex.: 15)
  --dobro       prazo em dobro (CPC, arts. 180, 183, 186 e 229)
  --comarca X   inclui os feriados municipais conhecidos da comarca (ex.: "São Paulo", "São Roque")
  --calendario arquivo.json   (repetível) calendário com dias conferidos; ver references/feriados/
  --suspensao "dd/mm/aaaa[-dd/mm/aaaa]|motivo|fonte"   (repetível) suspensão pontual conferida
  --protocolo dd/mm/aaaa      data do protocolo da peça, para dizer se é tempestiva
  --fls "fls. 1.358"          folha do ato, para o parágrafo
  --peca "contraminuta"       nome da peça, para o parágrafo
  --ato "O r. despacho"        ato intimado, para o parágrafo (padrão: "A r. decisão"; a concordância segue o artigo)
  --fundamento "CPC, art. 1.019, II"   dispositivo do prazo, para o parágrafo
  --diario DJEN       nome do diário no parágrafo (padrão: DJEN)
  --plano saida.json          grava os blocos (parágrafo + tabela) para colar no plano da peça

Regra de segurança: dias cuja suspensão depende do calendário anual do TJSP (Carnaval, Semana
Santa, Corpus Christi, feriados municipais, pontos facultativos) entram como "a conferir" até
serem confirmados num arquivo de calendário. O script dá dois termos finais: o CONSERVADOR
(conta esses dias como úteis — use este para protocolar) e o termo CONSIDERANDO as suspensões.
"""
import argparse
import datetime as dt
import glob
import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extenso import inteiro  # noqa: E402
from banco import pastas  # noqa: E402

AQUI = os.path.dirname(os.path.abspath(__file__))
SEMANA = ['segunda-feira', 'terça-feira', 'quarta-feira', 'quinta-feira', 'sexta-feira', 'sábado', 'domingo']

L662 = 'Lei nº 662/1949, art. 1º (redação da Lei nº 10.607/2002)'
NACIONAIS = [
    ((1, 1), 'Confraternização Universal', L662),
    ((4, 21), 'Tiradentes', L662),
    ((5, 1), 'Dia do Trabalho', L662),
    ((9, 7), 'Independência do Brasil', L662),
    ((10, 12), 'Nossa Senhora Aparecida', 'Lei nº 6.802/1980'),
    ((11, 2), 'Finados', L662),
    ((11, 15), 'Proclamação da República', L662),
    ((11, 20), 'Dia Nacional de Zumbi e da Consciência Negra', 'Lei nº 14.759/2023'),
    ((12, 25), 'Natal', L662),
]
ESTADUAIS_SP = [((7, 9), 'Revolução Constitucionalista de 1932', 'Lei Estadual (SP) nº 9.497/1997')]
A_CONFERIR = 'calendário forense do TJSP do ano (Provimento do Conselho Superior da Magistratura) — conferir'
# feriados municipais que costumam suspender o expediente forense: sempre "a conferir"
MUNICIPAIS = {
    'são paulo': [((1, 25), 'Aniversário da cidade de São Paulo', 'lei municipal — conferir no calendário do TJSP')],
    'são roque': [((8, 16), 'Dia de São Roque (padroeiro)', 'lei municipal — conferir no calendário do TJSP')],
}


def pascoa(ano):
    a = ano % 19; b = ano // 100; c = ano % 100; d = b // 4; e = b % 4
    f = (b + 8) // 25; g = (b - f + 1) // 3; h = (19 * a + b - d - g + 15) % 30
    i = c // 4; k = c % 4; l = (32 + 2 * e + 2 * i - h - k) % 7
    m = (a + 11 * h + 22 * l) // 451
    mes = (h + l - 7 * m + 114) // 31; dia = ((h + l - 7 * m + 114) % 31) + 1
    return dt.date(ano, mes, dia)


def data(s):
    s = s.strip()
    for fmt in ('%d/%m/%Y', '%Y-%m-%d'):
        try:
            return dt.datetime.strptime(s, fmt).date()
        except ValueError:
            pass
    sys.exit(f'data inválida: {s} (use dd/mm/aaaa)')


def br(d):
    return d.strftime('%d/%m/%Y')


class Calendario:
    """dias[date] = {'motivo', 'fonte', 'conferido'}; fins de semana tratados à parte."""

    def __init__(self, comarca=None):
        self.dias = {}
        self.comarca = (comarca or '').strip().lower()
        self.anos = set()
        self.arquivos = []

    def _por(self, d, motivo, fonte, conferido, sobrescreve=False):
        if d in self.dias and not sobrescreve:
            return
        self.dias[d] = {'motivo': motivo, 'fonte': fonte, 'conferido': conferido}

    def ano(self, a):
        if a in self.anos:
            return
        self.anos.add(a)
        for (m, d), mot, fonte in NACIONAIS + ESTADUAIS_SP:
            self._por(dt.date(a, m, d), mot, fonte, True)
        p = pascoa(a)
        moveis = [(-48, 'Carnaval (segunda-feira)'), (-47, 'Carnaval (terça-feira)'),
                  (-46, 'Quarta-feira de Cinzas'), (-3, 'Quinta-feira Santa'),
                  (-2, 'Sexta-feira da Paixão'), (60, 'Corpus Christi')]
        for delta, mot in moveis:
            self._por(p + dt.timedelta(days=delta), mot, A_CONFERIR, False)
        self._por(dt.date(a, 10, 28), 'Dia do Servidor Público', A_CONFERIR, False)
        self._por(dt.date(a, 12, 8), 'Dia da Justiça', A_CONFERIR, False)
        for (m, d), mot, fonte in MUNICIPAIS.get(self.comarca, []):
            self._por(dt.date(a, m, d), mot, fonte, False)
        # recesso forense: suspensão de prazos de 20/12 a 20/01 (CPC, art. 220)
        for ini in (dt.date(a - 1, 12, 20), dt.date(a, 12, 20)):
            k = ini
            while k <= dt.date(ini.year + 1, 1, 20):
                self._por(k, 'Suspensão de prazos (20/12 a 20/01)', 'CPC, art. 220', True, sobrescreve=True)
                k += dt.timedelta(days=1)
        # calendários conferidos: references/feriados/ da skill e banco-em/feriados/ local
        for pasta in pastas('feriados'):
            for arq in sorted(glob.glob(os.path.join(pasta, f'*{a}*.json'))):
                self.carregar(arq)

    def carregar(self, arq):
        if arq in self.arquivos:
            return
        self.arquivos.append(arq)
        with open(arq, encoding='utf-8') as f:
            c = json.load(f)
        for e in c.get('dias', []):
            abr = e.get('abrangencia', 'TJSP').lower()
            if abr.startswith('comarca:') and abr.split(':', 1)[1].strip() != self.comarca:
                continue
            if e.get('expediente_normal'):          # confirmado que NÃO há suspensão
                self.dias.pop(data(e['data']), None)
                continue
            self._por(data(e['data']), e['motivo'], e.get('fonte', c.get('fonte_geral', '')),
                      bool(e.get('conferido', False)), sobrescreve=True)
        for s in c.get('suspensoes', []):
            abr = s.get('abrangencia', 'TJSP').lower()
            if abr.startswith('comarca:') and abr.split(':', 1)[1].strip() != self.comarca:
                continue
            k, fim = data(s['de']), data(s.get('ate', s['de']))
            while k <= fim:
                self._por(k, s['motivo'], s.get('fonte', ''), bool(s.get('conferido', False)), sobrescreve=True)
                k += dt.timedelta(days=1)

    def info(self, d):
        self.ano(d.year)
        return self.dias.get(d)

    def util(self, d, cenario):
        """cenario 'conservador': só dias conferidos suspendem; 'suspensoes': todos suspendem."""
        if d.weekday() >= 5:
            return False
        i = self.info(d)
        if not i:
            return True
        return not (i['conferido'] or cenario == 'suspensoes')

    def proximo_util(self, d, cenario):
        d += dt.timedelta(days=1)
        while not self.util(d, cenario):
            d += dt.timedelta(days=1)
        return d


def calcular(cal, tipo, d0, dias, sem_consulta, cenario, diario='DJEN'):
    passos = []
    if tipo == 'dje':
        passos.append((d0, f'Disponibilização no {diario}', 'Lei nº 11.419/2006, art. 4º, § 3º'))
        pub = cal.proximo_util(d0, cenario)
        passos.append((pub, 'Publicação (1º dia útil seguinte à disponibilização)',
                       'Lei nº 11.419/2006, art. 4º, § 3º; CPC, art. 224, § 2º'))
        base = pub
    elif tipo == 'portal':
        if sem_consulta:
            passos.append((d0, 'Envio da intimação pelo portal eletrônico', 'Lei nº 11.419/2006, art. 5º'))
            t = d0 + dt.timedelta(days=10)
            if not cal.util(t, cenario):
                t = cal.proximo_util(t, cenario)
            passos.append((t, 'Intimação tácita (10 dias corridos do envio, sem consulta)',
                           'Lei nº 11.419/2006, art. 5º, § 3º'))
            base = t
        else:
            t = d0 if cal.util(d0, cenario) else cal.proximo_util(d0, cenario)
            passos.append((t, 'Consulta à intimação no portal eletrônico',
                           'Lei nº 11.419/2006, art. 5º, §§ 1º e 2º'))
            base = t
    elif tipo == 'juntada':
        passos.append((d0, 'Juntada aos autos do comprovante de citação/intimação', 'CPC, art. 231, I, II e VI'))
        base = d0
    else:
        passos.append((d0, 'Termo inicial (ciência)', 'CPC, art. 231'))
        base = d0
    ini = cal.proximo_util(base, cenario)
    passos.append((ini, 'Início do prazo (exclui-se o dia do começo)', 'CPC, art. 224, caput e § 3º'))
    fim, n = ini, 1
    while n < dias:
        fim = cal.proximo_util(fim, cenario)
        n += 1
    passos.append((fim, f'Termo final ({dias}º dia útil)', 'CPC, art. 219'))
    return passos, ini, fim


def nao_uteis(cal, de, ate):
    out = []
    k = de
    while k <= ate:
        i = cal.info(k)
        if i and k.weekday() < 5:
            out.append((k, i))
        k += dt.timedelta(days=1)
    return out


def main():
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument('--tipo', required=True, choices=['dje', 'portal', 'juntada', 'ciencia'])
    ap.add_argument('--data', required=True)
    ap.add_argument('--dias', type=int, required=True)
    ap.add_argument('--dobro', action='store_true')
    ap.add_argument('--sem-consulta', action='store_true')
    ap.add_argument('--comarca')
    ap.add_argument('--calendario', action='append', default=[])
    ap.add_argument('--suspensao', action='append', default=[])
    ap.add_argument('--protocolo')
    ap.add_argument('--fls', default='')
    ap.add_argument('--peca', default='peça')
    ap.add_argument('--ato', default='A r. decisão')
    ap.add_argument('--fundamento', default='')
    ap.add_argument('--diario', default='DJEN')
    ap.add_argument('--plano')
    a = ap.parse_args()

    cal = Calendario(a.comarca)
    d0 = data(a.data)
    for y in range(d0.year - 1, d0.year + 2):
        cal.ano(y)
    for arq in a.calendario:
        cal.carregar(arq)
    for s in a.suspensao:
        partes = (s.split('|') + ['', ''])[:3]
        datas = partes[0].split('-') if '/' in partes[0] else [partes[0]]
        k, fim = data(datas[0]), data(datas[-1])
        while k <= fim:
            cal._por(k, partes[1] or 'Suspensão de expediente', partes[2], True, sobrescreve=True)
            k += dt.timedelta(days=1)

    dias = a.dias * (2 if a.dobro else 1)
    passos_c, ini_c, fim_c = calcular(cal, a.tipo, d0, dias, a.sem_consulta, 'conservador', a.diario)
    passos_s, ini_s, fim_s = calcular(cal, a.tipo, d0, dias, a.sem_consulta, 'suspensoes', a.diario)
    periodo = nao_uteis(cal, d0, fim_s)
    pendentes = [(k, i) for k, i in periodo if not i['conferido']]

    # ------------------------------------------------------------------ relatório
    print(f'PRAZO: {dias} ({inteiro(dias)}) dias úteis{" (em dobro)" if a.dobro else ""} — tipo: {a.tipo}')
    for d, ato, fund in passos_s:
        print(f'  {br(d)} ({SEMANA[d.weekday()]})  {ato}  [{fund}]')
    print('\nDias sem expediente no período (fora sábados e domingos):')
    if not periodo:
        print('  nenhum')
    for k, i in periodo:
        st = 'conferido' if i['conferido'] else 'A CONFERIR'
        print(f'  {br(k)} ({SEMANA[k.weekday()]})  {i["motivo"]}  — fonte: {i["fonte"]}  [{st}]')
    print()
    if fim_c == fim_s:
        print(f'TERMO FINAL: {br(fim_c)} ({SEMANA[fim_c.weekday()]})')
        if pendentes:
            print('  (há dias a conferir no período, mas eles não alteram o termo final)')
    else:
        print(f'TERMO FINAL CONSERVADOR (protocole até aqui): {br(fim_c)} ({SEMANA[fim_c.weekday()]})')
        print(f'TERMO FINAL CONSIDERANDO AS SUSPENSÕES A CONFERIR: {br(fim_s)} ({SEMANA[fim_s.weekday()]})')
        print('  -> confirme no calendário do TJSP os dias marcados "A CONFERIR" e registre-os em '
              'banco-em/feriados/ (ou passe --calendario).')
    if a.protocolo:
        p = data(a.protocolo)
        if p <= fim_c:
            print(f'PROTOCOLO em {br(p)}: TEMPESTIVO.')
        elif p <= fim_s:
            print(f'PROTOCOLO em {br(p)}: tempestivo SOMENTE se confirmadas as suspensões a conferir.')
        else:
            print(f'PROTOCOLO em {br(p)}: INTEMPESTIVO (termo final {br(fim_s)}).')

    # ------------------------------------------------------------------ blocos para o plano
    if a.plano:
        cenario = 'suspensoes' if fim_c == fim_s else 'conservador'
        usar = passos_s if cenario == 'suspensoes' else passos_c
        fim = fim_s if cenario == 'suspensoes' else fim_c
        ini = ini_s if cenario == 'suspensoes' else ini_c
        linhas = [[br(d), ato, fund] for d, ato, fund in usar]
        excl = []
        for k, i in periodo:
            if not (usar[0][0] < k <= fim):
                continue
            if not cal.util(k, cenario):
                linhas.append([br(k), f'Sem expediente: {i["motivo"]}', i['fonte']])
                if k >= ini:
                    excl.append(f'{br(k)} ({i["motivo"]})')
            else:
                linhas.append([br(k), f'A conferir: {i["motivo"]} (contado como dia útil)', f'[{i["fonte"]}]'])
        linhas.sort(key=lambda r: dt.datetime.strptime(r[0], '%d/%m/%Y'))
        destaque = [k + 1 for k, r in enumerate(linhas) if r[1].startswith('Termo final')]
        ref = f' [[({a.fls})]]' if a.fls else ' [[(fls. [__])]]'
        fund = f' ({a.fundamento})' if a.fundamento else ''
        if a.tipo == 'dje':
            fem = not a.ato.strip().lower().startswith('o ')
            abre = (f'{a.ato}{ref} foi disponibilizad{"a" if fem else "o"} no {a.diario} em '
                    f'{br(passos_s[0][0])}, considerando-se publicad{"a" if fem else "o"} no primeiro dia útil seguinte, '
                    f'{br(passos_s[1][0])} (Lei nº 11.419/2006, art. 4º, § 3º).')
        elif a.tipo == 'portal':
            abre = (f'A intimação{ref} considera-se realizada em {br(passos_s[-3][0])} '
                    f'(Lei nº 11.419/2006, art. 5º).')
        elif a.tipo == 'juntada':
            abre = f'O comprovante de citação/intimação foi juntado aos autos em {br(d0)}{ref} (CPC, art. 231).'
        else:
            abre = f'A ciência do ato ocorreu em {br(d0)}{ref}.'
        if excl:
            excl_txt = (', excluídos, além de sábados e domingos, ' + ('o dia ' if len(excl) == 1 else 'os dias ')
                        + '; '.join(excl))
        else:
            excl_txt = ', excluídos sábados e domingos'
        texto = (f'{abre} O prazo de {dias} ({inteiro(dias)}) dias úteis{fund}, contado na forma do art. 219 do '
                 f'CPC, teve início em {br(ini)} e se encerra em {br(fim)}'
                 f'{excl_txt}. É, portanto, tempestiva a presente {a.peca}.')
        if fim_c != fim_s:
            texto += (f' [prazo contado de forma conservadora; se confirmada no calendário do TJSP a suspensão de '
                      + '; '.join(f'{br(k)} ({i["motivo"]})' for k, i in pendentes)
                      + f', o termo final passa a {br(fim_s)}]')
        blocos = [{'t': 'p', 'texto': texto},
                  {'t': 'tabela', 'titulo': 'Tempestividade', 'colunas': ['Data', 'Ato', 'Fundamento'],
                   'larguras': [1.2, 3.2, 2.6], 'alinhamento': ['center', 'both', 'left'],
                   'linhas': linhas, 'destaque': destaque}]
        with open(a.plano, 'w', encoding='utf-8') as f:
            json.dump({'blocos': blocos}, f, ensure_ascii=False, indent=2)
        print(f'\nBlocos gravados em {a.plano} (cole na seção de tempestividade do plano).')


if __name__ == '__main__':
    main()
