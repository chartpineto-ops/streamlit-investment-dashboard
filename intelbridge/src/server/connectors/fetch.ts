import {
  assertPublicDns,
  canonicalizePublicUrl,
  validatePublicUrl,
} from "@/server/connectors/security";

const DEFAULT_MAX_BYTES = 2_000_000;
const supportedMimeTypes = new Set([
  "application/atom+xml",
  "application/json",
  "application/pdf",
  "application/rss+xml",
  "application/xml",
  "text/csv",
  "text/html",
  "text/markdown",
  "text/plain",
  "text/xml",
]);

export type SafeFetchResult = {
  bytes: ArrayBuffer;
  canonicalUrl: string;
  contentType: string;
  responseHeaders: Headers;
};

function normalizeMimeType(value: string | null) {
  return value?.split(";")[0]?.trim().toLowerCase() ?? "";
}

function sniffMimeType(bytes: Uint8Array) {
  const prefix = new TextDecoder("utf-8", { fatal: false })
    .decode(bytes.slice(0, 256))
    .trimStart()
    .toLowerCase();
  if (prefix.startsWith("%pdf-")) return "application/pdf";
  if (prefix.startsWith("<!doctype html") || prefix.startsWith("<html")) {
    return "text/html";
  }
  if (prefix.startsWith("<?xml") || prefix.startsWith("<rss")) {
    return "application/xml";
  }
  if (prefix.startsWith("{") || prefix.startsWith("[")) {
    return "application/json";
  }
  return "text/plain";
}

function assertContentType(declared: string, sniffed: string) {
  if (!supportedMimeTypes.has(declared)) {
    throw new Error("SOURCE_CONTENT_TYPE_UNSUPPORTED");
  }
  if (
    (declared === "application/pdf" && sniffed !== "application/pdf") ||
    (declared === "application/json" && sniffed !== "application/json") ||
    (declared === "text/html" && sniffed !== "text/html")
  ) {
    throw new Error("SOURCE_CONTENT_TYPE_MISMATCH");
  }
}

export async function fetchPublicResource(
  value: string,
  options: {
    accept?: string;
    headers?: Record<string, string>;
    maxBytes?: number;
    timeoutMs?: number;
  } = {},
): Promise<SafeFetchResult> {
  const maxBytes = options.maxBytes ?? DEFAULT_MAX_BYTES;
  let currentUrl = validatePublicUrl(value);
  let response: Response | undefined;

  for (let redirectCount = 0; redirectCount <= 4; redirectCount += 1) {
    await assertPublicDns(currentUrl);
    for (let attempt = 0; attempt < 2; attempt += 1) {
      response = await fetch(currentUrl, {
        headers: {
          Accept:
            options.accept ??
            "text/html,text/plain,text/markdown,text/csv,application/json,application/xml,application/rss+xml,application/atom+xml,application/pdf",
          "User-Agent": "IntelBridge/1.0 (+source-ingestion)",
          ...options.headers,
        },
        redirect: "manual",
        signal: AbortSignal.timeout(options.timeoutMs ?? 10_000),
      });
      if (response.status !== 429 && response.status < 500) break;
    }
    if (!response) {
      throw new Error("SOURCE_RETRIEVAL_FAILED");
    }
    if (response.status < 300 || response.status >= 400) break;
    const location = response.headers.get("location");
    if (!location) {
      throw new Error("SOURCE_REDIRECT_INVALID");
    }
    currentUrl = validatePublicUrl(new URL(location, currentUrl).toString());
    response = undefined;
  }

  if (!response?.ok) {
    throw new Error("SOURCE_RETRIEVAL_FAILED");
  }
  const declaredLength = Number(response.headers.get("content-length") ?? 0);
  if (declaredLength > maxBytes) {
    throw new Error("SOURCE_CONTENT_TOO_LARGE");
  }
  const bytes = await response.arrayBuffer();
  if (bytes.byteLength > maxBytes) {
    throw new Error("SOURCE_CONTENT_TOO_LARGE");
  }
  const declared = normalizeMimeType(response.headers.get("content-type"));
  const sniffed = sniffMimeType(new Uint8Array(bytes));
  const contentType = declared || sniffed;
  assertContentType(contentType, sniffed);

  return {
    bytes,
    canonicalUrl: canonicalizePublicUrl(currentUrl),
    contentType,
    responseHeaders: response.headers,
  };
}
