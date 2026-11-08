"""
Gera as versões PDF e DOCX dos contratos fictícios a partir dos arquivos .txt.

Uso (na raiz do projeto):  python demo/gerar_contratos_demo.py
"""

import io
import re
from html import escape
from pathlib import Path

import pymupdf
from docx import Document
from docx.enum.text import WD_ALIGN_PARAGRAPH
from docx.shared import Pt

PASTA = Path(__file__).resolve().parent

CSS = """
* { font-family: serif; }
body { font-size: 11px; line-height: 1.45; color: #111; }
h1 { font-size: 14px; text-align: center; margin-bottom: 4px; }
.aviso { text-align: center; font-size: 8px; color: #8A2D2D; margin-bottom: 14px; }
h2 { font-size: 11px; margin-top: 12px; margin-bottom: 4px; }
p { margin-top: 0; margin-bottom: 6px; text-align: justify; }
"""


def _blocos(texto: str):
    """Classifica cada linha do TXT em título, aviso, cláusula ou parágrafo."""
    linhas = [l.strip() for l in texto.splitlines()]
    for i, linha in enumerate(linhas):
        if not linha:
            continue
        if i == 0:
            yield "titulo", linha
        elif linha.startswith("DOCUMENTO FICTÍCIO"):
            yield "aviso", linha
        elif re.match(r"CLÁUSULA\s", linha):
            yield "clausula", linha
        else:
            yield "paragrafo", linha


def gerar_pdf(texto: str, destino: Path):
    partes = []
    for tipo, linha in _blocos(texto):
        if tipo == "titulo":
            partes.append(f"<h1>{escape(linha)}</h1>")
        elif tipo == "aviso":
            partes.append(f"<p class='aviso'>{escape(linha)}</p>")
        elif tipo == "clausula":
            partes.append(f"<h2>{escape(linha)}</h2>")
        else:
            partes.append(f"<p>{escape(linha)}</p>")

    story = pymupdf.Story(html="".join(partes), user_css=CSS)
    buffer = io.BytesIO()
    escritor = pymupdf.DocumentWriter(buffer)
    pagina = pymupdf.paper_rect("a4")
    continuar = True
    while continuar:
        dispositivo = escritor.begin_page(pagina)
        continuar, _ = story.place(pagina + (64, 64, -64, -64))
        story.draw(dispositivo)
        escritor.end_page()
    escritor.close()
    destino.write_bytes(buffer.getvalue())


def gerar_docx(texto: str, destino: Path):
    doc = Document()
    doc.styles["Normal"].font.name = "Times New Roman"
    doc.styles["Normal"].font.size = Pt(11)
    for tipo, linha in _blocos(texto):
        paragrafo = doc.add_paragraph()
        run = paragrafo.add_run(linha)
        if tipo in ("titulo", "aviso"):
            paragrafo.alignment = WD_ALIGN_PARAGRAPH.CENTER
            run.bold = tipo == "titulo"
            run.font.size = Pt(13 if tipo == "titulo" else 8)
        elif tipo == "clausula":
            run.bold = True
        else:
            paragrafo.alignment = WD_ALIGN_PARAGRAPH.JUSTIFY
    doc.save(destino)


if __name__ == "__main__":
    for arquivo in sorted(PASTA.glob("contrato_*.txt")):
        texto = arquivo.read_text(encoding="utf-8")
        gerar_pdf(texto, arquivo.with_suffix(".pdf"))
        gerar_docx(texto, arquivo.with_suffix(".docx"))
        print(f"Gerado: {arquivo.stem}.pdf e {arquivo.stem}.docx")
