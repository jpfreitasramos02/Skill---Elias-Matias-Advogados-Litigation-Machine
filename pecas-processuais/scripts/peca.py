#!/usr/bin/env python3
"""Gera peças processuais (.docx) no padrão da Elias, Matias Advogados.

Uso:
  python3 peca.py gerar plano.json      # monta a peça a partir do plano
  python3 peca.py data                  # data de hoje por extenso
  python3 peca.py exemplo               # imprime um plano de exemplo (petição)
  python3 peca.py exemplo procuracao    # imprime um plano de procuração

O plano é um JSON com "saida" e "blocos".
A lista completa de blocos e da marcação de texto está em references/blocos.md.
Só usa a biblioteca padrão do Python (Pillow, se existir, é usado para medir imagens).
"""
import datetime
import json
import os
import re
import struct
import sys
import zipfile
from xml.sax.saxutils import escape

AQUI = os.path.dirname(os.path.abspath(__file__))
ASSETS = os.path.join(AQUI, '..', 'assets')

MESES = ['janeiro', 'fevereiro', 'março', 'abril', 'maio', 'junho', 'julho',
         'agosto', 'setembro', 'outubro', 'novembro', 'dezembro']


def hoje():
    """Data de hoje no horário de Brasília (o container pode estar em UTC)."""
    try:
        from zoneinfo import ZoneInfo
        return datetime.datetime.now(ZoneInfo('America/Sao_Paulo')).date()
    except Exception:
        return (datetime.datetime.utcnow() - datetime.timedelta(hours=3)).date()


def data_extenso(d=None):
    """Data por extenso, sem zero à esquerda no dia: "3 de novembro de 2026"."""
    d = d or hoje()
    return f"{d.day} de {MESES[d.month - 1]} de {d.year}"


# --------------------------------------------------------------------------------------
# Perfil da Elias, Matias Advogados (extraído das peças do escritório)
# --------------------------------------------------------------------------------------
PERFIL = {
    'modelo': 'modelo_em.docx',
    'fonte': '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>',
    'recuo': 1418,            # 2,5 cm
    'apos': 240,
    'entrelinha': 360,
    # identidade visual do escritório: preto, cinza (#9D9D9D) e amarelo
    'acento': '000000',       # preto da marca (faixa de título das tabelas, títulos)
    'amarelo': 'FFC000',      # amarelo da marca: cabeçalho das colunas e fio do quadro
    'cinza_marca': '9D9D9D',  # cinza da marca ("ADVOGADOS")
    'cinza_claro': 'F2F2F2',  # fundo do quadro "Em síntese" e linhas alternadas
    'destaque': 'DCDCDC',     # linha destacada da tabela e trecho ==destacado==
    'cinza': '6E6E6E',        # textos secundários (legendas, referências de ementa)
    'cidade': 'São Paulo',
    'assinatura': [('Rubens Carmo Elias Filho', 'OAB/SP 138.871'),
                   ('Carla Maluf Elias', 'OAB/SP 110.819')],
    'img_borda': 'BFBFBF',
}

INTIMACAO = ('Por fim, reitera que as intimações sejam realizadas, exclusivamente, em nome dos advogados '
             '**Rubens Carmo Elias Filho (OAB/SP 138.871)** e **Carla Maluf Elias (OAB/SP 110.819)**, '
             'endereços eletrônicos: rubens.elias.filho@eliasmatias.com e carla.elias@eliasmatias.com, '
             'sob pena de nulidade.')


# Procuração ad judicia et extra, no texto do modelo do escritório.
# {o_a}: "a" ou "o", conforme o outorgante (representá-la / representá-lo).
OUTORGADOS = ('os advogados **Carla Maluf Elias, Rubens Carmo Elias Filho e Eduardo Felipe Pérez Matias**, '
              'inscritos na Ordem dos Advogados do Brasil - Secção São Paulo, sob os nºs 110.819, 138.871 e '
              '144.471, respectivamente, sócios do escritório **ELIAS MATIAS ADVOGADOS**, registrado na Ordem '
              'dos Advogados do Brasil - Secção São Paulo - sob o nº 2.961, com sede na cidade de São Paulo, '
              'Avenida Paulista, 1842, 16º andar, Cj. 165, CEP 01310-200, onde recebem intimações')
PODERES = ('aos quais confere os poderes da cláusula *ad judicia et extra*, a fim de que possam, agindo em '
           'conjunto ou separadamente, independentemente da ordem de nomeação, defender-lhe os interesses, '
           'podendo, para tanto, representá-{o_a} em qualquer juízo, instância ou tribunal, bem como quaisquer '
           'repartições públicas, praticando todas as medidas necessárias, judiciais ou extrajudiciais, '
           'produzir provas, requerer medidas preventivas, precatórias ou incidentes, firmar compromissos, '
           'passar recibos, receber e dar quitação, fazer acordos, transigir, variar, desistir, concordar, '
           'discordar, retificar atos já praticados, requerendo e assinando o que preciso for, e tudo o mais '
           'fazer para o bom e fiel cumprimento do presente mandato, inclusive substabelecer com ou sem '
           'reserva de iguais poderes')


# Estilos de nota de rodapé (o modelo do escritório não os traz): texto em Calibri 9 e número
# sobrescrito. Sem eles, o Word/LibreOffice mostram o número do rodapé no tamanho do texto.
ESTILOS_NOTA = (
    '<w:style w:type="paragraph" w:styleId="Textodenotaderodap"><w:name w:val="footnote text"/>'
    '<w:basedOn w:val="Normal"/><w:link w:val="TextodenotaderodapChar"/><w:uiPriority w:val="99"/>'
    '<w:unhideWhenUsed/><w:pPr><w:spacing w:after="0" w:line="240" w:lineRule="auto"/><w:jc w:val="both"/></w:pPr>'
    '<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:style>'
    '<w:style w:type="character" w:customStyle="1" w:styleId="TextodenotaderodapChar">'
    '<w:name w:val="Texto de nota de rodapé Char"/><w:basedOn w:val="Fontepargpadro"/>'
    '<w:link w:val="Textodenotaderodap"/><w:uiPriority w:val="99"/>'
    '<w:rPr><w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/><w:sz w:val="18"/><w:szCs w:val="18"/></w:rPr></w:style>'
    '<w:style w:type="character" w:styleId="Refdenotaderodap"><w:name w:val="footnote reference"/>'
    '<w:basedOn w:val="Fontepargpadro"/><w:uiPriority w:val="99"/><w:unhideWhenUsed/>'
    '<w:rPr><w:vertAlign w:val="superscript"/></w:rPr></w:style>')


def limpo_fim(texto):
    """Texto sem notas de rodapé e sem marcação, para olhar como o parágrafo termina."""
    t = re.sub(r'\{\{nota:.*?\}\}', '', texto, flags=re.S)
    return re.sub(r'\*\*|\+\+|==|\]\]|\[\[|\*', '', t).rstrip()


class Peca:
    def __init__(self):
        self.p = PERFIL
        self._quebra = False
        self.corpo = []
        self.notas = []          # xml de cada nota de rodapé
        self.imagens = []        # (rid, nome_no_docx, caminho_origem)
        self.pendencias = []     # textos entre [colchetes]
        self.refs = []           # referências [[fls. x]] usadas
        self.base_dir = '.'

    # ---------------------------------------------------------------- runs e marcação
    def rpr(self, b=False, i=False, u=False, cor=None, sz=None, esp=None, hl=None,
            shd=None, sup=False, caps=False):
        x = self.p['fonte']
        if b: x += '<w:b/><w:bCs/>'
        if i: x += '<w:i/><w:iCs/>'
        if caps: x += '<w:caps/>'
        if cor: x += f'<w:color w:val="{cor}"/>'
        if esp: x += f'<w:spacing w:val="{esp}"/>'
        if sz: x += f'<w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/>'
        if hl: x += f'<w:highlight w:val="{hl}"/>'
        if u: x += '<w:u w:val="single"/>'
        if shd: x += f'<w:shd w:val="clear" w:color="auto" w:fill="{shd}"/>'
        if sup: x += '<w:vertAlign w:val="superscript"/>'
        return f'<w:rPr>{x}</w:rPr>'

    def run(self, texto, **fmt):
        out = []
        partes = texto.split('\t')
        for k, parte in enumerate(partes):
            if k:
                out.append(f'<w:r>{self.rpr(**fmt)}<w:tab/></w:r>')
            if parte:
                out.append(f'<w:r>{self.rpr(**fmt)}<w:t xml:space="preserve">{escape(parte)}</w:t></w:r>')
        return ''.join(out)

    # colchetes que são marcação editorial de citação, não pendência
    EDITORIAL = re.compile(r'\[(\.\.\.|…|sic|g\.\s?n\.|grifo[s]? (?:nosso[s]?|meu[s]?|no original)|'
                           r'(?:sem )?grifo[s]? no original|destaque[s]? (?:nosso[s]?|no original)|'
                           r'grifei|grifamos|negritei|negrito nosso|sublinhei)\]', re.I)
    PENDENCIA = re.compile(r'(\[[^\[\]]+\])')

    TOKEN = re.compile(r'(\\\*|\*\*|\*|\+\+|==|\[\[|\]\]|\{\{nota:)')

    def inline(self, texto, base=None):
        """Converte a marcação leve em runs.
        **negrito**  *itálico*  ++sublinhado++  ==destaque==  [[fls. 10]]  {{nota: texto}}
        [colchetes] simples marcam pendência e saem grifados em amarelo."""
        base = dict(base or {})
        out = []
        st = {'b': False, 'i': False, 'u': False, 'hl': False, 'ref': False}
        pos = 0
        buf = ''

        def flush():
            nonlocal buf
            if not buf:
                return
            # pendências em [colchetes] (exceto [...])
            pedacos = self.PENDENCIA.split(buf)
            for ped in pedacos:
                if not ped:
                    continue
                fmt = dict(base)
                if st['b']: fmt['b'] = True
                if st['i']: fmt['i'] = True
                if st['u']: fmt['u'] = True
                if st['hl']:
                    fmt['b'] = True
                    fmt['shd'] = self.p['destaque']
                if st['ref']:
                    fmt['b'] = True
                if self.PENDENCIA.fullmatch(ped) and not self.EDITORIAL.fullmatch(ped):
                    fmt['hl'] = 'yellow'
                    self.pendencias.append(ped)
                out.append(self.run(ped, **fmt))
            buf = ''

        while pos < len(texto):
            m = self.TOKEN.search(texto, pos)
            if not m:
                buf += texto[pos:]
                break
            buf += texto[pos:m.start()]
            tok = m.group(1)
            pos = m.end()
            if tok == '\\*':
                buf += '*'
                continue
            if tok == '{{nota:':
                fim = self._fecha_nota(texto, pos)
                conteudo = texto[pos:fim].strip()
                pos = fim + 2
                flush()
                out.append(self.nota(conteudo))
                continue
            flush()
            if tok == '**': st['b'] = not st['b']
            elif tok == '*': st['i'] = not st['i']
            elif tok == '++': st['u'] = not st['u']
            elif tok == '==': st['hl'] = not st['hl']
            elif tok == '[[':
                st['ref'] = True
                fim = texto.find(']]', pos)
                if fim >= 0:
                    self.refs.append(texto[pos:fim])
            elif tok == ']]': st['ref'] = False
        flush()
        return ''.join(out)

    @staticmethod
    def _fecha_nota(texto, pos):
        prof = 0
        i = pos
        while i < len(texto) - 1:
            if texto.startswith('{{', i):
                prof += 1; i += 2; continue
            if texto.startswith('}}', i):
                if prof == 0:
                    return i
                prof -= 1; i += 2; continue
            i += 1
        sys.exit('nota de rodapé sem "}}" de fechamento')

    # ---------------------------------------------------------------- parágrafos
    def ppr(self, jc='both', recuo=None, esq=None, deslocado=None, linha=None, antes=0,
            depois=None, keep=False, borda_inf=None, tabs=None, quebra_antes=False):
        x = ''
        if keep: x += '<w:keepNext/>'
        if self._quebra:
            quebra_antes = True
            self._quebra = False
        if quebra_antes: x += '<w:pageBreakBefore/>'
        if borda_inf:
            x += f'<w:pBdr><w:bottom w:val="single" w:sz="4" w:space="4" w:color="{borda_inf}"/></w:pBdr>'
        if tabs:
            x += '<w:tabs>' + ''.join(f'<w:tab w:val="left" w:pos="{t}"/>' for t in tabs) + '</w:tabs>'
        linha = self.p['entrelinha'] if linha is None else linha
        depois = self.p['apos'] if depois is None else depois
        x += f'<w:spacing w:before="{antes}" w:after="{depois}" w:line="{linha}" w:lineRule="auto"/>'
        ind = ''
        if esq is not None: ind += f' w:left="{esq}"'
        if deslocado is not None: ind += f' w:hanging="{deslocado}"'
        elif recuo is not None: ind += f' w:firstLine="{recuo}"'
        if ind: x += f'<w:ind{ind}/>'
        x += f'<w:jc w:val="{jc}"/>'
        return f'<w:pPr>{x}</w:pPr>'

    def par(self, conteudo_xml, **kw):
        return f'<w:p>{self.ppr(**kw)}{conteudo_xml}</w:p>'

    def add(self, xml):
        # quebra pendente antes de tabela: parágrafo mínimo com pageBreakBefore,
        # para a tabela (quadro, linha do tempo, assinatura) começar na página nova
        if self._quebra and xml.startswith('<w:tbl'):
            self._quebra = False
            self.corpo.append('<w:p><w:pPr><w:pageBreakBefore/><w:spacing w:before="0" w:after="0" '
                              'w:line="20" w:lineRule="exact"/></w:pPr></w:p>')
        self.corpo.append(xml)

    def vazio(self, n=1, linha=None):
        for _ in range(n):
            self.add(self.par('', jc='left', depois=0, linha=linha))

    # ---------------------------------------------------------------- notas de rodapé
    # número da nota: estilo "Referência de nota de rodapé" (sobrescrito) + tamanho explícito,
    # para o Word e o LibreOffice mostrarem o número pequeno, no corpo e no rodapé
    REF_NOTA = ('<w:rPr><w:rStyle w:val="Refdenotaderodap"/>'
                '<w:rFonts w:ascii="Calibri" w:hAnsi="Calibri" w:cs="Calibri"/>'
                '<w:vertAlign w:val="superscript"/><w:sz w:val="{sz}"/><w:szCs w:val="{sz}"/></w:rPr>')

    def nota(self, conteudo):
        nid = len(self.notas) + 1
        paras = []
        for k, linha in enumerate(conteudo.split('\n')):
            ref = ''
            if k == 0:
                ref = (f'<w:r>{self.REF_NOTA.format(sz=18)}<w:footnoteRef/></w:r>'
                       f'<w:r>{self.rpr(sz=18)}<w:t xml:space="preserve"> </w:t></w:r>')
            antes = self.inline(linha, {'sz': 18})
            paras.append(f'<w:p><w:pPr><w:pStyle w:val="Textodenotaderodap"/>'
                         f'<w:spacing w:after="0" w:line="240" w:lineRule="auto"/>'
                         f'<w:jc w:val="both"/></w:pPr>{ref}{antes}</w:p>')
        self.notas.append(f'<w:footnote w:id="{nid}">{"".join(paras)}</w:footnote>')
        return f'<w:r>{self.REF_NOTA.format(sz=24)}<w:footnoteReference w:id="{nid}"/></w:r>'

    # ---------------------------------------------------------------- tabelas
    def _borda(self, lados):
        nomes = ['top', 'left', 'bottom', 'right']
        x = ''
        for n in nomes:
            v = lados.get(n)
            if v:
                sz, cor = v
                x += f'<w:{n} w:val="single" w:sz="{sz}" w:space="0" w:color="{cor}"/>'
            else:
                x += f'<w:{n} w:val="nil"/>'
        return f'<w:tcBorders>{x}</w:tcBorders>'

    def celula(self, conteudo_xml, larg, fill=None, bordas=None, span=1, mar=(70, 110), valign='center'):
        x = f'<w:tcW w:w="{larg}" w:type="dxa"/>'
        if span > 1: x += f'<w:gridSpan w:val="{span}"/>'
        x += self._borda(bordas or {})
        if fill: x += f'<w:shd w:val="clear" w:color="auto" w:fill="{fill}"/>'
        v, h = mar
        x += (f'<w:tcMar><w:top w:w="{v}" w:type="dxa"/><w:left w:w="{h}" w:type="dxa"/>'
              f'<w:bottom w:w="{v}" w:type="dxa"/><w:right w:w="{h}" w:type="dxa"/></w:tcMar>')
        x += f'<w:vAlign w:val="{valign}"/>'
        return f'<w:tc><w:tcPr>{x}</w:tcPr>{conteudo_xml}</w:tc>'

    def ptab(self, texto, jc='left', base=None, keep=False):
        k = '<w:keepNext/>' if keep else ''
        return (f'<w:p><w:pPr>{k}<w:spacing w:before="0" w:after="0" w:line="252" w:lineRule="auto"/>'
                f'<w:jc w:val="{jc}"/></w:pPr>{self.inline(texto, base)}</w:p>')

    def tabela_xml(self, larguras, linhas_xml):
        total = sum(larguras)
        grid = ''.join(f'<w:gridCol w:w="{w}"/>' for w in larguras)
        return (f'<w:tbl><w:tblPr><w:tblW w:w="{total}" w:type="dxa"/><w:jc w:val="center"/>'
                f'<w:tblLayout w:type="fixed"/>'
                f'<w:tblCellMar><w:left w:w="10" w:type="dxa"/><w:right w:w="10" w:type="dxa"/></w:tblCellMar>'
                f'<w:tblLook w:val="0000"/></w:tblPr><w:tblGrid>{grid}</w:tblGrid>{"".join(linhas_xml)}</w:tbl>')

    def largura_util(self):
        return 9070

    def _larguras(self, b, ncol):
        total = self.largura_util()
        if b.get('larguras'):
            pesos = b['larguras']
            soma = sum(pesos)
            ls = [round(total * w / soma) for w in pesos]
            ls[-1] += total - sum(ls)
            return ls
        if ncol == 3:
            return [1400, total - 2630, 1230]
        if ncol == 2:
            return [2300, total - 2300]
        return [total // ncol] * (ncol - 1) + [total - (total // ncol) * (ncol - 1)]

    def tabela(self, b):
        """Tabela com cabeçalho (linha do tempo, quadro-resumo, documentos)."""
        cols = b['colunas']
        n = len(cols)
        ls = self._larguras(b, n)
        destaque = set(b.get('destaque', []))   # índices (1 = primeira linha de dados)
        padrao = ['center'] + ['both'] * (n - 2) + ['center'] if n >= 3 else ['left', 'both'][:n]
        alinh = list(b.get('alinhamento') or padrao)
        alinh += padrao[len(alinh):] if len(alinh) < n else []
        rows = []
        branco = {k: (4, 'FFFFFF') for k in ('top', 'left', 'bottom', 'right')}
        if b.get('titulo'):
            rows.append('<w:tr><w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>' + self.celula(
                self.ptab(b['titulo'].upper(), base={'b': True, 'cor': 'FFFFFF', 'sz': 18}, keep=True),
                sum(ls), fill=self.p['acento'], bordas=branco, span=n, mar=(70, 150)) + '</w:tr>')
        cab = ''.join(self.celula(self.ptab(c.upper(), 'center', {'b': True, 'cor': '000000', 'sz': 18}, True),
                                  ls[k], fill=self.p['amarelo'], bordas=branco, mar=(60, 110))
                      for k, c in enumerate(cols))
        rows.append(f'<w:tr><w:trPr><w:cantSplit/><w:tblHeader/></w:trPr>{cab}</w:tr>')
        # tabela curta (até 10 linhas) fica inteira numa página; maior pode quebrar, repetindo o cabeçalho
        inteira = len(b['linhas']) <= 10
        for r, linha in enumerate(b['linhas'], 1):
            d = r in destaque
            fill = self.p['destaque'] if d else (self.p['cinza_claro'] if r % 2 else 'FFFFFF')
            base = {'sz': 18, 'b': d} if d else {'sz': 18}
            junto = inteira and r < len(b['linhas'])
            cels = ''.join(self.celula(self.ptab(str(t), alinh[k] if k < len(alinh) else 'both',
                                                 dict(base, b=True) if k == 0 else base, junto),
                                       ls[k], fill=fill, bordas=branco, mar=(90, 130))
                           for k, t in enumerate(linha))
            rows.append(f'<w:tr><w:trPr><w:cantSplit/></w:trPr>{cels}</w:tr>')
        self.add(self.tabela_xml(ls, rows))
        if b.get('legenda'):
            self.legenda(b['legenda'])
        else:
            self.vazio(1)

    def quadro(self, b):
        """Quadro-resumo "Em síntese": caixa cinza-clara com fio amarelo à esquerda, pares rótulo/texto."""
        itens = b['itens']
        titulo = b.get('titulo', 'Em síntese')
        total = self.largura_util()
        rows = []
        lado = {'left': (36, self.p['amarelo'])}
        conteudo = self.ptab(titulo, base={'b': True, 'cor': self.p['acento'], 'sz': 20}, keep=True)
        for it in itens:
            rot, txt = it[0], it[1]
            pre = f'**{rot}** ' if rot else ''
            conteudo += (f'<w:p><w:pPr><w:spacing w:before="60" w:after="0" w:line="252" w:lineRule="auto"/>'
                         f'<w:jc w:val="both"/></w:pPr>{self.inline(pre + txt, {"sz": 18, "cor": "000000"})}</w:p>')
        rows.append('<w:tr><w:trPr><w:cantSplit/></w:trPr>' +
                    self.celula(conteudo, total, fill=self.p['cinza_claro'], bordas=lado, mar=(120, 200)) + '</w:tr>')
        self.add(self.tabela_xml([total], rows))
        self.vazio(1)

    def partes(self, b):
        """Quadro sem bordas de partes (razões recursais): [["AGRAVANTE:", "FULANO"], ...]."""
        total = self.largura_util()
        ls = [2600, total - 2600]
        rows = []
        for rot, txt in b['linhas']:
            c1 = self.celula(self.ptab(rot, base={'b': True}), ls[0], mar=(30, 0), valign='top')
            c2 = self.celula(self.ptab(txt, 'both'), ls[1], mar=(30, 60), valign='top')
            rows.append(f'<w:tr>{c1}{c2}</w:tr>')
        self.add(self.tabela_xml(ls, rows))
        self.vazio(1)

    # ---------------------------------------------------------------- imagens
    @staticmethod
    def tamanho_imagem(caminho):
        try:
            from PIL import Image
            with Image.open(caminho) as im:
                return im.size
        except Exception:
            pass
        with open(caminho, 'rb') as f:
            dados = f.read()
        if dados[:8] == b'\x89PNG\r\n\x1a\n':
            return struct.unpack('>II', dados[16:24])
        i = 2
        while i < len(dados):
            if dados[i] != 0xFF:
                i += 1; continue
            marca = dados[i + 1]
            if marca in (0xC0, 0xC1, 0xC2):
                h, w = struct.unpack('>HH', dados[i + 5:i + 9])
                return w, h
            i += 2 + struct.unpack('>H', dados[i + 2:i + 4])[0]
        raise ValueError(f'não consegui medir {caminho}')

    def imagem(self, b):
        caminho = b['arquivo']
        if not os.path.isabs(caminho):
            caminho = os.path.join(self.base_dir, caminho)
        if not os.path.exists(caminho):
            sys.exit(f'imagem não encontrada: {caminho}')
        w, h = self.tamanho_imagem(caminho)
        larg_cm = float(b.get('largura_cm', 14.5))
        cx = int(larg_cm * 360000)
        cy = int(cx * h / w)
        n = len(self.imagens) + 1
        ext = os.path.splitext(caminho)[1].lower().lstrip('.') or 'png'
        if ext == 'jpeg': ext = 'jpg'
        rid = f'rIdPeca{n}'
        self.imagens.append((rid, f'peca_img{n}.{ext}', caminho))
        borda = ''
        if self.p['img_borda'] and b.get('borda', True):
            borda = f'<a:ln w="6350"><a:solidFill><a:srgbClr val="{self.p["img_borda"]}"/></a:solidFill></a:ln>'
        desc = escape(re.sub(r'[\[\]*=_{}]', '', b.get('legenda', 'Imagem')))[:250]
        draw = (f'<w:r><w:rPr><w:noProof/></w:rPr><w:drawing><wp:inline distT="0" distB="0" distL="0" distR="0">'
                f'<wp:extent cx="{cx}" cy="{cy}"/><wp:effectExtent l="0" t="0" r="0" b="0"/>'
                f'<wp:docPr id="{5000 + n}" name="Imagem {n}" descr="{desc}"/>'
                f'<wp:cNvGraphicFramePr><a:graphicFrameLocks xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main" noChangeAspect="1"/></wp:cNvGraphicFramePr>'
                f'<a:graphic xmlns:a="http://schemas.openxmlformats.org/drawingml/2006/main">'
                f'<a:graphicData uri="http://schemas.openxmlformats.org/drawingml/2006/picture">'
                f'<pic:pic xmlns:pic="http://schemas.openxmlformats.org/drawingml/2006/picture">'
                f'<pic:nvPicPr><pic:cNvPr id="{5000 + n}" name="Imagem {n}"/><pic:cNvPicPr><a:picLocks noChangeAspect="1"/></pic:cNvPicPr></pic:nvPicPr>'
                f'<pic:blipFill><a:blip r:embed="{rid}"/><a:stretch><a:fillRect/></a:stretch></pic:blipFill>'
                f'<pic:spPr><a:xfrm><a:off x="0" y="0"/><a:ext cx="{cx}" cy="{cy}"/></a:xfrm>'
                f'<a:prstGeom prst="rect"><a:avLst/></a:prstGeom>{borda}</pic:spPr></pic:pic></a:graphicData></a:graphic>'
                f'</wp:inline></w:drawing></w:r>')
        self.add(self.par(draw, jc='center', linha=240, depois=60, keep=True))
        if b.get('legenda'):
            self.legenda(b['legenda'])
        else:
            self.vazio(1)

    def legenda(self, texto):
        self.add(self.par(self.inline(texto, {'i': True, 'cor': '595959', 'sz': 18}), jc='center', linha=276))

    # ---------------------------------------------------------------- blocos de texto
    def enderecamento(self, b):
        self.add(self.par(self.inline(b['texto']), jc='both', depois=0))
        self.vazio(b.get('espaco', 3))

    def processo(self, b):
        linhas = b['linhas'] if isinstance(b.get('linhas'), list) else [b['texto']]
        for k, l in enumerate(linhas):
            self.add(self.par(self.inline(l), jc='left', depois=0))
        self.vazio(b.get('espaco', 3))

    def qualificacao(self, b):
        self.add(self.par(self.inline(b['texto']), recuo=self.p['recuo']))

    def titulo(self, b):
        self.add(self.par(self.inline(b['texto'], {'b': True}), jc='center', antes=b.get('antes', 240),
                          depois=360, keep=True, quebra_antes=b.get('nova_pagina', False)))

    def secao(self, b):
        num = b.get('num', '')
        texto = f'{num} {b["texto"]}' if num else b['texto']
        self.add(self.par(self.inline(texto, {'b': True}), jc='center', antes=240, depois=240, keep=True))

    def subsecao(self, b):
        num = b.get('num', '')
        texto = f'{num} {b["texto"]}' if num else b['texto']
        self.add(self.par(self.inline(texto, {'i': True}), jc='center', antes=120, depois=240, keep=True))

    def paragrafo(self, b):
        recuo = 0 if b.get('sem_recuo') else self.p['recuo']
        jc = b.get('alinhamento', 'both')
        # parágrafo que anuncia o que vem a seguir (termina em ":") fica na mesma página do
        # bloco seguinte (ementa, print, citação), para não ficar sozinho no pé da página
        anuncia = limpo_fim(b['texto']).endswith(':')
        self.add(self.par(self.inline(b['texto']), recuo=recuo if jc == 'both' else None, jc=jc, keep=anuncia))

    def citacao(self, b):
        """Citação recuada (artigo de lei, trecho de decisão). Uma string por parágrafo."""
        linhas = b['linhas'] if 'linhas' in b else [b['texto']]
        for k, l in enumerate(linhas):
            ult = k == len(linhas) - 1
            self.add(self.par(self.inline(l, {'i': b.get('italico', False)}), esq=2268, linha=276,
                              depois=self.p['apos'] if ult else 60, keep=not ult))
        if b.get('fonte'):
            self.add(self.par(self.inline(b['fonte'], {'sz': 20, 'cor': self.p['cinza']}), esq=2268,
                              linha=276, jc='right'))

    def ementa(self, b):
        """Ementa de julgado: tribunal em destaque, ementa em itálico, ==trecho-chave== destacado
        e a referência completa (órgão, número, relator, data) logo abaixo."""
        trib = b.get('tribunal', '')
        pre = ''
        if trib:
            pre = self.run(f'{trib}: ', b=True, i=True, cor=self.p['acento'])
        corpo = self.inline(b['texto'], {'i': True})
        self.add(self.par(pre + corpo, esq=2268, linha=276, depois=60, keep=True))
        ref = b.get('referencia', '[referência do julgado: tribunal, órgão julgador, número, relator, data]')
        self.add(self.par(self.inline(ref, {'sz': 20, 'cor': self.p['cinza']}), esq=2268, linha=276, jc='both'))

    def vocativo(self, b):
        for k, l in enumerate(b['linhas']):
            self.add(self.par(self.inline(l, {'b': True}), jc='left', depois=0, keep=True))
        self.vazio(1)

    def pedidos(self, b):
        if b.get('intro'):
            self.add(self.par(self.inline(b['intro']), recuo=self.p['recuo']))
        letras = 'abcdefghijklmnopqrstuvwxyz'
        for k, it in enumerate(b['itens']):
            letra = letras[k] if k < 26 else letras[k // 26 - 1] + letras[k % 26]
            rot = f'{letra})\t'
            self.add(self.par(self.inline(rot + it), esq=567, deslocado=567, tabs=[567], jc='both'))

    def intimacao(self, b):
        texto = b.get('texto') or INTIMACAO
        self.add(self.par(self.inline(texto), recuo=self.p['recuo']))

    def fecho(self, b):
        data = b.get('data', 'hoje')
        if data == 'hoje':
            data = data_extenso()
        cidade = b.get('cidade', self.p['cidade'])
        self.vazio(1)
        abertura = b.get('abertura', ['Termos em que,', 'pede deferimento.'])
        for l in abertura:
            self.add(self.par(self.run(l), jc='center', depois=0, keep=True))
        self.add(self.par('', jc='center', depois=0, keep=True))
        self.add(self.par(self.run(f'{cidade}, {data}.'), jc='center', depois=0, keep=True))
        if b.get('assinatura', True):
            self.add(self.par('', jc='center', depois=0, keep=True))
            self.add(self.par('', jc='center', depois=0, keep=True))
            ass = b.get('advogados') or self.p['assinatura']
            if len(ass) == 1:
                nome, oab = ass[0]
                self.add(self.par(self.run(nome), jc='center', depois=0, keep=True, linha=240))
                self.add(self.par(self.run(oab), jc='center', depois=0, linha=240))
            else:
                total = self.largura_util()
                ls = [total // len(ass)] * len(ass)
                ls[-1] += total - sum(ls)
                cels = ''.join(self.celula(self.ptab(f'{n}', 'center') + self.ptab(f'{o}', 'center'),
                                           ls[k], mar=(0, 0)) for k, (n, o) in enumerate(ass))
                self.add(self.tabela_xml(ls, [f'<w:tr><w:trPr><w:cantSplit/></w:trPr>{cels}</w:tr>']))

    def procuracao(self, b):
        """Procuração completa no padrão do modelo do escritório (corpo em 11 pt).
        Campos: outorgante (qualificação, com o nome em **negrito**), nome (para a assinatura),
        o_a ("a" ou "o"), especiais (poderes específicos, opcional), outorgados (substitui o
        trecho dos advogados, opcional), data, cidade."""
        sz = 22
        o_a = b.get('o_a', 'a')
        if o_a not in ('a', 'o'):
            sys.exit('procuracao: "o_a" deve ser "a" ou "o"')
        outorgante = b['outorgante'].rstrip().rstrip(',')
        texto = (f'{outorgante}, pelo presente Instrumento Particular de Procuração, nomeia e constitui '
                 f'seus bastantes procuradores {b.get("outorgados", OUTORGADOS)}, {PODERES.format(o_a=o_a)}')
        esp = b.get('especiais', '').strip().rstrip('.')
        texto += (f', especialmente para {esp}.' if esp else '.')
        data = b.get('data', 'hoje')
        if data == 'hoje':
            data = data_extenso()
        cidade = b.get('cidade', self.p['cidade'])
        self.vazio(1)
        self.add(self.par(self.inline('PROCURAÇÃO', {'b': True, 'sz': sz}), jc='center', antes=0, depois=480))
        self.add(self.par(self.inline(texto, {'sz': sz}), jc='both', recuo=0, depois=360))
        self.add(self.par(self.inline(f'{cidade}, {data}.', {'sz': sz}), jc='center', depois=0, keep=True))
        for _ in range(3):
            self.add(self.par('', jc='center', depois=0, keep=True))
        # linha de assinatura: fio acima do nome, com recuos laterais (~11 cm de linha)
        nome = b.get('nome')
        if not nome:
            m = re.match(r'\s*\*\*(.+?)\*\*', outorgante)
            nome = m.group(1) if m else '[NOME DO OUTORGANTE]'
        x = (f'<w:pPr><w:pBdr><w:top w:val="single" w:sz="6" w:space="6" w:color="000000"/></w:pBdr>'
             f'<w:spacing w:before="0" w:after="0" w:line="240" w:lineRule="auto"/>'
             f'<w:ind w:left="1300" w:right="1300"/><w:jc w:val="center"/></w:pPr>')
        self.add(f'<w:p>{x}{self.inline(nome, {"b": True, "sz": sz})}</w:p>')

    def quebra(self, b):
        # a quebra é aplicada ao próximo parágrafo (pageBreakBefore), sem criar página em branco
        self._quebra = True

    def espaco(self, b):
        self.vazio(b.get('n', 1))

    # ---------------------------------------------------------------- montagem
    def montar(self, plano):
        self.base_dir = plano.get('_base', '.')
        tipos = {
            'enderecamento': self.enderecamento, 'processo': self.processo,
            'qualificacao': self.qualificacao, 'titulo': self.titulo, 'secao': self.secao,
            'subsecao': self.subsecao, 'p': self.paragrafo, 'paragrafo': self.paragrafo,
            'citacao': self.citacao, 'ementa': self.ementa, 'imagem': self.imagem,
            'tabela': self.tabela, 'quadro': self.quadro, 'partes': self.partes,
            'vocativo': self.vocativo, 'pedidos': self.pedidos, 'intimacao': self.intimacao,
            'fecho': self.fecho, 'quebra': self.quebra, 'espaco': self.espaco,
            'procuracao': self.procuracao,
        }
        for k, b in enumerate(plano['blocos']):
            t = b.get('t')
            if t not in tipos:
                sys.exit(f'bloco {k}: tipo desconhecido "{t}". Tipos: {", ".join(sorted(tipos))}')
            tipos[t](b)

    def salvar(self, saida):
        if self.corpo and self.corpo[-1].startswith('<w:tbl'):
            self.corpo.append('<w:p><w:pPr><w:spacing w:after="0" w:line="120" w:lineRule="auto"/></w:pPr></w:p>')
        modelo = os.path.join(ASSETS, self.p['modelo'])
        zin = zipfile.ZipFile(modelo)
        os.makedirs(os.path.dirname(os.path.abspath(saida)), exist_ok=True)
        zout = zipfile.ZipFile(saida, 'w', zipfile.ZIP_DEFLATED)
        exts = set()
        for it in zin.infolist():
            n = it.filename
            dados = zin.read(n)
            if n == 'word/document.xml':
                s = dados.decode('utf-8')
                s = s.replace('<w:body><w:p/>', '<w:body>' + ''.join(self.corpo), 1)
                dados = s.encode('utf-8')
            elif n == 'word/_rels/document.xml.rels':
                s = dados.decode('utf-8')
                novas = ''.join(
                    f'<Relationship Id="{rid}" Type="http://schemas.openxmlformats.org/officeDocument/2006/relationships/image" Target="media/{nome}"/>'
                    for rid, nome, _ in self.imagens)
                s = s.replace('</Relationships>', novas + '</Relationships>')
                dados = s.encode('utf-8')
            elif n == 'word/styles.xml':
                s = dados.decode('utf-8')
                if 'w:styleId="Refdenotaderodap"' not in s:
                    s = s.replace('</w:styles>', ESTILOS_NOTA + '</w:styles>')
                dados = s.encode('utf-8')
            elif n == 'word/footnotes.xml' and self.notas:
                s = dados.decode('utf-8')
                s = s.replace('</w:footnotes>', ''.join(self.notas) + '</w:footnotes>')
                dados = s.encode('utf-8')
            elif n == '[Content_Types].xml':
                s = dados.decode('utf-8')
                for _, nome, _ in self.imagens:
                    exts.add(nome.rsplit('.', 1)[1])
                for e in exts:
                    if f'Extension="{e}"' not in s:
                        ct = 'image/png' if e == 'png' else 'image/jpeg'
                        s = s.replace('<Default ', f'<Default Extension="{e}" ContentType="{ct}"/><Default ', 1)
                dados = s.encode('utf-8')
            zout.writestr(it, dados)
        for _, nome, origem in self.imagens:
            with open(origem, 'rb') as f:
                zout.writestr(f'word/media/{nome}', f.read())
        zout.close()


def gerar(caminho_plano):
    with open(caminho_plano, encoding='utf-8') as f:
        plano = json.load(f)
    plano['_base'] = os.path.dirname(os.path.abspath(caminho_plano))
    peca = Peca()
    peca.montar(plano)
    saida = plano['saida']
    if not os.path.isabs(saida):
        saida = os.path.join(plano['_base'], saida)
    peca.salvar(saida)
    print(f'OK: {saida}')
    print(f'  notas de rodapé: {len(peca.notas)} | imagens: {len(peca.imagens)} | referências [[ ]]: {len(peca.refs)}')
    if peca.pendencias:
        print('  PENDÊNCIAS em [colchetes] (grifadas em amarelo):')
        vistos = []
        for p in peca.pendencias:
            if p not in vistos:
                vistos.append(p)
                print(f'    - {p}')
    else:
        print('  sem pendências em [colchetes]')
    # revisão automática (scripts/revisar.py)
    try:
        sys.path.insert(0, AQUI)
        import revisar
        revisar.imprimir(revisar.revisar(plano))
    except Exception as e:  # o revisor nunca impede a geração da peça
        print(f'  (revisor não executado: {e})')


EXEMPLO = {
    'saida': 'Exemplo EM.docx',
    'blocos': [
        {'t': 'enderecamento', 'texto': 'EXCELENTÍSSIMO(A) SENHOR(A) DOUTOR(A) JUIZ(A) DE DIREITO DA 2ª VARA CÍVEL DA COMARCA DE SÃO ROQUE – SP'},
        {'t': 'processo', 'linhas': ['Processo nº [_______-__.____.8.26.0586].']},
        {'t': 'qualificacao', 'texto': '**ASSOCIAÇÃO RESIDENCIAL ECOLÓGICA PATRIMÔNIO DO CARMO – AREPC**, já qualificada nos autos do processo em epígrafe, por seus advogados, vem, respeitosamente, à presença de Vossa Excelência, [...], pelas razões de fato e de direito a seguir expostas.'},
        {'t': 'secao', 'num': 'I.', 'texto': 'SÍNTESE DO PROCESSADO'},
        {'t': 'p', 'texto': 'Texto corrido [[fls. 708/709]].'},
        {'t': 'pedidos', 'intro': 'Diante do exposto, requer:', 'itens': ['**primeiro verbo** e complemento;', '**segundo verbo** e complemento.']},
        {'t': 'intimacao'},
        {'t': 'fecho', 'data': 'hoje'},
    ]}


EXEMPLO_PROCURACAO = {
    'saida': 'Procuracao_[Cliente].docx',
    'blocos': [
        {'t': 'procuracao',
         'outorgante': '**[NOME DO OUTORGANTE]**, [nacionalidade], [estado civil], [profissão], portador(a) da '
                       'cédula de identidade RG nº [___], inscrito(a) no CPF/MF sob nº [___], residente e '
                       'domiciliado(a) na [endereço completo]',
         'o_a': 'a',
         'especiais': '[poderes específicos, se houver — ou apague este campo]',
         'data': 'hoje'},
    ]}


def main():
    if len(sys.argv) < 2:
        print(__doc__); sys.exit(1)
    cmd = sys.argv[1]
    if cmd == 'gerar' and len(sys.argv) == 3:
        gerar(sys.argv[2])
    elif cmd == 'data':
        print(data_extenso())
    elif cmd == 'exemplo':
        ex = EXEMPLO_PROCURACAO if sys.argv[2:3] == ['procuracao'] else EXEMPLO
        print(json.dumps(ex, ensure_ascii=False, indent=2))
    else:
        print(__doc__); sys.exit(1)


if __name__ == '__main__':
    main()
