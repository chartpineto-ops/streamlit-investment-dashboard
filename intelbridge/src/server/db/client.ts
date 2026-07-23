import { PrismaClient } from "@prisma/client";

import { getServerEnvironment } from "@/shared/schemas/environment";

const globalForPrisma = globalThis as unknown as {
  intelBridgePrisma?: PrismaClient;
};

function createPrismaClient() {
  const environment = getServerEnvironment();

  return new PrismaClient({
    datasources: {
      db: {
        url: environment.DATABASE_URL,
      },
    },
  });
}

export const prisma = globalForPrisma.intelBridgePrisma ?? createPrismaClient();

if (process.env.NODE_ENV !== "production") {
  globalForPrisma.intelBridgePrisma = prisma;
}
