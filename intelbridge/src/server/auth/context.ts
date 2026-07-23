import { headers } from "next/headers";

import { DEMO_WORKSPACE_ID, getDatabase } from "@/server/db/client";
import type { UserRole } from "@/shared/domain";
import { getServerEnvironment } from "@/shared/schemas/environment";

export type AuthContext = {
  user: {
    email: string;
    id: string;
    name: string;
    role: UserRole;
  };
  workspace: {
    id: string;
    name: string;
  };
};

type AuthenticatedUserRow = {
  email: string;
  id: string;
  name: string;
  role: UserRole;
  workspace_id: string;
  workspace_name: string;
};

function decodeForwardedName(value: string | null, encoding: string | null) {
  if (!value || encoding !== "percent-encoded-utf-8") {
    return null;
  }

  try {
    return decodeURIComponent(value);
  } catch {
    return null;
  }
}

export async function getAuthContext(): Promise<AuthContext> {
  const requestHeaders = await headers();
  const environment = getServerEnvironment();
  const forwardedEmail = requestHeaders.get("oai-authenticated-user-email");
  const requestedEmail =
    forwardedEmail ??
    requestHeaders.get("x-intelbridge-user-email") ??
    environment.INTELBRIDGE_DEMO_USER_EMAIL;
  const forwardedName = decodeForwardedName(
    requestHeaders.get("oai-authenticated-user-full-name"),
    requestHeaders.get("oai-authenticated-user-full-name-encoding"),
  );
  const database = await getDatabase();

  let user = await database
    .prepare(
      `SELECT
        u.id,
        u.email,
        u.name,
        u.role,
        w.id AS workspace_id,
        w.name AS workspace_name
      FROM users u
      INNER JOIN workspaces w ON w.id = u.workspace_id
      WHERE u.email = ?
      LIMIT 1`,
    )
    .bind(requestedEmail)
    .first<AuthenticatedUserRow>();

  if (!user && forwardedEmail) {
    const userId = `user-${crypto.randomUUID()}`;
    const now = new Date().toISOString();
    await database
      .prepare(
        `INSERT INTO users
          (id, workspace_id, name, email, role, created_at, updated_at)
          VALUES (?, ?, ?, ?, ?, ?, ?)`,
      )
      .bind(
        userId,
        DEMO_WORKSPACE_ID,
        forwardedName ?? forwardedEmail,
        forwardedEmail,
        "ANALYST",
        now,
        now,
      )
      .run();

    user = await database
      .prepare(
        `SELECT
          u.id,
          u.email,
          u.name,
          u.role,
          w.id AS workspace_id,
          w.name AS workspace_name
        FROM users u
        INNER JOIN workspaces w ON w.id = u.workspace_id
        WHERE u.id = ?
        LIMIT 1`,
      )
      .bind(userId)
      .first<AuthenticatedUserRow>();
  }

  if (!user) {
    throw new Error("AUTH_USER_NOT_FOUND");
  }

  return {
    user: {
      email: user.email,
      id: user.id,
      name: user.name,
      role: user.role,
    },
    workspace: {
      id: user.workspace_id,
      name: user.workspace_name,
    },
  };
}
