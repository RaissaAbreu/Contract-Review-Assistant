"""
Regras de classificação do Contract Review Assistant.

Todos os padrões são escritos em minúsculas e SEM acentos, porque a busca é
feita sobre uma versão normalizada do texto (ver analisador.normalizar).
Para ajustar o comportamento da ferramenta, edite apenas este arquivo.
"""

VERSAO_REGRAS = "1.0"

# ---------------------------------------------------------------------------
# Severidades e pontuação
# ---------------------------------------------------------------------------
SEVERIDADES = {
    "Baixa": 1,
    "Média": 3,
    "Alta": 6,
    "Crítica": 15,
}

# Ordem usada para ordenar os pontos (mais grave primeiro)
ORDEM_SEVERIDADE = ["Crítica", "Alta", "Média", "Baixa"]

# Faixas de classificação final.
# - Crítico: existe ao menos um ponto "Crítica" OU pontuação >= LIMITE_CRITICO
# - Alto:    pontuação >= LIMITE_ALTO OU ao menos MIN_ALTAS_PARA_ALTO pontos "Alta"
# - Médio:   pontuação >= LIMITE_MEDIO
# - Baixo:   demais casos
LIMITE_CRITICO = 40
LIMITE_ALTO = 20
MIN_ALTAS_PARA_ALTO = 2
LIMITE_MEDIO = 8

# Níveis que exigem revisão humana
NIVEIS_COM_REVISAO = {"Alto", "Crítico"}

# Abaixo deste número de caracteres o texto é considerado insuficiente
# (ex.: PDF escaneado sem camada de texto) e a revisão humana é obrigatória.
MIN_CARACTERES_TEXTO = 400

# ---------------------------------------------------------------------------
# Cláusulas que a ferramenta procura
# - titulo: padrões procurados no título/início da cláusula (peso alto)
# - termos: padrões procurados no corpo da cláusula
# - ausencia: (severidade, recomendação) quando a cláusula não é encontrada
# ---------------------------------------------------------------------------
CLAUSULAS = {
    "rescisao": {
        "nome": "Rescisão",
        "titulo": [r"rescis", r"resilic", r"extincao", r"encerramento do contrato"],
        "termos": [r"rescis", r"rescind", r"resili", r"denuncia", r"aviso previo",
                   r"extincao do contrato"],
        "ausencia": ("Alta", "Incluir cláusula de rescisão com hipóteses, aviso prévio "
                             "e efeitos do encerramento."),
    },
    "multa": {
        "nome": "Multa",
        "titulo": [r"\bmultas?\b", r"penalidade", r"sancoes", r"clausula penal"],
        "termos": [r"\bmultas?\b", r"penalidade", r"clausula penal", r"juros de mora",
                   r"sancao"],
        "ausencia": ("Média", "Incluir multa por descumprimento com percentual e base de "
                              "cálculo definidos."),
    },
    "responsabilidade": {
        "nome": "Responsabilidade",
        "titulo": [r"responsabilidade", r"indenizac"],
        "termos": [r"responsabilidade", r"responsabiliza", r"indeniz", r"perdas e danos",
                   r"lucros cessantes", r"danos diretos", r"danos indiretos"],
        "ausencia": ("Alta", "Incluir cláusula de responsabilidade com limite de "
                             "indenização e exclusões (danos indiretos, lucros cessantes)."),
    },
    "confidencialidade": {
        "nome": "Confidencialidade",
        "titulo": [r"confidencial", r"sigilo"],
        "termos": [r"confidencia", r"sigilo", r"informacoes confidenciais",
                   r"nao divulga"],
        "ausencia": ("Média", "Incluir cláusula de confidencialidade com definição de "
                              "informação confidencial, exceções e prazo."),
    },
    "protecao_dados": {
        "nome": "Proteção de dados",
        "titulo": [r"protecao de dados", r"dados pessoais", r"\blgpd\b", r"privacidade"],
        "termos": [r"dados pessoais", r"\blgpd\b", r"13\.709", r"protecao de dados",
                   r"tratamento de dados", r"titulares? dos dados", r"\bcontrolador",
                   r"\boperador"],
        "ausencia": ("Alta", "Incluir cláusula de proteção de dados conforme a LGPD "
                             "(Lei 13.709/2018): papéis, finalidade, segurança e incidentes."),
    },
    "prazo": {
        "nome": "Prazo e vigência",
        "titulo": [r"\bprazo\b(?! de pagamento)", r"vigencia", r"duracao"],
        "termos": [r"vigencia", r"vigorara", r"duracao do contrato", r"prazo determinado",
                   r"prazo indeterminado", r"renovac", r"renovad"],
        "ausencia": ("Alta", "Incluir cláusula de prazo com início, término e regras de "
                             "renovação."),
    },
}

# ---------------------------------------------------------------------------
# Pontos de atenção baseados em padrões de texto.
# escopo:
#   - chave de uma cláusula: busca apenas dentro dela
#   - "texto": busca no contrato inteiro
# ---------------------------------------------------------------------------
REGRAS_PADRAO = [
    # Rescisão
    {
        "categoria": "rescisao", "escopo": "rescisao", "severidade": "Alta",
        "padrao": r"sem (?:a )?(?:necessidade de )?(?:qualquer )?aviso previo"
                  r"|independentemente de (?:qualquer )?(?:aviso|notificacao)"
                  r"|imediatamente,? sem (?:qualquer )?(?:aviso|notificacao)",
        "titulo": "Rescisão sem aviso prévio",
        "descricao": "O contrato permite o encerramento imediato, sem aviso prévio.",
        "recomendacao": "Prever aviso prévio mínimo (ex.: 30 dias) para rescisão imotivada.",
    },
    {
        "categoria": "rescisao", "escopo": "rescisao", "severidade": "Alta",
        "padrao": r"(?:somente|apenas|exclusivamente) (?:a|pela) contratante (?:podera|tera)",
        "titulo": "Direito de rescisão unilateral",
        "descricao": "Apenas uma das partes pode rescindir o contrato.",
        "recomendacao": "Garantir reciprocidade no direito de rescisão.",
    },
    {
        "categoria": "rescisao", "escopo": "rescisao", "severidade": "Média",
        "padrao": r"a (?:seu )?exclusivo criterio",
        "titulo": "Rescisão a exclusivo critério de uma parte",
        "descricao": "A rescisão depende do exclusivo critério de uma das partes.",
        "recomendacao": "Verificar reciprocidade e prever compensação pelos serviços prestados.",
    },
    # Multa
    {
        "categoria": "multa", "escopo": "multa", "severidade": "Média",
        "padrao": r"multa[^.]{0,120}(?:valor (?:total|global) do contrato|valor global)",
        "titulo": "Multa calculada sobre o valor total do contrato",
        "descricao": "A base de cálculo da multa é o valor total, e não a parcela inadimplida.",
        "recomendacao": "Avaliar multa proporcional à obrigação descumprida ou ao período restante.",
    },
    {
        "categoria": "multa", "escopo": "multa", "severidade": "Baixa",
        "padrao": r"sem prejuizo (?:de|das?) (?:eventuais )?perdas e danos|cumulativ",
        "titulo": "Multa cumulativa com perdas e danos",
        "descricao": "A multa não exclui a cobrança de indenização adicional.",
        "recomendacao": "Confirmar se a multa deve ser compensatória (teto) ou cumulativa.",
    },
    # Responsabilidade
    {
        "categoria": "responsabilidade", "escopo": "texto", "severidade": "Crítica",
        "padrao": r"responsabilidade (?:sera )?(?:integral e )?ilimitada"
                  r"|sem qualquer limit(?:e|acao) (?:de|a) (?:valor|responsabilidade)"
                  r"|ilimitadamente responsavel",
        "titulo": "Responsabilidade ilimitada",
        "descricao": "Uma das partes assume responsabilidade sem qualquer teto de indenização.",
        "recomendacao": "Limitar a responsabilidade (ex.: ao valor pago nos últimos 12 meses).",
    },
    {
        "categoria": "responsabilidade", "escopo": "texto", "severidade": "Alta",
        "padrao": r"(?:nao se responsabiliza|isenta de (?:qualquer|toda) responsabilidade"
                  r"|nao respondera)[^.]{0,40}(?:qualquer|quaisquer|nenhum|hipotese)",
        "titulo": "Exclusão ampla de responsabilidade",
        "descricao": "Uma das partes se exime de responsabilidade de forma genérica.",
        "recomendacao": "Restringir a exclusão a hipóteses específicas; dolo e culpa grave "
                        "não podem ser excluídos.",
    },
    {
        "categoria": "responsabilidade", "escopo": "responsabilidade", "severidade": "Média",
        "padrao": r"(?:inclusive|incluindo|bem como)[^.]{0,40}(?:lucros cessantes|danos indiretos)",
        "titulo": "Responsabilidade por danos indiretos",
        "descricao": "A indenização inclui lucros cessantes ou danos indiretos.",
        "recomendacao": "Avaliar a exclusão de danos indiretos e lucros cessantes.",
    },
    # Confidencialidade
    {
        "categoria": "confidencialidade", "escopo": "confidencialidade", "severidade": "Média",
        "padrao": r"perpetu|por prazo indeterminado|indefinidamente|para sempre",
        "titulo": "Sigilo por prazo indeterminado",
        "descricao": "A obrigação de confidencialidade não tem prazo final.",
        "recomendacao": "Definir prazo de sigilo após o término (ex.: 5 anos).",
    },
    # Proteção de dados
    {
        "categoria": "protecao_dados", "escopo": "texto", "severidade": "Média",
        "padrao": r"transferencia internacional|fora do (?:brasil|territorio nacional)",
        "titulo": "Transferência internacional de dados",
        "descricao": "O contrato prevê tratamento de dados fora do Brasil.",
        "recomendacao": "Verificar a base legal da transferência (art. 33 da LGPD).",
    },
    # Prazo
    {
        "categoria": "prazo", "escopo": "prazo", "severidade": "Média",
        "padrao": r"renovad[oa]s? automaticamente|renovacao automatica|renovar-se-a"
                  r"|prorrogad[oa]s? automaticamente|prorrogacao automatica",
        "titulo": "Renovação automática",
        "descricao": "O contrato se renova sem manifestação expressa das partes.",
        "recomendacao": "Controlar a data de renovação ou exigir aditivo para prorrogar.",
    },
    {
        "categoria": "prazo", "escopo": "prazo", "severidade": "Média",
        "padrao": r"prazo indeterminado",
        "titulo": "Contrato por prazo indeterminado",
        "descricao": "O contrato não tem data de término definida.",
        "recomendacao": "Confirmar se o prazo indeterminado é intencional e prever saída.",
    },
    # Gerais
    {
        "categoria": "geral", "escopo": "texto", "severidade": "Alta",
        "padrao": r"renuncia[^.]{0,60}(?:a qualquer|a todo|aos? direitos?|de qualquer)",
        "titulo": "Renúncia de direitos",
        "descricao": "Uma das partes renuncia antecipadamente a direitos.",
        "recomendacao": "Avaliar a validade e o alcance da renúncia.",
    },
    {
        "categoria": "geral", "escopo": "texto", "severidade": "Média",
        "padrao": r"\bexclusividade\b",
        "titulo": "Cláusula de exclusividade",
        "descricao": "O contrato impõe exclusividade a uma das partes.",
        "recomendacao": "Verificar escopo, prazo e contrapartida da exclusividade.",
    },
    {
        "categoria": "geral", "escopo": "texto", "severidade": "Média",
        "padrao": r"ced(?:er|ido)[^.]{0,80}sem (?:a )?(?:previa )?(?:anuencia|consentimento|autorizacao)",
        "ignorar_se_negado": True,
        "titulo": "Cessão sem anuência",
        "descricao": "O contrato pode ser cedido a terceiros sem concordância da outra parte.",
        "recomendacao": "Exigir anuência prévia e por escrito para cessão.",
    },
    {
        "categoria": "geral", "escopo": "texto", "severidade": "Média",
        "padrao": r"\[[^\]\n]{0,25}\]|r\$\s*_{2,}|\bx{3,}\b|\(\s*_+\s*\)",
        "titulo": "Campo não preenchido",
        "descricao": "Há trechos com marcadores ou lacunas a preencher.",
        "recomendacao": "Preencher todos os campos antes da assinatura.",
    },
]

# Limites usados pelas regras numéricas (analisador.py)
MULTA_PERCENTUAL_MEDIA = 10   # acima disso: severidade Média
MULTA_PERCENTUAL_ALTA = 20    # acima disso: severidade Alta
AVISO_PREVIO_MINIMO_DIAS = 30  # abaixo disso: severidade Média

# ---------------------------------------------------------------------------
# Dados das partes
# ---------------------------------------------------------------------------
PADRAO_CNPJ = r"\b\d{2}\.?\d{3}\.?\d{3}/?\d{4}-?\d{2}\b"
PADRAO_CPF = r"\b\d{3}\.\d{3}\.\d{3}-\d{2}\b"
PADRAO_ENDERECO = r"com sede|sediad[ao]|domiciliad[ao]|residente|endereco"
PADRAO_REPRESENTANTE = r"representad[ao]|neste ato"
PADRAO_ASSINATURA = r"assinatura|assinam|firmam|_{5,}"
PADRAO_TESTEMUNHAS = r"testemunha"

NOMES_CATEGORIAS = {
    **{chave: dados["nome"] for chave, dados in CLAUSULAS.items()},
    "partes": "Dados das partes",
    "geral": "Geral",
    "documento": "Documento",
}
