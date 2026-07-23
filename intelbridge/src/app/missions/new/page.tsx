import { NewMissionForm } from "@/components/new-mission-form";
import { PageHeader } from "@/components/page-header";
import { getNewMissionData } from "@/server/services/missions";

export const metadata = {
  title: "New Mission",
};

export default async function NewMissionPage() {
  const { connectors, projects } = await getNewMissionData();

  return (
    <>
      <PageHeader
        description="Create the durable research objective and source policy. Starting a live collection run remains disabled until Milestone 2."
        eyebrow="Mission setup"
        title="Define a research mission"
      />
      <NewMissionForm connectors={connectors} projects={projects} />
    </>
  );
}
