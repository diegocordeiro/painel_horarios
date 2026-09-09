import os
from pathlib import Path

from django.test import TestCase
from django.core.management import call_command

from .fet import (
    merge_slots,
    normalize_day,
    normalize_hour_range,
    parse_course_turma_turno,
    parse_csv_line,
    split_course_and_turma,
)
from .slug import url_slug
from .models import Aula, Curso, Professor, Sala, Turma, Versao


class FetParsingTests(TestCase):
    def test_normalize_hour(self):
        self.assertEqual(normalize_hour_range("14h30 - 15h00"), "14:30 - 15:00")
        self.assertEqual(normalize_hour_range("19:00 - 20:00"), "19:00 - 20:00")
        self.assertEqual(normalize_hour_range("19h00 - 20h00"), "19:00 - 20:00")
        self.assertIsNone(normalize_hour_range("invalido"))

    def test_normalize_day(self):
        self.assertEqual(normalize_day("Terça-feira"), "Terça-Feira")
        self.assertEqual(normalize_day("Sexta-feira"), "Sexta-Feira")
        self.assertEqual(normalize_day("Sábado"), "Sábado")
        self.assertEqual(normalize_day("Terça"), "Terça-Feira")
        self.assertEqual(normalize_day("Sexta"), "Sexta-Feira")
        self.assertEqual(normalize_day("Quarta"), "Quarta-Feira")

    def test_split_course_turma(self):
        self.assertEqual(
            split_course_and_turma("Licenciatura em Física - 6º Período (Noite) 725"),
            ("Licenciatura em Física", "6º Período (Noite) 725"),
        )
        self.assertEqual(split_course_and_turma("Sem hífen"), ("Outros", "Sem hífen"))

    def test_parse_course_turma_turno(self):
        self.assertEqual(
            parse_course_turma_turno("Técnico em Administração PROEJA - 1º ANO (NOITE)"),
            ("Técnico em Administração PROEJA", "1º ANO", "NOITE"),
        )
        self.assertEqual(
            parse_course_turma_turno("Licenciatura em Física - 6º Período (Noite) 725"),
            ("Licenciatura em Física", "6º Período", "Noite"),
        )
        self.assertEqual(
            parse_course_turma_turno("1º ADM PROEJA (NOITE)"),
            ("Outros", "1º ADM PROEJA", "NOITE"),
        )

    def test_merge_slots(self):
        result = merge_slots(["07:30 - 08:00", "08:00 - 08:30"])
        self.assertEqual(result, ["07:30 - 08:30"])

    def test_parse_csv_line(self):
        line = '"1","Sexta-feira","14h30 - 15h00","Turma A","Disciplina","Prof"'
        self.assertEqual(
            parse_csv_line(line),
            ["1", "Sexta-feira", "14h30 - 15h00", "Turma A", "Disciplina", "Prof"],
        )

    def test_url_slug(self):
        self.assertEqual(url_slug("Licenciatura em Física"), "licenciatura_em_fisica")
        self.assertEqual(
            url_slug("Tecnologia em Sistemas para Internet"),
            "tecnologia_em_sistemas_para_internet",
        )


class ImportTimetableTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        csv_path = Path(__file__).resolve().parent.parent / "HorarioOficial_timetable.csv"
        cls.csv_path = str(csv_path)

    def test_import_from_csv(self):
        call_command("import_timetable", self.csv_path, verbosity=0)
        self.assertGreaterEqual(Versao.objects.count(), 1)
        self.assertGreater(Curso.objects.count(), 0)
        self.assertGreater(Professor.objects.count(), 0)
        self.assertGreater(Sala.objects.count(), 0)
        self.assertGreater(Turma.objects.count(), 0)
        self.assertGreater(Aula.objects.count(), 0)
        self.assertTrue(Turma.objects.filter(nome_completo__contains="Administração").exists())
        # O turno não deve ficar embutido no rótulo da turma.
        self.assertFalse(Turma.objects.filter(rotulo__contains="(").exists())
        # O rótulo da turma fica limpo e o curso é detectado pelo padrão.
        turma = Turma.objects.get(
            nome_completo="Técnico Integrado em Administração (Integrado) - 1º ADM (Manhã)"
        )
        self.assertEqual(turma.rotulo, "1º ADM")
        self.assertEqual(turma.curso.nome, "Técnico Integrado em Administração (Integrado)")
        # O turno da grade é registrado no campo turno do curso.
        adm = Curso.objects.get(nome="Técnico Integrado em Administração (Integrado)")
        self.assertIn("Manhã", adm.turno)
        self.assertIn("Tarde", adm.turno)
