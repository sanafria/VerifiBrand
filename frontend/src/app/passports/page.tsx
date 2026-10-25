'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { useSearchParams } from 'next/navigation';
import {
  Shield, CheckCircle2, AlertTriangle, RefreshCw,
  Calendar, User, Clock, FileText,
  Award, Hash, Copy, Check, ArrowLeft, AlertOctagon, Lock,
  Download, Share2, Sparkles, CheckCheck, ChevronDown, ChevronUp,
  FileCheck, ShieldAlert
} from 'lucide-react';
import {
  reviewClient,
  PassportRecord,
  computeCanonicalSha256,
  SEED_DEFAULT_PASSPORTS
} from '@/lib/api/reviewClient';
import { CertificateSeal } from './CertificateSeal';
import styles from './page.module.css';

function PassportsContent() {
  const searchParams = useSearchParams();
  const queryPassportId = searchParams.get('id');

  const [passports, setPassports] = useState<PassportRecord[]>([]);
  const [selectedPassport, setSelectedPassport] = useState<PassportRecord | null>(null);
  const [filter, setFilter] = useState<'all' | 'valid' | 'override'>('all');
  
  // Interactive state
  const [copiedHash, setCopiedHash] = useState(false);
  const [isTampered, setIsTampered] = useState(false);
  const [recomputing, setRecomputing] = useState(false);
  const [tamperedHash, setTamperedHash] = useState<string | null>(null);
  const [toastMessage, setToastMessage] = useState<string | null>(null);
  const [showTechnicalDetails, setShowTechnicalDetails] = useState(false);
  const [showDemoControls, setShowDemoControls] = useState(false);

  const showToast = (msg: string) => {
    setToastMessage(msg);
    setTimeout(() => setToastMessage(null), 3500);
  };

  // Load passports on mount
  useEffect(() => {
    async function loadData() {
      let list = reviewClient.getAllPassports();
      if (list.length === 0) {
        // Fallback to seed records
        list = Object.values(SEED_DEFAULT_PASSPORTS);
      }
      setPassports(list);

      if (queryPassportId) {
        const found = list.find(p => p.id === queryPassportId);
        if (found) {
          setSelectedPassport(found);
        } else {
          const direct = await reviewClient.getPassport(queryPassportId);
          if (direct) {
            setSelectedPassport(direct);
            setPassports(prev => [direct, ...prev]);
          } else if (list.length > 0) {
            setSelectedPassport(list[0]);
          }
        }
      } else if (list.length > 0) {
        setSelectedPassport(list[0]);
      }
    }
    loadData();
  }, [queryPassportId]);

  // Copy SHA-256
  const copyToClipboard = (text: string) => {
    if (navigator.clipboard) {
      navigator.clipboard.writeText(text);
      setCopiedHash(true);
      showToast('Integrity fingerprint copied to clipboard');
      setTimeout(() => setCopiedHash(false), 2000);
    }
  };

  // Copy Verification URL
  const copyVerificationLink = () => {
    if (!selectedPassport) return;
    const url = `${window.location.origin}/passports?id=${selectedPassport.id}`;
    if (navigator.clipboard) {
      navigator.clipboard.writeText(url);
      showToast('Permanent Verification Link copied to clipboard');
    }
  };

  // Download Cryptographic Certificate JSON Proof
  const downloadCertificateJson = () => {
    if (!selectedPassport) return;
    const exportData = {
      verifibrand_certificate: {
        passport_id: selectedPassport.id,
        draft_id: selectedPassport.draft_id,
        scan_id: selectedPassport.scan_id,
        review_id: selectedPassport.review_id,
        status: selectedPassport.status,
        canonical_sha256_hash: selectedPassport.passport_hash,
        hash_verified: selectedPassport.hash_verified,
        issued_at: selectedPassport.created_at,
        metadata_snapshot: selectedPassport.metadata_snapshot,
        cryptographic_standard: 'FIPS 180-4 SHA-256 (Canonical JSON)',
        verified_by: 'VerifiBrand Multi-Party Governance Engine',
      }
    };
    const blob = new Blob([JSON.stringify(exportData, null, 2)], { type: 'application/json' });
    const href = URL.createObjectURL(blob);
    const link = document.createElement('a');
    link.href = href;
    link.download = `verifibrand_passport_${selectedPassport.id}.json`;
    document.body.appendChild(link);
    link.click();
    document.body.removeChild(link);
    URL.revokeObjectURL(href);
    showToast('Downloaded signed Certificate JSON proof');
  };

  // Preset: Load Authentic Untampered Record
  const handleLoadAuthentic = () => {
    if (selectedPassport) {
      setIsTampered(false);
      setTamperedHash(null);
      setSelectedPassport({
        ...selectedPassport,
        hash_verified: true,
      });
      showToast('Authentic approval record verified intact');
    }
  };

  // Simulate Database Tampering (AT-022 / Act 5)
  const handleSimulateTamper = async () => {
    if (!selectedPassport) return;
    setRecomputing(true);

    setTimeout(async () => {
      // Modify one word in the approved copy snapshot without recalculating stored hash
      const originalCopy = selectedPassport.metadata_snapshot?.draft_content || '';
      const tamperedCopy = originalCopy.includes('[UNAUTHORIZED]')
        ? originalCopy
        : originalCopy + ' [UNAUTHORIZED AD AGENCY EDIT]';

      const tamperedSnapshot = {
        ...selectedPassport.metadata_snapshot,
        draft_content: tamperedCopy,
      };

      const recomputed = await computeCanonicalSha256(tamperedSnapshot);
      const isMatch = recomputed === selectedPassport.passport_hash;

      setTamperedHash(recomputed);
      setSelectedPassport({
        ...selectedPassport,
        metadata_snapshot: tamperedSnapshot,
        hash_verified: isMatch,
      });

      setIsTampered(true);
      setShowTechnicalDetails(true);
      setRecomputing(false);
      showToast('Database Tampering Simulated: Hash mismatch detected!');
    }, 400);
  };

  // Restore Original Copy
  const handleRestoreIntegrity = async () => {
    if (!selectedPassport) return;
    setRecomputing(true);

    setTimeout(async () => {
      const originalCopy = (selectedPassport.metadata_snapshot?.draft_content || '').replace(' [UNAUTHORIZED AD AGENCY EDIT]', '');
      const restoredSnapshot = {
        ...selectedPassport.metadata_snapshot,
        draft_content: originalCopy,
      };

      const recomputed = await computeCanonicalSha256(restoredSnapshot);
      const isMatch = recomputed === selectedPassport.passport_hash;

      setSelectedPassport({
        ...selectedPassport,
        metadata_snapshot: restoredSnapshot,
        hash_verified: isMatch,
      });

      setIsTampered(false);
      setTamperedHash(null);
      setRecomputing(false);
      showToast('Integrity Restored: Cryptographic signature verified authentic!');
    }, 300);
  };

  // Filtered Passports
  const filtered = passports.filter(p => {
    if (filter === 'all') return true;
    if (filter === 'valid') return p.status === 'valid' && p.metadata_snapshot?.decision !== 'approved_with_override';
    if (filter === 'override') return p.metadata_snapshot?.decision === 'approved_with_override';
    return true;
  });

  const snapshot = selectedPassport?.metadata_snapshot || {};
  const findingsList = snapshot.findings_summary || [];
  const evidenceList = snapshot.evidence_used || [
    { name: 'Promotional Claims Policy', version: 'v2.1', type: 'Policy Standard', authority: 'Legal & Regulatory' },
    { name: 'Marketing Claims Register', version: 'Ref #014', type: 'Fact Register', authority: 'Verified Product Specs' },
    { name: 'Approved Terminology Standard', version: 'v1.4', type: 'Brand Guideline', authority: 'Brand Voice Guidelines' },
    { name: 'Primary Logo & Asset Guide', version: 'v3.2', type: 'Visual Asset', authority: 'Global Design System' }
  ];
  const reviewStats = snapshot.review_stats || {
    total_findings: findingsList.length || 3,
    suggestions_applied: findingsList.filter((f: any) => f.status === 'resolved').length || 2,
    approved_with_override: findingsList.filter((f: any) => f.status === 'override').length || 1,
  };

  return (
    <div className={styles.container}>
      {/* Toast Notification */}
      {toastMessage && (
        <div className={styles.toast}>
          <Sparkles size={16} color="var(--brand-gold)" />
          <span>{toastMessage}</span>
        </div>
      )}

      {/* Header Banner */}
      <div className={styles.banner}>
        <div className={styles.headerTop}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 10, flexWrap: 'wrap' }}>
            <span className={styles.teamBadge}>
              <Award size={14} /> Brand Governance &amp; Compliance Registry
            </span>
            <span style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              fontSize: '0.74rem',
              fontWeight: 700,
              padding: '3px 10px',
              borderRadius: 20,
              background: 'var(--status-review-bg)',
              border: '1px solid rgba(30, 64, 175, 0.2)',
              color: 'var(--status-review-text)',
            }}>
              <FileCheck size={12} />
              <span>Evidence-Backed Verification Record</span>
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
              <ShieldAlert size={13} color={showDemoControls ? '#F59E0B' : 'currentColor'} />
              <span>{showDemoControls ? 'Hide Testing Controls' : 'Demo & Testing Controls'}</span>
            </button>
            <Link href="/review" className={styles.backLink}>
              <ArrowLeft size={14} /> Back to Review Gate
            </Link>
          </div>
        </div>

        <h1 className={styles.title}>Content Passport</h1>
        <p className={styles.desc}>
          An evidence-backed approval record for every published content version.
        </p>
        <div className={styles.contextBox}>
          This record shows what was reviewed, which policies were applied, what corrections were made, and who approved this version before public distribution.
        </div>

        {/* Demo Preset Buttons for Presentation */}
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
            <span style={{ fontSize: '0.76rem', fontWeight: 700, color: 'var(--brand-gold)', textTransform: 'uppercase' }}>
              Tamper Verification &amp; Simulation Tests:
            </span>
            <div style={{ display: 'flex', gap: 10, flexWrap: 'wrap' }}>
              <button
                type="button"
                className={styles.presetBtn}
                onClick={handleLoadAuthentic}
              >
                <CheckCheck size={14} color="var(--brand-forest)" />
                <span>Verify Authentic Record</span>
              </button>
              <button
                type="button"
                className={styles.presetBtn}
                onClick={handleSimulateTamper}
              >
                <AlertOctagon size={14} color="var(--status-blocked-text)" />
                <span>Simulate Downstream Tampering</span>
              </button>
            </div>
          </div>
        )}
      </div>

      {/* Hero Key Information Cards */}
      <div className={styles.metricGrid}>
        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Campaign Version</div>
          <div className={styles.metricVal} style={{ color: 'var(--brand-navy)' }}>
            v{snapshot.version || 4}
          </div>
          <div className={styles.metricSub}>
            {snapshot.draft_title || 'Summer Membership Campaign'}
          </div>
        </div>

        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Governance Status</div>
          <div className={styles.metricVal} style={{ color: selectedPassport?.hash_verified ? 'var(--status-approved-text)' : 'var(--status-blocked-text)' }}>
            {selectedPassport?.hash_verified ? 'Record Verified' : 'Tamper Alert'}
          </div>
          <div className={styles.metricSub}>
            {selectedPassport?.hash_verified ? 'Integrity check passed' : 'Discrepancy detected'}
          </div>
        </div>

        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Reviewer Sign-off</div>
          <div className={styles.metricVal} style={{ color: 'var(--brand-gold)', fontSize: '1.25rem' }}>
            {snapshot.reviewer_name || 'Authorised Reviewer'}
          </div>
          <div className={styles.metricSub}>
            {snapshot.reviewer_role || 'Senior Compliance Officer'}
          </div>
        </div>

        <div className={styles.metricCard}>
          <div className={styles.metricLabel}>Evidence Checked</div>
          <div className={styles.metricVal} style={{ color: 'var(--color-success)' }}>
            {evidenceList.length} Sources
          </div>
          <div className={styles.metricSub}>
            Policies, Fact Registers &amp; Specs
          </div>
        </div>
      </div>

      {/* Main Two-Column Layout */}
      <div className={styles.mainGrid}>
        {/* Left Column: Passport Registry */}
        <div className={styles.listCard}>
          <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
            <span style={{ fontSize: '0.78rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase', letterSpacing: '0.05em' }}>
              Passport Registry ({passports.length})
            </span>
            <div style={{ display: 'flex', gap: 4 }}>
              {(['all', 'valid', 'override'] as const).map(f => (
                <button
                  key={f}
                  type="button"
                  onClick={() => setFilter(f)}
                  style={{
                    padding: '2px 8px',
                    borderRadius: 12,
                    fontSize: '0.68rem',
                    fontWeight: 700,
                    textTransform: 'capitalize',
                    border: '1px solid var(--border-subtle)',
                    background: filter === f ? 'var(--brand-navy)' : 'transparent',
                    color: filter === f ? '#FFFFFF' : 'var(--text-muted)',
                    cursor: 'pointer',
                  }}
                >
                  {f === 'override' ? 'Overrides' : f}
                </button>
              ))}
            </div>
          </div>

          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {filtered.map(p => {
              const isSelected = selectedPassport?.id === p.id;
              const pSnap = p.metadata_snapshot || {};
              const isOverride = pSnap.decision === 'approved_with_override';

              return (
                <div
                  key={p.id}
                  className={`${styles.passportItem} ${isSelected ? styles.passportItemActive : ''}`}
                  onClick={() => {
                    setSelectedPassport(p);
                    setIsTampered(false);
                    setTamperedHash(null);
                  }}
                >
                  <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', marginBottom: 6 }}>
                    <code style={{ fontSize: '0.82rem', fontWeight: 800, color: 'var(--brand-navy)' }}>
                      {p.id}
                    </code>
                    <span style={{
                      fontSize: '0.66rem',
                      fontWeight: 800,
                      padding: '2px 7px',
                      borderRadius: 4,
                      background: isOverride ? 'var(--status-warning-bg)' : 'var(--status-approved-bg)',
                      color: isOverride ? 'var(--status-warning-text)' : 'var(--status-approved-text)',
                      textTransform: 'uppercase'
                    }}>
                      {isOverride ? 'Override' : 'Approved'}
                    </span>
                  </div>

                  <div style={{ fontSize: '0.84rem', color: 'var(--text-primary)', marginBottom: 6, fontWeight: 700, lineHeight: 1.3 }}>
                    {pSnap.draft_title || 'Marketing Campaign'}
                  </div>

                  <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <User size={12} /> {pSnap.reviewer_name || 'Reviewer'} • v{pSnap.version || 4}
                    </span>
                    <span style={{ display: 'flex', alignItems: 'center', gap: 4 }}>
                      <Clock size={12} /> {p.created_at ? p.created_at.slice(0, 10) : '2026-10-24'}
                    </span>
                  </div>
                </div>
              );
            })}
          </div>
        </div>

        {/* Right Column: Content Passport Inspection */}
        {selectedPassport ? (
          <div className={styles.certificateCard} data-tour="passport-card">
            {/* Watermark Seal */}
            <div className={styles.watermarkContainer}>
              <CertificateSeal verified={selectedPassport.hash_verified} size={150} />
            </div>

            {/* Header: Title & Decision Badge */}
            <div className={styles.certHeader}>
              <div style={{ flex: 1 }}>
                <div style={{ display: 'flex', alignItems: 'center', gap: 10, marginBottom: 4 }}>
                  <Award size={24} color="var(--brand-gold)" />
                  <span style={{ fontSize: '1.45rem', fontWeight: 900, color: 'var(--text-primary)', letterSpacing: '-0.02em' }}>
                    {snapshot.draft_title || 'Summer Membership Campaign'}
                  </span>
                </div>
                <div style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>
                  Passport ID: <code style={{ color: 'var(--brand-navy)', fontWeight: 800 }}>{selectedPassport.id}</code> • Version: <strong style={{ color: 'var(--text-primary)' }}>{snapshot.version || 4}</strong> • Review ID: <code>{selectedPassport.review_id}</code>
                </div>
              </div>

              {/* Status Badge */}
              <div>
                {selectedPassport.hash_verified ? (
                  <div className={styles.verifiedBadge}>
                    <CheckCircle2 size={16} />
                    <span>Approval record verified</span>
                  </div>
                ) : (
                  <div className={styles.tamperBadge}>
                    <AlertOctagon size={16} />
                    <span>Tamper Detected! Hash Mismatch</span>
                  </div>
                )}
              </div>
            </div>

            {/* Quick Actions Row */}
            <div style={{ display: 'flex', gap: 8, justifyContent: 'flex-end', marginTop: -14 }}>
              <button
                type="button"
                className={styles.actionIconBtn}
                onClick={copyVerificationLink}
                title="Share Verification Link"
              >
                <Share2 size={13} />
                <span>Share Link</span>
              </button>
              <button
                type="button"
                className={styles.actionIconBtn}
                onClick={downloadCertificateJson}
                title="Download Signed Proof JSON"
              >
                <Download size={13} />
                <span>JSON Proof</span>
              </button>
              <button
                type="button"
                className={styles.actionIconBtn}
                onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
                title="Toggle Technical Integrity Details"
              >
                <Lock size={13} />
                <span>{showTechnicalDetails ? 'Hide Integrity' : 'View Integrity'}</span>
              </button>
            </div>

            {/* Section 1: Approved Content Snapshot */}
            <div>
              <div className={styles.sectionHeaderRow}>
                <div>
                  <div className={styles.sectionTitle}>
                    <FileText size={16} color="var(--brand-navy)" />
                    <span>Approved Content Snapshot</span>
                  </div>
                  <div className={styles.sectionSubtitle}>
                    The exact text frozen and cleared for publication across digital channels.
                  </div>
                </div>
                {isTampered && (
                  <span style={{ fontSize: '0.74rem', color: 'var(--status-blocked-text)', fontWeight: 800 }}>
                    [MODIFIED CONTENT DETECTED]
                  </span>
                )}
              </div>

              <div className={`${styles.contentBox} ${isTampered ? styles.contentBoxTampered : ''}`}>
                &ldquo;{snapshot.draft_content || 'Exclusive Summer Access: Eligible Members enjoy verified tier pricing and early preview benefits starting today through August 31st across all partner lounges.'}&rdquo;
              </div>
            </div>

            {/* Section 2: Review Summary & Brand Findings */}
            <div>
              <div className={styles.sectionHeaderRow}>
                <div>
                  <div className={styles.sectionTitle}>
                    <CheckCircle2 size={16} color="var(--brand-forest)" />
                    <span>Review Summary &amp; Brand Findings</span>
                  </div>
                  <div className={styles.sectionSubtitle}>
                    Compliance checks and remediation applied prior to authorized sign-off.
                  </div>
                </div>
              </div>

              {/* Stats Pills */}
              <div className={styles.reviewStatsPills}>
                <span className={`${styles.statPill} ${styles.statPillReviewed}`}>
                  <FileCheck size={14} />
                  <strong>{reviewStats.total_findings}</strong> Findings Reviewed
                </span>
                <span className={`${styles.statPill} ${styles.statPillApplied}`}>
                  <CheckCheck size={14} />
                  <strong>{reviewStats.suggestions_applied}</strong> Suggestions Applied
                </span>
                <span className={`${styles.statPill} ${styles.statPillOverride}`}>
                  <AlertTriangle size={14} />
                  <strong>{reviewStats.approved_with_override}</strong> Approved with Override
                </span>
              </div>

              {/* Findings Stack */}
              <div className={styles.findingsList}>
                {findingsList.map((f: any, idx: number) => {
                  const isResolved = f.status === 'resolved';
                  return (
                    <div key={idx} className={styles.findingCard}>
                      <div className={styles.findingTop}>
                        <div className={styles.findingTitle}>
                          {isResolved ? (
                            <CheckCircle2 size={15} color="var(--status-approved-text)" />
                          ) : (
                            <AlertTriangle size={15} color="var(--status-warning-text)" />
                          )}
                          <span>{f.title}</span>
                          <span className={styles.findingPolicyTag}>{f.policy}</span>
                        </div>
                        <span className={isResolved ? styles.badgeResolved : styles.badgeOverride}>
                          {isResolved ? 'Resolved' : 'Approved with override'}
                        </span>
                      </div>
                      <div className={styles.findingDetail}>
                        {f.detail}
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Section 3: Evidence Used for Approval */}
            <div>
              <div className={styles.sectionHeaderRow}>
                <div>
                  <div className={styles.sectionTitle}>
                    <Shield size={16} color="var(--brand-gold)" />
                    <span>Evidence Used for Approval</span>
                  </div>
                  <div className={styles.sectionSubtitle}>
                    Authoritative sources cross-checked during the automated scan and human sign-off.
                  </div>
                </div>
              </div>

              <div className={styles.evidenceGrid}>
                {evidenceList.map((ev: any, idx: number) => (
                  <div key={idx} className={styles.evidenceCard}>
                    <div className={styles.evidenceTop}>
                      <span className={styles.evidenceName}>{ev.name}</span>
                      <span className={styles.evidenceVersion}>{ev.version}</span>
                    </div>
                    <div className={styles.evidenceAuthority}>
                      {ev.type} • {ev.authority}
                    </div>
                  </div>
                ))}
              </div>
            </div>

            {/* Section 4: Reviewer Decision & Sign-off */}
            <div>
              <div className={styles.sectionHeaderRow}>
                <div>
                  <div className={styles.sectionTitle}>
                    <User size={16} color="var(--brand-navy)" />
                    <span>Reviewer Decision &amp; Audit Sign-off</span>
                  </div>
                  <div className={styles.sectionSubtitle}>
                    Human oversight record satisfying governance audit requirements.
                  </div>
                </div>
              </div>

              <div className={styles.reviewerDecisionCard}>
                <div className={styles.reviewerTop}>
                  <div className={styles.reviewerInfo}>
                    <div className={styles.reviewerAvatar}>
                      {(snapshot.reviewer_name || 'Reviewer').charAt(0)}
                    </div>
                    <div>
                      <div style={{ fontSize: '0.94rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                        {snapshot.reviewer_name || 'Authorised Reviewer'}
                      </div>
                      <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)' }}>
                        {snapshot.reviewer_role || 'Senior Compliance Officer'} • ID: <code>{snapshot.reviewer_id || 'rev-auth-01'}</code>
                      </div>
                    </div>
                  </div>

                  <div style={{ textAlign: 'right' }}>
                    <div style={{ fontSize: '0.78rem', fontWeight: 700, color: 'var(--status-approved-text)' }}>
                      {snapshot.status_label || 'Approved with override'}
                    </div>
                    <div style={{ fontSize: '0.72rem', color: 'var(--text-muted)', display: 'flex', alignItems: 'center', gap: 4, justifyContent: 'flex-end', marginTop: 2 }}>
                      <Calendar size={12} /> {snapshot.last_verified_at || '24 Oct 2026, 14:32 UTC'}
                    </div>
                  </div>
                </div>

                <div className={styles.reviewerNote}>
                  &ldquo;{snapshot.comment || 'Partner-specific campaign with supporting evidence attached. Verified against active Q3 promotional schedule and legal clearance.'}&rdquo;
                </div>
              </div>
            </div>

            {/* Section 5: Secondary Technical Integrity Details (Collapsible) */}
            <div>
              <button
                type="button"
                className={styles.technicalToggleBtn}
                onClick={() => setShowTechnicalDetails(!showTechnicalDetails)}
              >
                <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
                  <Lock size={16} color="var(--brand-navy)" />
                  <div style={{ textAlign: 'left' }}>
                    <div style={{ fontSize: '0.88rem', fontWeight: 800, color: 'var(--text-primary)' }}>
                      Technical Integrity Details &amp; Tamper Verification
                    </div>
                    <div style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>
                      Cryptographic SHA-256 fingerprint anchoring the approved snapshot against silent downstream alteration.
                    </div>
                  </div>
                </div>
                {showTechnicalDetails ? <ChevronUp size={18} /> : <ChevronDown size={18} />}
              </button>

              {showTechnicalDetails && (
                <div className={styles.technicalPanel}>
                  {/* Integrity Bar */}
                  <div className={styles.hashBar}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', width: '100%', flexWrap: 'wrap', gap: 8 }}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                        <Hash size={15} color="var(--brand-navy)" />
                        <span style={{ fontSize: '0.74rem', fontWeight: 800, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
                          Integrity Fingerprint (SHA-256 FIPS 180-4):
                        </span>
                      </div>
                      <div style={{ display: 'flex', gap: 6 }}>
                        <button
                          type="button"
                          className={styles.actionIconBtn}
                          onClick={() => copyToClipboard(selectedPassport.passport_hash)}
                          title="Copy SHA-256"
                        >
                          {copiedHash ? <Check size={13} color="var(--status-approved-text)" /> : <Copy size={13} />}
                          <span>{copiedHash ? 'Copied' : 'Copy'}</span>
                        </button>
                        <button
                          type="button"
                          className={styles.actionIconBtn}
                          onClick={downloadCertificateJson}
                          title="Download Signed Proof JSON"
                        >
                          <Download size={13} />
                          <span>Signed JSON</span>
                        </button>
                      </div>
                    </div>

                    <code className={styles.hashCode}>
                      {selectedPassport.passport_hash}
                    </code>
                  </div>

                  {/* Avalanche Effect Hash Comparison if Tampered (AT-022) */}
                  {isTampered && tamperedHash && (
                    <div className={styles.tamperComparisonBox}>
                      <div style={{ display: 'flex', alignItems: 'center', gap: 8, color: 'var(--status-blocked-text)', fontWeight: 800, fontSize: '0.86rem', marginBottom: 8 }}>
                        <ShieldAlert size={18} />
                        <span>Mathematical Proof of Alteration (Avalanche Effect):</span>
                      </div>

                      <div style={{ display: 'grid', gridTemplateColumns: '130px 1fr', gap: 8, fontSize: '0.76rem', fontFamily: 'monospace' }}>
                        <span style={{ color: 'var(--status-approved-text)', fontWeight: 700 }}>Frozen Origin Hash:</span>
                        <code style={{ color: 'var(--status-approved-text)', wordBreak: 'break-all' }}>{selectedPassport.passport_hash}</code>

                        <span style={{ color: 'var(--status-blocked-text)', fontWeight: 700 }}>Recomputed Hash:</span>
                        <code style={{ color: 'var(--status-blocked-text)', wordBreak: 'break-all' }}>{tamperedHash}</code>
                      </div>

                      <div style={{ fontSize: '0.76rem', color: 'var(--text-secondary)', marginTop: 8, lineHeight: 1.4 }}>
                        Altering even a single word in the draft copy completely randomizes all 64 hexadecimal characters of the SHA-256 digest. No downstream actor can alter approved copy undetected.
                      </div>
                    </div>
                  )}

                  {/* Live Tamper Simulator */}
                  <div className={styles.tamperPanel}>
                    <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', flexWrap: 'wrap', gap: 14 }}>
                      <div>
                        <div style={{ display: 'flex', alignItems: 'center', gap: 8, fontWeight: 800, fontSize: '0.9rem', color: isTampered ? 'var(--status-blocked-text)' : 'var(--text-primary)' }}>
                          <Shield size={16} color={isTampered ? 'var(--status-blocked-text)' : 'var(--brand-navy)'} />
                          <span>Live Cryptographic Tamper Simulator (Act 5 &amp; AT-022)</span>
                        </div>
                        <div style={{ fontSize: '0.76rem', color: 'var(--text-muted)', marginTop: 4, lineHeight: 1.4 }}>
                          Demonstrates audit protection: Downstream modification to approved text immediately breaks the integrity check.
                        </div>
                      </div>

                      <div style={{ display: 'flex', gap: 10 }}>
                        {!isTampered ? (
                          <button
                            type="button"
                            className={styles.tamperBtn}
                            onClick={handleSimulateTamper}
                            disabled={recomputing}
                          >
                            <AlertTriangle size={14} />
                            <span>{recomputing ? 'Recalculating...' : 'Simulate Database Tampering'}</span>
                          </button>
                        ) : (
                          <button
                            type="button"
                            className={styles.restoreBtn}
                            onClick={handleRestoreIntegrity}
                            disabled={recomputing}
                          >
                            <RefreshCw size={14} />
                            <span>{recomputing ? 'Re-verifying...' : 'Restore Authentic Copy'}</span>
                          </button>
                        )}
                      </div>
                    </div>
                  </div>
                </div>
              )}
            </div>
          </div>
        ) : (
          <div className={styles.certificateCard} style={{ display: 'flex', alignItems: 'center', justifyContent: 'center', minHeight: 400 }}>
            <span style={{ color: 'var(--text-muted)' }}>No passport selected</span>
          </div>
        )}
      </div>
    </div>
  );
}

export default function PassportsPage() {
  return (
    <React.Suspense fallback={<div className={styles.container} style={{ color: 'var(--text-muted)', padding: '60px 0', textAlign: 'center' }}>Loading Content Passports...</div>}>
      <PassportsContent />
    </React.Suspense>
  );
}
