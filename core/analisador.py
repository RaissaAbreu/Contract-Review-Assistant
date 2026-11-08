"""
Motor de análise por regras.

Fluxo:
1. normalizar o texto (minúsculas, sem acentos) mantendo as posições;
2. segmentar o contrato em cláusulas;
3. identificar as cláusulas de interesse;
4. aplicar as regras de pontos de atenção e de informações ausentes;
5. montar o resumo esquematizado;
6. calcular a classificação de risco.
"""

import re
import unicodedata
from dataclasses import asdict, dataclass

from . import regras


# ---------------------------------------------------------------------------
# Estruturas
# ---------------------------------------------------------------------------
@dataclass
class Segmento:
    indice: int
    titulo: str
    inicio: int
    fim: int


@dataclass
class Ponto:
    categoria: str
    titulo: str
    descricao: str
    severidade: str
    trecho: str
    referencia: str
    recomendacao: str


# ---------------------------------------------------------------------------
# Utilitários de texto
# ---------------------------------------------------------------------------
def normalizar(texto: str) -> str:
    """Minúsculas e sem acentos, com o MESMO tamanho do texto original.

    Manter o tamanho permite usar as posições encontradas no texto normalizado
    para recortar o trecho original (com acentos).
    """
    return "".join(unicodedata.normalize("NFD", c)[0] for c in texto).lower()


def _uma_linha(texto: str) -> str:
    return re.sub(r"\s+", " ", texto).strip()


def _eh_maiuscula(linha: str) -> bool:
    letras = [c for c in linha if c.isalpha()]
    if len(letras) < 4 or len(linha) > 90:
        return False
    return sum(c.isupper() for c in letras) / len(letras) >= 0.85


def _eh_fim_de_frase(texto: str, i: int) -> bool:
    """Indica se o ponto na posição i encerra uma frase.

    Não encerram frase: numeração de cláusula ("5.1."), números ("18.000"),
    siglas e abreviações seguidas de vírgula ou letra ("LTDA.,", "S.A.").
    """
    if texto[i] == ";":
        return True
    if texto[i] != ".":
        return False
    seguinte = texto[i + 1:i + 2]
    if seguinte and not seguinte.isspace():
        return False
    token = re.split(r"\s", texto[max(0, i - 15):i + 1])[-1]
    return re.fullmatch(r"\d+(\.\d+)*\.", token) is None


def _inicio_de_bloco(texto: str, pos: int) -> bool:
    """Indica se a linha que começa em pos inicia um novo item/título."""
    linha = texto[pos:texto.find("\n", pos) if "\n" in texto[pos:] else len(texto)]
    return bool(re.match(r"\s*(\d+(\.\d+)*\.?\s|par[aá]grafo|cl[aá]usula)", linha, re.I)) \
        or _eh_maiuscula(linha)


def _em_titulo(texto: str, pos: int) -> bool:
    """Indica se a posição está numa linha de título de cláusula."""
    inicio = texto.rfind("\n", 0, pos) + 1
    fim = texto.find("\n", pos)
    linha = texto[inicio:fim if fim != -1 else len(texto)]
    return _eh_maiuscula(linha) or re.match(r"\s*cl[aá]usula\s", linha, re.I) is not None


def _buscar(padrao, norm, texto, inicio=0, fim=None, evitar=None):
    """Primeira ocorrência fora de linhas de título (ou a de título, se só houver ela)."""
    fim = len(norm) if fim is None else fim
    reserva = None
    for achado in re.finditer(padrao, norm[inicio:fim]):
        if evitar and evitar(achado):
            continue
        if _em_titulo(texto, inicio + achado.start()):
            reserva = reserva or achado
            continue
        return achado
    return reserva


def recortar_frase(texto: str, inicio: int, fim: int, limite: int = 420) -> str:
    """Expande uma ocorrência até os limites da frase em que está."""
    esquerda = inicio
    while esquerda > 0 and inicio - esquerda < 260:
        anterior = texto[esquerda - 1]
        if anterior == "\n" and _inicio_de_bloco(texto, esquerda):
            break
        if anterior in ".;" and _eh_fim_de_frase(texto, esquerda - 1):
            break
        esquerda -= 1

    direita = fim
    while direita < len(texto) and direita - fim < 260:
        atual = texto[direita]
        if atual == "\n" and _inicio_de_bloco(texto, direita + 1):
            break
        if atual in ".;" and _eh_fim_de_frase(texto, direita):
            direita += 1
            break
        direita += 1

    frase = _uma_linha(texto[esquerda:direita])
    # Remove numeração solta no início ("5.1 ", "Parágrafo único.")
    frase = re.sub(r"^\d+(\.\d+)*\s*[-–.)]?\s*", "", frase)
    if len(frase) > limite:
        frase = frase[:limite].rsplit(" ", 1)[0] + "…"
    return frase


# ---------------------------------------------------------------------------
# Segmentação
# ---------------------------------------------------------------------------
def segmentar(texto: str, norm: str) -> list[Segmento]:
    """Divide o contrato em blocos a partir dos títulos das cláusulas."""
    linhas = []
    posicao = 0
    for linha in texto.split("\n"):
        linhas.append((posicao, linha))
        posicao += len(linha) + 1

    def eh_titulo_clausula(pos, linha):
        return re.match(r"\s*clausula\s+\S+", norm[pos:pos + len(linha)]) is not None

    titulos = [(p, l) for p, l in linhas if eh_titulo_clausula(p, l)]
    if len(titulos) < 3:
        # Sem "CLÁUSULA X": usa linhas numeradas ou em caixa alta
        titulos = [(p, l) for p, l in linhas
                   if l.strip() and (_eh_maiuscula(l) or re.match(r"\s*\d{1,2}\s*[.)-]\s+[A-ZÁ-Ú]{3}", l))]

    if len(titulos) < 3:
        # Último recurso: parágrafos separados por linha em branco
        segmentos = []
        for achado in re.finditer(r"[^\n](?:.|\n(?!\n))*", texto):
            primeira = achado.group().split("\n", 1)[0]
            segmentos.append(Segmento(len(segmentos), _uma_linha(primeira)[:80],
                                      achado.start(), achado.end()))
        return segmentos

    segmentos = []
    if titulos[0][0] > 0:
        segmentos.append(Segmento(0, "Preâmbulo", 0, titulos[0][0]))
    for i, (pos, linha) in enumerate(titulos):
        fim = titulos[i + 1][0] if i + 1 < len(titulos) else len(texto)
        titulo = _uma_linha(linha)
        # Título em duas linhas: "CLÁUSULA 1ª" + "DO OBJETO"
        resto = texto[pos + len(linha) + 1:fim].split("\n", 1)[0]
        if resto and _eh_maiuscula(resto) and len(titulo) < 25:
            titulo = f"{titulo} – {_uma_linha(resto)}"
        segmentos.append(Segmento(len(segmentos), titulo, pos, fim))
    return segmentos


# ---------------------------------------------------------------------------
# Identificação das cláusulas
# ---------------------------------------------------------------------------
def identificar_clausulas(texto, norm, segmentos):
    """Retorna, para cada cláusula de interesse, os segmentos em que aparece."""
    encontradas = {}
    for chave, definicao in regras.CLAUSULAS.items():
        candidatos = []
        for seg in segmentos:
            titulo_norm = normalizar(seg.titulo)
            corpo = norm[seg.inicio:seg.fim]
            no_titulo = any(re.search(p, titulo_norm) for p in definicao["titulo"])
            termos = sum(1 for p in definicao["termos"] if re.search(p, corpo))
            pontuacao = (10 if no_titulo else 0) + termos
            if no_titulo or termos >= 2:
                candidatos.append((pontuacao, no_titulo, seg))
        candidatos.sort(key=lambda c: (-c[0], c[2].indice))
        encontradas[chave] = candidatos
    return encontradas


def _texto_segmento(texto, seg, limite=600):
    corpo = texto[seg.inicio:seg.fim]
    # Remove a linha de título
    corpo = corpo.split("\n", 1)[1] if "\n" in corpo else corpo
    corpo = re.sub(r"^\d+(\.\d+)*\.?\s+", "", _uma_linha(corpo))
    return corpo if len(corpo) <= limite else corpo[:limite].rsplit(" ", 1)[0] + "…"


# ---------------------------------------------------------------------------
# Pontos de atenção
# ---------------------------------------------------------------------------
def _segmentos_do_escopo(escopo, encontradas, segmentos):
    if escopo == "texto":
        return segmentos
    candidatos = encontradas.get(escopo, [])
    com_titulo = [c[2] for c in candidatos if c[1]]
    return com_titulo or [c[2] for c in candidatos[:1]]


def _referencia(seg: Segmento) -> str:
    return seg.titulo if seg.titulo else f"Bloco {seg.indice + 1}"


def aplicar_regras_padrao(texto, norm, segmentos, encontradas) -> list[Ponto]:
    pontos = []
    for regra in regras.REGRAS_PADRAO:
        for seg in _segmentos_do_escopo(regra["escopo"], encontradas, segmentos):
            corpo = norm[seg.inicio:seg.fim]

            def negado(candidato, corpo=corpo):
                # Ignora ocorrências negadas ("não poderá ser cedido sem anuência")
                antes = corpo[max(0, candidato.start() - 40):candidato.start()]
                return re.search(r"\b(?:nao|nenhuma?|vedad[oa])\b", antes) is not None

            achado = _buscar(regra["padrao"], norm, texto, seg.inicio, seg.fim,
                             negado if regra.get("ignorar_se_negado") else None)
            if not achado:
                continue
            inicio, fim = seg.inicio + achado.start(), seg.inicio + achado.end()
            pontos.append(Ponto(regra["categoria"], regra["titulo"], regra["descricao"],
                                regra["severidade"], recortar_frase(texto, inicio, fim),
                                _referencia(seg), regra["recomendacao"]))
            break  # um registro por regra é suficiente
    return pontos


def _numero(valor: str) -> float:
    return float(valor.replace(".", "").replace(",", "."))


def aplicar_regras_numericas(texto, norm, segmentos, encontradas) -> list[Ponto]:
    pontos = []

    # Multa: percentual elevado ou ausência de valor definido
    segs_multa = _segmentos_do_escopo("multa", encontradas, segmentos)
    maior = None
    for seg in segs_multa:
        corpo = norm[seg.inicio:seg.fim]
        for achado in re.finditer(r"(?:multa|penalidade|clausula penal)[^.%]{0,160}?"
                                  r"(\d{1,3}(?:,\d+)?)\s*%", corpo):
            percentual = _numero(achado.group(1))
            if maior is None or percentual > maior[0]:
                maior = (percentual, seg, seg.inicio + achado.start(), seg.inicio + achado.end())
    if maior:
        percentual, seg, inicio, fim = maior
        if percentual > regras.MULTA_PERCENTUAL_MEDIA:
            severidade = "Alta" if percentual > regras.MULTA_PERCENTUAL_ALTA else "Média"
            pontos.append(Ponto(
                "multa", f"Multa elevada ({percentual:g}%)",
                f"Multa acima de {regras.MULTA_PERCENTUAL_MEDIA}%, o que pode ser considerado "
                f"excessivo (art. 413 do Código Civil permite redução judicial).",
                severidade, recortar_frase(texto, inicio, fim), _referencia(seg),
                "Avaliar redução do percentual ou proporcionalidade ao inadimplemento."))
    elif segs_multa:
        seg = segs_multa[0]
        if not re.search(r"\d\s*%|r\$\s*\d", norm[seg.inicio:seg.fim]):
            achado = re.search(r"multa|penalidade", norm[seg.inicio:seg.fim])
            ini = seg.inicio + (achado.start() if achado else 0)
            pontos.append(Ponto(
                "multa", "Multa sem valor definido",
                "A cláusula prevê penalidade, mas não define percentual ou valor.",
                "Média", recortar_frase(texto, ini, ini + 5), _referencia(seg),
                "Definir o percentual ou valor da multa e sua base de cálculo."))

    # Rescisão: aviso prévio inferior ao mínimo
    for seg in _segmentos_do_escopo("rescisao", encontradas, segmentos):
        corpo = norm[seg.inicio:seg.fim]
        achado = re.search(r"aviso previo[^.]{0,80}?(\d{1,3})\s*(?:\([^)]*\)\s*)?dias"
                           r"|(\d{1,3})\s*(?:\([^)]*\)\s*)?dias[^.]{0,40}aviso", corpo)
        if achado:
            dias = int(achado.group(1) or achado.group(2))
            if dias < regras.AVISO_PREVIO_MINIMO_DIAS:
                pontos.append(Ponto(
                    "rescisao", f"Aviso prévio curto ({dias} dias)",
                    f"Aviso prévio inferior a {regras.AVISO_PREVIO_MINIMO_DIAS} dias.",
                    "Média", recortar_frase(texto, seg.inicio + achado.start(),
                                            seg.inicio + achado.end()),
                    _referencia(seg), "Avaliar prazo de aviso prévio compatível com a "
                                      "transição dos serviços."))
            break

    # Cláusulas encontradas, mas incompletas
    def corpo_da(chave):
        segs = _segmentos_do_escopo(chave, encontradas, segmentos)
        return (segs[0], " ".join(norm[s.inicio:s.fim] for s in segs)) if segs else (None, "")

    seg, corpo = corpo_da("responsabilidade")
    if seg and not re.search(r"limit|teto|nao excedera|valor maximo", corpo) \
            and not any(p.titulo == "Responsabilidade ilimitada" for p in pontos):
        pontos.append(Ponto("responsabilidade", "Sem limite de responsabilidade",
                            "A cláusula não estabelece teto para indenizações.", "Média",
                            _texto_segmento(texto, seg, 300), _referencia(seg),
                            "Incluir limite de responsabilidade e exclusões."))

    seg, corpo = corpo_da("confidencialidade")
    if seg:
        if not re.search(r"\d+\s*(?:\([^)]*\)\s*)?anos?|perpetu|indeterminado|indefinidamente", corpo):
            pontos.append(Ponto("confidencialidade", "Prazo de sigilo não definido",
                                "Não há prazo para a obrigação de confidencialidade.", "Baixa",
                                _texto_segmento(texto, seg, 300), _referencia(seg),
                                "Definir por quanto tempo o sigilo vigora após o término."))
        if not re.search(r"exceto|excecao|excecoes|salvo|nao se aplica", corpo):
            pontos.append(Ponto("confidencialidade", "Sem exceções ao dever de sigilo",
                                "Não há exceções (informação pública, ordem judicial etc.).",
                                "Baixa", _texto_segmento(texto, seg, 300), _referencia(seg),
                                "Incluir exceções usuais ao dever de confidencialidade."))

    seg, corpo = corpo_da("protecao_dados")
    if seg:
        if not re.search(r"\blgpd\b|13\.709", corpo):
            pontos.append(Ponto("protecao_dados", "Sem referência à LGPD",
                                "A cláusula de dados não menciona a Lei 13.709/2018.", "Alta",
                                _texto_segmento(texto, seg, 300), _referencia(seg),
                                "Referenciar a LGPD e definir os papéis de controlador e operador."))
        if not re.search(r"incidente|vazamento|violacao de dados|violacao de seguranca", corpo):
            pontos.append(Ponto("protecao_dados", "Sem procedimento para incidentes",
                                "Não há dever de comunicar incidentes de segurança.", "Média",
                                _texto_segmento(texto, seg, 300), _referencia(seg),
                                "Prever comunicação de incidentes em prazo definido (ex.: 48h)."))

    return pontos


# ---------------------------------------------------------------------------
# Informações ausentes
# ---------------------------------------------------------------------------
def verificar_ausencias(texto, norm, encontradas) -> list[Ponto]:
    ausentes = []
    for chave, definicao in regras.CLAUSULAS.items():
        if not encontradas[chave]:
            severidade, recomendacao = definicao["ausencia"]
            ausentes.append(Ponto(chave, f"Cláusula de {definicao['nome'].lower()} não encontrada",
                                  f"Não foi identificada cláusula de {definicao['nome'].lower()}.",
                                  severidade, "", "Contrato inteiro", recomendacao))

    documentos = set(re.findall(regras.PADRAO_CNPJ, texto)) | set(re.findall(regras.PADRAO_CPF, texto))
    documentos = {re.sub(r"\D", "", d) for d in documentos}
    if not documentos:
        ausentes.append(Ponto("partes", "Partes sem CNPJ/CPF",
                              "Nenhum CNPJ ou CPF foi encontrado no contrato.", "Alta", "",
                              "Qualificação das partes", "Incluir CNPJ/CPF de todas as partes."))
    elif len(documentos) == 1:
        ausentes.append(Ponto("partes", "Apenas uma parte com CNPJ/CPF",
                              "Somente um número de CNPJ/CPF foi encontrado.", "Média", "",
                              "Qualificação das partes",
                              "Incluir CNPJ/CPF de todas as partes."))

    verificacoes = [
        (regras.PADRAO_ENDERECO, "Endereço/sede das partes ausente",
         "Não foi encontrado endereço ou sede das partes.", "Média",
         "Qualificar as partes com endereço completo."),
        (regras.PADRAO_REPRESENTANTE, "Representante legal não indicado",
         "Não há indicação de quem representa as partes.", "Baixa",
         "Indicar o representante legal e seus poderes."),
        (regras.PADRAO_ASSINATURA, "Campo de assinaturas ausente",
         "Não foi encontrado bloco de assinaturas.", "Alta",
         "Incluir campo de assinatura das partes."),
        (regras.PADRAO_TESTEMUNHAS, "Testemunhas ausentes",
         "Sem testemunhas, o contrato não é título executivo extrajudicial "
         "(art. 784, III, do CPC), salvo assinatura eletrônica.", "Baixa",
         "Incluir duas testemunhas ou prever assinatura eletrônica."),
    ]
    for padrao, titulo, descricao, severidade, recomendacao in verificacoes:
        if not re.search(padrao, norm):
            ausentes.append(Ponto("partes", titulo, descricao, severidade, "",
                                  "Qualificação e assinaturas", recomendacao))
    return ausentes


# ---------------------------------------------------------------------------
# Resumo esquematizado
# ---------------------------------------------------------------------------
MESES = r"janeiro|fevereiro|marco|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro"


def _primeira_frase(texto, norm, padrao, inicio=0, fim=None):
    achado = _buscar(padrao, norm, texto, inicio, fim)
    if not achado:
        return None
    return recortar_frase(texto, inicio + achado.start(), inicio + achado.end(), 300)


def _nome_parte(texto, norm, papel):
    # Formato "CONTRATANTE: EMPRESA X LTDA., ..."
    achado = re.search(rf"\b{papel}\s*:\s*", norm)
    if achado:
        resto = texto[achado.end():achado.end() + 160]
        nome = re.split(r",|\n|;| inscrit| pessoa", resto, maxsplit=1)[0].strip()
        if len(nome) > 2:
            return nome
    # Formato "EMPRESA X LTDA., ..., doravante denominada CONTRATANTE"
    for achado in re.finditer(rf"(?:doravante|simplesmente) (?:denominad|designad|chamad)[ao]s?"
                              rf"(?: apenas| simplesmente)?\s*[\"“']?{papel}", norm):
        anterior = texto[max(0, achado.start() - 400):achado.start()]
        candidatos = re.findall(r"([A-ZÁ-Ú][A-ZÁ-Ú0-9&\.\- ]{3,80}(?:LTDA|S\.?A|ME|EIRELI|EPP)?\.?)\s*,",
                                anterior)
        if candidatos:
            return candidatos[-1].strip()
    return None


# Papéis equivalentes em outros tipos de contrato (compra e venda, locação etc.)
PAPEIS_CONTRATANTE = ["contratante", "compradora?", "promitente compradora?", "locataria?", "cessionaria?"]
PAPEIS_CONTRATADA = ["contratada", "vendedora?", "promitente vendedora?", "locadora?", "cedente"]


def _primeira_parte(texto, norm, papeis):
    for papel in papeis:
        nome = _nome_parte(texto, norm, papel)
        if nome:
            return nome
    return None


def montar_resumo(texto, norm, segmentos, encontradas):
    def segmento_titulo(padrao):
        for seg in segmentos:
            if re.search(padrao, normalizar(seg.titulo)):
                return seg
        return None

    seg_objeto = segmento_titulo(r"objeto")
    objeto = _texto_segmento(texto, seg_objeto, 350) if seg_objeto else \
        _primeira_frase(texto, norm, r"tem (?:como|por) objeto|o presente contrato tem")

    valor = None
    seg_valor = segmento_titulo(r"valor|preco|remuneracao|pagamento")
    if seg_valor:
        valor = _primeira_frase(texto, norm, r"r\$\s*\d", seg_valor.inicio, seg_valor.fim)
    valor = valor or _primeira_frase(texto, norm, r"r\$\s*\d")

    pagamento = None
    if seg_valor:
        pagamento = _primeira_frase(texto, norm, r"pagamento (?:sera|devera|deve|ocorrera)"
                                                 r"|sera pag[oa]|serao pag[oa]s|em parcelas",
                                    seg_valor.inicio, seg_valor.fim)

    vigencia = None
    if encontradas["prazo"]:
        seg = encontradas["prazo"][0][2]
        vigencia = _primeira_frase(texto, norm, r"vigencia|vigorara|prazo de|prazo indeterminado",
                                   seg.inicio, seg.fim)

    foro = _primeira_frase(texto, norm, r"\bforo\b")
    datas = list(re.finditer(rf"\d{{1,2}}\s+de\s+(?:{MESES})\s+de\s+\d{{4}}", norm))
    data = _uma_linha(texto[datas[-1].start():datas[-1].end()]) if datas else None

    # Título: primeiro bloco de linhas em caixa alta que cite o tipo de instrumento
    titulo_contrato = None
    linhas = [l for l in texto.split("\n")[:8]]
    for i, linha in enumerate(linhas):
        if re.search(r"contrato|instrumento|compromisso|termo|acordo", normalizar(linha)):
            partes = [linha]
            for seguinte in linhas[i + 1:i + 3]:
                if seguinte.strip() and _eh_maiuscula(seguinte) and not re.search(r"ficticio", normalizar(seguinte)):
                    partes.append(seguinte)
                else:
                    break
            titulo_contrato = _uma_linha(" ".join(partes))[:200]
            break

    return {
        "titulo": titulo_contrato,
        "contratante": _primeira_parte(texto, norm, PAPEIS_CONTRATANTE),
        "contratada": _primeira_parte(texto, norm, PAPEIS_CONTRATADA),
        "objeto": objeto,
        "valor": valor,
        "pagamento": pagamento,
        "vigencia": vigencia,
        "foro": foro,
        "data_assinatura": data,
        "estrutura": [s.titulo for s in segmentos if s.titulo != "Preâmbulo"],
    }


# ---------------------------------------------------------------------------
# Classificação de risco
# ---------------------------------------------------------------------------
def classificar(pontos: list[Ponto], texto_insuficiente: bool):
    contagem = {s: 0 for s in regras.ORDEM_SEVERIDADE}
    for ponto in pontos:
        contagem[ponto.severidade] += 1
    pontuacao = sum(regras.SEVERIDADES[p.severidade] for p in pontos)

    motivos = []
    if contagem["Crítica"] or pontuacao >= regras.LIMITE_CRITICO:
        nivel = "Crítico"
        if contagem["Crítica"]:
            motivos.append(f"{contagem['Crítica']} ponto(s) de severidade crítica.")
        if pontuacao >= regras.LIMITE_CRITICO:
            motivos.append(f"Pontuação {pontuacao} ≥ {regras.LIMITE_CRITICO}.")
    elif pontuacao >= regras.LIMITE_ALTO or contagem["Alta"] >= regras.MIN_ALTAS_PARA_ALTO:
        nivel = "Alto"
        if pontuacao >= regras.LIMITE_ALTO:
            motivos.append(f"Pontuação {pontuacao} ≥ {regras.LIMITE_ALTO}.")
        if contagem["Alta"] >= regras.MIN_ALTAS_PARA_ALTO:
            motivos.append(f"{contagem['Alta']} pontos de severidade alta.")
    elif pontuacao >= regras.LIMITE_MEDIO:
        nivel = "Médio"
        motivos.append(f"Pontuação {pontuacao} entre {regras.LIMITE_MEDIO} e {regras.LIMITE_ALTO - 1}.")
    else:
        nivel = "Baixo"
        motivos.append(f"Pontuação {pontuacao} abaixo de {regras.LIMITE_MEDIO}.")

    revisao = nivel in regras.NIVEIS_COM_REVISAO
    if texto_insuficiente:
        revisao = True
        motivos.append("Pouco texto extraído (possível PDF escaneado): leitura humana obrigatória.")

    return {
        "nivel": nivel,
        "pontuacao": pontuacao,
        "contagem": contagem,
        "revisao_humana": revisao,
        "motivos": motivos,
    }


# ---------------------------------------------------------------------------
# Função principal
# ---------------------------------------------------------------------------
def analisar_contrato(texto: str, paginas: int = 0) -> dict:
    norm = normalizar(texto)
    segmentos = segmentar(texto, norm)
    # Depois de segmentar, as quebras de linha viram espaços para que expressões
    # partidas pelo PDF ("exclusivo\ncritério") também sejam encontradas.
    # O tamanho do texto não muda, então as posições continuam válidas.
    norm = norm.replace("\n", " ")
    encontradas = identificar_clausulas(texto, norm, segmentos)

    clausulas = []
    for chave, definicao in regras.CLAUSULAS.items():
        candidatos = encontradas[chave]
        if candidatos:
            _, no_titulo, seg = candidatos[0]
            clausulas.append({
                "chave": chave, "nome": definicao["nome"], "identificada": True,
                "confianca": "Alta" if no_titulo else "Média",
                "referencia": _referencia(seg),
                "trecho": _texto_segmento(texto, seg),
            })
        else:
            clausulas.append({"chave": chave, "nome": definicao["nome"], "identificada": False,
                              "confianca": None, "referencia": None, "trecho": None})

    pontos = aplicar_regras_padrao(texto, norm, segmentos, encontradas)
    pontos += aplicar_regras_numericas(texto, norm, segmentos, encontradas)
    ausentes = verificar_ausencias(texto, norm, encontradas)

    texto_insuficiente = len(texto) < regras.MIN_CARACTERES_TEXTO
    if texto_insuficiente:
        ausentes.append(Ponto("documento", "Texto insuficiente",
                              "O arquivo tem pouco texto legível. Pode ser um PDF escaneado.",
                              "Alta", "", "Arquivo", "Enviar versão com texto selecionável."))

    ordem = {s: i for i, s in enumerate(regras.ORDEM_SEVERIDADE)}
    pontos.sort(key=lambda p: ordem[p.severidade])
    ausentes.sort(key=lambda p: ordem[p.severidade])

    return {
        "versao_regras": regras.VERSAO_REGRAS,
        "estatisticas": {
            "caracteres": len(texto),
            "palavras": len(texto.split()),
            "paginas": paginas,
            "blocos": len(segmentos),
        },
        "clausulas": clausulas,
        "pontos_atencao": [asdict(p) for p in pontos],
        "informacoes_ausentes": [asdict(p) for p in ausentes],
        "resumo": montar_resumo(texto, norm, segmentos, encontradas),
        "classificacao": classificar(pontos + ausentes, texto_insuficiente),
    }
