const privateIpv4Patterns = [
  /^10\./,
  /^127\./,
  /^169\.254\./,
  /^192\.168\./,
  /^172\.(1[6-9]|2\d|3[01])\./,
] as const;

const blockedHostnames = new Set([
  "0.0.0.0",
  "::1",
  "localhost",
  "metadata.google.internal",
]);

export function canonicalizePublicUrl(value: string) {
  const url = new URL(value);
  url.hash = "";
  url.hostname = url.hostname.toLowerCase();
  url.pathname = url.pathname.replace(/\/{2,}/g, "/");

  for (const parameter of [...url.searchParams.keys()]) {
    if (
      parameter.toLowerCase().startsWith("utm_") ||
      ["fbclid", "gclid", "mc_cid", "mc_eid"].includes(parameter.toLowerCase())
    ) {
      url.searchParams.delete(parameter);
    }
  }
  url.searchParams.sort();

  if (url.pathname !== "/" && url.pathname.endsWith("/")) {
    url.pathname = url.pathname.slice(0, -1);
  }

  return url.toString();
}

export function validatePublicUrl(value: string) {
  let url: URL;
  try {
    url = new URL(value);
  } catch {
    throw new Error("SOURCE_URL_INVALID");
  }

  if (url.protocol !== "https:") {
    throw new Error("SOURCE_URL_HTTPS_REQUIRED");
  }
  if (url.username || url.password) {
    throw new Error("SOURCE_URL_CREDENTIALS_FORBIDDEN");
  }
  if (url.port && url.port !== "443") {
    throw new Error("SOURCE_URL_PORT_FORBIDDEN");
  }

  const hostname = url.hostname.toLowerCase().replace(/^\[|\]$/g, "");
  if (
    blockedHostnames.has(hostname) ||
    hostname.endsWith(".local") ||
    hostname.endsWith(".internal") ||
    privateIpv4Patterns.some((pattern) => pattern.test(hostname))
  ) {
    throw new Error("SOURCE_URL_PRIVATE_NETWORK_FORBIDDEN");
  }

  return canonicalizePublicUrl(url.toString());
}

export function stripUntrustedMarkup(value: string) {
  return value
    .replace(/<script\b[^>]*>[\s\S]*?<\/script>/gi, " ")
    .replace(/<style\b[^>]*>[\s\S]*?<\/style>/gi, " ")
    .replace(/<noscript\b[^>]*>[\s\S]*?<\/noscript>/gi, " ")
    .replace(/<!--[\s\S]*?-->/g, " ")
    .replace(/<[^>]+>/g, " ")
    .replace(/&nbsp;/g, " ")
    .replace(/&amp;/g, "&")
    .replace(/&lt;/g, "<")
    .replace(/&gt;/g, ">")
    .replace(/&quot;/g, '"')
    .replace(/&#39;/g, "'")
    .replace(/\s+/g, " ")
    .trim();
}

export function containsPromptInjectionPattern(value: string) {
  return [
    /ignore (all |the )?(previous|prior) instructions/i,
    /system prompt/i,
    /developer message/i,
    /you are chatgpt/i,
    /reveal (the )?(prompt|instructions)/i,
  ].some((pattern) => pattern.test(value));
}
