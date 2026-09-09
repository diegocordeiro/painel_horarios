"""Gera o banco de horários a partir do CSV exportado pelo FET.

Uso:
  python manage.py import_timetable <arquivo.csv> [--versao 2026.2.v4]
        [--inicio 2026-09-03] [--fim 2026-09-02] [--atual]
"""
from __future__ import annotations

import csv
from datetime import date, datetime

from django.core.management.base import BaseCommand, CommandError

from horarios.fet import (
    merge_slots,
    normalize_day,
    normalize_hour_range,
    parse_course_turma_turno,
    split_plus,
)
from horarios.models import Aula, Curso, Professor, Sala, Turma, Versao


class Command(BaseCommand):
    help = "Importa um CSV do FET e popula o banco de horários."

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Caminho absoluto do arquivo CSV do FET.")
        parser.add_argument("--versao", default=None, help="Nome da versão (ex.: 2026.2.v4).")
        parser.add_argument("--inicio", default=None, help="Data de início (YYYY-MM-DD).")
        parser.add_argument("--fim", default=None, help="Data de fim (YYYY-MM-DD).")
        parser.add_argument("--atual", action="store_true", help="Marca esta versão como atual.")

    def handle(self, *args, **opts):
        path = opts["csv_path"]
        versao_nome = opts["versao"]
        inicio = self._parse_date(opts["inicio"], required=False)
        fim = self._parse_date(opts["fim"], required=False)
        marcar_atual = opts["atual"]

        versao = self._get_versao(versao_nome, inicio, fim)
        if marcar_atual:
            Versao.objects.filter(atual=True).update(atual=False)
            versao.atual = True
            versao.save()

        aulas_criadas = self._import_csv(path, versao)

        self.stdout.write(
            self.style.SUCCESS(
                f"Importado: versão {versao.versao} — {aulas_criadas} bloco(s) de aula, "
                f"{Professor.objects.count()} professor(es), "
                f"{Turma.objects.count()} turma(s), "
                f"{Sala.objects.count()} sala(s), "
                f"{Curso.objects.count()} curso(s)."
            )
        )

    def _parse_date(self, value, required=False):
        if not value:
            if required:
                raise CommandError("Informe --inicio (--versao é obrigatório).")
            return None
        try:
            return date.fromisoformat(value)
        except ValueError:
            raise CommandError(f"Data inválida: {value}. Use YYYY-MM-DD.")

    def _get_versao(self, nome, inicio, fim):
        if nome:
            versao, created = Versao.objects.get_or_create(
                versao=nome, defaults={"inicio": inicio, "fim": fim}
            )
            if not created:
                versao.inicio = inicio or versao.inicio
                if fim is not None:
                    versao.fim = fim
                versao.save()
            return versao
        # Sem versão: assume a mais recente, ou cria uma.
        versao = Versao.objects.filter(atual=True).first()
        if versao is None:
            versao = Versao.objects.order_by("-inicio").first()
        if versao is None:
            versao = Versao.objects.create(
                versao=f"import-{datetime.now().strftime('%Y%m%d%H%M%S')}",
                inicio=inicio or date.today(),
            )
        return versao

    def _import_csv(self, path, versao):
        try:
            with open(path, "r", encoding="utf-8-sig", newline="") as fh:
                reader = csv.reader(fh)
                rows = list(reader)
        except FileNotFoundError:
            raise CommandError(f"Arquivo não encontrado: {path}")

        if not rows:
            raise CommandError("O CSV está vazio.")

        header = [h.strip().lstrip("\ufeff") for h in rows[0]]
        required = ["Day", "Hour", "Students Sets", "Subject", "Teachers", "Room"]
        idx = {h: i for i, h in enumerate(header)}
        for key in required:
            if key not in idx:
                raise CommandError(f'Coluna obrigatória ausente no CSV: "{key}".')

        # Agrupa por (atividade_id, dia).
        groups = {}
        for line in rows[1:]:
            if not line or not "".join(line).strip():
                continue
            atividade = (line[idx["Activity Id"]] if "Activity Id" in idx else "") or ""
            dia = normalize_day(line[idx["Day"]]) if idx["Day"] < len(line) else ""
            hour_raw = line[idx["Hour"]] if idx["Hour"] < len(line) else ""
            hour = normalize_hour_range(hour_raw)
            subject = (line[idx["Subject"]] if idx["Subject"] < len(line) else "").strip()
            teachers_raw = line[idx["Teachers"]] if idx["Teachers"] < len(line) else ""
            students_raw = line[idx["Students Sets"]] if idx["Students Sets"] < len(line) else ""
            room_raw = (line[idx["Room"]] if idx["Room"] < len(line) else "").strip()
            tag = ""
            if "Activity Tags" in idx and idx["Activity Tags"] < len(line):
                tag = (line[idx["Activity Tags"]] or "").strip()

            if not dia or not hour or not subject:
                continue

            key = (atividade, dia)
            g = groups.setdefault(
                key,
                {
                    "subject": subject,
                    "teachers": [],
                    "students": [],
                    "room": room_raw,
                    "tag": tag,
                    "hours": [],
                },
            )
            g["subject"] = g["subject"] or subject
            g["teachers"].extend(split_plus(teachers_raw))
            g["students"].extend(split_plus(students_raw))
            g["hours"].append(hour)
            if room_raw:
                g["room"] = room_raw
            if tag:
                g["tag"] = tag

        aprof, aturma, asala, acurso, aturnos = {}, {}, {}, {}, {}

        def get_prof(nome):
            if nome not in aprof:
                aprof[nome] = Professor.objects.get_or_create(nome=nome)[0]
            return aprof[nome]

        def get_sala(nome):
            nome = nome or "Indefinido"
            if nome not in asala:
                asala[nome] = Sala.objects.get_or_create(nome=nome)[0]
            return asala[nome]

        def get_turma(nome):
            if nome not in aturma:
                curso_name, rotulo, turno = parse_course_turma_turno(nome)
                if curso_name not in acurso:
                    acurso[curso_name] = Curso.objects.get_or_create(
                        nome=curso_name,
                    )[0]
                    aturnos[curso_name] = set()
                turma, _ = Turma.objects.get_or_create(
                    nome_completo=nome,
                    defaults={"curso": acurso[curso_name], "rotulo": rotulo},
                )
                if turno:
                    aturnos[curso_name].add(turno)
                    novo_turno = " / ".join(sorted(aturnos[curso_name]))
                    if acurso[curso_name].turno != novo_turno:
                        acurso[curso_name].turno = novo_turno
                        acurso[curso_name].save(update_fields=["turno"])
                aturma[nome] = turma
            return aturma[nome]

        # Remove aulas antigas da versão (importação idempotente).
        Aula.objects.filter(versao=versao).delete()

        contador = 0
        for (atividade, dia), g in groups.items():
            sala = get_sala(g["room"])
            turmas = [get_turma(s) for s in dict.fromkeys(g["students"])]
            professores = [get_prof(p) for p in dict.fromkeys(g["teachers"])]
            for block in merge_slots(g["hours"], max_minutes=60):
                start, end = block.split("-")
                aula = Aula.objects.create(
                    versao=versao,
                    atividade_id=atividade,
                    disciplina=g["subject"],
                    dia_semana=dia,
                    hora_inicio=start.strip(),
                    hora_fim=end.strip(),
                    tag=g["tag"],
                    sala=sala,
                )
                aula.professores.set(professores)
                aula.turmas.set(turmas)
                contador += 1
        return contador
