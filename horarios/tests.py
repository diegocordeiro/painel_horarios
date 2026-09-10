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
from .carga_horaria import (aula_minutes, build_carga_horaria, faixa_referencia, fmt_minutes, modalidade_of, sort_key)
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


class CargaHorariaTests(TestCase):
    """Valida a agregação da carga horária (horas por turma/curso/área)."""

    @classmethod
    def setUpTestData(cls):
        csv_path = Path(__file__).resolve().parent.parent / "horarios.csv"
        call_command("import_timetable", str(csv_path), atual=True, verbosity=0)
        call_command("seed_cursos", verbosity=0)
        cls.versao = Versao.objects.get(atual=True)

    def _dados(self):
        aulas = Aula.objects.filter(versao=self.versao).prefetch_related(
            "professores", "turmas__curso"
        )
        return build_carga_horaria(list(aulas))

    def test_ordem_alfabetica(self):
        dados = self._dados()
        nomes = [p["nome"] for p in dados["professores"]]
        self.assertGreater(len(nomes), 0)
        self.assertEqual(nomes, sorted(nomes, key=sort_key))
        # Ordenação ignora acentos (ex.: "Antônio" deve vir junto de "Antonio").
        self.assertEqual(sort_key("Antônio"), sort_key("antonio"))

    def test_carga_e_blocos_do_professor(self):
        dados = self._dados()
        prof = Professor.objects.get(nome="Diego Cordeiro de Oliveira")
        aulas = Aula.objects.filter(versao=self.versao, professores=prof)
        esperado_min = sum(aula_minutes(a) for a in aulas)

        entrada = next(p for p in dados["professores"] if p["nome"] == prof.nome)
        self.assertEqual(entrada["total_min"], esperado_min)
        self.assertEqual(entrada["total_hhmm"], fmt_minutes(esperado_min))
        self.assertEqual(entrada["blocos"], aulas.count())
        self.assertGreater(entrada["total_min"], 0)

    def test_geral_nao_duplica_co_docencia(self):
        dados = self._dados()
        aulas = Aula.objects.filter(versao=self.versao)
        self.assertEqual(
            dados["geral"]["total_min"], sum(aula_minutes(a) for a in aulas)
        )
        self.assertEqual(dados["geral"]["blocos"], aulas.count())
        self.assertEqual(dados["geral"]["professores"], len(dados["professores"]))

    def test_agrupa_por_area_e_curso(self):
        dados = self._dados()
        areas = {a["nome"] for a in dados["areas"]}
        self.assertIn("Técnico (PROEJA)", areas)
        self.assertIn("Licenciatura", areas)
        for area in dados["areas"]:
            self.assertGreater(area["total_min"], 0)
            self.assertGreaterEqual(area["professores_count"], 1)

        cursos = {c["nome"]: c for c in dados["cursos"]}
        self.assertEqual(cursos["PEDAGOGIA"]["area"], "Licenciatura")
        self.assertGreater(cursos["PEDAGOGIA"]["total_min"], 0)

    def test_quebra_por_turma(self):
        dados = self._dados()
        prof = next(
            p for p in dados["professores"] if p["nome"] == "Diego Cordeiro de Oliveira"
        )
        self.assertGreaterEqual(len(prof["turmas"]), 1)
        for turma in prof["turmas"]:
            self.assertGreater(turma["total_min"], 0)
            self.assertGreater(turma["blocos"], 0)

    def test_curso_sem_tipo_cai_em_nao_classificado(self):
        curso = Curso.objects.create(nome="CURSO SEM TIPO")
        self.assertEqual(modalidade_of(curso), "Não classificado")

    def test_percentuais_usam_ponto_decimal(self):
        """O CSS depende de ponto (ex.: '66.7'), nunca vírgula da localização."""
        dados = self._dados()
        for prof in dados["professores"]:
            self.assertNotIn(",", prof["pct"])
            for grupo in prof["areas"] + prof["cursos"] + prof["turmas"]:
                self.assertNotIn(",", grupo["pct"])


class CargaHorariaStaticTests(TestCase):
    """Garante que o dashboard é gerado para a versão atual e para o histórico."""

    def test_render_carga_horaria_versionada(self):
        csv_fonte = Path(__file__).resolve().parent.parent / "horarios.csv"
        tmp_dir = Path(tempfile.mkdtemp(prefix="versoes_"))
        (tmp_dir / "2026.1.v1.csv").write_bytes(csv_fonte.read_bytes())
        (tmp_dir / "2026.2.v1.csv").write_bytes(csv_fonte.read_bytes())
        manifest = {
            "versions": [
                {"versao": "2026.1.v1", "csv": "2026.1.v1.csv", "inicio": "2026-02-16"},
                {"versao": "2026.2.v1", "csv": "2026.2.v1.csv", "inicio": "2026-09-14"},
            ]
        }
        manifest_path = tmp_dir / "manifest.json"
        manifest_path.write_text(json.dumps(manifest), encoding="utf-8")
        call_command(
            "import_versoes", manifest=str(manifest_path), base_dir=str(tmp_dir), verbosity=0
        )
        call_command("seed_cursos", verbosity=0)

        out = Path(tempfile.mkdtemp(prefix="build_"))
        call_command("render_static_site", output=str(out), base_url="/", verbosity=0)

        atual = out / "carga-horaria" / "index.html"
        historica = out / "versoes" / "2026.1.v1" / "carga-horaria" / "index.html"
        self.assertTrue(atual.exists())
        self.assertTrue(historica.exists())

        html = atual.read_text(encoding="utf-8")
        self.assertIn("Carga horária dos professores", html)
        self.assertIn("carga-segmented", html)
        # A largura das barras nunca pode sair localizada com vírgula.
        self.assertNotRegex(html, r"width: \d+,\d+%")
        # Histórico aponta o menu para a subárvore da versão.
        historic_html = historica.read_text(encoding="utf-8")
        self.assertIn("/versoes/2026.1.v1/carga-horaria/", historic_html)


class DistribuicaoCargaTests(TestCase):
    """Valida a régua fixa da coluna Distribuição (mín. 10h / máx. 20h)."""

    def test_faixa_padrao(self):
        self.assertEqual(faixa_referencia(), (600, 1200))

    def test_faixa_configuravel(self):
        with self.settings(CARGA_HORARIA_MINIMA_HORAS=8, CARGA_HORARIA_MAXIMA_HORAS=16):
            self.assertEqual(faixa_referencia(), (480, 960))

    def test_pct_e_status_pela_faixa(self):
        csv_path = Path(__file__).resolve().parent.parent / "horarios.csv"
        call_command("import_timetable", str(csv_path), atual=True, verbosity=0)
        call_command("seed_cursos", verbosity=0)
        versao = Versao.objects.get(atual=True)
        aulas = list(Aula.objects.filter(versao=versao).prefetch_related("professores", "turmas__curso"))
        dados = build_carga_horaria(aulas)
        self.assertEqual(dados["faixa"]["min_hhmm"], "10:00")
        self.assertEqual(dados["faixa"]["max_hhmm"], "20:00")
        self.assertEqual(dados["faixa"]["min_pct"], "50")
        total = dados["faixa"]["abaixo"] + dados["faixa"]["dentro"] + dados["faixa"]["acima"]
        self.assertEqual(total, len(dados["professores"]))
        for prof in dados["professores"]:
            esperado = round(prof["total_min"] * 100 / 1200, 1)
            self.assertAlmostEqual(float(prof["pct"]), esperado, places=1)
            if prof["total_min"] < 600:
                self.assertEqual(prof["status"], "abaixo")
            elif prof["total_min"] > 1200:
                self.assertEqual(prof["status"], "acima")
            else:
                self.assertEqual(prof["status"], "dentro")


