#!/usr/bin/env python3
"""Folhas e prints dos autos do e-SAJ (PDF da pasta digital).

Uso:
  python3 autos.py indexar autos.pdf                     # mapa página do PDF -> folha (carimbo "fls.")
  python3 autos.py folha autos.pdf --fls 387             # em que página do PDF está a folha 387
  python3 autos.py buscar autos.pdf "texto a localizar"  # página, folha e trecho onde o texto aparece
  python3 autos.py recortar autos.pdf --de "início do trecho" [--ate "fim do trecho"]
                   [--fls 387 | --pagina 412] [--saida print.png] [--legenda "Trecho da r. decisão"]
                   [--margem 10] [--dpi 200] [--destacar]
  python3 autos.py recortar autos.pdf --fls 387 --area 10,20,90,45 [--saida ...]
                   # recorte por área (% da página: esquerda,topo,direita,base) — página digitalizada

O e-SAJ carimba cada página com "fls. N" na margem. O número da página do PDF NÃO é a folha: o
script lê o carimbo, separa-o das referências a folhas no corpo do texto (preferindo o número na
margem e coerente com a sequência) e, onde faltar carimbo, infere pela sequência (marcado
"inferido"). O índice fica em cache ao lado do PDF (<autos>.indice.json).

`recortar` imprime o bloco `imagem` pronto para o plano, com a legenda terminando em [[(fls. N)]].
Requer poppler (pdftotext, pdftoppm) e Pillow.
"""
import json
import os
import re
import subprocess
import sys
import tempfile
import unicodedata
from collections import Counter
from html import unescape

FLS_JUNTO = re.compile(r'^fls?\.?:?(\d{1,3}(?:\.\d{3})*|\d+)$', re.I)
FLS_SO = re.compile(r'^fls?\.?:?$', re.I)
NUM = re.compile(r'^(\d{1,3}(?:\.\d{3})+|\d+)[.,;)]?$')


def norm(s):
    s = unicodedata.normalize('NFKD', s.lower())
    s = ''.join(c for c in s if not unicodedata.combining(c))
    return re.sub(r'[^\w]', '', s)


def inteiro(s):
    return int(re.sub(r'\D', '', s))


def fmt_fls(n):
    return f'{n:,}'.replace(',', '.')


# ------------------------------------------------------------------------------ leitura
def ler_pdf(pdf, primeira=None, ultima=None):
    """Páginas com blocos > linhas > palavras (coordenadas em pontos, origem no topo)."""
    cmd = ['pdftotext', '-bbox-layout']
    if primeira:
        cmd += ['-f', str(primeira), '-l', str(ultima or primeira)]
    cmd += [pdf, '-']
    xml = subprocess.run(cmd, capture_output=True, check=True).stdout.decode('utf-8', 'replace')
    paginas = []
    for pm in re.finditer(r'<page width="([\d.]+)" height="([\d.]+)">(.*?)</page>', xml, re.S):
        pag = {'w': float(pm.group(1)), 'h': float(pm.group(2)), 'blocos': []}
        for bm in re.finditer(r'<block [^>]*>(.*?)</block>', pm.group(3), re.S):
            bloco = []
            for lm in re.finditer(r'<line [^>]*>(.*?)</line>', bm.group(1), re.S):
                linha = [(float(a), float(b), float(c), float(d), unescape(t)) for a, b, c, d, t in re.findall(
                    r'<word xMin="([\d.]+)" yMin="([\d.]+)" xMax="([\d.]+)" yMax="([\d.]+)">(.*?)</word>', lm.group(1))]
                if linha:
                    bloco.append(linha)
            if bloco:
                pag['blocos'].append(bloco)
        paginas.append(pag)
    return paginas


def palavras(pag):
    return [w for b in pag['blocos'] for l in b for w in l]


# ------------------------------------------------------------------------------ índice de folhas
def candidatos(pag):
    ws = palavras(pag)
    out = []
    for i, w in enumerate(ws):
        x0, y0, x1, y1, t = w
        n = None
        m = FLS_JUNTO.match(t)
        if m:
            n = inteiro(m.group(1))
        elif FLS_SO.match(t) and i + 1 < len(ws) and NUM.match(ws[i + 1][4]):
            n = inteiro(NUM.match(ws[i + 1][4]).group(1))
            x1 = max(x1, ws[i + 1][2]); y1 = max(y1, ws[i + 1][3])
        if n is None:
            continue
        # margem: faixa direita, topo ou rodapé da página
        margem = x0 > pag['w'] * 0.78 or y1 < pag['h'] * 0.10 or y0 > pag['h'] * 0.92
        out.append({'fls': n, 'margem': margem})
    return out


def indexar(pdf, silencioso=False):
    cache = pdf + '.indice.json'
    st = os.stat(pdf)
    chave = f'{st.st_size}:{int(st.st_mtime)}'
    if os.path.exists(cache):
        with open(cache, encoding='utf-8') as f:
            c = json.load(f)
        if c.get('chave') == chave:
            return c['paginas']
    pags = ler_pdf(pdf)
    cands = [candidatos(p) for p in pags]
    # deslocamento mais comum entre folha do carimbo (na margem) e página do PDF
    desl = Counter(c['fls'] - (k + 1) for k, cs in enumerate(cands) for c in cs if c['margem'])
    offset = desl.most_common(1)[0][0] if desl else None
    res = []
    for k, cs in enumerate(cands):
        esperado = (k + 1 + offset) if offset is not None else None
        margem = [c['fls'] for c in cs if c['margem']]
        if esperado in margem:
            res.append({'pagina': k + 1, 'fls': esperado, 'origem': 'carimbo'})
        elif margem:
            res.append({'pagina': k + 1, 'fls': margem[0], 'origem': 'carimbo (fora da sequência)'})
        else:
            res.append({'pagina': k + 1, 'fls': None, 'origem': 'sem carimbo'})
    # inferência pelas vizinhas
    for k, r in enumerate(res):
        if r['fls'] is None:
            ant = next((res[j] for j in range(k - 1, -1, -1) if res[j]['origem'].startswith('carimbo')), None)
            if ant:
                r['fls'] = ant['fls'] + (k - (ant['pagina'] - 1))
                r['origem'] = 'inferido'
        r['sem_texto'] = not palavras(pags[k])
    with open(cache, 'w', encoding='utf-8') as f:
        json.dump({'chave': chave, 'paginas': res}, f, ensure_ascii=False)
    return res


def pagina_da_folha(idx, fls):
    for r in idx:
        if r['fls'] == fls:
            return r
    sys.exit(f'folha {fmt_fls(fls)} não encontrada no índice (folhas de '
             f'{fmt_fls(min(r["fls"] for r in idx if r["fls"]))} a {fmt_fls(max(r["fls"] for r in idx if r["fls"]))})')


# ------------------------------------------------------------------------------ busca
def achar(pag, texto, depois=None):
    """Localiza `texto` na página. Retorna (bloco_i, linha_i_ini, linha_i_fim) ou None.
    `depois` = (bloco_i, linha_i): só aceita ocorrências a partir daí."""
    alvo = [norm(t) for t in texto.split() if norm(t)]
    seq = []   # (token, bloco_i, linha_i)
    for bi, b in enumerate(pag['blocos']):
        for li, l in enumerate(b):
            for w in l:
                n = norm(w[4])
                if n:
                    seq.append((n, bi, li))
    if not alvo:
        return None
    for i in range(len(seq)):
        if depois and (seq[i][1], seq[i][2]) < depois:
            continue
        ok, j, a = True, i, 0
        acumulado = ''
        while a < len(alvo):
            if j >= len(seq):
                ok = False; break
            acumulado += seq[j][0]
            alvo_acum = ''.join(alvo[:a + 1])
            if acumulado == alvo_acum:
                a += 1; j += 1
            elif alvo_acum.startswith(acumulado):      # palavra hifenizada/quebrada em duas
                j += 1
            else:
                ok = False; break
        if ok:
            return seq[i][1], seq[i][2], seq[j - 1][1], seq[j - 1][2]
    return None


def cmd_buscar(pdf, texto):
    idx = indexar(pdf)
    achou = 0
    for pag_n, pag in enumerate(ler_pdf(pdf), 1):
        r = achar(pag, texto)
        if r:
            achou += 1
            info = idx[pag_n - 1]
            linha = ' '.join(w[4] for w in pag['blocos'][r[0]][r[1]])
            print(f'página {pag_n} | fls. {fmt_fls(info["fls"]) if info["fls"] else "?"} ({info["origem"]}) | “{linha[:120]}”')
    if not achou:
        print('texto não encontrado (página digitalizada sem texto? use recortar --area).')


# ------------------------------------------------------------------------------ recorte
def rasterizar(pdf, pagina, dpi):
    from PIL import Image
    with tempfile.TemporaryDirectory() as d:
        base = os.path.join(d, 'p')
        subprocess.run(['pdftoppm', '-r', str(dpi), '-f', str(pagina), '-l', str(pagina), '-png',
                        '-singlefile', pdf, base], check=True)
        im = Image.open(base + '.png')
        im.load()
        return im


def cmd_recortar(pdf, a):
    from PIL import ImageDraw
    idx = indexar(pdf)
    dpi = int(a.get('--dpi', 200))
    margem = float(a.get('--margem', 10))
    if '--fls' in a:
        info = pagina_da_folha(idx, inteiro(a['--fls']))
    elif '--pagina' in a:
        info = idx[int(a['--pagina']) - 1]
    else:
        info = None
    if '--area' in a:
        if not info:
            sys.exit('--area exige --fls ou --pagina')
        l, t, r, b = [float(x) / 100 for x in a['--area'].split(',')]
        im = rasterizar(pdf, info['pagina'], dpi)
        W, H = im.size
        corte = im.crop((int(l * W), int(t * H), int(r * W), int(b * H)))
    else:
        if '--de' not in a:
            sys.exit('informe --de "texto inicial" (e opcionalmente --ate) ou --area')
        paginas = [info['pagina']] if info else range(1, len(idx) + 1)
        achado = None
        for pn in paginas:
            pag = ler_pdf(pdf, pn)[0]
            r = achar(pag, a['--de'])
            if r:
                achado = (pn, pag, r)
                break
        if not achado:
            sys.exit('trecho inicial não encontrado' + (f' na fls. {fmt_fls(info["fls"])}' if info else '')
                     + '. Confira o texto (ou use --area em página digitalizada).')
        pn, pag, (b0, l0, b1, l1) = achado
        info = idx[pn - 1]
        if '--ate' in a:
            r2 = achar(pag, a['--ate'], depois=(b0, l0))
            if not r2:
                sys.exit('trecho final não encontrado na mesma página, depois do inicial.')
            b1, l1 = r2[2], r2[3]
        else:                                    # até o fim do parágrafo do trecho inicial
            bloco = pag['blocos'][b1]
            larg = max(l[-1][2] for l in bloco) - min(l[0][0] for l in bloco)
            l1 = len(bloco) - 1
            for li in range(l0, len(bloco) - 1):
                linha = bloco[li]
                curta = (linha[-1][2] - linha[0][0]) < 0.85 * larg
                if re.search(r'[.:;)”"]$', linha[-1][4]) and curta:
                    l1 = li
                    break
        linhas = []
        todas = [(bi, li, linha) for bi, b in enumerate(pag['blocos']) for li, linha in enumerate(b)]
        for bi, li, linha in todas:
            if (b0, l0) <= (bi, li) <= (b1, l1):
                linhas.append(linha)
        # largura: a da coluna de texto da página (evita cortar recuos), limitada à área útil
        x0 = min(w[0] for l in linhas for w in l)
        x1 = max(w[2] for l in linhas for w in l)
        corpo = [w for w in palavras(pag) if w[0] < pag['w'] * 0.78]
        if corpo:
            x0 = min(x0, min(w[0] for w in corpo)); x1 = max(x1, max(w[2] for w in corpo if w[2] < pag['w'] * 0.80))
        y0 = min(w[1] for w in linhas[0]); y1 = max(w[3] for w in linhas[-1])
        # não invadir as linhas vizinhas: corta no meio do espaço entre elas
        acima = [max(w[3] for w in l) for _, _, l in todas if max(w[3] for w in l) <= y0 + 1 and l[0][0] < x1 and l[-1][2] > x0]
        abaixo = [min(w[1] for w in l) for _, _, l in todas if min(w[1] for w in l) >= y1 - 1 and l[0][0] < x1 and l[-1][2] > x0]
        topo = max(y0 - margem, (max(acima) + y0) / 2) if acima else y0 - margem
        base = min(y1 + margem, (min(abaixo) + y1) / 2) if abaixo else y1 + margem
        im = rasterizar(pdf, pn, dpi)
        k = dpi / 72.0
        caixa = (max(0, int((x0 - margem) * k)), max(0, int(topo * k)),
                 min(im.width, int((x1 + margem) * k)), min(im.height, int(base * k)))
        if '--destacar' in a:
            over = im.convert('RGBA')
            camada = __import__('PIL.Image', fromlist=['Image']).new('RGBA', over.size, (0, 0, 0, 0))
            dr = ImageDraw.Draw(camada)
            for l in linhas:
                dr.rectangle((l[0][0] * k - 2, l[0][1] * k - 1, l[-1][2] * k + 2, max(w[3] for w in l) * k + 1),
                             fill=(255, 235, 59, 90))
            im = __import__('PIL.Image', fromlist=['Image']).alpha_composite(over, camada).convert('RGB')
        corte = im.crop(caixa)
    fls = info['fls']
    saida = a.get('--saida') or f'print_fls_{fls}.png'
    corte.save(saida)
    aviso = '' if info['origem'] == 'carimbo' else \
        f' [folha {"inferida pela sequência" if info["origem"] == "inferido" else info["origem"]}: conferir no PDF]'
    legenda = (a.get('--legenda') or '[descrever o trecho]') + f' [[(fls. {fmt_fls(fls)})]]' + aviso
    bloco = {'t': 'imagem', 'arquivo': os.path.abspath(saida), 'legenda': legenda}
    print(f'OK: {saida} ({corte.width}x{corte.height}px) — página {info["pagina"]} do PDF = fls. {fmt_fls(fls)} ({info["origem"]})')
    print(json.dumps(bloco, ensure_ascii=False))


def opcoes(args):
    a, k = {}, 0
    while k < len(args):
        if args[k].startswith('--'):
            if k + 1 < len(args) and not args[k + 1].startswith('--'):
                a[args[k]] = args[k + 1]; k += 2
            else:
                a[args[k]] = True; k += 1
        else:
            k += 1
    return a


def main():
    if len(sys.argv) < 3:
        print(__doc__); sys.exit(1)
    cmd, pdf = sys.argv[1], sys.argv[2]
    if not os.path.exists(pdf):
        sys.exit(f'PDF não encontrado: {pdf}')
    a = opcoes(sys.argv[3:])
    if cmd == 'indexar':
        idx = indexar(pdf)
        com = [r for r in idx if r['fls']]
        print(f'{len(idx)} páginas | folhas {fmt_fls(com[0]["fls"]) if com else "?"} a {fmt_fls(com[-1]["fls"]) if com else "?"}')
        for r in idx:
            if r['origem'] != 'carimbo' or r['sem_texto']:
                extra = ' | página sem texto (digitalizada)' if r['sem_texto'] else ''
                print(f'  página {r["pagina"]}: fls. {fmt_fls(r["fls"]) if r["fls"] else "?"} — {r["origem"]}{extra}')
        print(f'índice: {pdf}.indice.json')
    elif cmd == 'folha':
        r = pagina_da_folha(indexar(pdf), inteiro(a['--fls']))
        print(f'fls. {fmt_fls(r["fls"])} = página {r["pagina"]} do PDF ({r["origem"]})')
    elif cmd == 'buscar':
        cmd_buscar(pdf, sys.argv[3])
    elif cmd == 'recortar':
        cmd_recortar(pdf, a)
    else:
        print(__doc__); sys.exit(1)


if __name__ == '__main__':
    main()
