/**
 * CYBERGUARD AI · SOC v2.1 — SECURITY GATEWAY: CORS & IP WHITELIST CONTROLLER
 * Protects SOC endpoints against unauthorized origins and client IPs [CD-05].
 */

// Default private subnets and loopback addresses
const DEFAULT_WHITELISTED_CIDRS = [
  "127.0.0.1",
  "::1",
  "10.0.0.0/8",
  "172.16.0.0/12",
  "192.168.0.0/16"
];

/**
 * Converts an IPv4 string to a 32-bit unsigned integer.
 */
function ipToInt(ip: string): number | null {
  const parts = ip.trim().split(".");
  if (parts.length !== 4) return null;
  let res = 0;
  for (const p of parts) {
    const n = parseInt(p, 10);
    if (isNaN(n) || n < 0 || n > 255) return null;
    res = ((res << 8) + n) >>> 0;
  }
  return res;
}

/**
 * Checks if an IPv4 address falls within a given CIDR block or matches exact IP.
 */
function isIpInCidr(ip: string, cidr: string): boolean {
  const cleanIp = ip.trim();
  const cleanCidr = cidr.trim();

  // Handle direct equality (e.g. IPv6 loopback or exact IPv4)
  if (!cleanCidr.includes("/")) {
    return cleanIp.toLowerCase() === cleanCidr.toLowerCase();
  }

  const [rangeIp, prefixStr] = cleanCidr.split("/");
  const prefix = parseInt(prefixStr, 10);
  if (isNaN(prefix) || prefix < 0 || prefix > 32) return false;

  const ipNum = ipToInt(cleanIp);
  const rangeNum = ipToInt(rangeIp);
  if (ipNum === null || rangeNum === null) return false;

  const mask = prefix === 0 ? 0 : (~0 << (32 - prefix)) >>> 0;
  return (ipNum & mask) === (rangeNum & mask);
}

/**
 * Validates whether a client IP is authorized under the whitelist.
 * Always permits loopback and local private networks unless explicitly prohibited.
 */
export function isIpWhitelisted(clientIp: string, allowedIpsConfig?: string): boolean {
  if (!clientIp) return false;

  // Normalize IPv4-mapped IPv6 (e.g., ::ffff:127.0.0.1)
  let normalizedIp = clientIp.trim();
  if (normalizedIp.startsWith("::ffff:")) {
    normalizedIp = normalizedIp.replace("::ffff:", "");
  }

  // 1. Check default internal networks
  for (const cidr of DEFAULT_WHITELISTED_CIDRS) {
    if (isIpInCidr(normalizedIp, cidr)) {
      return true;
    }
  }

  // 2. Check user-configured allowed IPs / CIDRs
  if (allowedIpsConfig) {
    const configuredList = allowedIpsConfig
      .split(",")
      .map((s) => s.trim())
      .filter(Boolean);

    for (const cidr of configuredList) {
      if (isIpInCidr(normalizedIp, cidr)) {
        return true;
      }
    }
  }

  return false;
}

/**
 * Validates whether an incoming HTTP Origin header is in the CORS whitelist.
 * Non-browser requests without an Origin header (e.g. Python AI scripts, IoT cameras) are allowed.
 */
export function isOriginWhitelisted(origin: string | null, allowedOriginsConfig?: string): boolean {
  // If no Origin header (direct server-to-server or non-browser HTTP client), allow
  if (!origin) return true;

  const cleanOrigin = origin.trim().toLowerCase();

  // 1. Dev & Localhost origins
  if (
    cleanOrigin.startsWith("http://localhost:") ||
    cleanOrigin === "http://localhost" ||
    cleanOrigin.startsWith("http://127.0.0.1:") ||
    cleanOrigin === "http://127.0.0.1" ||
    cleanOrigin.startsWith("https://localhost:") ||
    cleanOrigin === "https://localhost"
  ) {
    return true;
  }

  // 2. Cloudflare Pages & Workers deployment domains
  if (cleanOrigin.endsWith(".pages.dev") || cleanOrigin.endsWith(".workers.dev")) {
    return true;
  }

  // 3. User-configured origins
  if (allowedOriginsConfig) {
    const configuredList = allowedOriginsConfig
      .split(",")
      .map((s) => s.trim().toLowerCase())
      .filter(Boolean);

    for (const item of configuredList) {
      if (item === "*" || cleanOrigin === item) {
        return true;
      }
      if (item.includes("*")) {
        const regexStr =
          "^" +
          item
            .replace(/[.+?^${}()|[\]\\]/g, "\\$&")
            .replace(/\*/g, "[a-z0-9-_.]+") +
          "$";
        if (new RegExp(regexStr, "i").test(cleanOrigin)) {
          return true;
        }
      }
    }
  }

  return false;
}

/**
 * Returns dynamic CORS headers according to request origin and whitelist policy.
 */
export function getCorsHeaders(request: Request, allowedOriginsConfig?: string): HeadersInit {
  const origin = request.headers.get("Origin");

  if (isOriginWhitelisted(origin, allowedOriginsConfig)) {
    return {
      "Access-Control-Allow-Origin": origin || "*",
      "Access-Control-Allow-Methods": "GET, POST, PUT, DELETE, OPTIONS",
      "Access-Control-Allow-Headers": "Content-Type, Authorization, X-Correlation-ID",
      "Access-Control-Allow-Credentials": "true",
      "Vary": "Origin",
      "Content-Type": "application/json"
    };
  }

  // Origin is not whitelisted: do not emit Access-Control-Allow-Origin
  return {
    "Vary": "Origin",
    "Content-Type": "application/json"
  };
}
