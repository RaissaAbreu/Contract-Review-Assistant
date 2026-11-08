"""Persistência das análises e revisões em SQLite."""

import json
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path

CAMINHO_BANCO = Path(__file__).resolve().parent.parent / "data" / "analises.db"

STATUS_NAO_EXIGIDA = "Revisão não exigida"
STATUS_AGUARDANDO = "Aguardando revisão"
DECISOES = ["Aprovado", "Aprovado com ressalvas", "Reprovado"]


@contextmanager
def conexao():
    CAMINHO_BANCO.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(CAMINHO_BANCO)
    con.row_factory = sqlite3.Row
    try:
        yield con
        con.commit()
    finally:
        con.close()


def inicializar():
    with conexao() as con:
        con.execute("""
            CREATE TABLE IF NOT EXISTS analises (
                id                 INTEGER PRIMARY KEY AUTOINCREMENT,
                criado_em          TEXT NOT NULL,
                nome_arquivo       TEXT NOT NULL,
                formato            TEXT NOT NULL,
                paginas            INTEGER,
                texto              TEXT NOT NULL,
                resultado_json     TEXT NOT NULL,
                nivel_risco        TEXT NOT NULL,
                pontuacao          INTEGER NOT NULL,
                revisao_necessaria INTEGER NOT NULL,
                parecer_ia_json    TEXT,
                modelo_ia          TEXT,
                status_revisao     TEXT NOT NULL,
                revisor            TEXT,
                observacoes        TEXT,
                data_revisao       TEXT
            )
        """)


def _agora():
    return datetime.now().strftime("%Y-%m-%d %H:%M:%S")


def salvar_analise(documento, resultado: dict) -> int:
    classificacao = resultado["classificacao"]
    status = STATUS_AGUARDANDO if classificacao["revisao_humana"] else STATUS_NAO_EXIGIDA
    with conexao() as con:
        cursor = con.execute(
            """INSERT INTO analises (criado_em, nome_arquivo, formato, paginas, texto,
                   resultado_json, nivel_risco, pontuacao, revisao_necessaria, status_revisao)
               VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
            (_agora(), documento.nome_arquivo, documento.formato, documento.paginas,
             documento.texto, json.dumps(resultado, ensure_ascii=False),
             classificacao["nivel"], classificacao["pontuacao"],
             int(classificacao["revisao_humana"]), status),
        )
        return cursor.lastrowid


def _converter(linha: sqlite3.Row) -> dict:
    analise = dict(linha)
    analise["resultado"] = json.loads(analise.pop("resultado_json"))
    parecer = analise.pop("parecer_ia_json")
    analise["parecer_ia"] = json.loads(parecer) if parecer else None
    analise["revisao_necessaria"] = bool(analise["revisao_necessaria"])
    return analise


def obter_analise(analise_id: int) -> dict | None:
    with conexao() as con:
        linha = con.execute("SELECT * FROM analises WHERE id = ?", (analise_id,)).fetchone()
    return _converter(linha) if linha else None


def listar_analises(status: str | None = None) -> list[dict]:
    """Lista resumida (sem texto e sem JSON) para tabelas e seletores."""
    consulta = """SELECT id, criado_em, nome_arquivo, formato, nivel_risco, pontuacao,
                         revisao_necessaria, status_revisao, revisor, data_revisao,
                         parecer_ia_json IS NOT NULL AS tem_parecer_ia
                  FROM analises"""
    parametros = ()
    if status:
        consulta += " WHERE status_revisao = ?"
        parametros = (status,)
    consulta += " ORDER BY id DESC"
    with conexao() as con:
        return [dict(l) for l in con.execute(consulta, parametros).fetchall()]


def salvar_parecer_ia(analise_id: int, parecer: dict, modelo: str):
    with conexao() as con:
        con.execute("UPDATE analises SET parecer_ia_json = ?, modelo_ia = ? WHERE id = ?",
                    (json.dumps(parecer, ensure_ascii=False), modelo, analise_id))


def registrar_revisao(analise_id: int, revisor: str, decisao: str, observacoes: str):
    if decisao not in DECISOES:
        raise ValueError(f"Decisão inválida: {decisao}")
    with conexao() as con:
        con.execute(
            """UPDATE analises SET status_revisao = ?, revisor = ?, observacoes = ?,
                   data_revisao = ? WHERE id = ?""",
            (decisao, revisor.strip(), observacoes.strip(), _agora(), analise_id),
        )


def contar_por_status() -> dict:
    with conexao() as con:
        linhas = con.execute(
            "SELECT status_revisao, COUNT(*) AS total FROM analises GROUP BY status_revisao"
        ).fetchall()
    return {l["status_revisao"]: l["total"] for l in linhas}


def excluir_analise(analise_id: int):
    with conexao() as con:
        con.execute("DELETE FROM analises WHERE id = ?", (analise_id,))
