"""Popular/atualizar os cursos do campus (metadados e PPCs).

Uso:
  python manage.py seed_cursos

Idempotente: cria os cursos que faltam e atualiza os existentes (por `nome`),
sem apagar cursos que existam apenas no CSV. Deve rodar depois do
`import_timetable` e antes do `render_static_site` (é o que o workflow faz).
"""
from __future__ import annotations

from django.core.management.base import BaseCommand

from horarios.data.cursos import CURSOS
from horarios.models import Curso


class Command(BaseCommand):
    help = "Cria/atualiza os cursos do campus (metadados e PPCs)."

    def handle(self, *args, **opts):
        criados = 0
        atualizados = 0
        for raw in CURSOS:
            data = dict(raw)
            nome = data.pop("nome")
            _, foi_criado = Curso.objects.update_or_create(nome=nome, defaults=data)
            if foi_criado:
                criados += 1
            else:
                atualizados += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"seed_cursos: {criados} curso(s) criado(s), {atualizados} atualizado(s)."
            )
        )
