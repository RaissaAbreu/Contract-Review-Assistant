"""
Integração opcional com a OpenAI.

A análise principal é feita por regras. Este módulo só é chamado quando o
usuário clica em "Analisar com IA" e gera um parecer complementar. Ele não
altera a classificação de risco calculada pelas regras.
"""

import json
import os

from dotenv import load_dotenv

load_dotenv()

MODELO_PADRAO = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
LIMITE_CARACTERES = 60_000  # evita enviar contratos muito longos de uma vez


class ErroIA(Exception):
    """Erro na chamada ao modelo."""


def chave_configurada() -> bool:
    return bool(os.getenv("OPENAI_API_KEY"))


PROMPT_SISTEMA = """Você é um assistente de revisão contratual que apoia advogados brasileiros.
Você NÃO substitui a análise de um advogado. Responda sempre em português do Brasil.

Você receberá:
1. o texto de um contrato;
2. o resultado de uma análise automática por regras (cláusulas identificadas,
   pontos de atenção, informações ausentes e classificação de risco).

Sua tarefa é complementar essa análise. Responda SOMENTE com um JSON válido no formato:
{
  "resumo_executivo": "3 a 5 frases sobre o contrato e seus principais riscos",
  "pontos_adicionais": [
    {
      "titulo": "nome curto do ponto",
      "categoria": "Rescisão | Multa | Responsabilidade | Confidencialidade | Proteção de dados | Prazo e vigência | Outro",
      "severidade": "Baixa | Média | Alta | Crítica",
      "trecho": "trecho LITERAL do contrato que fundamenta o ponto",
      "comentario": "por que isso merece atenção"
    }
  ],
  "divergencias": ["pontos da análise por regras que parecem falsos positivos ou mal classificados"],
  "nivel_risco_sugerido": "Baixo | Médio | Alto | Crítico",
  "justificativa_nivel": "por que você sugere esse nível",
  "recomendacoes": ["ações objetivas para a revisão humana"]
}

Regras:
- Em "pontos_adicionais", traga apenas pontos que a análise por regras NÃO identificou.
- Todo "trecho" deve ser copiado literalmente do contrato. Não invente cláusulas.
- Se não houver nada a acrescentar, use listas vazias."""


def _resumo_regras(resultado: dict) -> dict:
    """Versão compacta do resultado das regras para enviar ao modelo."""
    return {
        "clausulas": [{"nome": c["nome"], "identificada": c["identificada"]}
                      for c in resultado["clausulas"]],
        "pontos_atencao": [{"titulo": p["titulo"], "severidade": p["severidade"],
                            "trecho": p["trecho"]} for p in resultado["pontos_atencao"]],
        "informacoes_ausentes": [{"titulo": p["titulo"], "severidade": p["severidade"]}
                                 for p in resultado["informacoes_ausentes"]],
        "classificacao": {k: resultado["classificacao"][k] for k in ("nivel", "pontuacao")},
    }


def analisar_com_ia(texto: str, resultado: dict, modelo: str | None = None) -> dict:
    """Envia o contrato ao modelo e retorna o parecer complementar (dict)."""
    if not chave_configurada():
        raise ErroIA("OPENAI_API_KEY não configurada. Defina a chave no arquivo .env.")

    from openai import OpenAI, OpenAIError  # importação tardia: só quando a IA é usada

    modelo = (modelo or MODELO_PADRAO).strip()
    texto_enviado = texto[:LIMITE_CARACTERES]
    aviso_truncado = len(texto) > LIMITE_CARACTERES

    mensagem_usuario = (
        "CONTRATO:\n<<<\n" + texto_enviado + "\n>>>\n\n"
        + ("(Atenção: o contrato foi truncado por tamanho.)\n\n" if aviso_truncado else "")
        + "ANÁLISE POR REGRAS:\n" + json.dumps(_resumo_regras(resultado), ensure_ascii=False)
    )

    try:
        cliente = OpenAI()
        resposta = cliente.chat.completions.create(
            model=modelo,
            messages=[
                {"role": "system", "content": PROMPT_SISTEMA},
                {"role": "user", "content": mensagem_usuario},
            ],
            response_format={"type": "json_object"},
        )
    except OpenAIError as erro:
        raise ErroIA(f"Falha na chamada à OpenAI: {erro}") from erro

    conteudo = resposta.choices[0].message.content or ""
    try:
        parecer = json.loads(conteudo)
    except json.JSONDecodeError as erro:
        raise ErroIA("O modelo não retornou um JSON válido.") from erro

    # Garante as chaves esperadas mesmo que o modelo omita alguma
    parecer.setdefault("resumo_executivo", "")
    parecer.setdefault("pontos_adicionais", [])
    parecer.setdefault("divergencias", [])
    parecer.setdefault("nivel_risco_sugerido", "")
    parecer.setdefault("justificativa_nivel", "")
    parecer.setdefault("recomendacoes", [])
    parecer["texto_truncado"] = aviso_truncado

    # Confere se cada trecho citado pelo modelo existe de fato no contrato
    from .analisador import normalizar
    contrato = " ".join(normalizar(texto).split())
    for ponto in parecer["pontos_adicionais"]:
        citado = " ".join(normalizar(str(ponto.get("trecho", ""))).split()).strip(" .…\"'")
        ponto["trecho_verificado"] = bool(citado) and citado in contrato
    return parecer
