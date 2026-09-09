"""Importa todas as versões de horário definidas em data/versoes/manifest.json.

Permite publicar o histórico completo de forma determinística: o CI sempre recria o
banco a partir das grades versionadas, preservando todas as versões anteriores.

Uso:
  python manage.py import_versoes
  python manage.py import_versoes --manifest <caminho> --base-dir <pasta>

O manifest é uma lista em `versions`, com cada item no formato:
  {"versao": "2026.2.v4", "csv": "2026.2.v4.csv", "inicio": "2026-09-03", "fim": null}

As versões são importadas em ordem cronológica (pelo campo `inicio`), reutilizando o
`import_timetable` (idempotente), e a mais recente é marcada como a versão atual.
"""
from __future__ import annotations

import json
from datetime import date
from pathlib import Path

from django.conf import settings
from django.core.management import call_command
from django.core.management.base import BaseCommand, CommandError


class Command(BaseCommand):
    help = (
        "Importa todas as versões de horário listadas no manifest.json "
        "(data/versoes) e marca a mais recente como a versão atual."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--manifest",
            default=None,
            help=(
                "Caminho do manifest (padrão: "
                "<BASE_DIR>/horarios/data/versoes/manifest.json)."
            ),
        )
        parser.add_argument(
            "--base-dir",
            default=None,
            help=(
                "Pasta base onde os CSVs referenciados no manifest são resolvidos "
                "(padrão: <BASE_DIR>/horarios/data/versoes)."
            ),
        )

    def handle(self, *args, **opts):
        base_dir = (
            Path(opts["base_dir"])
            if opts["base_dir"]
            else Path(settings.BASE_DIR) / "horarios" / "data" / "versoes"
        )
        manifest_path = (
            Path(opts["manifest"]) if opts["manifest"] else base_dir / "manifest.json"
        )

        if not manifest_path.exists():
            raise CommandError(f"Manifest não encontrado: {manifest_path}")

        try:
            data = json.loads(manifest_path.read_text(encoding="utf-8"))
        except json.JSONDecodeError as exc:
            raise CommandError(f"Manifest inválido ({manifest_path}): {exc}")

        versions = data.get("versions", [])
        if not versions:
            self.stderr.write("Nenhuma versão declarada no manifest.")
            return

        # Garante ordem determinística: da versão mais antiga para a mais recente.
        versions = sorted(versions, key=lambda v: _parse_date(v.get("inicio")))

        total = 0
        for i, entry in enumerate(versions):
            versao = entry["versao"]
            csv_name = entry["csv"]
            csv_path = base_dir / csv_name
            if not csv_path.exists():
                raise CommandError(
                    f"CSV não encontrado para a versão {versao}: {csv_path}"
                )

            # A última versão (mais recente) é marcada como a atual.
            marcar_atual = i == len(versions) - 1

            call_command(
                "import_timetable",
                str(csv_path),
                **{
                    "versao": versao,
                    "inicio": entry.get("inicio"),
                    "fim": entry.get("fim"),
                    "atual": marcar_atual,
                },
            )
            total += 1

        self.stdout.write(
            self.style.SUCCESS(
                f"Importadas {total} versão(ões); a mais recente marcada como atual."
            )
        )


def _parse_date(value: str | None) -> date:
    """Converte a data do manifest (YYYY-MM-DD) em date, com fallback para date.today()."""
    if not value:
        return date.today()
    return date.fromisoformat(str(value))
