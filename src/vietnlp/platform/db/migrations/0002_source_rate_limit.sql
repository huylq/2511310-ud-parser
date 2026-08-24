-- 0002_source_rate_limit.sql
-- Adds per-source politeness rate limiting for P1's acquisition crawler.
-- Postgres is a projection of Gold (CLAUDE.md rule 3): additive DDL only,
-- no data-fixing UPDATE/DELETE.

ALTER TABLE sources ADD COLUMN IF NOT EXISTS rate_limit_seconds INT NOT NULL DEFAULT 5;
