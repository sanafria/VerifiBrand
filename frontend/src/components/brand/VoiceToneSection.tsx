'use client';

import React from 'react';
import Link from 'next/link';
import { BrandProfile } from '@/types/policy';
import styles from './VoiceToneSection.module.css';

interface VoiceToneSectionProps {
  brand: BrandProfile;
}

export const VoiceToneSection: React.FC<VoiceToneSectionProps> = ({ brand }) => {
  return (
    <section className={styles.section} aria-labelledby="voice-pillars-title">
      <div className={styles.header}>
        <div className={styles.titleArea}>
          <h2 id="voice-pillars-title" className={styles.title}>Brand Voice &amp; Tone Architecture</h2>
          <p className={styles.subtitle}>
            Principles governed by AI tone validation and deterministic editorial policies.
          </p>
        </div>
        <Link href="/policies?cat=tone" className={styles.btnLink}>
          <span>View Tone Policies</span>
          <span>&rarr;</span>
        </Link>
      </div>

      <div className={styles.grid}>
        {brand.voicePillars.map((pillar, idx) => (
          <div key={idx} className={styles.pillarCard}>
            <h3 className={styles.pillarTitle}>{pillar.title}</h3>
            <p className={styles.pillarDesc}>{pillar.description}</p>

            <div className={styles.listsRow}>
              <div className={styles.listCol}>
                <span className={styles.listHeaderDo}>✓ Mandated &ldquo;Dos&rdquo;</span>
                <ul className={styles.listUl}>
                  {pillar.dos.map((item, i) => (
                    <li key={i} className={styles.itemDo}>
                      <span style={{ color: '#10b981' }}>•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>

              <div className={styles.listCol}>
                <span className={styles.listHeaderDont}>✕ Prohibited &ldquo;Don&apos;ts&rdquo;</span>
                <ul className={styles.listUl}>
                  {pillar.donts.map((item, i) => (
                    <li key={i} className={styles.itemDont}>
                      <span style={{ color: '#f43f5e' }}>•</span>
                      <span>{item}</span>
                    </li>
                  ))}
                </ul>
              </div>
            </div>
          </div>
        ))}
      </div>
    </section>
  );
};
