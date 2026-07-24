import type { Metadata } from "next";

import { ApplicationShell } from "@/components/application-shell";
import { getShellData } from "@/server/services/missions";

import "./globals.css";

export const metadata: Metadata = {
  description:
    "Persistent research operations with projects, missions, queued ingestion runs, governed connectors, and versioned source documents.",
  openGraph: {
    description:
      "Run governed research ingestion with durable events and versioned source documents.",
    images: [
      {
        alt: "IntelBridge evidence-to-decision workflow",
        height: 921,
        url: "/og.png",
        width: 1792,
      },
    ],
    title: "IntelBridge · Research operations",
    type: "website",
  },
  title: {
    default: "IntelBridge",
    template: "%s | IntelBridge",
  },
  twitter: {
    card: "summary_large_image",
    description:
      "Run governed research ingestion with durable events and versioned source documents.",
    images: ["/og.png"],
    title: "IntelBridge · Research operations",
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
