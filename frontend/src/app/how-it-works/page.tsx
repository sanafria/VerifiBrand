'use client';

import React from 'react';
import Link from 'next/link';
import {
  Shield, BookOpen, Layers, CheckCircle2, ArrowRight,
  UserCheck, AlertTriangle, FileText, Check, Clock, RotateCcw
} from 'lucide-react';

export default function HowItWorksPage() {
  return (
    <div style={{ maxWidth: 'var(--max-width)', margin: '0 auto', padding: '48px 24px 80px' }}>
      {/* Header */}
      <div style={{ textAlign: 'center', maxWidth: 760, margin: '0 auto 60px' }}>
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
          <Shield size={14} />
          <span>Product Workflow</span>
        </div>

        <h1 style={{
          fontFamily: 'var(--font-heading)',
          fontSize: '3rem',
          color: 'var(--brand-navy)',
          marginBottom: 16,
          fontWeight: 400
        }}>
          How VerifiBrand Works
        </h1>

        <p style={{ fontSize: '1.15rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          A shared review layer connecting your approved guidelines, content drafts, and authorized human approvals into one defensible workflow.
        </p>
      </div>

      {/* 7 Workflow Steps Detailed */}
      <div style={{ display: 'flex', flexDirection: 'column', gap: 32, maxWidth: 900, margin: '0 auto 64px' }}>
        {/* Step 1 */}
        <div className="bl-card" style={{ padding: '32px', display: 'flex', gap: 24, alignItems: 'flex-start' }}>
          <div style={{
            fontFamily: 'var(--font-heading)',
            fontSize: '2.4rem',
            color: 'var(--brand-gold)',
            lineHeight: 1,
            flexShrink: 0,
            width: 50
          }}>
            01
          </div>
          <div>
            <h2 style={{ fontSize: '1.3rem', color: 'var(--brand-navy)', marginBottom: 8 }}>
              Define the approved truth
            </h2>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 14 }}>
              Brand guidelines, claim substantiations, terminology rules, and active promotional calendars are codified into versioned <strong>Policy Cards</strong>. When policies change, versions increment automatically, preserving a snapshot of what was active at every point in time.
            </p>
            <div style={{ background: '#F8F5EE', border: '1px solid var(--border-light)', padding: '10px 14px', borderRadius: 6, fontSize: '0.85rem', color: 'var(--brand-navy)' }}>
              <strong>Artifacts:</strong> Policy Cards, Claims Register, Terminology Allow/Deny Lists, Approved Assets.
            </div>
          </div>
        </div>

        {/* Step 2 */}
        <div className="bl-card" style={{ padding: '32px', display: 'flex', gap: 24, alignItems: 'flex-start' }}>
          <div style={{
            fontFamily: 'var(--font-heading)',
            fontSize: '2.4rem',
            color: 'var(--brand-gold)',
            lineHeight: 1,
            flexShrink: 0,
            width: 50
          }}>
            02
          </div>
          <div>
            <h2 style={{ fontSize: '1.3rem', color: 'var(--brand-navy)', marginBottom: 8 }}>
              Submit a content draft
            </h2>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 14 }}>
              Content creators or agencies submit drafts across channels—social posts, email blasts, banner ad copy, or PDF briefs. Drafts are assigned a unique Content ID (e.g. <code>CMP-1042</code>) and versioned.
            </p>
            <div style={{ background: '#F8F5EE', border: '1px solid var(--border-light)', padding: '10px 14px', borderRadius: 6, fontSize: '0.85rem', color: 'var(--brand-navy)' }}>
              <strong>Formats supported:</strong> Plain text, rich copy, markdown, and visual images via OCR extraction.
            </div>
          </div>
        </div>

        {/* Step 3 */}
        <div className="bl-card" style={{ padding: '32px', display: 'flex', gap: 24, alignItems: 'flex-start' }}>
          <div style={{
            fontFamily: 'var(--font-heading)',
            fontSize: '2.4rem',
            color: 'var(--brand-gold)',
            lineHeight: 1,
            flexShrink: 0,
            width: 50
          }}>
            03
          </div>
          <div>
            <h2 style={{ fontSize: '1.3rem', color: 'var(--brand-navy)', marginBottom: 8 }}>
              Assisted analysis &amp; deterministic checks
            </h2>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 14 }}>
              VerifiBrand combines deterministic rule matching (date expirations, prohibited vocabulary, discount caps) with AI-assisted linguistic analysis. AI responses are strictly treated as <em>candidate findings</em>—never final, unchallengeable decisions.
            </p>
            <div style={{ background: '#F8F5EE', border: '1px solid var(--border-light)', padding: '10px 14px', borderRadius: 6, fontSize: '0.85rem', color: 'var(--brand-navy)' }}>
              <strong>Pipeline:</strong> Permission validation &rarr; Policy retrieval &rarr; Deterministic checks &rarr; Assisted analysis.
            </div>
          </div>
        </div>

        {/* Step 4 */}
        <div className="bl-card" style={{ padding: '32px', display: 'flex', gap: 24, alignItems: 'flex-start' }}>
          <div style={{
            fontFamily: 'var(--font-heading)',
            fontSize: '2.4rem',
            color: 'var(--brand-gold)',
            lineHeight: 1,
            flexShrink: 0,
            width: 50
          }}>
            04
          </div>
          <div>
            <h2 style={{ fontSize: '1.3rem', color: 'var(--brand-navy)', marginBottom: 8 }}>
              Explain findings with source evidence
            </h2>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 14 }}>
              Every flagged issue includes what was detected, why it matters, and a verbatim excerpt from the registered policy. Creators and reviewers see the exact citation—ensuring complete transparency and mutual understanding.
            </p>
            <div style={{ background: '#F8F5EE', border: '1px solid var(--border-light)', padding: '10px 14px', borderRadius: 6, fontSize: '0.85rem', color: 'var(--brand-navy)' }}>
              <strong>Standard:</strong> Policy ID + Active Version Number + Verbatim Quotation + Last Updated Date.
            </div>
          </div>
        </div>

        {/* Step 5 */}
        <div className="bl-card" style={{ padding: '32px', display: 'flex', gap: 24, alignItems: 'flex-start' }}>
          <div style={{
            fontFamily: 'var(--font-heading)',
            fontSize: '2.4rem',
            color: 'var(--brand-gold)',
            lineHeight: 1,
            flexShrink: 0,
            width: 50
          }}>
            05
          </div>
          <div>
            <h2 style={{ fontSize: '1.3rem', color: 'var(--brand-navy)', marginBottom: 8 }}>
              Revise or respond with suggestions
            </h2>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 14 }}>
              VerifiBrand offers context-aware corrections designed to preserve the creator&rsquo;s original marketing intent. Creators can apply suggestions in one click, edit manually, or submit with an explanation.
            </p>
            <div style={{ background: '#F8F5EE', border: '1px solid var(--border-light)', padding: '10px 14px', borderRadius: 6, fontSize: '0.85rem', color: 'var(--brand-navy)' }}>
              <strong>Actions:</strong> Apply suggested correction &bull; Edit manually &bull; Retain original for reviewer consideration.
            </div>
          </div>
        </div>

        {/* Step 6 */}
        <div className="bl-card" style={{ padding: '32px', display: 'flex', gap: 24, alignItems: 'flex-start' }}>
          <div style={{
            fontFamily: 'var(--font-heading)',
            fontSize: '2.4rem',
            color: 'var(--brand-gold)',
            lineHeight: 1,
            flexShrink: 0,
            width: 50
          }}>
            06
          </div>
          <div>
            <h2 style={{ fontSize: '1.3rem', color: 'var(--brand-navy)', marginBottom: 8 }}>
              Authorised human approval &amp; recorded overrides
            </h2>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 14 }}>
              AI never publishes autonomously. An authorized human reviewer inspects the draft, evaluates any open findings or creator explanations, and records a definitive decision: <strong>APPROVED</strong>, <strong>CHANGES REQUESTED</strong>, or <strong>APPROVED WITH OVERRIDE</strong> (recording a mandatory justification).
            </p>
            <div style={{ background: '#F8F5EE', border: '1px solid var(--border-light)', padding: '10px 14px', borderRadius: 6, fontSize: '0.85rem', color: 'var(--brand-navy)' }}>
              <strong>Governance guarantee:</strong> No content is approved without a named reviewer and timestamped audit entry.
            </div>
          </div>
        </div>

        {/* Step 7 */}
        <div className="bl-card" style={{ padding: '32px', display: 'flex', gap: 24, alignItems: 'flex-start' }}>
          <div style={{
            fontFamily: 'var(--font-heading)',
            fontSize: '2.4rem',
            color: 'var(--brand-gold)',
            lineHeight: 1,
            flexShrink: 0,
            width: 50
          }}>
            07
          </div>
          <div>
            <h2 style={{ fontSize: '1.3rem', color: 'var(--brand-navy)', marginBottom: 8 }}>
              Content Passport &amp; traceable audit record
            </h2>
            <p style={{ color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 14 }}>
              Upon approval, VerifiBrand generates a <strong>Content Passport</strong>. This verifiable certificate details the content snapshot, policy versions utilized, reviewer credentials, and cryptographic fingerprint—giving distribution channels proof of compliance before publication.
            </p>
            <div style={{ background: '#F8F5EE', border: '1px solid var(--border-light)', padding: '10px 14px', borderRadius: 6, fontSize: '0.85rem', color: 'var(--brand-navy)' }}>
              <strong>Verification:</strong> Exportable certificate seal, verifiable SHA-256 fingerprint, and audit trail link.
            </div>
          </div>
        </div>
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
          Experience the workflow in action.
        </h3>
        <p style={{ color: '#CBD5E1', marginBottom: 24, fontSize: '1.05rem' }}>
          Walk through the Northstar Membership sample campaign or test your own draft in the workspace.
        </p>
        <div style={{ display: 'flex', gap: 14, justifyContent: 'center', flexWrap: 'wrap' }}>
          <Link href="/demo-preview" style={{ background: '#FFFFFF', color: '#1E293B', padding: '10px 22px', borderRadius: 6, fontWeight: 700 }}>
            View sample review
          </Link>
          <Link href="/workspace" style={{ background: 'transparent', border: '1px solid rgba(255, 255, 255, 0.4)', color: '#FFFFFF', padding: '10px 22px', borderRadius: 6, fontWeight: 600 }}>
            Open workspace
          </Link>
        </div>
      </div>
    </div>
  );
}
