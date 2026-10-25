'use client';

import React, { useState, useEffect, Suspense, useTransition } from 'react';
import { useSearchParams } from 'next/navigation';
import { PolicyCard, PolicyFilterState } from '@/types/policy';
import { policyClient } from '@/lib/api/policyClient';
import { PolicyCardItem } from '@/components/policies/PolicyCardItem';
import { PolicyFilters } from '@/components/policies/PolicyFilters';
import { PolicyDetailDrawer } from '@/components/policies/PolicyDetailDrawer';
import { PolicyFormModal } from '@/components/policies/PolicyFormModal';
import styles from './page.module.css';

function PolicyLibraryContent() {
  const searchParams = useSearchParams();
  const initialCategory = searchParams.get('cat') || 'all';

  const [filters, setFilters] = useState<PolicyFilterState>({
    searchQuery: '',
    category: initialCategory,
    status: 'all',
    brandId: 'all',
    sortBy: 'updated_desc',
  });

  const [policies, setPolicies] = useState<PolicyCard[]>([]);
  const [totalCount, setTotalCount] = useState(0);
  const [loading, setLoading] = useState(true);
  const [dataSource, setDataSource] = useState<string>('dev_adapter');

  const [selectedPolicy, setSelectedPolicy] = useState<PolicyCard | null>(null);
  const [editingPolicy, setEditingPolicy] = useState<PolicyCard | null>(null);
  const [isFormOpen, setIsFormOpen] = useState(false);

  const [, startTransition] = useTransition();

  const loadPolicies = async () => {
    setLoading(true);
    try {
      const result = await policyClient.getPolicies(filters);
      startTransition(() => {
        setPolicies(result.policies);
        setTotalCount(result.total);
        setDataSource(result.dataSource);
      });
    } catch (err) {
      console.error('Failed to load policies:', err);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    loadPolicies();
  }, [filters]);

  // Sync category if URL param changes
  useEffect(() => {
    const cat = searchParams.get('cat');
    if (cat && cat !== filters.category) {
      setFilters((prev) => ({ ...prev, category: cat }));
    }
  }, [searchParams]);

  const handleCreateNew = () => {
    setEditingPolicy(null);
    setIsFormOpen(true);
  };

  const handleEdit = (policy: PolicyCard) => {
    setEditingPolicy(policy);
    setIsFormOpen(true);
  };

  const handleSaved = (saved: PolicyCard) => {
    loadPolicies();
    if (selectedPolicy && selectedPolicy.id === saved.id) {
      setSelectedPolicy(saved);
    }
  };

  const handleArchive = async (id: string) => {
    try {
      await policyClient.archivePolicy(id);
      loadPolicies();
      setSelectedPolicy(null);
    } catch (err) {
      alert((err as Error).message || 'Failed to archive policy');
    }
  };

  const handleResetData = () => {
    if (confirm('Reset policies to original seed data? This restores the exact test fixture policies.')) {
      policyClient.resetToDefault();
      loadPolicies();
    }
  };

  // Metrics calculations
  const approvedCount = policies.filter((p) => p.status === 'approved' || !p.status).length;
  const totalRulesEnforced = policies.reduce((acc, p) => acc + (p.rules?.length || 0), 0);
  const prohibitedTermsCount = policies
    .filter((p) => p.category === 'terminology')
    .reduce((acc, p) => acc + (p.rules?.length || 1), 0);
  const activeOffersCount = policies.filter((p) => p.category === 'offer_validity').length;

  return (
    <div className={styles.container}>
      <div className={styles.headerSection}>
        <div className={styles.titleArea}>
          <h1 className={styles.title}>Brand Policy Library</h1>
          <p className={styles.subtitle}>
            Authoritative brand governance repository. Every active rule can be linked to source evidence.
          </p>
        </div>

        <div className={styles.storeStatusBadge}>
          <span className={styles.dotGreen} />
          <span>
            {dataSource === 'backend_api' ? 'FastAPI Service Connected' : 'Policy Repository &bull; Active Rules Enforced'}
          </span>
          <button type="button" className={styles.btnReset} onClick={handleResetData} title="Reset to official seed data">
            Reset Seed Data
          </button>
        </div>
      </div>

      {/* Metrics Bar */}
      <div className={styles.metricsBar}>
        <div className={styles.metricCard}>
          <div className={styles.metricValue}>{approvedCount}</div>
          <div className={styles.metricLabel}>Approved Policies</div>
        </div>
        <div className={styles.metricCard}>
          <div className={styles.metricValue} style={{ color: '#38bdf8' }}>{totalRulesEnforced}</div>
          <div className={styles.metricLabel}>Active Engine Rules</div>
        </div>
        <div className={styles.metricCard}>
          <div className={styles.metricValue} style={{ color: '#f43f5e' }}>{prohibitedTermsCount}</div>
          <div className={styles.metricLabel}>Prohibited Terms</div>
        </div>
        <div className={styles.metricCard}>
          <div className={styles.metricValue} style={{ color: '#f59e0b' }}>{activeOffersCount}</div>
          <div className={styles.metricLabel}>Tracked Campaigns</div>
        </div>
      </div>

      {/* Filters and Search */}
      <PolicyFilters
        filters={filters}
        onChange={setFilters}
        onCreateClick={handleCreateNew}
      />

      {/* Policy Grid */}
      {loading ? (
        <div className={styles.loadingSkeleton} data-tour="policies-grid">
          <div className={styles.skeletonCard} />
          <div className={styles.skeletonCard} />
          <div className={styles.skeletonCard} />
        </div>
      ) : policies.length > 0 ? (
        <div className={styles.grid} data-tour="policies-grid">
          {policies.map((policy) => (
            <PolicyCardItem
              key={policy.id}
              policy={policy}
              onSelect={setSelectedPolicy}
              onEdit={handleEdit}
            />
          ))}
        </div>
      ) : (
        <div className={styles.emptyState}>
          <h2 className={styles.emptyTitle}>No policies match your criteria</h2>
          <p className={styles.emptyDesc}>
            Try clearing search keywords or switching category filters to display all policies.
          </p>
          <button
            type="button"
            className={styles.btnReset}
            style={{ padding: '8px 16px', fontSize: '0.9rem' }}
            onClick={() => setFilters({ searchQuery: '', category: 'all', status: 'all', brandId: 'all', sortBy: 'updated_desc' })}
          >
            Clear All Filters
          </button>
        </div>
      )}

      {/* Policy Details Drawer */}
      <PolicyDetailDrawer
        policy={selectedPolicy}
        onClose={() => setSelectedPolicy(null)}
        onEdit={(p) => {
          setSelectedPolicy(null);
          handleEdit(p);
        }}
        onArchive={handleArchive}
      />

      {/* Create / Edit Modal */}
      <PolicyFormModal
        isOpen={isFormOpen}
        initialPolicy={editingPolicy}
        onClose={() => setIsFormOpen(false)}
        onSaved={handleSaved}
      />
    </div>
  );
}

export default function PolicyLibraryPage() {
  return (
    <Suspense fallback={<div className={styles.container}>Loading Policy Library...</div>}>
      <PolicyLibraryContent />
    </Suspense>
  );
}
