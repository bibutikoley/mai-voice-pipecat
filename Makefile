COMPOSE ?= docker compose
EXTRAS ?=

.PHONY: help build up down restart logs ps models test lint lock shell clean stt-server tts-server stt-stop tts-stop

help:
	@echo "mai-voice"
	@echo ""
	@echo "  make stt-server  Start the MLX STT server on the Mac (127.0.0.1:8001)"
	@echo "  make tts-server  Start the MLX TTS server on the Mac (127.0.0.1:8002)"
	@echo "  make up          Build and start the Docker Pipecat server (:7860)"
	@echo ""
	@echo "  make stt-stop    Stop the STT server"
	@echo "  make tts-stop    Stop the TTS server"
	@echo "  make down        Stop and remove the Docker server"
	@echo "  make restart     Recreate the Docker server (applies backend/.env changes)"
	@echo "  make logs        Follow Docker server logs"
	@echo "  make ps          Show Docker container status"
	@echo "  make models      Warm in-container caches (Moonshine/Kokoro)"
	@echo "  make test        Run backend unit tests (host uv)"
	@echo "  make lint        Run ruff (host uv)"
	@echo "  make lock        Refresh backend/uv.lock"
	@echo "  make shell       Shell into the backend image"
	@echo ""
	@echo "  EXTRAS='whisper piper cloud' make build   install optional providers"
	@echo ""
	@echo "  Server:  http://localhost:7860        (browser client at /client)"
	@echo "  Health:  http://localhost:7860/status"

# --- Apple Silicon audio servers (independent; restart either without touching the others)

stt-server:
	uvx --prerelease=allow --from "mlx-audio[server]" mlx_audio.server --host 127.0.0.1 --port 8001

tts-server:
	uvx --prerelease=allow --from "mlx-audio[server]" mlx_audio.server --host 127.0.0.1 --port 8002

stt-stop:
	-pkill -f "mlx_audio.server.*--port 8001"

tts-stop:
	-pkill -f "mlx_audio.server.*--port 8002"

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
