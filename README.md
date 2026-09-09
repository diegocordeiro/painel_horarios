# Quadro de Horários — IFPI Campus Barras

Sistema em **Python + Django** que converte a carga de horários exportada pelo
**FET** ([Flexible Timetabling](https://lalescu.ro/liviu/fet/)) em um **site estático**,
publicado no **GitHub Pages** com a mesma estrutura do portal anterior (turmas,
professores, salas, cursos, campus e histórico de versões).

## Como funciona

Fluxo completo, da grade gerada no FET até a publicação:

```
FET (exporta .csv) → import_versoes → render_static_site → build/ → GitHub Pages
```

1. **Registrar as grades versionadas** — cada versão do quadro vira um CSV em
   `horarios/data/versoes/`, listado no `manifest.json`:

   ```bash
   # Adicione o arquivo da nova versão em horarios/data/versoes/<versao>.csv
   # e acrescente a entrada no manifest.json, ex.:
   # { "versao": "2026.2.v1", "csv": "2026.2.v1.csv", "inicio": "2026-09-14" }
   ```

2. **Importar todas as versões do histórico** — o comando `import_versoes` lê o
   `manifest.json`, reimporta cada versão em ordem cronológica e marca a mais
   recente como atual (os arquivos antigos continuam como histórico):

   ```bash
   python manage.py import_versoes
   ```

3. **Gerar o site estático** — grava as páginas HTML na pasta `build/`:

   ```bash
   python manage.py render_static_site
   ```

   Em terminal interativo o comando pergunta o path/URL base do GitHub Pages
   (ex.: `https://diegocordeiro.github.io/painel_horarios/`). Você também pode
   informar direto com `--base-url <path-or-url>`. Assim, todos os links e assets
   (CSS/JS/imagens) em `build/` são gerados com o prefixo correto.

4. **Publicar** — o conteúdo de `build/` é enviado ao GitHub Pages pelo workflow
   (automaticamente a cada push na branch `main`). Como o CI reimporta todo o
   manifesto, as versões anteriores continuam disponíveis em `/versoes/<versao>/`.

> A base URL (`/repo/` em *project pages* ou `/` em *user/org pages*) é calculada
> dinamicamente a partir do nome do repositório (env `SITE_BASE_URL`), então funciona
> em qualquer conta/organização, sem hardcode. Localmente você pode apontar o subpath
> manualmente com `--base-url` ou respondendo ao prompt do `render_static_site`.

## Recursos

- **Grade por turma, professor e sala**, com slots contíguos unidos e legendas;
- **Cores estáveis por disciplina** (derivadas de um hash do nome), com legenda na
  grade;
- **Modos de visualização**: Completo, Condensado e Super condensado;
- **Tema claro/escuro** persistido no `localStorage` e aderente ao
  `prefers-color-scheme`;
- **Busca client-side** na listagem de turmas (ignora acentos e filtra por curso,
  turma ou turno);
- **Histórico de versões** publicado sob `/versoes/<versao>/`;
- **Páginas de curso** com PPCs (PDFs em `media/attachments/`) e **páginas do
  campus** (administração, calendário acadêmico e setor de saúde).

## Estrutura do projeto

```
barras_horarios/
├── horarios/            # Aplicação Django (models, importador FET, gerador estático, views, templates)
│   ├── management/commands/   # import_timetable, render_static_site
│   ├── fet.py                 # Parsing/normalização do CSV do FET
│   ├── static_site.py         # Geração do site estático (build/)
│   └── templates/horarios/    # Templates das páginas e da grade
├── config/              # Settings/urls do projeto Django
├── static/              # Logo, favicon, CSS e JS do site
├── media/attachments/   # PPCs (PDFs) dos cursos
├── .github/workflows/deploy.yml  # Build + publicação no GitHub Pages
├── manage.py
└── requirements.txt
```

## Modelo de dados

- `Versao` — uma versão/histórico do quadro (o campo `atual` marca a vigente).
- `Curso` — curso do campus, com tipo, modalidade, turno, coordenação e PPCs.
- `Professor`, `Sala`, `Turma` — entidades com `slug` gerado automaticamente.
- `Aula` — bloco de aula (com slots contíguos unidos), ligada a `Versao` e às
  entidades por relacionamentos M2M.

## Pré-requisitos

- **Python 3.13+** (versão usada no CI);
- **Django 5.2.13** (definido em `requirements.txt`);
- **FET** para gerar o CSV da grade.

## Desenvolvimento local (prévia)

```bash
python -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py import_versoes
python manage.py runserver
```

Abra `http://127.0.0.1:8000/`.

## Comandos de gestão

| Comando              | Descrição                               | Argumentos relevantes                                   |
| -------------------- | --------------------------------------- | ------------------------------------------------------- |
| `import_timetable`   | Importa um CSV do FET e popula o banco  | `csv_path`, `--versao`, `--inicio`, `--fim`, `--atual`  |
| `import_versoes`     | Reimporta todas as versões do `manifest.json` | `--manifest`, `--base-dir`                         |
| `render_static_site` | Gera o site estático em `build/`        | `--output`, `--base-url`                                |

## Importar uma nova versão

Para publicar um novo semestre/grade:

1. Exporte a grade no **FET** e salve como `horarios/data/versoes/<versao>.csv`
   (ex.: `2026.2.v1.csv`).
2. Acrescente a entrada no `horarios/data/versoes/manifest.json`, na ordem desejada
   (sequencialmente; cada item tem `versao`, `csv`, `inicio` e, opcionalmente, `fim`).
3. Rode `python manage.py import_versoes` (reimporta todo o histórico e marca a mais
   recente como atual) e, se for publicar localmente, `render_static_site`.

Como todo o histórico fica versionado no repo, as versões antigas são preservadas
entre execuções do GitHub Actions e continuam disponíveis sob `/versoes/<versao>/`.

## Publicação (GitHub Pages)

O workflow `.github/workflows/deploy.yml` executa o build e o deploy a cada push na
branch `main` (ou manualmente via *workflow_dispatch*). Ele migra o banco, reimporta
**todas** as versões do manifesto (`import_versoes`), gera o site estático e publica
`build/` no GitHub Pages.

## Testes

```bash
python manage.py test
```

## Observações sobre o CSV

- O `horarios.csv` da raiz é apenas o **fixture da suíte de testes**
  (`horarios/tests.py`). O conteúdo versionado (histórico) fica em
  `horarios/data/versoes/<versao>.csv`, listado no `manifest.json`.
- As grades **são versionadas** no repositório (ficam em `horarios/data/versoes/`),
  portanto o GitHub Actions reimporta todo o histórico a cada execução.
- `.gitignore` ignora `db.sqlite3` e `build/`, mas **não** os CSVs — eles entram
  normalmente no repositório.
