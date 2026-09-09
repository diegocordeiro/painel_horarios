"""Porta fiel da lógica do gerador original (scripts/fet-csv-to-mdx.mjs) para Python.

Lida com a leitura/normalização do CSV exportado pelo FET.
"""
from __future__ import annotations

import re

from .slug import url_slug

DAY_MAP = {
    "Segunda-feira": "Segunda-Feira",
    "Terça-feira": "Terça-Feira",
    "Quarta-feira": "Quarta-Feira",
    "Quinta-feira": "Quinta-Feira",
    "Sexta-feira": "Sexta-Feira",
    "Sábado": "Sábado",
    # Forma curta exportada pelo FET (sem o sufixo "feira").
    "Segunda": "Segunda-Feira",
    "Terça": "Terça-Feira",
    "Quarta": "Quarta-Feira",
    "Quinta": "Quinta-Feira",
    "Sexta": "Sexta-Feira",
}

DAY_ORDER = [
    "Segunda-Feira",
    "Terça-Feira",
    "Quarta-Feira",
    "Quinta-Feira",
    "Sexta-Feira",
    "Sábado",
]

# Porta de COURSE_POSITIONS.
from .data.cursos import COURSE_POSITIONS  # noqa: E402


def parse_csv_line(line: str) -> list[str]:
    """Divisão de linha CSV respeitando aspas (como no parser do gerador)."""
    out: list[str] = []
    current = ""
    in_quotes = False
    i = 0
    while i < len(line):
        char = line[i]
        if char == '"':
            if in_quotes and i + 1 < len(line) and line[i + 1] == '"':
                current += '"'
                i += 1
            else:
                in_quotes = not in_quotes
        elif char == "," and not in_quotes:
            out.append(current)
            current = ""
        else:
            current += char
        i += 1
    out.append(current)
    return out


def normalize_hour_range(value: str):
    """Normaliza horário para 'HH:MM - HH:MM'.

    Aceita tanto '14h30 - 15h00' (formato FET com 'h') quanto '14:30 - 15:00'
    (formato com ':'). Retorna None se o valor for inválido.
    """
    if value is None:
        return None
    match = re.match(r"^\s*(\d{1,2})[h:](\d{2})\s*-\s*(\d{1,2})[h:](\d{2})\s*$", value)
    if not match:
        return None
    h1, m1, h2, m2 = match.groups()
    return f"{int(h1):02d}:{m1} - {int(h2):02d}:{m2}"


def normalize_day(value: str) -> str:
    value = (value or "").strip()
    return DAY_MAP.get(value, value)


def split_plus(value) -> list[str]:
    if value is None:
        return []
    return [s.strip() for s in str(value).split("+") if s.strip()]


def minutes_from_hhmm(hhmm: str):
    match = re.match(r"^(\d{2}):(\d{2})$", str(hhmm).strip())
    if not match:
        return None
    return int(match.group(1)) * 60 + int(match.group(2))


def split_course_and_turma(full_name: str) -> tuple[str, str]:
    """'X - Y' -> (X, Y); sem ' - ' -> ('Outros', nome)."""
    name = str(full_name or "").strip()
    match = re.match(r"^(.*?)\s*-\s*(.+)$", name)
    if not match:
        return "Outros", name
    return match.group(1).strip(), match.group(2).strip()


def get_course_position(course_name: str) -> int:
    return COURSE_POSITIONS.get(url_slug(course_name), 9999)


def _parse_time_slot(time_value: str):
    """Divide 'HH:MM - HH:MM' em (start_min, end_min)."""
    parts = str(time_value).split("-")
    if len(parts) < 2:
        return (None, None)
    start = minutes_from_hhmm(parts[0].strip())
    end = minutes_from_hhmm("-".join(parts[1:]).strip())
    return (start, end)


def merge_slots(slots: list[str], max_minutes: int | None = None) -> list[str]:
    """Une intervalos contíguos, opcionalmente limitando a duração a `max_minutes`.

    Ex.: ['07:30 - 08:00', '08:00 - 08:30'] -> ['07:30 - 08:30'].
    Com max_minutes=60, blocos contíguos que somariam mais de 1h NÃO são unidos
    (ex.: '19:00 - 20:00' + '20:00 - 21:00' permanecem separados).
    """
    parsed = []
    for slot in slots:
        start, end = _parse_time_slot(slot)
        if start is None or end is None:
            continue
        parsed.append((start, end, slot))
    parsed.sort(key=lambda x: x[0])
    merged: list[tuple[int, int, str]] = []
    for start, end, label in parsed:
        if merged:
            last_start, last_end, _ = merged[-1]
            if last_end == start and (max_minutes is None or (end - last_start) <= max_minutes):
                merged[-1] = (last_start, end, f"{_fmt(last_start)} - {_fmt(end)}")
                continue
        merged.append((start, end, f"{_fmt(start)} - {_fmt(end)}"))
    return [m[2] for m in merged]


def _fmt(total: int) -> str:
    return f"{total // 60:02d}:{total % 60:02d}"
