"""Orquestra a renderização do site estático (gera build/).

Usa o engine de templates do Django (sem HTTP) e links prefixados por SITE_BASE_URL.
"""
from __future__ import annotations

import shutil
import zlib
from pathlib import Path

from django.conf import settings
from django.template.loader import render_to_string
from django.utils.text import slugify

from urllib.parse import urlparse

from .fet import DAY_ORDER, normalize_day
from .models import Aula, Curso, Professor, Sala, Turma, Versao

DAY_ORDER_LABELS = {
    "Segunda-Feira": "Segunda",
    "Terça-Feira": "Terça",
    "Quarta-Feira": "Quarta",
    "Quinta-Feira": "Quinta",
    "Sexta-Feira": "Sexta",
    "Sábado": "Sábado",
}


def _fmt(total: int) -> str:
    return f"{total // 60:02d}:{total % 60:02d}"


def make_slots():
    """Slots de 1 hora de 07:00 até 22:00 (intervalos como no CSV)."""
    slots = []
    start = 7 * 60       # 07:00
    end = 22 * 60        # 22:00
    step = 60            # 1 hora
    cur = start
    while cur < end:
        nxt = min(cur + step, end)
        slots.append((f"{_fmt(cur)} - {_fmt(nxt)}", cur))
        cur += step
    return slots


def slot_index(hhmm: str, slots) -> int:
    """Índice do slot cujo início é >= horas:minutos.

    Retorna len(slots) para horários além do último início (ex.: 22:00), permitindo
    calcular corretamente o rowspan de aulas que terminam no fim da grade.
    """
    h, m = (int(x) for x in str(hhmm).strip().split(":"))
    mins = h * 60 + m
    for i, (_, v) in enumerate(slots):
        if v >= mins:
            return i
    return len(slots)


def _subject_color(subject: str) -> str:
    """Cor estável e distinta por disciplina.

    Deriva de um hash crc32 do nome da disciplina (normalizando os espaços),
    espalhando matiz/saturação/luminosidade para que disciplinas diferentes
    tenham cores (quase sempre) distintas, e a mesma disciplina tenha sempre
    a mesma cor em qualquer página (turma, professor, sala).
    """
    name = " ".join(str(subject).split())
    h = zlib.crc32(name.encode("utf-8"))
    hue = h % 360
    sat = 60 + ((h >> 9) % 25)    # 60..84%
    light = 45 + ((h >> 16) % 22)  # 45..66%
    return f"hsl({hue}, {sat}%, {light}%)"


def _subject_slug(subject: str) -> str:
    """Slug CSS estável por disciplina (ex.: 's-analise-de-dados')."""
    return "s-" + slugify(subject)


def build_grid(aulas):
    """Constrói a estrutura de grade consumida pelo template _timetable.html."""
    slots = make_slots()
    n = len(slots)
    grid = {day: [{"type": "empty"} for _ in range(n)] for day in DAY_ORDER}
    color_cache = {}

    for aula in aulas:
        day = normalize_day(aula.dia_semana)
        if day not in grid:
            continue
        start_idx = slot_index(aula.hora_inicio, slots)
        end_idx = slot_index(aula.hora_fim, slots)
        rowspan = max(end_idx - start_idx, 1)
        if aula.disciplina not in color_cache:
            color_cache[aula.disciplina] = {
                "color": _subject_color(aula.disciplina),
                "cls": _subject_slug(aula.disciplina),
            }
        meta = color_cache[aula.disciplina]
        cell = {
            "type": "class",
            "subject": aula.disciplina,
            "time": f"{aula.hora_inicio} - {aula.hora_fim}",
            "rowspan": rowspan,
            "color": meta["color"],
            "cls": meta["cls"],
            "sala": {"nome": aula.sala.nome, "slug": aula.sala.slug} if aula.sala_id else None,
            "professores": [{"nome": p.nome, "slug": p.slug} for p in aula.professores.all()],
            "turmas": [
                {"nome": t.nome_completo, "slug": t.slug, "curso_slug": t.curso.slug}
                for t in aula.turmas.all()
            ],
            "tag": aula.tag,
        }
        grid[day][start_idx] = cell
        for i in range(start_idx + 1, min(start_idx + rowspan, n)):
            grid[day][i] = {"type": "covered"}

    rows = []
    for i, (label, _) in enumerate(slots):
        row = {"time": label, "cells": {day: grid[day][i] for day in DAY_ORDER}}
        row["has_class"] = any(grid[d][i].get("type") == "class" for d in DAY_ORDER)
        rows.append(row)

    active_days = [d for d in DAY_ORDER if any(c.get("type") == "class" for c in grid[d])]
    active_rows = [
        i for i in range(n) if any(grid[d][i].get("type") == "class" for d in DAY_ORDER)
    ]
    first_row = min(active_rows) if active_rows else 0
    last_row = max(active_rows) if active_rows else n - 1

    return {
        "slots": [s[0] for s in slots],
        "days": DAY_ORDER,
        "day_labels": {d: DAY_ORDER_LABELS[d] for d in DAY_ORDER},
        "rows": rows,
        "active_days": active_days,
        "first_row": first_row,
        "last_row": last_row,
        "total_rows": n,
        "subject_legend": [
            {"name": d, "cls": m["cls"], "color": m["color"]}
            for d, m in color_cache.items()
        ],
    }


def normalize_base_url(raw) -> str:
    """Normaliza a base URL usada nos links/assets.

    Aceita tanto um path quanto uma URL absoluta. Em URLs absolutas extrai apenas
    o path (ex.: ``https://user.github.io/repo/`` -> ``/repo/``), garantindo sempre
    ``/`` no início e no final.
    """
    raw = (raw or "").strip()
    if not raw:
        raw = "/"
    # Se for URL absoluta, usa apenas o path (ex.: https://u.github.io/repo/ -> /repo/).
    if "://" in raw:
        raw = urlparse(raw).path or "/"
    if not raw.startswith("/"):
        raw = "/" + raw
    if not raw.endswith("/"):
        raw += "/"
    return raw


TIPO_SLUGS = {
    "Técnico Integrado": "integrado",
    "Técnico Subsequente": "subsequente",
    "Técnico (PROEJA)": "proeja",
    "Licenciatura": "licenciatura",
    "Tecnologia": "tecnologia",
}


def tipo_slug(tipo: str) -> str:
    """Slug estável do tipo de curso para estilos/badges (ver main.css)."""
    return TIPO_SLUGS.get(str(tipo).strip(), "geral")


def entity_color(name: str) -> str:
    """Cor estável e distinta por entidade (ex.: professor/sala)."""
    name = " ".join(str(name).split())
    h = zlib.crc32(name.encode("utf-8"))
    hue = h % 360
    sat = 55 + ((h >> 9) % 28)
    light = 42 + ((h >> 16) % 22)
    return f"hsl({hue}, {sat}%, {light}%)"


class StaticSite:
    """Ponto de entrada para gerar todas as páginas estáticas."""

    def __init__(self, build_root: Path, base_url: str):
        self.build_root = Path(build_root)
        self.base = normalize_base_url(base_url)
        self.static_url = self.base + "static/"

    def _ctx(self, prefix="", **extra):
        """Monta o contexto padrão dos templates.

        ``base`` passa a ser "ciente da versão": em páginas de versões históricas
        (prefixo ``versoes/<slug>/``) os links internos (menu, listas, grade)
        apontam para dentro daquela versão. ``root_base`` é a raiz real do site,
        usada nos links que não devem ser versionados (Início, logo, Cursos,
        página de Versões e breadcrumb de curso).
        """
        ctx = {
            "base": self.base + prefix,
            "root_base": self.base,
            "static_url": self.static_url,
            "site_title": "Quadro de Horários do IFPI - Campus Barras",
        }
        ctx.update(extra)
        return ctx

    def _write(self, rel_path: str, template: str, ctx: dict):
        html = render_to_string(template, ctx)
        out = self.build_root / rel_path
        out.parent.mkdir(parents=True, exist_ok=True)
        out.write_text(html, encoding="utf-8")

    # ---------- páginas ----------
    def render_home(self, versao_atual, history):
        self._write(
            "index.html",
            "horarios/home.html",
            self._ctx(
                versao_atual=versao_atual,
                history=history,
                cursos_total=Curso.objects.count(),
                turmas_total=Turma.objects.count(),
                professores_total=Professor.objects.count(),
                salas_total=Sala.objects.count(),
                active="inicio",
            ),
        )

    def render_intro(self, versao_atual, history):
        self._write(
            "introducao/index.html",
            "horarios/intro.html",
            self._ctx(versao_atual=versao_atual, history=history, active="inicio"),
        )

    def render_versoes(self, versao_atual, history):
        self._write(
            "versoes/index.html",
            "horarios/versoes.html",
            self._ctx(versao_atual=versao_atual, history=history, active="versoes"),
        )

    def _aulas_versao(self, versao_id):
        return list(
            Aula.objects.filter(versao_id=versao_id).prefetch_related("professores", "turmas", "sala")
        )

    def _prefix_path(self, prefix, path):
        return f"{prefix}{path}" if prefix else path

    def render_turmas(self, versao, prefix=""):
        context = self._ctx(prefix=prefix, versao=versao, active="turmas")
        cursos = list(Curso.objects.order_by("posicao", "nome").prefetch_related("turmas"))
        context["cursos"] = cursos
        self._write(self._prefix_path(prefix, "turma/index.html"), "horarios/turma_list.html", context)
        aulas_versao = self._aulas_versao(versao.id)
        for curso in cursos:
            aulas_curso = [a for a in aulas_versao if any(t.curso_id == curso.id for t in a.turmas.all())]
            for turma in curso.turmas.all():
                aulas = [a for a in aulas_curso if any(t.id == turma.id for t in a.turmas.all())]
                ctx = self._ctx(
                    prefix=prefix,
                    versao=versao,
                    curso=curso,
                    turma=turma,
                    grid=build_grid(aulas),
                    kind="turma",
                    active="turmas",
                )
                self._write(
                    self._prefix_path(prefix, f"turma/{curso.slug}/{turma.slug}/index.html"),
                    "horarios/turma_detail.html",
                    ctx,
                )
            if not prefix:
                self._write(
                    "curso/{}/index.html".format(curso.slug),
                    "horarios/curso_detail.html",
                    self._ctx(versao=versao, curso=curso, active="cursos"),
                )

    def render_professores(self, versao, prefix=""):
        aulas_versao = self._aulas_versao(versao.id)
        cont = {}
        for a in aulas_versao:
            for p in a.professores.all():
                cont[p.id] = cont.get(p.id, 0) + 1
        profs = list(Professor.objects.order_by("nome"))
        professores = [
            {
                "nome": p.nome,
                "slug": p.slug,
                "color": entity_color(p.nome),
                "aulas_count": cont.get(p.id, 0),
            }
            for p in profs
        ]
        self._write(
            self._prefix_path(prefix, "professor/index.html"),
            "horarios/professor_list.html",
            self._ctx(prefix=prefix, versao=versao, active="professores", professores=professores),
        )
        for prof in profs:
            aulas = [a for a in aulas_versao if a.professores.filter(id=prof.id).exists()]
            self._write(
                self._prefix_path(prefix, f"professor/{prof.slug}/index.html"),
                "horarios/professor_detail.html",
                self._ctx(prefix=prefix, versao=versao, professor=prof, grid=build_grid(aulas), kind="professor", color=entity_color(prof.nome), active="professores"),
            )

    def render_salas(self, versao, prefix=""):
        aulas_versao = self._aulas_versao(versao.id)
        cont = {}
        for a in aulas_versao:
            if a.sala_id:
                cont[a.sala_id] = cont.get(a.sala_id, 0) + 1
        salas = [
            {
                "nome": s.nome,
                "slug": s.slug,
                "predio": s.predio,
                "color": entity_color(s.nome),
                "aulas_count": cont.get(s.id, 0),
            }
            for s in Sala.objects.order_by("nome")
        ]
        self._write(
            self._prefix_path(prefix, "sala/index.html"),
            "horarios/sala_list.html",
            self._ctx(prefix=prefix, versao=versao, active="salas", salas=salas),
        )
        for sala in Sala.objects.order_by("nome"):
            aulas = [a for a in aulas_versao if a.sala_id == sala.id]
            self._write(
                self._prefix_path(prefix, f"sala/{sala.slug}/index.html"),
                "horarios/sala_detail.html",
                self._ctx(prefix=prefix, versao=versao, sala=sala, grid=build_grid(aulas), kind="sala", color=entity_color(sala.nome), active="salas"),
            )

    def render_cursos(self):
        cursos = [
            {
                "nome": c.nome,
                "slug": c.slug,
                "tipo": c.tipo,
                "tipo_slug": tipo_slug(c.tipo),
                "turno": c.turno,
                "modalidade": c.modalidade,
                "coordenador": c.coordenador,
                "turmas_count": len(c.turmas.all()),
            }
            for c in Curso.objects.order_by("posicao", "nome").prefetch_related("turmas")
        ]
        self._write(
            "cursos/index.html",
            "horarios/curso_list.html",
            self._ctx(cursos=cursos, active="cursos"),
        )

    def copy_assets(self):
        static_src = Path(settings.BASE_DIR) / "static"
        if static_src.exists():
            shutil.copytree(static_src, self.build_root / "static", dirs_exist_ok=True)
        media_src = Path(settings.BASE_DIR) / "media"
        if media_src.exists():
            shutil.copytree(media_src, self.build_root / "media", dirs_exist_ok=True)
