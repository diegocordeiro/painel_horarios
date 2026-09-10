"""Agrega a carga horária dos professores por turma, curso e área.

A **carga horária** de um professor é a soma das durações
(``hora_fim - hora_inicio``) dos blocos de aula a ele atribuídos na versão do
quadro. O **nº de aulas** é a contagem desses blocos. O agrupamento por
**área** usa o ``tipo`` do curso (``Curso.tipo``), com fallback para
"Não classificado" quando o curso ainda não tem tipo definido.

O bloco conta **uma única vez** no total do professor (evita inflar o total em
casos de co-docência), mas aparece em cada turma/curso/área a que estiver
vinculado — é isso que permite ler a carga "com base no número de aulas por
turma" de cada docente.

Compartilhado entre as views de preview (``runserver``) e o gerador de site
estático, garantindo o mesmo resultado em ``/carga-horaria/`` e em
``/versoes/<versao>/carga-horaria/``.
"""
from __future__ import annotations

import unicodedata

from .fet import minutes_from_hhmm

AREA_NAO_CLASSIFICADA = "Não classificado"


def fmt_minutes(total) -> str:
    """Formata minutos como HH:MM (ex.: 900 -> '15:00')."""
    total = int(total or 0)
    return f"{total // 60:02d}:{total % 60:02d}"


def sort_key(nome) -> str:
    """Chave de ordenação alfabética pt-BR (ignora acentos e caixa)."""
    normalized = unicodedata.normalize("NFKD", str(nome or ""))
    return "".join(c for c in normalized if not unicodedata.combining(c)).casefold().strip()


def modalidade_of(curso) -> str:
    """Modalidade do curso = seu tipo (com fallback para 'Não classificado')."""
    tipo = (getattr(curso, "tipo", "") or "").strip()
    return tipo or AREA_NAO_CLASSIFICADA


def aula_minutes(aula) -> int:
    """Duração do bloco em minutos (fallback de 60 min se o horário for inválido)."""
    start = minutes_from_hhmm(aula.hora_inicio)
    end = minutes_from_hhmm(aula.hora_fim)
    if start is None or end is None or end <= start:
        return 60
    return end - start


def faixa_referencia():
    from django.conf import settings
    lo = int(getattr(settings, "CARGA_HORARIA_MINIMA_HORAS", 10)) * 60
    hi = int(getattr(settings, "CARGA_HORARIA_MAXIMA_HORAS", 20)) * 60
    return lo, hi


def _status_info(minutos):
    lo, hi = faixa_referencia()
    if minutos < lo:
        return {"status": "abaixo", "status_texto": "abaixo do mínimo"}
    if minutos > hi:
        return {"status": "acima", "status_texto": "acima do máximo"}
    return {"status": "dentro", "status_texto": "na faixa"}


def _pct(minutos: int, referencia: int) -> str:
    """Percentual como texto com ponto decimal (ex.: '66.7').

    Formata em Python (fora da localização de templates) para garantir que o CSS
    receba ``width: 66.7%`` em vez de ``66,7%`` (que quebraria a barra).
    """
    if not referencia:
        return "0"
    valor = round(minutos * 100 / referencia, 1)
    texto = f"{valor:.1f}".rstrip("0").rstrip(".")
    return texto or "0"


def _linha_professor(prof: dict, bucket: dict, referencia: int) -> dict:
    """Linha compacta de um professor dentro de um grupo (modalidade/curso)."""
    return {
        "nome": prof["nome"],
        "slug": prof["slug"],
        "color": prof["color"],
        "total_min": bucket["min"],
        "total_hhmm": fmt_minutes(bucket["min"]),
        "blocos": bucket["blocos"],
        "pct": _pct(bucket["min"], referencia),
        **_status_info(bucket["min"]),
    }


def tipo_slug_modalidade(modalidade: str) -> str:
    """Slug CSS da modalidade (reaproveita o mapa de tipos dos cursos)."""
    from .static_site import tipo_slug

    return tipo_slug(modalidade)


def build_carga_horaria(aulas) -> dict:
    """Calcula a estrutura do dashboard de carga horária a partir das aulas.

    ``aulas`` é uma lista/queryset de ``Aula`` com ``professores`` e
    ``turmas__curso`` já resolvidos (prefetch) para evitar N+1.
    """
    # Import tardio: evita ciclo de import com static_site (que importa este módulo).
    from .static_site import entity_color

    professores: dict[int, dict] = {}
    areas: dict[str, dict] = {}
    cursos: dict[int, dict] = {}

    geral_min = 0
    geral_blocos = 0
    turmas_ids: set[int] = set()

    for aula in aulas:
        minutos = aula_minutes(aula)
        geral_min += minutos
        geral_blocos += 1

        turmas = list(aula.turmas.all())
        for turma in turmas:
            turmas_ids.add(turma.id)

        cursos_aula = {t.curso_id: t.curso for t in turmas}
        modalidades_aula = {modalidade_of(t.curso) for t in turmas}

        # Totais por curso/modalidade: o bloco conta uma vez por nível distinto.
        for curso_id, curso in cursos_aula.items():
            info = cursos.setdefault(
                curso_id, {"obj": curso, "min": 0, "blocos": 0, "prof_ids": set()}
            )
            info["min"] += minutos
            info["blocos"] += 1
        for modalidade in modalidades_aula:
            info = areas.setdefault(modalidade, {"min": 0, "blocos": 0, "prof_ids": set()})
            info["min"] += minutos
            info["blocos"] += 1

        for professor in aula.professores.all():
            prof = professores.get(professor.id)
            if prof is None:
                prof = {
                    "nome": professor.nome,
                    "slug": professor.slug,
                    "color": entity_color(professor.nome),
                    "total_min": 0,
                    "blocos": 0,
                    "_areas": {},
                    "_cursos": {},
                    "_turmas": {},
                }
                professores[professor.id] = prof

            prof["total_min"] += minutos
            prof["blocos"] += 1

            for turma in turmas:
                bucket = prof["_turmas"].setdefault(
                    turma.id, {"obj": turma, "min": 0, "blocos": 0}
                )
                bucket["min"] += minutos
                bucket["blocos"] += 1

            for curso_id, curso in cursos_aula.items():
                bucket = prof["_cursos"].setdefault(
                    curso_id, {"obj": curso, "min": 0, "blocos": 0}
                )
                bucket["min"] += minutos
                bucket["blocos"] += 1
                cursos[curso_id]["prof_ids"].add(professor.id)

            for modalidade in modalidades_aula:
                bucket = prof["_areas"].setdefault(modalidade, {"min": 0, "blocos": 0})
                bucket["min"] += minutos
                bucket["blocos"] += 1
                areas[modalidade]["prof_ids"].add(professor.id)

    min_ref, max_ref = faixa_referencia()
    max_min = max_ref

    lista_professores = []
    for prof in professores.values():
        lista_areas = sorted(
            (
                {
                    "nome": modalidade,
                    "slug": tipo_slug_modalidade(modalidade),
                    "total_min": bucket["min"],
                    "total_hhmm": fmt_minutes(bucket["min"]),
                    "blocos": bucket["blocos"],
                    "pct": _pct(bucket["min"], max_min),
                    **_status_info(bucket["min"]),
                }
                for modalidade, bucket in prof["_areas"].items()
            ),
            key=lambda item: (-item["total_min"], sort_key(item["nome"])),
        )
        lista_cursos = sorted(
            (
                {
                    "nome": bucket["obj"].nome,
                    "slug": bucket["obj"].slug,
                    "area": modalidade_of(bucket["obj"]),
                    "area_slug": tipo_slug_modalidade(modalidade_of(bucket["obj"])),
                    "total_min": bucket["min"],
                    "total_hhmm": fmt_minutes(bucket["min"]),
                    "blocos": bucket["blocos"],
                    "pct": _pct(bucket["min"], max_min),
                    **_status_info(bucket["min"]),
                }
                for bucket in prof["_cursos"].values()
            ),
            key=lambda item: (-item["total_min"], sort_key(item["nome"])),
        )
        lista_turmas = sorted(
            (
                {
                    "nome": bucket["obj"].rotulo or bucket["obj"].nome_completo,
                    "slug": bucket["obj"].slug,
                    "curso": bucket["obj"].curso.nome,
                    "curso_slug": bucket["obj"].curso.slug,
                    "area": modalidade_of(bucket["obj"].curso),
                    "area_slug": tipo_slug_modalidade(modalidade_of(bucket["obj"].curso)),
                    "total_min": bucket["min"],
                    "total_hhmm": fmt_minutes(bucket["min"]),
                    "blocos": bucket["blocos"],
                    "pct": _pct(bucket["min"], max_min),
                    **_status_info(bucket["min"]),
                }
                for bucket in prof["_turmas"].values()
            ),
            key=lambda item: (-item["total_min"], sort_key(item["nome"])),
        )
        lista_professores.append(
            {
                "nome": prof["nome"],
                "slug": prof["slug"],
                "color": prof["color"],
                "total_min": prof["total_min"],
                "total_hhmm": fmt_minutes(prof["total_min"]),
                "blocos": prof["blocos"],
                "pct": _pct(prof["total_min"], max_min),
            **_status_info(prof["total_min"]),
                "areas": lista_areas,
                "cursos": lista_cursos,
                "turmas": lista_turmas,
            }
        )
    lista_professores.sort(key=lambda item: sort_key(item["nome"]))

    return {
        "geral": {
            "total_min": geral_min,
            "total_hhmm": fmt_minutes(geral_min),
            "blocos": geral_blocos,
            "professores": len(professores),
            "turmas": len(turmas_ids),
            "media_min": round(geral_min / len(professores)) if professores else 0,
            "media_hhmm": (
                fmt_minutes(round(geral_min / len(professores))) if professores else "00:00"
            ),
            "max_min": max_min,
        },
        "faixa": {"min_min": min_ref, "max_min": max_ref, "min_hhmm": fmt_minutes(min_ref), "max_hhmm": fmt_minutes(max_ref), "min_pct": _pct(min_ref, max_ref), "abaixo": sum(1 for x in lista_professores if x["status"] == "abaixo"), "dentro": sum(1 for x in lista_professores if x["status"] == "dentro"), "acima": sum(1 for x in lista_professores if x["status"] == "acima")},
        "professores": lista_professores,
        "areas": _agrupa_areas(areas, professores),
        "cursos": _agrupa_cursos(cursos, professores),
    }


def _agrupa_areas(areas: dict, professores: dict) -> list[dict]:
    """Consolida os grupos por área (tipo de curso), com seus professores."""
    referencia = faixa_referencia()[1]
    saida = []
    for nome, info in areas.items():
        linhas = [
            _linha_professor(professores[prof_id], professores[prof_id]["_areas"][nome], referencia)
            for prof_id in info["prof_ids"]
            if nome in professores[prof_id]["_areas"]
        ]
        linhas.sort(key=lambda item: sort_key(item["nome"]))
        saida.append(
            {
                "nome": nome,
                "slug": tipo_slug_modalidade(nome),
                "total_min": info["min"],
                "total_hhmm": fmt_minutes(info["min"]),
                "blocos": info["blocos"],
                "professores": linhas,
                "professores_count": len(linhas),
            }
        )
    saida.sort(key=lambda item: (-item["total_min"], sort_key(item["nome"])))
    return saida


def _agrupa_cursos(cursos: dict, professores: dict) -> list[dict]:
    """Consolida os grupos por curso, com seus professores."""
    referencia = faixa_referencia()[1]
    saida = []
    for curso_id, info in cursos.items():
        curso = info["obj"]
        linhas = [
            _linha_professor(
                professores[prof_id], professores[prof_id]["_cursos"][curso_id], referencia
            )
            for prof_id in info["prof_ids"]
            if curso_id in professores[prof_id]["_cursos"]
        ]
        linhas.sort(key=lambda item: sort_key(item["nome"]))
        saida.append(
            {
                "nome": curso.nome,
                "slug": curso.slug,
                "area": modalidade_of(curso),
                "area_slug": tipo_slug_modalidade(modalidade_of(curso)),
                "total_min": info["min"],
                "total_hhmm": fmt_minutes(info["min"]),
                "blocos": info["blocos"],
                "professores": linhas,
                "professores_count": len(linhas),
            }
        )
    saida.sort(key=lambda item: (-item["total_min"], sort_key(item["nome"])))
    return saida


