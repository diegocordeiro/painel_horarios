"""Cursos do campus: metadados de coordenação e PPCs.

Usado pelo management command `seed_cursos` para manter os dados versionados
e reproduzíveis no CI (o banco é recriado a cada deploy).

A chave é `nome` (igual ao que o `import_timetable` deriva do CSV). Cada item
de `ppcs` tem `file` (arquivo dentro de media/attachments/) e `label` (texto do
link). Preencha coordenador/email/lattes/carga_horaria/duracao/modalidade com os
dados reais do curso.
"""

CURSOS = [
    {
        "nome": "PEDAGOGIA",
        "tipo": "Licenciatura",
        "modalidade": "Presencial",
        "turno": "NOITE",
        "carga_horaria": "",
        "duracao": "",
        "coordenador": "",
        "email": "",
        "lattes": "",
        "posicao": 1,
        "ppcs": [],
    },
    {
        "nome": "TÉCNICO EM ADMINISTRAÇÃO PROEJA",
        "tipo": "Técnico (PROEJA)",
        "modalidade": "Presencial",
        "turno": "NOITE",
        "carga_horaria": "2.400 horas.",
        "duracao": "Mínima: 03 (três) anos e Máxima: 06 (seis) anos.",
        "coordenador": "",
        "email": "",
        "lattes": "",
        "posicao": 2,
        "ppcs": [
            {
                "file": "ppc_administracao_proeja_2023.pdf",
                "label": "PPC Administração PROEJA 2023",
            },
        ],
    },
    {
        "nome": "TÉCNICO SUBSEQUENTE EM MEIO AMBIENTE",
        "tipo": "Técnico Subsequente",
        "modalidade": "Presencial",
        "turno": "NOITE",
        "carga_horaria": "1.200 horas. ",
        "duracao": "3 semestres ",
        "coordenador": "",
        "email": "",
        "lattes": "",
        "posicao": 3,
        "ppcs": [
            {
                "file": "ppc_meio_ambiente_concomitante_subsequente_2026.pdf",
                "label": "PPC Meio Ambiente 2026",
            },
        ],
    },
]
