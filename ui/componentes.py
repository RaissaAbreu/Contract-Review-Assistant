"""Blocos de interface reutilizáveis (HTML renderizado via st.markdown)."""

from html import escape

import streamlit as st

from .estilo import CORES_NIVEL, CORES_SEVERIDADE


def html(conteudo: str):
    st.markdown(conteudo, unsafe_allow_html=True)


def cabecalho_app(ia_disponivel: bool):
    esquerda, direita = st.columns([3, 1], vertical_alignment="center")
    with esquerda:
        html("<div class='cra-sobrelinha'>Legal operations / Contract review</div>"
             "<h1 class='cra-titulo-app'>Análise de contratos</h1>"
             "<div class='cra-subtitulo'>Identificação de cláusulas, pontos de atenção e "
             "classificação de risco.</div>")
    with direita:
        if ia_disponivel:
            html("<div style='text-align:right'><span class='cra-pilula'>● Sistema operacional</span></div>")
        else:
            html("<div style='text-align:right'><span class='cra-pilula alerta'>● IA não configurada</span></div>")
    html("<hr class='cra-divisor'/>")


def cabecalho_secao(sobrelinha: str, titulo: str, subtitulo: str = ""):
    html(f"<div class='cra-sobrelinha'>{escape(sobrelinha)}</div>"
         f"<h2 class='cra-secao-titulo'>{escape(titulo)}</h2>"
         + (f"<div class='cra-secao-sub'>{escape(subtitulo)}</div>" if subtitulo else ""))


def etapa(numero: str, titulo: str):
    html(f"<div class='cra-etapa'><span>{escape(numero)}</span>{escape(titulo)}</div>")


def campo(rotulo: str, valor) -> str:
    """Retorna o HTML de um par rótulo/valor."""
    if valor in (None, "", []):
        return (f"<div><div class='cra-rotulo'>{escape(rotulo)}</div>"
                f"<div class='cra-valor vazio'>Não identificado</div></div>")
    return (f"<div><div class='cra-rotulo'>{escape(rotulo)}</div>"
            f"<div class='cra-valor'>{escape(str(valor))}</div></div>")


def metricas(itens: list[tuple[str, int | str]]):
    colunas = st.columns(len(itens))
    for coluna, (rotulo, numero) in zip(colunas, itens):
        with coluna:
            html(f"<div class='cra-metrica'><div class='rotulo'>{escape(rotulo)}</div>"
                 f"<div class='numero'>{escape(str(numero))}</div></div>")


def chip(texto: str, cor: str, fundo: str) -> str:
    return (f"<span class='cra-chip' style='color:{cor};background:{fundo};"
            f"border:1px solid {cor}33'>{escape(texto)}</span>")


def chip_severidade(severidade: str) -> str:
    cor, fundo = CORES_SEVERIDADE.get(severidade, ("#4A5B7A", "#EEF0F4"))
    return chip(severidade, cor, fundo)


def chip_nivel(nivel: str) -> str:
    cor, fundo = CORES_NIVEL.get(nivel, ("#4A5B7A", "#EEF0F4"))
    return chip(nivel, cor, fundo)


def item_ponto(ponto: dict, extra: str = ""):
    """Cartão de ponto de atenção / informação ausente."""
    cor, _ = CORES_SEVERIDADE.get(ponto["severidade"], ("#4A5B7A", ""))
    trecho = ""
    if ponto.get("trecho"):
        trecho = (f"<div class='cra-rotulo' style='margin-top:.3rem'>Trecho analisado</div>"
                  f"<div class='cra-trecho'>“{escape(ponto['trecho'])}”</div>")
    recomendacao = ""
    if ponto.get("recomendacao"):
        recomendacao = (f"<div class='cra-rec'><b>Recomendação</b>"
                        f"{escape(ponto['recomendacao'])}</div>")
    referencia = f"<span class='ref'>{escape(ponto.get('referencia') or '')}</span>"
    html(f"<div class='cra-item' style='border-left-color:{cor}'>"
         f"<div class='topo'>{chip_severidade(ponto['severidade'])}"
         f"<span class='titulo'>{escape(ponto['titulo'])}</span>{referencia}{extra}</div>"
         f"<div class='desc'>{escape(ponto.get('descricao', ''))}</div>"
         f"{trecho}{recomendacao}</div>")


def vazio(mensagem: str):
    html(f"<div class='cra-cartao' style='text-align:center;color:#5B6475'>{escape(mensagem)}</div>")
