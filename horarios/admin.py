"""Admin de inspeção (somente leitura).

O banco (db.sqlite3) NÃO é a fonte da verdade: ele é um artefato de staging,
recriado a cada deploy a partir das grades versionadas (horarios/data/versoes/*.csv
+ manifest.json) e dos metadados de curso (horarios/data/cursos.py), via
`import_versoes` + `seed_cursos`.

Por isso este admin é apenas para inspeção do conteúdo temporário. Qualquer edição
aqui NÃO persiste: será sobrescrita na próxima execução de `import_versoes`/`seed_cursos`
(em todo deploy do GitHub Actions e em todo `make site`/`make importar`).

Para alterar o conteúdo, edite a fonte da verdade (CSVs / manifest.json / cursos.py)
e rode os comandos de importação.
"""
from django.contrib import admin

from .models import Aula, Curso, Professor, Sala, Turma, Versao


class ReadOnlyAdmin(admin.ModelAdmin):
    """ModelAdmin que impede criação, alteração e exclusão pela UI."""

    def has_add_permission(self, request):
        return False

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(Versao)
class VersaoAdmin(ReadOnlyAdmin):
    list_display = ("versao", "inicio", "fim", "atual")
    list_filter = ("atual",)


@admin.register(Curso)
class CursoAdmin(ReadOnlyAdmin):
    list_display = ("nome", "tipo", "posicao", "coordenador")
    list_filter = ("tipo",)
    search_fields = ("nome", "coordenador")


@admin.register(Professor)
class ProfessorAdmin(ReadOnlyAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)


@admin.register(Sala)
class SalaAdmin(ReadOnlyAdmin):
    list_display = ("nome", "predio")
    search_fields = ("nome",)


@admin.register(Turma)
class TurmaAdmin(ReadOnlyAdmin):
    list_display = ("nome_completo", "curso", "rotulo")
    search_fields = ("nome_completo",)
    list_filter = ("curso",)


@admin.register(Aula)
class AulaAdmin(ReadOnlyAdmin):
    list_display = ("disciplina", "dia_semana", "hora_inicio", "hora_fim", "versao", "sala")
    list_filter = ("versao", "dia_semana")
    search_fields = ("disciplina",)

