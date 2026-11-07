// Test Suite: Security Gateway (CORS Origin & Client IP Whitelist)

import { isIpWhitelisted, isOriginWhitelisted, getCorsHeaders } from './src/security.ts';

function runUnitTests() {
  console.log('=== TEST SUITE: CORS & IP WHITELIST LOGIC ===\n');

  let passed = 0;
  let failed = 0;

  function assert(condition, message) {
    if (condition) {
      console.log(`  [PASS] ${message}`);
      passed++;
    } else {
      console.error(`  [FAIL] ${message}`);
      failed++;
    }
  }

  // ---------------------------------------------------------------------------
  // 1. IP Whitelisting Tests
  // ---------------------------------------------------------------------------
  console.log('1. Testing IP Whitelist:');

  // Loopback
  assert(isIpWhitelisted('127.0.0.1'), 'Allows IPv4 loopback 127.0.0.1');
  assert(isIpWhitelisted('::1'), 'Allows IPv6 loopback ::1');
  assert(isIpWhitelisted('::ffff:127.0.0.1'), 'Allows IPv4-mapped IPv6 loopback ::ffff:127.0.0.1');

  // Private Subnets (RFC 1918)
  assert(isIpWhitelisted('192.168.1.100'), 'Allows Class C private IP 192.168.1.100');
  assert(isIpWhitelisted('10.50.2.1'), 'Allows Class A private IP 10.50.2.1');
  assert(isIpWhitelisted('172.20.10.5'), 'Allows Class B private IP 172.20.10.5 (172.16.0.0/12)');

  // Public IP without custom config -> should be rejected
  assert(!isIpWhitelisted('203.0.113.195'), 'Rejects unknown public IP 203.0.113.195 by default');

  // Public IP with custom config
  const customConfig = '203.0.113.195, 198.51.100.0/24';
  assert(isIpWhitelisted('203.0.113.195', customConfig), 'Allows explicit configured IP 203.0.113.195');
  assert(isIpWhitelisted('198.51.100.42', customConfig), 'Allows IP in configured CIDR 198.51.100.0/24');
  assert(!isIpWhitelisted('198.51.101.1', customConfig), 'Rejects IP outside configured CIDR');

  // ---------------------------------------------------------------------------
  // 2. CORS Origin Whitelisting Tests
  // ---------------------------------------------------------------------------
  console.log('\n2. Testing CORS Origin Whitelist:');

  // Direct server/script calls (null/empty origin)
  assert(isOriginWhitelisted(null), 'Allows non-browser requests without Origin header (curl, python)');
  assert(isOriginWhitelisted(''), 'Allows empty Origin');

  // Local dev origins
  assert(isOriginWhitelisted('http://localhost:5173'), 'Allows Vite dev server http://localhost:5173');
  assert(isOriginWhitelisted('http://127.0.0.1:5173'), 'Allows IP dev server http://127.0.0.1:5173');
  assert(isOriginWhitelisted('http://localhost:8787'), 'Allows Wrangler dev server http://localhost:8787');

  // Cloudflare Pages & Workers domains
  assert(isOriginWhitelisted('https://urban-safety-soc.pages.dev'), 'Allows Cloudflare Pages domain *.pages.dev');
  assert(isOriginWhitelisted('https://my-soc.workers.dev'), 'Allows Cloudflare Workers domain *.workers.dev');

  // Malicious/unauthorized origins
  assert(!isOriginWhitelisted('http://attacker-site.com'), 'Rejects unauthorized origin http://attacker-site.com');
  assert(!isOriginWhitelisted('https://malicious-phishing.org'), 'Rejects unauthorized origin https://malicious-phishing.org');

  // Custom configured origins
  const allowedOriginsConfig = 'https://soc.danang.gov.vn, https://*.secure-soc.com';
  assert(isOriginWhitelisted('https://soc.danang.gov.vn', allowedOriginsConfig), 'Allows explicit origin https://soc.danang.gov.vn');
  assert(isOriginWhitelisted('https://cam01.secure-soc.com', allowedOriginsConfig), 'Allows wildcard domain https://*.secure-soc.com');
  assert(!isOriginWhitelisted('https://other.com', allowedOriginsConfig), 'Rejects origin not in custom list');

  // ---------------------------------------------------------------------------
  // 3. Dynamic CORS Headers Generator Tests
  // ---------------------------------------------------------------------------
  console.log('\n3. Testing Dynamic CORS Headers Generator:');

  const reqAllowed = new Request('http://localhost:8787/api/soc/overview', {
    headers: { Origin: 'http://localhost:5173' }
  });
  const headersAllowed = getCorsHeaders(reqAllowed);
  assert(headersAllowed['Access-Control-Allow-Origin'] === 'http://localhost:5173', 'Emits matching Access-Control-Allow-Origin for allowed origin');
  assert(headersAllowed['Access-Control-Allow-Credentials'] === 'true', 'Emits Access-Control-Allow-Credentials: true');
  assert(headersAllowed['Vary'] === 'Origin', 'Emits Vary: Origin');

  const reqDenied = new Request('http://localhost:8787/api/soc/overview', {
    headers: { Origin: 'http://evil-hacker.xyz' }
  });
  const headersDenied = getCorsHeaders(reqDenied);
  assert(!headersDenied['Access-Control-Allow-Origin'], 'Does not emit Access-Control-Allow-Origin for disallowed origin');

  console.log(`\n=== RESULTS: ${passed} PASSED, ${failed} FAILED ===\n`);
  if (failed > 0) {
    process.exit(1);
  }
}

runUnitTests();
