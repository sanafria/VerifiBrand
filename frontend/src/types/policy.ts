/**
 * Brand Ledger - Policy Library & Brand Passport Type Definitions
 * 
 * Accurately mirrors and extends backend/app/schemas/policy.py and backend/app/schemas/finding.py
 * while preserving full compatibility with the compliance rules engine
 * and shared API layer.
 */

export type PolicyCategory = 
  | 'terminology'
  | 'offer_validity'
  | 'numerical'
  | 'claims'
  | 'tone'
  | 'visual';

export type PolicyStatus = 'approved' | 'draft' | 'archived';

export type LimitType = 'max' | 'exact' | 'min' | 'standard';

export interface BaseRule {
  type: string;
  quote?: string;
}

export interface TerminologyRule extends BaseRule {
  type: 'terminology' | 'term_prohibition';
  prohibited: string;
  replacement: string;
  quote: string;
}

export interface NumericalRule extends BaseRule {
  type: 'numerical' | 'factual_limit' | 'fact';
  metric: string;
  value: number;
  unit: string;
  limit_type: LimitType;
  quote: string;
}

export interface ClaimRule extends BaseRule {
  type: 'claim_verification' | 'claims' | 'unsupported_claims';
  requires_evidence: boolean;
  quote: string;
}

export interface OfferValidityRule extends BaseRule {
  type: 'offer_validity';
  offer_name: string;
  valid_until: string; // YYYY-MM-DD
  quote: string;
}

export type AnyRule = TerminologyRule | NumericalRule | ClaimRule | OfferValidityRule | Record<string, unknown>;

export interface PolicyMetadata {
  offer_name?: string;
  valid_until?: string;
  expires_at?: string;
  prohibited_terms?: Array<{ term: string; replacement: string }>;
  quote?: string;
  author?: string;
  approved_by?: string;
  brand_id?: string;
  brand_name?: string;
  last_updated?: string;
  status?: PolicyStatus;
  changelog?: string;
  [key: string]: unknown;
}

/**
 * Exact representation of PolicyCard conforming to backend/app/schemas/policy.py
 */
export interface PolicyCard {
  id: string;
  version: string;
  title: string;
  category: PolicyCategory | string;
  content: string;
  rules: AnyRule[];
  metadata: PolicyMetadata;
  status?: PolicyStatus;
  created_at?: string;
  updated_at?: string;
}

export interface PolicyFilterState {
  searchQuery: string;
  category: string; // 'all' | PolicyCategory
  status: string;   // 'all' | PolicyStatus
  brandId: string;  // 'all' | specific brand ID
  sortBy: 'updated_desc' | 'title_asc' | 'version_desc';
}

export interface BrandColor {
  name: string;
  hex: string;
  usage: string;
}

export interface BrandProfile {
  id: string;
  name: string;
  tagline: string;
  industry: string;
  mission: string;
  governanceScore: number;
  lastCertifiedDate: string;
  certifiedBy: string;
  voicePillars: Array<{
    title: string;
    description: string;
    dos: string[];
    donts: string[];
  }>;
  colors: BrandColor[];
  logoGuidelines: {
    minClearSpacePx: number;
    lightBgUrl?: string;
    darkBgUrl?: string;
    prohibitedModifications: string[];
  };
}
