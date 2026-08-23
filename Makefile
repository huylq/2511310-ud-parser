# VietNLP. `make help` lists targets.
HOST ?= _59
REMOTE ?= vietnlp

.PHONY: help
help:
	@grep -hE '^[a-zA-Z_-]+:.*?## ' $(MAKEFILE_LIST) | awk 'BEGIN{FS=":.*?## "}{printf "  \033[36m%-16s\033[0m %s\n",$$1,$$2}'

.PHONY: deploy
deploy: ## sync, build, test and start the stack on $(HOST)
	./deploy/deploy.sh --host $(HOST) --path $(REMOTE)

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
