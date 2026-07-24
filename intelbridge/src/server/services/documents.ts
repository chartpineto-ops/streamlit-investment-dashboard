import { getAuthContext } from "@/server/auth/context";
import {
  getWorkspaceDocument,
  getWorkspaceDocumentVersion,
  listWorkspaceDocuments,
} from "@/server/repositories/documents";
import { listWorkspaceConnectors } from "@/server/repositories/foundation";
import { listMissions } from "@/server/repositories/missions";
import { documentListQuerySchema } from "@/shared/schemas/platform";

export async function listDocumentsForCurrentWorkspace(values: unknown = {}) {
  const context = await getAuthContext();
  const filters = documentListQuerySchema.parse(values);
  return listWorkspaceDocuments(context.workspace.id, filters);
}

export async function getDocumentForCurrentWorkspace(documentId: string) {
  const context = await getAuthContext();
  return getWorkspaceDocument(context.workspace.id, documentId);
}

export async function getDocumentVersionForCurrentWorkspace(
  documentId: string,
  versionId: string,
) {
  const context = await getAuthContext();
  return getWorkspaceDocumentVersion(
    context.workspace.id,
    documentId,
    versionId,
  );
}

export async function getDocumentsWorkspaceData(values: unknown = {}) {
  const context = await getAuthContext();
  const filters = documentListQuerySchema.parse(values);
  return {
    connectors: await listWorkspaceConnectors(context.workspace.id),
    context,
    documents: await listWorkspaceDocuments(context.workspace.id, filters),
    missions: await listMissions(context.workspace.id),
  };
}
