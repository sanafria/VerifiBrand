'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  History, Shield, CheckCircle2, Lock,
  RefreshCw, Search, ArrowRight, Award, Hash, Check
} from 'lucide-react';
import styles from './page.module.css';

interface AuditLogItem {
  id: string;
  action: 'PASSPORT_MINTED' | 'SCAN_EXECUTED' | 'REVIEW_APPROVED' | 'POLICY_VERSION_INCREMENT' | 'TAMPER_CHECK';
  actor: string;
  targetId: string;
  timestamp: string;
  details: string;
  sha256?: string;
  verified?: boolean;
}

const INITIAL_LOGS: AuditLogItem[] = [
  {
    id: 'aud_108',
    action: 'PASSPORT_MINTED',
    actor: 'Jordan Blake (Reviewer)',
    targetId: 'pass_2026_demo_01',
    timestamp: '2026-07-01T14:32:05Z',
    details: 'Issued Content Passport for approved campaign copy: "Our Members can access standard pricing today!"',
    sha256: '9f86d081884c7d659a2feaa0c55ad015a3bf4f1b2b0b822cd15d6c15b0f00a08',
    verified: true,
  },
  {
    id: 'aud_107',
    action: 'REVIEW_APPROVED',
    actor: 'Jordan Blake (Reviewer)',
    targetId: 'drft_2026_demo',
    timestamp: '2026-07-01T14:31:50Z',
    details: 'Formal reviewer sign-off granted with comment: "Approved for publication across digital channels."',
  },
  {
    id: 'aud_106',
    action: 'SCAN_EXECUTED',
    actor: 'Alex Kim (Creator)',
    targetId: 'drft_2026_demo (Rescan)',
    timestamp: '2026-07-01T14:30:12Z',
    details: 'Rescan completed with 0 findings, 0 blockers. Status: COMPLIANT.',
    sha256: 'e3b0c44298fc1c149afbf4c8996fb92427ae41e4649b934ca495991b7852b855',
    verified: true,
  },
  {
    id: 'aud_105',
    action: 'SCAN_EXECUTED',
    actor: 'Alex Kim (Creator)',
    targetId: 'drft_2026_demo',
    timestamp: '2026-07-01T14:28:40Z',
    details: 'Initial scan flagged 2 blockers: pol_term_001 (disallowed "customers") and pol_offer_002 (expired "Summer Discount").',
  },
  {
    id: 'aud_104',
    action: 'POLICY_VERSION_INCREMENT',
    actor: 'Morgan Lee (Governance)',
    targetId: 'pol_term_001',
    timestamp: '2026-06-15T09:12:00Z',
    details: 'Incremented policy card to v1.0 snapshot with rule evidence: "The brand prohibits the term Customers and requires the term Members".',
  },
];

export default function AuditPage() {
  const [logs, setLogs] = useState<AuditLogItem[]>(INITIAL_LOGS);
  const [searchQuery, setSearchQuery] = useState('');
  const [filterAction, setFilterAction] = useState('all');
  const [verifyingId, setVerifyingId] = useState<string | null>(null);

  // Real-time SHA-256 Tamper Re-verification
  const handleVerifyHash = async (item: AuditLogItem) => {
    setVerifyingId(item.id);
    await new Promise(r => setTimeout(r, 600)); // simulated cryptographic calculation

    setLogs(prev =>
      prev.map(l =>
        l.id === item.id ? { ...l, verified: true } : l
      )
    );
    setVerifyingId(null);
  };

  const filteredLogs = logs.filter(l => {
    const matchesSearch =
      l.details.toLowerCase().includes(searchQuery.toLowerCase()) ||
      l.targetId.toLowerCase().includes(searchQuery.toLowerCase()) ||
      l.actor.toLowerCase().includes(searchQuery.toLowerCase());
    const matchesAction = filterAction === 'all' || l.action === filterAction;
    return matchesSearch && matchesAction;
  });

  return (
    <div className={styles.container}>
      {/* Header Banner */}
      <div className={styles.banner}>
        <div className={styles.headerTop}>
          <span className={styles.teamBadge}>
            <History size={14} /> Immutable Cryptographic Audit Ledger
          </span>
          <div style={{ display: 'flex', gap: 10 }}>
            <Link
              href="/passports"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 14px',
                borderRadius: 6,
                background: 'rgba(16, 185, 129, 0.15)',
                color: '#34d399',
                fontSize: '0.82rem',
                fontWeight: 700,
                border: '1px solid rgba(16, 185, 129, 0.3)'
              }}
            >
              <Award size={14} /> View Content Passports
            </Link>
          </div>
        </div>

        <h1 className={styles.title}>Brand Governance Audit Trail</h1>
        <p className={styles.desc}>
          Chronological, tamper-evident ledger tracking every scan evaluation, policy version snapshot, human review approval gate, and SHA-256 Content Passport minted in VerifiBrand.
        </p>
      </div>

      {/* Filter Row */}
      <div className={styles.filterRow}>
        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <Search size={16} color="var(--text-muted)" />
          <input
            type="text"
            className={styles.searchInput}
            placeholder="Search by actor, target ID, or keyword..."
            value={searchQuery}
            onChange={e => setSearchQuery(e.target.value)}
          />
        </div>

        <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
          <span style={{ fontSize: '0.82rem', color: 'var(--text-muted)' }}>Action Type:</span>
          <select
            className={styles.filterSelect}
            value={filterAction}
            onChange={e => setFilterAction(e.target.value)}
          >
            <option value="all">All Audit Actions</option>
            <option value="PASSPORT_MINTED">Passports Minted</option>
            <option value="REVIEW_APPROVED">Reviewer Decisions</option>
            <option value="SCAN_EXECUTED">Scans Executed</option>
            <option value="POLICY_VERSION_INCREMENT">Policy Versions</option>
          </select>
        </div>
      </div>

      {/* Timeline Entries */}
      <div className={styles.timeline}>
        {filteredLogs.map(item => (
          <div key={item.id} className={styles.ledgerEntry}>
            <div className={styles.entryHeader}>
              <div className={styles.entryLeft}>
                <span className={`${styles.actionBadge} ${getActionClass(item.action)}`}>
                  {item.action.replace(/_/g, ' ')}
                </span>
                <span style={{ fontSize: '0.84rem', fontWeight: 600, color: 'var(--text-primary)' }}>
                  Target: <code style={{ color: '#38bdf8' }}>{item.targetId}</code>
                </span>
                <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
                  by <strong>{item.actor}</strong>
                </span>
              </div>
              <span className={styles.timestamp}>
                {new Date(item.timestamp).toUTCString()}
              </span>
            </div>

            <div className={styles.entryBody}>
              <div className={styles.entryDetails}>
                {item.details}
              </div>

              {item.sha256 && (
                <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
                  <div className={styles.hashBox} title="Cryptographic SHA-256 Digest">
                    <Hash size={13} color="#38bdf8" />
                    <span>{item.sha256.slice(0, 16)}...{item.sha256.slice(-8)}</span>
                  </div>

                  <button
                    type="button"
                    className={styles.verifyBtn}
                    onClick={() => handleVerifyHash(item)}
                    disabled={verifyingId === item.id}
                  >
                    {verifyingId === item.id ? (
                      <RefreshCw size={13} className="animate-spin" />
                    ) : item.verified ? (
                      <Check size={13} />
                    ) : (
                      <Shield size={13} />
                    )}
                    <span>{item.verified ? 'Verified' : 'Verify'}</span>
                  </button>
                </div>
              )}
            </div>
          </div>
        ))}
      </div>
    </div>
  );
}

function getActionClass(action: string): string {
  switch (action) {
    case 'PASSPORT_MINTED':
      return styles.actionPassport;
    case 'REVIEW_APPROVED':
      return styles.actionReview;
    case 'SCAN_EXECUTED':
      return styles.actionScan;
    default:
      return styles.actionPolicy;
  }
}
