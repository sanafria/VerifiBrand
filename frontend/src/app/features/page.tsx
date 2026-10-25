'use client';

import React from 'react';
import Link from 'next/link';
import {
  BookOpen, CheckCircle2, FileText, Layers, Eye, UserCheck,
  Shield, ArrowRight, Award, History, BarChart2, Check
} from 'lucide-react';

export default function FeaturesPage() {
  const features = [
    {
      icon: <BookOpen size={24} />,
      title: 'Policy Cards',
      summary: 'Turn long guidelines into searchable, versioned decisions.',
      description: 'Convert dense brand books and PDFs into discrete, active policy rules. Each card specifies clear constraints, active dates, applicable channels, and literal source quotations.',
      benefits: [
        'Automatic semantic versioning on rule updates',
        'Scoped applicability (Social, Email, Ads, Web)',
        'Quote integrity verification with source register links'
      ],
      link: '/policies',
      linkText: 'Explore Policy Library'
    },
    {
      icon: <CheckCircle2 size={24} />,
      title: 'Approved Facts Library',
      summary: 'Keep important claims connected to a source and version.',
      description: 'Store verified company metrics, registered statistics, and active promotional offers. Never let drafts repeat outdated numbers or unverified commercial statements.',
      benefits: [
        'Time-bound promotional validity dates',
        'Automatic expiration warnings for outdated claims',
        'Strict evidence citations required for superlative claims'
      ],
      link: '/policies',
      linkText: 'View Fact Library'
    },
    {
      icon: <FileText size={24} />,
      title: 'Terminology & Voice',
      summary: 'Help cross-functional teams use the same language.',
      description: 'Govern vocabulary across creators, contractors, and agencies. Detect deprecated naming, banned competitor terminology, and unapproved product labels before publishing.',
      benefits: [
        'Prohibited term detection with recommended replacements',
        'Context-sensitive voice & tone evaluation',
        'Customizable enterprise vocabulary registers'
      ],
      link: '/workspace',
      linkText: 'Test Terminology Scanner'
    },
    {
      icon: <Layers size={24} />,
      title: 'Asset Specifications & Checks',
      summary: 'Reduce the chance of using a retired or incorrect asset.',
      description: 'Catalog approved logos, badge formats, and lockup variants. Ensure visual marketing materials adhere to strict color palette rules and exclusion zone requirements.',
      benefits: [
        'Clear RETIRED vs APPROVED status tags on all assets',
        'Channel-specific aspect ratio and resolution rules',
        'OCR text extraction from graphic banners and promotional images'
      ],
      link: '/brand-passport',
      linkText: 'View Brand Assets'
    },
    {
      icon: <Eye size={24} />,
      title: 'Accessibility & Readability',
      summary: 'Surface basic contrast, readability, and alt-text concerns.',
      description: 'Ensure brand content is legible and accessible to all audiences. Automated checks flag dense reading complexity, insufficient color contrast, and missing media descriptions.',
      benefits: [
        'Reading grade level and sentence length analysis',
        'Basic WCAG contrast threshold evaluation',
        'Alt-text validation for uploaded graphic assets'
      ],
      link: '/workspace',
      linkText: 'Run Accessibility Check'
    },
    {
      icon: <UserCheck size={24} />,
      title: 'Review Gateway & Decision Trail',
      summary: 'Assign, comment, revise, approve, and retain decision history.',
      description: 'A structured review workflow with clear role separation. Reviewers can approve, request changes, or approve with an override while logging mandatory audit justifications.',
      benefits: [
        'Role-based permissions separating creators from reviewers',
        'Cryptographic Content Passport generation upon approval',
        'Immutable audit log tracking all actions and timestamps'
      ],
      link: '/review',
      linkText: 'Open Review Gate'
    }
  ];

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
          <Shield size={14} />
          <span>Platform Capabilities</span>
        </div>

        <h1 style={{
          fontFamily: 'var(--font-heading)',
          fontSize: '3rem',
          color: 'var(--brand-navy)',
          marginBottom: 16,
          fontWeight: 400
        }}>
          VerifiBrand Features
        </h1>

        <p style={{ fontSize: '1.15rem', color: 'var(--text-secondary)', lineHeight: 1.6 }}>
          Practical, evidence-backed capabilities designed to eliminate guesswork and streamline brand governance.
        </p>
      </div>

      {/* Feature Grid */}
      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(360px, 1fr))', gap: 32, marginBottom: 64 }}>
        {features.map((feature, idx) => (
          <div key={idx} className="bl-card" style={{ padding: '32px', display: 'flex', flexDirection: 'column', justifyContent: 'space-between' }}>
            <div>
              <div style={{
                width: 44,
                height: 44,
                borderRadius: 8,
                background: '#F8F5EE',
                color: 'var(--brand-navy)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                marginBottom: 20
              }}>
                {feature.icon}
              </div>

              <h2 style={{ fontSize: '1.3rem', color: 'var(--brand-navy)', marginBottom: 8, fontWeight: 700 }}>
                {feature.title}
              </h2>

              <p style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--brand-gold)', marginBottom: 12 }}>
                {feature.summary}
              </p>

              <p style={{ fontSize: '0.9rem', color: 'var(--text-secondary)', lineHeight: 1.6, marginBottom: 20 }}>
                {feature.description}
              </p>

              <div style={{ borderTop: '1px solid var(--border-light)', paddingTop: 16, marginBottom: 24 }}>
                <div style={{ fontSize: '0.75rem', fontWeight: 700, textTransform: 'uppercase', color: 'var(--text-muted)', marginBottom: 10 }}>
                  Key Capabilities
                </div>
                <ul style={{ listStyle: 'none', display: 'flex', flexDirection: 'column', gap: 8 }}>
                  {feature.benefits.map((benefit, bIdx) => (
                    <li key={bIdx} style={{ display: 'flex', alignItems: 'flex-start', gap: 8, fontSize: '0.85rem', color: 'var(--brand-navy)' }}>
                      <Check size={14} color="#166534" style={{ flexShrink: 0, marginTop: 3 }} />
                      <span>{benefit}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>

            <Link href={feature.link} style={{
              display: 'inline-flex',
              alignItems: 'center',
              gap: 6,
              fontSize: '0.9rem',
              fontWeight: 600,
              color: 'var(--brand-navy)',
              textDecoration: 'none'
            }}>
              <span>{feature.linkText}</span>
              <ArrowRight size={14} />
            </Link>
          </div>
        ))}
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
          Ready to review with evidence?
        </h3>
        <p style={{ color: '#CBD5E1', marginBottom: 24, fontSize: '1.05rem' }}>
          Open the scan workspace to test drafts against your live policy cards.
        </p>
        <Link href="/workspace" style={{ background: '#FFFFFF', color: '#1E293B', padding: '12px 24px', borderRadius: 6, fontWeight: 700, display: 'inline-flex', alignItems: 'center', gap: 8 }}>
          <span>Open workspace</span>
          <ArrowRight size={16} />
        </Link>
      </div>
    </div>
  );
}
