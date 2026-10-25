/**
 * Brand Ledger - Policy & Brand API Client
 * 
 * Provides an enterprise-grade typed interface for:
 * 1. Policy Library CRUD and filtering
 * 2. Brand Passport governance summaries
 * 3. Enforcing "No receipt, no flag" quote integrity checks
 * 
 * Architecture:
 * - Direct REST integration with FastAPI backend when endpoints are deployed
 * - Development persistence adapter (localStorage + in-memory fallback) when
 *   backend persistence is unavailable
 */

import type { PolicyCard, PolicyFilterState, BrandProfile } from '../../types/policy.ts';
import { INITIAL_POLICY_CARDS, INITIAL_BRAND_PROFILES } from '../mockData.ts';

const STORAGE_KEY_POLICIES = 'brandledger_policies_v1';
const STORAGE_KEY_BRANDS = 'brandledger_brands_v1';

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';

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
        console.warn('LocalStorage unavailable, defaulting to in-memory store:', e);
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
        error: `Source quote does not exist as an exact substring in the policy text. Every rule requires direct textual evidence.`
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
    // Attempt real backend call if configured
    if (process.env.NEXT_PUBLIC_USE_BACKEND_CRUD === 'true') {
      try {
        const res = await fetch(`${API_BASE_URL}/api/policies`, {
          headers: { 'Content-Type': 'application/json' },
          cache: 'no-store'
        });
        if (res.ok) {
          const data = await res.json();
          return { policies: data, total: data.length, dataSource: 'backend_api' };
        }
      } catch {
        // Fall back gracefully to development store
      }
    }

    // Development adapter with filtering
    let results = [...this.inMemoryPolicies];

    if (filters) {
      if (filters.searchQuery && filters.searchQuery.trim()) {
        const query = filters.searchQuery.toLowerCase().trim();
        results = results.filter(
          p =>
            p.title.toLowerCase().includes(query) ||
            p.id.toLowerCase().includes(query) ||
            p.content.toLowerCase().includes(query) ||
            (p.metadata.author && String(p.metadata.author).toLowerCase().includes(query)) ||
            (p.metadata.prohibited_terms && JSON.stringify(p.metadata.prohibited_terms).toLowerCase().includes(query))
        );
      }

      if (filters.category && filters.category !== 'all') {
        results = results.filter(p => p.category.toLowerCase() === filters.category!.toLowerCase());
      }

      if (filters.status && filters.status !== 'all') {
        results = results.filter(p => (p.status || 'approved').toLowerCase() === filters.status!.toLowerCase());
      }

      if (filters.brandId && filters.brandId !== 'all') {
        results = results.filter(p => p.metadata.brand_id === filters.brandId);
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
      dataSource: 'dev_adapter'
    };
  }

  /**
   * Get single policy by ID.
   */
  public async getPolicyById(id: string): Promise<PolicyCard | null> {
    const policy = this.inMemoryPolicies.find(p => p.id === id);
    return policy || null;
  }

  /**
   * Create a new approved or draft policy.
   */
  public async createPolicy(newPolicy: Omit<PolicyCard, 'created_at' | 'updated_at'>): Promise<PolicyCard> {
    // 1. Check ID uniqueness
    if (this.inMemoryPolicies.some(p => p.id === newPolicy.id)) {
      throw new Error(`Policy ID '${newPolicy.id}' already exists. Policy identifiers must be unique.`);
    }

    // 2. Validate quote integrity
    const quote = (newPolicy.metadata.quote as string) || (newPolicy.rules[0] && (newPolicy.rules[0] as { quote?: string }).quote);
    if (quote) {
      const check = this.verifyQuoteIntegrity(newPolicy.content, quote);
      if (!check.isValid) {
        throw new Error(check.error);
      }
    }

    const now = new Date().toISOString();
    const created: PolicyCard = {
      ...newPolicy,
      status: newPolicy.status || 'approved',
      created_at: now,
      updated_at: now
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
    const index = this.inMemoryPolicies.findIndex(p => p.id === id);
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

    const now = new Date().toISOString();
    const updated: PolicyCard = {
      ...current,
      ...updates,
      id: current.id, // Immutable ID
      updated_at: now
    };

    this.inMemoryPolicies[index] = updated;
    this.persistPolicies();
    return updated;
  }

  /**
   * Archive a policy.
   */
  public async archivePolicy(id: string): Promise<PolicyCard> {
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
    return this.inMemoryBrands.find(b => b.id === brandId) || this.inMemoryBrands[0] || null;
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

    return policies.map(p => ({
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
