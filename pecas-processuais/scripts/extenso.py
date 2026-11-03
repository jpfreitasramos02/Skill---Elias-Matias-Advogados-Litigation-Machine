#!/usr/bin/env python3
"""Números e valores em reais por extenso (pt-BR), e comparação tolerante de extensos.

Uso:  python3 extenso.py 2660.26        -> dois mil, seiscentos e sessenta reais e vinte e seis centavos
      python3 extenso.py 15 --inteiro   -> quinze
"""
import re
import sys
import unicodedata

UNID = ['zero', 'um', 'dois', 'três', 'quatro', 'cinco', 'seis', 'sete', 'oito', 'nove', 'dez',
        'onze', 'doze', 'treze', 'quatorze', 'quinze', 'dezesseis', 'dezessete', 'dezoito', 'dezenove']
DEZ = ['', '', 'vinte', 'trinta', 'quarenta', 'cinquenta', 'sessenta', 'setenta', 'oitenta', 'noventa']
CENT = ['', 'cento', 'duzentos', 'trezentos', 'quatrocentos', 'quinhentos', 'seiscentos', 'setecentos',
        'oitocentos', 'novecentos']
ESCALAS = [('', ''), ('mil', 'mil'), ('milhão', 'milhões'), ('bilhão', 'bilhões'), ('trilhão', 'trilhões')]


def _ate_999(n):
    if n == 0:
        return ''
    if n == 100:
        return 'cem'
    c, r = divmod(n, 100)
    partes = []
    if c:
        partes.append(CENT[c])
    if r:
        if r < 20:
            partes.append(UNID[r])
        else:
            d, u = divmod(r, 10)
            partes.append(DEZ[d] + (f' e {UNID[u]}' if u else ''))
    return ' e '.join(partes)


def inteiro(n):
    """Inteiro por extenso: 2660 -> 'dois mil, seiscentos e sessenta'."""
    n = int(n)
    if n == 0:
        return 'zero'
    grupos = []
    k = 0
    while n:
        n, g = divmod(n, 1000)
        grupos.append((k, g))
        k += 1
    grupos = [(k, g) for k, g in reversed(grupos) if g]
    textos = []
    for k, g in grupos:
        sing, plur = ESCALAS[k]
        if k == 1:
            t = 'mil' if g == 1 else f'{_ate_999(g)} mil'
        elif k >= 2:
            t = f'{_ate_999(g)} {sing if g == 1 else plur}'
        else:
            t = _ate_999(g)
        textos.append((g, t))
    out = textos[0][1]
    for g, t in textos[1:]:
        # "e" antes do último grupo quando ele é < 100 ou centena redonda; senão, vírgula
        ult = (g, t) == textos[-1]
        out += (' e ' if ult and (g < 100 or g % 100 == 0) else ', ') + t
    return out


def reais(valor):
    """Valor em reais por extenso: 2660.26 -> 'dois mil, seiscentos e sessenta reais e vinte e seis centavos'."""
    centavos_total = round(float(valor) * 100)
    r, c = divmod(centavos_total, 100)
    partes = []
    if r:
        t = inteiro(r)
        # "um milhão de reais", "dois milhões de reais"
        de = ' de' if r >= 1_000_000 and r % 1_000_000 == 0 else ''
        partes.append(f'{t}{de} {"real" if r == 1 else "reais"}')
    if c:
        partes.append(f'{inteiro(c)} {"centavo" if c == 1 else "centavos"}')
    return ' e '.join(partes) if partes else 'zero real'


def valor_de_texto(txt):
    """'R$ 2.660,26' ou '2.660,26' -> 2660.26"""
    num = re.sub(r'[^\d,]', '', txt).replace(',', '.')
    return float(num)


def _norm(s):
    s = unicodedata.normalize('NFKD', s.lower())
    s = ''.join(ch for ch in s if not unicodedata.combining(ch))
    s = re.sub(r'[^a-z ]', ' ', s)
    s = s.replace('quatorze', 'catorze')
    return [w for w in s.split() if w not in ('e', 'de')]


def confere(escrito, valor):
    """True se o extenso escrito corresponde ao valor (tolera vírgulas, 'e' e acentos)."""
    return _norm(escrito) == _norm(reais(valor))


if __name__ == '__main__':
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    if '--inteiro' in sys.argv:
        print(inteiro(int(sys.argv[1])))
    else:
        print(reais(float(sys.argv[1].replace('.', '').replace(',', '.')) if ',' in sys.argv[1] else float(sys.argv[1])))
