'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import {
  Shield, CheckCircle2, ArrowRight, BookOpen, Layers,
  FileText, AlertTriangle, Eye, Check, Clock, UserCheck,
  Sparkles, History, BarChart2, Lock, HelpCircle, RefreshCw
} from 'lucide-react';
import CrystalizedBall from '@/components/ui/CrystalizedBall';
import styles from './page.module.css';

export default function HomePage() {
  const [sampleApplied, setSampleApplied] = useState(false);

  return (
    <div className={styles.pageWrapper}>
      {/* ── Section 1: Hero ── */}
      <section className={`${styles.container} ${styles.heroSection}`}>
        {/* Crystalized Ball Background */}
        <div className={styles.heroBallWrapper}>
          <CrystalizedBall
            preset="solar"
            color="#FFD36E"
            size={0.7}
            crackle={0.7}
            fill={0.55}
            interactive
            hoverStrength={0.7}
            flares={1}
            glow={1.1}
            sparks={0.5}
            motion="orbit"
            sway={0.7}
            haze={0.8}
          />
        </div>

        <div className={styles.heroContent}>
          <div className={styles.heroTrustLine}>
            <Shield size={16} />
            <span>AI-assisted findings. Human-controlled decisions.</span>
          </div>

          <h1 className={styles.heroTitle}>
            Review content before your audience does.
          </h1>

          <p className={styles.heroSubtitle}>
            VerifiBrand checks drafts against your approved guidelines, facts, terminology, and assets—then gives your team a clear way to review and approve them.
          </p>

          <div className={styles.heroCtaGroup}>
            <Link href="/how-it-works" className="btn-primary">
              <span>See how it works</span>
              <ArrowRight size={16} />
            </Link>
            <Link href="/demo-preview" className="btn-secondary">
              <span>View a sample review</span>
            </Link>
          </div>
        </div>

        {/* Hero Product Workflow Mockup (Draft → Finding → Evidence → Approval) */}
        <div className={styles.workflowMockup}>
          <div className={styles.mockupHeader}>
            <div className={styles.mockupTabs}>
              <span style={{ fontWeight: 600, color: 'var(--brand-navy)' }}>Summer Membership Campaign</span>
              <span>&bull;</span>
              <span style={{ fontSize: '0.74rem', background: '#FFF5D9', color: '#8A5A00', padding: '1px 6px', borderRadius: 4, fontWeight: 700 }}>
                Sample preview
              </span>
            </div>
            <div style={{ display: 'flex', alignItems: 'center', gap: 6, fontSize: '0.8rem', color: 'var(--status-review-text)', background: 'var(--status-review-bg)', padding: '3px 10px', borderRadius: 4, fontWeight: 600 }}>
              <Clock size={12} />
              <span>IN REVIEW</span>
            </div>
          </div>

          <div className={styles.mockupGrid}>
            {/* Draft Panel */}
            <div className={styles.draftPanel}>
              <div className={styles.panelLabel}>Content Preview &amp; Highlights</div>
              <div className={styles.draftExcerpt}>
                Celebrate summer with Northstar! We are proud to be <span className={styles.highlightedText}>India’s No. 1 platform for creators</span>. Existing members receive 20% off all renewal packages through September.
              </div>
              <div style={{ marginTop: 20, display: 'flex', gap: 12, fontSize: '0.82rem', color: 'var(--text-secondary)' }}>
                <span>Target Channel: <strong>Social &amp; Web</strong></span>
                <span>&bull;</span>
                <span>Language: <strong>English (IN)</strong></span>
              </div>
            </div>

            {/* Finding & Evidence Panel */}
            <div className={styles.findingPanel}>
              <div className={styles.panelLabel}>Evidence-Backed Finding</div>

              <div className={styles.findingCard}>
                <div className={styles.findingHeader}>
                  <div className={styles.findingTitle}>Unsupported promotional claim</div>
                  <span className={styles.badgeHigh}>HIGH SEVERITY</span>
                </div>

                <p className={styles.findingText}>
                  This superlative claim requires an approved evidence reference that is not currently linked to the draft.
                </p>

                <div className={styles.evidenceBox}>
                  <div style={{ fontWeight: 600, marginBottom: 2 }}>Promotional Claims Policy v2.1</div>
                  <div style={{ fontStyle: 'italic', color: 'var(--text-secondary)' }}>
                    &ldquo;Superlative claims require an approved evidence reference.&rdquo;
                  </div>
                  <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)', marginTop: 4 }}>
                    Source: Marketing Claims Register &bull; Last updated: 18 Oct 2026
                  </div>
                </div>

                <div style={{ background: '#FDFBF7', border: '1px solid var(--border-light)', borderRadius: 6, padding: '10px 14px', marginBottom: 12 }}>
                  <div style={{ fontSize: '0.75rem', fontWeight: 600, color: 'var(--brand-gold)', textTransform: 'uppercase', marginBottom: 2 }}>
                    Suggested Correction
                  </div>
                  <div style={{ fontSize: '0.88rem', color: 'var(--brand-navy)', fontWeight: 500 }}>
                    &ldquo;Trusted by creators across India.&rdquo;
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
                  <span style={{ fontSize: '0.8rem', color: 'var(--text-muted)' }}>Decision: Pending reviewer</span>
                  <Link href="/demo-preview" style={{ fontSize: '0.85rem', fontWeight: 600, color: 'var(--brand-navy)', textDecoration: 'underline' }}>
                    Open interactive review &rarr;
                  </Link>
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 2: Problem ── */}
      <section className={styles.problemSection}>
        <div className={styles.container}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionPretitle}>The Governance Challenge</div>
            <h2 className={styles.sectionTitle}>
              Content is created everywhere. Brand knowledge is not.
            </h2>
            <p className={styles.sectionSubtitle}>
              Employees, agencies, and AI tools can all create content. The guidance they rely on may be spread across old briefs, PDFs, spreadsheets, and private messages.
            </p>
          </div>

          <div className={styles.problemGrid}>
            <div className={styles.problemCard}>
              <div className={styles.problemIcon}>
                <Clock size={20} />
              </div>
              <h3 className={styles.problemHeading}>An offer has expired.</h3>
              <p className={styles.problemDesc}>
                A marketer copies a discount headline from last quarter&rsquo;s newsletter. The campaign launches before anyone realizes the promo ended three weeks ago.
              </p>
            </div>

            <div className={styles.problemCard}>
              <div className={styles.problemIcon}>
                <AlertTriangle size={20} />
              </div>
              <h3 className={styles.problemHeading}>A familiar term is replaced.</h3>
              <p className={styles.problemDesc}>
                An agency writes copy using legacy product naming or competitor terminology, diluting the brand voice across major distribution channels.
              </p>
            </div>

            <div className={styles.problemCard}>
              <div className={styles.problemIcon}>
                <BookOpen size={20} />
              </div>
              <h3 className={styles.problemHeading}>A claim has no approved source.</h3>
              <p className={styles.problemDesc}>
                A draft includes superlative claims like &ldquo;No. 1 platform&rdquo; without an audited research citation, exposing the organization to compliance risks.
              </p>
            </div>
          </div>

          <div className={styles.closingBanner}>
            The challenge is not producing more content. It is reviewing the content consistently.
          </div>
        </div>
      </section>

      {/* ── Section 3: Product Workflow ── */}
      <section className={styles.container} id="workflow">
        <div className={styles.sectionHeader}>
          <div className={styles.sectionPretitle}>End-to-End Workflow</div>
          <h2 className={styles.sectionTitle}>
            One review layer for every draft.
          </h2>
          <p className={styles.sectionSubtitle}>
            From approved policies to verifiable publication proof, VerifiBrand connects brand guidelines directly to everyday content creation.
          </p>
        </div>

        <div className={styles.stepsGrid}>
          <div className={styles.stepCard}>
            <div className={styles.stepNumber}>01</div>
            <h3 className={styles.stepTitle}>Define the truth</h3>
            <p className={styles.stepDesc}>
              Store approved guidelines, facts, terms, and assets in versioned, searchable Policy Cards.
            </p>
          </div>

          <div className={styles.stepCard}>
            <div className={styles.stepNumber}>02</div>
            <h3 className={styles.stepTitle}>Submit content</h3>
            <p className={styles.stepDesc}>
              Upload a draft document, paste campaign copy, or submit an image banner asset for evaluation.
            </p>
          </div>

          <div className={styles.stepCard}>
            <div className={styles.stepNumber}>03</div>
            <h3 className={styles.stepTitle}>Understand findings</h3>
            <p className={styles.stepDesc}>
              See exactly what was flagged, why it matters, and which active source policy is related.
            </p>
          </div>

          <div className={styles.stepCard}>
            <div className={styles.stepNumber}>04</div>
            <h3 className={styles.stepTitle}>Make the decision</h3>
            <p className={styles.stepDesc}>
              Revise, request changes, approve, or record an authorized override with a clear audit reason.
            </p>
          </div>
        </div>
      </section>

      {/* ── Section 4: Review Example ── */}
      <section className={styles.container}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionPretitle}>Verifiable Review</div>
          <h2 className={styles.sectionTitle}>
            A finding should come with a reason.
          </h2>
          <p className={styles.sectionSubtitle}>
            Never settle for an unexplained AI confidence score. VerifiBrand pairs every flag with verbatim evidence and an actionable path forward.
          </p>
        </div>

        <div className={styles.exampleCard}>
          <div className={styles.panelLabel}>Submitted Draft Excerpt</div>
          <div className={styles.exampleDraft}>
            Draft copy: &ldquo;{sampleApplied ? 'Trusted by creators across India' : 'India’s No. 1 platform for creators'}&rdquo;
          </div>

          <div className={styles.exampleDetailsGrid}>
            <div className={styles.exampleBlock}>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--brand-gold)', textTransform: 'uppercase', marginBottom: 6 }}>
                Finding &amp; Context
              </div>
              <div style={{ fontWeight: 700, color: 'var(--brand-navy)', marginBottom: 6 }}>
                Unsupported promotional claim
              </div>
              <p style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                This claim requires an approved evidence reference that is not currently linked to the draft.
              </p>
            </div>

            <div className={styles.exampleBlock}>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--brand-navy)', textTransform: 'uppercase', marginBottom: 6 }}>
                Verified Source Evidence
              </div>
              <div style={{ fontWeight: 600, color: 'var(--brand-navy)', marginBottom: 4 }}>
                Promotional Claims Policy v2.1
              </div>
              <div style={{ fontStyle: 'italic', fontSize: '0.88rem', color: 'var(--text-secondary)', marginBottom: 6 }}>
                &ldquo;Superlative claims require an approved evidence reference.&rdquo;
              </div>
              <div style={{ fontSize: '0.75rem', color: 'var(--text-muted)' }}>
                Source: Marketing Claims Register &bull; Updated 18 Oct 2026
              </div>
            </div>
          </div>

          <div style={{ background: '#F8F5EE', border: '1px solid var(--border-light)', borderRadius: 8, padding: '16px', marginBottom: 20 }}>
            <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--brand-gold)', textTransform: 'uppercase', marginBottom: 4 }}>
              Suggested Correction
            </div>
            <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--brand-navy)' }}>
              &ldquo;Trusted by creators across India.&rdquo;
            </div>
          </div>

          <div className={styles.exampleActions}>
            <button
              type="button"
              onClick={() => setSampleApplied(!sampleApplied)}
              className="btn-primary"
            >
              <Check size={16} />
              <span>{sampleApplied ? 'Suggestion applied (Undo)' : 'Apply suggestion'}</span>
            </button>
            <Link href="/workspace" className="btn-secondary">
              Edit manually
            </Link>
            <Link href="/review" className="btn-secondary">
              Keep original (Request override)
            </Link>
          </div>
        </div>
      </section>

      {/* ── Section 5: Human Approval ── */}
      <section className={styles.problemSection}>
        <div className={styles.container}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionPretitle}>Human-In-The-Loop Governance</div>
            <h2 className={styles.sectionTitle}>
              AI can assist the review. People decide what happens next.
            </h2>
            <p className={styles.sectionSubtitle}>
              VerifiBrand can surface possible issues and suggest alternatives. An authorised reviewer still decides whether content is changed, approved, or accepted with an override.
            </p>
          </div>

          <div className={styles.statesGrid}>
            <div className={styles.stateCard}>
              <span className={styles.stateLabel} style={{ background: 'var(--status-draft-bg)', color: 'var(--status-draft-text)' }}>
                DRAFT
              </span>
              <div className={styles.stateDesc}>Not yet submitted for review</div>
            </div>

            <div className={styles.stateCard}>
              <span className={styles.stateLabel} style={{ background: 'var(--status-review-bg)', color: 'var(--status-review-text)' }}>
                IN REVIEW
              </span>
              <div className={styles.stateDesc}>Assisted checks completed, awaiting reviewer</div>
            </div>

            <div className={styles.stateCard}>
              <span className={styles.stateLabel} style={{ background: 'var(--status-warning-bg)', color: 'var(--status-warning-text)' }}>
                CHANGES REQUESTED
              </span>
              <div className={styles.stateDesc}>Creator must revise flagged wording</div>
            </div>

            <div className={styles.stateCard}>
              <span className={styles.stateLabel} style={{ background: 'var(--status-approved-bg)', color: 'var(--status-approved-text)' }}>
                APPROVED
              </span>
              <div className={styles.stateDesc}>Approved for publication with Content Passport</div>
            </div>

            <div className={styles.stateCard}>
              <span className={styles.stateLabel} style={{ background: 'var(--status-revalidation-bg)', color: 'var(--status-revalidation-text)' }}>
                WITH OVERRIDE
              </span>
              <div className={styles.stateDesc}>Reviewer recorded approval with documented reason</div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 6: Features ── */}
      <section className={styles.container}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionPretitle}>Core Capabilities</div>
          <h2 className={styles.sectionTitle}>
            Built for everyday brand operations.
          </h2>
          <p className={styles.sectionSubtitle}>
            Practical tools designed to reduce avoidable revisions and make brand guidelines usable.
          </p>
        </div>

        <div className={styles.featuresGrid}>
          <div className={styles.featureCard}>
            <div className={styles.featureIcon}><BookOpen size={20} /></div>
            <h3 className={styles.featureTitle}>Policy Cards</h3>
            <p className={styles.featureDesc}>
              Turn long guidelines and PDFs into searchable, versioned decisions that evaluate drafts against active Policy Cards.
            </p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.featureIcon}><CheckCircle2 size={20} /></div>
            <h3 className={styles.featureTitle}>Approved Facts</h3>
            <p className={styles.featureDesc}>
              Keep important claims, offer dates, and pricing numbers connected to an authoritative source and version.
            </p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.featureIcon}><FileText size={20} /></div>
            <h3 className={styles.featureTitle}>Terminology</h3>
            <p className={styles.featureDesc}>
              Help cross-functional teams and external agencies use the same approved language across all channels.
            </p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.featureIcon}><Layers size={20} /></div>
            <h3 className={styles.featureTitle}>Asset Checks</h3>
            <p className={styles.featureDesc}>
              Reduce the chance of using a retired logo, outdated badge, or incorrect visual template in public.
            </p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.featureIcon}><Eye size={20} /></div>
            <h3 className={styles.featureTitle}>Accessibility Checks</h3>
            <p className={styles.featureDesc}>
              Surface basic contrast concerns, readability levels, and alt-text omissions before content goes live.
            </p>
          </div>

          <div className={styles.featureCard}>
            <div className={styles.featureIcon}><UserCheck size={20} /></div>
            <h3 className={styles.featureTitle}>Review Workflow</h3>
            <p className={styles.featureDesc}>
              Assign, comment, revise, approve, and retain the decision history for review and audit.
            </p>
          </div>
        </div>
      </section>

      {/* ── Section 7: Governance Insights ── */}
      <section className={styles.container}>
        <div className={styles.insightsCard}>
          <div style={{ textAlign: 'center', marginBottom: 24 }}>
            <div className={styles.sectionPretitle}>Recurring Patterns</div>
            <h2 className={styles.sectionTitle} style={{ fontSize: '2rem' }}>
              Learn from the mistakes that keep returning.
            </h2>
            <p className={styles.sectionSubtitle}>
              VerifiBrand tracks recurring findings across teams so you can clarify ambiguous guidelines.
            </p>
          </div>

          <div className={styles.insightRow}>
            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>
                Repeated Issue
              </div>
              <div style={{ fontSize: '1.05rem', fontWeight: 700, color: 'var(--brand-navy)' }}>
                Outdated terminology
              </div>
              <div style={{ fontSize: '0.82rem', color: 'var(--status-warning-text)', marginTop: 2 }}>
                7 findings across 4 campaigns
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>
                Affected Areas
              </div>
              <div style={{ fontSize: '1rem', fontWeight: 600, color: 'var(--brand-navy)' }}>
                Content &bull; Social &bull; Agency
              </div>
              <div style={{ fontSize: '0.82rem', color: 'var(--text-secondary)', marginTop: 2 }}>
                Primary source: Q3 Messaging Brief
              </div>
            </div>

            <div>
              <div style={{ fontSize: '0.75rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase', marginBottom: 4 }}>
                Recommended Action
              </div>
              <div style={{ fontSize: '0.95rem', fontWeight: 600, color: 'var(--brand-forest)' }}>
                Clarify campaign messaging rule
              </div>
              <Link href="/insights" style={{ fontSize: '0.82rem', color: 'var(--brand-navy)', textDecoration: 'underline', marginTop: 4, display: 'inline-block' }}>
                Open insights dashboard &rarr;
              </Link>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 8: Security & Responsible Design ── */}
      <section className={styles.problemSection}>
        <div className={styles.container}>
          <div className={styles.sectionHeader}>
            <div className={styles.sectionPretitle}>Defensible Governance</div>
            <h2 className={styles.sectionTitle}>
              Designed for sensitive brand work.
            </h2>
            <p className={styles.sectionSubtitle}>
              Built with privacy and responsible AI principles. Server-side secrets, client-server data boundaries, and verifiable human control.
            </p>
          </div>

          <div className={styles.securityGrid}>
            <div className={styles.securityCard}>
              <Lock size={20} color="var(--brand-navy)" style={{ flexShrink: 0, marginTop: 2 }} />
              <div>
                <div style={{ fontWeight: 700, color: 'var(--brand-navy)', marginBottom: 4 }}>Role-based access</div>
                <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  Distinct roles for creators, managers, and authorized compliance reviewers ensure separation of duties.
                </div>
              </div>
            </div>

            <div className={styles.securityCard}>
              <BookOpen size={20} color="var(--brand-navy)" style={{ flexShrink: 0, marginTop: 2 }} />
              <div>
                <div style={{ fontWeight: 700, color: 'var(--brand-navy)', marginBottom: 4 }}>Source-linked findings</div>
                <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  Every flag cites exact policy text and active version snapshots—eliminating mysterious, black-box scores.
                </div>
              </div>
            </div>

            <div className={styles.securityCard}>
              <History size={20} color="var(--brand-navy)" style={{ flexShrink: 0, marginTop: 2 }} />
              <div>
                <div style={{ fontWeight: 700, color: 'var(--brand-navy)', marginBottom: 4 }}>Visible revision history</div>
                <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  Full chronological audit trails capture every draft revision, reviewer sign-off, and override explanation.
                </div>
              </div>
            </div>

            <div className={styles.securityCard}>
              <UserCheck size={20} color="var(--brand-navy)" style={{ flexShrink: 0, marginTop: 2 }} />
              <div>
                <div style={{ fontWeight: 700, color: 'var(--brand-navy)', marginBottom: 4 }}>Human decision control</div>
                <div style={{ fontSize: '0.88rem', color: 'var(--text-secondary)', lineHeight: 1.5 }}>
                  AI assists with text extraction and candidate detection; authorized people remain in command of approvals.
                </div>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 9: Who It Is For ── */}
      <section className={styles.container}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionPretitle}>Target Roles</div>
          <h2 className={styles.sectionTitle}>
            Who VerifiBrand is built for.
          </h2>
          <p className={styles.sectionSubtitle}>
            A shared workspace serving every participant in the content creation and approval lifecycle.
          </p>
        </div>

        <div className={styles.personaGrid}>
          <div className={styles.personaCard}>
            <div className={styles.personaRole}>Brand Managers</div>
            <div className={styles.personaNeed}>
              Keep guidance current, manage policy cards, and review candidate findings without repetitive manual checking.
            </div>
          </div>

          <div className={styles.personaCard}>
            <div className={styles.personaRole}>Content Creators</div>
            <div className={styles.personaNeed}>
              Get clear, actionable feedback and suggested wording corrections before submitting drafts for sign-off.
            </div>
          </div>

          <div className={styles.personaCard}>
            <div className={styles.personaRole}>Marketing Agencies</div>
            <div className={styles.personaNeed}>
              Work from one single, verified source of truth across clients, reducing avoidable revision cycles.
            </div>
          </div>

          <div className={styles.personaCard}>
            <div className={styles.personaRole}>Compliance Reviewers</div>
            <div className={styles.personaNeed}>
              Trace evidence, inspect revision differences, record overrides, and retain tamper-evident approval records.
            </div>
          </div>
        </div>
      </section>

      {/* ── Section 10: Validation & Impact ── */}
      <section className={styles.container}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionPretitle}>Measurable Operations</div>
          <h2 className={styles.sectionTitle}>
            Make content review easier to measure.
          </h2>
          <p className={styles.sectionSubtitle}>
            VerifiBrand is designed to help teams understand where review time goes, which mistakes repeat, and which rules need clarification.
          </p>
        </div>

        <div className={styles.metricsGrid}>
          <div className={styles.metricCard}>
            <div className={styles.metricTitle}>Time to first actionable finding</div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricTitle}>Number of repeated issues over time</div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricTitle}>Percentage of findings with evidence links</div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricTitle}>Number of overrides and recorded reasons</div>
          </div>
          <div className={styles.metricCard}>
            <div className={styles.metricTitle}>Time from submission to authorized decision</div>
          </div>
        </div>
      </section>

      {/* ── Section 11: Future Scope ── */}
      <section className={styles.container}>
        <div className={styles.sectionHeader}>
          <div className={styles.sectionPretitle}>Roadmap &bull; Planned Extensions</div>
          <h2 className={styles.sectionTitle}>
            Start with review. Expand where the workflow proves useful.
          </h2>
          <p className={styles.sectionSubtitle}>
            Future integrations planned to bring VerifiBrand verification into external design and publication tools.
          </p>
        </div>

        <div className={styles.futurePills}>
          <div className={styles.futurePill}>
            <span>Figma &amp; Canva integrations</span>
          </div>
          <div className={styles.futurePill}>
            <span>CMS and marketing platform connectors</span>
          </div>
          <div className={styles.futurePill}>
            <span>Video and audio checks</span>
          </div>
          <div className={styles.futurePill}>
            <span>Guideline extraction assistance</span>
          </div>
          <div className={styles.futurePill}>
            <span>Global market profiles</span>
          </div>
          <div className={styles.futurePill}>
            <span>Policy-change revalidation alerts</span>
          </div>
        </div>
      </section>

      {/* ── Section 12: Final Call to Action ── */}
      <section className={styles.container}>
        <div className={styles.finalCtaSection}>
          <h2 className={styles.ctaTitle}>
            Give creators clearer guidance and reviewers better evidence.
          </h2>
          <p className={styles.ctaSubtitle}>
            Join content teams maintaining high standards without slowing down campaign delivery.
          </p>

          <div className={styles.ctaButtons}>
            <Link href="/workspace" style={{ background: '#FFFFFF', color: '#1E293B', padding: '12px 24px', borderRadius: 8, fontWeight: 700, fontSize: '1rem', display: 'inline-flex', alignItems: 'center', gap: 8 }}>
              <span>Open workspace</span>
              <ArrowRight size={16} />
            </Link>
            <Link href="/demo-preview" style={{ background: 'transparent', border: '1px solid rgba(255, 255, 255, 0.4)', color: '#FFFFFF', padding: '12px 24px', borderRadius: 8, fontWeight: 600, fontSize: '1rem' }}>
              <span>View a sample review</span>
            </Link>
          </div>
        </div>
      </section>
    </div>
  );
}
