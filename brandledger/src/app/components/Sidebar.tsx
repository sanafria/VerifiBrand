'use client';

import React, { useState } from 'react';
import Link from 'next/link';
import { usePathname } from 'next/navigation';
import { useApp } from '../context/AppContext';
import {
  LayoutDashboard, FileText, Upload, ClipboardCheck, Shield,
  BarChart3, BookOpen, Menu, X, ChevronDown, LogOut, User
} from 'lucide-react';

const navItems = [
  { href: '/', label: 'Dashboard', icon: LayoutDashboard },
  { href: '/policy-cards', label: 'Policy Cards', icon: FileText },
  { href: '/scan', label: 'Upload & Scan', icon: Upload },
  { href: '/review', label: 'Review', icon: ClipboardCheck },
  { href: '/passports', label: 'Passports', icon: Shield },
  { href: '/insights', label: 'Insights', icon: BarChart3 },
  { href: '/audit', label: 'Audit Log', icon: BookOpen },
];

export default function Sidebar() {
  const pathname = usePathname();
  const { currentUser, setCurrentUser, allUsers, sidebarOpen, setSidebarOpen } = useApp();
  const [userMenuOpen, setUserMenuOpen] = useState(false);

  return (
    <>
      {/* Mobile toggle */}
      <button
        onClick={() => setSidebarOpen(!sidebarOpen)}
        className="fixed top-4 left-4 z-50 lg:hidden btn-ghost"
        style={{ background: 'white', border: '1px solid var(--color-warm-border)' }}
      >
        {sidebarOpen ? <X size={20} /> : <Menu size={20} />}
      </button>

      {/* Overlay for mobile */}
      {sidebarOpen && (
        <div
          className="fixed inset-0 bg-black/20 z-30 lg:hidden"
          onClick={() => setSidebarOpen(false)}
        />
      )}

      {/* Sidebar */}
      <aside
        className={`fixed top-0 left-0 h-full z-40 flex flex-col transition-transform duration-300 lg:translate-x-0 ${sidebarOpen ? 'translate-x-0' : '-translate-x-full'}`}
        style={{
          width: 260,
          background: 'white',
          borderRight: '1px solid var(--color-warm-border)',
        }}
      >
        {/* Logo */}
        <div style={{ padding: '24px 20px 16px' }}>
          <Link href="/" style={{ textDecoration: 'none' }}>
            <div style={{ display: 'flex', alignItems: 'center', gap: 10 }}>
              <div style={{
                width: 36, height: 36, borderRadius: 8,
                background: 'var(--color-forest-700)',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
              }}>
                <Shield size={20} color="white" />
              </div>
              <div>
                <div style={{
                  fontFamily: 'var(--font-heading)',
                  fontSize: 18,
                  color: 'var(--color-charcoal-800)',
                  lineHeight: 1.1,
                }}>
                  VerifiBrand
                </div>
                <div style={{ fontSize: 11, color: 'var(--color-charcoal-400)', letterSpacing: '0.05em' }}>
                  CONTENT GOVERNANCE
                </div>
              </div>
            </div>
          </Link>
        </div>

        {/* Divider */}
        <div style={{ height: 1, background: 'var(--color-warm-border)', margin: '0 16px' }} />

        {/* Navigation */}
        <nav style={{ padding: '16px 12px', flex: 1, overflowY: 'auto' }}>
          <div style={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            {navItems.map(item => {
              const isActive = pathname === item.href;
              return (
                <Link
                  key={item.href}
                  href={item.href}
                  className={`sidebar-link ${isActive ? 'active' : ''}`}
                  onClick={() => {
                    if (window.innerWidth < 1024) setSidebarOpen(false);
                  }}
                >
                  <item.icon size={18} />
                  {item.label}
                </Link>
              );
            })}
          </div>
        </nav>

        {/* Divider */}
        <div style={{ height: 1, background: 'var(--color-warm-border)', margin: '0 16px' }} />

        {/* User Switcher */}
        <div style={{ padding: '12px 12px 16px', position: 'relative' }}>
          <button
            onClick={() => setUserMenuOpen(!userMenuOpen)}
            style={{
              width: '100%',
              display: 'flex', alignItems: 'center', gap: 10,
              padding: '10px 12px',
              borderRadius: 8,
              border: '1px solid var(--color-warm-border)',
              background: 'var(--color-cream-50)',
              cursor: 'pointer',
              transition: 'background 0.15s',
              fontSize: 14,
            }}
          >
            <div style={{
              width: 32, height: 32, borderRadius: '50%',
              background: 'var(--color-forest-700)',
              color: 'white',
              display: 'flex', alignItems: 'center', justifyContent: 'center',
              fontSize: 12, fontWeight: 600,
              flexShrink: 0,
            }}>
              {currentUser.avatar}
            </div>
            <div style={{ flex: 1, textAlign: 'left' }}>
              <div style={{ fontWeight: 500, color: 'var(--color-charcoal-800)', lineHeight: 1.2 }}>
                {currentUser.name}
              </div>
              <div style={{ fontSize: 12, color: 'var(--color-charcoal-400)', textTransform: 'capitalize' }}>
                {currentUser.role}
              </div>
            </div>
            <ChevronDown size={16} style={{
              color: 'var(--color-charcoal-400)',
              transform: userMenuOpen ? 'rotate(180deg)' : 'rotate(0)',
              transition: 'transform 0.2s',
            }} />
          </button>

          {/* Dropdown */}
          {userMenuOpen && (
            <div
              className="animate-scale-in"
              style={{
                position: 'absolute',
                bottom: '100%',
                left: 12, right: 12,
                marginBottom: 4,
                background: 'white',
                border: '1px solid var(--color-warm-border)',
                borderRadius: 10,
                boxShadow: '0 8px 24px rgba(44,40,37,0.12)',
                overflow: 'hidden',
                zIndex: 100,
              }}
            >
              <div style={{ padding: '8px 6px' }}>
                <div style={{ padding: '4px 10px 8px', fontSize: 11, color: 'var(--color-charcoal-400)', fontWeight: 600, textTransform: 'uppercase', letterSpacing: '0.05em' }}>
                  Switch Role
                </div>
                {allUsers.map(u => (
                  <button
                    key={u.id}
                    onClick={() => { setCurrentUser(u); setUserMenuOpen(false); }}
                    style={{
                      width: '100%',
                      display: 'flex', alignItems: 'center', gap: 10,
                      padding: '8px 10px',
                      borderRadius: 6,
                      border: 'none',
                      background: currentUser.id === u.id ? 'var(--color-cream-200)' : 'transparent',
                      cursor: 'pointer',
                      fontSize: 13,
                      transition: 'background 0.1s',
                    }}
                    onMouseEnter={e => {
                      if (currentUser.id !== u.id) (e.target as HTMLButtonElement).style.background = 'var(--color-cream-100)';
                    }}
                    onMouseLeave={e => {
                      if (currentUser.id !== u.id) (e.target as HTMLButtonElement).style.background = 'transparent';
                    }}
                  >
                    <div style={{
                      width: 28, height: 28, borderRadius: '50%',
                      background: currentUser.id === u.id ? 'var(--color-forest-700)' : 'var(--color-cream-300)',
                      color: currentUser.id === u.id ? 'white' : 'var(--color-charcoal-600)',
                      display: 'flex', alignItems: 'center', justifyContent: 'center',
                      fontSize: 11, fontWeight: 600, flexShrink: 0,
                    }}>
                      {u.avatar}
                    </div>
                    <div style={{ textAlign: 'left' }}>
                      <div style={{ fontWeight: 500, color: 'var(--color-charcoal-700)' }}>{u.name}</div>
                      <div style={{ fontSize: 11, color: 'var(--color-charcoal-400)', textTransform: 'capitalize' }}>{u.role}</div>
                    </div>
                  </button>
                ))}
              </div>
            </div>
          )}
        </div>
      </aside>
    </>
  );
}
