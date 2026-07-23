import { CircleDashed } from "lucide-react";
import { notFound } from "next/navigation";

import { PageHeader } from "@/components/page-header";

const sections = {
  "agent-studio": {
    milestone: 5,
    purpose:
      "Inspect grounded agent configuration, prompt versions, and allow-listed tools.",
    title: "Agent Studio",
  },
  datasets: {
    milestone: 3,
    purpose:
      "Review normalized source documents and managed dataset boundaries.",
    title: "Datasets",
  },
  evidence: {
    milestone: 4,
    purpose:
      "Search source excerpts, validation state, claim links, and evidence relationships.",
    title: "Evidence",
  },
  insights: {
    milestone: 6,
    purpose:
      "Review supported findings, risks, opportunities, contradictions, and uncertainty.",
    title: "Insights",
  },
  monitoring: {
    milestone: 7,
    purpose:
      "Configure incremental schedules, materiality rules, and alert health.",
    title: "Monitoring",
  },
  projects: {
    milestone: 1,
    purpose: "Group durable missions under workspace-scoped research programs.",
    title: "Projects",
  },
  reports: {
    milestone: 6,
    purpose: "Generate executive briefs and evidence-backed export packages.",
    title: "Reports",
  },
  sources: {
    milestone: 3,
    purpose:
      "Connect approved sources, test retrieval access, and inspect checkpoints.",
    title: "Sources",
  },
} as const;

type PlaceholderPageProps = {
  params: Promise<{
    section: string;
  }>;
};

export default async function PlaceholderPage({
  params,
}: PlaceholderPageProps) {
  const { section } = await params;
  const sectionDefinition = sections[section as keyof typeof sections];

  if (!sectionDefinition) {
    notFound();
  }

  return (
    <>
      <PageHeader
        description={sectionDefinition.purpose}
        eyebrow="Planned workspace"
        title={sectionDefinition.title}
      />
      <section className="grid min-h-72 place-items-center rounded-[4px] border border-[var(--rule)] bg-[var(--surface-1)] p-8 text-center">
        <div>
          <CircleDashed
            aria-hidden="true"
            className="mx-auto size-7 text-[var(--text-3)]"
          />
          <h2 className="mb-0 mt-3 text-[13px] font-semibold">
            Scheduled for Milestone {sectionDefinition.milestone}
          </h2>
          <p className="mb-0 mt-1 max-w-lg text-[11px] leading-5 text-[var(--text-3)]">
            This route is present for stable navigation, but it does not display
            fabricated records or expose inactive controls. The underlying
            domain workflow will be connected in its scheduled milestone.
          </p>
        </div>
      </section>
    </>
  );
}
