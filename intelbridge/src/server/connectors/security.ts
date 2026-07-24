const privateIpv4Patterns = [
  /^0\./,
  /^10\./,
  /^127\./,
  /^169\.254\./,
  /^192\.168\./,
  /^172\.(1[6-9]|2\d|3[01])\./,
  /^100\.(6[4-9]|[7-9]\d|1[01]\d|12[0-7])\./,
  /^192\.0\.0\./,
  /^192\.0\.2\./,
  /^198\.(1[89])\./,
  /^198\.51\.100\./,
  /^203\.0\.113\./,
  /^22[4-9]\./,
  /^23\d\./,
  /^24\d\./,
  /^25[0-5]\./,
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

  if (!["http:", "https:"].includes(url.protocol)) {
    throw new Error("SOURCE_URL_PROTOCOL_UNSUPPORTED");
  }
  if (url.username || url.password) {
    throw new Error("SOURCE_URL_CREDENTIALS_FORBIDDEN");
  }
  const permittedPort = url.protocol === "https:" ? "443" : "80";
  if (url.port && url.port !== permittedPort) {
    throw new Error("SOURCE_URL_PORT_FORBIDDEN");
  }

  const hostname = url.hostname.toLowerCase().replace(/^\[|\]$/g, "");
  if (
    blockedHostnames.has(hostname) ||
    hostname.endsWith(".local") ||
    hostname.endsWith(".internal") ||
    hostname.endsWith(".localhost") ||
    hostname === "host.docker.internal" ||
    hostname.startsWith("fc") ||
    hostname.startsWith("fd") ||
    hostname.startsWith("fe8") ||
    hostname.startsWith("fe9") ||
    hostname.startsWith("fea") ||
    hostname.startsWith("feb") ||
    hostname.startsWith("::ffff:") ||
    privateIpv4Patterns.some((pattern) => pattern.test(hostname))
  ) {
    throw new Error("SOURCE_URL_PRIVATE_NETWORK_FORBIDDEN");
  }

  return canonicalizePublicUrl(url.toString());
}

export function assertPublicIpAddress(value: string) {
  const normalized = value.toLowerCase().replace(/^\[|\]$/g, "");
  if (
    blockedHostnames.has(normalized) ||
    normalized === "::" ||
    normalized.startsWith("fc") ||
    normalized.startsWith("fd") ||
    normalized.startsWith("fe8") ||
    normalized.startsWith("fe9") ||
    normalized.startsWith("fea") ||
    normalized.startsWith("feb") ||
    normalized.startsWith("::ffff:") ||
    privateIpv4Patterns.some((pattern) => pattern.test(normalized))
  ) {
    throw new Error("SOURCE_URL_PRIVATE_NETWORK_FORBIDDEN");
  }
  return normalized;
}

export async function assertPublicDns(
  value: string,
  fetcher: typeof fetch = fetch,
) {
  const hostname = new URL(validatePublicUrl(value)).hostname;
  if (/^[\d.]+$/.test(hostname) || hostname.includes(":")) {
    assertPublicIpAddress(hostname);
    return;
  }

  const query = async (type: "A" | "AAAA") => {
    const response = await fetcher(
      `https://cloudflare-dns.com/dns-query?name=${encodeURIComponent(hostname)}&type=${type}`,
      {
        headers: { Accept: "application/dns-json" },
        signal: AbortSignal.timeout(3_000),
      },
    );
    if (!response.ok) {
      throw new Error("SOURCE_DNS_VALIDATION_FAILED");
    }
    const body = (await response.json()) as {
      Answer?: { data: string; type: number }[];
    };
    return (body.Answer ?? [])
      .filter((answer) => answer.type === 1 || answer.type === 28)
      .map((answer) => answer.data);
  };
  const addresses = [...(await query("A")), ...(await query("AAAA"))];
  if (addresses.length === 0) {
    throw new Error("SOURCE_DNS_VALIDATION_FAILED");
  }
  addresses.forEach(assertPublicIpAddress);
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
