#!/usr/bin/env python3
"""Revisor automático do plano da peça. Roda sozinho ao final de `peca.py gerar`.

Uso:  python3 revisar.py plano.json [--json relatorio.json]

Aponta, com o número do bloco e um trecho:
  1. CNJ        número de processo no padrão CNJ com dígito verificador inválido;
  2. VALOR      valor em R$ sem o extenso no corpo, ou extenso que não confere com o número;
  3. ARTIGO     artigo citado no corpo sem transcrição em nota de rodapé (ou citação recuada);
  4. JULGADO    julgado citado no corpo sem bloco `ementa`; ementa pendente ou com referência
                incompleta; Tema/Súmula sem a tese ou o enunciado transcrito;
  5. FLS        parágrafo que narra fato dos autos (data, ato processual) sem [[fls.]]/Evento/doc.

São alertas para conferência, não erros: o revisor usa heurísticas. Cada alerta deve ser
resolvido na peça ou justificado no resumo de entrega.
"""
import json
import os
import re
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from extenso import confere, reais, valor_de_texto  # noqa: E402

# ------------------------------------------------------------------------------------- CNJ
CNJ_RE = re.compile(r'(?<![\d.])(\d{7})-(\d{2})\.(\d{4})\.(\d)\.(\d{2})\.(\d{4})(?![\d])')


def dv_cnj(n7, ano, j, tr, orig):
    """Dígito verificador do número CNJ (Res. CNJ nº 65/2008, módulo 97 – ISO 7064)."""
    base = int(f'{n7}{ano}{j}{tr}{orig}00')
    return 98 - (base % 97)


def cnj_valido(numero):
    m = CNJ_RE.search(numero)
    if not m:
        return None
    n7, dv, ano, j, tr, orig = m.groups()
    return int(dv) == dv_cnj(n7, ano, j, tr, orig)


# ------------------------------------------------------------------------------- utilidades
def limpar(t):
    """Remove a marcação leve para análise (mantém o texto)."""
    t = re.sub(r'\{\{nota:.*?\}\}', ' ', t, flags=re.S)
    return re.sub(r'\*\*|\+\+|==|(?<!\\)\*', '', t)


def notas_de(t):
    out = []
    i = 0
    while True:
        a = t.find('{{nota:', i)
        if a < 0:
            return out
        prof, k = 0, a + 7
        while k < len(t) - 1:
            if t.startswith('{{', k):
                prof += 1; k += 2; continue
            if t.startswith('}}', k):
                if prof == 0:
                    break
                prof -= 1; k += 2; continue
            k += 1
        out.append(t[a + 7:k])
        i = k + 2


def trecho(t, ini=0, n=90):
    t = re.sub(r'\s+', ' ', limpar(t)).strip()
    if len(t) <= n:
        return t
    ini = max(0, min(ini, len(t) - n))
    return ('…' if ini else '') + t[ini:ini + n] + '…'


def textos_do_bloco(b):
    """Todos os textos de um bloco, com o papel de cada um: corpo, citacao, ementa, tabela, ref."""
    t = b.get('t')
    out = []
    if t in ('p', 'paragrafo', 'qualificacao', 'intimacao'):
        out.append(('corpo', b.get('texto', '')))
    elif t in ('secao', 'subsecao', 'titulo'):
        out.append(('titulo', b.get('texto', '')))
    elif t == 'pedidos':
        out.append(('pedido', b.get('intro', '')))
        out += [('pedido', i) for i in b.get('itens', [])]
    elif t == 'citacao':
        out += [('citacao', l) for l in (b.get('linhas') or [b.get('texto', '')])]
        if b.get('fonte'):
            out.append(('citacao', b['fonte']))
    elif t == 'ementa':
        out.append(('ementa', b.get('texto', '')))
        out.append(('ementa_ref', b.get('referencia', '')))
    elif t == 'tabela':
        for linha in b.get('linhas', []):
            out += [('tabela', str(c)) for c in linha]
    elif t == 'quadro':
        out += [('tabela', str(it[1])) for it in b.get('itens', [])]
    elif t in ('processo', 'partes'):
        for l in b.get('linhas', []):
            out.append(('ref', ' '.join(l) if isinstance(l, list) else l))
    elif t == 'enderecamento':
        out.append(('ref', b.get('texto', '')))
    elif t == 'imagem':
        out.append(('legenda', b.get('legenda', '')))
    elif t == 'procuracao':
        out.append(('corpo', b.get('outorgante', '') + ' ' + b.get('especiais', '')))
    return out


# ------------------------------------------------------------------------------- artigos
LEIS = [
    (r'c[oó]digo de processo civil|\bcpc\b|lei n?º? ?13\.105', 'CPC'),
    (r'c[oó]digo civil|\bcc\b|lei n?º? ?10\.406', 'CC'),
    (r'c[oó]digo tribut[aá]rio|\bctn\b|lei n?º? ?5\.172', 'CTN'),
    (r'c[oó]digo de defesa do consumidor|\bcdc\b|lei n?º? ?8\.078', 'CDC'),
    (r'constitui[cç][aã]o|\bcf\b|\bcrfb\b', 'CF'),
    (r'c[oó]digo de tr[aâ]nsito|\bctb\b|lei n?º? ?9\.503', 'CTB'),
    (r'c[oó]digo penal|\bcp\b', 'CP'),
    (r'\bclt\b', 'CLT'),
]


def lei_de(t):
    tl = t.lower()
    for rx, nome in LEIS:
        if re.search(rx, tl):
            return nome
    m = re.search(r'lei(?: complementar)? n?[ºo°]?\.? ?([\d.]+)', tl)
    return f'Lei {m.group(1).rstrip(".")}' if m else None


def num_art(s):
    return re.sub(r'[.ºo°]', '', s).upper()


ART_CORPO = re.compile(r'\b(?:arts?\.|artigos?)\s*(\d{1,4}(?:\.\d{3})?(?:-[A-Za-z])?)\s*[ºo°]?', re.I)
ART_TRANSCR = re.compile(r'\bArt\.\s*(\d{1,4}(?:\.\d{3})?(?:-[A-Za-z])?)\s*[ºo°]?', re.I)
ART_SIGLA_ANTES = re.compile(r'\(?\b(CPC|CC|CTN|CDC|CF|CTB|CLT)\s*,\s*$')


def lei_perto(texto, ini, fim):
    antes = texto[max(0, ini - 40):ini]
    m = ART_SIGLA_ANTES.search(antes[-12:])
    if m:
        return m.group(1)
    m = re.search(r'Lei(?: Complementar)? n?[ºo°]?\.? ?([\d.]+)(?:/\d{2,4})?\s*,\s*$', antes)
    if m:
        return f'Lei {m.group(1).rstrip(".")}'
    depois = texto[fim:fim + 90]
    # para no fim da frase ou em outro "art."
    corte = re.search(r'[;.](?:\s|$)|\bart', depois[3:])
    if corte:
        depois = depois[:corte.start() + 3]
    return lei_de(depois)


# ------------------------------------------------------------------------------- julgados
JULGADO_RE = re.compile(
    r'\b(REsp|AREsp|RE|ARE|AgInt|AgRg|EDcl|EREsp|HC|RHC|MS|RMS|ADI|ADPF|Rcl|'
    r'Apela[cç][aã]o(?: C[ií]vel)?|APL|Ap\.|Agravo de Instrumento|AI|Agravo Interno|'
    r'Embargos de Declara[cç][aã]o|Recurso Especial|Recurso Extraordin[aá]rio)'
    r'(?:\s+(?:no|na|nos|nas)\s+\w+)*\s*(?:n[º°.]?\s*|n\.º\s*)?([\d][\d.\-/]*\d(?:/[A-Z]{2})?)')
PRECEDENTE_RE = re.compile(r'\b(Tema|S[uú]mula(?: Vinculante)?)\s*(?:n[º°.]?\s*)?(\d{1,4})(?:\s*(?:/|do |da )\s*(STF|STJ|TST|TJSP))?', re.I)


def digitos(s):
    return re.sub(r'\D', '', s)


# ------------------------------------------------------------------------------- fatos
ATOS = re.compile(
    r'\b(?:foi|foram|restou|restaram|ser[aá]|est[aá])\s+(?:juntad|intimad|citad|disponibilizad|publicad|'
    r'protocolad|homologad|deferid|indeferid|proferid|certificad|arrematad|penhorad|expedid|realizad|'
    r'apresentad|distribu[ií]d|recebid|transitad)\w*'
    r'|\b(?:juntou|juntaram|protocolou|requereu|requereram|apresentou|apresentaram|interp[ôo]s|op[ôo]s|'
    r'homologou|deferiu|indeferiu|determinou|proferiu|certificou|arrematou|intimou|citou|expediu|'
    r'manifestou-se|impugnou|peticionou|ajuizou|propôs|transitou)\b', re.I)
DATA = re.compile(r'\b\d{2}/\d{2}/\d{4}\b')
TEM_REF = re.compile(r'\[\[|\bfls?\.\s*\d|\bevento\s*\d|\bev\.\s*\d|\bdoc(?:s)?\.\s*\d|\bID\s*\d|'
                     r'\b[A-Z]{3,}\d+\b|p[aá]g\.\s*\d', re.I)
SECOES_SEM_FATO = re.compile(r'PEDIDO|PREQUESTIONAMENTO|DIREITO|PROVAS|VALOR DA CAUSA', re.I)


# ------------------------------------------------------------------------------- revisão
def revisar(plano):
    blocos = plano.get('blocos', [])
    alertas = []

    def alerta(tipo, k, msg, t=''):
        alertas.append({'tipo': tipo, 'bloco': k + 1, 'msg': msg, 'trecho': t})

    # índices auxiliares
    transcritos = set()        # (lei|None, numero)
    ementa_refs = []           # textos de ementa + referência
    ementa_txt_total = ''
    precedentes_transcritos = ''
    numeros_proprios = set()   # números do próprio processo (não são julgados citados)
    for k, b in enumerate(blocos):
        for papel, t in textos_do_bloco(b):
            for nota in notas_de(t):
                lei = lei_de(nota.split('\n')[0])
                for m in ART_TRANSCR.finditer(nota):
                    transcritos.add((lei, num_art(m.group(1))))
                precedentes_transcritos += ' ' + nota
            if papel == 'citacao':
                lei = lei_de(' '.join(textos for _, textos in textos_do_bloco(b)))
                for m in ART_TRANSCR.finditer(t):
                    transcritos.add((lei, num_art(m.group(1))))
                precedentes_transcritos += ' ' + t
            if papel in ('ementa', 'ementa_ref'):
                ementa_refs.append(t)
                ementa_txt_total += ' ' + t
            if papel == 'ref':
                for m in CNJ_RE.finditer(t):
                    numeros_proprios.add(digitos(m.group(0)))
                for m in JULGADO_RE.finditer(t):
                    numeros_proprios.add(digitos(m.group(2)))
    ementa_digitos = digitos(' '.join(ementa_refs))

    secao_atual = ''
    vistos_valor = {}          # valor -> (tem_extenso, k, trecho)
    for k, b in enumerate(blocos):
        if b.get('t') == 'secao':
            secao_atual = b.get('texto', '')
        for papel, t in textos_do_bloco(b):
            texto_sem_nota = re.sub(r'\{\{nota:.*?\}\}', ' ', t, flags=re.S)
            limpo = limpar(t)

            # 1. CNJ (em qualquer texto, inclusive notas)
            for m in CNJ_RE.finditer(t):
                n7, dv, ano, j, tr, orig = m.groups()
                certo = dv_cnj(n7, ano, j, tr, orig)
                if int(dv) != certo:
                    alerta('CNJ', k, f'nº {m.group(0)} com dígito verificador inválido '
                                     f'(o dígito calculado seria {certo:02d}); confira o número', m.group(0))

            # 2. valores (só no corpo; tabelas, ementas e citações não exigem extenso)
            if papel in ('corpo', 'pedido'):
                for m in re.finditer(r'R\$\s?(\d{1,3}(?:\.\d{3})*,\d{2})', texto_sem_nota):
                    v = valor_de_texto(m.group(1))
                    resto = texto_sem_nota[m.end():m.end() + 260]
                    me = re.match(r'\s*\(([^)]*)\)', resto)
                    tem = bool(me and re.search(r'rea(l|is)|centavo', me.group(1)))
                    if tem and not confere(me.group(1), v):
                        alerta('VALOR', k, f'extenso de R$ {m.group(1)} não confere; o correto é '
                                           f'"{reais(v)}"', me.group(1))
                    ant = vistos_valor.get(v)
                    if ant is None:
                        vistos_valor[v] = [tem, k, m.group(0)]
                    elif tem:
                        ant[0] = True

            # 3. artigos citados no corpo sem transcrição
            if papel == 'corpo' and not re.search('PREQUESTIONAMENTO', secao_atual, re.I):
                for m in ART_CORPO.finditer(texto_sem_nota):
                    n = num_art(m.group(1))
                    lei = lei_perto(texto_sem_nota, m.start(), m.end())
                    ok = (lei, n) in transcritos or (not lei and any(x[1] == n for x in transcritos)) \
                        or (lei and (None, n) in transcritos)
                    if not ok:
                        alerta('ARTIGO', k, f'art. {m.group(1)}{" do " + lei if lei else ""} citado sem '
                                            f'transcrição em nota de rodapé',
                               trecho(texto_sem_nota, m.start() - 30))

            # 4. julgados e precedentes citados no corpo
            if papel in ('corpo', 'pedido'):
                for m in JULGADO_RE.finditer(texto_sem_nota):
                    d = digitos(m.group(2))
                    if len(d) < 4 or d in numeros_proprios:
                        continue
                    if d not in ementa_digitos:
                        alerta('JULGADO', k, f'{m.group(1)} {m.group(2)} citado sem bloco `ementa` com a '
                                             f'ementa e a referência completa', trecho(texto_sem_nota, m.start() - 30))
                for m in PRECEDENTE_RE.finditer(texto_sem_nota):
                    rotulo = f'{m.group(1)} {m.group(2)}'
                    alvo = re.compile(rf'{m.group(1)[:4]}\w*\s*(?:n[º°.]?\s*)?{m.group(2)}\b', re.I)
                    if not alvo.search(precedentes_transcritos + ementa_txt_total):
                        alerta('JULGADO', k, f'{rotulo} citado(a) sem a tese/enunciado transcrito '
                                             f'(nota de rodapé ou citação)', trecho(texto_sem_nota, m.start() - 30))

            # 5. fato sem folha
            if papel == 'corpo' and b.get('t') in ('p', 'paragrafo') and not SECOES_SEM_FATO.search(secao_atual):
                if (DATA.search(limpo) or ATOS.search(limpo)) and not TEM_REF.search(t):
                    # imagem logo em seguida com referência na legenda também vale
                    prox = blocos[k + 1] if k + 1 < len(blocos) else {}
                    if not (prox.get('t') == 'imagem' and TEM_REF.search(prox.get('legenda', ''))):
                        alerta('FLS', k, 'narra fato dos autos (data ou ato processual) sem [[fls.]], '
                                         'Evento ou doc.', trecho(t))

        # ementa: pendente ou com referência incompleta
        if b.get('t') == 'ementa':
            txt, ref = b.get('texto', ''), b.get('referencia', '')
            if re.search(r'\[(ementa|refer)', txt + ref, re.I) or not txt.strip():
                alerta('JULGADO', k, 'ementa pendente: localizar e conferir na fonte oficial', trecho(txt or ref))
            elif ref:
                faltam = []
                if not re.search(r'\d{3,}', ref):
                    faltam.append('número')
                if not re.search(r'\bRel', ref, re.I):
                    faltam.append('relator')
                if not re.search(r'\bj\.|julg', ref, re.I):
                    faltam.append('data de julgamento')
                if faltam:
                    alerta('JULGADO', k, 'referência da ementa sem ' + ', '.join(faltam), trecho(ref))

    for v, (tem, k, txt) in vistos_valor.items():
        if not tem:
            alerta('VALOR', k, f'{txt} sem o valor por extenso em nenhuma menção do corpo; '
                               f'sugestão: "{txt} ({reais(v)})"', txt)
    return alertas


NOMES = {'CNJ': 'Número CNJ inválido', 'VALOR': 'Valores sem extenso / extenso errado',
         'ARTIGO': 'Artigos citados sem transcrição', 'JULGADO': 'Julgados e precedentes',
         'FLS': 'Fatos sem folha dos autos'}


def imprimir(alertas, saida=sys.stdout):
    if not alertas:
        print('  REVISÃO: nenhum alerta.', file=saida)
        return
    print(f'  REVISÃO: {len(alertas)} alerta(s) para conferir', file=saida)
    for tipo in NOMES:
        grupo = [a for a in alertas if a['tipo'] == tipo]
        if not grupo:
            continue
        print(f'   [{tipo}] {NOMES[tipo]} ({len(grupo)})', file=saida)
        for a in grupo:
            print(f'     - bloco {a["bloco"]}: {a["msg"]}', file=saida)
            if a['trecho'] and a['trecho'] not in a['msg']:
                print(f'         “{a["trecho"]}”', file=saida)


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    with open(sys.argv[1], encoding='utf-8') as f:
        plano = json.load(f)
    alertas = revisar(plano)
    imprimir(alertas)
    if '--json' in sys.argv:
        with open(sys.argv[sys.argv.index('--json') + 1], 'w', encoding='utf-8') as f:
            json.dump(alertas, f, ensure_ascii=False, indent=2)


if __name__ == '__main__':
    main()
