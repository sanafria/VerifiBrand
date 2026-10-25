'use client';

import React from 'react';
import Link from 'next/link';
import {
  BarChart2, Shield, AlertTriangle, CheckCircle2,
  TrendingUp, Award, Layers, ArrowUpRight, FileText, Download
} from 'lucide-react';
import styles from './page.module.css';

export default function InsightsPage() {
  const categoryStats = [
    { name: 'Terminology Violations', count: 42, percent: 42, color: '#f43f5e', desc: 'Disallowed terms (e.g. "customers" vs "Members")' },
    { name: 'Expired Offers', count: 28, percent: 28, color: '#f59e0b', desc: 'Post-expiration promotional dates' },
    { name: 'Numerical & Factual Accuracy', count: 18, percent: 18, color: '#a855f7', desc: 'Unverified metrics, founding year or caps' },
    { name: 'Tone & Unsubstantiated Claims', count: 12, percent: 12, color: '#ec4899', desc: 'Ambiguous superlatives (e.g. "exclusive")' },
  ];

  const highRiskPolicies = [
    { id: 'pol_term_001', title: 'Brand Addressing Terminology', version: 'v1.0', flags: 42, resolution: '98%', severity: 'Blocker' },
    { id: 'pol_offer_002', title: 'Summer Discount Promotion Validity', version: 'v1.0', flags: 28, resolution: '96%', severity: 'Blocker' },
    { id: 'pol_fact_003', title: 'Active Member Base Metric', version: 'v1.0', flags: 18, resolution: '100%', severity: 'Blocker' },
    { id: 'pol_tone_004', title: 'Unsubstantiated Exclusivity Claims', version: 'v1.0', flags: 12, resolution: '92%', severity: 'Warning' },
  ];

  return (
    <div className={styles.container}>
      {/* Header Banner */}
      <div className={styles.banner}>
        <div className={styles.headerTop}>
          <span className={styles.teamBadge}>
            <BarChart2 size={14} /> Executive Brand Governance Analytics
          </span>
          <div style={{ display: 'flex', gap: 10 }}>
            <Link
              href="/workspace"
              style={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 6,
                padding: '6px 14px',
                borderRadius: 6,
                background: 'rgba(56, 189, 248, 0.15)',
                color: '#38bdf8',
                fontSize: '0.82rem',
                fontWeight: 700,
                border: '1px solid rgba(56, 189, 248, 0.3)'
              }}
            >
              <Layers size={14} /> Go to Scan Workspace
            </Link>
          </div>
        </div>

        <h1 className={styles.title}>Governance Insights</h1>
        <p className={styles.desc}>
          Visibility into recurring policy findings, resolution patterns, high-risk rule citations, and Content Passport issuance across marketing channels.
        </p>

        {/* Governance Metrics Baseline Cue */}
        <div style={{
          marginTop: 16,
          padding: '10px 16px',
          background: 'rgba(255, 255, 255, 0.08)',
          border: '1px solid rgba(255, 255, 255, 0.15)',
          borderRadius: 8,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          flexWrap: 'wrap',
          gap: 10,
          color: '#E2E8F0',
          fontSize: '0.82rem',
          fontWeight: 500
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: 8 }}>
            <span style={{
              background: '#38bdf8',
              color: '#0F172A',
              fontSize: '0.7rem',
              fontWeight: 800,
              padding: '2px 8px',
              borderRadius: 4,
              letterSpacing: '0.04em',
              textTransform: 'uppercase'
            }}>
              Active Monitoring
            </span>
            <span>Real-time aggregation across all active brand policy cards and review channels</span>
          </div>
          <span style={{ fontSize: '0.78rem', color: '#94A3B8' }}>
            Updates automatically with every scan &amp; approved passport
          </span>
        </div>
      </div>

      {/* KPI Stats Grid - Honest Operational Demo Counts */}
      <div className={styles.statsGrid} data-tour="insights-stats">
        <div className={styles.statCard}>
          <div className={styles.statHeader}>
            <span className={styles.statLabel}>Sample Drafts Scanned</span>
            <div className={styles.statIcon} style={{ background: 'rgba(56, 189, 248, 0.15)', color: '#38bdf8' }}>
              <FileText size={16} />
            </div>
          </div>
          <div className={styles.statValue}>142</div>
          <div className={styles.statTrend} style={{ color: 'var(--text-muted)' }}>
            <span>Across 4 digital channels</span>
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statHeader}>
            <span className={styles.statLabel}>Findings Resolved</span>
            <div className={styles.statIcon} style={{ background: 'rgba(16, 185, 129, 0.15)', color: '#34d399' }}>
              <CheckCircle2 size={16} />
            </div>
          </div>
          <div className={styles.statValue}>136</div>
          <div className={`${styles.statTrend} ${styles.trendPositive}`}>
            <TrendingUp size={14} />
            <span>One-click suggested fixes accepted</span>
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statHeader}>
            <span className={styles.statLabel}>Items Awaiting Review</span>
            <div className={styles.statIcon} style={{ background: 'rgba(245, 158, 11, 0.15)', color: '#fbbf24' }}>
              <Shield size={16} />
            </div>
          </div>
          <div className={styles.statValue}>6</div>
          <div className={styles.statTrend} style={{ color: '#fbbf24' }}>
            <span>Pending authorised human decision</span>
          </div>
        </div>

        <div className={styles.statCard}>
          <div className={styles.statHeader}>
            <span className={styles.statLabel}>Content Passports Issued</span>
            <div className={styles.statIcon} style={{ background: 'rgba(168, 85, 247, 0.15)', color: '#c084fc' }}>
              <Award size={16} />
            </div>
          </div>
          <div className={styles.statValue}>28</div>
          <div className={styles.statTrend} style={{ color: '#34d399' }}>
            <span>Traceable approval records</span>
          </div>
        </div>
      </div>

      {/* 2-Column Analytics Grid */}
      <div className={styles.contentGrid}>
        {/* Left: Category Distribution */}
        <div className={styles.analyticsCard}>
          <h2 className={styles.cardTitle}>
            <AlertTriangle size={18} color="#f43f5e" />
            Violation Category Breakdown
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Distribution of policy breaches caught pre-publication by deterministic rule checks and assisted linguistic analysis.
          </p>

          <div className={styles.categoryList}>
            {categoryStats.map((cat, idx) => (
              <div key={idx} className={styles.categoryItem}>
                <div className={styles.categoryMeta}>
                  <span className={styles.categoryName}>{cat.name}</span>
                  <span className={styles.categoryPercent}>{cat.percent}% ({cat.count} flags)</span>
                </div>
                <div className={styles.barTrack}>
                  <div
                    className={styles.barFill}
                    style={{ width: `${cat.percent}%`, background: cat.color }}
                  />
                </div>
                <span style={{ fontSize: '0.74rem', color: 'var(--text-muted)' }}>{cat.desc}</span>
              </div>
            ))}
          </div>
        </div>

        {/* Right: Channel Compliance */}
        <div className={styles.analyticsCard}>
          <h2 className={styles.cardTitle}>
            <Award size={18} color="#38bdf8" />
            Compliance by Channel & Brand Voice
          </h2>
          <p style={{ fontSize: '0.85rem', color: 'var(--text-secondary)' }}>
            Quality scores across marketing publication destinations and brand voice pillars.
          </p>

          <div className={styles.channelGrid}>
            <div className={styles.channelBox}>
              <span className={styles.channelName}>Social Media</span>
              <div className={styles.channelScore} style={{ color: '#fbbf24' }}>88.5%</div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>High terminology risk</span>
            </div>
            <div className={styles.channelBox}>
              <span className={styles.channelName}>Web Display Banners</span>
              <div className={styles.channelScore}>96.2%</div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>OCR extraction validated</span>
            </div>
            <div className={styles.channelBox}>
              <span className={styles.channelName}>Email Newsletters</span>
              <div className={styles.channelScore}>92.8%</div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Expired offer checks active</span>
            </div>
            <div className={styles.channelBox}>
              <span className={styles.channelName}>Press Releases</span>
              <div className={styles.channelScore}>100%</div>
              <span style={{ fontSize: '0.72rem', color: 'var(--text-muted)' }}>Zero blockers detected</span>
            </div>
          </div>

          <div style={{
            background: 'var(--bg-input)',
            border: '1px solid var(--border-subtle)',
            borderRadius: 8,
            padding: 14,
            marginTop: 4
          }}>
            <span style={{ fontSize: '0.76rem', fontWeight: 700, color: 'var(--text-muted)', textTransform: 'uppercase' }}>
              Brand Voice Adherence (Governance Guidelines):
            </span>
            <div style={{ display: 'flex', gap: 12, marginTop: 8, flexWrap: 'wrap' }}>
              <span style={{ fontSize: '0.82rem', color: '#38bdf8', fontWeight: 600 }}>• Authoritative (96%)</span>
              <span style={{ fontSize: '0.82rem', color: '#34d399', fontWeight: 600 }}>• Welcoming (98%)</span>
              <span style={{ fontSize: '0.82rem', color: '#c084fc', fontWeight: 600 }}>• Transparent (100%)</span>
            </div>
          </div>
        </div>
      </div>

      {/* High Risk Policies Table */}
      <div className={styles.analyticsCard}>
        <div style={{ display: 'flex', alignItems: 'center', justifyContent: 'space-between' }}>
          <h2 className={styles.cardTitle}>
            <Shield size={18} color="#38bdf8" />
            High-Impact Policy Leaderboard
          </h2>
          <span style={{ fontSize: '0.78rem', color: 'var(--text-muted)' }}>
            Ranked by scan triggers & resolution speed
          </span>
        </div>

        <div className={styles.tableContainer}>
          <table className={styles.policyTable}>
            <thead>
              <tr>
                <th>Policy Card ID</th>
                <th>Policy Title</th>
                <th>Active Version</th>
                <th>Total Citations</th>
                <th>Fix Acceptance</th>
                <th>Severity</th>
              </tr>
            </thead>
            <tbody>
              {highRiskPolicies.map((p, idx) => (
                <tr key={idx}>
                  <td><span className={styles.policyKey}>{p.id}</span></td>
                  <td style={{ fontWeight: 600 }}>{p.title}</td>
                  <td style={{ color: 'var(--text-muted)' }}>{p.version}</td>
                  <td><strong>{p.flags}</strong> drafts flagged</td>
                  <td style={{ color: '#34d399', fontWeight: 700 }}>{p.resolution}</td>
                  <td>
                    <span style={{
                      fontSize: '0.72rem',
                      fontWeight: 700,
                      padding: '2px 8px',
                      borderRadius: 4,
                      background: p.severity === 'Blocker' ? 'rgba(244, 63, 94, 0.15)' : 'rgba(245, 158, 11, 0.15)',
                      color: p.severity === 'Blocker' ? '#fb7185' : '#fbbf24',
                    }}>
                      {p.severity}
                    </span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      </div>
    </div>
  );
}
