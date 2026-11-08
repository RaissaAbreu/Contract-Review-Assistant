"""Identidade visual: mesma linguagem do Legal Intake (fundo creme, sidebar azul-marinho,
títulos em serifa, rótulos em caixa alta e detalhes em dourado)."""

import streamlit as st

CORES = {
    "fundo": "#F7F5F1",
    "cartao": "#FFFFFF",
    "marinho": "#14213D",
    "dourado": "#A47E3B",
    "tinta": "#1F2430",
    "suave": "#5B6475",
    "rotulo": "#4A5B7A",
    "borda": "#E4DED3",
    "escuro": "#2E2B27",
}

CORES_NIVEL = {
    "Baixo": ("#2F6B3F", "#E7F0E6"),
    "Médio": ("#8A5F0E", "#F6EEDB"),
    "Alto": ("#B4531F", "#F8E6DA"),
    "Crítico": ("#9B1C1C", "#F6DEDE"),
}

CORES_SEVERIDADE = {
    "Baixa": ("#3F5F8A", "#E5EBF4"),
    "Média": ("#8A5F0E", "#F6EEDB"),
    "Alta": ("#B4531F", "#F8E6DA"),
    "Crítica": ("#9B1C1C", "#F6DEDE"),
}

CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Cormorant+Garamond:wght@500;600;700&family=Source+Sans+3:wght@400;500;600;700&display=swap');

:root {
  --fundo: #F7F5F1; --cartao: #FFFFFF; --marinho: #14213D; --dourado: #A47E3B;
  --tinta: #1F2430; --suave: #5B6475; --rotulo: #4A5B7A; --borda: #E4DED3; --escuro: #2E2B27;
}

/* Base -------------------------------------------------------------------- */
.stApp { background: var(--fundo); }
html, body, .stApp, .stMarkdown, p, label, input, textarea, button, li, td, th {
  font-family: 'Source Sans 3', sans-serif !important;
}
.stApp, .stMarkdown p, .stMarkdown li { color: var(--tinta); }
h1, h2, h3, .cra-serifa {
  font-family: 'Cormorant Garamond', serif !important; color: var(--tinta) !important;
  font-weight: 600 !important; letter-spacing: 0 !important;
}
.block-container { padding-top: 2.4rem; max-width: 1180px; }
header[data-testid="stHeader"] { background: transparent; }

/* Sidebar ----------------------------------------------------------------- */
section[data-testid="stSidebar"] { background: var(--marinho); }
section[data-testid="stSidebar"] * { color: #F3EFE6; }
section[data-testid="stSidebar"] hr { border-color: rgba(243,239,230,.35); margin: 1.6rem 0; }
.cra-marca { text-align: center; padding: 1.2rem 0 .2rem; }
.cra-marca .icone { font-size: 2.3rem; color: var(--dourado) !important; line-height: 1; }
.cra-marca .nome { font-family: 'Cormorant Garamond', serif; font-size: 1.32rem;
  letter-spacing: .1em; white-space: nowrap; margin-top: 1rem; color: #F3EFE6 !important; }
.cra-marca .sub { font-size: .66rem; letter-spacing: .32em; color: var(--dourado) !important;
  font-weight: 600; margin-top: .6rem; }
.cra-side-rotulo { font-size: .78rem; letter-spacing: .3em; color: #C9C3B6 !important;
  margin-bottom: .4rem; }
.cra-side-texto { font-size: 1.05rem; line-height: 1.5; }
section[data-testid="stSidebar"] [role="radiogroup"] { gap: .7rem; }
section[data-testid="stSidebar"] [role="radiogroup"] label p { font-size: 1.04rem; }
/* círculo do rádio (Streamlit novo: stRadioOption / antigo: baseweb) */
section[data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div:first-child,
section[data-testid="stSidebar"] label[data-baseweb="radio"] > div:first-child {
  background: #1B2742 !important; border: 1px solid #3A4766 !important; box-shadow: none !important; }
section[data-testid="stSidebar"] label[data-testid="stRadioOption"] > div > div:first-child > div {
  background: transparent !important; }
section[data-testid="stSidebar"] label[data-testid="stRadioOption"][data-selected="true"] > div > div:first-child,
section[data-testid="stSidebar"] label[data-baseweb="radio"]:has(input:checked) > div:first-child {
  background: #D9534F !important; border-color: #D9534F !important; }
section[data-testid="stSidebar"] label[data-testid="stRadioOption"][data-selected="true"] > div > div:first-child > div {
  background: #FFFFFF !important; }
section[data-testid="stSidebar"] [data-testid="stWidgetLabel"] p { color: #C9C3B6 !important; font-size: .85rem !important; }
section[data-testid="stSidebar"] [data-testid="stTextInput"] input {
  background: #1B2742 !important; color: #F3EFE6 !important; border: 1px solid #3A4766 !important;
  border-radius: 8px !important; }
section[data-testid="stSidebar"] [data-testid="stTextInput"] div:has(> input) { background: transparent !important; border: none !important; }

/* Cabeçalho --------------------------------------------------------------- */
.cra-sobrelinha { font-size: .74rem; letter-spacing: .26em; color: var(--dourado);
  font-weight: 700; text-transform: uppercase; margin-bottom: .35rem; }
.cra-titulo-app { font-family: 'Cormorant Garamond', serif; font-size: 2.9rem;
  font-weight: 600; color: var(--tinta); line-height: 1.1; margin: 0; }
.cra-subtitulo { color: var(--suave); font-size: 1rem; margin-top: .6rem; }
.cra-pilula { display: inline-block; background: #E9F1E7; border: 1px solid #CFE0CB;
  color: #1E5130; font-weight: 700; font-size: .85rem; padding: .85rem 2.6rem;
  border-radius: 999px; white-space: nowrap; }
.cra-pilula.alerta { background: #F6EEDB; border-color: #E8D6AE; color: #6E4B0A; }
.cra-divisor { border: 0; border-top: 1px solid var(--borda); margin: 1.8rem 0 2rem; }
.cra-secao-titulo { font-family: 'Cormorant Garamond', serif; font-size: 2.1rem;
  font-weight: 600; color: var(--tinta); margin: 0; line-height: 1.15; }
.cra-secao-sub { color: var(--suave); font-size: .92rem; margin: .4rem 0 1.4rem; }

/* Cartões e painéis ------------------------------------------------------- */
.cra-cartao { background: var(--cartao); border: 1px solid var(--borda); border-radius: 16px;
  padding: 1.7rem 2rem; box-shadow: 0 10px 30px rgba(20,33,61,.04); margin-bottom: 1.2rem; }
.cra-painel { border: 1px solid var(--escuro); border-radius: 10px; padding: 1.4rem 1.2rem;
  margin-bottom: 1.2rem; }
.cra-etapa { font-weight: 700; font-size: 1.02rem; color: var(--marinho); margin-bottom: .9rem; }
.cra-etapa span { margin-right: .5rem; }
.cra-rotulo { font-size: .8rem; font-weight: 700; letter-spacing: .03em; text-transform: uppercase;
  color: var(--rotulo); margin-bottom: .25rem; }
.cra-valor { font-size: 1.05rem; color: var(--tinta); margin-bottom: 1.1rem; line-height: 1.45; }
.cra-valor.vazio { color: #9AA1AE; font-style: italic; }
.cra-grade { display: grid; grid-template-columns: 1fr 1fr; column-gap: 2.4rem; }
.cra-grade-3 { display: grid; grid-template-columns: repeat(3, 1fr); gap: 1rem; }
@media (max-width: 900px) { .cra-grade, .cra-grade-3 { grid-template-columns: 1fr; } }
.cra-sub-titulo { font-family: 'Cormorant Garamond', serif; font-size: 1.6rem; font-weight: 600;
  color: var(--tinta); margin: .2rem 0 1rem; }
.cra-linha { border: 0; border-top: 1px solid var(--borda); margin: 1.4rem 0; }

/* Métricas ---------------------------------------------------------------- */
.cra-metrica .rotulo { font-weight: 600; font-size: 1.02rem; color: var(--tinta); }
.cra-metrica .numero { font-weight: 700; font-size: 2.8rem; color: var(--marinho); line-height: 1.15; }

/* Resultado final --------------------------------------------------------- */
.cra-resultado { display: flex; gap: 2rem; align-items: stretch; flex-wrap: wrap; }
.cra-nivel { border-radius: 14px; padding: 1.3rem 1.6rem; min-width: 220px; }
.cra-nivel .rotulo { font-size: .76rem; letter-spacing: .2em; font-weight: 700; text-transform: uppercase; }
.cra-nivel .valor { font-family: 'Cormorant Garamond', serif; font-size: 3rem; font-weight: 700; line-height: 1.05; }
.cra-nivel .pontos { font-size: .9rem; font-weight: 600; }
.cra-chip { display: inline-block; font-size: .74rem; font-weight: 700; padding: .2rem .7rem;
  border-radius: 999px; letter-spacing: .03em; }

/* Itens (pontos de atenção) ----------------------------------------------- */
.cra-item { background: var(--cartao); border: 1px solid var(--borda); border-left: 5px solid;
  border-radius: 10px; padding: 1.1rem 1.3rem; margin-bottom: .9rem; }
.cra-item .topo { display: flex; gap: .7rem; align-items: center; flex-wrap: wrap; margin-bottom: .35rem; }
.cra-item .titulo { font-weight: 700; font-size: 1.05rem; color: var(--tinta); }
.cra-item .ref { color: var(--suave); font-size: .85rem; }
.cra-item .desc { color: var(--tinta); font-size: .97rem; margin-bottom: .55rem; }
.cra-trecho { background: #FBF9F5; border-left: 3px solid var(--dourado); padding: .65rem .9rem;
  font-size: .93rem; color: #3A3F4B; font-style: italic; border-radius: 0 6px 6px 0; margin: .4rem 0 .6rem; }
.cra-rec { font-size: .92rem; color: var(--tinta); }
.cra-rec b { color: var(--rotulo); font-size: .76rem; letter-spacing: .04em; text-transform: uppercase; margin-right: .3rem; }

/* Cláusulas --------------------------------------------------------------- */
.cra-clausula { background: var(--cartao); border: 1px solid var(--borda); border-radius: 12px;
  padding: 1.1rem 1.2rem; height: 100%; }
.cra-clausula .nome { font-family: 'Cormorant Garamond', serif; font-size: 1.45rem; font-weight: 600; }
.cra-clausula .ref { color: var(--suave); font-size: .83rem; margin: .35rem 0 .5rem; }
.cra-clausula .trecho { font-size: .88rem; color: #3A3F4B; line-height: 1.45; }

/* Contêineres com key "cartao_*": cartão branco como na tela de abertura */
[class*="st-key-cartao"] { background: var(--cartao) !important; border: 1px solid var(--borda) !important;
  border-radius: 16px !important; padding: 1.8rem 2.1rem !important;
  box-shadow: 0 10px 30px rgba(20,33,61,.04); }

/* Widgets ----------------------------------------------------------------- */
.stMain [data-testid="stWidgetLabel"] p { color: var(--tinta) !important; font-size: 1rem !important; }
/* Selectbox escuro (Streamlit novo: role=group / antigo: baseweb) */
[data-testid="stSelectbox"] [role="group"],
[data-testid="stSelectbox"] div[data-baseweb="select"] > div {
  background: var(--escuro) !important; border-radius: 8px !important; border: none !important;
  min-height: 50px; }
[data-testid="stSelectbox"] input, [data-testid="stSelectbox"] [role="group"] *,
[data-testid="stSelectbox"] div[data-baseweb="select"] * { color: #FFFFFF !important; font-size: 1.02rem; }
[data-testid="stSelectbox"] svg { fill: #FFFFFF !important; color: #FFFFFF !important; }
/* Campos de texto com borda escura */
.stMain [data-testid="stTextInput"] input, .stMain [data-testid="stTextArea"] textarea {
  background: #FFFFFF !important; color: var(--tinta) !important; }
.stMain [data-testid="stTextInput"] div:has(> input), .stMain [data-testid="stTextArea"] div:has(> textarea) {
  border: 1.5px solid var(--escuro) !important; border-radius: 8px !important; background: #FFFFFF !important; }
.stMain [data-testid="stTextArea"] textarea:disabled { color: #3A3F4B !important; -webkit-text-fill-color: #3A3F4B; }
[data-testid="stFileUploaderDropzone"] { background: #FBF9F5 !important; border: 1.5px dashed #CBBF9F !important;
  border-radius: 12px !important; }
.stButton > button, .stDownloadButton > button, .stFormSubmitButton > button {
  border-radius: 8px !important; font-weight: 600; padding: .6rem 1.4rem; min-height: 46px;
  border: 1.5px solid var(--marinho) !important; }
.stButton > button[kind="primary"], .stFormSubmitButton > button[kind="primary"],
.stButton > button[data-testid="stBaseButton-primary"], .stFormSubmitButton > button[data-testid="stBaseButton-primaryFormSubmit"] {
  background: var(--marinho) !important; color: #FFFFFF !important; }
.stButton > button[kind="secondary"], .stDownloadButton > button,
.stButton > button[data-testid="stBaseButton-secondary"] { background: transparent !important; color: var(--marinho) !important; }
.stButton > button p, .stDownloadButton > button p, .stFormSubmitButton > button p { font-weight: 600; }
[data-testid="stTabs"] [role="tablist"] { gap: 1.8rem; border-bottom: 1px solid var(--borda); }
[data-testid="stTabs"] [role="tab"] { padding: .7rem 0; }
[data-testid="stTabs"] [role="tab"] p { font-size: 1rem; font-weight: 600; color: var(--suave); }
[data-testid="stTabs"] [role="tab"][aria-selected="true"] p { color: var(--marinho); }
[data-testid="stExpander"] details { border-color: var(--borda) !important; border-radius: 10px !important; background: #FFFFFF; }
[data-testid="stDataFrame"] { border: 1px solid var(--borda); border-radius: 10px; }
[data-testid="stForm"] { background: var(--cartao); border: 1px solid var(--borda) !important; border-radius: 16px; padding: 1.6rem 1.8rem; }
</style>
"""


def aplicar_estilo():
    st.markdown(CSS, unsafe_allow_html=True)
