import {
  containsPromptInjectionPattern,
  stripUntrustedMarkup,
} from "@/server/connectors/security";
import { sha256 } from "@/server/repositories/documents";
import type {
  NormalizedDocument,
  RetrievedDocument,
} from "@/server/connectors/types";

function decodeEntities(value: string) {
  return value
    .replace(/<!\[CDATA\[([\s\S]*?)\]\]>/g, "$1")
    .replace(/&apos;/g, "'")
    .replace(/&quot;/g, '"')
    .replace(/&gt;/g, ">")
    .replace(/&lt;/g, "<")
    .replace(/&amp;/g, "&");
}

export function extractPdfText(value: string) {
  if (!value.startsWith("%PDF-")) {
    throw new Error("SOURCE_PDF_MALFORMED");
  }
  if (/\/Encrypt\b/.test(value)) {
    throw new Error("SOURCE_PDF_ENCRYPTED");
  }
  const pageCount = Math.max(
    1,
    [...value.matchAll(/\/Type\s*\/Page\b/g)].length,
  );
  const parts = [...value.matchAll(/\(((?:\\.|[^\\)])*)\)\s*Tj/g)].map(
    (match) =>
      match[1]
        .replace(/\\([\\()])/g, "$1")
        .replace(/\\n/g, "\n")
        .replace(/\\r/g, "\n"),
  );
  const text = parts.join(" ").replace(/\s+/g, " ").trim();
  if (!text) {
    throw new Error("SOURCE_PDF_TEXT_UNAVAILABLE");
  }
  return { pageCount, text };
}

export async function normalizeRetrievedDocument(
  document: RetrievedDocument,
): Promise<NormalizedDocument> {
  let normalizedContent: string;
  let pageCount: number | undefined;
  const mimeType = document.mimeType.toLowerCase();

  if (mimeType === "text/html") {
    normalizedContent = stripUntrustedMarkup(document.rawContent);
  } else if (
    mimeType.includes("xml") ||
    mimeType === "application/rss+xml" ||
    mimeType === "application/atom+xml"
  ) {
    normalizedContent = stripUntrustedMarkup(
      decodeEntities(document.rawContent),
    );
  } else if (mimeType === "application/json") {
    try {
      normalizedContent = JSON.stringify(
        JSON.parse(document.rawContent),
        null,
        2,
      );
    } catch {
      throw new Error("SOURCE_JSON_MALFORMED");
    }
  } else if (mimeType === "application/pdf") {
    const extracted = extractPdfText(document.rawContent);
    normalizedContent = extracted.text;
    pageCount = extracted.pageCount;
  } else {
    normalizedContent = document.rawContent
      .replace(/\r\n/g, "\n")
      .replace(/[ \t]+\n/g, "\n")
      .replace(/\n{3,}/g, "\n\n")
      .trim();
  }
  if (!normalizedContent) {
    throw new Error("SOURCE_CONTENT_EMPTY");
  }

  return {
    ...document,
    language: "en",
    metadata: {
      ...document.metadata,
      contentHash: await sha256(normalizedContent),
      pageCount,
      promptInjectionFlag: containsPromptInjectionPattern(normalizedContent),
      trustState: "UNTRUSTED_SOURCE",
    },
    normalizedContent,
    title: document.title?.trim() || "Untitled source",
  };
}

export function decodeUtf8(bytes: ArrayBuffer) {
  return new TextDecoder("utf-8", { fatal: false }).decode(bytes);
}

export function decodePdfBytes(bytes: ArrayBuffer) {
  return new TextDecoder("latin1", { fatal: false }).decode(bytes);
}
