import { NextRequest, NextResponse } from 'next/server.js';

/**
 * Checks whether an IP or hostname is a private/internal network target (SSRF prevention).
 */
function isPrivateHost(hostname: string): boolean {
  const lower = hostname.toLowerCase();
  if (
    lower === 'localhost' ||
    lower === '127.0.0.1' ||
    lower === '0.0.0.0' ||
    lower === '::1' ||
    lower.endsWith('.local') ||
    lower.endsWith('.internal')
  ) {
    return true;
  }

  // IPv4 Private Range Check
  const ipv4Match = lower.match(/^(\d{1,3})\.(\d{1,3})\.(\d{1,3})\.(\d{1,3})$/);
  if (ipv4Match) {
    const oct1 = parseInt(ipv4Match[1], 10);
    const oct2 = parseInt(ipv4Match[2], 10);
    // 10.0.0.0/8
    if (oct1 === 10) return true;
    // 172.16.0.0/12 (172.16 - 172.31)
    if (oct1 === 172 && oct2 >= 16 && oct2 <= 31) return true;
    // 192.168.0.0/16
    if (oct1 === 192 && oct2 === 168) return true;
    // 169.254.0.0/16 (Link Local / Cloud Metadata)
    if (oct1 === 169 && oct2 === 254) return true;
    // 127.0.0.0/8 (Loopback)
    if (oct1 === 127) return true;
  }

  return false;
}

/**
 * Decodes common HTML entities into standard characters.
 */
function decodeHtmlEntities(html: string): string {
  return html
    .replace(/&nbsp;/gi, ' ')
    .replace(/&amp;/gi, '&')
    .replace(/&lt;/gi, '<')
    .replace(/&gt;/gi, '>')
    .replace(/&quot;/gi, '"')
    .replace(/&#39;/gi, "'")
    .replace(/&mdash;/gi, '—')
    .replace(/&ndash;/gi, '–')
    .replace(/&bull;/gi, '•')
    .replace(/&copy;/gi, '©')
    .replace(/&reg;/gi, '®')
    .replace(/&trade;/gi, '™')
    .replace(/&#(\d+);/g, (_, dec) => String.fromCharCode(parseInt(dec, 10)))
    .replace(/&#x([0-9a-f]+);/gi, (_, hex) => String.fromCharCode(parseInt(hex, 16)));
}

/**
 * Sanitizes and extracts visible marketing copy from raw HTML.
 */
function extractPageContent(html: string): {
  title: string;
  description: string;
  text: string;
  headings: string[];
} {
  // 1. Extract Page Title
  const titleMatch = html.match(/<title[^>]*>([\s\S]*?)<\/title>/i);
  const rawTitle = titleMatch ? titleMatch[1].trim() : '';
  const title = decodeHtmlEntities(rawTitle).replace(/\s+/g, ' ');

  // 2. Extract Meta Description or og:description
  const descMatch =
    html.match(/<meta\s+name=["']description["']\s+content=["'](.*?)["']/i) ||
    html.match(/<meta\s+content=["'](.*?)["']\s+name=["']description["']/i) ||
    html.match(/<meta\s+property=["']og:description["']\s+content=["'](.*?)["']/i) ||
    html.match(/<meta\s+content=["'](.*?)["']\s+property=["']og:description["']/i);
  const rawDesc = descMatch ? descMatch[1].trim() : '';
  const description = decodeHtmlEntities(rawDesc).replace(/\s+/g, ' ');

  // 3. Extract Headings (h1, h2, h3)
  const headings: string[] = [];
  const headingMatches = html.matchAll(/<h[1-3][^>]*>([\s\S]*?)<\/h[1-3]>/gi);
  for (const match of headingMatches) {
    const cleanHeading = decodeHtmlEntities(match[1].replace(/<[^>]+>/g, '')).replace(/\s+/g, ' ').trim();
    if (cleanHeading && !headings.includes(cleanHeading) && headings.length < 15) {
      headings.push(cleanHeading);
    }
  }

  // 4. Strip non-content blocks (scripts, styles, noscript, svg, nav, footer)
  let cleanHtml = html
    .replace(/<script[\s\S]*?<\/script>/gi, ' ')
    .replace(/<style[\s\S]*?<\/style>/gi, ' ')
    .replace(/<noscript[\s\S]*?<\/noscript>/gi, ' ')
    .replace(/<svg[\s\S]*?<\/svg>/gi, ' ')
    .replace(/<!--[\s\S]*?-->/g, ' ');

  // 5. Replace block boundaries with newlines
  cleanHtml = cleanHtml
    .replace(/<(?:p|div|section|article|li|tr|h[1-6]|header|footer|nav|blockquote)[^>]*>/gi, '\n')
    .replace(/<\/(?:p|div|section|article|li|tr|h[1-6]|header|footer|nav|blockquote)>/gi, '\n')
    .replace(/<br\s*\/?>/gi, '\n')
    .replace(/<hr\s*\/?>/gi, '\n');

  // 6. Strip all remaining tags
  let text = cleanHtml.replace(/<[^>]+>/g, ' ');

  // 7. Decode HTML entities
  text = decodeHtmlEntities(text);

  // 8. Normalize spacing: convert multiple blank lines into max 2, strip leading/trailing spaces on each line
  const lines = text
    .split('\n')
    .map(line => line.replace(/[ \t]+/g, ' ').trim())
    .filter(line => line.length > 0);

  text = lines.join('\n');

  // Truncate to reasonable maximum length for marketing collateral (first ~12,000 characters)
  if (text.length > 12000) {
    text = text.slice(0, 12000) + '\n\n[...Content truncated for scan workspace...]';
  }

  return { title, description, text, headings };
}

export async function POST(req: NextRequest) {
  try {
    const body = await req.json();
    const targetUrl = (body.url || '').trim();

    if (!targetUrl) {
      return NextResponse.json(
        { success: false, error: 'A valid website URL is required.' },
        { status: 400 }
      );
    }

    // Validate URL structure
    let parsedUrl: URL;
    try {
      parsedUrl = new URL(targetUrl);
    } catch {
      return NextResponse.json(
        { success: false, error: 'Invalid URL format. Please include http:// or https://' },
        { status: 400 }
      );
    }

    // Only allow HTTP and HTTPS
    if (parsedUrl.protocol !== 'http:' && parsedUrl.protocol !== 'https:') {
      return NextResponse.json(
        { success: false, error: 'Only HTTP and HTTPS protocols are supported.' },
        { status: 400 }
      );
    }

    // SSRF Safeguard
    if (isPrivateHost(parsedUrl.hostname)) {
      return NextResponse.json(
        { success: false, error: 'Access to local or private network hostnames is restricted.' },
        { status: 403 }
      );
    }

    // Fetch the webpage with a 10s timeout
    const controller = new AbortController();
    const timeoutId = setTimeout(() => controller.abort(), 10000);

    let res: Response;
    try {
      res = await fetch(parsedUrl.toString(), {
        method: 'GET',
        headers: {
          'User-Agent':
            'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36 VerifiBrand/1.0 (Brand Compliance Auditor)',
          'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8',
          'Accept-Language': 'en-US,en;q=0.9',
        },
        signal: controller.signal,
        redirect: 'follow',
      });
    } catch (err: unknown) {
      const isAbort = (err as Error)?.name === 'AbortError';
      return NextResponse.json(
        {
          success: false,
          error: isAbort
            ? 'Connection timed out while attempting to reach website (10s limit).'
            : `Failed to connect to destination: ${(err as Error)?.message || 'Network error'}`,
        },
        { status: 504 }
      );
    } finally {
      clearTimeout(timeoutId);
    }

    if (!res.ok) {
      return NextResponse.json(
        {
          success: false,
          error: `Website responded with HTTP status ${res.status} (${res.statusText || 'Error'}).`,
        },
        { status: 502 }
      );
    }

    const contentType = res.headers.get('content-type') || '';
    if (!contentType.includes('text/html') && !contentType.includes('text/plain') && !contentType.includes('application/xhtml')) {
      return NextResponse.json(
        {
          success: false,
          error: `Unsupported content type "${contentType}". URL must serve an HTML webpage.`,
        },
        { status: 415 }
      );
    }

    const html = await res.text();
    const { title, description, text, headings } = extractPageContent(html);

    if (!text || text.trim().length === 0) {
      return NextResponse.json(
        {
          success: false,
          error: 'No readable marketing text could be extracted from this page (it may be client-side rendered with heavy JavaScript).',
        },
        { status: 422 }
      );
    }

    const wordCount = text.trim().split(/\s+/).filter(Boolean).length;
    const charCount = text.length;

    return NextResponse.json({
      success: true,
      url: parsedUrl.toString(),
      hostname: parsedUrl.hostname,
      title: title || parsedUrl.hostname,
      description,
      headings,
      text,
      word_count: wordCount,
      char_count: charCount,
    });
  } catch (error: unknown) {
    return NextResponse.json(
      {
        success: false,
        error: (error as Error)?.message || 'An unexpected error occurred while processing URL.',
      },
      { status: 500 }
    );
  }
}
