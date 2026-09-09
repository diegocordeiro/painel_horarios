"""Mapa de nomes de curso (como vêm do CSV do FET) para a posição de exibição.

Usado no momento da importação (import_timetable) para ordenar os cursos criados
a partir do CSV. Inclui as variações de nomes que aparecem no CSV e as abreviações
usadas no JS. Não é usado para semear metadados.
"""

COURSE_POSITIONS = {
    "tec_em_administracao_integrado": 1,
    "tecnico_integrado_em_administracao_integrado": 1,
    "tecnico_em_administracao_integrado": 1,
    "tec_em_eventos_integrado": 2,
    "tecnico_integrado_em_eventos_integrado": 2,
    "tecnico_em_eventos_integrado": 2,
    "tec_em_informatica_integrado": 3,
    "tecnico_integrado_em_informatica_integrado": 3,
    "tecnico_em_informatica_integrado": 3,
    "tec_em_administracao_subsequente": 4,
    "tecnico_em_administracao_subsequente": 4,
    "tec_em_guia_de_turismo_subsequente": 5,
    "tecnico_em_guia_de_turismo_subsequente": 5,
    "tec_gastronomia": 6,
    "tecnico_em_gastronomia_subsequente": 6,
    "tec_gastronomia_proeja": 7,
    "tecnico_em_gastronomia_proeja": 7,
    "lic_em_matematica": 8,
    "licenciatura_em_matematica": 8,
    "lic_em_fisica": 9,
    "licenciatura_em_fisica": 9,
    "tecnologia_em_sistemas_para_internet": 10,
    "sistemas_para_internet": 10,
    "tecnologia_em_gastronomia": 11,
    "tecnico_em_servico_de_restaurante_e_bar_subsequente": 12,
}
