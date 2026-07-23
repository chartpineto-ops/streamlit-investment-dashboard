CREATE TABLE `mission_sources` (
	`mission_id` text NOT NULL,
	`priority` integer DEFAULT 50 NOT NULL,
	`source_connector_id` text NOT NULL,
	PRIMARY KEY(`mission_id`, `source_connector_id`),
	FOREIGN KEY (`mission_id`) REFERENCES `missions`(`id`) ON UPDATE no action ON DELETE cascade,
	FOREIGN KEY (`source_connector_id`) REFERENCES `source_connectors`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `mission_sources_connector_idx` ON `mission_sources` (`source_connector_id`);--> statement-breakpoint
CREATE TABLE `missions` (
	`created_at` text NOT NULL,
	`created_by_id` text NOT NULL,
	`id` text PRIMARY KEY NOT NULL,
	`monitoring_interval` integer,
	`monitoring_mode` text NOT NULL,
	`objective` text NOT NULL,
	`project_id` text NOT NULL,
	`research_depth` text NOT NULL,
	`scope_json` text NOT NULL,
	`status` text NOT NULL,
	`title` text NOT NULL,
	`updated_at` text NOT NULL,
	FOREIGN KEY (`created_by_id`) REFERENCES `users`(`id`) ON UPDATE no action ON DELETE restrict,
	FOREIGN KEY (`project_id`) REFERENCES `projects`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE INDEX `missions_project_status_idx` ON `missions` (`project_id`,`status`);--> statement-breakpoint
CREATE INDEX `missions_created_by_idx` ON `missions` (`created_by_id`);--> statement-breakpoint
CREATE INDEX `missions_updated_at_idx` ON `missions` (`updated_at`);--> statement-breakpoint
CREATE TABLE `projects` (
	`created_at` text NOT NULL,
	`description` text NOT NULL,
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`status` text NOT NULL,
	`updated_at` text NOT NULL,
	`workspace_id` text NOT NULL,
	FOREIGN KEY (`workspace_id`) REFERENCES `workspaces`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `projects_workspace_name_unique` ON `projects` (`workspace_id`,`name`);--> statement-breakpoint
CREATE INDEX `projects_workspace_status_idx` ON `projects` (`workspace_id`,`status`);--> statement-breakpoint
CREATE TABLE `source_connectors` (
	`created_at` text NOT NULL,
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`status` text NOT NULL,
	`type` text NOT NULL,
	`updated_at` text NOT NULL,
	`workspace_id` text NOT NULL,
	FOREIGN KEY (`workspace_id`) REFERENCES `workspaces`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `source_connectors_workspace_name_unique` ON `source_connectors` (`workspace_id`,`name`);--> statement-breakpoint
CREATE INDEX `source_connectors_workspace_type_status_idx` ON `source_connectors` (`workspace_id`,`type`,`status`);--> statement-breakpoint
CREATE TABLE `users` (
	`created_at` text NOT NULL,
	`email` text NOT NULL,
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`role` text NOT NULL,
	`updated_at` text NOT NULL,
	`workspace_id` text NOT NULL,
	FOREIGN KEY (`workspace_id`) REFERENCES `workspaces`(`id`) ON UPDATE no action ON DELETE cascade
);
--> statement-breakpoint
CREATE UNIQUE INDEX `users_email_unique` ON `users` (`email`);--> statement-breakpoint
CREATE INDEX `users_workspace_role_idx` ON `users` (`workspace_id`,`role`);--> statement-breakpoint
CREATE TABLE `workspaces` (
	`created_at` text NOT NULL,
	`id` text PRIMARY KEY NOT NULL,
	`name` text NOT NULL,
	`updated_at` text NOT NULL
);
--> statement-breakpoint
CREATE INDEX `workspaces_name_idx` ON `workspaces` (`name`);