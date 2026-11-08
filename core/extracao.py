"""Extração de texto de arquivos PDF, TXT e DOCX."""

import io
import re
from dataclasses import dataclass

import pymupdf
from docx import Document

FORMATOS_ACEITOS = ["pdf", "txt", "docx"]


class ErroExtracao(Exception):
    """Erro ao ler o arquivo enviado."""


@dataclass
class DocumentoExtraido:
    nome_arquivo: str
    formato: str
    texto: str
    paginas: int


def extrair_texto(nome_arquivo: str, conteudo: bytes) -> DocumentoExtraido:
    """Identifica o formato pela extensão e extrai o texto do arquivo."""
    formato = nome_arquivo.rsplit(".", 1)[-1].lower() if "." in nome_arquivo else ""
    if formato not in FORMATOS_ACEITOS:
        raise ErroExtracao(f"Formato '.{formato}' não suportado. Use PDF, TXT ou DOCX.")

    if formato == "pdf":
        texto, paginas = _extrair_pdf(conteudo)
    elif formato == "docx":
        texto, paginas = _extrair_docx(conteudo), 0
    else:
        texto, paginas = _extrair_txt(conteudo), 0

    return DocumentoExtraido(nome_arquivo, formato, limpar_texto(texto), paginas)


def _extrair_pdf(conteudo: bytes) -> tuple[str, int]:
    try:
        with pymupdf.open(stream=conteudo, filetype="pdf") as documento:
            if documento.needs_pass:
                raise ErroExtracao("O PDF está protegido por senha.")
            paginas = [pagina.get_text("text", sort=True) for pagina in documento]
            return "\n".join(paginas), len(paginas)
    except ErroExtracao:
        raise
    except Exception as erro:  # PDF corrompido ou inválido
        raise ErroExtracao(f"Não foi possível ler o PDF: {erro}") from erro


def _extrair_docx(conteudo: bytes) -> str:
    try:
        documento = Document(io.BytesIO(conteudo))
    except Exception as erro:
        raise ErroExtracao(f"Não foi possível ler o DOCX: {erro}") from erro

    linhas = [paragrafo.text for paragrafo in documento.paragraphs]
    # Tabelas (ex.: quadro de assinaturas) também são extraídas
    for tabela in documento.tables:
        for linha in tabela.rows:
            linhas.append(" | ".join(celula.text for celula in linha.cells))
    return "\n".join(linhas)


def _extrair_txt(conteudo: bytes) -> str:
    for codificacao in ("utf-8-sig", "cp1252", "latin-1"):
        try:
            return conteudo.decode(codificacao)
        except UnicodeDecodeError:
            continue
    raise ErroExtracao("Não foi possível identificar a codificação do arquivo de texto.")


def limpar_texto(texto: str) -> str:
    """Remove ruídos comuns da extração sem alterar o conteúdo."""
    texto = texto.replace("\r\n", "\n").replace("\r", "\n").replace("\xa0", " ")
    # Ligaduras tipográficas comuns em PDF ("ﬁ" → "fi")
    for ligadura, letras in {"\ufb00": "ff", "\ufb01": "fi", "\ufb02": "fl",
                             "\ufb03": "ffi", "\ufb04": "ffl"}.items():
        texto = texto.replace(ligadura, letras)
    # Junta palavras hifenizadas na quebra de linha do PDF ("presta-\nção")
    texto = re.sub(r"(\w)-\n(\w)", r"\1\2", texto)
    texto = re.sub(r"[ \t]+", " ", texto)
    texto = re.sub(r" *\n *", "\n", texto)
    texto = re.sub(r"\n{3,}", "\n\n", texto)
    return texto.strip()
