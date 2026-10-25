/**
 * Brand Ledger - Seed Policy Data
 * 
 * Directly aligned with fixtures in backend/tests/conftest.py to ensure 100%
 * compatibility with the compliance rules engine and backend test cases.
 */

import type { PolicyCard, BrandProfile } from '../types/policy.ts';

export const INITIAL_BRAND_PROFILES: BrandProfile[] = [
  {
    id: 'brand_apex_01',
    name: 'Apex Health Technologies',
    tagline: 'Precision Care Governed by Trust & Transparency',
    industry: 'Healthcare & Clinical AI',
    mission: 'Empowering healthcare practitioners and patients with accountable, verified digital health records and intelligent diagnosis assistance.',
    governanceScore: 98,
    lastCertifiedDate: '2026-10-15',
    certifiedBy: 'Legal & Clinical Governance Committee',
    voicePillars: [
      {
        title: 'Empathetic & Member-Centric',
        description: 'Speak directly to the patient or practitioner with dignity, respect, and compassionate clarity.',
        dos: ['Refer to patients as Members', 'Use clear, reassuring language', 'Highlight patient autonomy'],
        donts: ['Never use impersonal labels like "Customers"', 'Never use alarmist clinical jargon', 'Avoid transactional phrasing']
      },
      {
        title: 'Evidence-Backed & Fact-Bound',
        description: 'Every medical claim and performance statement must be grounded in peer-reviewed clinical validation.',
        dos: ['Quote exact clinical efficacy percentages with citations', 'Qualify outcomes ("results may vary")', 'Provide legal disclosure links'],
        donts: ['Never claim "100% cure" or "guaranteed results"', 'Never make superlative claims like "#1 doctor choice" without audit receipts']
      },
      {
        title: 'Transparent & Accountable',
        description: 'Provide clear, explicit boundaries on pricing, discounts, and rewards redemption.',
        dos: ['State exact expiration dates on promotional offers', 'State numerical reward caps explicitly', 'Clarify data usage policies'],
        donts: ['Hide expiration dates in asterisks', 'Promise unlimited loyalty points']
      }
    ],
    colors: [
      { name: 'Apex Navy', hex: '#0F172A', usage: 'Primary brand dark, headers, authoritative text' },
      { name: 'Clinical Indigo', hex: '#3B82F6', usage: 'Primary accent, interactive elements, verified chips' },
      { name: 'Healing Teal', hex: '#0D9488', usage: 'Success states, approved policy badges, metrics' },
      { name: 'Warm Amber', hex: '#F59E0B', usage: 'Expiring offer warnings, terminology cautions' },
      { name: 'Critical Crimson', hex: '#EF4444', usage: 'Prohibited terms, expired promotions, violations' }
    ],
    logoGuidelines: {
      minClearSpacePx: 28,
      prohibitedModifications: [
        'Do not stretch, skew, or rotate the emblem',
        'Do not place the navy logo over low-contrast dark backgrounds',
        'Do not alter the gradient angle of the clinical cross'
      ]
    }
  },
  {
    id: 'brand_novapay_02',
    name: 'NovaPay Global Ledger',
    tagline: 'Enterprise Financial Clearing with Deterministic Proof',
    industry: 'FinTech & Blockchain Governance',
    mission: 'Providing cross-border treasury settlements with real-time compliance validation and cryptographic receipt auditing.',
    governanceScore: 94,
    lastCertifiedDate: '2026-09-30',
    certifiedBy: 'Global Financial Compliance Council',
    voicePillars: [
      {
        title: 'Institutional Rigor',
        description: 'Professional, precise, and devoid of speculative cryptocurrency hype.',
        dos: ['Use established banking terminology', 'Cite regulatory licenses'],
        donts: ['Never use speculative hype like "to the moon"', 'Avoid unverified return promises']
      }
    ],
    colors: [
      { name: 'Deep Slate', hex: '#1E293B', usage: 'Primary background' },
      { name: 'Emerald Vault', hex: '#10B981', usage: 'Verified settlements' }
    ],
    logoGuidelines: {
      minClearSpacePx: 24,
      prohibitedModifications: ['Do not apply drop shadows to NovaPay wordmark']
    }
  }
];

export const INITIAL_POLICY_CARDS: PolicyCard[] = [
  {
    id: 'pol_term_001',
    version: '1.0',
    title: 'Brand Terminology Policy',
    category: 'terminology',
    status: 'approved',
    created_at: '2026-01-10T09:00:00Z',
    updated_at: '2026-10-15T14:30:00Z',
    content: "The brand prohibits the term 'Customers' and requires the term 'Members'. Always refer to account holders as members.",
    rules: [
      {
        type: 'terminology',
        prohibited: 'Customers',
        replacement: 'Members',
        quote: "The brand prohibits the term 'Customers' and requires the term 'Members'."
      }
    ],
    metadata: {
      brand_id: 'brand_apex_01',
      brand_name: 'Apex Health Technologies',
      author: 'Legal & Communications Team',
      approved_by: 'Executive Brand Director',
      prohibited_terms: [{ term: 'Customers', replacement: 'Members' }],
      quote: "The brand prohibits the term 'Customers' and requires the term 'Members'."
    }
  },
  {
    id: 'pol_offer_002',
    version: '2.1',
    title: 'Summer Discount Promotion',
    category: 'offer_validity',
    status: 'approved',
    created_at: '2026-05-01T10:00:00Z',
    updated_at: '2026-06-01T11:00:00Z',
    content: 'Summer Discount promotion is valid through 2026-06-30. After this date, standard pricing applies.',
    rules: [
      {
        type: 'offer_validity',
        offer_name: 'Summer Discount',
        valid_until: '2026-06-30',
        quote: 'Summer Discount promotion is valid through 2026-06-30.'
      }
    ],
    metadata: {
      brand_id: 'brand_apex_01',
      brand_name: 'Apex Health Technologies',
      author: 'Marketing Operations',
      approved_by: 'Commercial Director',
      offer_name: 'Summer Discount',
      valid_until: '2026-06-30',
      expires_at: '2026-06-30',
      quote: 'Summer Discount promotion is valid through 2026-06-30.'
    }
  },
  {
    id: 'pol_num_003',
    version: '1.5',
    title: 'Rewards Program Limits',
    category: 'numerical',
    status: 'approved',
    created_at: '2026-02-15T12:00:00Z',
    updated_at: '2026-08-20T16:15:00Z',
    content: 'The maximum reward is 500 points for any individual transaction. Points cannot be transferred.',
    rules: [
      {
        type: 'numerical',
        metric: 'reward',
        value: 500,
        unit: 'points',
        limit_type: 'max',
        quote: 'The maximum reward is 500 points for any individual transaction.'
      }
    ],
    metadata: {
      brand_id: 'brand_apex_01',
      brand_name: 'Apex Health Technologies',
      author: 'Loyalty & Customer Success',
      approved_by: 'Finance & Compliance Head',
      metric: 'reward',
      value: 500,
      unit: 'points',
      quote: 'The maximum reward is 500 points for any individual transaction.'
    }
  },
  {
    id: 'pol_claim_004',
    version: '3.0',
    title: 'Marketing Claim Substantiation',
    category: 'claims',
    status: 'approved',
    created_at: '2026-03-01T08:30:00Z',
    updated_at: '2026-09-12T13:45:00Z',
    content: 'All performance guarantees and promises of guaranteed results require prior approved evidence from legal compliance.',
    rules: [
      {
        type: 'claim_verification',
        requires_evidence: true,
        quote: 'All performance guarantees and promises of guaranteed results require prior approved evidence from legal compliance.'
      }
    ],
    metadata: {
      brand_id: 'brand_apex_01',
      brand_name: 'Apex Health Technologies',
      author: 'Regulatory Affairs',
      approved_by: 'General Counsel',
      requires_evidence: true,
      quote: 'All performance guarantees and promises of guaranteed results require prior approved evidence from legal compliance.'
    }
  },
  {
    id: 'pol_tone_005',
    version: '1.0',
    title: 'Clinical Voice & Compassion Standard',
    category: 'tone',
    status: 'approved',
    created_at: '2026-04-10T14:00:00Z',
    updated_at: '2026-10-01T10:20:00Z',
    content: 'Draft marketing copy must maintain a professional and empathetic tone. Sensationalist claims and high-pressure sales urgency are strictly prohibited.',
    rules: [
      {
        type: 'tone_guideline',
        prohibited_tones: ['sensationalist', 'aggressive', 'fear-inducing'],
        required_tones: ['professional', 'empathetic'],
        quote: 'Draft marketing copy must maintain a professional and empathetic tone.'
      }
    ],
    metadata: {
      brand_id: 'brand_apex_01',
      brand_name: 'Apex Health Technologies',
      author: 'Brand Editorial Board',
      approved_by: 'VP of Patient Experience',
      quote: 'Draft marketing copy must maintain a professional and empathetic tone.'
    }
  },
  {
    id: 'pol_vis_006',
    version: '1.2',
    title: 'Visual Identity & Logo Safe Zones',
    category: 'visual',
    status: 'approved',
    created_at: '2026-02-01T11:00:00Z',
    updated_at: '2026-07-15T09:30:00Z',
    content: 'The official Apex Health mark requires a minimum clear space of 28 pixels on all digital collateral. Authorized brand primary hex is #0F172A.',
    rules: [
      {
        type: 'visual_asset',
        min_clear_space_px: 28,
        primary_color_hex: '#0F172A',
        quote: 'The official Apex Health mark requires a minimum clear space of 28 pixels on all digital collateral.'
      }
    ],
    metadata: {
      brand_id: 'brand_apex_01',
      brand_name: 'Apex Health Technologies',
      author: 'Creative Studio',
      approved_by: 'Design Director',
      quote: 'The official Apex Health mark requires a minimum clear space of 28 pixels on all digital collateral.'
    }
  }
];
