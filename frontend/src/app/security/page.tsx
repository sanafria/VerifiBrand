'use client';

import React from 'react';
import Link from 'next/link';
import {
  Shield, Lock, Key, Server, UserCheck, Eye,
  CheckCircle2, AlertTriangle, ArrowRight, FileText
} from 'lucide-react';

export default function SecurityPage() {
  return (
    <div style={{ maxWidth: 'var(--max-width)', margin: '0 auto', padding: '48px 24px 80px' }}>
      {/* Header */}
      <div style={{ textAlign: 'center', maxWidth: 740, margin: '0 auto 60px' }}>
        <div style={{
          display: 'inline-flex',
          alignItems: 'center',
          gap: 6,
          background: 'var(--brand-gold-subtle)',
          color: 'var(--brand-gold)',
          padding: '4px 14px',
          borderRadius: 'var(--radius-full)',
          fontSize: '0.82rem',
          fontWeight: 600,
          marginBottom: 16
        }}>
          <Lock size={14} />
          <span>Trust &amp; Governance</span>
        </div>

        <h1 style={{
          fontFamily: 'var(--font-heading)',
          fontSize: '3rem',
          color: 'var(--brand-navy)',
          marginBottom: 16,
          fontWeight: 400
        }}>
          Security &amp; Responsible Design
        </h1>

        <p style={{ fontSize: '1.15rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          Designed with privacy, data minimisation, and responsible AI principles. Built for enterprise brand teams managing sensitive pre-publication campaigns.
        </p>
      </div>

      {/* 5 Core Pillars */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(340px, 1fr))', gap: 28, marginBottom: 48 }}>
        <div className="bl-card" style={{ padding: '28px' }}>
          <div style={{ width: 40, height: 40, borderRadius: 8, background: '#F8F5EE', color: 'var(--brand-navy)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
            <UserCheck size={20} />
          </div>
          <h2 style={{ fontSize: '1.2rem', color: 'var(--brand-navy)', marginBottom: 8, fontWeight: 700 }}>
            Role-Aware Workflow &amp; Access Controls
          </h2>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            The prototype uses role-aware review states so creators and reviewers follow different paths. Content creators cannot self-approve drafts; formal sign-off requires designated Compliance Officer or Brand Manager credentials.
          </p>
        </div>

        <div className="bl-card" style={{ padding: '28px' }}>
          <div style={{ width: 40, height: 40, borderRadius: 8, background: '#F8F5EE', color: 'var(--brand-navy)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
            <Server size={20} />
          </div>
          <h2 style={{ fontSize: '1.2rem', color: 'var(--brand-navy)', marginBottom: 8, fontWeight: 700 }}>
            Server-Side Provider Isolation
          </h2>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            The browser never calls AI providers or external APIs directly. AI-service credentials, API tokens, and secrets are managed server-side rather than exposed in client-side code.
          </p>
        </div>

        <div className="bl-card" style={{ padding: '28px' }}>
          <div style={{ width: 40, height: 40, borderRadius: 8, background: '#F8F5EE', color: 'var(--brand-navy)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
            <Eye size={20} />
          </div>
          <h2 style={{ fontSize: '1.2rem', color: 'var(--brand-navy)', marginBottom: 8, fontWeight: 700 }}>
            Source-Linked Verification
          </h2>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            Every finding cites an authoritative, registered policy ID, active version snapshot, and exact verbatim quotation. We provide source-linked explanations rather than unsupported black-box scores.
          </p>
        </div>

        <div className="bl-card" style={{ padding: '28px' }}>
          <div style={{ width: 40, height: 40, borderRadius: 8, background: '#F8F5EE', color: 'var(--brand-navy)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
            <Shield size={20} />
          </div>
          <h2 style={{ fontSize: '1.2rem', color: 'var(--brand-navy)', marginBottom: 8, fontWeight: 700 }}>
            Human Decision Authority
          </h2>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            AI performs text extraction, candidate issue classification, and suggests alternative phrasing. Final publication decisions, rejections, and documented overrides remain strictly under human control.
          </p>
        </div>

        <div className="bl-card" style={{ padding: '28px' }}>
          <div style={{ width: 40, height: 40, borderRadius: 8, background: '#F8F5EE', color: 'var(--brand-navy)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
            <Key size={20} />
          </div>
          <h2 style={{ fontSize: '1.2rem', color: 'var(--brand-navy)', marginBottom: 8, fontWeight: 700 }}>
            Traceable Content Passports
          </h2>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            Approved versions are stamped with a cryptographic SHA-256 fingerprint linking the content version, active policy rules, reviewer ID, and timestamp in a tamper-evident audit trail.
          </p>
        </div>

        <div className="bl-card" style={{ padding: '28px' }}>
          <div style={{ width: 40, height: 40, borderRadius: 8, background: '#F8F5EE', color: 'var(--brand-navy)', display: 'flex', alignItems: 'center', justifyContent: 'center', marginBottom: 16 }}>
            <AlertTriangle size={20} />
          </div>
          <h2 style={{ fontSize: '1.2rem', color: 'var(--brand-navy)', marginBottom: 8, fontWeight: 700 }}>
            Graceful Failure Resilience
          </h2>
          <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
            If external AI analysis is temporarily unavailable, VerifiBrand never falsely reports &ldquo;No issues found.&rdquo; Deterministic checks run independently and pending statuses are clearly communicated.
          </p>
        </div>
      </div>

      {/* Prototype Scope & Limitation Statement */}
      <div style={{
        background: '#FFF5D9',
        border: '1px solid #E8C76A',
        borderRadius: 8,
        padding: '16px 22px',
        maxWidth: 860,
        margin: '0 auto 40px',
        display: 'flex',
        alignItems: 'flex-start',
        gap: 12
      }}>
        <AlertTriangle size={18} color="#8A5A00" style={{ flexShrink: 0, marginTop: 2 }} />
        <div style={{ fontSize: '0.88rem', color: '#6B4E00', lineHeight: 1.55 }}>
          <strong>Prototype Transparency Note:</strong> This hackathon prototype is designed to demonstrate the governed review workflow. Production deployment in an enterprise environment would incorporate additional organizational controls, extended retention policies, and formal security audits.
        </div>
      </div>

      {/* Internal Architecture Callout (Section 17) */}
      <div style={{
        background: '#F8F5EE',
        border: '1px solid var(--border-light)',
        borderRadius: 12,
        padding: '32px',
        maxWidth: 860,
        margin: '0 auto 64px'
      }}>
        <h3 style={{ fontSize: '1.25rem', color: 'var(--brand-navy)', marginBottom: 12, fontWeight: 700 }}>
          Data Handling Principles
        </h3>
        <p style={{ fontSize: '0.95rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 16 }}>
          VerifiBrand operates on a principle of data minimisation:
        </p>
        <ul style={{ listStyle: 'disc', paddingLeft: 24, display: 'flex', flexDirection: 'column', gap: 8, fontSize: '0.9rem', color: 'var(--brand-navy)' }}>
          <li>Only content submitted for review is analyzed.</li>
          <li>Unnecessary personal identifiable information is stripped before external processing.</li>
          <li>Deterministic rule checks run prior to expensive analysis calls.</li>
          <li>Responses are cached by content hash and policy version to prevent duplicate external requests.</li>
        </ul>
      </div>

      {/* CTA Box */}
      <div style={{
        background: '#1E293B',
        color: '#FFFFFF',
        borderRadius: 12,
        padding: '40px',
        textAlign: 'center',
        maxWidth: 800,
        margin: '0 auto'
      }}>
        <h3 style={{ fontFamily: 'var(--font-heading)', fontSize: '2rem', marginBottom: 12, fontWeight: 400 }}>
          Audit the review process yourself.
        </h3>
        <p style={{ color: '#CBD5E1', marginBottom: 24, fontSize: '1.05rem' }}>
          Inspect the chronological audit trail and Content Passports in the live workspace.
        </p>
        <div style={{ display: 'flex', gap: 14, justifyContent: 'center' }}>
          <Link href="/audit" style={{ background: '#FFFFFF', color: '#1E293B', padding: '12px 24px', borderRadius: 6, fontWeight: 700 }}>
            Open audit trail
          </Link>
          <Link href="/workspace" style={{ background: 'transparent', border: '1px solid rgba(255, 255, 255, 0.4)', color: '#FFFFFF', padding: '12px 24px', borderRadius: 6, fontWeight: 600 }}>
            Open workspace
          </Link>
        </div>
      </div>
    </div>
  );
}
