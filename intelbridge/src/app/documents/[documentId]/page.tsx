import { notFound } from "next/navigation";

import { DocumentDetail } from "@/components/operations-workspaces";
import { getDocumentForCurrentWorkspace } from "@/server/services/documents";

export default async function DocumentPage({
  params,
  searchParams,
}: {
  params: Promise<{ documentId: string }>;
  searchParams: Promise<Record<string, string | string[] | undefined>>;
}) {
  const [{ documentId }, query] = await Promise.all([params, searchParams]);
  const detail = await getDocumentForCurrentWorkspace(documentId);
  if (!detail) notFound();
  return (
    <DocumentDetail
      detail={detail}
      selectedVersionId={
        typeof query.version === "string" ? query.version : undefined
      }
    />
  );
}
