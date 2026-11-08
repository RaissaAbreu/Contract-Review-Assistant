"""
Contract Review Assistant — análise automatizada de contratos.

Execute com:  streamlit run app.py
"""

import hashlib
from html import escape
from pathlib import Path

import pandas as pd
import streamlit as st

from core import banco, llm, regras, relatorio
from core.analisador import analisar_contrato
from core.extracao import FORMATOS_ACEITOS, ErroExtracao, extrair_texto
from ui.componentes import (cabecalho_app, cabecalho_secao, campo, chip, chip_nivel,
                            chip_severidade, etapa, html, item_ponto, metricas, vazio)
from ui.estilo import CORES_NIVEL, aplicar_estilo

PASTA_DEMO = Path(__file__).resolve().parent / "demo"

PAGINA_NOVA = "Nova análise"
PAGINA_RESULTADO = "Resultado da análise"
PAGINA_REVISAO = "Revisão jurídica"
PAGINA_HISTORICO = "Histórico"
PAGINAS = [PAGINA_NOVA, PAGINA_RESULTADO, PAGINA_REVISAO, PAGINA_HISTORICO]

st.set_page_config(page_title="Contract Review Assistant", page_icon="⚖️", layout="wide")
banco.inicializar()
aplicar_estilo()


# ---------------------------------------------------------------------------
# Navegação
# ---------------------------------------------------------------------------
def ir_para(pagina: str, analise_id: int | None = None):
    """Callback de botões: troca de seção (e opcionalmente seleciona uma análise)."""
    st.session_state["pagina"] = pagina
    if analise_id is not None:
        st.session_state["analise_id"] = analise_id


# Mudança de página pedida no ciclo anterior (fora de callback)
if "pagina_pendente" in st.session_state:
    st.session_state["pagina"] = st.session_state.pop("pagina_pendente")
st.session_state.setdefault("pagina", PAGINA_NOVA)
st.session_state.setdefault("modelo_ia", llm.MODELO_PADRAO)


# ---------------------------------------------------------------------------
# Sidebar
# ---------------------------------------------------------------------------
with st.sidebar:
    html("<div class='cra-marca'><div class='icone'>⚖</div>"
         "<div class='nome'>CONTRACT REVIEW</div>"
         "<div class='sub'>EXECUTIVE PLATFORM</div></div><hr/>")
    html("<div class='cra-side-rotulo'>WORKSPACE</div>")
    st.radio("Navegação", PAGINAS, key="pagina", label_visibility="collapsed")
    html("<hr/><div class='cra-side-rotulo'>INTELIGÊNCIA ARTIFICIAL</div>")
    st.text_input("Modelo OpenAI", key="modelo_ia",
                  help="Modelo usado no botão 'Analisar com IA'. O padrão vem de OPENAI_MODEL no .env.")
    if llm.chave_configurada():
        html("<div style='font-size:.85rem'>● Chave da API configurada</div>")
    else:
        html("<div style='font-size:.85rem;color:#E8C77E !important'>● OPENAI_API_KEY ausente no .env</div>")
    html("<hr/><div class='cra-side-rotulo'>LEGAL OPERATIONS</div>"
         "<div class='cra-side-texto'>Revisão inteligente de contratos.</div>")

cabecalho_app(llm.chave_configurada())


# ---------------------------------------------------------------------------
# Utilitários
# ---------------------------------------------------------------------------
def rotulo_analise(a: dict) -> str:
    return f"#{a['id']} — {a['nome_arquivo']} · {a['nivel_risco']}"


def selecionar_analise(analises: list[dict], rotulo: str, chave: str) -> dict | None:
    """Selectbox de análises que respeita a análise escolhida em outra seção."""
    if not analises:
        return None
    ids = [a["id"] for a in analises]
    atual = st.session_state.get("analise_id")
    # Sincroniza o seletor com a análise escolhida em outra seção
    if atual in ids:
        st.session_state[chave] = atual
    elif st.session_state.get(chave) not in ids:
        st.session_state[chave] = ids[0]
    escolhido = st.selectbox(rotulo, ids, key=chave,
                             format_func=lambda i: rotulo_analise(next(a for a in analises if a["id"] == i)))
    st.session_state["analise_id"] = escolhido
    return banco.obter_analise(escolhido)


@st.cache_data(show_spinner=False)
def extrair_cache(nome: str, conteudo: bytes, _hash: str):
    return extrair_texto(nome, conteudo)


# ---------------------------------------------------------------------------
# 01 — Nova análise
# ---------------------------------------------------------------------------
def pagina_nova_analise():
    cabecalho_secao("Contract intake / 01", "Envio de contrato",
                    "Envie um contrato em PDF, TXT ou DOCX para análise automática.")

    with st.container(border=True, key="cartao_envio"):
        etapa("01", "Origem do contrato")
        origem = st.radio("Origem", ["Enviar arquivo", "Usar contrato de demonstração"],
                          horizontal=True, label_visibility="collapsed")
        nome, conteudo = None, None
        if origem == "Enviar arquivo":
            arquivo = st.file_uploader("Arquivo do contrato", type=FORMATOS_ACEITOS)
            if arquivo:
                nome, conteudo = arquivo.name, arquivo.getvalue()
        else:
            demos = sorted(p for p in PASTA_DEMO.iterdir() if p.suffix[1:] in FORMATOS_ACEITOS)
            if not demos:
                st.warning("Nenhum contrato de demonstração encontrado na pasta demo/.")
            else:
                escolhido = st.selectbox("Contrato fictício", demos, format_func=lambda p: p.name)
                nome, conteudo = escolhido.name, escolhido.read_bytes()

        if not conteudo:
            return

        try:
            documento = extrair_cache(nome, conteudo, hashlib.sha256(conteudo).hexdigest())
        except ErroExtracao as erro:
            st.error(str(erro))
            return

        html("<hr class='cra-linha'/>")
        etapa("02", "Extração de conteúdo")
        html("<div class='cra-grade-3' style='grid-template-columns:repeat(4,1fr)'>"
             + campo("Arquivo", documento.nome_arquivo)
             + campo("Formato", documento.formato.upper())
             + campo("Páginas", documento.paginas or "—")
             + campo("Palavras", f"{len(documento.texto.split()):,}".replace(",", "."))
             + "</div>")
        if len(documento.texto) < regras.MIN_CARACTERES_TEXTO:
            st.warning("Pouco texto foi extraído. Se for um PDF escaneado, a análise automática "
                       "será limitada e a revisão humana será obrigatória.")
        with st.expander("Pré-visualizar texto extraído"):
            st.text_area("Texto extraído", documento.texto, height=320, disabled=True,
                         label_visibility="collapsed")

        html("<hr class='cra-linha'/>")
        etapa("03", "Análise")
        if st.button("Analisar contrato", type="primary"):
            with st.spinner("Analisando cláusulas..."):
                resultado = analisar_contrato(documento.texto, documento.paginas)
                analise_id = banco.salvar_analise(documento, resultado)
            st.session_state["analise_id"] = analise_id
            st.session_state["pagina_pendente"] = PAGINA_RESULTADO
            st.rerun()


# ---------------------------------------------------------------------------
# 02 — Resultado da análise
# ---------------------------------------------------------------------------
def bloco_resultado_final(analise: dict):
    c = analise["resultado"]["classificacao"]
    cor, fundo = CORES_NIVEL[c["nivel"]]
    if c["revisao_humana"]:
        revisao = chip("Revisão humana necessária", "#9B1C1C", "#F6DEDE")
    else:
        revisao = chip("Revisão humana não obrigatória", "#2F6B3F", "#E7F0E6")
    motivos = "".join(f"<li>{escape(m)}</li>" for m in c["motivos"])
    contagem = " ".join(f"{chip_severidade(s)} <b>{n}</b>&nbsp;&nbsp;" for s, n in c["contagem"].items())
    html(f"""<div class='cra-cartao'><div class='cra-resultado'>
<div class='cra-nivel' style='background:{fundo};color:{cor}'>
<div class='rotulo'>Classificação de risco</div>
<div class='valor'>{escape(c['nivel'])}</div>
<div class='pontos'>Pontuação {c['pontuacao']}</div></div>
<div style='flex:1;min-width:280px'>
<div class='cra-rotulo'>Resultado final</div>
<div style='margin:.3rem 0 .8rem'>{revisao} {chip(analise['status_revisao'], '#14213D', '#ECEFF5')}</div>
<div class='cra-rotulo'>Critérios aplicados</div>
<ul style='margin:.2rem 0 .8rem 1.1rem;padding:0'>{motivos}</ul>
<div class='cra-rotulo'>Itens por severidade</div><div>{contagem}</div>
</div></div></div>""")


def aba_resumo(analise: dict):
    r = analise["resultado"]
    resumo = r["resumo"]
    est = r["estatisticas"]
    identificadas = sum(1 for c in r["clausulas"] if c["identificada"])
    html("<div class='cra-painel'>"
         "<div class='cra-sub-titulo'>Dados gerais</div><div class='cra-grade'>"
         + campo("Contratante", resumo.get("contratante"))
         + campo("Contratada", resumo.get("contratada"))
         + campo("Valor", resumo.get("valor"))
         + campo("Forma de pagamento", resumo.get("pagamento"))
         + campo("Vigência", resumo.get("vigencia"))
         + campo("Foro", resumo.get("foro"))
         + campo("Data", resumo.get("data_assinatura"))
         + campo("Cláusulas de interesse", f"{identificadas} de {len(r['clausulas'])} identificadas")
         + "</div><hr class='cra-linha'/>"
         "<div class='cra-sub-titulo'>Objeto</div>"
         + (f"<div class='cra-valor'>{escape(resumo['objeto'])}</div>" if resumo.get("objeto")
            else "<div class='cra-valor vazio'>Não identificado</div>")
         + "<hr class='cra-linha'/><div class='cra-sub-titulo'>Estrutura do contrato</div>"
         + ("<ol style='margin-left:1.1rem;padding:0'>"
            + "".join(f"<li>{escape(t)}</li>" for t in resumo.get("estrutura", [])) + "</ol>"
            if resumo.get("estrutura") else "<div class='cra-valor vazio'>Estrutura não identificada</div>")
         + "<hr class='cra-linha'/><div class='cra-grade-3' style='grid-template-columns:repeat(4,1fr)'>"
         + campo("Arquivo", analise["nome_arquivo"])
         + campo("Páginas", est["paginas"] or "—")
         + campo("Palavras", est["palavras"])
         + campo("Blocos identificados", est["blocos"])
         + "</div></div>")


def aba_clausulas(analise: dict):
    clausulas = analise["resultado"]["clausulas"]
    for i in range(0, len(clausulas), 3):
        colunas = st.columns(3)
        for coluna, cl in zip(colunas, clausulas[i:i + 3]):
            with coluna:
                if cl["identificada"]:
                    status = chip("Identificada", "#2F6B3F", "#E7F0E6")
                    if cl["confianca"] == "Média":
                        status += " " + chip("Confiança média", "#8A5F0E", "#F6EEDB")
                    corpo = (f"<div class='ref'>{escape(cl['referencia'])}</div>"
                             f"<div class='trecho'>{escape(cl['trecho'])}</div>")
                else:
                    status = chip("Não encontrada", "#9B1C1C", "#F6DEDE")
                    corpo = ("<div class='ref'>Nenhum trecho correspondente.</div>"
                             "<div class='trecho'>Veja a aba Informações ausentes.</div>")
                html(f"<div class='cra-clausula'><div class='nome'>{escape(cl['nome'])}</div>"
                     f"<div style='margin-top:.3rem'>{status}</div>{corpo}</div>")
        st.write("")


def lista_pontos(pontos: list[dict], chave: str, mensagem_vazio: str):
    if not pontos:
        vazio(mensagem_vazio)
        return
    presentes = [s for s in regras.ORDEM_SEVERIDADE if any(p["severidade"] == s for p in pontos)]
    filtro = st.multiselect("Filtrar por severidade", presentes, default=presentes, key=chave)
    for ponto in pontos:
        if ponto["severidade"] in filtro:
            categoria = regras.NOMES_CATEGORIAS.get(ponto["categoria"], ponto["categoria"])
            item_ponto(ponto, f"<span class='ref'>· {escape(categoria)}</span>")


def aba_ia(analise: dict):
    parecer = analise.get("parecer_ia")
    disponivel = llm.chave_configurada()
    html("<div class='cra-secao-sub' style='margin-top:0'>Parecer complementar gerado por modelo "
         "de linguagem. Ele não altera a classificação calculada pelas regras e deve ser "
         "conferido pelo revisor.</div>")

    rotulo = "Gerar novamente com IA" if parecer else "Analisar com IA"
    if st.button(rotulo, type="primary" if not parecer else "secondary", disabled=not disponivel,
                 key=f"ia_{analise['id']}"):
        modelo = st.session_state["modelo_ia"]
        with st.spinner(f"Consultando {modelo}..."):
            try:
                novo = llm.analisar_com_ia(analise["texto"], analise["resultado"], modelo)
                banco.salvar_parecer_ia(analise["id"], novo, modelo)
                st.rerun()
            except llm.ErroIA as erro:
                st.error(str(erro))
    if not disponivel:
        st.info("Configure OPENAI_API_KEY no arquivo .env para habilitar a análise com IA.")

    if not parecer:
        return

    nivel_ia = parecer.get("nivel_risco_sugerido") or "—"
    nivel_regras = analise["resultado"]["classificacao"]["nivel"]
    concorda = nivel_ia == nivel_regras
    comparacao = chip("Mesmo nível das regras" if concorda else "Diverge das regras",
                      "#2F6B3F" if concorda else "#8A5F0E", "#E7F0E6" if concorda else "#F6EEDB")
    html("<div class='cra-painel'><div class='cra-sub-titulo'>Resumo executivo</div>"
         f"<div class='cra-valor'>{escape(parecer.get('resumo_executivo', ''))}</div>"
         "<div class='cra-grade'>"
         + campo("Modelo utilizado", analise.get("modelo_ia"))
         + f"<div><div class='cra-rotulo'>Nível sugerido pela IA</div><div class='cra-valor'>"
           f"{chip_nivel(nivel_ia)} {comparacao}</div></div>"
         + "</div>"
         + campo("Justificativa", parecer.get("justificativa_nivel"))
         + ("<div class='cra-valor' style='color:#8A5F0E'>O contrato foi truncado antes do envio "
            "ao modelo por excesso de tamanho.</div>" if parecer.get("texto_truncado") else "")
         + "</div>")

    html("<div class='cra-sub-titulo'>Pontos adicionais</div>")
    adicionais = parecer.get("pontos_adicionais", [])
    if not adicionais:
        vazio("A IA não identificou pontos além dos já apontados pelas regras.")
    for p in adicionais:
        severidade = p.get("severidade") if p.get("severidade") in regras.SEVERIDADES else "Média"
        verificado = (chip("Trecho conferido no contrato", "#2F6B3F", "#E7F0E6")
                      if p.get("trecho_verificado")
                      else chip("Trecho não localizado no contrato", "#9B1C1C", "#F6DEDE"))
        item_ponto({"severidade": severidade, "titulo": str(p.get("titulo", "")),
                    "referencia": str(p.get("categoria", "")), "descricao": str(p.get("comentario", "")),
                    "trecho": str(p.get("trecho", "")), "recomendacao": ""}, verificado)

    if parecer.get("divergencias"):
        html("<div class='cra-sub-titulo'>Divergências em relação às regras</div><ul>"
             + "".join(f"<li>{escape(str(d))}</li>" for d in parecer["divergencias"]) + "</ul>")
    if parecer.get("recomendacoes"):
        html("<div class='cra-sub-titulo'>Recomendações</div><ul>"
             + "".join(f"<li>{escape(str(d))}</li>" for d in parecer["recomendacoes"]) + "</ul>")


def pagina_resultado():
    cabecalho_secao("Contract analysis / 02", "Resultado da análise",
                    "Cláusulas identificadas, pontos de atenção e classificação de risco.")
    analises = banco.listar_analises()
    if not analises:
        vazio("Nenhuma análise realizada ainda. Envie um contrato em 'Nova análise'.")
        return
    analise = selecionar_analise(analises, "Selecione uma análise para consultar", "sel_resultado")
    st.write("")

    bloco_resultado_final(analise)

    col_pdf, col_docx, col_rev, _ = st.columns([1, 1, 1.3, 1.7])
    nome_base = f"analise_{analise['id']}_{Path(analise['nome_arquivo']).stem}"
    col_pdf.download_button("Baixar relatório PDF", relatorio.gerar_pdf(analise),
                            f"{nome_base}.pdf", "application/pdf", width="stretch")
    col_docx.download_button(
        "Baixar relatório DOCX", relatorio.gerar_docx(analise), f"{nome_base}.docx",
        "application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        width="stretch")
    if analise["status_revisao"] == banco.STATUS_AGUARDANDO:
        col_rev.button("Registrar revisão jurídica", type="primary", width="stretch",
                       on_click=ir_para, args=(PAGINA_REVISAO, analise["id"]))
    st.write("")

    r = analise["resultado"]
    abas = st.tabs([
        "Resumo esquematizado",
        f"Cláusulas ({sum(c['identificada'] for c in r['clausulas'])}/{len(r['clausulas'])})",
        f"Pontos de atenção ({len(r['pontos_atencao'])})",
        f"Informações ausentes ({len(r['informacoes_ausentes'])})",
        "Parecer da IA" + (" ✓" if analise.get("parecer_ia") else ""),
        "Texto extraído",
    ])
    with abas[0]:
        aba_resumo(analise)
    with abas[1]:
        aba_clausulas(analise)
    with abas[2]:
        lista_pontos(r["pontos_atencao"], f"f_pa_{analise['id']}",
                     "Nenhum ponto de atenção identificado pelas regras.")
    with abas[3]:
        lista_pontos(r["informacoes_ausentes"], f"f_au_{analise['id']}",
                     "Nenhuma informação obrigatória ausente.")
    with abas[4]:
        aba_ia(analise)
    with abas[5]:
        st.text_area("Texto", analise["texto"], height=480, disabled=True,
                     label_visibility="collapsed", key=f"txt_{analise['id']}")


# ---------------------------------------------------------------------------
# 03 — Revisão jurídica
# ---------------------------------------------------------------------------
def pagina_revisao():
    cabecalho_secao("Legal control / 03", "Central de revisão jurídica",
                    "Confira a análise automática e registre a decisão do advogado revisor.")
    contagem = banco.contar_por_status()
    metricas([
        ("Aguardando revisão", contagem.get(banco.STATUS_AGUARDANDO, 0)),
        ("Aprovados", contagem.get("Aprovado", 0)),
        ("Aprovados com ressalvas", contagem.get("Aprovado com ressalvas", 0)),
        ("Reprovados", contagem.get("Reprovado", 0)),
    ])
    html("<hr class='cra-divisor'/>")

    incluir_todas = st.checkbox("Mostrar também análises sem revisão obrigatória ou já revisadas")
    analises = banco.listar_analises() if incluir_todas else banco.listar_analises(banco.STATUS_AGUARDANDO)
    if not analises:
        vazio("Nenhuma análise aguardando revisão.")
        return
    analise = selecionar_analise(analises, "Selecione uma análise", "sel_revisao")
    r = analise["resultado"]
    c = r["classificacao"]

    html("<h3 class='cra-sub-titulo' style='font-size:2rem;margin-top:1.2rem'>Dados da análise</h3>")
    html("<div class='cra-painel'><div class='cra-grade'>"
         + campo("Arquivo", analise["nome_arquivo"])
         + campo("Analisado em", analise["criado_em"])
         + f"<div><div class='cra-rotulo'>Classificação de risco</div><div class='cra-valor'>"
           f"{chip_nivel(c['nivel'])} &nbsp;pontuação {c['pontuacao']}</div></div>"
         + campo("Status atual", analise["status_revisao"])
         + campo("Contratante", r["resumo"].get("contratante"))
         + campo("Contratada", r["resumo"].get("contratada"))
         + "</div></div>")

    principais = (r["pontos_atencao"] + r["informacoes_ausentes"])
    ordem = {s: i for i, s in enumerate(regras.ORDEM_SEVERIDADE)}
    principais = sorted(principais, key=lambda p: ordem[p["severidade"]])[:5]
    if principais:
        html("<div class='cra-sub-titulo'>Principais pontos</div>")
        for p in principais:
            item_ponto(p)
    st.button("Ver análise completa", on_click=ir_para, args=(PAGINA_RESULTADO, analise["id"]))

    if analise.get("revisor"):
        html("<div class='cra-painel' style='margin-top:1rem'><div class='cra-sub-titulo'>Revisão registrada</div>"
             "<div class='cra-grade'>"
             + campo("Decisão", analise["status_revisao"])
             + campo("Data da revisão", analise["data_revisao"])
             + campo("Advogado revisor", analise["revisor"])
             + "</div>"
             + campo("Observações da revisão", analise["observacoes"] or "Nenhuma observação registrada.")
             + "</div>")

    html("<h3 class='cra-sub-titulo' style='font-size:2rem;margin-top:1.4rem'>Registrar revisão</h3>")
    with st.form(f"form_revisao_{analise['id']}", clear_on_submit=False):
        revisor = st.text_input("Advogado revisor *", value=analise.get("revisor") or "",
                                placeholder="Nome e OAB")
        decisao = st.radio("Decisão *", banco.DECISOES, horizontal=True,
                           index=banco.DECISOES.index(analise["status_revisao"])
                           if analise["status_revisao"] in banco.DECISOES else 0)
        observacoes = st.text_area("Observações", value=analise.get("observacoes") or "",
                                   placeholder="Ajustes solicitados, ressalvas, próximos passos...")
        enviado = st.form_submit_button("Registrar revisão", type="primary")
    if enviado:
        if not revisor.strip():
            st.error("Informe o nome do advogado revisor.")
        else:
            banco.registrar_revisao(analise["id"], revisor, decisao, observacoes)
            st.success(f"Revisão da análise #{analise['id']} registrada como '{decisao}'.")
            st.rerun()


# ---------------------------------------------------------------------------
# 04 — Histórico
# ---------------------------------------------------------------------------
def pagina_historico():
    cabecalho_secao("History / 04", "Histórico de análises",
                    "Consulte as análises realizadas e o andamento das revisões.")
    analises = banco.listar_analises()
    if not analises:
        vazio("Nenhuma análise realizada ainda.")
        return

    niveis = ["Baixo", "Médio", "Alto", "Crítico"]
    contagem = {n: sum(a["nivel_risco"] == n for a in analises) for n in niveis}
    metricas([("Total de análises", len(analises))] + [(f"Risco {n.lower()}", contagem[n]) for n in niveis])
    html("<hr class='cra-divisor'/>")

    col_busca, col_nivel, col_status = st.columns([2, 1.5, 1.5])
    busca = col_busca.text_input("Buscar por arquivo", placeholder="Nome do arquivo")
    filtro_nivel = col_nivel.multiselect("Nível de risco", niveis, default=niveis)
    status_existentes = sorted({a["status_revisao"] for a in analises})
    filtro_status = col_status.multiselect("Status da revisão", status_existentes, default=status_existentes)

    filtradas = [a for a in analises
                 if a["nivel_risco"] in filtro_nivel and a["status_revisao"] in filtro_status
                 and busca.lower() in a["nome_arquivo"].lower()]
    tabela = pd.DataFrame([{
        "ID": a["id"], "Data": a["criado_em"], "Arquivo": a["nome_arquivo"],
        "Formato": a["formato"].upper(), "Risco": a["nivel_risco"], "Pontuação": a["pontuacao"],
        "Revisão humana": "Necessária" if a["revisao_necessaria"] else "Não obrigatória",
        "Status": a["status_revisao"], "Revisor": a["revisor"] or "—",
        "IA": "Sim" if a["tem_parecer_ia"] else "Não",
    } for a in filtradas])
    if tabela.empty:
        vazio("Nenhuma análise corresponde aos filtros.")
        return
    st.dataframe(tabela, hide_index=True, width="stretch")

    html("<h3 class='cra-sub-titulo' style='font-size:2rem;margin-top:1.4rem'>Consulta detalhada</h3>")
    analise = selecionar_analise(filtradas, "Selecione uma análise para consultar", "sel_historico")
    c = analise["resultado"]["classificacao"]
    html("<div class='cra-painel'><div class='cra-grade'>"
         + campo("Arquivo", analise["nome_arquivo"])
         + campo("Analisado em", analise["criado_em"])
         + f"<div><div class='cra-rotulo'>Classificação de risco</div><div class='cra-valor'>"
           f"{chip_nivel(c['nivel'])} &nbsp;pontuação {c['pontuacao']}</div></div>"
         + campo("Revisão humana", "Necessária" if c["revisao_humana"] else "Não obrigatória")
         + campo("Status da revisão", analise["status_revisao"])
         + campo("Advogado revisor", analise["revisor"] or "Não informado")
         + "</div>"
         + campo("Observações da revisão", analise["observacoes"] or "Nenhuma observação registrada.")
         + "</div>")
    col_abrir, col_excluir, _ = st.columns([1, 1, 2])
    col_abrir.button("Abrir resultado completo", type="primary", width="stretch",
                     on_click=ir_para, args=(PAGINA_RESULTADO, analise["id"]))
    with col_excluir.popover("Excluir análise", width="stretch"):
        st.write(f"Excluir definitivamente a análise #{analise['id']}?")
        if st.button("Confirmar exclusão", key=f"excluir_{analise['id']}"):
            banco.excluir_analise(analise["id"])
            st.session_state.pop("analise_id", None)
            st.rerun()


# ---------------------------------------------------------------------------
# Roteamento
# ---------------------------------------------------------------------------
{
    PAGINA_NOVA: pagina_nova_analise,
    PAGINA_RESULTADO: pagina_resultado,
    PAGINA_REVISAO: pagina_revisao,
    PAGINA_HISTORICO: pagina_historico,
}[st.session_state["pagina"]]()
