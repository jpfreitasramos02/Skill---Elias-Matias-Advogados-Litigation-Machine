#!/usr/bin/env python3
"""Desenha a linha do tempo horizontal (PNG) no padrão visual da Elias, Matias Advogados.

Requer matplotlib (pip install matplotlib). Sem ele, use o bloco "tabela" (Data | Evento | Fls.).

Uso:  python3 linha_tempo.py linha.json

linha.json:
{
  "saida": "linha_tempo.png",
  "eventos": [
    {"data": "15/07/2026", "rotulo": "Suposta infração",
     "descricao": "Condutor habilitado; sem abordagem", "ref": "(docs. 04, 06 a 09)"},
    {"data": "15/09/2026", "rotulo": "Postagem", "descricao": "Notificação expedida",
     "ref": "(doc. 05)", "destaque": true}
  ],
  "trechos": [                                # opcional: legenda sobre o trecho entre dois eventos
    {"de": 0, "ate": 1, "texto": "prazo legal: 30 dias"},
    {"de": 1, "ate": 2, "texto": "atraso: 32 dias", "destaque": true}
  ]
}

Até 6 eventos ficam legíveis numa página. Acima disso, prefira a tabela de linha do tempo.
A "descricao" aceita quebra de linha com \\n; se vier longa, é quebrada automaticamente.
"""
import json
import os
import sys
import textwrap

try:
    import matplotlib
except ImportError:
    sys.exit('matplotlib não instalado: rode "pip install matplotlib" '
             'ou use o bloco "tabela" (Data | Evento | Fls.) no lugar do gráfico.')
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib import font_manager

ESTILO = {'fontes': ['Calibri', 'Carlito', 'Lato', 'DejaVu Sans'],
          'texto': '#262626', 'cinza': '#6B6E76', 'linha': '#D9D9D9', 'passado': '#383B45',
          'acento': '#F69C08'}


def fonte(lista):
    disponiveis = {f.name for f in font_manager.fontManager.ttflist}
    for f in lista:
        if f in disponiveis:
            return f
    return 'DejaVu Sans'


def desenhar(cfg, base='.'):
    est = ESTILO
    plt.rcParams['font.family'] = fonte(est['fontes'])
    ev = cfg['eventos']
    n = len(ev)
    larg = 18.9
    fig, ax = plt.subplots(figsize=(larg / 2.54 * 1.0, 5.25 / 2.54 * 1.0), dpi=250)
    ax.set_xlim(-0.6, n - 0.4)
    ax.set_ylim(-0.8, 10)
    ax.axis('off')
    y = 5.2
    ultimo_destaque = max([k for k, e in enumerate(ev) if e.get('destaque')], default=-1)
    # trilho
    for k in range(n - 1):
        cor = est['linha']
        for t in cfg.get('trechos', []):
            if t['de'] <= k < t['ate']:
                cor = est['acento'] if t.get('destaque') else est['passado']
        ax.plot([k, k + 1], [y, y], color=cor, lw=3.2, solid_capstyle='butt', zorder=1)
    for t in cfg.get('trechos', []):
        meio = (t['de'] + t['ate']) / 2
        ax.text(meio, y + 1.0, t['texto'], ha='center', va='bottom', fontsize=8.5,
                color=est['acento'] if t.get('destaque') else est['cinza'],
                fontweight='bold' if t.get('destaque') else 'normal')
    largura_txt = max(18, int(100 / max(n, 1)))
    for k, e in enumerate(ev):
        d = e.get('destaque')
        cor_borda = est['acento'] if d else est['texto']
        ax.scatter([k], [y], s=95, facecolor='white', edgecolor=cor_borda, linewidths=2.6, zorder=3)
        ax.text(k, 9.3, e['data'], ha='center', va='center', fontsize=11, fontweight='bold',
                color=est['acento'] if d else est['texto'])
        if e.get('rotulo'):
            ax.text(k, 8.1, e['rotulo'].upper(), ha='center', va='center', fontsize=7.5, color=est['cinza'])
        desc = e.get('descricao', '')
        if desc and '\n' not in desc:
            desc = '\n'.join(textwrap.wrap(desc, largura_txt))
        ax.text(k, 3.6, desc, ha='center', va='top', fontsize=8.5, color=est['texto'], linespacing=1.25)
        if e.get('ref'):
            ax.text(k, -0.3, e['ref'], ha='center', va='center', fontsize=7.5, fontweight='bold',
                    color=est['cinza'])
    saida = cfg.get('saida', 'linha_tempo.png')
    if not os.path.isabs(saida):
        saida = os.path.join(base, saida)
    fig.savefig(saida, dpi=250, bbox_inches='tight', pad_inches=0.08, facecolor='white')
    print(f'OK: {saida}')


if __name__ == '__main__':
    if len(sys.argv) != 2:
        print(__doc__); sys.exit(1)
    with open(sys.argv[1], encoding='utf-8') as f:
        cfg = json.load(f)
    desenhar(cfg, os.path.dirname(os.path.abspath(sys.argv[1])))
