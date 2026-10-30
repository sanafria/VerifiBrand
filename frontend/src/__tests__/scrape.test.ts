import { describe, it } from 'node:test';
import assert from 'node:assert/strict';
import { POST } from '../app/api/scrape/route.ts';

describe('Live Website URL Scraper API Tests', () => {
  it('1. Rejects request with missing or empty URL', async () => {
    const req = new Request('http://localhost:3000/api/scrape', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: '' }),
    });

    const res = await POST(req as any);
    assert.equal(res.status, 400);
    const data = await res.json();
    assert.equal(data.success, false);
    assert.match(data.error, /URL is required/i);
  });

  it('2. Rejects invalid protocols like ftp:// or javascript:', async () => {
    const req = new Request('http://localhost:3000/api/scrape', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ url: 'ftp://files.example.com/asset.html' }),
    });

    const res = await POST(req as any);
    assert.equal(res.status, 400);
    const data = await res.json();
    assert.equal(data.success, false);
    assert.match(data.error, /HTTP and HTTPS/i);
  });

  it('3. Enforces SSRF defense by blocking private/loopback IP addresses', async () => {
    const privateTargets = [
      'http://localhost/admin',
      'http://127.0.0.1:8080/secret',
      'http://192.168.1.1/router',
      'http://10.0.0.1/internal',
      'http://169.254.169.254/latest/meta-data',
    ];

    for (const url of privateTargets) {
      const req = new Request('http://localhost:3000/api/scrape', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ url }),
      });

      const res = await POST(req as any);
      assert.equal(res.status, 403, `Expected 403 for SSRF target: ${url}`);
      const data = await res.json();
      assert.equal(data.success, false);
      assert.match(data.error, /restricted/i);
    }
  });
});
