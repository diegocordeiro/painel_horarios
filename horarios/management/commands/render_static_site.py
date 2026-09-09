"""Gera o site estático completo dentro de build/ (para publicar no GitHub Pages)."""
from __future__ import annotations

import os
import sys
from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from horarios.models import Versao
from horarios.static_site import StaticSite, normalize_base_url


class Command(BaseCommand):
    help = "Renderiza todas as páginas estáticas em build/."

    def add_arguments(self, parser):
        parser.add_argument("--output", default=None, help="Pasta de saída (padrão: <BASE_DIR>/build).")
        parser.add_argument(
            "--base-url",
            default=None,
            help=(
                "URL ou path base do GitHub Pages usado nos links/assets "
                "(ex.: https://user.github.io/repo/ ou /repo/). Se omitido, usa a env "
                "SITE_BASE_URL e, em terminal interativo, pergunta ao usuário."
            ),
        )

    def handle(self, *args, **opts):
        build_root = Path(opts["output"]) if opts["output"] else Path(settings.BASE_DIR) / "build"
        if build_root.exists():
            import shutil

            shutil.rmtree(build_root)
        build_root.mkdir(parents=True, exist_ok=True)

        base = opts["base_url"] or settings.SITE_BASE_URL
        if (
            not opts["base_url"]
            and not os.environ.get("SITE_BASE_URL")
            and sys.stdin.isatty()
        ):
            default = settings.SITE_BASE_URL
            raw = input(f"Path/URL base do GitHub Pages [{default}]: ").strip()
            base = raw or default
        base = normalize_base_url(base)
        site = StaticSite(build_root, base)
        self.stdout.write(f"Base URL usada nos links/assets: {base}")

        atual = Versao.objects.filter(atual=True).first() or Versao.objects.order_by("-inicio").first()
        if atual is None:
            self.stderr.write("Nenhuma versão de horário encontrada. Rode 'import_timetable'.")
            return

        history = list(Versao.objects.exclude(id=atual.id))
        # Histórico em ordem decrescente de início (mais recente primeiro).
        history.sort(key=lambda v: v.inicio, reverse=True)

        site.copy_assets()
        site.render_home()
        site.render_intro(atual, history)
        site.render_versoes(atual, history)
        site.render_turmas(atual, prefix="")
        site.render_professores(atual, prefix="")
        site.render_salas(atual, prefix="")
        site.render_cursos()

        # Versões antigas ficam sob /versoes/<slug>/...
        for versao in history:
            prefix = f"versoes/{versao.slug}/"
            site.render_turmas(versao, prefix=prefix)
            site.render_professores(versao, prefix=prefix)
            site.render_salas(versao, prefix=prefix)

        self.stdout.write(self.style.SUCCESS(f"Site estático gerado em: {build_root}"))
