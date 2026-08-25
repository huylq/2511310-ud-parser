# VietNLP. `make help` lists targets.
HOST ?= _59
REMOTE ?= vietnlp

.PHONY: help
help:
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n",$$1,$$2}'

.PHONY: deploy
deploy: ## sync, build, test and start the stack on $(HOST)
	./deploy/deploy.sh --host $(HOST) --path $(REMOTE)

.PHONY: up
up: ## start the stack from the already-built image (no rebuild, no test run)
	ssh $(HOST) "cd $(REMOTE)/deploy && docker compose up -d --remove-orphans"

.PHONY: migrate
migrate: ## apply pending Postgres migrations on $(HOST)
	ssh $(HOST) "cd $(REMOTE)/deploy && docker compose run --rm --entrypoint python agents -m vietnlp.platform.db.migrate up"

.PHONY: run-acquisition
run-acquisition: ## run acquisition_flow for one source ($(HOST)); SOURCE=name required
	ssh $(HOST) "cd $(REMOTE)/deploy && docker compose run --rm --entrypoint python agents -m vietnlp.platform.flows.acquisition_flow $(SOURCE)"

.PHONY: test-live
test-live: ## full test suite against the live stack (exercises the integration tests that self-skip under `make test`)
	ssh $(HOST) "cd $(REMOTE)/deploy && docker compose run --rm --entrypoint pytest agents /app/tests -q"

.PHONY: test
test: ## run the test suite in the container on $(HOST)
	ssh $(HOST) "cd $(REMOTE)/deploy && docker compose run --rm --no-deps --entrypoint pytest agents /app/tests -q"

.PHONY: routes
routes: ## show the task -> model cost table
	ssh $(HOST) "cd $(REMOTE)/deploy && docker compose run --rm --no-deps agents routes"

.PHONY: agents
agents: ## list registered sub-agents and their models
	ssh $(HOST) "cd $(REMOTE)/deploy && docker compose run --rm --no-deps agents agents"

.PHONY: spend
spend: ## report DeepSeek spend against the caps
	ssh $(HOST) "cd $(REMOTE)/deploy && docker compose run --rm --no-deps agents spend"

.PHONY: cache
cache: ## cache hit statistics
	ssh $(HOST) "cd $(REMOTE)/deploy && docker compose run --rm --no-deps agents cache"

.PHONY: logs
logs: ## tail service logs
	ssh $(HOST) "cd $(REMOTE)/deploy && docker compose logs -f --tail=100"

.PHONY: ps
ps: ## service status
	ssh $(HOST) "cd $(REMOTE)/deploy && docker compose ps"

.PHONY: down
down: ## stop the stack (volumes are preserved)
	ssh $(HOST) "cd $(REMOTE)/deploy && docker compose down"

.PHONY: tunnel
tunnel: ## forward postgres/minio to localhost
	ssh -N -L 6042:127.0.0.1:6042 -L 6043:127.0.0.1:6043 -L 6044:127.0.0.1:6044 $(HOST)
