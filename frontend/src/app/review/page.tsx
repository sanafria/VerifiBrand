'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import {
  Shield, CheckCircle2, XCircle, AlertTriangle,
  Lock, ArrowRight, Award, MessageSquare, UserCheck,
  FileText, Clock, RefreshCw, Zap, Check, Eye, HelpCircle,
  Hash, ExternalLink, ChevronRight, AlertOctagon
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
    const apiBase = process.env.NEXT_PUBLIC_API_URL || 'http://127.0.0.1:8000';
    fetch(`${apiBase}/health`, { method: 'GET' })
      .then(res => setBackendConnected(res.ok))
      .catch(() => setBackendConnected(false));
  }, [queryDraftId]);

  const selectedItem = queue.find(q => q.id === selectedId) || queue[0];

  const filteredQueue = queue.filter(item => {
    if (filterStatus === 'all') return true;
    return item.status === filterStatus;
  });

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
    const match = queue.find(q => q.title.includes('Snippet B') || q.blockersCount === 0);
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

  // Handle Review Approval (Calls POST /api/reviews)
  const handleApprove = async () => {
    if (!selectedItem) return;
    setErrorMessage(null);
    setErrorStatus(null);
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

  // Handle Review Rejection
  const handleReject = async () => {
    if (!selectedItem) return;
    setErrorMessage(null);
    setErrorStatus(null);
    setSubmitting(true);

    try {
      const result = await reviewClient.submitReview(
        {
          draft_id: selectedItem.draftId,
          scan_id: selectedItem.scanId,
          decision: 'rejected',
          comment: reviewComment || 'Draft rejected. Revise prohibited terminology and expired promotions before resubmitting.',
        },
        userRole,
        reviewerId,
        reviewerName
      );

      if (result.success && result.data) {
        setQueue(reviewClient.getQueue());
        setSuccessResponse(null);
        showToast('Draft marked as Rejected. Feedback logged for creator.');
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

      {/* Header Banner */}
      <div className={styles.banner}>
        <div className={styles.headerTop}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <span className={styles.teamBadge}>
              <Shield size={14} /> Review Gateway • Separation of Duties Engine
            </span>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              fontSize: '0.75rem',
              fontWeight: 600,
              padding: '3px 10px',
              borderRadius: 20,
              background: backendConnected ? 'var(--status-approved-bg)' : 'var(--status-warning-bg)',
              border: `1px solid ${backendConnected ? 'rgba(27, 77, 62, 0.25)' : 'rgba(146, 64, 14, 0.25)'}`,
              color: backendConnected ? 'var(--status-approved-text)' : 'var(--status-warning-text)',
            }}>
              <span style={{
                width: 7, height: 7, borderRadius: '50%',
                background: backendConnected ? 'var(--brand-forest)' : 'var(--brand-gold)',
              }} />
              {backendConnected ? 'FastAPI Backend Online (:8000)' : 'Client Cryptographic Engine (Deterministic Safe Mode)'}
            </span>
          </div>

          <div style={{ display: 'flex', gap: 10 }}>
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
          Check drafts against active brand policies, substantiate claims, and generate tamper-evident content passports before publishing.
        </p>

        {/* Presentation Fast Presets */}
        <div style={{ display: 'flex', gap: 10, marginTop: 16, flexWrap: 'wrap' }}>
          <button
            type="button"
            className={styles.presetBtn}
            onClick={handleLoadAct4Preset}
          >
            <Check size={14} color="var(--brand-forest)" />
            <span>Preset: Act 4 (Compliant Snippet B • Reviewer)</span>
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

      {/* Role Switcher Bar */}
      <div className={styles.roleSelectorBar}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <UserCheck size={18} color="var(--brand-navy)" />
          <div>
            <div style={{ fontSize: '0.85rem', fontWeight: 700, color: 'var(--text-primary)' }}>
              Active Authorization Context (X-User-Role Header):
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
            <span>Reviewer (Authorized)</span>
          </button>
          <button
            type="button"
            className={`${styles.roleBtn} ${userRole === 'creator' ? styles.roleBtnActiveCreator : ''}`}
            onClick={() => handleRoleChange('creator')}
          >
            <Lock size={14} />
            <span>Creator (Triggers 403)</span>
          </button>
          <button
            type="button"
            className={`${styles.roleBtn} ${userRole === 'admin' ? styles.roleBtnActiveAdmin : ''}`}
            onClick={() => handleRoleChange('admin')}
          >
            <Award size={14} />
            <span>Admin (Authorized)</span>
          </button>
        </div>
      </div>

      {/* Main Review Grid */}
      <div className={styles.reviewGrid}>
        {/* Left Column: Submissions Queue */}
        <div className={styles.queueCard}>
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
            {filteredQueue.map(item => {
              const isSelected = selectedId === item.id;
              const hasBlockers = item.blockersCount > 0;

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

                  <div style={{ display: 'flex', gap: 8, marginTop: 8 }}>
                    {hasBlockers ? (
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
                    ) : (
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
                        <CheckCircle2 size={11} /> 0 Blockers (Eligible)
                      </span>
                    )}

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
            })}
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
                </div>
              </div>

              <div style={{ textAlign: 'right' }}>
                <span style={{
                  fontSize: '0.78rem',
                  fontWeight: 800,
                  padding: '6px 12px',
                  borderRadius: 6,
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 6,
                  background: selectedItem.blockersCount === 0 ? 'var(--status-approved-bg)' : 'var(--status-blocked-bg)',
                  color: selectedItem.blockersCount === 0 ? 'var(--status-approved-text)' : 'var(--status-blocked-text)',
                  border: `1px solid ${selectedItem.blockersCount === 0 ? 'rgba(27, 77, 62, 0.25)' : 'rgba(153, 27, 27, 0.25)'}`
                }}>
                  {selectedItem.blockersCount === 0 ? (
                    <>
                      <CheckCircle2 size={14} />
                      <span>Compliant for Approval</span>
                    </>
                  ) : (
                    <>
                      <AlertTriangle size={14} />
                      <span>{selectedItem.blockersCount} Blockers Unresolved</span>
                    </>
                  )}
                </span>
              </div>
            </div>

            {/* Content Preview */}
            <div>
              <label style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 6, display: 'block' }}>
                Draft Marketing Copy Under Review:
              </label>
              <div className={styles.contentPreview}>
                &ldquo;{selectedItem.content}&rdquo;
              </div>
            </div>

            {/* Evidence & Findings Audit Section ("No receipt, no flag") */}
            <div>
              <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 8 }}>
                <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                  Policy Evidence Audit Trail ({selectedItem.findings?.length || 0})
                </span>
                <span style={{ fontSize: '0.74rem', color: 'var(--brand-navy-light)', fontWeight: 600 }}>
                  Guaranteed Quote Citations Enforced
                </span>
              </div>

              {selectedItem.findings && selectedItem.findings.length > 0 ? (
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
                    Zero policy citations flagged against active guidelines. Clean bill of health.
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
                        Content Passport Minted Successfully!
                      </div>
                      <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                        Draft transitioned to <strong style={{ color: 'var(--status-approved-text)' }}>APPROVED</strong> status
                      </div>
                    </div>
                  </div>

                  <Link
                    href={`/passports?id=${successResponse.passport_id}`}
                    className={styles.inspectBtn}
                  >
                    <span>Inspect Passport Certificate</span>
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
                    <span style={{ color: 'var(--text-muted)', display: 'block' }}>Canonical SHA-256 Fingerprint:</span>
                    <code style={{ color: 'var(--brand-forest)', fontSize: '0.72rem', fontWeight: 700 }}>
                      {successResponse.sha256 ? `${successResponse.sha256.slice(0, 24)}...` : 'Verified Untampered'}
                    </code>
                  </div>
                  <div>
                    <span style={{ color: 'var(--text-muted)', display: 'block' }}>Authorized Sign-off:</span>
                    <span style={{ color: 'var(--text-primary)', fontWeight: 600 }}>{successResponse.reviewer_name}</span>
                  </div>
                </div>
              </div>
            )}

            {/* Review Decision Form */}
            <div className={styles.actionPanel}>
              <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
                <label style={{ fontSize: '0.8rem', fontWeight: 700, color: 'var(--text-primary)' }}>
                  Reviewer Sign-Off Comments & Instructions:
                </label>
                <input
                  type="text"
                  className={styles.commentInput}
                  value={reviewComment}
                  onChange={e => setReviewComment(e.target.value)}
                  placeholder="Reason or conditions for approval or revision notes..."
                />
              </div>

              <div style={{ display: 'flex', gap: 12, flexWrap: 'wrap' }}>
                <button
                  type="button"
                  className={styles.btnApprove}
                  onClick={handleApprove}
                  disabled={submitting || selectedItem.status === 'approved'}
                >
                  <CheckCircle2 size={16} />
                  <span>
                    {submitting ? 'Executing Cryptographic Minting...' : 'Approve & Mint Content Passport'}
                  </span>
                </button>

                <button
                  type="button"
                  className={styles.btnReject}
                  onClick={handleReject}
                  disabled={submitting}
                >
                  <XCircle size={16} />
                  <span>Reject & Request Revision</span>
                </button>
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
          <div className={styles.detailCard} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 400 }}>
            <span style={{ color: 'var(--text-muted)' }}>No submission selected</span>
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
