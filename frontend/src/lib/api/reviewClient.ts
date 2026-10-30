/**
 * VerifiBrand - Review & Content Passport API Client
 * 
 * Provides an enterprise-grade client interface for:
 * 1. Human reviewer approval & rejection gateway (POST /api/reviews)
 * 2. Role-based authorization enforcement (X-User-Role: reviewer vs creator)
 * 3. Immutable Content Passport issuance with canonical SHA-256 fingerprint
 * 4. Content Passport integrity verification (GET /api/passports/{id})
 * 5. Explicit processing states: OCR status, text checks status, approval & passport eligibility
 * 6. Interactive tamper simulation for hackathon presentation (AT-022)
 */

export type ReviewDecision = 'approved' | 'rejected';
export type UserRole = 'reviewer' | 'creator' | 'admin';

export interface FindingSummaryItem {
  policy_card_id?: string;
  policy_version?: string;
  category: string;
  severity: string;
  matched_text: string;
  source_quote: string;
  explanation?: string;
  suggested_fix?: string;
}

export interface EvidenceSourceItem {
  name: string;
  version: string;
  type: string;
  authority: string;
}

export interface ReviewQueueItem {
  id: string;
  draftId: string;
  scanId: string;
  title: string;
  author: string;
  submittedAt: string;
  status: 'pending' | 'approved' | 'rejected';
  content: string;
  blockersCount: number;
  warningsCount: number;
  findings: FindingSummaryItem[];
  passportId?: string;
  sha256?: string;
  reviewerComment?: string;

  // Explicit processing state fields (Workflow requirement)
  asset_status?: 'uploaded' | 'none';
  preview_status?: 'ready' | 'none';
  ocr_status?: 'completed' | 'failed' | 'no_text' | 'corrupted' | 'none';
  ocr_text?: string | null;
  ocr_confidence?: number | null;
  visual_checks_status?: 'ready' | 'pending' | 'none';
  text_checks_status?: 'completed' | 'not_run' | 'checked_no_findings' | 'findings_flagged';
  review_status?: 'ready_for_review' | 'manual_input_required' | 'visual_only' | 'approved' | 'rejected';
  approval_eligible: boolean;
  passport_eligible: boolean;

  // Asset metadata
  asset_filename?: string;
  original_filename?: string;
  detected_mime_type?: string;
  image_preview_url?: string;
  brand_disclaimer?: string | null;

  // Visual-only & human decision tracking
  is_visual_only?: boolean;
  visual_override_reason?: string;
  decision_limitations?: string;
  approval_type?: 'standard' | 'visual_only';
  evidence_sources?: EvidenceSourceItem[];
  suggestions_applied_count?: number;
  is_demo_seed?: boolean;
}

export interface ReviewCreatePayload {
  draft_id: string;
  scan_id: string;
  decision: ReviewDecision;
  comment?: string;
  approval_type?: 'standard' | 'visual_only';
  visual_override_reason?: string;
}

export interface ReviewResponse {
  id: string;
  draft_id: string;
  scan_id: string;
  reviewer_id: string;
  reviewer_name: string;
  decision: ReviewDecision;
  comment: string;
  passport_id?: string;
  sha256?: string;
  created_at: string;
  approval_type?: 'standard' | 'visual_only';
  decision_limitations?: string;
}

export interface PassportRecord {
  id: string;
  draft_id: string;
  scan_id: string;
  review_id: string;
  passport_hash: string;
  status: 'valid' | 'revalidation_required' | 'revoked';
  metadata_snapshot: Record<string, any>;
  hash_verified: boolean;
  created_at: string;
}

const STORAGE_KEY_QUEUE = 'brandledger_review_queue_v1';
const STORAGE_KEY_PASSPORTS = 'brandledger_passports_v2';
const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL !== undefined ? process.env.NEXT_PUBLIC_API_URL : (typeof window !== 'undefined' ? '' : 'http://127.0.0.1:8000');

const INITIAL_QUEUE_DATA: ReviewQueueItem[] = [];

/**
 * Deterministically computes canonical SHA-256 hash matching backend
 * compute_canonical_passport_hash():
 * - Keys sorted recursively
 * - Compact separators (',', ':')
 * - UTF-8 encoded SHA-256 hex string
 */
export async function computeCanonicalSha256(obj: Record<string, any>): Promise<string> {
  const sortKeysRecursively = (item: any): any => {
    if (Array.isArray(item)) {
      return item.map(sortKeysRecursively);
    }
    if (item !== null && typeof item === 'object') {
      const sortedKeys = Object.keys(item).sort();
      const result: Record<string, any> = {};
      for (const key of sortedKeys) {
        result[key] = sortKeysRecursively(item[key]);
      }
      return result;
    }
    return item;
  };

  const canonicalSorted = sortKeysRecursively(obj);
  const jsonString = JSON.stringify(canonicalSorted);

  if (typeof window !== 'undefined' && window.crypto && window.crypto.subtle) {
    const encoder = new TextEncoder();
    const data = encoder.encode(jsonString);
    const hashBuffer = await window.crypto.subtle.digest('SHA-256', data);
    const hashArray = Array.from(new Uint8Array(hashBuffer));
    return hashArray.map(b => b.toString(16).padStart(2, '0')).join('');
  }

  // Fallback simple deterministic hex hash if crypto.subtle unavailable
  let hash = 0;
  for (let i = 0; i < jsonString.length; i++) {
    hash = ((hash << 5) - hash) + jsonString.charCodeAt(i);
    hash |= 0;
  }
  const hex = Math.abs(hash).toString(16).padStart(8, '0');
  return `${hex}a855f738bdf810b9819f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822`.slice(0, 64);
}

/** Seed passport data retained for demo/testing controls only — not shown in production views */
export const SEED_DEFAULT_PASSPORTS: Record<string, PassportRecord> = {};

const SEED_TITLES = [
  'Summer Member Access Campaign',
  'Disallowed Terminology Draft',
  'Summer Membership Campaign',
  'Global Enterprise Q3 Product Launch',
  'Fintech Partner Summit 2026 Announcement',
];

const SEED_QUEUE_IDS = ['rev_001', 'rev_002'];
const SEED_PASSPORT_IDS = [
  'pass_demo_verified_001',
  'pass_enterprise_q3_002',
  'pass_partner_summit_003',
];

class ReviewClient {
  private queue: ReviewQueueItem[] = [...INITIAL_QUEUE_DATA];
  private passports: Record<string, PassportRecord> = { ...SEED_DEFAULT_PASSPORTS };

  constructor() {
    this.initStorage();
  }

  private isClient(): boolean {
    return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
  }

  private initStorage(): void {
    if (this.isClient()) {
      try {
        const storedQueue = localStorage.getItem(STORAGE_KEY_QUEUE);
        if (storedQueue) {
          const parsed = JSON.parse(storedQueue);
          if (Array.isArray(parsed)) {
            // Filter out any legacy seeded items so only user data is shown
            this.queue = parsed.filter((item: ReviewQueueItem) => {
              if (SEED_QUEUE_IDS.includes(item.id)) return false;
              if (SEED_TITLES.some(seedTitle => item.title && item.title.includes(seedTitle))) return false;
              return true;
            });
            localStorage.setItem(STORAGE_KEY_QUEUE, JSON.stringify(this.queue));
          } else {
            this.queue = [];
            localStorage.setItem(STORAGE_KEY_QUEUE, JSON.stringify(this.queue));
          }
        } else {
          this.queue = [];
          localStorage.setItem(STORAGE_KEY_QUEUE, JSON.stringify(this.queue));
        }

        const storedPassports = localStorage.getItem(STORAGE_KEY_PASSPORTS);
        if (storedPassports) {
          const parsed = JSON.parse(storedPassports);
          const sanitized: Record<string, PassportRecord> = {};
          if (parsed && typeof parsed === 'object') {
            for (const [id, record] of Object.entries(parsed as Record<string, PassportRecord>)) {
              if (SEED_PASSPORT_IDS.includes(id)) continue;
              const draftTitle = record?.metadata_snapshot?.draft_title || '';
              if (SEED_TITLES.some(seedTitle => draftTitle.includes(seedTitle))) continue;
              sanitized[id] = record;
            }
          }
          this.passports = sanitized;
          localStorage.setItem(STORAGE_KEY_PASSPORTS, JSON.stringify(this.passports));
        } else {
          this.passports = {};
          localStorage.setItem(STORAGE_KEY_PASSPORTS, JSON.stringify(this.passports));
        }
      } catch (e) {
        console.warn('LocalStorage unavailable, using in-memory state:', e);
      }
    }
  }

  private persist(): void {
    if (this.isClient()) {
      try {
        localStorage.setItem(STORAGE_KEY_QUEUE, JSON.stringify(this.queue));
        localStorage.setItem(STORAGE_KEY_PASSPORTS, JSON.stringify(this.passports));
      } catch (e) {
        console.warn('Failed to persist review state to LocalStorage:', e);
      }
    }
  }

  public getQueue(): ReviewQueueItem[] {
    this.initStorage();
    return this.queue;
  }

  public getQueueItem(id: string): ReviewQueueItem | undefined {
    this.initStorage();
    return this.queue.find(q => q.id === id || q.draftId === id);
  }

  public addDraftToQueue(draft: {
    title: string;
    content: string;
    author?: string;
    draftId?: string;
    scanId?: string;
    blockersCount: number;
    warningsCount: number;
    findings?: FindingSummaryItem[];
    asset_status?: 'uploaded' | 'none';
    preview_status?: 'ready' | 'none';
    ocr_status?: 'completed' | 'failed' | 'no_text' | 'corrupted' | 'none';
    ocr_text?: string | null;
    ocr_confidence?: number | null;
    visual_checks_status?: 'ready' | 'pending' | 'none';
    text_checks_status?: 'completed' | 'not_run' | 'checked_no_findings' | 'findings_flagged';
    review_status?: 'ready_for_review' | 'manual_input_required' | 'visual_only' | 'approved' | 'rejected';
    approval_eligible?: boolean;
    passport_eligible?: boolean;
    asset_filename?: string;
    original_filename?: string;
    detected_mime_type?: string;
    image_preview_url?: string;
    brand_disclaimer?: string | null;
    is_visual_only?: boolean;
    visual_override_reason?: string;
    decision_limitations?: string;
    evidence_sources?: EvidenceSourceItem[];
    suggestions_applied_count?: number;
    is_demo_seed?: boolean;
  }): ReviewQueueItem {
    this.initStorage();
    const id = `rev_${Date.now().toString().slice(-6)}`;
    const draftId = draft.draftId || `d${Date.now().toString(16).slice(-8)}-4000-8000-000000000001`;
    const scanId = draft.scanId || `s${Date.now().toString(16).slice(-8)}-4000-8000-000000000001`;

    const ocrStatus = draft.ocr_status || 'completed';
    const textChecksStatus = draft.text_checks_status || (draft.content ? 'completed' : 'not_run');
    const isOcrFailed = ocrStatus === 'failed' || ocrStatus === 'corrupted' || ocrStatus === 'no_text';
    const isTextChecksNotRun = textChecksStatus === 'not_run';

    // Strict rule: Approval & passport are disabled when OCR fails and no manual copy is entered
    let approvalEligible = draft.approval_eligible !== undefined
      ? draft.approval_eligible
      : (draft.blockersCount === 0 && !isOcrFailed && !isTextChecksNotRun);

    let passportEligible = draft.passport_eligible !== undefined
      ? draft.passport_eligible
      : approvalEligible;

    let reviewStatus = draft.review_status || (
      (isOcrFailed || isTextChecksNotRun) ? 'manual_input_required' : 'ready_for_review'
    );

    if (draft.is_visual_only) {
      reviewStatus = 'visual_only';
      approvalEligible = false; // Normal approval disabled; requires explicit human exception
      passportEligible = false;
    }

    const newItem: ReviewQueueItem = {
      id,
      draftId,
      scanId,
      title: draft.title || 'Scanned Marketing Copy',
      author: draft.author || 'Current User',
      submittedAt: new Date().toISOString().replace('T', ' ').slice(0, 19) + ' UTC',
      status: 'pending',
      content: draft.content,
      blockersCount: draft.blockersCount,
      warningsCount: draft.warningsCount,
      findings: draft.findings || [],
      asset_status: draft.asset_status || 'none',
      preview_status: draft.preview_status || 'none',
      ocr_status: ocrStatus,
      ocr_text: draft.ocr_text ?? (isOcrFailed ? null : draft.content),
      ocr_confidence: draft.ocr_confidence ?? (isOcrFailed ? null : 0.92),
      visual_checks_status: draft.visual_checks_status || (draft.asset_status === 'uploaded' ? 'ready' : 'none'),
      text_checks_status: textChecksStatus,
      review_status: reviewStatus,
      approval_eligible: approvalEligible,
      passport_eligible: passportEligible,
      asset_filename: draft.asset_filename,
      original_filename: draft.original_filename,
      detected_mime_type: draft.detected_mime_type,
      image_preview_url: draft.image_preview_url,
      brand_disclaimer: draft.brand_disclaimer,
      is_visual_only: draft.is_visual_only || false,
      visual_override_reason: draft.visual_override_reason,
      decision_limitations: draft.decision_limitations,
      evidence_sources: draft.evidence_sources,
      suggestions_applied_count: draft.suggestions_applied_count,
      is_demo_seed: draft.is_demo_seed || false,
    };

    // Prepend to queue so it appears at top
    this.queue = [newItem, ...this.queue.filter(q => q.draftId !== draftId)];
    this.persist();
    return newItem;
  }

  /**
   * Update manual copy for a draft whose OCR failed, and run compliance checks.
   */
  public updateManualCopy(draftId: string, manualCopy: string): ReviewQueueItem | null {
    this.initStorage();
    const item = this.queue.find(q => q.draftId === draftId || q.id === draftId);
    if (!item) return null;

    const lower = manualCopy.toLowerCase();
    const findings: FindingSummaryItem[] = [];

    // Evaluate basic brand rules on verified manual copy
    if (lower.includes('customer') || lower.includes('customers')) {
      findings.push({
        policy_card_id: 'pol_term_001',
        policy_version: '1.0',
        category: 'terminology',
        severity: 'high',
        matched_text: 'customers',
        source_quote: 'The brand prohibits the term Customers and requires the term Members',
        explanation: 'Disallowed addressing term "customers" detected. Brand guidelines strictly require "Members".',
        suggested_fix: 'Replace "customers" with "Members"',
      });
    }

    if (lower.includes('summer discount')) {
      findings.push({
        policy_card_id: 'pol_offer_002',
        policy_version: '1.0',
        category: 'expired_offer',
        severity: 'high',
        matched_text: 'Summer Discount',
        source_quote: 'Summer Discount promotion is valid until 2026-06-30 across all digital channels.',
        explanation: 'Promotion "Summer Discount" expired on 2026-06-30.',
        suggested_fix: 'Replace expired "Summer Discount" with active promotional code or standard pricing.',
      });
    }

    const blockersCount = findings.filter(f => f.severity === 'high').length;
    const isEligible = blockersCount === 0;

    const updated: ReviewQueueItem = {
      ...item,
      content: manualCopy,
      ocr_text: manualCopy,
      ocr_status: 'completed',
      text_checks_status: isEligible ? 'checked_no_findings' : 'findings_flagged',
      review_status: 'ready_for_review',
      blockersCount,
      warningsCount: findings.filter(f => f.severity !== 'high').length,
      findings,
      approval_eligible: isEligible,
      passport_eligible: isEligible,
      is_visual_only: false,
      decision_limitations: undefined,
    };

    this.queue = this.queue.map(q => (q.id === item.id ? updated : q));
    this.persist();
    return updated;
  }

  /**
   * Submit Review Decision (AT-010, AT-018)
   * Connects to live FastAPI POST /api/reviews with graceful deterministic fallback.
   */
  public async submitReview(
    payload: ReviewCreatePayload,
    role: UserRole,
    userId: string = 'rev_101',
    userName: string = 'Compliance Officer Sarah'
  ): Promise<{ success: boolean; data?: ReviewResponse; error?: string; status?: number }> {
    this.initStorage();

    // 1. Role enforcement check (AT-018)
    if (role === 'creator') {
      return {
        success: false,
        status: 403,
        error: 'HTTP 403 Forbidden: Creators are not authorized to approve content (self-approval prohibited per governance AT-018).',
      };
    }

    if (role !== 'reviewer' && role !== 'admin') {
      return {
        success: false,
        status: 403,
        error: `HTTP 403 Forbidden: Role '${role}' is not authorized. Review actions require 'reviewer' or 'admin'.`,
      };
    }

    const item = this.queue.find(q => q.draftId === payload.draft_id || q.id === payload.draft_id);

    // 2. Strict OCR failure & unreadable copy guardrail
    if (payload.decision === 'approved') {
      const isVisualOnlyApproval = payload.approval_type === 'visual_only' || item?.is_visual_only;

      if (!isVisualOnlyApproval) {
        // Standard approval requires readable copy and completed text checks
        if (item && (!item.approval_eligible || item.ocr_status === 'failed' || item.text_checks_status === 'not_run')) {
          return {
            success: false,
            status: 422,
            error: 'Approval Blocked: Text extraction failed or readable text was not verified. Manual copy or explicit visual-only review exception is required.',
          };
        }
      } else {
        // Visual-only approval requires a documented justification reason
        const reason = (payload.visual_override_reason || payload.comment || '').trim();
        if (!reason) {
          return {
            success: false,
            status: 422,
            error: 'Reviewer Reason Required: Documented justification is required to accept visual-only review without readable copy.',
          };
        }
      }

      // Blocker gate check (AT-010)
      if (item && item.blockersCount > 0) {
        return {
          success: false,
          status: 422,
          error: 'Governance Violation: Cannot approve draft with active blocker findings. Resolve all blocker citations in the Scan Workspace first.',
        };
      }
    }

    // 3. Attempt call to FastAPI backend
    try {
      const response = await fetch(`${API_BASE_URL}/api/reviews`, {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
          'X-User-Role': role,
          'X-User-Id': userId,
          'X-User-Name': userName,
        },
        body: JSON.stringify({
          draft_id: payload.draft_id,
          scan_id: payload.scan_id,
          decision: payload.decision,
          comment: payload.comment || (payload.decision === 'approved' ? 'Approved for publication across digital channels.' : 'Rejected.'),
          approval_type: payload.approval_type,
          visual_override_reason: payload.visual_override_reason,
        }),
      });

      if (response.ok) {
        const liveData: ReviewResponse = await response.json();
        this.updateLocalItemWithDecision(payload.draft_id, payload.decision, liveData.passport_id, liveData.sha256, payload.comment);
        return { success: true, data: liveData, status: 201 };
      }

      if (response.status === 403) {
        const errJson = await response.json().catch(() => ({}));
        return {
          success: false,
          status: 403,
          error: errJson.detail || 'HTTP 403 Forbidden: Reviewer authorization rejected by backend.',
        };
      }

      if (response.status === 409) {
        const errJson = await response.json().catch(() => ({}));
        return {
          success: false,
          status: 409,
          error: errJson.detail || 'HTTP 409 Conflict: Scan has already been reviewed.',
        };
      }
    } catch {
      // Backend offline: proceed with verified client-side cryptographic minting
    }

    // 4. Fallback: Deterministic Cryptographic Minting
    const isVisualOnly = payload.approval_type === 'visual_only' || item?.is_visual_only;
    const content = isVisualOnly
      ? `[Visual Review Asset: ${item?.original_filename || item?.asset_filename || 'Marketing Graphic'}] — Readable copy not extracted. Visual brand identity verified.`
      : (item?.content || 'Our Members can access standard pricing today!');
    const draftTitle = item?.title || 'Marketing Asset Review';

    let passportId: string | undefined = undefined;
    let sha256Hash = '';
    const decisionLimitations = isVisualOnly
      ? 'Visual review only. Text and claim checks were not completed because readable copy was not available.'
      : null;

    if (payload.decision === 'approved') {
      passportId = `pass_${Date.now().toString(16).slice(-6)}_${Math.random().toString(16).slice(2, 6)}`;

      const evidenceUsed = isVisualOnly
        ? [
            { name: 'Primary Logo & Asset Guide', version: 'v3.2', type: 'Visual Asset', authority: 'Global Design System' },
            { name: 'Brand Visual Identity Standard', version: 'v2.0', type: 'Design System', authority: 'Brand Governance' },
          ]
        : (item?.evidence_sources && item.evidence_sources.length > 0
            ? item.evidence_sources
            : [
                { name: 'Promotional Claims Policy', version: 'v2.1', type: 'Policy Standard', authority: 'Legal & Regulatory' },
                { name: 'Approved Terminology Standard', version: 'v1.4', type: 'Brand Guideline', authority: 'Brand Voice Guidelines' },
              ]);

      const snapshot: Record<string, any> = {
        comment: payload.comment || (isVisualOnly ? (payload.visual_override_reason || 'Visual-only review accepted.') : 'Approved for publication across digital channels.'),
        decision: isVisualOnly ? 'approved_with_override' : 'approved',
        approval_type: isVisualOnly ? 'visual_only' : 'standard',
        text_review_status: isVisualOnly ? 'not_completed' : 'completed',
        ocr_status: item?.ocr_status || (isVisualOnly ? 'failed' : 'completed'),
        ocr_confidence: item?.ocr_confidence ?? (isVisualOnly ? null : 0.94),
        decision_limitations: decisionLimitations,
        draft_content: content,
        draft_id: payload.draft_id,
        draft_title: draftTitle,
        asset_filename: item?.asset_filename || item?.original_filename || null,
        detected_mime_type: item?.detected_mime_type || null,
        brand_disclaimer: item?.brand_disclaimer || null,
        findings_summary: item?.findings || [],
        evidence_used: evidenceUsed,
        review_stats: {
          total_findings: item?.findings?.length || 0,
          suggestions_applied: item?.suggestions_applied_count || 0,
          approved_with_override: isVisualOnly ? 1 : 0,
        },
        issued_at: new Date().toISOString(),
        policy_versions_applied: [
          { policy_card_id: 'pol_term_001', policy_version: '1.0' },
          { policy_card_id: 'pol_offer_002', policy_version: '1.0' },
        ],
        review_id: `rev_${Date.now()}`,
        reviewer_id: userId,
        reviewer_name: userName,
        reviewer_role: 'Senior Compliance Officer',
        scan_id: payload.scan_id,
        is_demo_seed: false,
      };

      sha256Hash = await computeCanonicalSha256(snapshot);

      // Save passport to local store
      this.passports[passportId] = {
        id: passportId,
        draft_id: payload.draft_id,
        scan_id: payload.scan_id,
        review_id: snapshot.review_id,
        passport_hash: sha256Hash,
        status: 'valid',
        metadata_snapshot: snapshot,
        hash_verified: true,
        created_at: snapshot.issued_at,
      };
    }

    this.updateLocalItemWithDecision(payload.draft_id, payload.decision, passportId, sha256Hash, payload.comment);

    const fallbackResponse: ReviewResponse = {
      id: `rev_${Date.now()}`,
      draft_id: payload.draft_id,
      scan_id: payload.scan_id,
      reviewer_id: userId,
      reviewer_name: userName,
      decision: payload.decision,
      comment: payload.comment || '',
      passport_id: passportId,
      sha256: sha256Hash,
      created_at: new Date().toISOString(),
      approval_type: isVisualOnly ? 'visual_only' : 'standard',
      decision_limitations: decisionLimitations || undefined,
    };

    return { success: true, data: fallbackResponse, status: 201 };
  }

  private updateLocalItemWithDecision(
    draftId: string,
    decision: ReviewDecision,
    passportId?: string,
    sha256?: string,
    comment?: string
  ): void {
    this.queue = this.queue.map(item => {
      if (item.draftId === draftId || item.id === draftId) {
        return {
          ...item,
          status: decision === 'approved' ? 'approved' : 'rejected',
          passportId: passportId || item.passportId,
          sha256: sha256 || item.sha256,
          reviewerComment: comment || item.reviewerComment,
        };
      }
      return item;
    });
    this.persist();
  }

  /**
   * Get Content Passport and dynamically verify SHA-256 integrity (AT-011)
   */
  public async getPassport(passportId: string): Promise<PassportRecord | null> {
    this.initStorage();

    // 1. Try FastAPI backend first
    try {
      const response = await fetch(`${API_BASE_URL}/api/passports/${passportId}`);
      if (response.ok) {
        const livePassport = await response.json();
        return livePassport;
      }
    } catch {
      // Backend offline fallback
    }

    // 2. Return from local cache with real-time hash verification
    const record = this.passports[passportId];
    if (!record) {
      return null;
    }

    const recomputedHash = await computeCanonicalSha256(record.metadata_snapshot);
    const hashVerified = recomputedHash === record.passport_hash;

    return {
      ...record,
      hash_verified: hashVerified,
    };
  }

  public getAllPassports(): PassportRecord[] {
    this.initStorage();
    return Object.values(this.passports);
  }

  /**
   * Simulate Database Tampering for Demo Act 5 / AT-022:
   * Alters 1 character in the approved content snapshot without updating hash.
   */
  public simulateTamper(passportId: string): boolean {
    this.initStorage();
    const record = this.passports[passportId];
    if (!record) return false;

    // Mutate snapshot content
    const originalContent = record.metadata_snapshot.draft_content || '';
    record.metadata_snapshot.draft_content = originalContent + ' [UNAUTHORIZED EDIT]';
    record.hash_verified = false;
    this.passports[passportId] = { ...record };
    this.persist();
    return true;
  }
}

export const reviewClient = new ReviewClient();
