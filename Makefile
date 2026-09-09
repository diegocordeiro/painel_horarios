# ============================================================================
# Quadro de Horários — IFPI Campus Barras
# Comandos locais amigáveis.
#
# Fluxo rápido (igual ao do CI, só que sem publicar):
#   make configurar  -> cria .venv e instala dependências
#   make site        -> banco + importar + gerar (monta tudo em build/)
#   make ver         -> python -m http.server -d build 8000
#   make rodar       -> site + ver (gera e abre para conferir)
#   make limpar      -> apaga o build/
#
# Atalhos compatíveis: help, setup, migrate, data, render, build, serve,
# dev, test e clean (apontam para os comandos amigáveis acima).
# ============================================================================

# ---- Configuração ---------------------------------------------------------
VENV     ?= .venv
PYTHON   ?= $(VENV)/bin/python
MANAGE    = $(PYTHON) manage.py
PORT     ?= 8000
# Base local: o site é servido na raiz do http.server. Para simular o GitHub
# Pages (project pages) use:  make site BASE_URL=/nome-do-repo/
BASE_URL ?= /

.PHONY: ajuda configurar banco importar gerar site ver rodar testar limpar
.PHONY: help setup migrate data render build serve dev test clean

ajuda: ## mostra todos os comandos disponíveis
	@echo "Comandos disponíveis:"
	@grep -E '^[a-zA-Z_-]+:.*?## .*$$' $(MAKEFILE_LIST) \
		| sort \
		| awk 'BEGIN {FS = ":.*?## "}; {printf "  %-12s %s\n", $$1, $$2}'

configurar: ## cria o ambiente virtual e instala as dependências
	python3 -m venv $(VENV)
	$(PYTHON) -m pip install --upgrade pip
	$(PYTHON) -m pip install -r requirements.txt
	@echo "Pronto! Ative o venv com:  source $(VENV)/bin/activate"

banco: ## prepara o banco de dados (migrate)
	$(MANAGE) migrate

importar: banco ## importa todas as versões e os cursos
	$(MANAGE) import_versoes
	$(MANAGE) seed_cursos

gerar: ## gera as páginas do site em build/
	$(MANAGE) render_static_site --base-url $(BASE_URL)

site: importar gerar ## monta o site do zero (banco + importar + gerar)
	@echo "OK: build/ pronto. Rode 'make ver' para conferir."

ver: ## sobe o servidor local em http://127.0.0.1:PORT
	$(PYTHON) -m http.server -d build $(PORT)

rodar: site ver ## gera o site e já abre para conferir

testar: banco ## roda a suíte de testes
	$(PYTHON) manage.py test

limpar: ## remove o diretório build/ gerado
	rm -rf build
	@echo "build/ apagado."

# ---- Atalhos (compatibilidade) --------------------------------------------
help: ajuda
setup: configurar
migrate: banco
data: importar
render: gerar
build: site
serve: ver
dev: rodar
test: testar
clean: limpar
