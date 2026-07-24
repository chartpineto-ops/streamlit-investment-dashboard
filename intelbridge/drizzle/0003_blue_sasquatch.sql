CREATE TABLE `connector_checkpoints` (
	`checkpoint_key` text NOT NULL,
	`checkpoint_value` text NOT NULL,
	`connector_id` text NOT NULL,
	`id` text PRIMARY KEY NOT NULL,
	`updated_at` text NOT NULL,
	FOREIGN KEY (`connector_id`) REFERENCES `source_connectors`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `connector_checkpoints_connector_key_unique` ON `connector_checkpoints` (`connector_id`,`checkpoint_key`);--> statement-breakpoint
CREATE TABLE `job_queue` (
	`attempts` integer DEFAULT 0 NOT NULL,
	`available_at` text NOT NULL,
	`completed_at` text,
	`created_at` text NOT NULL,
	`dead_lettered_at` text,
	`id` text PRIMARY KEY NOT NULL,
	`idempotency_key` text NOT NULL,
	`last_error_code` text,
	`lease_expires_at` text,
	`max_attempts` integer DEFAULT 3 NOT NULL,
	`payload_json` text NOT NULL,
	`queue_name` text NOT NULL,
	`run_id` text NOT NULL,
	`status` text NOT NULL,
	`updated_at` text NOT NULL,
	FOREIGN KEY (`run_id`) REFERENCES `research_runs`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `job_queue_idempotency_key_unique` ON `job_queue` (`idempotency_key`);--> statement-breakpoint
CREATE INDEX `job_queue_claim_idx` ON `job_queue` (`queue_name`,`status`,`available_at`);--> statement-breakpoint
CREATE INDEX `job_queue_run_idx` ON `job_queue` (`run_id`);--> statement-breakpoint
CREATE TABLE `retrieval_failures` (
	`attempt` integer NOT NULL,
	`connector_id` text NOT NULL,
	`created_at` text NOT NULL,
	`error_code` text NOT NULL,
	`external_id` text,
	`id` text PRIMARY KEY NOT NULL,
	`research_run_id` text NOT NULL,
	`retryable` integer NOT NULL,
	`safe_message` text NOT NULL,
	`url` text,
	FOREIGN KEY (`connector_id`) REFERENCES `source_connectors`(`id`) ON UPDATE no action ON DELETE restrict,
	FOREIGN KEY (`research_run_id`) REFERENCES `research_runs`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `retrieval_failures_run_created_idx` ON `retrieval_failures` (`research_run_id`,`created_at`);--> statement-breakpoint
CREATE TABLE `source_document_versions` (
	`content_hash` text NOT NULL,
	`created_at` text NOT NULL,
	`id` text PRIMARY KEY NOT NULL,
	`language` text,
	`metadata_json` text NOT NULL,
	`mime_type` text NOT NULL,
	`normalized_content` text NOT NULL,
	`raw_content` text NOT NULL,
	`research_run_id` text,
	`retrieved_at` text NOT NULL,
	`source_document_id` text NOT NULL,
	`storage_key` text,
	`version_number` integer NOT NULL,
	FOREIGN KEY (`research_run_id`) REFERENCES `research_runs`(`id`) ON UPDATE no action ON DELETE set null,
	FOREIGN KEY (`source_document_id`) REFERENCES `source_documents`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `source_document_versions_document_version_unique` ON `source_document_versions` (`source_document_id`,`version_number`);--> statement-breakpoint
CREATE UNIQUE INDEX `source_document_versions_document_hash_unique` ON `source_document_versions` (`source_document_id`,`content_hash`);--> statement-breakpoint
CREATE INDEX `source_document_versions_run_idx` ON `source_document_versions` (`research_run_id`);--> statement-breakpoint
ALTER TABLE `connector_configurations` ADD `last_tested_at` text;--> statement-breakpoint
ALTER TABLE `connector_configurations` ADD `last_test_message` text;--> statement-breakpoint
ALTER TABLE `connector_configurations` ADD `response_time_ms` integer;--> statement-breakpoint
ALTER TABLE `mission_sources` ADD `created_at` text;--> statement-breakpoint
ALTER TABLE `mission_sources` ADD `exclusion_rules_json` text DEFAULT '[]' NOT NULL;--> statement-breakpoint
ALTER TABLE `mission_sources` ADD `inclusion_rules_json` text DEFAULT '[]' NOT NULL;--> statement-breakpoint
ALTER TABLE `research_runs` ADD `cancel_requested_at` text;--> statement-breakpoint
ALTER TABLE `research_runs` ADD `documents_created` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `research_runs` ADD `documents_discovered` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `research_runs` ADD `documents_unchanged` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `research_runs` ADD `documents_updated` integer DEFAULT 0 NOT NULL;--> statement-breakpoint
ALTER TABLE `research_runs` ADD `retry_of_run_id` text;--> statement-breakpoint
ALTER TABLE `research_runs` ADD `created_at` text;--> statement-breakpoint
ALTER TABLE `research_runs` ADD `updated_at` text;--> statement-breakpoint
ALTER TABLE `run_steps` ADD `attempt` integer DEFAULT 1 NOT NULL;--> statement-breakpoint
ALTER TABLE `run_steps` ADD `created_at` text;--> statement-breakpoint
ALTER TABLE `run_steps` ADD `error_code` text;--> statement-breakpoint
ALTER TABLE `run_steps` ADD `metadata_json` text DEFAULT '{}' NOT NULL;--> statement-breakpoint
ALTER TABLE `run_steps` ADD `step_type` text;--> statement-breakpoint
ALTER TABLE `run_steps` ADD `updated_at` text;--> statement-breakpoint
ALTER TABLE `source_documents` ADD `current_version_id` text;--> statement-breakpoint
ALTER TABLE `source_documents` ADD `first_retrieved_at` text;--> statement-breakpoint
ALTER TABLE `source_documents` ADD `last_research_run_id` text;--> statement-breakpoint
ALTER TABLE `source_documents` ADD `last_retrieved_at` text;--> statement-breakpoint
ALTER TABLE `source_documents` ADD `change_status` text DEFAULT 'CREATED' NOT NULL;--> statement-breakpoint
UPDATE `users`
SET `role` = CASE `role`
	WHEN 'OWNER' THEN 'ADMIN'
	WHEN 'ANALYST' THEN 'EDITOR'
	ELSE `role`
END
WHERE `role` IN ('OWNER', 'ANALYST');--> statement-breakpoint
UPDATE `source_connectors`
SET
	`type` = CASE `type`
		WHEN 'RSS_ATOM' THEN 'RSS'
		WHEN 'PUBLIC_WEB' THEN 'WEBPAGE'
		WHEN 'GITHUB_PUBLIC' THEN 'GITHUB'
		ELSE `type`
	END,
	`status` = CASE `status`
		WHEN 'AVAILABLE' THEN 'CONNECTED'
		WHEN 'NOT_CONNECTED' THEN 'DISCONNECTED'
		WHEN 'DEGRADED' THEN 'ERROR'
		ELSE `status`
	END;--> statement-breakpoint
UPDATE `missions`
SET `status` = CASE `status`
	WHEN 'ACTIVE' THEN 'READY'
	WHEN 'PAUSED' THEN 'DRAFT'
	ELSE `status`
END;--> statement-breakpoint
UPDATE `research_runs`
SET
	`status` = CASE WHEN `status` = 'ACTIVE' THEN 'RUNNING' ELSE `status` END,
	`created_at` = COALESCE(`created_at`, `started_at`),
	`updated_at` = COALESCE(`updated_at`, `completed_at`, `started_at`),
	`documents_discovered` = `documents_processed`,
	`documents_created` = `documents_processed`;--> statement-breakpoint
UPDATE `run_steps`
SET
	`step_type` = CASE `agent_type`
		WHEN 'PLANNER' THEN 'PLAN'
		WHEN 'RETRIEVAL' THEN 'RETRIEVE'
		ELSE `agent_type`
	END,
	`created_at` = COALESCE(`created_at`, `started_at`),
	`updated_at` = COALESCE(`updated_at`, `completed_at`, `started_at`);--> statement-breakpoint
UPDATE `mission_sources`
SET `created_at` = COALESCE(`created_at`, '2026-07-23T00:00:00.000Z');--> statement-breakpoint
UPDATE `source_documents`
SET
	`first_retrieved_at` = COALESCE(`first_retrieved_at`, `retrieved_at`),
	`last_retrieved_at` = COALESCE(`last_retrieved_at`, `retrieved_at`);--> statement-breakpoint
INSERT OR IGNORE INTO `source_document_versions`
	(`id`, `source_document_id`, `research_run_id`, `version_number`,
	 `content_hash`, `raw_content`, `normalized_content`, `mime_type`,
	 `language`, `metadata_json`, `storage_key`, `retrieved_at`, `created_at`)
SELECT
	'version-' || `id`,
	`id`,
	`last_research_run_id`,
	`version`,
	`content_hash`,
	`raw_content`,
	`normalized_content`,
	`source_type`,
	'en',
	`metadata_json`,
	NULL,
	`retrieved_at`,
	`retrieved_at`
FROM `source_documents`;--> statement-breakpoint
UPDATE `source_documents`
SET `current_version_id` = 'version-' || `id`
WHERE `current_version_id` IS NULL;--> statement-breakpoint
CREATE INDEX `source_documents_workspace_connector_idx` ON `source_documents` (`workspace_id`,`connector_id`);--> statement-breakpoint
CREATE INDEX `source_documents_last_retrieved_idx` ON `source_documents` (`workspace_id`,`last_retrieved_at`);
