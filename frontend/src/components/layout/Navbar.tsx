'use client';

import React from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import {
  Shield, BookOpen, Layers, CheckCircle2,
  BarChart2, History, Play, ArrowRight, Home
} from 'lucide-react';
import styles from './Navbar.module.css';

export const Navbar: React.FC = () => {
  const pathname = usePathname();
  const isPublicRoute = pathname === '/' || pathname === '/how-it-works' || pathname === '/features' || pathname === '/security' || pathname === '/demo-preview';

  const triggerTour = () => {
    if (typeof window !== 'undefined') {
      window.dispatchEvent(new CustomEvent('open-demo-tour'));
    }
  };

  return (
    <header className={styles.navbar}>
      <div className={styles.container}>
        <div className={styles.brandGroup}>
          <Link href="/" className={styles.logo}>
            <div className={styles.shieldIcon}>
              <Shield size={18} strokeWidth={2.5} />
            </div>
            <span>VerifiBrand</span>
          </Link>
          <span className={styles.trustTag}>
            AI-assisted findings · Human decisions
          </span>
        </div>

        {isPublicRoute ? (
          /* Public Navigation (Section 7) */
          <nav className={styles.navLinks} aria-label="Public Navigation">
            <Link
              href="/features"
              className={`${styles.navLink} ${pathname === '/features' ? styles.navLinkActive : ''}`}
            >
              <span>Product</span>
            </Link>

            <Link
              href="/how-it-works"
              className={`${styles.navLink} ${pathname === '/how-it-works' ? styles.navLinkActive : ''}`}
            >
              <span>How it works</span>
            </Link>

            <Link
              href="/security"
              className={`${styles.navLink} ${pathname === '/security' ? styles.navLinkActive : ''}`}
            >
              <span>Security</span>
            </Link>
          </nav>
        ) : (
          /* Workspace Product Navigation */
          <nav className={styles.navLinks} aria-label="Workspace Navigation">
            <Link
              href="/workspace"
              className={`${styles.navLink} ${pathname === '/workspace' ? styles.navLinkActive : ''}`}
              title="Interactive Scan Workspace"
            >
              <Layers size={15} />
              <span>Workspace</span>
            </Link>

            <Link
              href="/policies"
              className={`${styles.navLink} ${pathname === '/policies' ? styles.navLinkActive : ''}`}
              title="Brand Policy Library"
            >
              <BookOpen size={15} />
              <span>Policies</span>
            </Link>

            <Link
              href="/review"
              className={`${styles.navLink} ${pathname === '/review' ? styles.navLinkActive : ''}`}
              title="Human Reviewer Approval Gate"
            >
              <Shield size={15} />
              <span>Review Gate</span>
            </Link>

            <Link
              href="/passports"
              className={`${styles.navLink} ${pathname === '/passports' ? styles.navLinkActive : ''}`}
              title="Content Passports"
            >
              <CheckCircle2 size={15} />
              <span>Passports</span>
            </Link>

            <Link
              href="/insights"
              className={`${styles.navLink} ${pathname === '/insights' ? styles.navLinkActive : ''}`}
              title="Governance Analytics"
            >
              <BarChart2 size={15} />
              <span>Insights</span>
            </Link>

            <Link
              href="/audit"
              className={`${styles.navLink} ${pathname === '/audit' ? styles.navLinkActive : ''}`}
              title="Audit Ledger"
            >
              <History size={15} />
              <span>Audit</span>
            </Link>
          </nav>
        )}

        <div className={styles.rightControls}>
          {isPublicRoute ? (
            <>
              <Link href="/demo-preview" className={styles.btnSample}>
                View a sample review
              </Link>
              <Link href="/workspace" className={styles.btnWorkspace}>
                <span>Open workspace</span>
                <ArrowRight size={14} />
              </Link>
            </>
          ) : (
            <>
              <button
                type="button"
                onClick={triggerTour}
                className={styles.btnTour}
                title="Replay the 7-step guided review tour"
              >
                <Play size={12} fill="currentColor" />
                <span>Replay tour</span>
              </button>
              <Link href="/" className={styles.btnSample} title="Return to public overview">
                <Home size={14} style={{ display: 'inline', marginRight: 4 }} />
                <span>Home</span>
              </Link>
            </>
          )}
        </div>
      </div>
    </header>
  );
};

