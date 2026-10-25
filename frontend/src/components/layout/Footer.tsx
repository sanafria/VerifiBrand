import React from 'react';
import Link from 'next/link';
import styles from './Footer.module.css';

export const Footer: React.FC = () => {
  return (
    <footer className={styles.footer}>
      <div className={styles.container}>
        <div className={styles.topRow}>
          <div className={styles.metaInfo}>
            <div className={styles.title}>VerifiBrand</div>
            <div className={styles.subtitle}>
              VerifiBrand checks the content. Your people make the decision. A shared review layer for content, brand rules, and verifiable approvals.
            </div>
          </div>

          <div className={styles.linksCol}>
            <div className={styles.linkGroup}>
              <div className={styles.groupTitle}>Product</div>
              <Link href="/features" className={styles.footerLink}>Features</Link>
              <Link href="/how-it-works" className={styles.footerLink}>How it works</Link>
              <Link href="/security" className={styles.footerLink}>Security &amp; Responsible AI</Link>
              <Link href="/demo-preview" className={styles.footerLink}>Sample review</Link>
            </div>

            <div className={styles.linkGroup}>
              <div className={styles.groupTitle}>Workspace</div>
              <Link href="/workspace" className={styles.footerLink}>Scan Workspace</Link>
              <Link href="/policies" className={styles.footerLink}>Policy Library</Link>
              <Link href="/review" className={styles.footerLink}>Review Gate</Link>
              <Link href="/passports" className={styles.footerLink}>Content Passports</Link>
            </div>

            <div className={styles.linkGroup}>
              <div className={styles.groupTitle}>Governance</div>
              <Link href="/insights" className={styles.footerLink}>Recurring Insights</Link>
              <Link href="/audit" className={styles.footerLink}>Audit Ledger</Link>
            </div>
          </div>
        </div>

        <div className={styles.bottomRow}>
          <div>
            VerifiBrand &bull; Team HexaForce &bull; FutureStack Hackathon by WeCodeCooders
          </div>
          <div className={styles.statusIndicator}>
            <span className={styles.greenDot} />
            <span>AI-assisted findings &bull; Human-controlled decisions</span>
          </div>
        </div>
      </div>
    </footer>
  );
};
