import {
  ConnectorStatus,
  ConnectorType,
  MissionStatus,
  MonitoringMode,
  Prisma,
  PrismaClient,
  ProjectStatus,
  ResearchDepth,
  UserRole,
} from "@prisma/client";

const prisma = new PrismaClient();

const ids = {
  workspace: "workspace-intelbridge-demo",
  users: {
    alex: "user-alex-parker",
    maya: "user-maya-chen",
  },
  projects: {
    competitive: "project-competitive-intelligence",
    marketEntry: "project-market-entry",
    product: "project-product-strategy",
  },
  connectors: {
    demo: "connector-demo",
    rss: "connector-rss",
    web: "connector-public-web",
    manual: "connector-manual-url",
    upload: "connector-file-upload",
    github: "connector-github-public",
  },
  missions: {
    enterpriseSearch: "mission-enterprise-search",
    midMarket: "mission-mid-market",
    developerPlatforms: "mission-developer-platforms",
  },
} as const;

const fixedCreatedAt = new Date("2026-07-15T13:00:00.000Z");
const fixedUpdatedAt = new Date("2026-07-22T18:30:00.000Z");

async function seedWorkspace() {
  await prisma.workspace.upsert({
    where: { id: ids.workspace },
    update: {
      name: "IntelBridge Demo Workspace",
      updatedAt: fixedUpdatedAt,
    },
    create: {
      id: ids.workspace,
      name: "IntelBridge Demo Workspace",
      createdAt: fixedCreatedAt,
      updatedAt: fixedUpdatedAt,
    },
  });
}

async function seedUsers() {
  const users = [
    {
      id: ids.users.alex,
      name: "Alex Parker",
      email: "alex.parker@intelbridge.demo",
      role: UserRole.OWNER,
    },
    {
      id: ids.users.maya,
      name: "Maya Chen",
      email: "maya.chen@intelbridge.demo",
      role: UserRole.ANALYST,
    },
  ];

  for (const user of users) {
    await prisma.user.upsert({
      where: { email: user.email },
      update: {
        name: user.name,
        role: user.role,
        workspaceId: ids.workspace,
        updatedAt: fixedUpdatedAt,
      },
      create: {
        ...user,
        workspaceId: ids.workspace,
        createdAt: fixedCreatedAt,
        updatedAt: fixedUpdatedAt,
      },
    });
  }
}

async function seedProjects() {
  const projects = [
    {
      id: ids.projects.competitive,
      name: "Competitive Intelligence",
      description:
        "Track product, pricing, and go-to-market changes across the enterprise search market.",
    },
    {
      id: ids.projects.marketEntry,
      name: "Market Entry",
      description:
        "Evaluate underserved customer segments and evidence-backed routes to market.",
    },
    {
      id: ids.projects.product,
      name: "Product Strategy",
      description:
        "Maintain a durable record of capability gaps, customer implications, and roadmap choices.",
    },
  ];

  for (const project of projects) {
    await prisma.project.upsert({
      where: {
        workspaceId_name: {
          workspaceId: ids.workspace,
          name: project.name,
        },
      },
      update: {
        description: project.description,
        status: ProjectStatus.ACTIVE,
        updatedAt: fixedUpdatedAt,
      },
      create: {
        ...project,
        workspaceId: ids.workspace,
        status: ProjectStatus.ACTIVE,
        createdAt: fixedCreatedAt,
        updatedAt: fixedUpdatedAt,
      },
    });
  }
}

async function seedConnectors() {
  const connectors = [
    {
      id: ids.connectors.demo,
      name: "Deterministic demo corpus",
      type: ConnectorType.DEMO,
      status: ConnectorStatus.AVAILABLE,
    },
    {
      id: ids.connectors.rss,
      name: "RSS and Atom feeds",
      type: ConnectorType.RSS_ATOM,
      status: ConnectorStatus.NOT_CONNECTED,
    },
    {
      id: ids.connectors.web,
      name: "Approved public webpages",
      type: ConnectorType.PUBLIC_WEB,
      status: ConnectorStatus.NOT_CONNECTED,
    },
    {
      id: ids.connectors.manual,
      name: "Manual URL submissions",
      type: ConnectorType.MANUAL_URL,
      status: ConnectorStatus.NOT_CONNECTED,
    },
    {
      id: ids.connectors.upload,
      name: "Uploaded documents",
      type: ConnectorType.FILE_UPLOAD,
      status: ConnectorStatus.NOT_CONNECTED,
    },
    {
      id: ids.connectors.github,
      name: "GitHub public repositories",
      type: ConnectorType.GITHUB_PUBLIC,
      status: ConnectorStatus.NOT_CONNECTED,
    },
  ];

  for (const connector of connectors) {
    await prisma.sourceConnector.upsert({
      where: {
        workspaceId_name: {
          workspaceId: ids.workspace,
          name: connector.name,
        },
      },
      update: {
        type: connector.type,
        status: connector.status,
        configurationEncrypted: null,
        updatedAt: fixedUpdatedAt,
      },
      create: {
        ...connector,
        workspaceId: ids.workspace,
        configurationEncrypted: null,
        createdAt: fixedCreatedAt,
        updatedAt: fixedUpdatedAt,
      },
    });
  }
}

type SeedMission = {
  id: string;
  projectId: string;
  title: string;
  objective: string;
  scope: Prisma.InputJsonValue;
  status: MissionStatus;
  researchDepth: ResearchDepth;
  monitoringMode: MonitoringMode;
  monitoringInterval: number | null;
  createdById: string;
};

async function seedMissions() {
  const missions: SeedMission[] = [
    {
      id: ids.missions.enterpriseSearch,
      projectId: ids.projects.competitive,
      title: "Enterprise search launch impact",
      objective:
        "Assess how recent competitor launches in enterprise search affect the product roadmap and identify capability gaps, customer implications, and recommended actions.",
      scope: {
        focusAreas: ["Products", "Pricing", "Go-to-market"],
        timeHorizonMonths: 12,
        regions: ["North America", "Europe"],
      },
      status: MissionStatus.READY,
      researchDepth: ResearchDepth.DEEP,
      monitoringMode: MonitoringMode.MANUAL,
      monitoringInterval: null,
      createdById: ids.users.alex,
    },
    {
      id: ids.missions.midMarket,
      projectId: ids.projects.marketEntry,
      title: "Mid-market buyer requirements",
      objective:
        "Identify unresolved information-retrieval needs among teams with 200 to 1,000 employees and map the evidence to pricing and packaging decisions.",
      scope: {
        focusAreas: ["Customer needs", "Pricing", "Adoption barriers"],
        timeHorizonMonths: 18,
        regions: ["United States"],
      },
      status: MissionStatus.PAUSED,
      researchDepth: ResearchDepth.STANDARD,
      monitoringMode: MonitoringMode.WEEKLY,
      monitoringInterval: 10080,
      createdById: ids.users.maya,
    },
    {
      id: ids.missions.developerPlatforms,
      projectId: ids.projects.product,
      title: "Developer platform capability baseline",
      objective:
        "Establish an evidence-backed baseline for retrieval APIs, deployment controls, and observability across approved developer platforms.",
      scope: {
        focusAreas: ["APIs", "Deployment", "Observability"],
        timeHorizonMonths: 6,
        regions: ["Global"],
      },
      status: MissionStatus.DRAFT,
      researchDepth: ResearchDepth.RAPID,
      monitoringMode: MonitoringMode.MANUAL,
      monitoringInterval: null,
      createdById: ids.users.alex,
    },
  ];

  for (const mission of missions) {
    await prisma.mission.upsert({
      where: { id: mission.id },
      update: {
        ...mission,
        updatedAt: fixedUpdatedAt,
      },
      create: {
        ...mission,
        createdAt: fixedCreatedAt,
        updatedAt: fixedUpdatedAt,
      },
    });
  }

  const sourceLinks = [
    [ids.missions.enterpriseSearch, ids.connectors.demo, 100],
    [ids.missions.midMarket, ids.connectors.demo, 100],
    [ids.missions.developerPlatforms, ids.connectors.demo, 100],
  ] as const;

  for (const [missionId, sourceConnectorId, priority] of sourceLinks) {
    await prisma.missionSource.upsert({
      where: {
        missionId_sourceConnectorId: {
          missionId,
          sourceConnectorId,
        },
      },
      update: {
        priority,
        inclusionRules: { mode: "deterministic-demo-only" },
        exclusionRules: Prisma.JsonNull,
      },
      create: {
        missionId,
        sourceConnectorId,
        priority,
        inclusionRules: { mode: "deterministic-demo-only" },
      },
    });
  }
}

async function main() {
  await seedWorkspace();
  await seedUsers();
  await seedProjects();
  await seedConnectors();
  await seedMissions();

  const [
    workspaceCount,
    userCount,
    projectCount,
    connectorCount,
    missionCount,
  ] = await Promise.all([
    prisma.workspace.count(),
    prisma.user.count({ where: { workspaceId: ids.workspace } }),
    prisma.project.count({ where: { workspaceId: ids.workspace } }),
    prisma.sourceConnector.count({ where: { workspaceId: ids.workspace } }),
    prisma.mission.count({
      where: { project: { workspaceId: ids.workspace } },
    }),
  ]);

  console.log(
    JSON.stringify({
      workspaceCount,
      userCount,
      projectCount,
      connectorCount,
      missionCount,
    }),
  );
}

main()
  .catch((error: unknown) => {
    console.error(error);
    process.exitCode = 1;
  })
  .finally(async () => {
    await prisma.$disconnect();
  });
