import type { Metadata } from "next";

import { ApplicationShell } from "@/components/application-shell";
import { getShellData } from "@/server/services/missions";

import "./globals.css";

export const metadata: Metadata = {
  description:
    "Persistent intelligence operations with research runs, evidence, claims, insights, monitoring, reports, and inspectable provenance.",
  openGraph: {
    description:
      "Turn approved sources into validated, traceable, decision-ready intelligence.",
    images: [
      {
        alt: "IntelBridge evidence-to-decision workflow",
        height: 921,
        url: "/og.png",
        width: 1792,
      },
    ],
    title: "IntelBridge · Evidence to decision",
    type: "website",
  },
  title: {
    default: "IntelBridge",
    template: "%s | IntelBridge",
  },
  twitter: {
    card: "summary_large_image",
    description:
      "Turn approved sources into validated, traceable, decision-ready intelligence.",
    images: ["/og.png"],
    title: "IntelBridge · Evidence to decision",
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
