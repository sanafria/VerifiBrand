'use client';

import React, { useState, useEffect } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import {
  Shield, CheckCircle2, ChevronRight, ChevronLeft,
  X, Play, Award, FileText, AlertTriangle, Sparkles,
  ExternalLink, ArrowRight, RotateCcw
} from 'lucide-react';

interface TourStep {
  title: string;
  stepNumber: number;
  badge: string;
  scenario: string;
  explanation: string;
  details: {
    label: string;
    value: string;
  }[];
  actionLabel: string;
}

const TOUR_STEPS: TourStep[] = [
  {
    stepNumber: 1,
    title: 'Submit a draft',
    badge: 'Draft Submission',
    scenario: 'Organisation: Northstar Membership · Campaign: Summer Membership Campaign · Creator: Sana',
    explanation: 'Content creators submit social posts, ad copy, or banner drafts. VerifiBrand parses text, checks campaign assets, and cross-references active brand rules.',
    details: [
      { label: 'Content ID', value: 'CMP-1042' },
      { label: 'Draft Excerpt', value: 'Join India’s No. 1 platform for creators! Get 40% off membership this weekend only.' },
      { label: 'Creator', value: 'Sana (Content Creator)' }
    ],
    actionLabel: 'Check draft for findings'
  },
  {
    stepNumber: 2,
    title: 'See a finding',
    badge: 'Deterministic Detection',
    scenario: 'VerifiBrand flags a superlative promotional statement and an unapproved discount figure.',
    explanation: 'Findings are categorized by policy severity. No vague confidence scores: each flag pinpoints the exact text and the required evidence tier.',
    details: [
      { label: 'Detected Flag', value: 'Unsupported superlative promotional claim' },
      { label: 'Flagged Text', value: '“India’s No. 1 platform for creators”' },
      { label: 'Severity', value: 'High · Open' }
    ],
    actionLabel: 'Open explanation'
  },
  {
    stepNumber: 3,
    title: 'Open the explanation',
    badge: 'Context & Rationale',
    scenario: 'Understanding why the claim cannot be published without substantiation.',
    explanation: 'VerifiBrand provides the reason behind the finding: superlative claims require a recognized market survey or registered evidence card linked to this draft version.',
    details: [
      { label: 'Why it matters', value: 'The claim requires an approved evidence reference that is not currently linked to the draft.' },
      { label: 'Policy Scope', value: 'Applies to Social, Website, Ads, and Email' },
      { label: 'Risk Tier', value: 'Regulatory advertising claim risk' }
    ],
    actionLabel: 'View related evidence'
  },
  {
    stepNumber: 4,
    title: 'View the evidence',
    badge: 'Source Verification',
    scenario: 'Inspecting the verified policy citation from the Brand Claims Register.',
    explanation: 'Every finding cites the authoritative source: the exact policy ID, active version number, and literal verbatim quote.',
    details: [
      { label: 'Related Policy', value: 'Promotional Claims Policy v2.1' },
      { label: 'Source Document', value: 'Marketing Claims Register' },
      { label: 'Source Excerpt', value: '“Superlative claims require an approved evidence reference.”' },
      { label: 'Last Updated', value: '18 October 2026' }
    ],
    actionLabel: 'Apply suggested correction'
  },
  {
    stepNumber: 5,
    title: 'Apply a correction',
    badge: 'Creator Revision',
    scenario: 'Preserving creator intent with approved terminology.',
    explanation: 'The creator replaces the unsupported claim with an approved wording alternative, bringing the draft into compliance before sending it to the reviewer.',
    details: [
      { label: 'Original', value: '“India’s No. 1 platform for creators”' },
      { label: 'Suggested Correction', value: '“Trusted by creators across India”' },
      { label: 'Action Taken', value: 'Suggestion applied · Revised to Version 2' }
    ],
    actionLabel: 'Submit for human approval'
  },
  {
    stepNumber: 6,
    title: 'Approve the version',
    badge: 'Authorized Decision',
    scenario: 'Reviewer Haany signs off on the compliant draft.',
    explanation: 'AI assists the review, but authorized humans make the decision. Reviewer Haany records an approval decision linked to their identity and verified credentials.',
    details: [
      { label: 'Authorised Reviewer', value: 'Haany (Brand Manager)' },
      { label: 'Decision', value: 'APPROVED' },
      { label: 'Audit Record', value: 'Recorded with policy version snapshot v2.1' }
    ],
    actionLabel: 'Generate Content Passport'
  },
  {
    stepNumber: 7,
    title: 'View the Content Passport',
    badge: 'Traceable Approval Record',
    scenario: 'A verifiable, tamper-evident record of the review decision.',
    explanation: 'The Content Passport proves what was reviewed, which source policies were active, and who authorized publication. Defensible compliance for teams and partners.',
    details: [
      { label: 'Passport ID', value: 'PASSPORT-CMP-1042' },
      { label: 'Approved Version', value: 'Version 2' },
      { label: 'Evidence Used', value: '3 verified policy sources' },
      { label: 'Decision Record', value: 'Approved · 24 Oct 2026, 14:32' }
    ],
    actionLabel: 'View completion summary'
  }
];

export const DemoToolbar: React.FC = () => {
  const [showInitialPrompt, setShowInitialPrompt] = useState(false);
  const [isOpen, setIsOpen] = useState(false);
  const [currentStepIndex, setCurrentStepIndex] = useState(0);
  const [isCompleted, setIsCompleted] = useState(false);

  const pathname = usePathname();
  const router = useRouter();

  // Show onboarding prompt only on product workspace routes for first-time visitors
  useEffect(() => {
    const isWorkspaceRoute = pathname === '/workspace' || pathname === '/review';
    if (typeof window !== 'undefined' && isWorkspaceRoute) {
      const hasSeen = localStorage.getItem('has_seen_demo_navigator');
      if (!hasSeen) {
        const timer = setTimeout(() => {
          setShowInitialPrompt(true);
        }, 800);
        return () => clearTimeout(timer);
      }
    }
  }, [pathname]);

  // Listen for replay event from Navbar or Settings
  useEffect(() => {
    const handleReplay = () => {
      setShowInitialPrompt(false);
      setCurrentStepIndex(0);
      setIsCompleted(false);
      setIsOpen(true);
    };

    window.addEventListener('open-demo-tour', handleReplay);
    return () => window.removeEventListener('open-demo-tour', handleReplay);
  }, []);

  const handleStartTour = () => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('has_seen_demo_navigator', 'true');
    }
    setShowInitialPrompt(false);
    setCurrentStepIndex(0);
    setIsCompleted(false);
    setIsOpen(true);
  };

  const handleDismissPrompt = () => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('has_seen_demo_navigator', 'true');
    }
    setShowInitialPrompt(false);
  };

  const handleNext = () => {
    if (currentStepIndex < TOUR_STEPS.length - 1) {
      setCurrentStepIndex(prev => prev + 1);
    } else {
      setIsCompleted(true);
    }
  };

  const handleBack = () => {
    if (currentStepIndex > 0) {
      setCurrentStepIndex(prev => prev - 1);
    }
  };

  const handleClose = () => {
    setIsOpen(false);
  };

  const handleRestart = () => {
    setCurrentStepIndex(0);
    setIsCompleted(false);
  };

  const handleOpenWorkspace = () => {
    setIsOpen(false);
    router.push('/workspace');
  };

  const currentStep = TOUR_STEPS[currentStepIndex];

  return (
    <>
      {/* 1. First-Use Welcome Prompt (Section 16) */}
      {showInitialPrompt && !isOpen && (
        <aside
          role="dialog"
          aria-label="Welcome to VerifiBrand"
          style={{
            position: 'fixed',
            bottom: 24,
            right: 24,
            zIndex: 9999,
            maxWidth: 420,
            background: '#FFFFFF',
            border: '1px solid #D8D3C8',
            borderRadius: 12,
            padding: '24px',
            boxShadow: '0 12px 36px rgba(30, 41, 59, 0.12)',
            animation: 'fadeIn 0.25s ease-out',
          }}
        >
          <div style={{ display: 'flex', alignItems: 'flex-start', justifyContent: 'space-between', marginBottom: 12 }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
              <div style={{
                width: 28,
                height: 28,
                borderRadius: 6,
                background: '#1E293B',
                color: '#FFFFFF',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center'
              }}>
                <Shield size={16} />
              </div>
              <h3 style={{ fontSize: '1.05rem', color: '#1E293B', margin: 0, fontWeight: 700 }}>
                Welcome to VerifiBrand
              </h3>
            </div>
            <button
              onClick={handleDismissPrompt}
              style={{ color: '#7A756E', padding: 4, cursor: 'pointer' }}
              aria-label="Close"
            >
              <X size={18} />
            </button>
          </div>

          <p style={{ fontSize: '0.9rem', color: '#5C5752', marginBottom: 18, lineHeight: 1.5 }}>
            Would you like a short guided tour of the review workflow? We will walk through the Northstar Membership campaign from submission to Content Passport.
          </p>

          <div style={{ display: 'flex', gap: 10 }}>
            <button
              onClick={handleStartTour}
              style={{
                flex: 1,
                background: '#1E293B',
                color: '#FFFFFF',
                border: 'none',
                borderRadius: 8,
                padding: '10px 14px',
                fontSize: '0.88rem',
                fontWeight: 600,
                display: 'inline-flex',
                alignItems: 'center',
                justifyContent: 'center',
                gap: 6,
                cursor: 'pointer'
              }}
            >
              <Play size={14} fill="currentColor" />
              <span>Start guided demo</span>
            </button>
            <button
              onClick={handleDismissPrompt}
              style={{
                background: '#FFFFFF',
                border: '1px solid #D8D3C8',
                color: '#1E293B',
                borderRadius: 8,
                padding: '10px 14px',
                fontSize: '0.88rem',
                fontWeight: 500,
                cursor: 'pointer'
              }}
            >
              Maybe later
            </button>
          </div>
        </aside>
      )}

      {/* 2. Interactive Guided Tour Modal Overlay (Section 16) */}
      {isOpen && (
        <div
          role="dialog"
          aria-modal="true"
          aria-label="VerifiBrand Workflow Tour"
          style={{
            position: 'fixed',
            inset: 0,
            background: 'rgba(15, 23, 42, 0.45)',
            backdropFilter: 'blur(4px)',
            zIndex: 10000,
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            padding: 20
          }}
        >
          <div
            style={{
              background: '#FFFFFF',
              border: '1px solid #D8D3C8',
              borderRadius: 14,
              maxWidth: 580,
              width: '100%',
              boxShadow: '0 20px 48px rgba(30, 41, 59, 0.2)',
              overflow: 'hidden',
              display: 'flex',
              flexDirection: 'column'
            }}
          >
            {/* Modal Header */}
            <div
              style={{
                padding: '18px 24px',
                background: '#F8F5EE',
                borderBottom: '1px solid #E5DDD3',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'space-between'
              }}
            >
              <div>
                <span style={{
                  fontSize: '0.75rem',
                  fontWeight: 700,
                  textTransform: 'uppercase',
                  color: '#B58A1F',
                  letterSpacing: '0.04em'
                }}>
                  Guided Review Workflow Tour
                </span>
                <div style={{ fontSize: '1rem', fontWeight: 700, color: '#1E293B', marginTop: 2 }}>
                  {!isCompleted ? `Step ${currentStep.stepNumber} of 7: ${currentStep.title}` : 'Review Workflow Complete'}
                </div>
              </div>

              <div style={{ display: 'flex', alignItems: 'center', gap: 12 }}>
                {!isCompleted && (
                  <span style={{
                    fontSize: '0.82rem',
                    fontWeight: 600,
                    color: '#5C5752',
                    background: '#FFFFFF',
                    border: '1px solid #D8D3C8',
                    padding: '3px 8px',
                    borderRadius: 6
                  }}>
                    {currentStep.stepNumber} / 7
                  </span>
                )}
                <button
                  onClick={handleClose}
                  style={{
                    color: '#7A756E',
                    cursor: 'pointer',
                    padding: 4,
                    borderRadius: 4
                  }}
                  title="Exit tour"
                >
                  <X size={18} />
                </button>
              </div>
            </div>

            {/* Modal Content */}
            {!isCompleted ? (
              <div style={{ padding: '24px 28px' }}>
                {/* Scenario Banner */}
                <div
                  style={{
                    fontSize: '0.78rem',
                    color: '#5C5752',
                    background: '#FDFBF7',
                    border: '1px solid #E8E2D8',
                    padding: '8px 12px',
                    borderRadius: 6,
                    marginBottom: 16
                  }}
                >
                  {currentStep.scenario}
                </div>

                <p style={{ fontSize: '0.94rem', color: '#1E293B', lineHeight: 1.55, marginBottom: 20 }}>
                  {currentStep.explanation}
                </p>

                {/* Evidence & Details Box */}
                <div
                  style={{
                    background: '#F8F5EE',
                    border: '1px solid #D8D3C8',
                    borderRadius: 8,
                    padding: '14px 18px',
                    display: 'flex',
                    flexDirection: 'column',
                    gap: 10,
                    marginBottom: 24
                  }}
                >
                  {currentStep.details.map((detail, idx) => (
                    <div key={idx} style={{ display: 'flex', justifyContent: 'space-between', gap: 16, fontSize: '0.85rem' }}>
                      <span style={{ color: '#5C5752', fontWeight: 600, flexShrink: 0 }}>{detail.label}:</span>
                      <span style={{ color: '#1E293B', textAlign: 'right', fontWeight: 500 }}>{detail.value}</span>
                    </div>
                  ))}
                </div>

                {/* Progress Bar */}
                <div style={{ width: '100%', height: 4, background: '#E8E2D8', borderRadius: 2, marginBottom: 20 }}>
                  <div
                    style={{
                      height: '100%',
                      background: '#1E293B',
                      borderRadius: 2,
                      width: `${(currentStep.stepNumber / 7) * 100}%`,
                      transition: 'width 0.25s ease'
                    }}
                  />
                </div>

                {/* Controls (Section 16: Back, Next step, Skip tour, Exit) */}
                <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between', gap: 12 }}>
                  <button
                    onClick={handleClose}
                    style={{
                      fontSize: '0.85rem',
                      color: '#7A756E',
                      cursor: 'pointer'
                    }}
                  >
                    Skip tour
                  </button>

                  <div style={{ display: 'flex', gap: 10 }}>
                    {currentStepIndex > 0 && (
                      <button
                        onClick={handleBack}
                        style={{
                          background: '#FFFFFF',
                          border: '1px solid #D8D3C8',
                          color: '#1E293B',
                          padding: '9px 16px',
                          borderRadius: 6,
                          fontSize: '0.88rem',
                          fontWeight: 600,
                          cursor: 'pointer',
                          display: 'inline-flex',
                          alignItems: 'center',
                          gap: 4
                        }}
                      >
                        <ChevronLeft size={16} />
                        <span>Back</span>
                      </button>
                    )}

                    <button
                      onClick={handleNext}
                      style={{
                        background: '#1E293B',
                        color: '#FFFFFF',
                        border: 'none',
                        padding: '9px 18px',
                        borderRadius: 6,
                        fontSize: '0.88rem',
                        fontWeight: 600,
                        cursor: 'pointer',
                        display: 'inline-flex',
                        alignItems: 'center',
                        gap: 6
                      }}
                    >
                      <span>{currentStep.actionLabel}</span>
                      <ChevronRight size={16} />
                    </button>
                  </div>
                </div>
              </div>
            ) : (
              /* Completion State (Section 16) */
              <div style={{ padding: '32px 28px', textAlign: 'center' }}>
                <div
                  style={{
                    width: 56,
                    height: 56,
                    borderRadius: '50%',
                    background: '#E8F3EC',
                    color: '#166534',
                    display: 'flex',
                    alignItems: 'center',
                    justifyContent: 'center',
                    margin: '0 auto 16px'
                  }}
                >
                  <CheckCircle2 size={32} />
                </div>

                <h3 style={{ fontSize: '1.3rem', color: '#1E293B', marginBottom: 6, fontWeight: 700 }}>
                  Campaign approved with proof.
                </h3>
                <p style={{ fontSize: '0.9rem', color: '#5C5752', marginBottom: 24 }}>
                  The Northstar Membership draft is now certified with a tamper-evident Content Passport.
                </p>

                {/* Completion Metric Chips */}
                <div
                  style={{
                    display: 'grid',
                    gridTemplateColumns: 'repeat(3, 1fr)',
                    gap: 12,
                    background: '#F8F5EE',
                    border: '1px solid #D8D3C8',
                    borderRadius: 8,
                    padding: '16px',
                    marginBottom: 28
                  }}
                >
                  <div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#1E293B' }}>3</div>
                    <div style={{ fontSize: '0.78rem', color: '#5C5752' }}>findings reviewed</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#B58A1F' }}>2</div>
                    <div style={{ fontSize: '0.78rem', color: '#5C5752' }}>suggestions applied</div>
                  </div>
                  <div>
                    <div style={{ fontSize: '1.25rem', fontWeight: 700, color: '#166534' }}>1</div>
                    <div style={{ fontSize: '0.78rem', color: '#5C5752' }}>human approval</div>
                  </div>
                </div>

                <div style={{ display: 'flex', justifyContent: 'center', gap: 12 }}>
                  <button
                    onClick={handleOpenWorkspace}
                    style={{
                      background: '#1E293B',
                      color: '#FFFFFF',
                      padding: '10px 20px',
                      borderRadius: 6,
                      fontSize: '0.9rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6
                    }}
                  >
                    <span>Open workspace</span>
                    <ArrowRight size={14} />
                  </button>

                  <button
                    onClick={handleRestart}
                    style={{
                      background: '#FFFFFF',
                      border: '1px solid #D8D3C8',
                      color: '#1E293B',
                      padding: '10px 18px',
                      borderRadius: 6,
                      fontSize: '0.9rem',
                      fontWeight: 600,
                      cursor: 'pointer',
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 6
                    }}
                  >
                    <RotateCcw size={14} />
                    <span>Restart tour</span>
                  </button>
                </div>
              </div>
            )}
          </div>
        </div>
      )}
    </>
  );
};
