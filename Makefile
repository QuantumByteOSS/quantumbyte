# QuantumByte — local dev orchestration.
# Three apps over one Postgres: web (Next.js), orchestrator (Python), worker (Python).
# Run `make help` for the target list.

WEB          := apps/web
ORCHESTRATOR := apps/orchestrator
WORKER       := apps/worker
PY           ?= python3

.DEFAULT_GOAL := help

.PHONY: help setup env install install-web install-orchestrator install-worker \
        db-up db-down migrate generate web orchestrator worker dev clean \
        lint typecheck test check

help: ## Show this help
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) \
		| awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-22s\033[0m %s\n", $$1, $$2}'

## ---- setup ----

setup: env install db-up migrate generate ## One-shot local setup (idempotent): env + deps + db + migrations + client

env: ## Create each app's .env from its .env.example if missing (never clobbers)
	@for app in $(WEB) $(ORCHESTRATOR) $(WORKER); do \
		if test -f $$app/.env; then \
			echo "$$app/.env exists — leaving it"; \
		else \
			cp $$app/.env.example $$app/.env && echo "Created $$app/.env"; \
		fi; \
	done
	@echo "Fill in secrets — the worker needs ANTHROPIC_API_KEY + GIT_PAT"

install: install-web install-orchestrator install-worker ## Install deps for all apps

install-web: ## Install web (npm) deps
	cd $(WEB) && npm install

install-orchestrator: ## Create venv + install orchestrator (pip) deps
	cd $(ORCHESTRATOR) && $(PY) -m venv .venv && .venv/bin/pip install -r requirements.txt

install-worker: ## Create venv + install worker (pip) deps
	cd $(WORKER) && $(PY) -m venv .venv && .venv/bin/pip install -r requirements.txt

## ---- database ----

db-up: ## Start Postgres (docker compose), wait until healthy
	docker compose up -d --wait

db-down: ## Stop Postgres
	docker compose down

migrate: ## Apply Prisma migrations + generate client
	cd $(WEB) && npx prisma migrate dev

generate: ## Generate Prisma client (src/generated/prisma)
	cd $(WEB) && npx prisma generate

## ---- run (each in its own terminal) ----

web: ## Run web dev server (http://localhost:3000)
	cd $(WEB) && npm run dev

orchestrator: ## Run the task→worker orchestrator
	cd $(ORCHESTRATOR) && .venv/bin/python main.py

worker: ## Run one worker instance (start several for a fleet)
	cd $(WORKER) && .venv/bin/python main.py

## ---- run everything at once ----

dev: db-up ## Start Postgres, then web + orchestrator + worker together (Ctrl-C stops all)
	@echo "Starting web + orchestrator + worker — Ctrl-C stops all"
	@trap 'kill 0' INT TERM; \
	( cd $(WEB) && npm run dev ) & \
	( cd $(ORCHESTRATOR) && .venv/bin/python main.py ) & \
	( cd $(WORKER) && .venv/bin/python main.py ) & \
	wait

## ---- quality (same checks CI runs) ----

TOOLS_VENV := .venv-tools

$(TOOLS_VENV)/bin/ruff:
	$(PY) -m venv $(TOOLS_VENV) && $(TOOLS_VENV)/bin/pip install --quiet ruff

lint: $(TOOLS_VENV)/bin/ruff ## Lint web (eslint) + python (ruff)
	cd $(WEB) && npm run lint
	$(TOOLS_VENV)/bin/ruff check $(ORCHESTRATOR) $(WORKER)

typecheck: ## Typecheck web (tsc --noEmit)
	cd $(WEB) && npm run typecheck

test: ## Run web unit tests (vitest)
	cd $(WEB) && npm test

check: lint typecheck test ## Run every CI check locally

clean: ## Remove installed deps + venvs
	rm -rf $(WEB)/node_modules $(ORCHESTRATOR)/.venv $(WORKER)/.venv $(TOOLS_VENV)
