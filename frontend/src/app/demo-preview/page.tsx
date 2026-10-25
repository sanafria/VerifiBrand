'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  Shield, CheckCircle2, ArrowRight, BookOpen, Layers,
  FileText, AlertTriangle, Eye, Check, Clock, UserCheck,
  RotateCcw, ExternalLink, Award, Sparkles, Hash
} from 'lucide-react';

export default function DemoPreviewPage() {
  const [suggestionApplied, setSuggestionApplied] = useState(false);
  const [isApproved, setIsApproved] = useState(false);

  const handleApplySuggestion = () => {
    setSuggestionApplied(true);
  };

  const handleRevert = () => {
    setSuggestionApplied(false);
    setIsApproved(false);
  };

  const handleApprove = () => {
    setIsApproved(true);
  };

  return (
    <div style={{ maxWidth: 'var(--max-width)', margin: '0 auto', padding: '40px 24px 80px' }}>
      {/* Header */}
      <div style={{ textAlign: 'center', maxWidth: 760, margin: '0 auto 40px' }}>
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
          marginBottom: 12
        }}>
          <Eye size={14} />
          <span>Interactive Sample Review</span>
        </div>

        <h1 style={{
          fontFamily: 'var(--font-heading)',
          fontSize: '2.8rem',
          color: 'var(--brand-navy)',
          marginBottom: 12,
          fontWeight: 400
        }}>
          Sample Review Workspace
        </h1>

        <p style={{ fontSize: '1.05rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          Experience the 3-panel review workspace using the official <strong>Northstar Membership</strong> scenario.
        </p>

        {/* Scenario Metadata Bar */}
        <div style={{
          background: '#FFFFFF',
          border: '1px solid var(--border-light)',
          borderRadius: 8,
          padding: '10px 18px',
          display: 'inline-flex',
          gap: 18,
          fontSize: '0.85rem',
          color: 'var(--brand-navy)',
          marginTop: 16,
          flexWrap: 'wrap',
          justifyContent: 'center'
        }}>
          <span>Organisation: <strong>Northstar Membership</strong></span>
          <span>&bull;</span>
          <span>Campaign: <strong>Summer Membership Campaign</strong></span>
          <span>&bull;</span>
          <span>Creator: <strong>Sana</strong></span>
          <span>&bull;</span>
          <span>Reviewer: <strong>Haany</strong></span>
        </div>
      </div>

      {/* 3-Panel Review Workspace Layout (Section 12) */}
      <div style={{
        display: 'grid',
        gridTemplateColumns: '1fr 1.15fr 1fr',
        gap: 20,
        marginBottom: 40,
        alignItems: 'start'
      }}>
        {/* PANEL 1: Content Preview */}
        <div className="bl-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
              1. Content Preview
            </span>
            <span style={{ fontSize: '0.75rem', background: '#F8F5EE', padding: '2px 8px', borderRadius: 4, color: 'var(--brand-navy)' }}>
              {suggestionApplied ? 'Draft v2' : 'Draft v1'}
            </span>
          </div>

          <div style={{
            background: '#FDFBF7',
            border: '1px solid var(--border-subtle)',
            borderRadius: 8,
            padding: '18px',
            fontSize: '0.98rem',
            lineHeight: 1.7,
            color: 'var(--brand-navy)',
            marginBottom: 20,
            minHeight: 180
          }}>
            Celebrate summer with Northstar! We are proud to be{' '}
            {suggestionApplied ? (
              <span style={{
                background: '#E8F3EC',
                borderBottom: '2px solid #166534',
                padding: '2px 6px',
                borderRadius: 4,
                fontWeight: 600,
                color: '#166534'
              }}>
                trusted by creators across India
              </span>
            ) : (
              <span style={{
                background: '#FFF5D9',
                borderBottom: '2px solid #B58A1F',
                padding: '2px 6px',
                borderRadius: 4,
                fontWeight: 600,
                color: '#92400E'
              }}>
                India’s No. 1 platform for creators
              </span>
            )}
            . Existing members receive 20% off all renewal packages through September.
          </div>

          <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', display: 'flex', flexDirection: 'column', gap: 6 }}>
            <div>Target Channels: <strong>Social &bull; Ads &bull; Website</strong></div>
            <div>Content ID: <code>CMP-1042</code></div>
            <div>Current State:{' '}
              {isApproved ? (
                <strong style={{ color: '#166534' }}>APPROVED</strong>
              ) : suggestionApplied ? (
                <strong style={{ color: '#B58A1F' }}>REVISED (READY FOR APPROVAL)</strong>
              ) : (
                <strong style={{ color: '#92400E' }}>FINDING DETECTED</strong>
              )}
            </div>
          </div>
        </div>

        {/* PANEL 2: Findings */}
        <div className="bl-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
              2. Findings
            </span>
            <span style={{
              fontSize: '0.72rem',
              fontWeight: 700,
              background: suggestionApplied ? '#E8F3EC' : 'var(--status-warning-bg)',
              color: suggestionApplied ? '#166534' : 'var(--status-warning-text)',
              padding: '2px 8px',
              borderRadius: 4
            }}>
              {suggestionApplied ? 'RESOLVED' : 'HIGH SEVERITY · OPEN'}
            </span>
          </div>

          <h3 style={{ fontSize: '1.1rem', color: 'var(--brand-navy)', marginBottom: 8, fontWeight: 700 }}>
            Unsupported promotional claim
          </h3>

          <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.55, marginBottom: 16 }}>
            <strong>Why it matters:</strong> This superlative claim requires an approved evidence reference that is not currently linked to the draft version.
          </div>

          {/* Suggested Correction Box */}
          <div style={{
            background: '#F8F5EE',
            border: '1px solid var(--border-light)',
            borderRadius: 8,
            padding: '14px',
            marginBottom: 20
          }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--brand-gold)', textTransform: 'uppercase', marginBottom: 4 }}>
              Suggested Correction
            </div>
            <div style={{ fontSize: '0.92rem', color: 'var(--brand-navy)', fontWeight: 600 }}>
              &ldquo;Trusted by creators across India.&rdquo;
            </div>
          </div>

          {/* Actions */}
          <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
            {!suggestionApplied ? (
              <button
                type="button"
                onClick={handleApplySuggestion}
                style={{
                  background: '#1E293B',
                  color: '#FFFFFF',
                  padding: '10px 16px',
                  borderRadius: 6,
                  fontWeight: 600,
                  fontSize: '0.9rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  cursor: 'pointer'
                }}
              >
                <Check size={16} />
                <span>Apply suggestion</span>
              </button>
            ) : (
              <button
                type="button"
                onClick={handleRevert}
                style={{
                  background: '#FFFFFF',
                  border: '1px solid var(--border-light)',
                  color: 'var(--brand-navy)',
                  padding: '8px 14px',
                  borderRadius: 6,
                  fontWeight: 600,
                  fontSize: '0.85rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 6,
                  cursor: 'pointer'
                }}
              >
                <RotateCcw size={14} />
                <span>Revert to original</span>
              </button>
            )}

            {!isApproved && suggestionApplied && (
              <button
                type="button"
                onClick={handleApprove}
                style={{
                  background: '#166534',
                  color: '#FFFFFF',
                  padding: '10px 16px',
                  borderRadius: 6,
                  fontWeight: 700,
                  fontSize: '0.9rem',
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'center',
                  gap: 8,
                  cursor: 'pointer'
                }}
              >
                <UserCheck size={16} />
                <span>Approve version as Reviewer Haany</span>
              </button>
            )}
          </div>
        </div>

        {/* PANEL 3: Evidence */}
        <div className="bl-card" style={{ padding: '24px' }}>
          <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center', marginBottom: 14 }}>
            <span style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)' }}>
              3. Evidence
            </span>
            <span style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
              Source Verifier
            </span>
          </div>

          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 2 }}>
              Related Policy
            </div>
            <div style={{ fontSize: '1rem', fontWeight: 700, color: 'var(--brand-navy)' }}>
              Promotional Claims Policy v2.1
            </div>
          </div>

          <div style={{ marginBottom: 16 }}>
            <div style={{ fontSize: '0.78rem', color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 2 }}>
              Source Register
            </div>
            <div style={{ fontSize: '0.9rem', color: 'var(--brand-navy)', fontWeight: 500 }}>
              Marketing Claims Register
            </div>
          </div>

          <div style={{
            background: '#F8F5EE',
            borderLeft: '3px solid var(--brand-gold)',
            borderRadius: '0 6px 6px 0',
            padding: '12px 14px',
            marginBottom: 16
          }}>
            <div style={{ fontSize: '0.75rem', color: 'var(--brand-gold)', fontWeight: 700, textTransform: 'uppercase', marginBottom: 4 }}>
              Source Excerpt
            </div>
            <div style={{ fontStyle: 'italic', fontSize: '0.88rem', color: 'var(--brand-navy)' }}>
              &ldquo;Superlative claims require an approved evidence reference.&rdquo;
            </div>
          </div>

          <div style={{ fontSize: '0.82rem', color: 'var(--text-muted)', display: 'flex', flexDirection: 'column', gap: 4 }}>
            <div>Last updated: <strong>18 October 2026</strong></div>
            <div>Policy Status: <strong style={{ color: '#166534' }}>ACTIVE</strong></div>
          </div>
        </div>
      </div>

      {/* Content Passport Certification Card (Shows after approval) */}
      {isApproved && (
        <div className="bl-card" style={{
          background: '#FDFBF7',
          border: '2px solid #166534',
          borderRadius: 12,
          padding: '32px',
          maxWidth: 720,
          margin: '0 auto 48px',
          boxShadow: 'var(--shadow-md)',
          animation: 'fadeIn 0.3s ease'
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 12, marginBottom: 16 }}>
            <div style={{
              width: 40,
              height: 40,
              borderRadius: '50%',
              background: '#E8F3EC',
              color: '#166534',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center'
            }}>
              <CheckCircle2 size={24} />
            </div>
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: '#166534', textTransform: 'uppercase' }}>
                Content Passport Minted
              </div>
              <h3 style={{ fontSize: '1.25rem', color: 'var(--brand-navy)', margin: 0, fontWeight: 700 }}>
                CMP-1042 Certified for Publication
              </h3>
            </div>
          </div>

          <p style={{ fontSize: '0.92rem', color: 'var(--text-secondary)', marginBottom: 20, fontStyle: 'italic' }}>
            &ldquo;This record shows what was reviewed, which sources were used, and who approved this version.&rdquo;
          </p>

          <div style={{
            display: 'grid',
            gridTemplateColumns: 'repeat(2, 1fr)',
            gap: 12,
            background: '#FFFFFF',
            border: '1px solid var(--border-light)',
            borderRadius: 8,
            padding: '16px',
            marginBottom: 20,
            fontSize: '0.85rem'
          }}>
            <div><strong>Content ID:</strong> CMP-1042</div>
            <div><strong>Approved version:</strong> 2</div>
            <div><strong>Reviewed by:</strong> Haany (Brand Manager)</div>
            <div><strong>Evidence used:</strong> 3 registered sources</div>
            <div><strong>Decision:</strong> APPROVED</div>
            <div><strong>Timestamp:</strong> 24 Oct 2026, 14:32</div>
          </div>

          <div style={{ display: 'flex', gap: 12, justifyContent: 'flex-end' }}>
            <Link href="/passports" style={{
              background: '#1E293B',
              color: '#FFFFFF',
              padding: '8px 16px',
              borderRadius: 6,
              fontSize: '0.85rem',
              fontWeight: 600,
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6
            }}>
              <span>Open Content Passports</span>
              <ArrowRight size={14} />
            </Link>
          </div>
        </div>
      )}

      {/* Footer Navigation */}
      <div style={{ textAlign: 'center' }}>
        <p style={{ fontSize: '0.95rem', color: 'var(--text-secondary)', marginBottom: 16 }}>
          Ready to review your team&rsquo;s real campaign drafts?
        </p>
        <div style={{ display: 'flex', gap: 14, justifyContent: 'center' }}>
          <Link href="/workspace" className="btn-primary">
            <span>Open live scan workspace</span>
            <ArrowRight size={16} />
          </Link>
          <Link href="/policies" className="btn-secondary">
            <span>Explore policy library</span>
          </Link>
        </div>
      </div>
    </div>
  );
}
