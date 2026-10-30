import { test, describe } from 'node:test';
import assert from 'node:assert';
import { reviewClient, computeCanonicalSha256 } from '../lib/api/reviewClient.ts';

describe('Screenshot-Specific Image Upload → Review Gate → Content Passport Workflow Tests', () => {

  // Test 1: Clear image with readable text: OCR succeeds and text checks run.
  test('1. Clear image with readable text: OCR succeeds and text checks run', () => {
    const item = reviewClient.addDraftToQueue({
      title: 'Winter Campaign Asset',
      content: 'Winter travel packages are available for members through December 31.',
      blockersCount: 0,
      warningsCount: 0,
      findings: [],
      asset_status: 'uploaded',
      preview_status: 'ready',
      ocr_status: 'completed',
      ocr_text: 'Winter travel packages are available for members through December 31.',
      ocr_confidence: 0.94,
      visual_checks_status: 'ready',
      text_checks_status: 'checked_no_findings',
      review_status: 'ready_for_review',
      approval_eligible: true,
      passport_eligible: true,
      asset_filename: 'clear_offer.png',
      detected_mime_type: 'image/png',
    });

    assert.strictEqual(item.ocr_status, 'completed');
    assert.strictEqual(item.text_checks_status, 'checked_no_findings');
    assert.strictEqual(item.approval_eligible, true);
    assert.strictEqual(item.passport_eligible, true);
    assert.strictEqual(item.blockersCount, 0);
  });

  // Test 2: Image with no text: status is "No readable text detected"; visual-only review is offered.
  test('2. Image with no text: status is "no_text"; visual-only review is offered and normal approval blocked', () => {
    const item = reviewClient.addDraftToQueue({
      title: 'Brand Logo Graphic',
      content: '[Visual Asset: logo.png] — Readable copy not extracted.',
      blockersCount: 0,
      warningsCount: 0,
      findings: [],
      asset_status: 'uploaded',
      preview_status: 'ready',
      ocr_status: 'no_text',
      ocr_text: null,
      ocr_confidence: null,
      visual_checks_status: 'ready',
      text_checks_status: 'not_run',
      is_visual_only: true,
      asset_filename: 'logo.png',
      detected_mime_type: 'image/png',
    });

    assert.strictEqual(item.ocr_status, 'no_text');
    assert.strictEqual(item.text_checks_status, 'not_run');
    assert.strictEqual(item.is_visual_only, true);
    assert.strictEqual(item.approval_eligible, false, 'Approval must be disabled for visual-only draft until reviewer records reason');
  });

  // Test 3: Blurry image: status is "Text extraction failed"; approval is blocked.
  test('3. Blurry image: status is "Text extraction failed"; approval is blocked', () => {
    const item = reviewClient.addDraftToQueue({
      title: 'Blurry Asset Upload',
      content: '',
      blockersCount: 0,
      warningsCount: 0,
      findings: [],
      asset_status: 'uploaded',
      preview_status: 'ready',
      ocr_status: 'failed',
      ocr_text: null,
      ocr_confidence: null,
      visual_checks_status: 'ready',
      text_checks_status: 'not_run',
      asset_filename: 'blurry_campaign_banner.jpg',
      detected_mime_type: 'image/jpeg',
    });

    assert.strictEqual(item.ocr_status, 'failed');
    assert.strictEqual(item.text_checks_status, 'not_run');
    assert.strictEqual(item.review_status, 'manual_input_required');
    assert.strictEqual(item.approval_eligible, false, 'Approval must be blocked when extraction fails');
    assert.strictEqual(item.passport_eligible, false, 'Passport cannot be created when approval is blocked');
  });

  // Test 4: Corrupted OCR output containing replacement characters: output is rejected and not analysed.
  test('4. Corrupted OCR output containing replacement characters: rejected and not analysed', async () => {
    // Attempting to submit approval for a corrupted draft must be blocked
    const corruptedDraft = reviewClient.addDraftToQueue({
      title: 'Corrupted OCR Banner',
      content: 'SAMSUNG WZNO = Galaxy Z Fold8 \uFFFD\uFFFD special promo',
      blockersCount: 0,
      warningsCount: 0,
      findings: [],
      asset_status: 'uploaded',
      preview_status: 'ready',
      ocr_status: 'corrupted',
      ocr_text: null, // nulled out
      ocr_confidence: null,
      visual_checks_status: 'ready',
      text_checks_status: 'not_run',
      approval_eligible: false,
      passport_eligible: false,
    });

    assert.strictEqual(corruptedDraft.approval_eligible, false);

    // Reviewer approval attempt must be blocked with error
    const result = await reviewClient.submitReview(
      {
        draft_id: corruptedDraft.draftId,
        scan_id: corruptedDraft.scanId,
        decision: 'approved',
      },
      'reviewer',
      'rev_101',
      'Sarah Chen'
    );

    assert.strictEqual(result.success, false);
    assert.strictEqual(result.status, 422);
    assert.ok(result.error?.includes('Approval Blocked'), 'Must reject approval of corrupted unverified OCR draft');
  });

  // Test 5: Image with valid text but no findings: status is "Checked — no findings", not merely "0 blockers".
  test('5. Image with valid text but no findings: status is "Checked — no findings", eligible for approval', () => {
    const item = reviewClient.addDraftToQueue({
      title: 'Compliant Asset',
      content: 'Our Members can access standard pricing today!',
      blockersCount: 0,
      warningsCount: 0,
      findings: [],
      asset_status: 'uploaded',
      preview_status: 'ready',
      ocr_status: 'completed',
      ocr_text: 'Our Members can access standard pricing today!',
      ocr_confidence: 0.95,
      visual_checks_status: 'ready',
      text_checks_status: 'checked_no_findings',
      review_status: 'ready_for_review',
      approval_eligible: true,
      passport_eligible: true,
    });

    assert.strictEqual(item.text_checks_status, 'checked_no_findings');
    assert.strictEqual(item.blockersCount, 0);
    assert.strictEqual(item.approval_eligible, true);
  });

  // Test 6: Reviewer approves a visual-only asset: Passport records the limitation.
  test('6. Reviewer approves a visual-only asset: Passport records the limitation', async () => {
    const visualDraft = reviewClient.addDraftToQueue({
      title: 'Display Ad Graphic (Visual Only)',
      content: '[Visual Asset: banner_16x9.jpg] — Readable copy not available.',
      blockersCount: 0,
      warningsCount: 0,
      findings: [],
      asset_status: 'uploaded',
      preview_status: 'ready',
      ocr_status: 'failed',
      ocr_text: null,
      ocr_confidence: null,
      visual_checks_status: 'ready',
      text_checks_status: 'not_run',
      is_visual_only: true,
      asset_filename: '33914_Z_Series_Diwali_Banner_16x9.jpg',
      original_filename: '33914_Z_Series_Diwali_Banner_16x9.jpg',
      detected_mime_type: 'image/jpeg',
    });

    // 6a. Attempting approval without a reason fails
    const failAttempt = await reviewClient.submitReview(
      {
        draft_id: visualDraft.draftId,
        scan_id: visualDraft.scanId,
        decision: 'approved',
        approval_type: 'visual_only',
        visual_override_reason: '', // Empty reason
      },
      'reviewer',
      'rev_101',
      'Sarah Chen'
    );
    assert.strictEqual(failAttempt.success, false, 'Visual-only approval must require a documented reason');

    // 6b. Approval with documented reason succeeds and records limitation
    const successResult = await reviewClient.submitReview(
      {
        draft_id: visualDraft.draftId,
        scan_id: visualDraft.scanId,
        decision: 'approved',
        comment: 'Visual brand elements and logo placement verified against design standards. Copy verified in ticket #402.',
        approval_type: 'visual_only',
        visual_override_reason: 'Visual brand elements verified. Copy verified in ticket #402.',
      },
      'reviewer',
      'rev_101',
      'Sarah Chen'
    );

    assert.strictEqual(successResult.success, true);
    assert.ok(successResult.data?.passport_id);
    assert.strictEqual(successResult.data?.approval_type, 'visual_only');
    assert.ok(successResult.data?.decision_limitations?.includes('Visual review only'));

    // Verify minted passport
    const passport = await reviewClient.getPassport(successResult.data.passport_id);
    assert.ok(passport);
    assert.strictEqual(passport.metadata_snapshot.approval_type, 'visual_only');
    assert.strictEqual(passport.metadata_snapshot.text_review_status, 'not_completed');
    assert.strictEqual(passport.metadata_snapshot.ocr_status, 'failed');
    assert.strictEqual(passport.metadata_snapshot.reviewer_name, 'Sarah Chen');
    assert.strictEqual(passport.metadata_snapshot.review_stats.approved_with_override, 1);
    assert.strictEqual(passport.hash_verified, true);
  });

  // Test 7: Failed OCR followed by manual copy: text checks run only after manual copy is entered.
  test('7. Failed OCR followed by manual copy: text checks run only after manual copy is entered', () => {
    // 7a. Item created with failed OCR
    const failedItem = reviewClient.addDraftToQueue({
      title: 'Billboard Ad Draft',
      content: '',
      blockersCount: 0,
      warningsCount: 0,
      findings: [],
      asset_status: 'uploaded',
      preview_status: 'ready',
      ocr_status: 'failed',
      text_checks_status: 'not_run',
      approval_eligible: false,
    });

    assert.strictEqual(failedItem.approval_eligible, false);
    assert.strictEqual(failedItem.text_checks_status, 'not_run');

    // 7b. Creator/reviewer enters manual copy containing violation ("customers")
    const updatedWithViolation = reviewClient.updateManualCopy(
      failedItem.draftId,
      'Welcome to all our customers!'
    );

    assert.ok(updatedWithViolation);
    assert.strictEqual(updatedWithViolation.text_checks_status, 'findings_flagged');
    assert.strictEqual(updatedWithViolation.blockersCount, 1, 'Should flag "customers" terminology blocker');
    assert.strictEqual(updatedWithViolation.approval_eligible, false, 'Cannot approve with active blocker');

    // 7c. Creator/reviewer updates copy to compliant wording ("Members")
    const updatedCompliant = reviewClient.updateManualCopy(
      failedItem.draftId,
      'Welcome to all our Members!'
    );

    assert.ok(updatedCompliant);
    assert.strictEqual(updatedCompliant.text_checks_status, 'checked_no_findings');
    assert.strictEqual(updatedCompliant.blockersCount, 0);
    assert.strictEqual(updatedCompliant.approval_eligible, true, 'Draft is now cleared for approval');
  });

  // Test 8: Passport content matches the exact approved reviewed version.
  test('8. Passport content matches the exact approved reviewed version', async () => {
    const verifiedCopy = 'Exclusive tier privileges are now available for all verified Members.';
    const draft = reviewClient.addDraftToQueue({
      title: 'Verified Autumn Campaign',
      content: verifiedCopy,
      blockersCount: 0,
      warningsCount: 0,
      findings: [],
      asset_status: 'uploaded',
      preview_status: 'ready',
      ocr_status: 'completed',
      ocr_text: verifiedCopy,
      ocr_confidence: 0.96,
      text_checks_status: 'checked_no_findings',
      approval_eligible: true,
      passport_eligible: true,
    });

    const reviewRes = await reviewClient.submitReview(
      {
        draft_id: draft.draftId,
        scan_id: draft.scanId,
        decision: 'approved',
        comment: 'Compliant copy approved for multi-channel publishing.',
      },
      'reviewer',
      'rev_101',
      'Sarah Chen'
    );

    assert.strictEqual(reviewRes.success, true);
    assert.ok(reviewRes.data?.passport_id);

    const passport = await reviewClient.getPassport(reviewRes.data.passport_id);
    assert.ok(passport);
    assert.strictEqual(passport.metadata_snapshot.draft_content, verifiedCopy, 'Passport snapshot must match approved content exactly');
    assert.strictEqual(passport.metadata_snapshot.reviewer_name, 'Sarah Chen');

    // Check canonical hash verification
    const recomputed = await computeCanonicalSha256(passport.metadata_snapshot);
    assert.strictEqual(passport.passport_hash, recomputed, 'Cryptographic hash must match canonical snapshot');
    assert.strictEqual(passport.hash_verified, true);
  });
});
