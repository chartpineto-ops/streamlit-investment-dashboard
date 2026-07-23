import { headers } from "next/headers";

import { prisma } from "@/server/db/client";
import { getServerEnvironment } from "@/shared/schemas/environment";

export type AuthContext = {
  user: {
    email: string;
    id: string;
    name: string;
    role: "OWNER" | "ADMIN" | "ANALYST" | "VIEWER";
  };
  workspace: {
    id: string;
    name: string;
  };
};

export async function getAuthContext(): Promise<AuthContext> {
  const requestHeaders = await headers();
  const environment = getServerEnvironment();
  const requestedEmail =
    requestHeaders.get("x-intelbridge-user-email") ??
    environment.INTELBRIDGE_DEMO_USER_EMAIL;

  const user = await prisma.user.findUnique({
    where: { email: requestedEmail },
    select: {
      email: true,
      id: true,
      name: true,
      role: true,
      workspace: {
        select: {
          id: true,
          name: true,
        },
      },
    },
  });

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
    workspace: user.workspace,
  };
}
