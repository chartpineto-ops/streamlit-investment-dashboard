import type { Metadata } from "next";

import { ApplicationShell } from "@/components/application-shell";
import { getShellData } from "@/server/services/missions";

import "./globals.css";

export const metadata: Metadata = {
  description:
    "Evidence-backed research missions with persistent workspace context and inspectable provenance.",
  title: {
    default: "IntelBridge",
    template: "%s | IntelBridge",
  },
};

export const dynamic = "force-dynamic";

export default async function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  const { context, missionCount, projects } = await getShellData();

  return (
    <html lang="en">
      <body>
        <ApplicationShell
          missionCount={missionCount}
          projects={projects.map((project) => ({
            id: project.id,
            missionCount: project._count.missions,
            name: project.name,
          }))}
          user={context.user}
          workspace={context.workspace}
        >
          {children}
        </ApplicationShell>
      </body>
    </html>
  );
}
