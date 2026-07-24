import { getReportForCurrentWorkspace } from "@/server/services/intelligence";

export const dynamic = "force-dynamic";

export async function GET(
  _request: Request,
  { params }: { params: Promise<{ reportId: string }> },
) {
  const { reportId } = await params;
  const report = await getReportForCurrentWorkspace(reportId);

  if (!report) {
    return Response.json(
      { code: "REPORT_NOT_FOUND", message: "Report not found." },
      { status: 404 },
    );
  }

  const extension =
    report.type === "EVIDENCE_CSV" || report.type === "COMPETITOR_MATRIX"
      ? "csv"
      : report.type === "JSON_PACKAGE"
        ? "json"
        : "md";
  const contentType =
    extension === "csv"
      ? "text/csv"
      : extension === "json"
        ? "application/json"
        : "text/markdown";
  const filename = `${report.title
    .toLowerCase()
    .replace(/[^a-z0-9]+/g, "-")
    .replace(/^-|-$/g, "")}.${extension}`;

  return new Response(report.content, {
    headers: {
      "Cache-Control": "private, no-store",
      "Content-Disposition": `attachment; filename="${filename}"`,
      "Content-Type": `${contentType}; charset=utf-8`,
    },
  });
}
