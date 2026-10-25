'use client';

import React, { useState } from 'react';
import { PolicyCard } from '@/types/policy';
import styles from './PolicyDetailDrawer.module.css';

interface PolicyDetailDrawerProps {
  policy: PolicyCard | null;
  onClose: () => void;
  onEdit: (policy: PolicyCard) => void;
  onArchive: (id: string) => void;
}

export const PolicyDetailDrawer: React.FC<PolicyDetailDrawerProps> = ({
  policy,
  onClose,
  onEdit,
  onArchive,
}) => {
  const [copied, setCopied] = useState(false);

  if (!policy) return null;

  const sourceQuote = (policy.metadata.quote as string) || (policy.rules[0] as { quote?: string })?.quote || '';

  const handleCopyJson = () => {
    navigator.clipboard.writeText(JSON.stringify(policy, null, 2));
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  return (
    <div className={styles.overlay} onClick={onClose} role="dialog" aria-modal="true" aria-labelledby="drawer-title">
      <div className={styles.drawer} onClick={(e) => e.stopPropagation()}>
        <div className={styles.header}>
          <div className={styles.headerMeta}>
            <span className={styles.idBadge}>{policy.id}</span>
            <span className={styles.versionBadge}>v{policy.version}</span>
            <span style={{ fontSize: '0.8rem', color: policy.status === 'approved' ? '#10b981' : '#f59e0b', fontWeight: 600 }}>
              ● {policy.status ? policy.status.toUpperCase() : 'APPROVED'}
            </span>
          </div>
          <button type="button" className={styles.btnClose} onClick={onClose} aria-label="Close drawer">
            <svg width="20" height="20" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <line x1="18" y1="6" x2="6" y2="18" />
              <line x1="6" y1="6" x2="18" y2="18" />
            </svg>
          </button>
        </div>

        <div className={styles.body}>
          <div className={styles.titleSection}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, color: '#38bdf8', textTransform: 'uppercase' }}>
              Category: {policy.category.toUpperCase()}
            </span>
            <h2 id="drawer-title" className={styles.title}>{policy.title}</h2>
          </div>

          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <path d="M14 2H6a2 2 0 0 0-2 2v16a2 2 0 0 0 2 2h12a2 2 0 0 0 2-2V8z" />
                <polyline points="14 2 14 8 20 8" />
              </svg>
              <span>Approved Policy Content</span>
            </div>
            <div className={styles.contentBox}>{policy.content}</div>
          </div>

          {sourceQuote && (
            <div className={styles.section}>
              <div className={styles.sectionHeader} style={{ color: '#38bdf8' }}>
                <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                  <path d="M12 22s8-4 8-10V5l-8-3-8 3v7c0 6 8 10 8 10z" />
                </svg>
                <span>Verified Source Quotation (&ldquo;No receipt, no flag&rdquo;)</span>
              </div>
              <div className={styles.evidenceBox}>
                <blockquote className={styles.evidenceQuote}>&ldquo;{sourceQuote}&rdquo;</blockquote>
                <span style={{ fontSize: '0.75rem', color: '#94a3b8' }}>
                  Enforced by the Evidence Verifier: Every reported finding must trace back to this exact text.
                </span>
              </div>
            </div>
          )}

          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
                <circle cx="12" cy="12" r="10" />
                <line x1="12" y1="16" x2="12" y2="12" />
                <line x1="12" y1="8" x2="12.01" y2="8" />
              </svg>
              <span>Structured Engine Rules ({policy.rules.length})</span>
            </div>
            <div className={styles.rulesList}>
              {policy.rules.map((rule, idx) => {
                const r = rule as Record<string, unknown>;
                return (
                  <div key={idx} className={styles.ruleItem}>
                    <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                      <strong style={{ color: '#38bdf8' }}>Rule #{idx + 1} ({String(r.type || 'standard')})</strong>
                    </div>
                    {Boolean(r.prohibited) && (
                      <div>
                        <strong>Prohibited:</strong> <code style={{ color: '#f43f5e' }}>&quot;{String(r.prohibited)}&quot;</code> &rarr;{' '}
                        <strong>Required:</strong> <code style={{ color: '#10b981' }}>&quot;{String(r.replacement)}&quot;</code>
                      </div>
                    )}
                    {Boolean(r.metric) && (
                      <div>
                        <strong>Metric:</strong> {String(r.metric)} | <strong>Cap:</strong> {String(r.value)} {String(r.unit || '')} ({String(r.limit_type || 'max')})
                      </div>
                    )}
                    {Boolean(r.valid_until) && (
                      <div>
                        <strong>Expiration Date:</strong> <span style={{ color: '#f59e0b' }}>{String(r.valid_until)}</span> (Inclusive boundary)
                      </div>
                    )}
                    {Boolean(r.requires_evidence) && (
                      <div>
                        <strong>Substantiation:</strong> Legal clearance &amp; clinical evidence mandatory
                      </div>
                    )}
                  </div>
                );
              })}
            </div>
          </div>

          <div className={styles.section}>
            <div className={styles.sectionHeader}>
              <span>Governance &amp; Provenance Metadata</span>
            </div>
            <div className={styles.metaGrid}>
              <div className={styles.metaCard}>
                <span className={styles.metaLabel}>Brand Reference</span>
                <span className={styles.metaValue}>{String(policy.metadata.brand_name || policy.metadata.brand_id || 'Apex Health')}</span>
              </div>
              <div className={styles.metaCard}>
                <span className={styles.metaLabel}>Author / Owner</span>
                <span className={styles.metaValue}>{String(policy.metadata.author || 'Governance Committee')}</span>
              </div>
              <div className={styles.metaCard}>
                <span className={styles.metaLabel}>Approved By</span>
                <span className={styles.metaValue}>{String(policy.metadata.approved_by || 'Legal & Brand Director')}</span>
              </div>
              <div className={styles.metaCard}>
                <span className={styles.metaLabel}>Last Modified</span>
                <span className={styles.metaValue}>
                  {policy.updated_at ? new Date(policy.updated_at).toLocaleString() : 'Active v' + policy.version}
                </span>
              </div>
            </div>
          </div>
        </div>

        <div className={styles.footer}>
          <button type="button" className={styles.btnCopyJson} onClick={handleCopyJson}>
            {copied ? '✓ JSON Copied' : 'Copy JSON'}
          </button>
          <div className={styles.btnActionGroup}>
            {policy.status !== 'archived' && (
              <button
                type="button"
                className={styles.btnArchive}
                onClick={() => {
                  if (confirm(`Are you sure you want to archive policy ${policy.id}? It will be excluded from active scans.`)) {
                    onArchive(policy.id);
                  }
                }}
              >
                Archive Policy
              </button>
            )}
            <button
              type="button"
              className={styles.btnPrimary}
              onClick={() => onEdit(policy)}
            >
              Edit Policy
            </button>
          </div>
        </div>
      </div>
    </div>
  );
};
