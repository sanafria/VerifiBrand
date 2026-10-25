import { test, describe } from 'node:test';
import assert from 'node:assert';
import { policyClient } from '../lib/api/policyClient.ts';
import { INITIAL_POLICY_CARDS, INITIAL_BRAND_PROFILES } from '../lib/mockData.ts';

describe('Policy Library & Brand Passport Tests', () => {

  test('Seed policies match backend/tests/conftest.py archetypes', () => {
    assert.strictEqual(INITIAL_POLICY_CARDS.length >= 4, true, 'Must have at least 4 seed policies');

    const termPolicy = INITIAL_POLICY_CARDS.find(p => p.id === 'pol_term_001');
    assert.ok(termPolicy, 'pol_term_001 must exist');
    assert.strictEqual(termPolicy.version, '1.0');
    assert.strictEqual(termPolicy.category, 'terminology');
    assert.strictEqual(termPolicy.status, 'approved');

    const offerPolicy = INITIAL_POLICY_CARDS.find(p => p.id === 'pol_offer_002');
    assert.ok(offerPolicy, 'pol_offer_002 must exist');
    assert.strictEqual(offerPolicy.version, '2.1');
    assert.strictEqual(offerPolicy.category, 'offer_validity');

    const numPolicy = INITIAL_POLICY_CARDS.find(p => p.id === 'pol_num_003');
    assert.ok(numPolicy, 'pol_num_003 must exist');
    assert.strictEqual(numPolicy.category, 'numerical');

    const claimPolicy = INITIAL_POLICY_CARDS.find(p => p.id === 'pol_claim_004');
    assert.ok(claimPolicy, 'pol_claim_004 must exist');
    assert.strictEqual(claimPolicy.category, 'claims');
  });

  test('PolicyClient retrieves all policies and supports category filtering', async () => {
    policyClient.resetToDefault();
    const all = await policyClient.getPolicies();
    assert.strictEqual(all.total >= 4, true);

    const termOnly = await policyClient.getPolicies({ category: 'terminology' });
    assert.strictEqual(termOnly.policies.every(p => p.category === 'terminology'), true);
    assert.ok(termOnly.total >= 1);

    const offerOnly = await policyClient.getPolicies({ category: 'offer_validity' });
    assert.strictEqual(offerOnly.policies.every(p => p.category === 'offer_validity'), true);

    const numOnly = await policyClient.getPolicies({ category: 'numerical' });
    assert.strictEqual(numOnly.policies.every(p => p.category === 'numerical'), true);
  });

  test('PolicyClient search filters accurately by keyword and prohibited term', async () => {
    policyClient.resetToDefault();

    const searchCustomers = await policyClient.getPolicies({ searchQuery: 'Customers' });
    assert.ok(searchCustomers.total >= 1);
    assert.strictEqual(searchCustomers.policies[0].id, 'pol_term_001');

    const searchPoints = await policyClient.getPolicies({ searchQuery: '500 points' });
    assert.ok(searchPoints.total >= 1);
    assert.strictEqual(searchPoints.policies[0].id, 'pol_num_003');

    const searchNonexistent = await policyClient.getPolicies({ searchQuery: 'UnmatchedKeywordXYZ123' });
    assert.strictEqual(searchNonexistent.total, 0);
  });

  test('Core Tenet ("No receipt, no flag"): Quote verification succeeds on verbatim match', () => {
    const content = "The brand prohibits the term 'Customers' and requires the term 'Members'. Always refer to account holders as members.";
    const validQuote = "The brand prohibits the term 'Customers' and requires the term 'Members'.";

    const result = policyClient.verifyQuoteIntegrity(content, validQuote);
    assert.strictEqual(result.isValid, true);
    assert.strictEqual(result.error, undefined);
  });

  test('Core Tenet ("No receipt, no flag"): Quote verification rejects fabricated quotes', () => {
    const content = "The brand prohibits the term 'Customers' and requires the term 'Members'.";
    const fabricatedQuote = "The brand completely allows the term 'Customers' everywhere.";

    const result = policyClient.verifyQuoteIntegrity(content, fabricatedQuote);
    assert.strictEqual(result.isValid, false);
    assert.match(result.error || '', /does not exist as an exact substring/);
  });

  test('Policy creation validates unique IDs and quote integrity', async () => {
    policyClient.resetToDefault();

    // 1. Should fail on duplicate ID
    await assert.rejects(
      async () => {
        await policyClient.createPolicy({
          id: 'pol_term_001', // existing ID
          version: '1.0',
          title: 'Duplicate Policy',
          category: 'terminology',
          content: 'Some valid text',
          rules: [],
          metadata: { quote: 'Some valid text' }
        });
      },
      /already exists/
    );

    // 2. Should fail on quote mismatch
    await assert.rejects(
      async () => {
        await policyClient.createPolicy({
          id: 'pol_test_new_999',
          version: '1.0',
          title: 'Tampered Quote Policy',
          category: 'terminology',
          content: 'Actual approved brand rule.',
          rules: [],
          metadata: { quote: 'Fabricated quote that is not in content.' }
        });
      },
      /does not exist as an exact substring/
    );

    // 3. Should succeed with verified quote
    const created = await policyClient.createPolicy({
      id: 'pol_test_valid_888',
      version: '1.0',
      title: 'Valid New Policy',
      category: 'terminology',
      content: 'Standard approved legal text for patient records.',
      rules: [{ type: 'terminology', quote: 'Standard approved legal text' }],
      metadata: { quote: 'Standard approved legal text' }
    });

    assert.strictEqual(created.id, 'pol_test_valid_888');
    assert.strictEqual(created.status, 'approved');

    const fetched = await policyClient.getPolicyById('pol_test_valid_888');
    assert.ok(fetched);
    assert.strictEqual(fetched.title, 'Valid New Policy');
  });

  test('Policy archival updates status to archived', async () => {
    policyClient.resetToDefault();

    const archived = await policyClient.archivePolicy('pol_term_001');
    assert.strictEqual(archived.status, 'archived');

    const approvedOnly = await policyClient.getPolicies({ status: 'approved' });
    assert.strictEqual(approvedOnly.policies.some(p => p.id === 'pol_term_001'), false);

    const archivedOnly = await policyClient.getPolicies({ status: 'archived' });
    assert.strictEqual(archivedOnly.policies.some(p => p.id === 'pol_term_001'), true);
  });

  test('Brand Passport profiles include governance scores, voice pillars, and colors', async () => {
    const brands = await policyClient.getBrandProfiles();
    assert.strictEqual(brands.length >= 1, true);

    const apex = brands[0];
    assert.strictEqual(apex.name, 'Apex Health Technologies');
    assert.strictEqual(apex.governanceScore, 98);
    assert.ok(apex.voicePillars.length >= 2);
    assert.ok(apex.colors.length >= 3);
    assert.strictEqual(apex.logoGuidelines.minClearSpacePx >= 20, true);
  });

  test('Policy serialization matches backend ScanDraftRequest contract', async () => {
    policyClient.resetToDefault();
    const { policies } = await policyClient.getPolicies();

    // Verify all policies can be JSON serialized without errors
    const serialized = JSON.parse(JSON.stringify(policies));
    assert.strictEqual(Array.isArray(serialized), true);

    serialized.forEach((p: Record<string, unknown>) => {
      assert.ok(typeof p.id === 'string');
      assert.ok(typeof p.version === 'string');
      assert.ok(typeof p.content === 'string');
      assert.ok(Array.isArray(p.rules));
      assert.ok(typeof p.metadata === 'object');
    });
  });

  test('getApprovedPoliciesForScan exports ONLY approved policies formatted for backend scan', async () => {
    policyClient.resetToDefault();

    // Archive one policy
    await policyClient.archivePolicy('pol_term_001');

    // Call dedicated scan export helper
    const scanCards = await policyClient.getApprovedPoliciesForScan();

    // pol_term_001 must NOT be in scanCards
    assert.strictEqual(scanCards.some(c => c.id === 'pol_term_001'), false, 'Archived policy must be excluded from scan payload');

    // All returned cards must have required fields
    scanCards.forEach(c => {
      assert.ok(typeof c.id === 'string' && c.id.length > 0);
      assert.ok(typeof c.version === 'string' && c.version.length > 0);
      assert.ok(typeof c.content === 'string' && c.content.length > 0);
      assert.ok(Array.isArray(c.rules));
      assert.ok(typeof c.metadata === 'object');
    });
  });

});
