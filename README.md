# Contract Review Assistant

Análise automatizada de contratos com Python, Streamlit, PyMuPDF, regras de classificação e integração opcional com a OpenAI.

A ferramenta recebe um contrato (PDF, TXT ou DOCX), extrai o texto e:

- identifica as cláusulas de **rescisão, multa, responsabilidade, confidencialidade, proteção de dados e prazo**;
- monta um **resumo esquematizado**: partes, objeto, valor, pagamento, vigência, foro, data e estrutura;
- lista os **pontos de atenção** com o **trecho analisado**, a cláusula de origem e uma recomendação;
- aponta **informações ausentes**: cláusulas do escopo e dados das partes (CNPJ/CPF, endereço, representante, assinaturas e testemunhas);
- calcula a **classificação de risco** (Baixo / Médio / Alto / Crítico) e indica se a **revisão humana** é necessária;
- registra a **revisão jurídica**: advogado, decisão e observações;
- gera um **parecer complementar da IA** sob demanda, pelo botão "Analisar com IA";
- exporta o relatório em **PDF** e **DOCX**;
- guarda todas as análises em **SQLite**, com histórico e consulta detalhada.

> Ferramenta de apoio. Ela não substitui a análise de um advogado.

## Estrutura

```
contract-review-assistant/
├── app.py                    # Interface Streamlit (4 seções na barra lateral)
├── core/
│   ├── extracao.py           # Leitura de PDF (PyMuPDF), DOCX e TXT
│   ├── regras.py             # TODAS as regras, pesos e limites (edite aqui)
│   ├── analisador.py         # Segmentação, identificação, pontos, resumo e risco
│   ├── llm.py                # Integração opcional com a OpenAI
│   ├── banco.py              # Persistência em SQLite (data/analises.db)
│   └── relatorio.py          # Exportação PDF e DOCX
├── ui/
│   ├── estilo.py             # Identidade visual (CSS)
│   └── componentes.py        # Blocos de interface reutilizáveis
├── demo/
│   ├── contrato_01_risco_baixo.(txt|pdf|docx)
│   ├── contrato_02_risco_medio.(txt|pdf|docx)
│   ├── contrato_03_risco_critico.(txt|pdf|docx)
│   ├── contrato_04_compra_venda_imovel_risco_alto.(txt|pdf|docx)
│   └── gerar_contratos_demo.py   # Regera PDF/DOCX a partir dos TXT
├── data/                     # Banco SQLite (criado automaticamente)
├── .streamlit/config.toml    # Tema claro e limite de upload (20 MB)
├── .env.example
└── requirements.txt
```

## Instalação

Requer Python 3.10 ou superior.

```bash
python -m venv .venv
```

```bash
source .venv/bin/activate
```

No Windows, use `.venv\Scripts\activate` no lugar do comando acima.

```bash
pip install -r requirements.txt
```

```bash
cp .env.example .env
```

Abra o `.env` e preencha `OPENAI_API_KEY`. Sem a chave, o app funciona normalmente e só o botão "Analisar com IA" fica desabilitado. `OPENAI_MODEL` define o modelo padrão, que também pode ser trocado na barra lateral.

## Execução

```bash
streamlit run app.py
```

## Seções

| Seção | O que faz |
|---|---|
| **Nova análise** | Upload do arquivo ou escolha de um contrato de demonstração, prévia do texto extraído e botão "Analisar contrato". |
| **Resultado da análise** | Classificação final, exportação PDF/DOCX e abas: resumo, cláusulas, pontos de atenção, informações ausentes, parecer da IA e texto extraído. |
| **Revisão jurídica** | Contadores por status, análises aguardando revisão e formulário de decisão (Aprovado / Aprovado com ressalvas / Reprovado). |
| **Histórico** | Tabela com filtros, consulta detalhada e exclusão. |

## Como funciona a classificação

1. O texto é normalizado (minúsculas, sem acentos) **sem mudar de tamanho**. Assim, cada ocorrência encontrada aponta para o trecho original.
2. O contrato é dividido em blocos pelos títulos ("CLÁUSULA X", linhas numeradas ou em caixa alta).
3. Uma cláusula é identificada quando o **título** contém um padrão da categoria (confiança alta) ou quando o **corpo** contém dois ou mais termos dela (confiança média).
4. As regras de `core/regras.py` geram pontos com severidade e pontuação:

| Severidade | Pontos |
|---|---|
| Baixa | 1 |
| Média | 3 |
| Alta | 6 |
| Crítica | 15 |

5. A classificação final segue estas faixas:

| Nível | Critério | Revisão humana |
|---|---|---|
| **Crítico** | algum ponto Crítico **ou** pontuação ≥ 40 | Sim |
| **Alto** | pontuação ≥ 20 **ou** 2 ou mais pontos Altos | Sim |
| **Médio** | pontuação ≥ 8 | Não |
| **Baixo** | demais casos | Não |

Se o arquivo tiver menos de 400 caracteres de texto (por exemplo, um PDF escaneado), a revisão humana passa a ser obrigatória.

Todos os limites, pesos e padrões ficam em `core/regras.py`.

## Integração com a OpenAI

O botão **Analisar com IA** envia ao modelo o texto do contrato e o resultado das regras, e recebe um JSON com:

- resumo executivo;
- pontos adicionais com o trecho citado;
- divergências em relação às regras;
- nível de risco sugerido e justificativa;
- recomendações.

O parecer **não altera** a classificação das regras. Ele aparece separado, indica se o nível sugerido coincide com o das regras e **confere se cada trecho citado existe de fato no contrato**. Trechos não encontrados recebem o aviso "Trecho não localizado no contrato".

Contratos com mais de 60.000 caracteres são truncados antes do envio, e o parecer avisa quando isso acontece.

## Roteiro de demonstração

1. Em **Nova análise**, escolha "Usar contrato de demonstração" e selecione `contrato_03_risco_critico.pdf`.
2. Abra **Pré-visualizar texto extraído** para mostrar a extração feita pelo PyMuPDF.
3. Clique em **Analisar contrato**. O resultado é **Crítico**, com revisão humana necessária.
4. Na aba **Cláusulas**, 4 de 6 são identificadas; proteção de dados e prazo não existem no contrato.
5. Em **Pontos de atenção**, mostre a responsabilidade ilimitada, a rescisão unilateral sem aviso prévio, a multa de 30% sobre o valor total, o sigilo perpétuo e os campos não preenchidos `[•]`, cada um com o trecho analisado.
6. Em **Informações ausentes**, mostre a falta de cláusula LGPD, de vigência, de assinaturas e o CNPJ da contratada.
7. Se a chave estiver configurada, clique em **Analisar com IA**. A IA aponta, por exemplo, o tratamento de dados de clientes sem cláusula de proteção de dados.
8. Baixe o relatório em PDF ou DOCX.
9. Em **Revisão jurídica**, registre a decisão do advogado.
10. Para comparar, analise `contrato_01_risco_baixo` (Baixo, sem pontos) e `contrato_02_risco_medio` (Médio: renovação automática, multa de 15%, aviso prévio de 15 dias etc.).

Resultados esperados (iguais para TXT, PDF e DOCX):

| Contrato | Nível | Pontuação |
|---|---|---|
| 01 — risco baixo | Baixo | 0 |
| 02 — risco médio | Médio | 15 |
| 03 — risco crítico | Crítico | 91 |
| 04 — compra e venda de imóvel (R$ 9,8 mi) | Alto | 31 |

Todos os contratos, empresas, CNPJs e pessoas dos arquivos de demonstração são **fictícios**.
