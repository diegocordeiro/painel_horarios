# Horários IFPI – Campus Barras (versão Django)

Sistema em **Python + Django** que gera um **site estático** com a mesma estrutura do
portal Docusaurus atual (turmas, professores, salas, cursos, campus e histórico de
versões). Ele lê o CSV exportado pelo **FET** (https://lalescu.ro/liviu/fet/) como
"carga de horários" e publica o resultado em **GitHub Pages**.

## Estrutura

- `horarios/` — aplicação Django (models, importador FET, gerador estático, templates).
- `config/` — settings/urls do projeto.
- `static/` — logo, favicon e CSS/JS do site.
- `media/attachments/` — PPCs (PDFs) dos cursos.
- `HorarioOficial_timetable.csv` — saída do FET (colunas `Day, Hour, Students Sets,
  Subject, Teachers, Room`, entre outras).
- `.github/workflows/deploy.yml` — build + publicação no GitHub Pages.

## Como funciona

1. **Importar o CSV do FET** (popula o banco com uma versão):

   ```bash
   python manage.py import_timetable HorarioOficial_timetable.csv \
     --versao 2026.2.v4 --inicio 2026-09-03 --atual
   ```

2. **Semear os metadados dos cursos** (coordenação, PPCs, etc.):

   ```bash
   python manage.py seed_content
   ```

3. **Gerar o site estático** (pasta `build/`):

   ```bash
   python manage.py render_static_site
   ```

4. **Publicar** o conteúdo de `build/` no GitHub Pages (o workflow faz isso
   automaticamente a cada push na branch `main`).

> A base URL (subpath `/ifpisrn-horarios/` ou `/`) é calculada dinamicamente a partir
> do nome do repositório, então funciona em qualquer conta/organização, sem hardcode.

## Desenvolvimento (prévia local)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py import_timetable HorarioOficial_timetable.csv --versao 2026.2.v4 --inicio 2026-09-03 --atual
python manage.py seed_content
python manage.py runserver
```

Abra `http://127.0.0.1:8000/`.

## Importar uma nova versão

Só é preciso rodar o passo 1 com `--versao` (e `--atual`) novo, seguido de
`seed_content` e `render_static_site`. As versões antigas são preservadas e ficam
divulgadas sob `/versoes/<versao>/`.

## Testes

```bash
python manage.py test
```

## Modelo de dados

- `Versao` — uma versão/histórico do quadro.
- `Curso`, `Professor`, `Sala`, `Turma` — entidades.
- `Aula` — bloco de aula (com slots contíguos unidos), ligado a `Versao` e às
  entidades por M2M.
