/**
 * Brand Ledger - Policy & Brand API Client
 * 
 * Provides an enterprise-grade typed interface for:
 * 1. Authoritative Policy Library CRUD and filtering against FastAPI & PostgreSQL
 * 2. Brand Passport governance summaries
 * 3. Enforcing "No receipt, no flag" quote integrity checks
 * 
 * Architecture:
 * - Authoritative REST integration with FastAPI backend (/api/policies)
 * - Transparent status & field mapping between frontend and backend schemas
 * - Compatible with NEXT_PUBLIC_USE_BACKEND_CRUD environment settings
 * - Development persistence adapter (localStorage + in-memory fallback) for offline & testing
 */

import type { PolicyCard, PolicyFilterState, BrandProfile, PolicyCategory, PolicyStatus } from '../../types/policy.ts';
import { INITIAL_POLICY_CARDS, INITIAL_BRAND_PROFILES } from '../mockData.ts';

const STORAGE_KEY_POLICIES = 'brandledger_policies_v1';
const STORAGE_KEY_BRANDS = 'brandledger_brands_v1';

const API_BASE_URL =
  process.env.NEXT_PUBLIC_API_URL !== undefined
    ? process.env.NEXT_PUBLIC_API_URL
    : typeof window !== 'undefined'
    ? ''
    : 'http://127.0.0.1:8000';

function isBackendEnabled(): boolean {
  // Backend is authoritative unless explicitly disabled via NEXT_PUBLIC_USE_BACKEND_CRUD='false'
  return process.env.NEXT_PUBLIC_USE_BACKEND_CRUD !== 'false';
}

export interface BackendPolicyResponse {
  id: string;
  policy_key?: string;
  title: string;
  card_type: string;
  rule_text: string;
  approved_value?: string;
  source_quote: string;
  valid_from?: string;
  valid_until?: string;
  severity?: string;
  status: string;
  version: number;
  rules?: any[];
  metadata?: Record<string, any>;
  created_at: string;
  updated_at: string;
}

export function mapCategoryToCardType(category?: string): 'terminology' | 'offer' | 'fact' | 'claim' | 'tone' {
  const norm = (category || '').toLowerCase().trim();
  if (norm === 'offer_validity' || norm === 'offer') return 'offer';
  if (norm === 'numerical' || norm === 'fact') return 'fact';
  if (norm === 'claims' || norm === 'claim') return 'claim';
  if (norm === 'tone' || norm === 'voice_tone') return 'tone';
  return 'terminology';
}

export function mapCardTypeToCategory(cardType?: string): PolicyCategory {
  const norm = (cardType || '').toLowerCase().trim();
  if (norm === 'offer') return 'offer_validity';
  if (norm === 'fact') return 'numerical';
  if (norm === 'claim') return 'claims';
  if (norm === 'tone') return 'tone';
  if (norm === 'visual') return 'visual';
  return (norm as PolicyCategory) || 'terminology';
}

export function mapBackendToFrontendPolicy(b: BackendPolicyResponse): PolicyCard {
  const category: PolicyCategory = mapCardTypeToCategory(b.card_type);

  const statusMap: Record<string, PolicyStatus> = {
    active: 'approved',
    inactive: 'archived',
    approved: 'approved',
    archived: 'archived',
    draft: 'draft',
  };
  const status: PolicyStatus = statusMap[b.status?.toLowerCase()] || 'approved';

  const rules = Array.isArray(b.rules) && b.rules.length > 0
    ? b.rules
    : [
        {
          type: category,
          quote: b.source_quote,
          approved_value: b.approved_value,
        },
      ];

  const metadata: Record<string, unknown> = {
    ...(b.metadata || {}),
    source_quote: b.source_quote,
    quote: b.source_quote,
    approved_value: b.approved_value,
    valid_from: b.valid_from,
    valid_until: b.valid_until,
    policy_key: b.policy_key,
    backend_id: b.id,
  };

  return {
    id: b.policy_key || b.id,
    version: String(b.version) || '1.0',
    title: b.title,
    category,
    content: b.rule_text,
    rules: rules as any,
    metadata,
    status,
    created_at: b.created_at,
    updated_at: b.updated_at,
  };
}

export function mapFrontendToBackendPayload(f: Partial<PolicyCard>): Record<string, any> {
  const card_type = f.category ? mapCategoryToCardType(f.category) : undefined;
  const status = f.status === 'archived' || f.status === 'draft' ? 'inactive' : 'active';
  const source_quote =
    (f.metadata?.quote as string) ||
    (f.rules?.[0] as any)?.quote ||
    (f.metadata?.source_quote as string) ||
    (f.content ? f.content.slice(0, 100) : '');

  return {
    title: f.title,
    card_type,
    rule_text: f.content,
    approved_value: (f.metadata?.approved_value as string) || (f.rules?.[0] as any)?.replacement || null,
    source_quote,
    status,
    policy_key: f.id,
    rules: f.rules || [],
    metadata: f.metadata || {},
  };
}

class PolicyClient {
  private inMemoryPolicies: PolicyCard[] = [...INITIAL_POLICY_CARDS];
  private inMemoryBrands: BrandProfile[] = [...INITIAL_BRAND_PROFILES];

  constructor() {
    this.initStorage();
  }

  private isClient(): boolean {
    return typeof window !== 'undefined' && typeof window.localStorage !== 'undefined';
  }

  private initStorage(): void {
    if (this.isClient()) {
      try {
        const storedPolicies = localStorage.getItem(STORAGE_KEY_POLICIES);
        if (storedPolicies) {
          this.inMemoryPolicies = JSON.parse(storedPolicies);
        } else {
          localStorage.setItem(STORAGE_KEY_POLICIES, JSON.stringify(this.inMemoryPolicies));
        }

        const storedBrands = localStorage.getItem(STORAGE_KEY_BRANDS);
        if (storedBrands) {
          this.inMemoryBrands = JSON.parse(storedBrands);
        } else {
          localStorage.setItem(STORAGE_KEY_BRANDS, JSON.stringify(this.inMemoryBrands));
        }
      } catch (e) {
        console.warn('LocalStorage unavailable, defaulting to memory-only storage:', e);
      }
    }
  }

  private persistPolicies(): void {
    if (this.isClient()) {
      try {
        localStorage.setItem(STORAGE_KEY_POLICIES, JSON.stringify(this.inMemoryPolicies));
      } catch (e) {
        console.warn('Failed to persist policies to LocalStorage:', e);
      }
    }
  }

  /**
   * Verify "No receipt, no flag":
   * Check whether source quotes in rules actually exist as literal substrings of content.
   */
  public verifyQuoteIntegrity(content: string, quote?: string): { isValid: boolean; error?: string } {
    if (!quote || !quote.trim()) {
      return { isValid: false, error: 'A valid source quote is required by brand governance ("No receipt, no flag").' };
    }
    const normQuote = quote.replace(/[\s“”]+/g, ' ').trim().toLowerCase();
    const normContent = content.replace(/[\s“”]+/g, ' ').trim().toLowerCase();

    if (!normContent.includes(normQuote)) {
      return {
        isValid: false,
        error: `Source quote does not exist as an exact substring in the policy text. Every rule requires direct textual evidence.`,
      };
    }
    return { isValid: true };
  }

  /**
   * Retrieve all policies matching optional filter state.
   */
  public async getPolicies(filters?: Partial<PolicyFilterState>): Promise<{
    policies: PolicyCard[];
    total: number;
    dataSource: 'backend_api' | 'dev_adapter';
  }> {
    if (isBackendEnabled()) {
      try {
        const params = new URLSearchParams();
        if (filters?.category && filters.category !== 'all') {
          params.set('card_type', mapCategoryToCardType(filters.category));
        }

        if (filters?.status && filters.status !== 'all') {
          params.set('status', filters.status === 'archived' ? 'inactive' : 'active');
        } else {
          params.set('status', 'all');
        }

        if (filters?.searchQuery && filters.searchQuery.trim()) {
          params.set('search', filters.searchQuery.trim());
        }

        const url = `${API_BASE_URL}/api/policies?${params.toString()}`;
        const res = await fetch(url, {
          headers: { 'Content-Type': 'application/json' },
          cache: 'no-store',
        });

        if (res.ok) {
          const envelope = await res.json();
          const items: BackendPolicyResponse[] = Array.isArray(envelope) ? envelope : envelope.items || [];
          let mapped = items.map(mapBackendToFrontendPolicy);

          // Update local memory cache with latest authoritative data
          if (mapped.length > 0) {
            this.inMemoryPolicies = mapped;
            this.persistPolicies();
          }

          if (filters?.searchQuery && filters.searchQuery.trim()) {
            const query = filters.searchQuery.toLowerCase().trim();
            mapped = mapped.filter(
              (p) =>
                p.title.toLowerCase().includes(query) ||
                p.id.toLowerCase().includes(query) ||
                p.content.toLowerCase().includes(query) ||
                (p.metadata.author && String(p.metadata.author).toLowerCase().includes(query)) ||
                (p.metadata.prohibited_terms && JSON.stringify(p.metadata.prohibited_terms).toLowerCase().includes(query))
            );
          }

          if (filters?.sortBy) {
            if (filters.sortBy === 'title_asc') {
              mapped.sort((a, b) => a.title.localeCompare(b.title));
            } else if (filters.sortBy === 'version_desc') {
              mapped.sort((a, b) => b.version.localeCompare(a.version));
            } else if (filters.sortBy === 'updated_desc') {
              mapped.sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''));
            }
          }

          return {
            policies: mapped,
            total: envelope.total !== undefined ? envelope.total : mapped.length,
            dataSource: 'backend_api',
          };
        }
      } catch (err) {
        console.warn('Backend policy request failed, falling back to local adapter:', err);
      }
    }

    // Development adapter with filtering
    let results = [...this.inMemoryPolicies];

    if (filters) {
      if (filters.searchQuery && filters.searchQuery.trim()) {
        const query = filters.searchQuery.toLowerCase().trim();
        results = results.filter(
          (p) =>
            p.title.toLowerCase().includes(query) ||
            p.id.toLowerCase().includes(query) ||
            p.content.toLowerCase().includes(query) ||
            (p.metadata.author && String(p.metadata.author).toLowerCase().includes(query)) ||
            (p.metadata.prohibited_terms && JSON.stringify(p.metadata.prohibited_terms).toLowerCase().includes(query))
        );
      }

      if (filters.category && filters.category !== 'all') {
        results = results.filter((p) => p.category.toLowerCase() === filters.category!.toLowerCase());
      }

      if (filters.status && filters.status !== 'all') {
        results = results.filter((p) => (p.status || 'approved').toLowerCase() === filters.status!.toLowerCase());
      }

      if (filters.brandId && filters.brandId !== 'all') {
        results = results.filter((p) => p.metadata.brand_id === filters.brandId);
      }

      if (filters.sortBy) {
        if (filters.sortBy === 'title_asc') {
          results.sort((a, b) => a.title.localeCompare(b.title));
        } else if (filters.sortBy === 'version_desc') {
          results.sort((a, b) => b.version.localeCompare(a.version));
        } else if (filters.sortBy === 'updated_desc') {
          results.sort((a, b) => (b.updated_at || '').localeCompare(a.updated_at || ''));
        }
      }
    }

    return {
      policies: results,
      total: results.length,
      dataSource: 'dev_adapter',
    };
  }

  /**
   * Get single policy by ID.
   */
  public async getPolicyById(id: string): Promise<PolicyCard | null> {
    if (isBackendEnabled()) {
      try {
        const res = await fetch(`${API_BASE_URL}/api/policies/${encodeURIComponent(id)}`, {
          headers: { 'Content-Type': 'application/json' },
          cache: 'no-store',
        });
        if (res.ok) {
          const data: BackendPolicyResponse = await res.json();
          return mapBackendToFrontendPolicy(data);
        }
      } catch {
        // Fall back to memory
      }
    }
    const policy = this.inMemoryPolicies.find((p) => p.id === id);
    return policy || null;
  }

  /**
   * Create a new approved or draft policy.
   * Backend is authoritative: server rejections are immediately thrown.
   */
  public async createPolicy(newPolicy: Omit<PolicyCard, 'created_at' | 'updated_at'>): Promise<PolicyCard> {
    // 1. Check ID uniqueness in local memory
    if (this.inMemoryPolicies.some((p) => p.id === newPolicy.id)) {
      throw new Error(`Policy ID '${newPolicy.id}' already exists. Policy identifiers must be unique.`);
    }

    // 2. Validate quote integrity ("No receipt, no flag")
    const quote =
      (newPolicy.metadata.quote as string) ||
      (newPolicy.rules[0] && (newPolicy.rules[0] as { quote?: string }).quote) ||
      (newPolicy.metadata.source_quote as string);
    if (quote) {
      const check = this.verifyQuoteIntegrity(newPolicy.content, quote);
      if (!check.isValid) {
        throw new Error(check.error);
      }
    }

    if (isBackendEnabled()) {
      try {
        const backendPayload = mapFrontendToBackendPayload(newPolicy);
        const res = await fetch(`${API_BASE_URL}/api/policies`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(backendPayload),
        });

        if (res.ok) {
          const createdBackend: BackendPolicyResponse = await res.json();
          const mapped = mapBackendToFrontendPolicy(createdBackend);
          this.inMemoryPolicies.unshift(mapped);
          this.persistPolicies();
          return mapped;
        } else {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Backend error: status ${res.status}`);
        }
      } catch (err: any) {
        // If server actively rejected or failed, throw without silent false success
        if (err.message && !err.message.includes('fetch failed') && !err.message.includes('ECONNREFUSED')) {
          throw err;
        }
        if (process.env.NEXT_PUBLIC_USE_BACKEND_CRUD === 'true') {
          throw err;
        }
      }
    }

    const now = new Date().toISOString();
    const created: PolicyCard = {
      ...newPolicy,
      status: newPolicy.status || 'approved',
      created_at: now,
      updated_at: now,
    };

    this.inMemoryPolicies.unshift(created);
    this.persistPolicies();
    return created;
  }

  /**
   * Update an existing policy card.
   * If updating an approved policy, advances the version string or marks updated.
   */
  public async updatePolicy(id: string, updates: Partial<PolicyCard>): Promise<PolicyCard> {
    const index = this.inMemoryPolicies.findIndex((p) => p.id === id);
    if (index === -1) {
      throw new Error(`Policy with ID '${id}' not found.`);
    }

    const current = this.inMemoryPolicies[index];
    const content = updates.content !== undefined ? updates.content : current.content;
    const quote =
      updates.metadata?.quote !== undefined
        ? (updates.metadata.quote as string)
        : (current.metadata.quote as string);

    if (quote) {
      const check = this.verifyQuoteIntegrity(content, quote);
      if (!check.isValid) {
        throw new Error(check.error);
      }
    }

    if (isBackendEnabled()) {
      try {
        const targetId = (current.metadata?.backend_id as string) || id;
        const backendPayload = mapFrontendToBackendPayload({ ...current, ...updates });
        const res = await fetch(`${API_BASE_URL}/api/policies/${encodeURIComponent(targetId)}`, {
          method: 'PATCH',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify(backendPayload),
        });

        if (res.ok) {
          const updatedBackend: BackendPolicyResponse = await res.json();
          const mapped = mapBackendToFrontendPolicy(updatedBackend);
          this.inMemoryPolicies[index] = mapped;
          this.persistPolicies();
          return mapped;
        } else {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Backend update failed (HTTP ${res.status})`);
        }
      } catch (err: any) {
        if (err.message && !err.message.includes('fetch failed') && !err.message.includes('ECONNREFUSED')) {
          throw err;
        }
        if (process.env.NEXT_PUBLIC_USE_BACKEND_CRUD === 'true') {
          throw err;
        }
      }
    }

    const now = new Date().toISOString();
    const updated: PolicyCard = {
      ...current,
      ...updates,
      id: current.id,
      updated_at: now,
    };

    this.inMemoryPolicies[index] = updated;
    this.persistPolicies();
    return updated;
  }

  /**
   * Archive a policy.
   */
  public async archivePolicy(id: string): Promise<PolicyCard> {
    if (isBackendEnabled()) {
      try {
        const current = this.inMemoryPolicies.find((p) => p.id === id);
        const targetId = (current?.metadata?.backend_id as string) || id;
        let res = await fetch(`${API_BASE_URL}/api/policies/${encodeURIComponent(targetId)}/archive`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
        });

        if (!res.ok && res.status === 404) {
          res = await fetch(`${API_BASE_URL}/api/policies/${encodeURIComponent(targetId)}`, {
            method: 'PATCH',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ status: 'inactive' }),
          });
        }

        if (res.ok) {
          const updatedBackend: BackendPolicyResponse = await res.json();
          const mapped = mapBackendToFrontendPolicy(updatedBackend);
          const index = this.inMemoryPolicies.findIndex((p) => p.id === id);
          if (index !== -1) {
            this.inMemoryPolicies[index] = mapped;
            this.persistPolicies();
          }
          return mapped;
        } else {
          const errData = await res.json().catch(() => ({}));
          throw new Error(errData.detail || `Backend archive failed (HTTP ${res.status})`);
        }
      } catch (err: any) {
        if (err.message && !err.message.includes('fetch failed') && !err.message.includes('ECONNREFUSED')) {
          throw err;
        }
        if (process.env.NEXT_PUBLIC_USE_BACKEND_CRUD === 'true') {
          throw err;
        }
      }
    }
    return this.updatePolicy(id, { status: 'archived' });
  }

  /**
   * Reset store to initial seed data.
   */
  public resetToDefault(): void {
    this.inMemoryPolicies = [...INITIAL_POLICY_CARDS];
    this.inMemoryBrands = [...INITIAL_BRAND_PROFILES];
    this.persistPolicies();
  }

  /**
   * Retrieve Brand Passport profiles.
   */
  public async getBrandProfiles(): Promise<BrandProfile[]> {
    return [...this.inMemoryBrands];
  }

  public async getBrandProfile(brandId: string): Promise<BrandProfile | null> {
    return this.inMemoryBrands.find((b) => b.id === brandId) || this.inMemoryBrands[0] || null;
  }

  /**
   * Dedicated export contract for the Scan Workspace
   * and Rules Engine.
   * 
   * Returns ONLY approved policies (excluding drafts and archived policies),
   * formatted strictly to match backend/app/schemas/policy.py:PolicyCard.
   */
  public async getApprovedPoliciesForScan(brandId?: string): Promise<Array<Record<string, unknown>>> {
    const { policies } = await this.getPolicies({
      status: 'approved',
      brandId: brandId && brandId !== 'all' ? brandId : undefined,
    });

    return policies.map((p) => ({
      id: p.id,
      version: p.version,
      title: p.title || '',
      category: p.category || '',
      content: p.content,
      rules: p.rules || [],
      metadata: p.metadata || {},
    }));
  }
}

export const policyClient = new PolicyClient();
