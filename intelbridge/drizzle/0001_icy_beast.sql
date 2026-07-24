CREATE TABLE `agent_definitions` (
	`agent_type` text NOT NULL,
	`allowed_tools_json` text NOT NULL,
	`id` text PRIMARY KEY NOT NULL,
	`model` text NOT NULL,
	`name` text NOT NULL,
	`output_schema` text NOT NULL,
	`prompt_name` text NOT NULL,
	`prompt_version` text NOT NULL,
	`purpose` text NOT NULL,
	`status` text NOT NULL,
	`updated_at` text NOT NULL,
	`workspace_id` text NOT NULL,
	FOREIGN KEY (`workspace_id`) REFERENCES `workspaces`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `agent_definitions_workspace_type_unique` ON `agent_definitions` (`workspace_id`,`agent_type`);--> statement-breakpoint
CREATE TABLE `alerts` (
	`alert_type` text NOT NULL,
	`created_at` text NOT NULL,
	`delivered_at` text,
	`id` text PRIMARY KEY NOT NULL,
	`insight_id` text,
	`materiality_score` real NOT NULL,
	`monitor_id` text NOT NULL,
	`status` text NOT NULL,
	`summary` text NOT NULL,
	`title` text NOT NULL,
	FOREIGN KEY (`insight_id`) REFERENCES `insights`(`id`) ON UPDATE no action ON DELETE set null,
	FOREIGN KEY (`monitor_id`) REFERENCES `monitors`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `alerts_monitor_created_idx` ON `alerts` (`monitor_id`,`created_at`);--> statement-breakpoint
CREATE TABLE `audit_logs` (
	`action` text NOT NULL,
	`created_at` text NOT NULL,
	`details_json` text NOT NULL,
	`entity_id` text NOT NULL,
	`entity_type` text NOT NULL,
	`id` text PRIMARY KEY NOT NULL,
	`request_id` text NOT NULL,
	`user_id` text,
	`workspace_id` text NOT NULL,
	FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE set null,
	FOREIGN KEY (`workspace_id`) REFERENCES `workspaces`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `audit_logs_workspace_created_idx` ON `audit_logs` (`workspace_id`,`created_at`);--> statement-breakpoint
CREATE TABLE `claim_evidence` (
	`claim_id` text NOT NULL,
	`evidence_id` text NOT NULL,
	`relationship` text NOT NULL,
	`support_strength` real NOT NULL,
	PRIMARY KEY(`claim_id`, `evidence_id`),
	FOREIGN KEY (`claim_id`) REFERENCES `claims`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`evidence_id`) REFERENCES `evidence`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `claim_evidence_evidence_idx` ON `claim_evidence` (`evidence_id`);--> statement-breakpoint
CREATE TABLE `claims` (
	`calculation_factors_json` text NOT NULL,
	`claim_type` text NOT NULL,
	`confidence_score` real NOT NULL,
	`data_status` text NOT NULL,
	`first_observed_at` text NOT NULL,
	`id` text PRIMARY KEY NOT NULL,
	`is_demo` integer NOT NULL,
	`last_observed_at` text NOT NULL,
	`materiality_score` real NOT NULL,
	`mission_id` text NOT NULL,
	`statement` text NOT NULL,
	`status` text NOT NULL,
	FOREIGN KEY (`mission_id`) REFERENCES `missions`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `claims_mission_statement_unique` ON `claims` (`mission_id`,`statement`);--> statement-breakpoint
CREATE INDEX `claims_mission_materiality_idx` ON `claims` (`mission_id`,`materiality_score`);--> statement-breakpoint
CREATE TABLE `connector_configurations` (
	`checkpoint_json` text,
	`configuration_json` text NOT NULL,
	`connector_id` text PRIMARY KEY NOT NULL,
	`last_error_at` text,
	`last_successful_sync_at` text,
	`updated_at` text NOT NULL,
	FOREIGN KEY (`connector_id`) REFERENCES `source_connectors`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE TABLE `evidence` (
	`confidence_score` real NOT NULL,
	`content_hash` text NOT NULL,
	`context_text` text NOT NULL,
	`data_status` text NOT NULL,
	`entities_json` text NOT NULL,
	`event_date` text,
	`evidence_type` text NOT NULL,
	`excerpt` text NOT NULL,
	`extracted_at` text NOT NULL,
	`id` text PRIMARY KEY NOT NULL,
	`is_demo` integer NOT NULL,
	`mission_id` text NOT NULL,
	`normalized_claim` text NOT NULL,
	`novelty_score` real NOT NULL,
	`relationship` text NOT NULL,
	`relevance_score` real NOT NULL,
	`research_run_id` text NOT NULL,
	`source_document_id` text NOT NULL,
	`source_quality_score` real NOT NULL,
	`topics_json` text NOT NULL,
	`validation_status` text NOT NULL,
	FOREIGN KEY (`mission_id`) REFERENCES `missions`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`research_run_id`) REFERENCES `research_runs`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`source_document_id`) REFERENCES `source_documents`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `evidence_document_hash_unique` ON `evidence` (`source_document_id`,`content_hash`);--> statement-breakpoint
CREATE INDEX `evidence_mission_extracted_idx` ON `evidence` (`mission_id`,`extracted_at`);--> statement-breakpoint
CREATE INDEX `evidence_validation_idx` ON `evidence` (`mission_id`,`validation_status`);--> statement-breakpoint
CREATE TABLE `insight_claims` (
	`claim_id` text NOT NULL,
	`importance` integer NOT NULL,
	`insight_id` text NOT NULL,
	PRIMARY KEY(`insight_id`, `claim_id`),
	FOREIGN KEY (`claim_id`) REFERENCES `claims`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`insight_id`) REFERENCES `insights`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE TABLE `insights` (
	`assumptions_json` text NOT NULL,
	`calculation_refs_json` text NOT NULL,
	`category` text NOT NULL,
	`confidence_score` real NOT NULL,
	`created_at` text NOT NULL,
	`data_status` text NOT NULL,
	`id` text PRIMARY KEY NOT NULL,
	`is_demo` integer NOT NULL,
	`materiality_score` real NOT NULL,
	`mission_id` text NOT NULL,
	`novelty_score` real NOT NULL,
	`owner` text NOT NULL,
	`recommended_action` text NOT NULL,
	`research_run_id` text NOT NULL,
	`severity` text NOT NULL,
	`status` text NOT NULL,
	`summary` text NOT NULL,
	`title` text NOT NULL,
	`uncertainty_note` text NOT NULL,
	`updated_at` text NOT NULL,
	FOREIGN KEY (`mission_id`) REFERENCES `missions`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`research_run_id`) REFERENCES `research_runs`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `insights_mission_materiality_idx` ON `insights` (`mission_id`,`materiality_score`);--> statement-breakpoint
CREATE TABLE `monitors` (
	`alert_cooldown_minutes` integer NOT NULL,
	`contradiction_alerts` integer NOT NULL,
	`entity_watchlist_json` text NOT NULL,
	`id` text PRIMARY KEY NOT NULL,
	`last_checked_at` text,
	`materiality_threshold` real NOT NULL,
	`minimum_confidence` real NOT NULL,
	`mission_id` text NOT NULL,
	`next_check_at` text,
	`required_source_count` integer NOT NULL,
	`schedule` text NOT NULL,
	`source_failure_alerts` integer NOT NULL,
	`status` text NOT NULL,
	`topic_allowlist_json` text NOT NULL,
	`topic_blocklist_json` text NOT NULL,
	`updated_at` text NOT NULL,
	FOREIGN KEY (`mission_id`) REFERENCES `missions`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `monitors_mission_id_unique` ON `monitors` (`mission_id`);--> statement-breakpoint
CREATE INDEX `monitors_status_next_check_idx` ON `monitors` (`status`,`next_check_at`);--> statement-breakpoint
CREATE TABLE `question_history` (
	`answer` text NOT NULL,
	`confidence_score` real NOT NULL,
	`created_at` text NOT NULL,
	`evidence_ids_json` text NOT NULL,
	`id` text PRIMARY KEY NOT NULL,
	`limitations` text NOT NULL,
	`mission_id` text NOT NULL,
	`question` text NOT NULL,
	`user_id` text NOT NULL,
	`workspace_id` text NOT NULL,
	FOREIGN KEY (`mission_id`) REFERENCES `missions`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`user_id`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE restrict,
	FOREIGN KEY (`workspace_id`) REFERENCES `workspaces`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE TABLE `reports` (
	`content` text NOT NULL,
	`data_status` text NOT NULL,
	`generated_at` text NOT NULL,
	`generated_by_id` text NOT NULL,
	`id` text PRIMARY KEY NOT NULL,
	`is_demo` integer NOT NULL,
	`mission_id` text NOT NULL,
	`research_run_id` text,
	`status` text NOT NULL,
	`title` text NOT NULL,
	`type` text NOT NULL,
	FOREIGN KEY (`generated_by_id`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE restrict,
	FOREIGN KEY (`mission_id`) REFERENCES `missions`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`research_run_id`) REFERENCES `research_runs`(`id`) ON UPDATE no action ON DELETE set null
);
--> statement-breakpoint
CREATE INDEX `reports_mission_generated_idx` ON `reports` (`mission_id`,`generated_at`);--> statement-breakpoint
CREATE TABLE `research_runs` (
	`completed_at` text,
	`confidence_score` real,
	`created_by_id` text NOT NULL,
	`data_status` text NOT NULL,
	`documents_processed` integer DEFAULT 0 NOT NULL,
	`error_summary` text,
	`evidence_created` integer DEFAULT 0 NOT NULL,
	`id` text PRIMARY KEY NOT NULL,
	`insights_created` integer DEFAULT 0 NOT NULL,
	`is_demo` integer NOT NULL,
	`mission_id` text NOT NULL,
	`model_provider` text NOT NULL,
	`progress_percent` integer DEFAULT 0 NOT NULL,
	`prompt_version` text NOT NULL,
	`sources_scanned` integer DEFAULT 0 NOT NULL,
	`started_at` text NOT NULL,
	`status` text NOT NULL,
	`trigger_type` text NOT NULL,
	FOREIGN KEY (`created_by_id`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE restrict,
	FOREIGN KEY (`mission_id`) REFERENCES `missions`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `research_runs_mission_started_idx` ON `research_runs` (`mission_id`,`started_at`);--> statement-breakpoint
CREATE TABLE `run_events` (
	`created_at` text NOT NULL,
	`event_type` text NOT NULL,
	`id` integer PRIMARY KEY AUTOINCREMENT NOT NULL,
	`payload_json` text NOT NULL,
	`research_run_id` text NOT NULL,
	`sequence_number` integer NOT NULL,
	FOREIGN KEY (`research_run_id`) REFERENCES `research_runs`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `run_events_run_sequence_unique` ON `run_events` (`research_run_id`,`sequence_number`);--> statement-breakpoint
CREATE INDEX `run_events_run_sequence_idx` ON `run_events` (`research_run_id`,`sequence_number`);--> statement-breakpoint
CREATE TABLE `run_steps` (
	`agent_type` text NOT NULL,
	`completed_at` text,
	`duration_ms` integer,
	`error_message` text,
	`id` text PRIMARY KEY NOT NULL,
	`input_summary` text NOT NULL,
	`name` text NOT NULL,
	`output_summary` text,
	`progress_percent` integer DEFAULT 0 NOT NULL,
	`research_run_id` text NOT NULL,
	`sequence_number` integer NOT NULL,
	`started_at` text,
	`status` text NOT NULL,
	`token_usage` integer DEFAULT 0 NOT NULL,
	`tool_name` text NOT NULL,
	FOREIGN KEY (`research_run_id`) REFERENCES `research_runs`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `run_steps_run_sequence_unique` ON `run_steps` (`research_run_id`,`sequence_number`);--> statement-breakpoint
CREATE INDEX `run_steps_run_status_idx` ON `run_steps` (`research_run_id`,`status`);--> statement-breakpoint
CREATE TABLE `source_documents` (
	`author` text,
	`canonical_url` text NOT NULL,
	`connector_id` text NOT NULL,
	`content_hash` text NOT NULL,
	`data_status` text NOT NULL,
	`external_id` text NOT NULL,
	`id` text PRIMARY KEY NOT NULL,
	`is_demo` integer NOT NULL,
	`metadata_json` text NOT NULL,
	`mission_id` text NOT NULL,
	`normalized_content` text NOT NULL,
	`prompt_injection_flag` integer DEFAULT 0 NOT NULL,
	`published_at` text NOT NULL,
	`publisher` text NOT NULL,
	`raw_content` text NOT NULL,
	`retrieved_at` text NOT NULL,
	`source_type` text NOT NULL,
	`title` text NOT NULL,
	`trust_state` text NOT NULL,
	`version` integer NOT NULL,
	`workspace_id` text NOT NULL,
	FOREIGN KEY (`connector_id`) REFERENCES `source_connectors`(`id`) ON UPDATE no action ON DELETE restrict,
	FOREIGN KEY (`mission_id`) REFERENCES `missions`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`workspace_id`) REFERENCES `workspaces`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `source_documents_workspace_url_version_unique` ON `source_documents` (`workspace_id`,`canonical_url`,`version`);--> statement-breakpoint
CREATE INDEX `source_documents_mission_retrieved_idx` ON `source_documents` (`mission_id`,`retrieved_at`);--> statement-breakpoint
CREATE INDEX `source_documents_content_hash_idx` ON `source_documents` (`content_hash`);