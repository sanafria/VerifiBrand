'use client';

import React, { useState, useEffect, useRef, useCallback } from 'react';
import { usePathname, useRouter } from 'next/navigation';
import {
  Sparkles, ArrowRight, ArrowLeft, X, Check,
  Shield, Play, Layers, Compass, Zap, RefreshCw
} from 'lucide-react';
import styles from './GuidedTour.module.css';

export interface TourStep {
  id: string;
  route: string;
  targetSelector: string;
  title: string;
  badge: string;
  category: string;
  description: string;
  placement: 'top' | 'bottom' | 'left' | 'right';
  actionPrompt?: string;
  actionButtonText?: string;
  onExecuteAction?: () => void;
}

const TOUR_STEPS: TourStep[] = [
  {
    id: 'step-nav',
    route: '/workspace',
    targetSelector: '[data-tour="nav-tabs"]',
    title: 'Enterprise Brand Governance Hub',
    badge: 'Step 1 of 10',
    category: 'Product Suite',
    description: 'Welcome to VerifiBrand! This navigation bar lets you move between the Scan Workspace, Policy Library, Human Review Gate, Content Passports, Insights, and Audit Ledger.',
    placement: 'bottom',
  },
  {
    id: 'step-presets',
    route: '/workspace',
    targetSelector: '[data-tour="workspace-presets"]',
    title: 'Try a Sample Campaign',
    badge: 'Step 2 of 10',
    category: 'Quick Start',
    description: 'Start testing right away! Click "Sample with issues" to test unapproved claims and pricing violations, or "Compliant sample" to see a clean pass.',
    placement: 'bottom',
    actionPrompt: 'Want to test violations now?',
    actionButtonText: 'Load Sample with Issues',
    onExecuteAction: () => {
      const btn = document.querySelector('button[title*="terminology"]') as HTMLButtonElement | null;
      if (btn) btn.click();
    }
  },
  {
    id: 'step-dropzone',
    route: '/workspace',
    targetSelector: '[data-tour="workspace-dropzone"]',
    title: 'Drop Files, Graphics & PDFs (OCR)',
    badge: 'Step 3 of 10',
    category: 'Asset Ingestion',
    description: 'Have banner visual proofs, marketing images, or PDF one-pagers? Drag and drop them right here. PyMuPDF and Tesseract OCR automatically extract embedded copy for verification.',
    placement: 'bottom',
    actionPrompt: 'Try sample banner extraction?',
    actionButtonText: 'Load Image Sample',
    onExecuteAction: () => {
      const btn = document.querySelector('button[title*="img_clear_offer"]') as HTMLButtonElement | null;
      if (btn) btn.click();
    }
  },
  {
    id: 'step-textarea',
    route: '/workspace',
    targetSelector: '[data-tour="workspace-textarea"]',
    title: 'Live Creative Draft Editor',
    badge: 'Step 4 of 10',
    category: 'Copy Editor',
    description: 'Your marketing copy, social slogans, or extracted visual text appears here. Edit draft text in real time, view word counts, and see which active policies are evaluated.',
    placement: 'top',
  },
  {
    id: 'step-scan',
    route: '/workspace',
    targetSelector: '[data-tour="workspace-scan-btn"]',
    title: 'Review Draft for Findings',
    badge: 'Step 5 of 10',
    category: 'Deterministic Engine',
    description: 'Click "Review Draft for Findings" to run our deterministic policy engine and AdaptionLabs AI checks against all active brand guidelines.',
    placement: 'top',
    actionPrompt: 'Ready to scan the draft?',
    actionButtonText: 'Run Review Scan',
    onExecuteAction: () => {
      const btn = document.querySelector('[data-tour="workspace-scan-btn"]') as HTMLButtonElement | null;
      if (btn) btn.click();
    }
  },
  {
    id: 'step-findings',
    route: '/workspace',
    targetSelector: '[data-tour="workspace-findings"]',
    title: 'Evidence-Backed Findings & Fixes',
    badge: 'Step 6 of 10',
    category: 'Verbatim Citations',
    description: 'Every flagged claim links verbatim to an authoritative Policy Card quotation. Creators can accept 1-click suggested corrections before sending to the reviewer gate.',
    placement: 'left',
  },
  {
    id: 'step-policies',
    route: '/policies',
    targetSelector: '[data-tour="policies-grid"]',
    title: 'Brand Policy Library',
    badge: 'Step 7 of 10',
    category: 'Governance Rules',
    description: 'Here are all active Brand Policies enforced across your organization: approved promotional claims, prohibited terminology, active pricing dates, and tone guidelines.',
    placement: 'top',
  },
  {
    id: 'step-review',
    route: '/review',
    targetSelector: '[data-tour="review-queue"]',
    title: 'Authorised Reviewer Gate',
    badge: 'Step 8 of 10',
    category: 'Human Sign-off',
    description: 'AI assists with findings, but authorized humans make the final call. Reviewers inspect flags, override with defensible justification when appropriate, and issue approvals.',
    placement: 'right',
  },
  {
    id: 'step-passports',
    route: '/passports',
    targetSelector: '[data-tour="passport-card"]',
    title: 'Tamper-Evident Content Passport',
    badge: 'Step 9 of 10',
    category: 'Cryptographic Seal',
    description: 'Approved drafts receive an immutable Content Passport sealed with SHA-256. If downstream teams or channels alter copy, the integrity check alerts immediately.',
    placement: 'top',
  },
  {
    id: 'step-audit',
    route: '/audit',
    targetSelector: '[data-tour="audit-timeline"]',
    title: 'Cryptographic Audit Ledger',
    badge: 'Step 10 of 10',
    category: 'Complete Defensibility',
    description: 'Every scan, rule increment, and reviewer decision is logged in chronological order with SHA-256 signatures, providing audit-ready compliance proof.',
    placement: 'top',
  },
];

export const GuidedTour: React.FC = () => {
  const [isActive, setIsActive] = useState(false);
  const [stepIndex, setStepIndex] = useState(0);
  const [isNavigating, setIsNavigating] = useState(false);
  const [showWelcome, setShowWelcome] = useState(false);
  const [targetRect, setTargetRect] = useState<{
    top: number;
    left: number;
    width: number;
    height: number;
  } | null>(null);
  const [popoverPos, setPopoverPos] = useState<{ top: number; left: number }>({ top: 120, left: 120 });

  const pathname = usePathname();
  const router = useRouter();
  const retryTimerRef = useRef<NodeJS.Timeout | null>(null);

  const currentStep = TOUR_STEPS[stepIndex] || TOUR_STEPS[0];

  // Show welcome invitation only on first visit for workspace routes
  useEffect(() => {
    if (typeof window !== 'undefined') {
      const hasSeen = localStorage.getItem('has_seen_interactive_tour');
      if (!hasSeen && (pathname === '/workspace' || pathname === '/review')) {
        const timer = setTimeout(() => setShowWelcome(true), 900);
        return () => clearTimeout(timer);
      }
    }
  }, [pathname]);

  // Listen for replay event from Navbar or anywhere in the app
  useEffect(() => {
    const handleOpenTour = () => {
      setShowWelcome(false);
      setStepIndex(0);
      setIsActive(true);
    };

    window.addEventListener('open-demo-tour', handleOpenTour);
    return () => window.removeEventListener('open-demo-tour', handleOpenTour);
  }, []);

  // Update target rect and position popover
  const updateSpotlightPosition = useCallback(() => {
    if (!isActive) return;

    const el = document.querySelector(currentStep.targetSelector) as HTMLElement | null;
    if (!el) return;

    const rect = el.getBoundingClientRect();
    const scrollY = window.scrollY || window.pageYOffset || 0;
    const scrollX = window.scrollX || window.pageXOffset || 0;

    const padding = 8;
    const top = rect.top + scrollY - padding;
    const left = rect.left + scrollX - padding;
    const width = rect.width + padding * 2;
    const height = rect.height + padding * 2;

    setTargetRect({ top, left, width, height });

    // Compute popover card position (fixed in viewport)
    const cardWidth = 380;
    const cardHeight = 280;
    const vpWidth = window.innerWidth;
    const vpHeight = window.innerHeight;

    let pTop = 100;
    let pLeft = 100;

    switch (currentStep.placement) {
      case 'bottom':
        pTop = rect.bottom + 18;
        pLeft = rect.left + rect.width / 2 - cardWidth / 2;
        break;
      case 'top':
        pTop = rect.top - cardHeight - 18;
        pLeft = rect.left + rect.width / 2 - cardWidth / 2;
        break;
      case 'left':
        pTop = rect.top + rect.height / 2 - cardHeight / 2;
        pLeft = rect.left - cardWidth - 20;
        break;
      case 'right':
        pTop = rect.top + rect.height / 2 - cardHeight / 2;
        pLeft = rect.right + 20;
        break;
    }

    // Boundary check so popover card never goes offscreen
    if (pLeft + cardWidth > vpWidth - 16) {
      pLeft = vpWidth - cardWidth - 16;
    }
    if (pLeft < 16) {
      pLeft = 16;
    }
    if (pTop + cardHeight > vpHeight - 16) {
      pTop = vpHeight - cardHeight - 16;
    }
    if (pTop < 75) {
      // Below navbar
      pTop = 75;
    }

    setPopoverPos({ top: pTop, left: pLeft });
  }, [isActive, currentStep]);

  // Handle route navigation and target finding when step changes
  useEffect(() => {
    if (!isActive) return;

    if (retryTimerRef.current) {
      clearInterval(retryTimerRef.current);
    }

    const targetRoute = currentStep.route;
    if (pathname !== targetRoute) {
      setIsNavigating(true);
      router.push(targetRoute);
    }

    let attempts = 0;
    const maxAttempts = 30;

    retryTimerRef.current = setInterval(() => {
      attempts++;
      const el = document.querySelector(currentStep.targetSelector) as HTMLElement | null;

      if (el) {
        if (retryTimerRef.current) clearInterval(retryTimerRef.current);
        setIsNavigating(false);

        // Smooth self-scroll to target element
        el.scrollIntoView({
          behavior: 'smooth',
          block: 'center',
          inline: 'nearest',
        });

        // Small delay to allow scroll and animation to settle
        setTimeout(() => {
          updateSpotlightPosition();
        }, 250);
      } else if (attempts >= maxAttempts) {
        if (retryTimerRef.current) clearInterval(retryTimerRef.current);
        setIsNavigating(false);
      }
    }, 120);

    return () => {
      if (retryTimerRef.current) clearInterval(retryTimerRef.current);
    };
  }, [isActive, stepIndex, pathname, currentStep, router, updateSpotlightPosition]);

  // Re-measure on window resize & scroll
  useEffect(() => {
    if (!isActive) return;

    const handleWindowChange = () => {
      updateSpotlightPosition();
    };

    window.addEventListener('resize', handleWindowChange);
    window.addEventListener('scroll', handleWindowChange, { passive: true });

    return () => {
      window.removeEventListener('resize', handleWindowChange);
      window.removeEventListener('scroll', handleWindowChange);
    };
  }, [isActive, updateSpotlightPosition]);

  const handleStartTour = () => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('has_seen_interactive_tour', 'true');
    }
    setShowWelcome(false);
    setStepIndex(0);
    setIsActive(true);
  };

  const handleDismissWelcome = () => {
    if (typeof window !== 'undefined') {
      localStorage.setItem('has_seen_interactive_tour', 'true');
    }
    setShowWelcome(false);
  };

  const handleNext = () => {
    if (stepIndex < TOUR_STEPS.length - 1) {
      setStepIndex(prev => prev + 1);
    } else {
      // Completed!
      handleClose();
    }
  };

  const handleBack = () => {
    if (stepIndex > 0) {
      setStepIndex(prev => prev - 1);
    }
  };

  const handleClose = () => {
    setIsActive(false);
    if (typeof window !== 'undefined') {
      localStorage.setItem('has_seen_interactive_tour', 'true');
    }
  };

  const progressPercent = Math.round(((stepIndex + 1) / TOUR_STEPS.length) * 100);

  return (
    <>
      {/* First-time Welcome Banner in Bottom-Left */}
      {showWelcome && !isActive && (
        <div className={styles.welcomeBanner}>
          <div className={styles.welcomeText}>
            <div className={styles.welcomeTitle}>
              <Sparkles size={14} color="#38bdf8" />
              <span>Interactive Tutorial</span>
            </div>
            <div>Take the guided 2-minute tour to see how drafts turn into certified Content Passports.</div>
          </div>
          <div className={styles.welcomeActions}>
            <button
              type="button"
              className={styles.welcomeStartBtn}
              onClick={handleStartTour}
            >
              Start Tour
            </button>
            <button
              type="button"
              className={styles.welcomeDismissBtn}
              onClick={handleDismissWelcome}
              title="Dismiss"
            >
              ✕
            </button>
          </div>
        </div>
      )}

      {/* Persistent Floating Launcher in Bottom-Right */}
      {!isActive && (
        <button
          type="button"
          className={styles.floatingLauncher}
          onClick={handleStartTour}
          title="Open interactive walkthrough tutorial"
        >
          <span className={styles.pulseOrb} />
          <Compass size={16} color="#38bdf8" />
          <span>Interactive Demo Tour</span>
        </button>
      )}

      {/* Active Guided Tour Spotlight Overlay */}
      {isActive && (
        <>
          {/* Navigating route indicator */}
          {isNavigating && (
            <div className={styles.navigatingNotice}>
              <RefreshCw size={14} className="animate-spin" />
              <span>Navigating to {currentStep.category}...</span>
            </div>
          )}

          <div className={styles.tourContainer}>
            {/* Glowing Spotlight Cutout */}
            {targetRect && (
              <>
                <div
                  className={styles.spotlight}
                  style={{
                    top: targetRect.top,
                    left: targetRect.left,
                    width: targetRect.width,
                    height: targetRect.height,
                  }}
                />

                {/* Pulsing Beacon pointing at element */}
                <div
                  className={styles.beacon}
                  style={{
                    top: targetRect.top - 32,
                    left: Math.max(16, targetRect.left + 12),
                  }}
                >
                  <span className={styles.beaconDot} />
                  <span>Pointing Here</span>
                </div>
              </>
            )}
          </div>

          {/* Interactive Popover Tooltip Card */}
          <div
            className={styles.popoverCard}
            style={{
              top: popoverPos.top,
              left: popoverPos.left,
            }}
          >
            {/* Card Header */}
            <div className={styles.cardHeader}>
              <div className={styles.badgeGroup}>
                <span className={styles.stepPill}>{currentStep.badge}</span>
                <span className={styles.categoryBadge}>{currentStep.category}</span>
              </div>
              <button
                type="button"
                className={styles.closeBtn}
                onClick={handleClose}
                title="Exit Tour"
              >
                <X size={16} />
              </button>
            </div>

            {/* Card Content */}
            <h3 className={styles.cardTitle}>
              <Zap size={18} color="#38bdf8" />
              <span>{currentStep.title}</span>
            </h3>
            <p className={styles.cardDescription}>{currentStep.description}</p>

            {/* In-Card Interactive Action Button if defined */}
            {currentStep.actionButtonText && (
              <div className={styles.cardActionBox}>
                <span className={styles.cardActionText}>
                  {currentStep.actionPrompt || 'Try this feature:'}
                </span>
                <button
                  type="button"
                  className={styles.cardActionBtn}
                  onClick={() => {
                    if (currentStep.onExecuteAction) {
                      currentStep.onExecuteAction();
                    }
                  }}
                >
                  <Play size={11} fill="currentColor" />
                  <span>{currentStep.actionButtonText}</span>
                </button>
              </div>
            )}

            {/* Progress Bar */}
            <div className={styles.progressBarTrack}>
              <div
                className={styles.progressBarFill}
                style={{ width: `${progressPercent}%` }}
              />
            </div>

            {/* Card Controls Footer */}
            <div className={styles.cardFooter}>
              <button
                type="button"
                className={styles.skipBtn}
                onClick={handleClose}
              >
                Skip Tour
              </button>

              <div className={styles.btnGroup}>
                <button
                  type="button"
                  className={styles.backBtn}
                  onClick={handleBack}
                  disabled={stepIndex === 0}
                >
                  <ArrowLeft size={14} />
                  <span>Back</span>
                </button>

                <button
                  type="button"
                  className={styles.nextBtn}
                  onClick={handleNext}
                >
                  {stepIndex === TOUR_STEPS.length - 1 ? (
                    <>
                      <span>Finish</span>
                      <Check size={14} />
                    </>
                  ) : (
                    <>
                      <span>Next</span>
                      <ArrowRight size={14} />
                    </>
                  )}
                </button>
              </div>
            </div>
          </div>
        </>
      )}
    </>
  );
};
