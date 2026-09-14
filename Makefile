COMPOSE ?= docker compose
EXTRAS ?=

.PHONY: help build up down restart logs ps models test lint lock shell clean audio-server

help:
	@echo "mai-voice"
	@echo ""
	@echo "  make build       Build the backend image"
	@echo "  make up          Build and start the server (port 7860)"
	@echo "  make down        Stop and remove containers"
	@echo "  make restart     Recreate the server (applies backend/.env changes)"
	@echo "  make logs        Follow server logs"
	@echo "  make models      Warm local model caches (Moonshine/Kokoro)"
	@echo "  make audio-server  Run MLX STT/TTS natively on the Mac (127.0.0.1:8000)"
	@echo "  make test        Run backend unit tests (host uv)"
	@echo "  make lint        Run ruff (host uv)"
	@echo "  make lock        Refresh backend/uv.lock"
	@echo "  make shell       Shell into the backend image"
	@echo ""
	@echo "  EXTRAS='whisper piper cloud' make build   install optional providers"
	@echo ""
	@echo "  Server:  http://localhost:7860        (browser client at /client)"
	@echo "  Health:  http://localhost:7860/status"

audio-server:
	uvx --prerelease=allow --from "mlx-audio[server]" mlx_audio.server --host 127.0.0.1 --port 8000

build:
	$(COMPOSE) build backend

up: build
	$(COMPOSE) up -d backend

down:
	$(COMPOSE) down

restart:
	$(COMPOSE) up -d --force-recreate backend

logs:
	$(COMPOSE) logs -f backend

ps:
	$(COMPOSE) ps

models: build
	$(COMPOSE) --profile tools run --rm models

test:
	cd backend && uv run pytest

lint:
	cd backend && uv run ruff check .

lock:
	cd backend && uv lock

shell:
	$(COMPOSE) run --rm --entrypoint bash backend

clean:
	$(COMPOSE) down --rmi local --volumes --remove-orphans
