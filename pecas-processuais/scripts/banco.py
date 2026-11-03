"""Localiza as pastas de dados da skill.

Há duas fontes, lidas nesta ordem (a local prevalece):
  1. a da própria skill:  references/teses/  e  references/feriados/   (somente leitura no Cowork)
  2. a pasta local do escritório, onde a skill grava o que for conferido:
       - a variável de ambiente BANCO_EM, se existir;
       - senão, ./banco-em/ na pasta de trabalho atual (no Cowork, a pasta escolhida pelo usuário).
     Estrutura:  banco-em/teses/*.json   banco-em/feriados/*.json
"""
import os

AQUI = os.path.dirname(os.path.abspath(__file__))
SKILL_REF = os.path.normpath(os.path.join(AQUI, '..', 'references'))


def pasta_local(criar=False):
    p = os.environ.get('BANCO_EM') or os.path.join(os.getcwd(), 'banco-em')
    p = os.path.abspath(p)
    if criar:
        os.makedirs(os.path.join(p, 'teses'), exist_ok=True)
        os.makedirs(os.path.join(p, 'feriados'), exist_ok=True)
    return p


def pastas(sub):
    """Pastas existentes de `sub` ('teses' ou 'feriados'): primeiro a da skill, depois a local."""
    out = [os.path.join(SKILL_REF, sub), os.path.join(pasta_local(), sub)]
    return [p for p in dict.fromkeys(out) if os.path.isdir(p)]
