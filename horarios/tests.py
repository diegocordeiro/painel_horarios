import json
import os
import tempfile
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
from .static_site import normalize_base_url
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


class NormalizeBaseUrlTests(TestCase):
    def test_absolute_url_extracts_path(self):
        self.assertEqual(
            normalize_base_url("https://diegocordeiro.github.io/painel_horarios/build/"),
            "/painel_horarios/build/",
        )
        self.assertEqual(
            normalize_base_url("https://diegocordeiro.github.io/painel_horarios"),
            "/painel_horarios/",
        )
        self.assertEqual(normalize_base_url("https://user.github.io/"), "/")

    def test_path_is_normalized(self):
        self.assertEqual(normalize_base_url("/painel_horarios/"), "/painel_horarios/")
        self.assertEqual(normalize_base_url("painel_horarios"), "/painel_horarios/")

    def test_empty_defaults_to_root(self):
        self.assertEqual(normalize_base_url(""), "/")
        self.assertEqual(normalize_base_url(None), "/")


class ImportTimetableTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        csv_path = Path(__file__).resolve().parent.parent / "horarios.csv"
        cls.csv_path = str(csv_path)

    def test_import_from_csv(self):
        call_command("import_timetable", self.csv_path, verbosity=0)
        self.assertGreaterEqual(Versao.objects.count(), 1)
        self.assertEqual(Curso.objects.count(), 3)
        self.assertEqual(Turma.objects.count(), 3)
        self.assertGreater(Professor.objects.count(), 0)
        self.assertGreater(Sala.objects.count(), 0)
        self.assertGreater(Aula.objects.count(), 0)
        # O turno não deve ficar embutido no rótulo da turma.
        self.assertFalse(Turma.objects.filter(rotulo__contains="(").exists())
        # O rótulo da turma fica limpo e o curso é detectado pelo padrão.
        turma = Turma.objects.get(
            nome_completo="TÉCNICO EM ADMINISTRAÇÃO PROEJA - 1º ANO (NOITE)"
        )
        self.assertEqual(turma.rotulo, "1º ANO")
        self.assertEqual(turma.curso.nome, "TÉCNICO EM ADMINISTRAÇÃO PROEJA")
        # O turno da grade é registrado no campo turno do curso.
        adm = Curso.objects.get(nome="TÉCNICO EM ADMINISTRAÇÃO PROEJA")
        self.assertEqual(adm.turno, "NOITE")


class SeedCursosTests(TestCase):
    def test_seed_cursos_popula_ppcs_e_tipo(self):
        call_command("seed_cursos", verbosity=0)
        adm = Curso.objects.get(nome="TÉCNICO EM ADMINISTRAÇÃO PROEJA")
        self.assertEqual(adm.tipo, "Técnico (PROEJA)")
        self.assertGreaterEqual(len(adm.ppcs), 1)
        self.assertEqual(adm.ppcs[0]["file"], "ppc_administracao_proeja_2023.pdf")
        self.assertEqual(adm.ppcs[0]["label"], "PPC Administração PROEJA 2023")
        # O seed não deve criar mais cursos além dos que vêm do CSV.
        self.assertEqual(Curso.objects.count(), 3)


class ImportVersoesTests(TestCase):
    """Valida o `import_versoes`: preserva todas as versões e marca a mais recente."""

    def _make_fixture(self):
        """Cria um manifest com duas versões (fora de ordem) em um dir temporário.

        Retorna (manifest_path, base_dir). Usa o `horarios.csv` como grade de ambas.
        """
        csv_fonte = Path(__file__).resolve().parent.parent / "horarios.csv"
        tmp_dir = Path(tempfile.mkdtemp(prefix="versoes_"))
        (tmp_dir / "2026.1.v1.csv").write_bytes(csv_fonte.read_bytes())
        (tmp_dir / "2026.2.v1.csv").write_bytes(csv_fonte.read_bytes())

        manifest = {
            "versions": [
                # Listadas fora de ordem de propósito; o comando ordena por `inicio`.
                {"versao": "2026.2.v1", "csv": "2026.2.v1.csv", "inicio": "2026-09-14"},
                {"versao": "2026.1.v1", "csv": "2026.1.v1.csv", "inicio": "2026-02-16"},
            ]
        }
        manifest_path = tmp_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        return str(manifest_path), str(tmp_dir)

    def test_import_versoes_preserves_multiple_versions(self):
        manifest, base_dir = self._make_fixture()
        call_command("import_versoes", manifest=manifest, base_dir=base_dir, verbosity=0)

        self.assertEqual(Versao.objects.count(), 2)
        self.assertEqual(
            set(Versao.objects.values_list("versao", flat=True)),
            {"2026.1.v1", "2026.2.v1"},
        )
        # Ambas as versões têm aulas importadas.
        for v in Versao.objects.all():
            self.assertGreater(v.aulas.count(), 0)

    def test_import_versoes_marca_a_mais_recente_como_atual(self):
        manifest, base_dir = self._make_fixture()
        call_command("import_versoes", manifest=manifest, base_dir=base_dir, verbosity=0)

        self.assertEqual(Versao.objects.filter(atual=True).count(), 1)
        atual = Versao.objects.get(atual=True)
        self.assertEqual(atual.versao, "2026.2.v1")

    def test_import_versoes_e_idempotente(self):
        manifest, base_dir = self._make_fixture()
        call_command("import_versoes", manifest=manifest, base_dir=base_dir, verbosity=0)
        call_command("import_versoes", manifest=manifest, base_dir=base_dir, verbosity=0)

        self.assertEqual(Versao.objects.count(), 2)
        self.assertEqual(Versao.objects.filter(atual=True).count(), 1)
