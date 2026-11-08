"""Geração do relatório da análise em PDF (PyMuPDF) e DOCX (python-docx)."""

import io
from html import escape

import pymupdf
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt, RGBColor

AVISO = ("Relatório gerado automaticamente por regras de classificação"
         " e, quando indicado, por modelo de linguagem. Não substitui a análise de um advogado.")

CORES_NIVEL = {"Baixo": "#2F6B3F", "Médio": "#9A6B12", "Alto": "#B4531F", "Crítico": "#9B1C1C"}

ROTULOS_RESUMO = [
    ("contratante", "Contratante"), ("contratada", "Contratada"), ("objeto", "Objeto"),
    ("valor", "Valor"), ("pagamento", "Pagamento"), ("vigencia", "Vigência"),
    ("foro", "Foro"), ("data_assinatura", "Data"),
]


def _v(valor):
    return valor if valor else "Não identificado"


# ---------------------------------------------------------------------------
# PDF
# ---------------------------------------------------------------------------
CSS_PDF = """
* { font-family: sans-serif; }
body { font-size: 10px; color: #1F2430; }
h1 { font-family: serif; font-size: 22px; color: #14213D; margin-bottom: 2px; }
h2 { font-family: serif; font-size: 15px; color: #14213D; margin-top: 16px;
     margin-bottom: 6px; border-bottom: 1px solid #D9D2C3; }
.sobrelinha { font-size: 8px; color: #A47E3B; font-weight: bold; letter-spacing: 2px; }
.rotulo { font-size: 8px; color: #4A5B7A; font-weight: bold; }
.muted { color: #5B6475; }
.trecho { color: #3A3F4B; font-style: italic; margin-left: 10px; }
.aviso { font-size: 8px; color: #5B6475; }
td { padding: 3px 6px; vertical-align: top; }
"""


def _html_pontos(pontos):
    if not pontos:
        return "<p class='muted'>Nenhum item.</p>"
    partes = []
    for p in pontos:
        partes.append(
            f"<p><b>[{escape(p['severidade'])}] {escape(p['titulo'])}</b>"
            f" <span class='muted'>— {escape(p['referencia'] or '')}</span><br/>"
            f"{escape(p['descricao'])}</p>"
        )
        if p.get("trecho"):
            partes.append(f"<p class='trecho'>“{escape(p['trecho'])}”</p>")
        partes.append(f"<p><span class='rotulo'>RECOMENDAÇÃO</span> {escape(p['recomendacao'])}</p>")
    return "".join(partes)


def _html_relatorio(analise: dict) -> str:
    r = analise["resultado"]
    c = r["classificacao"]
    cor = CORES_NIVEL.get(c["nivel"], "#14213D")
    resumo = r["resumo"]

    html = [
        "<p class='sobrelinha'>CONTRACT REVIEW ASSISTANT / RELATÓRIO</p>",
        f"<h1>Análise #{analise['id']} — {escape(analise['nome_arquivo'])}</h1>",
        f"<p class='muted'>Gerado em {escape(analise['criado_em'])} · regras v{escape(r['versao_regras'])}</p>",
        "<h2>Resultado final</h2>",
        f"<p><span class='rotulo'>CLASSIFICAÇÃO DE RISCO</span><br/>"
        f"<b style='color:{cor}; font-size:16px'>{escape(c['nivel'])}</b> (pontuação {c['pontuacao']})</p>",
        f"<p><span class='rotulo'>REVISÃO HUMANA</span><br/>"
        f"<b>{'Necessária' if c['revisao_humana'] else 'Não obrigatória'}</b></p>",
        "<p>" + "<br/>".join(escape(m) for m in c["motivos"]) + "</p>",
        f"<p><span class='rotulo'>STATUS DA REVISÃO</span><br/>{escape(analise['status_revisao'])}</p>",
    ]
    if analise.get("revisor"):
        html.append(f"<p><span class='rotulo'>REVISOR</span><br/>{escape(analise['revisor'])}"
                    f" — {escape(analise.get('data_revisao') or '')}</p>")
    if analise.get("observacoes"):
        html.append(f"<p><span class='rotulo'>OBSERVAÇÕES DA REVISÃO</span><br/>"
                    f"{escape(analise['observacoes'])}</p>")

    html.append("<h2>Resumo esquematizado</h2><table>")
    for chave, rotulo in ROTULOS_RESUMO:
        html.append(f"<tr><td class='rotulo'>{rotulo.upper()}</td>"
                    f"<td>{escape(_v(resumo.get(chave)))}</td></tr>")
    html.append("</table>")

    html.append("<h2>Cláusulas identificadas</h2><table>")
    for cl in r["clausulas"]:
        situacao = "Identificada" if cl["identificada"] else "Não encontrada"
        html.append(f"<tr><td><b>{escape(cl['nome'])}</b></td><td>{situacao}</td>"
                    f"<td class='muted'>{escape(cl['referencia'] or '—')}</td></tr>")
    html.append("</table>")

    html.append("<h2>Pontos de atenção</h2>" + _html_pontos(r["pontos_atencao"]))
    html.append("<h2>Informações ausentes</h2>" + _html_pontos(r["informacoes_ausentes"]))

    ia = analise.get("parecer_ia")
    if ia:
        html.append(f"<h2>Parecer complementar da IA</h2>"
                    f"<p class='muted'>Modelo: {escape(analise.get('modelo_ia') or '')}</p>"
                    f"<p>{escape(ia.get('resumo_executivo', ''))}</p>")
        if ia.get("nivel_risco_sugerido"):
            html.append(f"<p><span class='rotulo'>NÍVEL SUGERIDO PELA IA</span><br/>"
                        f"{escape(ia['nivel_risco_sugerido'])} — {escape(ia.get('justificativa_nivel', ''))}</p>")
        for p in ia.get("pontos_adicionais", []):
            verificado = "" if p.get("trecho_verificado") else " (trecho não localizado no contrato)"
            html.append(f"<p><b>[{escape(str(p.get('severidade', '')))}] {escape(str(p.get('titulo', '')))}</b><br/>"
                        f"{escape(str(p.get('comentario', '')))}</p>"
                        f"<p class='trecho'>“{escape(str(p.get('trecho', '')))}”{verificado}</p>")
        if ia.get("recomendacoes"):
            html.append("<p><span class='rotulo'>RECOMENDAÇÕES</span></p><ul>"
                        + "".join(f"<li>{escape(str(x))}</li>" for x in ia["recomendacoes"]) + "</ul>")

    html.append(f"<p class='aviso'><br/>{escape(AVISO)}</p>")
    return "".join(html)


def gerar_pdf(analise: dict) -> bytes:
    story = pymupdf.Story(html=_html_relatorio(analise), user_css=CSS_PDF)
    buffer = io.BytesIO()
    escritor = pymupdf.DocumentWriter(buffer)
    pagina = pymupdf.paper_rect("a4")
    area = pagina + (48, 48, -48, -56)
    continuar = True
    while continuar:
        dispositivo = escritor.begin_page(pagina)
        continuar, _ = story.place(area)
        story.draw(dispositivo)
        escritor.end_page()
    escritor.close()

    # Numeração de páginas
    with pymupdf.open(stream=buffer.getvalue(), filetype="pdf") as documento:
        total = documento.page_count
        for i, pg in enumerate(documento, start=1):
            pg.insert_text((48, pg.rect.height - 28),
                           f"Contract Review Assistant · Análise #{analise['id']} · página {i} de {total}",
                           fontsize=7, color=(0.36, 0.39, 0.46))
        return documento.tobytes(garbage=3, deflate=True)


# ---------------------------------------------------------------------------
# DOCX
# ---------------------------------------------------------------------------
AZUL = RGBColor(0x14, 0x21, 0x3D)
CINZA = RGBColor(0x5B, 0x64, 0x75)
DOURADO = RGBColor(0xA4, 0x7E, 0x3B)


def _rotulo(doc, texto):
    run = doc.add_paragraph().add_run(texto.upper())
    run.bold, run.font.size, run.font.color.rgb = True, Pt(8), RGBColor(0x4A, 0x5B, 0x7A)


def _titulo(doc, texto, nivel=1):
    cabecalho = doc.add_heading(texto, level=nivel)
    for run in cabecalho.runs:
        run.font.color.rgb = AZUL
        run.font.name = "Georgia"


def _docx_pontos(doc, pontos):
    if not pontos:
        doc.add_paragraph("Nenhum item.")
        return
    for p in pontos:
        par = doc.add_paragraph()
        par.add_run(f"[{p['severidade']}] {p['titulo']}").bold = True
        ref = par.add_run(f" — {p['referencia'] or ''}")
        ref.font.color.rgb = CINZA
        doc.add_paragraph(p["descricao"])
        if p.get("trecho"):
            trecho = doc.add_paragraph().add_run(f"“{p['trecho']}”")
            trecho.italic = True
        rec = doc.add_paragraph()
        rec.add_run("Recomendação: ").bold = True
        rec.add_run(p["recomendacao"])


def gerar_docx(analise: dict) -> bytes:
    r = analise["resultado"]
    c = r["classificacao"]
    resumo = r["resumo"]
    doc = Document()
    estilo = doc.styles["Normal"]
    estilo.font.name, estilo.font.size = "Calibri", Pt(10.5)

    sobre = doc.add_paragraph().add_run("CONTRACT REVIEW ASSISTANT / RELATÓRIO")
    sobre.bold, sobre.font.size, sobre.font.color.rgb = True, Pt(8), DOURADO
    _titulo(doc, f"Análise #{analise['id']} — {analise['nome_arquivo']}", 0)
    info = doc.add_paragraph().add_run(f"Gerado em {analise['criado_em']} · regras v{r['versao_regras']}")
    info.font.color.rgb = CINZA

    _titulo(doc, "Resultado final")
    _rotulo(doc, "Classificação de risco")
    par = doc.add_paragraph()
    nivel = par.add_run(c["nivel"])
    nivel.bold, nivel.font.size = True, Pt(16)
    nivel.font.color.rgb = RGBColor.from_string(CORES_NIVEL.get(c["nivel"], "#14213D")[1:])
    par.add_run(f"  (pontuação {c['pontuacao']})")
    _rotulo(doc, "Revisão humana")
    doc.add_paragraph("Necessária" if c["revisao_humana"] else "Não obrigatória")
    for motivo in c["motivos"]:
        doc.add_paragraph(motivo, style="List Bullet")
    _rotulo(doc, "Status da revisão")
    doc.add_paragraph(analise["status_revisao"])
    if analise.get("revisor"):
        _rotulo(doc, "Revisor")
        doc.add_paragraph(f"{analise['revisor']} — {analise.get('data_revisao') or ''}")
    if analise.get("observacoes"):
        _rotulo(doc, "Observações da revisão")
        doc.add_paragraph(analise["observacoes"])

    _titulo(doc, "Resumo esquematizado")
    tabela = doc.add_table(rows=0, cols=2)
    tabela.style = "Light Grid Accent 1"
    for chave, rotulo in ROTULOS_RESUMO:
        linha = tabela.add_row().cells
        linha[0].text, linha[1].text = rotulo, _v(resumo.get(chave))
        linha[0].paragraphs[0].runs[0].bold = True

    _titulo(doc, "Cláusulas identificadas")
    tabela = doc.add_table(rows=1, cols=3)
    tabela.style = "Light Grid Accent 1"
    for celula, texto in zip(tabela.rows[0].cells, ["Cláusula", "Situação", "Localização"]):
        celula.text = texto
    for cl in r["clausulas"]:
        linha = tabela.add_row().cells
        linha[0].text = cl["nome"]
        linha[1].text = "Identificada" if cl["identificada"] else "Não encontrada"
        linha[2].text = cl["referencia"] or "—"

    _titulo(doc, "Pontos de atenção")
    _docx_pontos(doc, r["pontos_atencao"])
    _titulo(doc, "Informações ausentes")
    _docx_pontos(doc, r["informacoes_ausentes"])

    ia = analise.get("parecer_ia")
    if ia:
        _titulo(doc, "Parecer complementar da IA")
        doc.add_paragraph(f"Modelo: {analise.get('modelo_ia') or ''}").runs[0].font.color.rgb = CINZA
        doc.add_paragraph(ia.get("resumo_executivo", ""))
        if ia.get("nivel_risco_sugerido"):
            _rotulo(doc, "Nível sugerido pela IA")
            doc.add_paragraph(f"{ia['nivel_risco_sugerido']} — {ia.get('justificativa_nivel', '')}")
        for p in ia.get("pontos_adicionais", []):
            par = doc.add_paragraph()
            par.add_run(f"[{p.get('severidade', '')}] {p.get('titulo', '')}").bold = True
            doc.add_paragraph(str(p.get("comentario", "")))
            sufixo = "" if p.get("trecho_verificado") else " (trecho não localizado no contrato)"
            doc.add_paragraph().add_run(f"“{p.get('trecho', '')}”{sufixo}").italic = True
        for rec in ia.get("recomendacoes", []):
            doc.add_paragraph(str(rec), style="List Bullet")

    aviso = doc.add_paragraph()
    aviso.alignment = WD_ALIGN_PARAGRAPH.LEFT
    run = aviso.add_run(AVISO)
    run.font.size, run.font.color.rgb = Pt(8), CINZA

    buffer = io.BytesIO()
    doc.save(buffer)
    return buffer.getvalue()
