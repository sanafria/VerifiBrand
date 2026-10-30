'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import {
  Shield, CheckCircle2, XCircle, AlertTriangle,
  Lock, ArrowRight, Award, MessageSquare, UserCheck,
  FileText, Clock, RefreshCw, Zap, Check, Eye, HelpCircle,
  Hash, ExternalLink, ChevronRight, AlertOctagon, Edit3, Upload, X
} from 'lucide-react';
import {
  reviewClient,
  ReviewQueueItem,
  UserRole,
  ReviewResponse,
  FindingSummaryItem
} from '@/lib/api/reviewClient';
import styles from './page.module.css';

function ReviewGateContent() {
  const searchParams = useSearchParams();
  const queryDraftId = searchParams.get('draftId');

  const [queue, setQueue] = useState<ReviewQueueItem[]>([]);
  const [selectedId, setSelectedId] = useState<string>('');
  const [userRole, setUserRole] = useState<UserRole>('reviewer');
  const [reviewerName, setReviewerName] = useState('Sarah Chen (Compliance Officer)');
  const [reviewerId, setReviewerId] = useState('rev_101');
  const [reviewComment, setReviewComment] = useState('All checks verified against active policy cards. Approved for digital release.');
  const [filterStatus, setFilterStatus] = useState<'all' | 'pending' | 'approved' | 'rejected'>('all');
  
  // Interaction states
  const [submitting, setSubmitting] = useState(false);
  const [errorMessage, setErrorMessage] = useState<string | null>(null);
  const [errorStatus, setErrorStatus] = useState<number | null>(null);
  const [successResponse, setSuccessResponse] = useState<ReviewResponse | null>(null);
  const [backendConnected, setBackendConnected] = useState<boolean | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [showDemoControls, setShowDemoControls] = useState(false);

  // Manual Copy Modal & Visual Override State
  const [showManualCopyModal, setShowManualCopyModal] = useState(false);
  const [manualCopyInput, setManualCopyInput] = useState('');
  const [showVisualOverrideModal, setShowVisualOverrideModal] = useState(false);
  const [visualReasonInput, setVisualReasonInput] = useState('');

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Load review queue from reviewClient & check backend connection
  useEffect(() => {
    const items = reviewClient.getQueue();
    setQueue(items);

    if (queryDraftId) {
      const match = items.find(q => q.draftId === queryDraftId || q.id === queryDraftId);
      if (match) {
        setSelectedId(match.id);
      } else if (items.length > 0) {
        setSelectedId(items[0].id);
      }
    } else if (items.length > 0) {
      setSelectedId(items[0].id);
    }

    // Ping FastAPI health
    const apiBase = process.env.NEXT_PUBLIC_API_URL !== undefined ? process.env.NEXT_PUBLIC_API_URL : (typeof window !== 'undefined' ? '' : 'http://127.0.0.1:8000');
    fetch(`${apiBase}/health`, { method: 'GET' })
      .then(res => setBackendConnected(res.ok))
      .catch(() => setBackendConnected(false));
  }, [queryDraftId]);

  const selectedItem = queue.find(q => q.id === selectedId) || queue[0];

  const filteredQueue = queue.filter(item => {
    if (filterStatus === 'all') return true;
    return item.status === filterStatus;
  });

  // Strict state checks
  const isOcrBlocked = Boolean(
    selectedItem && (
      selectedItem.ocr_status === 'failed' ||
      selectedItem.ocr_status === 'corrupted' ||
      (selectedItem.text_checks_status === 'not_run' && !selectedItem.content)
    )
  );

  const isVisualOnly = Boolean(
    selectedItem && (
      selectedItem.is_visual_only ||
      selectedItem.review_status === 'visual_only'
    )
  );

  const isCleanChecked = Boolean(
    selectedItem && (
      selectedItem.text_checks_status === 'checked_no_findings' ||
      (!isOcrBlocked && !isVisualOnly && selectedItem.blockersCount === 0 && selectedItem.findings?.length === 0 && !!selectedItem.content)
    )
  );

  // Role switch handler
  const handleRoleChange = (newRole: UserRole) => {
    setUserRole(newRole);
    setErrorMessage(null);
    setErrorStatus(null);
    if (newRole === 'creator') {
      setReviewerName('Alex Kim (Marketing Creator)');
      setReviewerId('creator_alex');
      showToast('Switched to Creator role. Self-approval will trigger HTTP 403 Forbidden.');
    } else if (newRole === 'reviewer') {
      setReviewerName('Sarah Chen (Compliance Officer)');
      setReviewerId('rev_101');
      showToast('Switched to Reviewer role. Authorized to approve & mint passports.');
    } else {
      setReviewerName('Jordan Blake (System Admin)');
      setReviewerId('admin_jordan');
      showToast('Switched to Admin role. Full authorization granted.');
    }
  };

  // Preset 1: Quick-Load Act 4 Demo Snippet B (Compliant)
  const handleLoadAct4Preset = () => {
    const match = queue.find(q => q.title.includes('Snippet B') || (q.blockersCount === 0 && q.approval_eligible));
    if (match) {
      setSelectedId(match.id);
    }
    handleRoleChange('reviewer');
    setReviewComment('Approved after verification against active policy cards.');
    setErrorMessage(null);
    setErrorStatus(null);
    setSuccessResponse(null);
    showToast('Loaded Act 4 Demo State (Compliant Snippet B + Reviewer Role)');
  };

  // Preset 2: Trigger 403 Forbidden Governance Gate (AT-018)
  const handleLoad403Demo = () => {
    const match = queue.find(q => q.title.includes('Snippet A') || q.blockersCount > 0);
    if (match) {
      setSelectedId(match.id);
    }
    handleRoleChange('creator');
    setErrorMessage(null);
    setErrorStatus(null);
    setSuccessResponse(null);
    showToast('Loaded AT-018 Governance Test: Creator Role Active');
  };

  // Submit Manual Copy
  const handleSaveManualCopy = () => {
    if (!selectedItem || !manualCopyInput.trim()) {
      showToast('Please enter campaign copy before saving.');
      return;
    }

    const updated = reviewClient.updateManualCopy(selectedItem.draftId, manualCopyInput.trim());
    if (updated) {
      setQueue(reviewClient.getQueue());
      setShowManualCopyModal(false);
      setManualCopyInput('');
      setErrorMessage(null);
      setErrorStatus(null);
      showToast('Manual copy saved & scanned against active brand policies.');
    }
  };

  // Handle Review Approval (Calls POST /api/reviews)
  const handleApprove = async () => {
    if (!selectedItem) return;
    setErrorMessage(null);
    setErrorStatus(null);

    // Rule: Block approval if OCR failed and no manual copy provided
    if (isOcrBlocked && !isVisualOnly) {
      setErrorMessage('Review blocked: Readable text required. Text findings have not been evaluated. Enter copy manually or request a clearer upload before approving.');
      setErrorStatus(422);
      return;
    }

    // Rule: Visual-only approval requires documented justification reason
    if (isVisualOnly) {
      setShowVisualOverrideModal(true);
      return;
    }

    setSubmitting(true);

    try {
      // Blocker gate check (AT-010)
      if (selectedItem.blockersCount > 0) {
        setErrorMessage('Governance Violation: Cannot approve draft with active blocker findings. Resolve all blocker citations in the Scan Workspace first.');
        setErrorStatus(422);
        setSubmitting(false);
        return;
      }

      const result = await reviewClient.submitReview(
        {
          draft_id: selectedItem.draftId,
          scan_id: selectedItem.scanId,
          decision: 'approved',
          comment: reviewComment || 'Approved for publication across digital channels.',
        },
        userRole,
        reviewerId,
        reviewerName
      );

      if (result.success && result.data) {
        setSuccessResponse(result.data);
        setQueue(reviewClient.getQueue());
        showToast('Official Content Passport Minted Successfully!');
      } else {
        setErrorMessage(result.error || 'Failed to submit review.');
        setErrorStatus(result.status || 400);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Unexpected error submitting review.');
      setErrorStatus(500);
    } finally {
      setSubmitting(false);
    }
  };

  // Handle Visual-Only Reviewer Approval with Justification
  const handleConfirmVisualApproval = async () => {
    if (!selectedItem) return;
    if (!visualReasonInput.trim()) {
      setErrorMessage('Reviewer justification is required to record a visual-only approval.');
      setErrorStatus(422);
      return;
    }

    setSubmitting(true);
    setErrorMessage(null);
    setErrorStatus(null);

    try {
      const result = await reviewClient.submitReview(
        {
          draft_id: selectedItem.draftId,
          scan_id: selectedItem.scanId,
          decision: 'approved',
          comment: visualReasonInput.trim(),
          approval_type: 'visual_only',
          visual_override_reason: visualReasonInput.trim(),
        },
        userRole,
        reviewerId,
        reviewerName
      );

      if (result.success && result.data) {
        setSuccessResponse(result.data);
        setQueue(reviewClient.getQueue());
        setShowVisualOverrideModal(false);
        setVisualReasonInput('');
        showToast('Visual-only Content Passport Minted (Documented Limitation Recorded)');
      } else {
        setErrorMessage(result.error || 'Failed to record visual approval.');
        setErrorStatus(result.status || 400);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Error recording visual approval.');
      setErrorStatus(500);
    } finally {
      setSubmitting(false);
    }
  };

  // Handle Review Rejection
  const handleReject = async (customReason?: string) => {
    if (!selectedItem) return;
    setErrorMessage(null);
    setErrorStatus(null);
    setSubmitting(true);

    const commentToLog = customReason || reviewComment || 'Draft rejected. Revise prohibited terminology and expired promotions before resubmitting.';

    try {
      const result = await reviewClient.submitReview(
        {
          draft_id: selectedItem.draftId,
          scan_id: selectedItem.scanId,
          decision: 'rejected',
          comment: commentToLog,
        },
        userRole,
        reviewerId,
        reviewerName
      );

      if (result.success && result.data) {
        setQueue(reviewClient.getQueue());
        setSuccessResponse(null);
        showToast('Draft marked as Rejected. Action requested from creator.');
      } else {
        setErrorMessage(result.error || 'Failed to submit rejection.');
        setErrorStatus(result.status || 400);
      }
    } catch (err: any) {
      setErrorMessage(err.message || 'Unexpected error submitting rejection.');
      setErrorStatus(500);
    } finally {
      setSubmitting(false);
    }
  };

  return (
    <div className={styles.container}>
      {/* Toast Notification */}
      {toastMessage && (
        <div className={styles.toast}>
          <Zap size={15} color="var(--brand-gold)" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Manual Copy Entry Modal */}
      {showManualCopyModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0,0,0,0.75)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: 20
        }}>
          <div style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-light)',
            borderRadius: 12,
            padding: 24,
            maxWidth: 580,
            width: '100%',
            boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
            display: 'flex',
            flexDirection: 'column',
            gap: 16
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Edit3 size={18} color="var(--brand-navy)" />
                <span style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                  Enter Campaign Copy Manually
                </span>
              </div>
              <button
                type="button"
                onClick={() => setShowManualCopyModal(false)}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
              >
                <X size={18} />
              </button>
            </div>

            <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', lineHeight: 1.5, margin: 0 }}>
              OCR could not extract readable copy from the asset. Enter the verified campaign copy below to run text-dependent compliance checks and clear this draft for approval.
            </p>

            <textarea
              value={manualCopyInput}
              onChange={e => setManualCopyInput(e.target.value)}
              placeholder="Paste or type verified marketing copy here..."
              rows={5}
              style={{
                width: '100%',
                padding: '12px 14px',
                background: '#FFFFFF',
                border: '1px solid var(--border-light)',
                borderRadius: 8,
                fontSize: '0.88rem',
                fontFamily: 'inherit',
                color: 'var(--text-primary)',
                outline: 'none',
              }}
            />

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button
                type="button"
                onClick={() => setShowManualCopyModal(false)}
                style={{
                  background: 'transparent',
                  border: '1px solid var(--border-subtle)',
                  padding: '8px 16px',
                  borderRadius: 6,
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleSaveManualCopy}
                style={{
                  background: 'var(--brand-forest)',
                  border: 'none',
                  padding: '8px 18px',
                  borderRadius: 6,
                  fontSize: '0.82rem',
                  fontWeight: 700,
                  color: '#FFFFFF',
                  cursor: 'pointer',
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6
                }}
              >
                <Check size={14} />
                <span>Save Copy &amp; Run Checks</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Visual-Only Override Reason Modal */}
      {showVisualOverrideModal && (
        <div style={{
          position: 'fixed',
          inset: 0,
          background: 'rgba(0,0,0,0.75)',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          zIndex: 1000,
          padding: 20
        }}>
          <div style={{
            background: 'var(--bg-card)',
            border: '1px solid var(--border-light)',
            borderRadius: 12,
            padding: 24,
            maxWidth: 580,
            width: '100%',
            boxShadow: '0 20px 40px rgba(0,0,0,0.5)',
            display: 'flex',
            flexDirection: 'column',
            gap: 16
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
              <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                <Eye size={18} color="#d97706" />
                <span style={{ fontSize: '1.05rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                  Accept Visual-Only Review
                </span>
              </div>
              <button
                type="button"
                onClick={() => setShowVisualOverrideModal(false)}
                style={{ background: 'transparent', border: 'none', cursor: 'pointer', color: 'var(--text-muted)' }}
              >
                <X size={18} />
              </button>
            </div>

            <div style={{
              background: 'rgba(245, 158, 11, 0.08)',
              border: '1px solid rgba(245, 158, 11, 0.3)',
              borderRadius: 6,
              padding: '10px 14px',
              fontSize: '0.78rem',
              color: 'var(--text-secondary)',
              lineHeight: 1.5
            }}>
              <strong>Governance Rule:</strong> The Content Passport will explicitly record that textual review was NOT completed due to unreadable OCR. A mandatory reviewer reason must be provided for audit compliance.
            </div>

            <div>
              <label style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)', display: 'block', marginBottom: 6 }}>
                Reviewer Documented Justification (Required):
              </label>
              <textarea
                value={visualReasonInput}
                onChange={e => setVisualReasonInput(e.target.value)}
                placeholder="E.g., Approved visual logo clear space and brand palette only. Campaign copy cleared under separate legal clearance ticket #842."
                rows={4}
                style={{
                  width: '100%',
                  padding: '12px 14px',
                  background: '#FFFFFF',
                  border: '1px solid var(--border-light)',
                  borderRadius: 8,
                  fontSize: '0.86rem',
                  fontFamily: 'inherit',
                  color: 'var(--text-primary)',
                  outline: 'none',
                }}
              />
            </div>

            <div style={{ display: 'flex', justifyContent: 'flex-end', gap: 10 }}>
              <button
                type="button"
                onClick={() => setShowVisualOverrideModal(false)}
                style={{
                  background: 'transparent',
                  border: '1px solid var(--border-subtle)',
                  padding: '8px 16px',
                  borderRadius: 6,
                  fontSize: '0.82rem',
                  fontWeight: 600,
                  color: 'var(--text-secondary)',
                  cursor: 'pointer'
                }}
              >
                Cancel
              </button>
              <button
                type="button"
                onClick={handleConfirmVisualApproval}
                disabled={submitting || !visualReasonInput.trim()}
                style={{
                  background: '#d97706',
                  border: 'none',
                  padding: '8px 18px',
                  borderRadius: 6,
                  fontSize: '0.82rem',
                  fontWeight: 700,
                  color: '#FFFFFF',
                  cursor: (!visualReasonInput.trim() || submitting) ? 'not-allowed' : 'pointer',
                  opacity: (!visualReasonInput.trim() || submitting) ? 0.5 : 1,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6
                }}
              >
                <CheckCircle2 size={14} />
                <span>{submitting ? 'Recording Human Sign-off...' : 'Approve with Documented Limitation'}</span>
              </button>
            </div>
          </div>
        </div>
      )}

      {/* Header Banner */}
      <div className={styles.banner}>
        <div className={styles.headerTop}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <span className={styles.teamBadge}>
              <Shield size={14} /> Review Gate &bull; Authorised Reviewer Approval
            </span>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
            <button
              type="button"
              onClick={() => setShowDemoControls(!showDemoControls)}
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                padding: '5px 12px',
                borderRadius: 6,
                background: showDemoControls ? 'var(--brand-navy)' : 'rgba(30, 41, 59, 0.08)',
                color: showDemoControls ? '#FFFFFF' : 'var(--brand-navy)',
                fontSize: '0.76rem',
                fontWeight: 700,
                border: '1px solid var(--border-subtle)',
                cursor: 'pointer'
              }}
            >
              <Zap size={13} color={showDemoControls ? '#F59E0B' : 'currentColor'} />
              <span>{showDemoControls ? 'Hide Testing Controls' : 'Demo & Testing Controls'}</span>
            </button>
            <Link
              href="/passports"
              className={styles.viewPassportsLink}
            >
              <Award size={14} /> View Issued Passports
            </Link>
          </div>
        </div>

        <h1 className={styles.title}>Review content before publication</h1>
        <p className={styles.desc}>
          Check drafts against active brand policies, review evidence citations, and record authorized publication decisions with Content Passports.
        </p>

        {/* Collapsible Presentation & Testing Controls */}
        {showDemoControls && (
          <div style={{
            marginTop: 16,
            padding: '12px 16px',
            background: 'var(--bg-card)',
            border: '1px solid var(--border-light)',
            borderRadius: 8,
            display: 'flex',
            flexDirection: 'column',
            gap: 10
          }}>
            <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 8 }}>
              <span style={{ fontSize: '0.76rem', fontWeight: 700, color: 'var(--brand-gold)', textTransform: 'uppercase' }}>
                Demo Operators &amp; Evaluation Testing:
              </span>
              <span style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                fontSize: '0.72rem',
                fontWeight: 600,
                padding: '2px 8px',
                borderRadius: 20,
                background: backendConnected ? 'var(--status-approved-bg)' : 'var(--status-warning-bg)',
                border: `1px solid ${backendConnected ? 'rgba(27, 77, 62, 0.25)' : 'rgba(146, 64, 14, 0.25)'}`,
                color: backendConnected ? 'var(--status-approved-text)' : 'var(--status-warning-text)',
              }}>
                <span style={{
                  width: 6, height: 6, borderRadius: '50%',
                  background: backendConnected ? 'var(--brand-forest)' : 'var(--brand-gold)',
                }} />
                {backendConnected ? 'FastAPI Service Online (:8000)' : 'Client Safe Mode Active'}
              </span>
            </div>

            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button
                type="button"
                className={styles.presetBtn}
                onClick={handleLoadAct4Preset}
              >
                <Check size={14} color="var(--brand-forest)" />
                <span>Preset: Act 4 (Compliant Draft &bull; Reviewer Role)</span>
              </button>
              <button
                type="button"
                className={styles.presetBtn}
                onClick={handleLoad403Demo}
              >
                <AlertOctagon size={14} color="var(--status-blocked-text)" />
                <span>Test AT-018: Creator Self-Approval 403 Gate</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Role Switcher Bar */}
      <div className={styles.roleSelectorBar}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <UserCheck size={18} color="var(--brand-navy)" />
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Reviewer Authorization &amp; Access Profile:
            </div>
            <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
              Active User: <strong style={{ color: 'var(--text-primary)' }}>{reviewerName}</strong> (ID: <code>{reviewerId}</code>)
            </div>
          </div>
        </div>

        <div className={styles.roleButtons}>
          <button
            type="button"
            className={`${styles.roleBtn} ${userRole === 'reviewer' ? styles.roleBtnActiveReviewer : ''}`}
            onClick={() => handleRoleChange('reviewer')}
          >
            <Shield size={14} />
            <span>Authorised Reviewer</span>
          </button>
          <button
            type="button"
            className={`${styles.roleBtn} ${userRole === 'creator' ? styles.roleBtnActiveCreator : ''}`}
            onClick={() => handleRoleChange('creator')}
          >
            <Lock size={14} />
            <span>Content Creator</span>
          </button>
          <button
            type="button"
            className={`${styles.roleBtn} ${userRole === 'admin' ? styles.roleBtnActiveAdmin : ''}`}
            onClick={() => handleRoleChange('admin')}
          >
            <Award size={14} />
            <span>Administrator</span>
          </button>
        </div>
      </div>

      {/* Main Review Grid */}
      <div className={styles.reviewGrid}>
        {/* Left Column: Submissions Queue */}
        <div className={styles.queueCard} data-tour="review-queue">
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 4 }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Submissions Queue ({queue.length})
            </span>
            <div style={{ display: 'flex', gap: 4 }}>
              {(['all', 'pending', 'approved', 'rejected'] as const).map(f => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setFilterStatus(f)}
                  style={{
                    padding: '3px 8px',
                    borderRadius: 12,
                    fontSize: '0.7rem',
                    fontWeight: 600,
                    textTransform: 'capitalize',
                    border: '1px solid var(--border-subtle)',
                    background: filterStatus === f ? 'var(--brand-navy)' : 'transparent',
                    color: filterStatus === f ? '#FFFFFF' : 'var(--text-muted)',
                    cursor: 'pointer',
                  }}
                >
                  {f}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10, marginTop: 8 }}>
            {filteredQueue.length === 0 ? (
              <div style={{ padding: '32px 16px', textAlign: 'center', color: 'var(--text-muted)', fontSize: '0.82rem', background: 'var(--bg-surface)', borderRadius: 8, border: '1px dashed var(--border-subtle)' }}>
                <FileText size={24} style={{ opacity: 0.4, display: 'block', margin: '0 auto 8px' }} />
                No drafts in queue.
              </div>
            ) : (
              filteredQueue.map(item => {
                const isSelected = selectedId === item.id;
                const hasBlockers = item.blockersCount > 0;
                const itemIsOcrBlocked = item.ocr_status === 'failed' || item.ocr_status === 'corrupted' || (item.text_checks_status === 'not_run' && !item.content);
                const itemIsVisualOnly = item.is_visual_only || item.review_status === 'visual_only';
                const itemIsCleanChecked = item.text_checks_status === 'checked_no_findings' || (!itemIsOcrBlocked && !itemIsVisualOnly && item.blockersCount === 0 && item.findings?.length === 0 && !!item.content);

                return (
                  <div
                    key={item.id}
                    className={`${styles.queueItem} ${isSelected ? styles.queueItemActive : ''}`}
                    onClick={() => {
                      setSelectedId(item.id);
                      setErrorMessage(null);
                      setErrorStatus(null);
                      setSuccessResponse(item.passportId ? {
                        id: item.id,
                        draft_id: item.draftId,
                        scan_id: item.scanId,
                        reviewer_id: reviewerId,
                        reviewer_name: reviewerName,
                        decision: 'approved',
                        comment: item.reviewerComment || 'Approved',
                        passport_id: item.passportId,
                        sha256: item.sha256,
                        created_at: item.submittedAt
                      } : null);
                    }}
                  >
                    <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 6 }}>
                      <span style={{ fontSize: '0.86rem', fontWeight: 700, color: 'var(--text-primary)', lineHeight: 1.3 }}>
                        {item.title}
                      </span>
                      <span style={{
                        fontSize: '0.68rem',
                        fontWeight: 800,
                        textTransform: 'uppercase',
                        padding: '2px 8px',
                        borderRadius: 4,
                        background: item.status === 'approved' ? 'var(--status-approved-bg)' : item.status === 'rejected' ? 'var(--status-blocked-bg)' : 'var(--status-warning-bg)',
                        color: item.status === 'approved' ? 'var(--status-approved-text)' : item.status === 'rejected' ? 'var(--status-blocked-text)' : 'var(--status-warning-text)',
                      }}>
                        {item.status}
                      </span>
                    </div>

                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
                      <span>{item.author}</span>
                      <span>•</span>
                      <span>{item.submittedAt.slice(0, 10)}</span>
                    </div>

                    <div style={{ display: 'flex', gap: 8, marginTop: 8, flexWrap: 'wrap' }}>
                      {itemIsOcrBlocked ? (
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4,
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          color: '#b91c1c',
                          background: 'rgba(239, 68, 68, 0.12)',
                          border: '1px solid rgba(239, 68, 68, 0.25)',
                          padding: '2px 6px',
                          borderRadius: 4,
                        }}>
                          <AlertTriangle size={11} /> Manual Input Required
                        </span>
                      ) : itemIsVisualOnly ? (
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4,
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          color: '#d97706',
                          background: 'rgba(245, 158, 11, 0.12)',
                          border: '1px solid rgba(245, 158, 11, 0.25)',
                          padding: '2px 6px',
                          borderRadius: 4,
                        }}>
                          <Eye size={11} /> Visual Review Only
                        </span>
                      ) : hasBlockers ? (
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4,
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          color: 'var(--status-blocked-text)',
                          background: 'var(--status-blocked-bg)',
                          padding: '2px 6px',
                          borderRadius: 4,
                        }}>
                          <XCircle size={11} /> {item.blockersCount} Blockers
                        </span>
                      ) : itemIsCleanChecked ? (
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4,
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          color: 'var(--status-approved-text)',
                          background: 'var(--status-approved-bg)',
                          padding: '2px 6px',
                          borderRadius: 4,
                        }}>
                          <CheckCircle2 size={11} /> Checked — No Findings
                        </span>
                      ) : null}

                      {item.passportId && (
                        <span style={{
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4,
                          fontSize: '0.7rem',
                          fontWeight: 700,
                          color: 'var(--brand-forest)',
                          background: 'var(--status-approved-bg)',
                          padding: '2px 6px',
                          borderRadius: 4,
                        }}>
                          <Award size={11} /> Passport Minted
                        </span>
                      )}
                    </div>
                  </div>
                );
              })
            )}
          </div>
        </div>

        {/* Right Column: Detailed Draft Inspection & Decision */}
        {selectedItem ? (
          <div className={styles.detailCard}>
            {/* Header info */}
            <div className={styles.detailHeader}>
              <div>
                <div style={{ display: 'flex', alignItems: 'center', gap: 8, marginBottom: 4 }}>
                  <h2 style={{ fontSize: '1.25rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                    {selectedItem.title}
                  </h2>
                </div>
                <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  Draft ID: <code style={{ color: 'var(--brand-navy)', fontWeight: 700 }}>{selectedItem.draftId}</code> • Scan ID: <code>{selectedItem.scanId}</code>
                  {selectedItem.original_filename && (
                    <span> • Asset: <strong>{selectedItem.original_filename}</strong></span>
                  )}
                  {selectedItem.detected_mime_type && (
                    <span> • Type: <code>{selectedItem.detected_mime_type}</code></span>
                  )}
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                {isOcrBlocked ? (
                  <span style={{
                    fontSize: '0.78rem',
                    fontWeight: 800,
                    padding: '6px 12px',
                    borderRadius: 6,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6,
                    background: 'rgba(239, 68, 68, 0.12)',
                    color: '#b91c1c',
                    border: '1px solid rgba(239, 68, 68, 0.3)'
                  }}>
                    <AlertOctagon size={14} />
                    <span>Review Blocked — Readable Text Required</span>
                  </span>
                ) : isVisualOnly ? (
                  <span style={{
                    fontSize: '0.78rem',
                    fontWeight: 800,
                    padding: '6px 12px',
                    borderRadius: 6,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6,
                    background: 'rgba(245, 158, 11, 0.12)',
                    color: '#d97706',
                    border: '1px solid rgba(245, 158, 11, 0.3)'
                  }}>
                    <Eye size={14} />
                    <span>Visual Review Only (Reason Required)</span>
                  </span>
                ) : selectedItem.blockersCount > 0 ? (
                  <span style={{
                    fontSize: '0.78rem',
                    fontWeight: 800,
                    padding: '6px 12px',
                    borderRadius: 6,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6,
                    background: 'var(--status-blocked-bg)',
                    color: 'var(--status-blocked-text)',
                    border: '1px solid rgba(153, 27, 27, 0.25)'
                  }}>
                    <AlertTriangle size={14} />
                    <span>{selectedItem.blockersCount} Blockers Unresolved</span>
                  </span>
                ) : (
                  <span style={{
                    fontSize: '0.78rem',
                    fontWeight: 800,
                    padding: '6px 12px',
                    borderRadius: 6,
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 6,
                    background: 'var(--status-approved-bg)',
                    color: 'var(--status-approved-text)',
                    border: '1px solid rgba(27, 77, 62, 0.25)'
                  }}>
                    <CheckCircle2 size={14} />
                    <span>Checked — No Findings (Eligible)</span>
                  </span>
                )}
              </div>
            </div>

            {/* Content Preview */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                <label style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Draft Content Under Review:
                </label>
                {selectedItem.brand_disclaimer && (
                  <span style={{
                    fontSize: '0.72rem',
                    fontWeight: 600,
                    color: '#d97706',
                    background: 'rgba(245, 158, 11, 0.12)',
                    padding: '2px 8px',
                    borderRadius: 4
                  }}>
                    {selectedItem.brand_disclaimer}
                  </span>
                )}
              </div>

              {isOcrBlocked ? (
                <div style={{
                  background: 'rgba(239, 68, 68, 0.04)',
                  border: '1px dashed rgba(239, 68, 68, 0.35)',
                  borderRadius: 8,
                  padding: '16px 20px',
                  fontSize: '0.88rem',
                  color: 'var(--text-secondary)',
                  lineHeight: 1.6
                }}>
                  <div style={{ color: '#b91c1c', fontWeight: 700, marginBottom: 4 }}>
                    [No verified campaign copy available]
                  </div>
                  <div>
                    OCR text extraction failed or yielded unreadable binary artifacts for asset &ldquo;{selectedItem.original_filename || selectedItem.title}&rdquo;.
                    Text-dependent policy checks have not been completed.
                  </div>
                </div>
              ) : (
                <div className={styles.contentPreview}>
                  &ldquo;{selectedItem.content}&rdquo;
                </div>
              )}
            </div>

            {/* Evidence & Findings Audit Section */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Policy Findings &amp; Evidence ({isOcrBlocked ? 0 : (selectedItem.findings?.length || 0)})
                </span>
                <span style={{ fontSize: '0.74rem', color: 'var(--brand-navy-light)', fontWeight: 600 }}>
                  Every finding links to a registered source
                </span>
              </div>

              {/* Exact Screenshot 2 Condition: OCR Failed -> Manual Input Required */}
              {isOcrBlocked ? (
                <div style={{
                  background: 'rgba(239, 68, 68, 0.06)',
                  border: '1px solid rgba(239, 68, 68, 0.35)',
                  borderRadius: 8,
                  padding: '18px 20px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 12,
                }}>
                  <div style={{ display: 'flex', alignItems: 'flex-start', gap: 12 }}>
                    <AlertOctagon size={24} color="#dc2626" style={{ flexShrink: 0, marginTop: 2 }} />
                    <div>
                      <div style={{ fontWeight: 800, fontSize: '1rem', color: '#b91c1c' }}>
                        Review blocked — readable text required
                      </div>
                      <div style={{ fontSize: '0.84rem', color: 'var(--text-secondary)', marginTop: 4, lineHeight: 1.5 }}>
                        OCR failed for this asset. No text-based compliance decision has been made.
                      </div>
                    </div>
                  </div>

                  <div style={{
                    background: '#FFFFFF',
                    border: '1px solid rgba(0, 0, 0, 0.08)',
                    borderRadius: 6,
                    padding: '10px 14px',
                    fontSize: '0.78rem',
                    display: 'grid',
                    gridTemplateColumns: 'repeat(auto-fit, minmax(180px, 1fr))',
                    gap: 10,
                  }}>
                    <div>Status: <strong style={{ color: '#b91c1c' }}>Manual input required</strong></div>
                    <div>Text findings: <strong style={{ color: 'var(--text-muted)' }}>Not evaluated</strong></div>
                    <div>Visual checks: <strong style={{ color: 'var(--brand-forest)' }}>Ready</strong></div>
                    {selectedItem.original_filename && (
                      <div>Original file: <strong>{selectedItem.original_filename}</strong></div>
                    )}
                    {selectedItem.detected_mime_type && (
                      <div>Detected type: <strong>{selectedItem.detected_mime_type}</strong></div>
                    )}
                  </div>

                  <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap', marginTop: 4 }}>
                    <button
                      type="button"
                      onClick={() => setShowManualCopyModal(true)}
                      style={{
                        background: 'var(--brand-navy)',
                        color: '#FFFFFF',
                        border: 'none',
                        padding: '8px 16px',
                        borderRadius: 6,
                        fontSize: '0.82rem',
                        fontWeight: 700,
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                      }}
                    >
                      <Edit3 size={14} />
                      <span>Enter copy manually</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => handleReject('OCR extraction failed. Clearer upload required.')}
                      style={{
                        background: 'transparent',
                        color: 'var(--status-blocked-text)',
                        border: '1px solid rgba(153, 27, 27, 0.3)',
                        padding: '8px 16px',
                        borderRadius: 6,
                        fontSize: '0.82rem',
                        fontWeight: 700,
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                      }}
                    >
                      <XCircle size={14} />
                      <span>Request a clearer upload</span>
                    </button>

                    <button
                      type="button"
                      onClick={() => setShowVisualOverrideModal(true)}
                      style={{
                        background: 'rgba(245, 158, 11, 0.1)',
                        color: '#d97706',
                        border: '1px solid rgba(245, 158, 11, 0.35)',
                        padding: '8px 16px',
                        borderRadius: 6,
                        fontSize: '0.82rem',
                        fontWeight: 700,
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6,
                      }}
                    >
                      <Eye size={14} />
                      <span>Accept visual-only review (Reason required)</span>
                    </button>
                  </div>
                </div>
              ) : isVisualOnly ? (
                <div style={{
                  background: 'rgba(245, 158, 11, 0.08)',
                  border: '1px solid rgba(245, 158, 11, 0.35)',
                  borderRadius: 8,
                  padding: '16px 20px',
                  display: 'flex',
                  flexDirection: 'column',
                  gap: 10,
                }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <Eye size={20} color="#d97706" />
                    <div>
                      <div style={{ fontWeight: 800, fontSize: '0.94rem', color: '#b45309' }}>
                        Visual review only &bull; Text and claim checks are pending
                      </div>
                      <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: 2 }}>
                        Readable copy was not extracted. Visual brand identity checks are ready. Reason required for authorized sign-off.
                      </div>
                    </div>
                  </div>
                  {selectedItem.decision_limitations && (
                    <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', fontStyle: 'italic' }}>
                      Limitation note: {selectedItem.decision_limitations}
                    </div>
                  )}
                </div>
              ) : selectedItem.findings && selectedItem.findings.length > 0 ? (
                <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
                  {selectedItem.findings.map((f, idx) => (
                    <div
                      key={idx}
                      style={{
                        background: 'var(--bg-surface)',
                        border: '1px solid var(--border-subtle)',
                        borderRadius: 8,
                        padding: '12px 16px',
                      }}
                    >
                      <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                          <span style={{
                            fontSize: '0.68rem',
                            fontWeight: 800,
                            padding: '2px 6px',
                            borderRadius: 4,
                            background: f.severity === 'high' || f.severity === 'block' ? 'var(--status-blocked-bg)' : 'var(--status-warning-bg)',
                            color: f.severity === 'high' || f.severity === 'block' ? 'var(--status-blocked-text)' : 'var(--status-warning-text)',
                            textTransform: 'uppercase',
                          }}>
                            {f.severity}
                          </span>
                          <span style={{ fontSize: '0.82rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                            {f.category.replace('_', ' ').toUpperCase()}
                          </span>
                        </div>
                        <code style={{ fontSize: '0.74rem', color: 'var(--brand-navy)', fontWeight: 700 }}>
                          {f.policy_card_id} (v{f.policy_version || '1.0'})
                        </code>
                      </div>

                      <p style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginBottom: 6 }}>
                        {f.explanation}
                      </p>

                      <div style={{
                        background: '#FFFFFF',
                        borderLeft: '3px solid var(--brand-forest)',
                        padding: '8px 12px',
                        fontSize: '0.78rem',
                        color: 'var(--text-secondary)',
                        fontStyle: 'italic',
                        borderRadius: '0 4px 4px 0',
                      }}>
                        Source Quote: &ldquo;{f.source_quote}&rdquo;
                      </div>
                    </div>
                  ))}
                </div>
              ) : (
                <div style={{
                  background: 'var(--status-approved-bg)',
                  border: '1px solid rgba(27, 77, 62, 0.25)',
                  borderRadius: 8,
                  padding: '14px 18px',
                  display: 'flex',
                  alignItems: 'center',
                  gap: 12
                }}>
                  <CheckCircle2 size={18} color="var(--brand-forest)" />
                  <span style={{ fontSize: '0.84rem', color: 'var(--status-approved-text)', fontWeight: 600 }}>
                    Checked — no findings. Zero policy citations flagged against active guidelines. Clean bill of health.
                  </span>
                </div>
              )}
            </div>

            {/* Error / Governance Rejection Banner */}
            {errorMessage && (
              <div style={{
                background: errorStatus === 403 ? 'var(--status-blocked-bg)' : 'var(--status-warning-bg)',
                border: `1px solid ${errorStatus === 403 ? 'rgba(153, 27, 27, 0.3)' : 'rgba(146, 64, 14, 0.3)'}`,
                borderRadius: 8,
                padding: '14px 18px',
                display: 'flex',
                alignItems: 'flex-start',
                gap: 12,
              }}>
                <AlertOctagon size={20} color={errorStatus === 403 ? 'var(--status-blocked-text)' : 'var(--status-warning-text)'} style={{ flexShrink: 0, marginTop: 2 }} />
                <div>
                  <div style={{ fontWeight: 800, fontSize: '0.9rem', color: errorStatus === 403 ? 'var(--status-blocked-text)' : 'var(--status-warning-text)' }}>
                    {errorStatus === 403 ? 'HTTP 403 Forbidden — Self-Approval Prohibited' : 'Review Submission Error'}
                  </div>
                  <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: 4, lineHeight: 1.5 }}>
                    {errorMessage}
                  </div>
                  {errorStatus === 403 && (
                    <div style={{ marginTop: 8 }}>
                      <button
                        type="button"
                        onClick={() => handleRoleChange('reviewer')}
                        style={{
                          background: 'var(--brand-forest)',
                          color: '#FFFFFF',
                          border: 'none',
                          borderRadius: 4,
                          padding: '5px 12px',
                          fontSize: '0.76rem',
                          fontWeight: 700,
                          cursor: 'pointer',
                        }}
                      >
                        Switch to Reviewer Role to Authorize
                      </button>
                    </div>
                  )}
                </div>
              </div>
            )}

            {/* Success Content Passport Minted Banner */}
            {successResponse && (
              <div className={styles.passportSuccessCard}>
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 12 }}>
                  <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                    <div style={{
                      width: 40, height: 40, borderRadius: 8,
                      background: 'rgba(27, 77, 62, 0.15)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      color: 'var(--brand-forest)',
                    }}>
                      <Award size={22} />
                    </div>
                    <div>
                      <div style={{ fontSize: '1rem', fontWeight: 800, color: 'var(--status-approved-text)' }}>
                        {successResponse.approval_type === 'visual_only'
                          ? 'Visual-Only Content Passport Issued!'
                          : 'Content Passport Minted Successfully!'}
                      </div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                        {successResponse.approval_type === 'visual_only'
                          ? 'Approved with documented limitation: Visual review only.'
                          : 'Draft transitioned to APPROVED status.'}
                      </div>
                    </div>
                  </div>

                  <Link
                    href={`/passports?id=${successResponse.passport_id}`}
                    className={styles.inspectBtn}
                  >
                    <span>Inspect Content Passport</span>
                    <ArrowRight size={14} />
                  </Link>
                </div>

                <div style={{
                  marginTop: 14,
                  padding: '12px 14px',
                  background: '#FFFFFF',
                  borderRadius: 6,
                  border: '1px solid var(--border-light)',
                  display: 'grid',
                  gridTemplateColumns: 'repeat(auto-fit, minmax(200px, 1fr))',
                  gap: 12,
                  fontSize: '0.78rem',
                }}>
                  <div>
                    <span style={{ color: 'var(--text-muted)', display: 'block' }}>Passport ID:</span>
                    <code style={{ color: 'var(--brand-navy)', fontWeight: 700 }}>{successResponse.passport_id}</code>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)', display: 'block' }}>Integrity Fingerprint:</span>
                    <code style={{ color: 'var(--brand-forest)', fontSize: '0.72rem', fontWeight: 700 }}>
                      {successResponse.sha256 ? `${successResponse.sha256.slice(0, 24)}...` : 'Verified Record'}
                    </code>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)', display: 'block' }}>Authorised Sign-off:</span>
                    <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{successResponse.reviewer_name}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Review Decision Form */}
            <div className={styles.actionPanel}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Reviewer Sign-Off Comments &amp; Instructions:
                </label>
                <input
                  type="text"
                  className={styles.commentInput}
                  value={reviewComment}
                  onChange={e => setReviewComment(e.target.value)}
                  placeholder="Reason or conditions for approval or revision notes..."
                />
              </div>

              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap', alignItems: 'center' }}>
                <button
                  type="button"
                  className={styles.btnApprove}
                  onClick={handleApprove}
                  disabled={submitting || selectedItem.status === 'approved' || (isOcrBlocked && !isVisualOnly)}
                  title={isOcrBlocked && !isVisualOnly ? 'Approval disabled: Readable text required' : 'Approve & Issue Content Passport'}
                >
                  <CheckCircle2 size={16} />
                  <span>
                    {submitting
                      ? 'Recording Human Approval...'
                      : isVisualOnly
                        ? 'Approve Visual-Only (Reason Required)'
                        : 'Approve & Issue Content Passport'}
                  </span>
                </button>

                <button
                  type="button"
                  className={styles.btnReject}
                  onClick={() => handleReject()}
                  disabled={submitting}
                >
                  <XCircle size={16} />
                  <span>Reject &amp; Request Changes</span>
                </button>

                {isOcrBlocked && !isVisualOnly && (
                  <span style={{
                    fontSize: '0.74rem',
                    fontWeight: 700,
                    color: '#b91c1c',
                    background: 'rgba(239, 68, 68, 0.1)',
                    padding: '4px 8px',
                    borderRadius: 4
                  }}>
                    Approval Disabled &bull; Readable text required
                  </span>
                )}
              </div>

              <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 6 }}>
                <HelpCircle size={13} />
                <span>
                  Requires <strong>Reviewer</strong> or <strong>Admin</strong> authorization. Submissions by <strong>Creator</strong> role trigger HTTP 403 Forbidden.
                </span>
              </div>
            </div>
          </div>
        ) : (
          <div className={styles.detailCard} style={{ display: 'flex', flexDirection: 'column', alignItems: 'center', justifyContent: 'center', minHeight: 400, gap: 12, padding: 32, textAlign: 'center' }}>
            <FileText size={36} color="var(--border-subtle)" />
            <span style={{ fontWeight: 700, color: 'var(--text-primary)', fontSize: '1rem' }}>No submission selected</span>
            <span style={{ color: 'var(--text-muted)', fontSize: '0.82rem', maxWidth: 400 }}>
              Upload or scan your creative in the Workspace and proceed to Review Gate to review and issue Content Passports.
            </span>
            <Link
              href="/workspace"
              style={{
                marginTop: 8,
                padding: '8px 16px',
                borderRadius: 6,
                background: 'var(--brand-navy)',
                color: '#FFFFFF',
                fontSize: '0.82rem',
                fontWeight: 700,
                textDecoration: 'none',
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6
              }}
            >
              <span>Go to Workspace</span>
              <ArrowRight size={14} />
            </Link>
          </div>
        )}
      </div>
    </div>
  );
}

export default function ReviewGatePage() {
  return (
    <React.Suspense fallback={<div className={styles.container} style={{ color: 'var(--text-muted)', padding: '60px 0', textAlign: 'center' }}>Loading Reviewer Gateway...</div>}>
      <ReviewGateContent />
    </React.Suspense>
  );
}
