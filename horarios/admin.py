from django.contrib import admin

from .models import Aula, Curso, Professor, Sala, Turma, Versao


@admin.register(Versao)
class VersaoAdmin(admin.ModelAdmin):
    list_display = ("versao", "inicio", "fim", "atual")
    list_filter = ("atual",)


@admin.register(Curso)
class CursoAdmin(admin.ModelAdmin):
    list_display = ("nome", "tipo", "posicao", "coordenador")
    list_filter = ("tipo",)
    search_fields = ("nome", "coordenador")
    prepopulated_fields = {"slug": ("nome",)}


@admin.register(Professor)
class ProfessorAdmin(admin.ModelAdmin):
    list_display = ("nome",)
    search_fields = ("nome",)
    prepopulated_fields = {"slug": ("nome",)}


@admin.register(Sala)
class SalaAdmin(admin.ModelAdmin):
    list_display = ("nome", "predio")
    search_fields = ("nome",)
    prepopulated_fields = {"slug": ("nome",)}


@admin.register(Turma)
class TurmaAdmin(admin.ModelAdmin):
    list_display = ("nome_completo", "curso", "rotulo")
    search_fields = ("nome_completo",)
    list_filter = ("curso",)


@admin.register(Aula)
class AulaAdmin(admin.ModelAdmin):
    list_display = ("disciplina", "dia_semana", "hora_inicio", "hora_fim", "versao", "sala")
    list_filter = ("versao", "dia_semana")
    search_fields = ("disciplina",)
