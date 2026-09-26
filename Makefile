.PHONY: install dev test lint typecheck check infra-up infra-down

install:
	npm install
	python3 -m venv packages/backend/.venv
	packages/backend/.venv/bin/pip install -e "packages/backend[dev]"

dev:
	npm run dev

test:
	npm run test

lint:
	npm run lint

typecheck:
	npm run typecheck

check:
	npm run check

infra-up:
	docker compose -f docker-compose.dev.yml up -d

infra-down:
	docker compose -f docker-compose.dev.yml down

