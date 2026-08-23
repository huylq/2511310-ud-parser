# Deployment — server `_59`

Target: `118.69.218.59` (`ssh _59`), Rocky Linux 8.10, Docker 26.1.3 / Compose v2.27.0.

## The host is shared — read this before changing anything

Roughly a dozen unrelated containers already run here, and only ~3-4 GB of the
15 GB is actually free. Every service therefore carries a hard memory limit:

| Service | Limit | Typical | Started by default |
|---|---|---|---|
| postgres (pgvector/pg16) | 768 MB | ~30 MB | yes |
| minio | 512 MB | ~80 MB | yes |
| agents | 512 MB | per-command | no — dispatch only |
| fuseki | 1 GB | — | no — `--profile graph`, needed from P3 |

Do not raise a limit to make something fit. Make the something smaller. OOM kills on
this box present as containers that restart for no visible reason.

There is **no GPU**. CPU-only inference for PhoBERT/VnCoreNLP in P2.

## Ports

The 6040–6049 block was free at deploy time; 5432 is the host's own Postgres and
most of 6010–6035 plus 8000/8081/9100 are taken by other tenants.

| Port | Service |
|---|---|
| 6042 | Postgres |
| 6043 | MinIO API |
| 6044 | MinIO console |
| 6045 | Fuseki (profile `graph`) |

All bind to **127.0.0.1 only**. Reach them through a tunnel:

```
make tunnel     # or: ssh -N -L 6042:127.0.0.1:6042 -L 6043:127.0.0.1:6043 _59
```

Never publish a database or object store to `0.0.0.0` on this machine.

## Secrets

`deploy/.env` lives **only on the server**, mode 600. It is excluded from the sync
and gitignored. `deploy/.env.example` documents the required keys.

Rotate a key by editing `deploy/.env` on the host and re-running `make deploy`.
Never echo a key value — not truncated, not into a log line.

## Deploy

```
make deploy     # tar-sync -> build -> pytest inside the image -> compose up
```

The test suite runs **inside the built image before services start**. A failing
build never becomes a running service. Keep that ordering.

`rsync` is not installed on the host, so the sync uses `tar` over SSH.

## Operating

```
make agents     # registered sub-agents and their models
make routes     # the task -> model cost table
make spend      # spend against the flow / daily / total caps
make cache      # cache hit rates
make test       # test suite in the container
make ps / logs / down
```

Work is dispatched explicitly and never runs automatically:

```
docker compose run --rm --no-deps agents run quality-scorer --text "..."
```

The `agents` service sits behind the `tools` profile so `compose up` does not start
it — its commands all exit, and an auto-restart on a finished flow would silently
re-spend the budget.

## Before launching any flow

```
docker compose run --rm --no-deps agents estimate <task> --count <n>
```

Caps hard-stop (charter rule 5). A flow that trips one aborts; it does not warn.

## Fuseki (P3, not started by default)

Fuseki is behind the `graph` compose profile and is not needed until ontology
work (P3) begins. To turn it on:

```
docker compose --profile graph up -d fuseki
docker compose run --rm --no-deps --entrypoint python agents -c "
from vietnlp.platform.graph.fuseki_admin import create_dataset
import os
create_dataset('http://fuseki:3030', 'vietnlp', auth=('admin', os.environ['FUSEKI_ADMIN_PASSWORD']))
"
```

`create_dataset` is idempotent -- safe to re-run.
