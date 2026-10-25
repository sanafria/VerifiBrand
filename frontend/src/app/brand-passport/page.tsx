'use client';

import React, { useState, useEffect } from 'react';
import Link from 'next/link';
import { BrandProfile, PolicyCard } from '@/types/policy';
import { policyClient } from '@/lib/api/policyClient';
import { BrandHeader } from '@/components/brand/BrandHeader';
import { VoiceToneSection } from '@/components/brand/VoiceToneSection';
import { TerminologySection } from '@/components/brand/TerminologySection';
import { GuardrailsSection } from '@/components/brand/GuardrailsSection';
import { VisualAssetsSection } from '@/components/brand/VisualAssetsSection';
import styles from './page.module.css';

export default function BrandPassportPage() {
  const [brands, setBrands] = useState<BrandProfile[]>([]);
  const [selectedBrand, setSelectedBrand] = useState<BrandProfile | null>(null);
  const [policies, setPolicies] = useState<PolicyCard[]>([]);
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const loadData = async () => {
      try {
        const brandList = await policyClient.getBrandProfiles();
        setBrands(brandList);
        if (brandList.length > 0) {
          setSelectedBrand(brandList[0]);
        }
        const policyData = await policyClient.getPolicies();
        setPolicies(policyData.policies);
      } catch (err) {
        console.error('Failed to load Brand Passport:', err);
      } finally {
        setLoading(false);
      }
    };
    loadData();
  }, []);

  const handleExportPassport = () => {
    if (!selectedBrand) return;
    const passportExport = {
      brandProfile: selectedBrand,
      governancePolicies: policies.map((p) => ({
        id: p.id,
        version: p.version,
        title: p.title,
        category: p.category,
        rules: p.rules,
        quote: p.metadata.quote,
      })),
      exportedAt: new Date().toISOString(),
      governanceCoreVersion: 'VerifiBrand Governance Blueprint v1.0',
    };
    const blob = new Blob([JSON.stringify(passportExport, null, 2)], { type: 'application/json' });
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = `${selectedBrand.id}_brand_passport.json`;
    a.click();
    URL.revokeObjectURL(url);
  };

  if (loading || !selectedBrand) {
    return <div className={styles.container}>Loading Brand Passport...</div>;
  }

  return (
    <div className={styles.container}>
      {/* 1. Header Overview */}
      <BrandHeader
        brand={selectedBrand}
        brands={brands}
        onSelectBrand={setSelectedBrand}
      />

      {/* Action / Quick-Nav Bar */}
      <div className={styles.actionBar}>
        <div className={styles.actionInfo}>
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
            <circle cx="12" cy="12" r="10" />
            <line x1="12" y1="16" x2="12" y2="12" />
            <line x1="12" y1="8" x2="12.01" y2="8" />
          </svg>
          <span>
            Brand Guidelines aggregate approved voice, tone, and identity rules to power the review engine.
          </span>
        </div>
        <div className={styles.actionButtons}>
          <button type="button" className={styles.btnExport} onClick={handleExportPassport}>
            <svg width="14" height="14" viewBox="0 0 24 24" fill="none" stroke="currentColor" strokeWidth="2">
              <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
              <polyline points="7 10 12 15 17 10" />
              <line x1="12" y1="15" x2="12" y2="3" />
            </svg>
            <span>Export Passport JSON</span>
          </button>
          <Link href="/policies" className={styles.btnPrimary}>
            <span>Manage Policies ({policies.length})</span>
            <span>&rarr;</span>
          </Link>
        </div>
      </div>

      {/* 2. Brand Voice & Tone Architecture */}
      <VoiceToneSection brand={selectedBrand} />

      {/* 3. Approved vs Prohibited Terminology */}
      <TerminologySection policies={policies} />

      {/* 4. Guardrails (Numerical, Offers, Claims) */}
      <GuardrailsSection policies={policies} />

      {/* 5. Visual Identity & Assets */}
      <VisualAssetsSection brand={selectedBrand} />
    </div>
  );
}
