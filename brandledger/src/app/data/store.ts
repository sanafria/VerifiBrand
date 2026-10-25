// ─── VerifiBrand Mock Data Store ───
// All data for the demo. In production, this would come from Supabase.

export type CardType = 'offer' | 'term' | 'fact' | 'asset' | 'claim' | 'tone' | 'accessibility';
export type CardStatus = 'active' | 'expired' | 'draft' | 'retired';
export type Severity = 'block' | 'warning' | 'info';
export type DetectionMethod = 'rule-detected' | 'ai-detected';
export type ContentStatus = 'draft' | 'scanning' | 'in-review' | 'approved' | 'rejected';
export type PassportStatus = 'valid' | 'revalidation_required' | 'revoked';
export type FindingAction = 'pending' | 'accepted' | 'edited' | 'dismissed';
export type UserRole = 'admin' | 'manager' | 'creator' | 'reviewer';

export interface PolicyCard {
  id: string;
  type: CardType;
  title: string;
  content: string;
  validFrom?: string;
  validTo?: string;
  severity: Severity;
  status: CardStatus;
  version: number;
  createdBy: string;
  createdAt: string;
  updatedAt: string;
  tags: string[];
}

export interface Finding {
  id: string;
  type: string;
  severity: Severity;
  detectionMethod: DetectionMethod;
  originalText: string;
  issue: string;
  evidenceQuote: string;
  sourceCardId: string;
  sourceCardVersion: number;
  suggestedFix: string;
  confidence: 'high' | 'medium' | 'low';
  action: FindingAction;
  dismissReason?: string;
}

export interface ContentSubmission {
  id: string;
  title: string;
  contentType: 'text' | 'image' | 'pdf';
  body: string;
  status: ContentStatus;
  submittedBy: string;
  submittedAt: string;
  findings: Finding[];
  reviewerId?: string;
  reviewComment?: string;
  passportId?: string;
}

export interface ContentPassport {
  id: string;
  contentId: string;
  contentTitle: string;
  status: PassportStatus;
  approvedBy: string;
  approvedAt: string;
  findingsResolved: number;
  findingsDismissed: number;
  dependencies: { cardId: string; cardTitle: string; version: number }[];
}

export interface AuditEntry {
  id: string;
  action: string;
  actor: string;
  target: string;
  timestamp: string;
  details: string;
}

export interface User {
  id: string;
  name: string;
  email: string;
  role: UserRole;
  avatar: string;
}

// ─── Users ───
export const users: User[] = [
  { id: 'u1', name: 'Alex Rivera', email: 'alex@novabrand.com', role: 'manager', avatar: 'AR' },
  { id: 'u2', name: 'Jordan Kim', email: 'jordan@novabrand.com', role: 'creator', avatar: 'JK' },
  { id: 'u3', name: 'Sam Okafor', email: 'sam@novabrand.com', role: 'reviewer', avatar: 'SO' },
  { id: 'u4', name: 'Dana Chen', email: 'dana@novabrand.com', role: 'admin', avatar: 'DC' },
  { id: 'u5', name: 'Priya Sharma', email: 'priya@novabrand.com', role: 'creator', avatar: 'PS' },
];

// ─── Policy Cards ───
export const initialPolicyCards: PolicyCard[] = [
  {
    id: 'OFFER_014',
    type: 'offer',
    title: '20% September Discount',
    content: 'Offer valid only from Sept 1 to Sept 30, 2026. Use code SEPT20. Applicable on all plans except Enterprise. Cannot be combined with other offers.',
    validFrom: '2026-09-01',
    validTo: '2026-09-30',
    severity: 'block',
    status: 'expired',
    version: 3,
    createdBy: 'u1',
    createdAt: '2026-08-25T10:00:00Z',
    updatedAt: '2026-09-15T14:30:00Z',
    tags: ['discount', 'campaign', 'q3'],
  },
  {
    id: 'OFFER_015',
    type: 'offer',
    title: '15% October Promotion',
    content: 'Offer valid from Oct 1 to Oct 31, 2026. Use code OCT15. Applicable on Starter and Growth plans. Not valid for existing subscribers on annual plans.',
    validFrom: '2026-10-01',
    validTo: '2026-10-31',
    severity: 'block',
    status: 'active',
    version: 1,
    createdBy: 'u1',
    createdAt: '2026-09-28T09:00:00Z',
    updatedAt: '2026-09-28T09:00:00Z',
    tags: ['discount', 'campaign', 'q4'],
  },
  {
    id: 'TERM_003',
    type: 'term',
    title: 'Address as "Members"',
    content: 'Always address the audience as "Members" in all customer-facing campaign copy. Never use "Customers", "Users", or "Subscribers" in marketing materials.',
    severity: 'warning',
    status: 'active',
    version: 2,
    createdBy: 'u1',
    createdAt: '2026-06-10T08:00:00Z',
    updatedAt: '2026-08-20T11:00:00Z',
    tags: ['terminology', 'voice', 'brand'],
  },
  {
    id: 'TERM_004',
    type: 'term',
    title: 'Product Name: "NovaShield Pro"',
    content: 'The product must always be referred to as "NovaShield Pro" (capitalized). Never abbreviate as "NSP" or "Nova Shield" (with space). The ™ symbol is required on first mention in any document.',
    severity: 'warning',
    status: 'active',
    version: 1,
    createdBy: 'u1',
    createdAt: '2026-07-01T09:00:00Z',
    updatedAt: '2026-07-01T09:00:00Z',
    tags: ['product', 'naming', 'trademark'],
  },
  {
    id: 'FACT_001',
    type: 'fact',
    title: 'Company Founded Year',
    content: 'NovaBrand was founded in 2019. Do not state 2018 or 2020. If stating age, compute from 2019.',
    severity: 'block',
    status: 'active',
    version: 1,
    createdBy: 'u1',
    createdAt: '2026-05-01T08:00:00Z',
    updatedAt: '2026-05-01T08:00:00Z',
    tags: ['company', 'history'],
  },
  {
    id: 'FACT_002',
    type: 'fact',
    title: 'Active User Count',
    content: 'NovaBrand has 2M+ active users as of Q3 2026. Do not state exact numbers beyond this. For internal docs, the exact figure is 2,147,000.',
    severity: 'warning',
    status: 'active',
    version: 3,
    createdBy: 'u1',
    createdAt: '2026-04-15T10:00:00Z',
    updatedAt: '2026-09-30T16:00:00Z',
    tags: ['metrics', 'users', 'growth'],
  },
  {
    id: 'CLAIM_001',
    type: 'claim',
    title: '"Award-Winning" Requires Citation',
    content: 'The phrase "award-winning" may only be used when accompanied by the specific award name and year. Accepted awards: TechVenture Innovation Award 2025, Digital Excellence Prize 2026. Any other award claim needs legal pre-approval.',
    severity: 'block',
    status: 'active',
    version: 2,
    createdBy: 'u3',
    createdAt: '2026-03-01T08:00:00Z',
    updatedAt: '2026-07-15T14:00:00Z',
    tags: ['legal', 'claims', 'compliance'],
  },
  {
    id: 'CLAIM_002',
    type: 'claim',
    title: '"Industry Leader" Statement',
    content: '"Industry leader" or "market leader" claims require third-party evidence from a recognized analyst firm (Gartner, Forrester, or IDC). Internal data alone is not sufficient for public-facing claims.',
    severity: 'block',
    status: 'active',
    version: 1,
    createdBy: 'u3',
    createdAt: '2026-06-20T09:00:00Z',
    updatedAt: '2026-06-20T09:00:00Z',
    tags: ['legal', 'claims', 'compliance'],
  },
  {
    id: 'ASSET_001',
    type: 'asset',
    title: 'Current Logo (2025 Rebrand)',
    content: 'Use only the 2025 rebranded logo. The logo uses the "NovaBrand" wordmark in DM Sans Bold with the shield icon in forest green (#1B4D3E). Minimum clear space: 16px on all sides.',
    severity: 'block',
    status: 'active',
    version: 1,
    createdBy: 'u1',
    createdAt: '2026-01-15T10:00:00Z',
    updatedAt: '2026-01-15T10:00:00Z',
    tags: ['logo', 'visual', 'brand-identity'],
  },
  {
    id: 'ASSET_002',
    type: 'asset',
    title: 'Old Circular Logo (Retired)',
    content: 'The circular logo from 2020–2024 is retired. Do not use in any new materials. If found in templates, replace with ASSET_001.',
    severity: 'block',
    status: 'retired',
    version: 1,
    createdBy: 'u1',
    createdAt: '2026-01-15T10:30:00Z',
    updatedAt: '2026-01-15T10:30:00Z',
    tags: ['logo', 'visual', 'retired'],
  },
  {
    id: 'TONE_001',
    type: 'tone',
    title: 'Brand Voice Profile',
    content: 'NovaBrand voice is professional yet approachable. Avoid jargon. Use active voice. Sentences should average 15–20 words. Exclamation marks: max 1 per piece. No ALL CAPS unless it is a legal requirement.',
    severity: 'warning',
    status: 'active',
    version: 2,
    createdBy: 'u1',
    createdAt: '2026-02-01T09:00:00Z',
    updatedAt: '2026-08-10T11:00:00Z',
    tags: ['tone', 'voice', 'writing'],
  },
  {
    id: 'ACC_002',
    type: 'accessibility',
    title: 'Image Accessibility Rules',
    content: 'All images must have descriptive alt text (not just "image" or filename). Text on images must meet WCAG AA contrast ratio (4.5:1 for normal text, 3:1 for large text). Decorative images should have empty alt="".',
    severity: 'warning',
    status: 'active',
    version: 1,
    createdBy: 'u1',
    createdAt: '2026-04-01T08:00:00Z',
    updatedAt: '2026-04-01T08:00:00Z',
    tags: ['accessibility', 'wcag', 'images'],
  },
];

// ─── Content Submissions ───
export const initialSubmissions: ContentSubmission[] = [
  {
    id: 'SUB_001',
    title: 'October Social Campaign — Instagram Post',
    contentType: 'text',
    body: `🚀 Get 20% OFF all NovaBrand plans this October! Our award-winning platform helps customers achieve more. Join 3 million users who trust Nova Shield. Founded in 2018, we've been leading the industry ever since. Use code SEPT20 at checkout!\n\n#NovaBrand #Discount #BestInClass`,
    status: 'in-review',
    submittedBy: 'u2',
    submittedAt: '2026-10-15T09:30:00Z',
    findings: [
      {
        id: 'f1',
        type: 'Expired Offer',
        severity: 'block',
        detectionMethod: 'rule-detected',
        originalText: 'Get 20% OFF all NovaBrand plans this October!',
        issue: 'The 20% discount promotion expired on Sept 30, 2026. The current active offer is 15% for October.',
        evidenceQuote: 'Offer valid only from Sept 1 to Sept 30, 2026. Use code SEPT20.',
        sourceCardId: 'OFFER_014',
        sourceCardVersion: 3,
        suggestedFix: 'Get 15% OFF Starter and Growth plans this October! Use code OCT15.',
        confidence: 'high',
        action: 'pending',
      },
      {
        id: 'f2',
        type: 'Wrong Promo Code',
        severity: 'block',
        detectionMethod: 'rule-detected',
        originalText: 'Use code SEPT20 at checkout!',
        issue: 'SEPT20 is the expired September promo code. The current October code is OCT15.',
        evidenceQuote: 'Offer valid from Oct 1 to Oct 31, 2026. Use code OCT15.',
        sourceCardId: 'OFFER_015',
        sourceCardVersion: 1,
        suggestedFix: 'Use code OCT15 at checkout!',
        confidence: 'high',
        action: 'pending',
      },
      {
        id: 'f3',
        type: 'Terminology Violation',
        severity: 'warning',
        detectionMethod: 'rule-detected',
        originalText: 'helps customers achieve more',
        issue: 'The term "customers" should be "Members" in all customer-facing campaign copy.',
        evidenceQuote: 'Always address the audience as "Members" in all customer-facing campaign copy.',
        sourceCardId: 'TERM_003',
        sourceCardVersion: 2,
        suggestedFix: 'helps Members achieve more',
        confidence: 'high',
        action: 'pending',
      },
      {
        id: 'f4',
        type: 'Unsupported Claim',
        severity: 'block',
        detectionMethod: 'ai-detected',
        originalText: 'award-winning platform',
        issue: '"Award-winning" requires the specific award name and year. No citation is provided in this copy.',
        evidenceQuote: 'The phrase "award-winning" may only be used when accompanied by the specific award name and year.',
        sourceCardId: 'CLAIM_001',
        sourceCardVersion: 2,
        suggestedFix: 'platform (winner of the Digital Excellence Prize 2026)',
        confidence: 'high',
        action: 'pending',
      },
      {
        id: 'f5',
        type: 'Incorrect Fact',
        severity: 'block',
        detectionMethod: 'rule-detected',
        originalText: 'Join 3 million users',
        issue: 'The approved user count is "2M+ active users". The stated "3 million" is unsupported.',
        evidenceQuote: 'NovaBrand has 2M+ active users as of Q3 2026.',
        sourceCardId: 'FACT_002',
        sourceCardVersion: 3,
        suggestedFix: 'Join 2M+ users',
        confidence: 'high',
        action: 'pending',
      },
      {
        id: 'f6',
        type: 'Product Name Error',
        severity: 'warning',
        detectionMethod: 'rule-detected',
        originalText: 'trust Nova Shield',
        issue: 'The product name "Nova Shield" (with space) is incorrect. It should be "NovaShield Pro".',
        evidenceQuote: 'The product must always be referred to as "NovaShield Pro" (capitalized). Never abbreviate as "NSP" or "Nova Shield" (with space).',
        sourceCardId: 'TERM_004',
        sourceCardVersion: 1,
        suggestedFix: 'trust NovaShield Pro™',
        confidence: 'high',
        action: 'pending',
      },
      {
        id: 'f7',
        type: 'Incorrect Fact',
        severity: 'block',
        detectionMethod: 'rule-detected',
        originalText: 'Founded in 2018',
        issue: 'NovaBrand was founded in 2019, not 2018.',
        evidenceQuote: 'NovaBrand was founded in 2019. Do not state 2018 or 2020.',
        sourceCardId: 'FACT_001',
        sourceCardVersion: 1,
        suggestedFix: 'Founded in 2019',
        confidence: 'high',
        action: 'pending',
      },
      {
        id: 'f8',
        type: 'Unsupported Claim',
        severity: 'block',
        detectionMethod: 'ai-detected',
        originalText: 'leading the industry',
        issue: '"Industry leader" claims require third-party evidence from Gartner, Forrester, or IDC.',
        evidenceQuote: '"Industry leader" or "market leader" claims require third-party evidence from a recognized analyst firm.',
        sourceCardId: 'CLAIM_002',
        sourceCardVersion: 1,
        suggestedFix: 'growing steadily ever since',
        confidence: 'medium',
        action: 'pending',
      },
    ],
  },
  {
    id: 'SUB_002',
    title: 'Email Newsletter — October Edition',
    contentType: 'text',
    body: `Dear Members,\n\nWe're excited to announce our October promotion! Get 15% off on Starter and Growth plans using code OCT15.\n\nNovaShield Pro™ continues to protect over 2M+ active users worldwide. Your trust drives our innovation.\n\nWarm regards,\nThe NovaBrand Team`,
    status: 'approved',
    submittedBy: 'u5',
    submittedAt: '2026-10-12T14:00:00Z',
    findings: [],
    reviewerId: 'u3',
    reviewComment: 'Clean copy, all facts verified. Approved.',
    passportId: 'PASSPORT_110',
  },
  {
    id: 'SUB_003',
    title: 'Blog Post — Product Update Q4',
    contentType: 'text',
    body: `NovaShield Pro: What's New in Q4 2026\n\nSince our founding in 2019, NovaBrand has grown to serve 2M+ active users. This quarter, we're introducing three major updates to NovaShield Pro.\n\nAs the winner of the Digital Excellence Prize 2026, we're committed to delivering the best experience for our Members.\n\nUpgrade today and use code OCT15 for 15% off Starter and Growth plans. Offer valid through October 31.`,
    status: 'approved',
    submittedBy: 'u2',
    submittedAt: '2026-10-10T11:00:00Z',
    findings: [],
    reviewerId: 'u3',
    reviewComment: 'Excellent copy. All claims properly cited. Approved.',
    passportId: 'PASSPORT_111',
  },
  {
    id: 'SUB_004',
    title: 'Facebook Ad — Seasonal Campaign',
    contentType: 'text',
    body: `🎉 SPECIAL OFFER! NovaBrand is the BEST platform in the market!! Get 20% off NOW!!!\n\nMillions of customers love us. We're India's No. 1 security platform.\n\nSign up TODAY!!!`,
    status: 'rejected',
    submittedBy: 'u2',
    submittedAt: '2026-10-08T16:00:00Z',
    findings: [
      {
        id: 'f9',
        type: 'Tone Violation',
        severity: 'warning',
        detectionMethod: 'ai-detected',
        originalText: 'SPECIAL OFFER! ... BEST ... NOW!!!',
        issue: 'Multiple ALL CAPS words and excessive exclamation marks violate brand voice guidelines.',
        evidenceQuote: 'No ALL CAPS unless it is a legal requirement. Exclamation marks: max 1 per piece.',
        sourceCardId: 'TONE_001',
        sourceCardVersion: 2,
        suggestedFix: 'Special offer: NovaBrand is a leading platform in the market. Get 15% off today.',
        confidence: 'high',
        action: 'accepted',
      },
      {
        id: 'f10',
        type: 'Expired Offer',
        severity: 'block',
        detectionMethod: 'rule-detected',
        originalText: 'Get 20% off NOW',
        issue: 'The 20% discount expired Sept 30. Current offer is 15% for October.',
        evidenceQuote: 'Offer valid only from Sept 1 to Sept 30, 2026.',
        sourceCardId: 'OFFER_014',
        sourceCardVersion: 3,
        suggestedFix: 'Get 15% off on Starter and Growth plans.',
        confidence: 'high',
        action: 'accepted',
      },
      {
        id: 'f11',
        type: 'Terminology Violation',
        severity: 'warning',
        detectionMethod: 'rule-detected',
        originalText: 'customers love us',
        issue: '"Customers" should be "Members" in marketing copy.',
        evidenceQuote: 'Always address the audience as "Members" in all customer-facing campaign copy.',
        sourceCardId: 'TERM_003',
        sourceCardVersion: 2,
        suggestedFix: 'Members love us',
        confidence: 'high',
        action: 'accepted',
      },
      {
        id: 'f12',
        type: 'Unsupported Claim',
        severity: 'block',
        detectionMethod: 'ai-detected',
        originalText: "India's No. 1 security platform",
        issue: '"No. 1" is a superlative claim requiring third-party evidence. No supporting data found.',
        evidenceQuote: '"Industry leader" or "market leader" claims require third-party evidence from a recognized analyst firm.',
        sourceCardId: 'CLAIM_002',
        sourceCardVersion: 1,
        suggestedFix: 'Remove this claim or replace with a verifiable statement.',
        confidence: 'high',
        action: 'accepted',
      },
    ],
    reviewerId: 'u3',
    reviewComment: 'Too many violations. Rejected. Please rewrite following the brand guidelines.',
  },
  {
    id: 'SUB_005',
    title: 'LinkedIn Thought Leadership Post',
    contentType: 'text',
    body: `At NovaBrand, we believe in building trust through transparency.\n\nSince 2019, our team has focused on one mission: giving organizations the tools to protect their digital identity. Today, over 2M+ users rely on NovaShield Pro™ to safeguard their brand.\n\nWe're honoured to have received the Digital Excellence Prize 2026. But more than any award, what drives us is hearing from our Members about how NovaShield Pro has changed the way they work.\n\nWhat does brand trust mean to your organization?`,
    status: 'approved',
    submittedBy: 'u5',
    submittedAt: '2026-10-18T10:00:00Z',
    findings: [],
    reviewerId: 'u3',
    reviewComment: 'Professional tone, all facts correct, claim properly cited. Great piece.',
    passportId: 'PASSPORT_113',
  },
  {
    id: 'SUB_006',
    title: 'Product Landing Page — Hero Section',
    contentType: 'text',
    body: `NovaShield Pro™\nThe award-winning security platform trusted by 2M+ Members worldwide.\n\n✓ Real-time threat detection\n✓ Compliance automation\n✓ Winner of the Digital Excellence Prize 2026\n\nStart your free trial — 15% off Starter and Growth plans with code OCT15.\nOffer valid through October 31, 2026.`,
    status: 'in-review',
    submittedBy: 'u2',
    submittedAt: '2026-10-20T13:00:00Z',
    findings: [
      {
        id: 'f13',
        type: 'Verified Claim',
        severity: 'info',
        detectionMethod: 'ai-detected',
        originalText: 'award-winning security platform',
        issue: '"Award-winning" is properly cited with "Digital Excellence Prize 2026" later in the copy.',
        evidenceQuote: 'The phrase "award-winning" may only be used when accompanied by the specific award name and year.',
        sourceCardId: 'CLAIM_001',
        sourceCardVersion: 2,
        suggestedFix: 'No change needed.',
        confidence: 'high',
        action: 'accepted',
      },
    ],
    reviewerId: 'u3',
  },
];

// ─── Content Passports ───
export const initialPassports: ContentPassport[] = [
  {
    id: 'PASSPORT_110',
    contentId: 'SUB_002',
    contentTitle: 'Email Newsletter — October Edition',
    status: 'valid',
    approvedBy: 'Sam Okafor',
    approvedAt: '2026-10-12T16:00:00Z',
    findingsResolved: 0,
    findingsDismissed: 0,
    dependencies: [
      { cardId: 'OFFER_015', cardTitle: '15% October Promotion', version: 1 },
      { cardId: 'TERM_003', cardTitle: 'Address as "Members"', version: 2 },
      { cardId: 'FACT_002', cardTitle: 'Active User Count', version: 3 },
      { cardId: 'TERM_004', cardTitle: 'Product Name: "NovaShield Pro"', version: 1 },
    ],
  },
  {
    id: 'PASSPORT_111',
    contentId: 'SUB_003',
    contentTitle: 'Blog Post — Product Update Q4',
    status: 'valid',
    approvedBy: 'Sam Okafor',
    approvedAt: '2026-10-11T09:00:00Z',
    findingsResolved: 0,
    findingsDismissed: 0,
    dependencies: [
      { cardId: 'OFFER_015', cardTitle: '15% October Promotion', version: 1 },
      { cardId: 'FACT_001', cardTitle: 'Company Founded Year', version: 1 },
      { cardId: 'FACT_002', cardTitle: 'Active User Count', version: 3 },
      { cardId: 'CLAIM_001', cardTitle: '"Award-Winning" Requires Citation', version: 2 },
      { cardId: 'TERM_004', cardTitle: 'Product Name: "NovaShield Pro"', version: 1 },
    ],
  },
  {
    id: 'PASSPORT_112',
    contentId: 'SUB_001',
    contentTitle: 'October Social Campaign — Instagram Post',
    status: 'revalidation_required',
    approvedBy: 'Sam Okafor',
    approvedAt: '2026-10-15T14:30:00Z',
    findingsResolved: 5,
    findingsDismissed: 1,
    dependencies: [
      { cardId: 'OFFER_014', cardTitle: '20% September Discount', version: 3 },
      { cardId: 'TERM_003', cardTitle: 'Address as "Members"', version: 2 },
      { cardId: 'CLAIM_001', cardTitle: '"Award-Winning" Requires Citation', version: 2 },
    ],
  },
  {
    id: 'PASSPORT_113',
    contentId: 'SUB_005',
    contentTitle: 'LinkedIn Thought Leadership Post',
    status: 'valid',
    approvedBy: 'Sam Okafor',
    approvedAt: '2026-10-18T14:00:00Z',
    findingsResolved: 0,
    findingsDismissed: 0,
    dependencies: [
      { cardId: 'FACT_001', cardTitle: 'Company Founded Year', version: 1 },
      { cardId: 'FACT_002', cardTitle: 'Active User Count', version: 3 },
      { cardId: 'CLAIM_001', cardTitle: '"Award-Winning" Requires Citation', version: 2 },
      { cardId: 'TERM_004', cardTitle: 'Product Name: "NovaShield Pro"', version: 1 },
    ],
  },
];

// ─── Audit Log ───
export const initialAuditLog: AuditEntry[] = [
  { id: 'a1', action: 'Card Created', actor: 'Alex Rivera', target: 'OFFER_015', timestamp: '2026-09-28T09:00:00Z', details: 'Created 15% October Promotion card' },
  { id: 'a2', action: 'Content Submitted', actor: 'Jordan Kim', target: 'SUB_001', timestamp: '2026-10-15T09:30:00Z', details: 'Submitted Instagram post for review' },
  { id: 'a3', action: 'Scan Completed', actor: 'System', target: 'SUB_001', timestamp: '2026-10-15T09:31:00Z', details: '8 findings detected (5 block, 3 warning)' },
  { id: 'a4', action: 'Content Approved', actor: 'Sam Okafor', target: 'SUB_002', timestamp: '2026-10-12T16:00:00Z', details: 'Email newsletter approved with no findings' },
  { id: 'a5', action: 'Passport Issued', actor: 'System', target: 'PASSPORT_110', timestamp: '2026-10-12T16:00:00Z', details: 'Passport issued for Email Newsletter' },
  { id: 'a6', action: 'Content Rejected', actor: 'Sam Okafor', target: 'SUB_004', timestamp: '2026-10-09T10:00:00Z', details: 'Facebook ad rejected — too many violations' },
  { id: 'a7', action: 'Card Updated', actor: 'Alex Rivera', target: 'FACT_002', timestamp: '2026-09-30T16:00:00Z', details: 'Updated user count to 2M+ for Q3 2026' },
  { id: 'a8', action: 'Passport Revoked', actor: 'System', target: 'PASSPORT_112', timestamp: '2026-10-01T00:01:00Z', details: 'Revoked — linked card OFFER_014 expired' },
  { id: 'a9', action: 'Content Approved', actor: 'Sam Okafor', target: 'SUB_003', timestamp: '2026-10-11T09:00:00Z', details: 'Blog post approved — all claims cited' },
  { id: 'a10', action: 'Content Approved', actor: 'Sam Okafor', target: 'SUB_005', timestamp: '2026-10-18T14:00:00Z', details: 'LinkedIn post approved' },
  { id: 'a11', action: 'Content Submitted', actor: 'Jordan Kim', target: 'SUB_006', timestamp: '2026-10-20T13:00:00Z', details: 'Submitted landing page hero copy' },
  { id: 'a12', action: 'Card Expired', actor: 'System', target: 'OFFER_014', timestamp: '2026-10-01T00:00:00Z', details: '20% September Discount auto-expired' },
];

// ─── Governance Insights Data ───
export const insightsData = {
  topBrokenRules: [
    { cardId: 'TERM_003', title: 'Address as "Members"', violations: 23, trend: 'down' as const },
    { cardId: 'OFFER_014', title: '20% September Discount (expired)', violations: 18, trend: 'up' as const },
    { cardId: 'CLAIM_001', title: '"Award-Winning" Requires Citation', violations: 14, trend: 'stable' as const },
    { cardId: 'TONE_001', title: 'Brand Voice Profile', violations: 11, trend: 'down' as const },
    { cardId: 'FACT_002', title: 'Active User Count', violations: 9, trend: 'up' as const },
  ],
  weeklyErrors: [
    { week: 'Sep 2', count: 34 },
    { week: 'Sep 9', count: 28 },
    { week: 'Sep 16', count: 31 },
    { week: 'Sep 23', count: 22 },
    { week: 'Sep 30', count: 38 },
    { week: 'Oct 7', count: 25 },
    { week: 'Oct 14', count: 19 },
    { week: 'Oct 21', count: 14 },
  ],
  dismissalRates: [
    { cardId: 'TONE_001', title: 'Brand Voice Profile', dismissRate: 42, note: 'High dismissal — rule may be unclear' },
    { cardId: 'ACC_002', title: 'Image Accessibility Rules', dismissRate: 31, note: 'Creators unsure about alt text format' },
    { cardId: 'TERM_003', title: 'Address as "Members"', dismissRate: 8, note: 'Well-understood rule' },
  ],
  detectionSplit: {
    ruleDetected: 67,
    aiDetected: 33,
  },
  contentStats: {
    totalSubmissions: 47,
    approved: 28,
    rejected: 8,
    inReview: 6,
    draft: 5,
    totalFindings: 142,
    findingsResolved: 118,
    findingsDismissed: 24,
    avgReviewTimeHours: 2.3,
  },
};
