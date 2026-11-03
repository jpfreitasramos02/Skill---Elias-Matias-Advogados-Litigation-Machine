#!/usr/bin/env python3
"""Banco de teses do escritório: teses recorrentes com dispositivos, precedentes e julgados.

Fontes (a local prevalece; ver scripts/banco.py):
  references/teses/*.json   — banco que acompanha a skill (somente leitura no Cowork)
  banco-em/teses/*.json     — banco local, na pasta de trabalho, onde a skill grava

Uso:
  python3 teses.py listar [--cliente AREPC]
  python3 teses.py buscar "termos da tese"                 # ranqueia por título, resumo, tags e ementas
  python3 teses.py mostrar ID                               # tudo da tese, com o status de cada item
  python3 teses.py blocos ID [--todos] [--saida f.json]     # blocos `ementa` + notas prontas para o plano
  python3 teses.py conferir ID --numero N --url URL [--ementa arquivo.txt] [--print img.png] [--por NOME]
  python3 teses.py adicionar ID --julgado julgado.json      # inclui julgado (ou --dispositivo / --precedente)
  python3 teses.py nova --arquivo tese.json                 # cria tese nova no banco local
  python3 teses.py validar                                  # CNJ, links oficiais, conferências vencidas

Status de cada julgado/dispositivo/precedente:
  conferido   visto na fonte oficial (url oficial + data de conferência) — pode ir direto para a peça;
  a_conferir  veio de peça anterior ou de memória: só entra na peça depois de conferido.
Conferências com mais de 12 meses são sinalizadas para reconferência.
"""
import datetime as dt
import glob
import json
import os
import re
import shutil
import sys
import unicodedata
from urllib.parse import urlparse

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from banco import pasta_local, pastas  # noqa: E402
from revisar import CNJ_RE, cnj_valido  # noqa: E402

VALIDADE_MESES = 12
DOMINIOS_OFICIAIS = ('.jus.br', 'planalto.gov.br', '.leg.br', 'al.sp.gov.br', 'legislacao.sp.gov.br',
                     'cnj.jus.br', 'in.gov.br')
LEIS_NOME = {'CPC': 'Código de Processo Civil (Lei nº 13.105/2015)', 'CC': 'Código Civil (Lei nº 10.406/2002)',
             'CDC': 'Código de Defesa do Consumidor (Lei nº 8.078/1990)', 'CTN': 'Código Tributário Nacional (Lei nº 5.172/1966)',
             'CF': 'Constituição Federal'}


def hoje():
    return dt.date.today()


def oficial(url):
    host = urlparse(url or '').netloc.lower()
    return bool(host) and any(host == d.lstrip('.') or host.endswith(d) for d in DOMINIOS_OFICIAIS)


def norm(s):
    s = unicodedata.normalize('NFKD', (s or '').lower())
    return ''.join(c for c in s if not unicodedata.combining(c))


# ------------------------------------------------------------------------------ carga
def carregar():
    teses = {}
    for pasta in pastas('teses'):
        for arq in sorted(glob.glob(os.path.join(pasta, '*.json'))):
            with open(arq, encoding='utf-8') as f:
                t = json.load(f)
            t['_arquivo'] = arq
            teses[t['id']] = t        # a pasta local vem depois e prevalece
    return teses


def salvar_local(t):
    destino = os.path.join(pasta_local(criar=True), 'teses', t['id'] + '.json')
    dados = {k: v for k, v in t.items() if not k.startswith('_')}
    with open(destino, 'w', encoding='utf-8') as f:
        json.dump(dados, f, ensure_ascii=False, indent=2)
    return destino


def obter(teses, tid):
    if tid not in teses:
        sys.exit(f'tese "{tid}" não encontrada. Use: teses.py listar')
    return teses[tid]


# ------------------------------------------------------------------------------ formatação
def vencido(item):
    c = item.get('conferido_em')
    if not c:
        return False
    d = dt.datetime.strptime(c, '%d/%m/%Y').date()
    return (hoje() - d).days > VALIDADE_MESES * 30.5


def status(item):
    if item.get('status') != 'conferido':
        return 'A CONFERIR'
    return 'RECONFERIR (conferido há mais de 12 meses)' if vencido(item) else f'conferido em {item["conferido_em"]}'


def referencia(j):
    trib = j.get('tribunal', '')
    rel = j.get('relator', '')
    if rel and not re.match(r'(Des|Min|Juiz)', rel):
        rel = ('Des. ' if trib.startswith('TJ') else 'Min. ' if trib in ('STJ', 'STF') else '') + rel
    partes = [trib, j.get('orgao', ''), f'{j.get("classe", "")} nº {j.get("numero", "")}'.strip(),
              f'Rel. {rel}' if rel else '', f'j. {j["julgamento"]}' if j.get('julgamento') else '']
    if j.get('publicacao'):
        partes.append(j['publicacao'])
    elif j.get('registro'):
        partes.append(f'registro {j["registro"]}')
    return '(' + ', '.join(p for p in partes if p) + ')'


def nota_dispositivo(d):
    lei = LEIS_NOME.get(d.get('lei'), d.get('lei', ''))
    txt = (d.get('texto') or '').strip()
    if not txt:
        return f'{{{{nota: {lei}:\n[transcrever o art. {d.get("artigo")} da fonte oficial: {d.get("fonte", "")}]}}}}'
    if not re.match(r'^[“"]?Art\.', txt):
        txt = f'“Art. {d.get("artigo")}. ' + txt.lstrip('“"')
    return '{{nota: ' + lei + ':\n' + txt + '}}'


# ------------------------------------------------------------------------------ comandos
def cmd_listar(teses, args):
    cliente = args[args.index('--cliente') + 1] if '--cliente' in args else None
    for t in teses.values():
        if cliente and norm(cliente) not in [norm(c) for c in t.get('clientes', [])]:
            continue
        js = t.get('julgados', [])
        ok = sum(1 for j in js if j.get('status') == 'conferido' and not vencido(j))
        local = ' (local)' if pasta_local() in t['_arquivo'] else ''
        print(f'{t["id"]}{local}\n   {t["titulo"]}\n   clientes: {", ".join(t.get("clientes", []))} | '
              f'julgados: {len(js)} ({ok} conferidos) | dispositivos: {len(t.get("dispositivos", []))} | '
              f'precedentes: {len(t.get("precedentes", []))}')


def cmd_buscar(teses, args):
    termos = [w for w in norm(' '.join(a for a in args if not a.startswith('--'))).split() if len(w) > 2]
    res = []
    for t in teses.values():
        campos = [(t.get('titulo', ''), 4), (' '.join(t.get('tags', [])), 4), (t.get('resumo', ''), 2),
                  (' '.join(j.get('ementa', '') for j in t.get('julgados', [])), 1)]
        pts = sum(peso * norm(txt).count(w) for w in termos for txt, peso in campos)
        if pts:
            res.append((pts, t))
    if not res:
        print('Nenhuma tese encontrada. Pesquise na fonte oficial e, depois de conferir, registre com `nova`.')
    for pts, t in sorted(res, key=lambda x: -x[0])[:8]:
        print(f'[{pts}] {t["id"]} — {t["titulo"]}')


def cmd_mostrar(teses, args):
    t = obter(teses, args[0])
    print(f'{t["titulo"]}\n  id: {t["id"]} | clientes: {", ".join(t.get("clientes", []))}\n  arquivo: {t["_arquivo"]}')
    print(f'\nRESUMO: {t.get("resumo", "")}')
    if t.get('uso'):
        print(f'FRASE DE INTRODUÇÃO: {t["uso"]}')
    for p in t.get('precedentes', []):
        print(f'\nPRECEDENTE {p.get("tipo")} {p.get("numero")}/{p.get("tribunal")} '
              f'{("(" + p["leading_case"] + ")") if p.get("leading_case") else ""} — {status(p)}')
        print(f'  tese: {p.get("tese") or "[não transcrita]"}')
        if p.get('obs'):
            print(f'  obs.: {p["obs"]}')
    for d in t.get('dispositivos', []):
        print(f'\nDISPOSITIVO {d.get("lei")}, art. {d.get("artigo")} — {status(d)}')
        print('  ' + (d.get('texto') or '[não transcrito]')[:300].replace('\n', '\n  '))
    for j in t.get('julgados', []):
        print(f'\nJULGADO {referencia(j)} — {status(j)}')
        if j.get('url'):
            print(f'  fonte: {j["url"]}')
        if j.get('print'):
            print(f'  print: {j["print"]}')
        print('  ' + j.get('ementa', '')[:400] + ('…' if len(j.get('ementa', '')) > 400 else ''))
        if j.get('origem'):
            print(f'  origem: {j["origem"]}')
    if t.get('observacoes'):
        print(f'\nOBSERVAÇÕES: {t["observacoes"]}')


def cmd_blocos(teses, args):
    t = obter(teses, args[0])
    todos = '--todos' in args
    blocos, avisos = [], []
    if t.get('uso'):
        blocos.append({'t': 'p', 'texto': t['uso']})
    for j in t.get('julgados', []):
        ok = j.get('status') == 'conferido' and not vencido(j)
        if not ok and not todos:
            avisos.append(f'omitido (não conferido): {referencia(j)}')
            continue
        ref = referencia(j) + ('' if ok else ' [a conferir na fonte oficial]')
        texto = j['ementa'] if j['ementa'].startswith('“') else f'“{j["ementa"]}”'
        blocos.append({'t': 'ementa', 'tribunal': j.get('tribunal', ''), 'texto': texto, 'referencia': ref})
    notas = {}
    for d in t.get('dispositivos', []):
        chave = f'{d.get("lei")} art. {d.get("artigo")}'
        nota = nota_dispositivo(d)
        if d.get('status') != 'conferido' or vencido(d):
            nota = nota[:-2] + '\n[conferir o texto vigente no Planalto]}}'
        notas[chave] = nota
    for p in t.get('precedentes', []):
        chave = f'{p.get("tipo")} {p.get("numero")}/{p.get("tribunal")}'
        tese = p.get('tese') or f'[transcrever a tese do {chave} da fonte oficial]'
        notas[chave] = '{{nota: ' + f'{chave}' + (f' ({p["leading_case"]})' if p.get('leading_case') else '') + \
                       f': “{tese}”' + ('' if p.get('status') == 'conferido' else ' [conferir na fonte oficial]') + '}}'
    saida = {'tese': t['id'], 'blocos': blocos, 'notas': notas}
    js = json.dumps(saida, ensure_ascii=False, indent=2)
    if '--saida' in args:
        with open(args[args.index('--saida') + 1], 'w', encoding='utf-8') as f:
            f.write(js)
        print(f'gravado em {args[args.index("--saida") + 1]}')
    else:
        print(js)
    for a in avisos:
        print('  ' + a, file=sys.stderr)


def _achar_julgado(t, numero):
    d = re.sub(r'\D', '', numero)
    for j in t.get('julgados', []):
        if re.sub(r'\D', '', j.get('numero', '')) == d:
            return j
    sys.exit(f'julgado {numero} não está na tese {t["id"]}')


def cmd_conferir(teses, args):
    t = obter(teses, args[0])

    def opt(n):
        return args[args.index(n) + 1] if n in args else None
    url = opt('--url')
    if not url or not oficial(url):
        sys.exit('informe --url de fonte OFICIAL (*.jus.br, planalto.gov.br, *.leg.br). '
                 'JusBrasil e similares não valem como conferência.')
    j = _achar_julgado(t, opt('--numero') or '')
    if opt('--ementa'):
        with open(opt('--ementa'), encoding='utf-8') as f:
            nova = f.read().strip()
        if re.sub(r'\W', '', norm(nova)) != re.sub(r'\W', '', norm(j['ementa'].replace('==', ''))):
            print('ATENÇÃO: a ementa da fonte difere da que estava no banco; o banco passa a usar a da fonte.')
            j['ementa_anterior'] = j['ementa']
        j['ementa'] = nova
    j.update({'url': url, 'status': 'conferido', 'conferido_em': hoje().strftime('%d/%m/%Y'),
              'conferido_por': opt('--por') or 'Claude (pesquisa na fonte oficial)'})
    if opt('--print'):
        j['print'] = os.path.abspath(opt('--print'))
    print(f'conferido: {referencia(j)}\ngravado em {salvar_local(t)}')


def cmd_adicionar(teses, args):
    t = obter(teses, args[0])
    for flag, campo in (('--julgado', 'julgados'), ('--dispositivo', 'dispositivos'), ('--precedente', 'precedentes')):
        if flag in args:
            with open(args[args.index(flag) + 1], encoding='utf-8') as f:
                item = json.load(f)
            problemas = validar_item(campo, item)
            if problemas:
                sys.exit('item recusado:\n  - ' + '\n  - '.join(problemas))
            item.setdefault('status', 'a_conferir')
            t.setdefault(campo, []).append(item)
            print(f'incluído em {campo}; gravado em {salvar_local(t)}')
            return
    sys.exit('use --julgado, --dispositivo ou --precedente com um arquivo JSON')


def cmd_nova(teses, args):
    with open(args[args.index('--arquivo') + 1], encoding='utf-8') as f:
        t = json.load(f)
    for campo in ('id', 'titulo', 'resumo'):
        if not t.get(campo):
            sys.exit(f'tese sem "{campo}"')
    if t['id'] in teses:
        sys.exit(f'já existe a tese {t["id"]}; use adicionar')
    problemas = [p for campo in ('julgados', 'dispositivos', 'precedentes') for it in t.get(campo, [])
                 for p in validar_item(campo, it)]
    if problemas:
        sys.exit('tese recusada:\n  - ' + '\n  - '.join(problemas))
    print(f'tese criada: {salvar_local(t)}')


def validar_item(campo, it):
    p = []
    if campo == 'julgados':
        for k in ('tribunal', 'classe', 'numero', 'relator', 'julgamento', 'ementa'):
            if not it.get(k):
                p.append(f'julgado sem "{k}"')
        if CNJ_RE.search(it.get('numero', '')) and not cnj_valido(it['numero']):
            p.append(f'número CNJ {it["numero"]} com dígito verificador inválido')
    if it.get('status') == 'conferido':
        if not oficial(it.get('url') or it.get('fonte')):
            p.append('marcado como conferido sem link de fonte oficial')
        if not it.get('conferido_em'):
            p.append('marcado como conferido sem "conferido_em"')
    return p


def cmd_validar(teses, args):
    total = 0
    for t in teses.values():
        for campo in ('julgados', 'dispositivos', 'precedentes'):
            for it in t.get(campo, []):
                rot = referencia(it) if campo == 'julgados' else f'{it.get("lei") or it.get("tipo")} {it.get("artigo") or it.get("numero")}'
                for prob in validar_item(campo, it):
                    print(f'[ERRO] {t["id"]}: {rot}: {prob}'); total += 1
                if it.get('status') != 'conferido':
                    print(f'[a conferir] {t["id"]}: {rot}'); total += 1
                elif vencido(it):
                    print(f'[reconferir] {t["id"]}: {rot} (conferido em {it["conferido_em"]})'); total += 1
    print(f'{len(teses)} teses; {total} item(ns) com pendência.')


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    cmd, args = sys.argv[1], sys.argv[2:]
    fn = {'listar': cmd_listar, 'buscar': cmd_buscar, 'mostrar': cmd_mostrar, 'blocos': cmd_blocos,
          'conferir': cmd_conferir, 'adicionar': cmd_adicionar, 'nova': cmd_nova, 'validar': cmd_validar}.get(cmd)
    if not fn:
        print(__doc__); sys.exit(1)
    fn(carregar(), args)


if __name__ == '__main__':
    main()
