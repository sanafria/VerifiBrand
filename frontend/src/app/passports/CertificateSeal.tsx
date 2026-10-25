'use client';

import React from 'react';

interface CertificateSealProps {
  verified: boolean;
  size?: number;
}

export const CertificateSeal: React.FC<CertificateSealProps> = ({ verified, size = 110 }) => {
  const goldColor = verified ? '#B58A1F' : '#991B1B';
  const glowColor = verified ? 'rgba(181, 138, 31, 0.18)' : 'rgba(153, 27, 27, 0.18)';
  const navyColor = verified ? '#1E293B' : '#7F1D1D';
  const forestColor = verified ? '#1B4D3E' : '#991B1B';

  return (
    <div style={{
      width: size,
      height: size,
      position: 'relative',
      display: 'inline-flex',
      alignItems: 'center',
      justifyContent: 'center',
      filter: `drop-shadow(0 2px 10px ${glowColor})`,
      transition: 'all 0.4s ease',
    }}>
      <svg
        width={size}
        height={size}
        viewBox="0 0 200 200"
        fill="none"
        xmlns="http://www.w3.org/2000/svg"
        style={{ overflow: 'visible' }}
      >
        <defs>
          {/* Subtle Warm Gradient */}
          <radialGradient id={`sealGlow-${verified ? 'v' : 't'}`} cx="50%" cy="50%" r="50%">
            <stop offset="0%" stopColor={goldColor} stopOpacity="0.16" />
            <stop offset="70%" stopColor={forestColor} stopOpacity="0.06" />
            <stop offset="100%" stopColor="transparent" />
          </radialGradient>

          <linearGradient id={`goldBorder-${verified ? 'v' : 't'}`} x1="0" y1="0" x2="200" y2="200">
            <stop offset="0%" stopColor={goldColor} />
            <stop offset="50%" stopColor="#D4A373" />
            <stop offset="100%" stopColor={forestColor} />
          </linearGradient>

          {/* Text Path Circle */}
          <path
            id={`textPathCircle-${verified ? 'v' : 't'}`}
            d="M 100, 100 m -72, 0 a 72,72 0 1,1 144,0 a 72,72 0 1,1 -144,0"
          />
        </defs>

        {/* Outer Radiant Glow */}
        <circle cx="100" cy="100" r="92" fill={`url(#sealGlow-${verified ? 'v' : 't'})`} />

        {/* Outer Scalloped Gear / Sunburst */}
        <circle
          cx="100"
          cy="100"
          r="86"
          stroke={`url(#goldBorder-${verified ? 'v' : 't'})`}
          strokeWidth="2.5"
          strokeDasharray="6 4"
        />

        {/* Circular Ribbons / Rings */}
        <circle
          cx="100"
          cy="100"
          r="76"
          stroke={goldColor}
          strokeWidth="1.5"
          opacity="0.85"
        />
        <circle
          cx="100"
          cy="100"
          r="66"
          stroke={navyColor}
          strokeWidth="1.2"
          opacity="0.6"
        />

        {/* Circular Text */}
        <text
          fill={verified ? '#1B4D3E' : '#991B1B'}
          fontSize="9.5"
          fontWeight="800"
          letterSpacing="2.8"
          style={{ textTransform: 'uppercase' }}
        >
          <textPath
            href={`#textPathCircle-${verified ? 'v' : 't'}`}
            startOffset="50%"
            textAnchor="middle"
          >
            {verified
              ? '• VERIFIBRAND • APPROVAL VERIFIED •'
              : '• INTEGRITY BREACH • TAMPER DETECTED •'}
          </textPath>
        </text>

        {/* Inner Solid Badge - Warm Ivory & Paper texture feel */}
        <circle
          cx="100"
          cy="100"
          r="54"
          fill="#FAF8F3"
          stroke={`url(#goldBorder-${verified ? 'v' : 't'})`}
          strokeWidth="2"
        />

        {/* Shield Icon and Verification Mark */}
        {verified ? (
          <g transform="translate(76, 74)">
            {/* Shield Outline */}
            <path
              d="M24 4 L42 10 V24 C42 35 24 44 24 44 C24 44 6 35 6 24 V10 Z"
              fill="rgba(27, 77, 62, 0.12)"
              stroke="#1B4D3E"
              strokeWidth="2.5"
              strokeLinejoin="round"
            />
            {/* Checkmark */}
            <path
              d="M16 23 L22 29 L32 17"
              stroke="#B58A1F"
              strokeWidth="3.2"
              strokeLinecap="round"
              strokeLinejoin="round"
            />
          </g>
        ) : (
          <g transform="translate(76, 74)">
            {/* Warning Shield */}
            <path
              d="M24 4 L42 10 V24 C42 35 24 44 24 44 C24 44 6 35 6 24 V10 Z"
              fill="rgba(153, 27, 27, 0.12)"
              stroke="#991B1B"
              strokeWidth="2.5"
              strokeLinejoin="round"
            />
            {/* Exclamation */}
            <path
              d="M24 16 V27 M24 33 H24.02"
              stroke="#991B1B"
              strokeWidth="3.5"
              strokeLinecap="round"
            />
          </g>
        )}

        {/* Security Stamp Subtext */}
        <text
          x="100"
          y="142"
          textAnchor="middle"
          fill={verified ? '#1B4D3E' : '#991B1B'}
          fontSize="7"
          fontWeight="800"
          letterSpacing="1"
        >
          {verified ? 'RECORD VERIFIED' : 'MISMATCH'}
        </text>
      </svg>
    </div>
  );
};
