ALTER TABLE `research_runs` ADD `idempotency_key` text;--> statement-breakpoint
UPDATE `research_runs`
SET `idempotency_key` = 'legacy:' || `id`
WHERE `idempotency_key` IS NULL;--> statement-breakpoint
CREATE UNIQUE INDEX `research_runs_idempotency_key_unique` ON `research_runs` (`idempotency_key`);
