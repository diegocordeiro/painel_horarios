"""Semeia os metadados estáticos dos cursos (docs/cursos) no banco."""
from __future__ import annotations

from django.core.management.base import BaseCommand

from horarios.data.cursos import CURSOS
from horarios.fet import get_course_position
from horarios.models import Curso


class Command(BaseCommand):
    help = "Popula/atualiza os Cursos com os metadados do site (coordenação, PPC, etc.)."

    def handle(self, *args, **opts):
        for item in CURSOS:
            curso, created = Curso.objects.get_or_create(
                nome=item["nome"],
                defaults={
                    "tipo": item["tipo"],
                    "modalidade": item["modalidade"],
                    "turno": item["turno"],
                    "carga_horaria": item["carga_horaria"],
                    "duracao": item["duracao"],
                    "coordenador": item["coordenador"],
                    "email": item["email"],
                    "lattes": item["lattes"],
                    "posicao": item["posicao"],
                    "ppcs": item["ppcs"],
                },
            )
            if not created:
                for field, value in item.items():
                    if field == "ppcs":
                        # Preserva eventuais PPCs já cadastrados manualmente no admin.
                        if not curso.ppcs:
                            setattr(curso, field, value)
                    else:
                        setattr(curso, field, value)
                curso.save()

        self._reconcile()

        self.stdout.write(self.style.SUCCESS(f"{Curso.objects.count()} curso(s) atualizado(s)."))

    def _reconcile(self):
        """Junta cursos gerados pelo CSV (nomes da grade) aos canônicos (página do curso).

        Cursos que vêm do CSV com o mesmo 'posicao' de um curso canônico são fundidos:
        suas turmas migram para o canônico e o registro duplicado é removido.
        """
        canonical_names = [item["nome"] for item in CURSOS]
        canonical = {
            c.posicao: c for c in Curso.objects.filter(nome__in=canonical_names, posicao__lt=9999)
        }
        movidos = 0
        for dup in Curso.objects.exclude(nome__in=canonical_names):
            dup.posicao = get_course_position(dup.nome)
            dup.save(update_fields=["posicao"])
            if dup.posicao == 9999:
                continue
            target = canonical.get(dup.posicao)
            if target and target.id != dup.id:
                dup.turmas.update(curso=target)
                dup.delete()
                movidos += 1
        if movidos:
            self.stdout.write(self.style.WARNING(f"{movidos} curso(s) duplicado(s) fundido(s)."))
