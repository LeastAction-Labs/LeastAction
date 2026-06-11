/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// Physics Easter Eggs — hidden, never visible upfront. Registry in Claude memory (project_easter_eggs.md).
// 1. Console welcome + Lagrangian integral  →  src/main.tsx
// 2. HTML source comment                    →  index.html <head>
// 3. Idle screensaver (5 min inactivity)    →  ChatbotWidget.tsx — FAB icon animates per physics concept
// 4. Secret search terms (schrodinger etc)  →  QuickSearch.tsx — physics one-liner appears above results
// 5. Pi time pulse (3:14 AM/PM)             →  ChatbotWidget.tsx — FAB icon bounces for 10s
import React, { useEffect, useMemo, useState } from 'react';

interface PhysicsIcon {
  id: number;
  name: string;
  description: string;
  svg: React.ReactNode;
}

export const physicsIcons: PhysicsIcon[] = [
  {
    id: 1,
    name: 'Pendulum',
    description: 'The path of least resistance through oscillating time',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <line x1="25" y1="5" x2="25" y2="30" stroke="currentColor" strokeWidth="2" />
        <circle cx="25" cy="35" r="8" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 2,
    name: 'Orbit',
    description: 'Gravitational dance in the void of spacetime',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="25" cy="25" r="4" fill="currentColor" />
        <ellipse
          cx="25"
          cy="25"
          rx="18"
          ry="10"
          stroke="currentColor"
          strokeWidth="2"
          transform="rotate(30 25 25)"
        />
      </svg>
    ),
  },
  {
    id: 3,
    name: 'Momentum',
    description: 'Mass in motion refuses to yield without force',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M10 25 L35 25" stroke="currentColor" strokeWidth="3" />
        <path d="M30 18 L40 25 L30 32" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 4,
    name: 'Wave',
    description: 'Energy rippling through the fabric of space',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M5 25 Q15 10, 25 25 T45 25" stroke="currentColor" strokeWidth="2" fill="none" />
      </svg>
    ),
  },
  {
    id: 5,
    name: 'Spiral',
    description: 'Growth following the golden ratio of nature',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path
          d="M25 25 Q25 15, 35 15 Q45 15, 45 25 Q45 40, 30 40 Q10 40, 10 20 Q10 5, 25 5"
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
        />
      </svg>
    ),
  },
  {
    id: 6,
    name: 'Atom',
    description: 'Electrons bound by electromagnetic symphony',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="25" cy="25" r="3" fill="currentColor" />
        <ellipse cx="25" cy="25" rx="15" ry="8" stroke="currentColor" strokeWidth="1.5" />
        <ellipse cx="25" cy="25" rx="8" ry="15" stroke="currentColor" strokeWidth="1.5" />
        <circle cx="40" cy="25" r="2" fill="currentColor" />
        <circle cx="25" cy="40" r="2" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 7,
    name: 'Vector',
    description: 'Direction and magnitude as one entity',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <line x1="10" y1="40" x2="35" y2="15" stroke="currentColor" strokeWidth="2.5" />
        <path d="M28 12 L38 15 L32 22" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 8,
    name: 'Trajectory',
    description: 'The arc of a projectile against gravity',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M5 40 Q25 5, 45 40" stroke="currentColor" strokeWidth="2" fill="none" />
        <circle cx="5" cy="40" r="2" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 9,
    name: 'Magnetism',
    description: 'Invisible fields that shape reality',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path
          d="M25 5 Q35 10, 35 20 L35 30 Q35 40, 25 45"
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
        />
        <path
          d="M25 5 Q15 10, 15 20 L15 30 Q15 40, 25 45"
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
        />
      </svg>
    ),
  },
  {
    id: 10,
    name: 'Photon',
    description: 'Light traversing the cosmos at constant speed',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="25" cy="25" r="6" fill="currentColor" />
        <line x1="25" y1="10" x2="25" y2="18" stroke="currentColor" strokeWidth="2" />
        <line x1="25" y1="32" x2="25" y2="40" stroke="currentColor" strokeWidth="2" />
        <line x1="10" y1="25" x2="18" y2="25" stroke="currentColor" strokeWidth="2" />
        <line x1="32" y1="25" x2="40" y2="25" stroke="currentColor" strokeWidth="2" />
      </svg>
    ),
  },
  {
    id: 11,
    name: 'Acceleration',
    description: 'Change in velocity over the arrow of time',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M8 30 L25 30" stroke="currentColor" strokeWidth="2" />
        <path d="M8 20 L35 20" stroke="currentColor" strokeWidth="2" />
        <path d="M8 10 L45 10" stroke="currentColor" strokeWidth="2" />
        <path d="M40 5 L45 10 L40 15" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 12,
    name: 'Centripetal',
    description: 'Force that curves straight motion into circles',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle
          cx="25"
          cy="25"
          r="15"
          stroke="currentColor"
          strokeWidth="2"
          strokeDasharray="3 3"
        />
        <circle cx="40" cy="25" r="3" fill="currentColor" />
        <line x1="40" y1="25" x2="32" y2="25" stroke="currentColor" strokeWidth="2" />
        <path d="M34 22 L32 25 L34 28" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 13,
    name: 'Resonance',
    description: 'Amplification through harmonic alignment',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path
          d="M10 25 L15 15 L20 25 L25 15 L30 25 L35 15 L40 25"
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
        />
        <circle cx="25" cy="15" r="4" stroke="currentColor" strokeWidth="2" fill="none" />
      </svg>
    ),
  },
  {
    id: 14,
    name: 'Torque',
    description: 'Rotational force around an axis of change',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle
          cx="25"
          cy="25"
          r="12"
          stroke="currentColor"
          strokeWidth="2"
          strokeDasharray="4 4"
        />
        <path d="M37 25 L42 25 L40 20" stroke="currentColor" strokeWidth="2" />
        <circle cx="25" cy="25" r="3" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 15,
    name: 'Diffraction',
    description: 'Waves bending around obstacles in space',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <line x1="5" y1="10" x2="20" y2="10" stroke="currentColor" strokeWidth="2" />
        <line x1="5" y1="25" x2="20" y2="25" stroke="currentColor" strokeWidth="2" />
        <line x1="5" y1="40" x2="20" y2="40" stroke="currentColor" strokeWidth="2" />
        <rect x="22" y="5" width="6" height="40" fill="currentColor" />
        <path d="M30 10 Q35 15, 40 10" stroke="currentColor" strokeWidth="1.5" fill="none" />
        <path d="M30 25 Q35 30, 40 25" stroke="currentColor" strokeWidth="1.5" fill="none" />
        <path d="M30 40 Q35 45, 40 40" stroke="currentColor" strokeWidth="1.5" fill="none" />
      </svg>
    ),
  },
  {
    id: 16,
    name: 'Equilibrium',
    description: 'Perfect balance where all forces cancel',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <line x1="10" y1="25" x2="40" y2="25" stroke="currentColor" strokeWidth="3" />
        <circle cx="25" cy="25" r="5" fill="currentColor" />
        <line x1="25" y1="10" x2="25" y2="20" stroke="currentColor" strokeWidth="2" />
        <line x1="25" y1="30" x2="25" y2="40" stroke="currentColor" strokeWidth="2" />
      </svg>
    ),
  },
  {
    id: 17,
    name: 'Inertia',
    description: 'The stubborn persistence of motion',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="10" y="18" width="14" height="14" fill="currentColor" />
        <line x1="24" y1="25" x2="40" y2="25" stroke="currentColor" strokeWidth="2.5" />
        <path d="M36 20 L40 25 L36 30" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 18,
    name: 'Relativity',
    description: 'Spacetime curved by mass and energy',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M5 15 Q25 10, 45 15" stroke="currentColor" strokeWidth="1.5" fill="none" />
        <path d="M5 25 Q25 35, 45 25" stroke="currentColor" strokeWidth="1.5" fill="none" />
        <path d="M5 35 Q25 30, 45 35" stroke="currentColor" strokeWidth="1.5" fill="none" />
        <circle cx="25" cy="25" r="6" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 19,
    name: 'Entropy',
    description: 'Order dissolving into chaos over time',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="10" y="10" width="8" height="8" fill="currentColor" />
        <rect x="10" y="21" width="8" height="8" fill="currentColor" />
        <circle cx="32" cy="14" r="2" fill="currentColor" />
        <circle cx="38" cy="18" r="2" fill="currentColor" />
        <circle cx="28" cy="25" r="1.5" fill="currentColor" />
        <circle cx="35" cy="28" r="1.5" fill="currentColor" />
        <circle cx="32" cy="35" r="1.5" fill="currentColor" />
        <circle cx="38" cy="38" r="1.5" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 20,
    name: 'Quantum',
    description: 'Discrete packets of energy in the void',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="15" cy="15" r="3" fill="currentColor" opacity="0.3" />
        <circle cx="35" cy="15" r="3" fill="currentColor" opacity="0.6" />
        <circle cx="25" cy="25" r="4" fill="currentColor" />
        <circle cx="15" cy="35" r="3" fill="currentColor" opacity="0.6" />
        <circle cx="35" cy="35" r="3" fill="currentColor" opacity="0.3" />
      </svg>
    ),
  },
  {
    id: 21,
    name: 'Refraction',
    description: 'Light bending as it crosses boundaries',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <line x1="15" y1="5" x2="25" y2="25" stroke="currentColor" strokeWidth="2" />
        <line x1="25" y1="25" x2="30" y2="45" stroke="currentColor" strokeWidth="2" />
        <line
          x1="5"
          y1="25"
          x2="45"
          y2="25"
          stroke="currentColor"
          strokeWidth="1"
          strokeDasharray="2 2"
        />
      </svg>
    ),
  },
  {
    id: 22,
    name: 'Friction',
    description: 'Resistance that steals kinetic energy',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="10" y="18" width="12" height="12" fill="currentColor" />
        <line x1="5" y1="35" x2="45" y2="35" stroke="currentColor" strokeWidth="3" />
        <path
          d="M8 35 L10 38 L12 35 L14 38 L16 35 L18 38 L20 35 L22 38 L24 35 L26 38 L28 35 L30 38 L32 35 L34 38 L36 35 L38 38 L40 35 L42 38"
          stroke="currentColor"
          strokeWidth="1"
          fill="none"
        />
      </svg>
    ),
  },
  {
    id: 23,
    name: 'Superposition',
    description: 'Existing in multiple states simultaneously',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle
          cx="22"
          cy="25"
          r="10"
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
          opacity="0.5"
        />
        <circle
          cx="28"
          cy="25"
          r="10"
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
          opacity="0.5"
        />
        <circle cx="25" cy="25" r="5" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 24,
    name: 'Doppler',
    description: 'Frequency shifted by relative motion',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="30" cy="25" r="3" fill="currentColor" />
        <circle cx="30" cy="25" r="8" stroke="currentColor" strokeWidth="1.5" fill="none" />
        <circle
          cx="30"
          cy="25"
          r="13"
          stroke="currentColor"
          strokeWidth="1.5"
          fill="none"
          opacity="0.6"
        />
        <circle
          cx="30"
          cy="25"
          r="18"
          stroke="currentColor"
          strokeWidth="1.5"
          fill="none"
          opacity="0.3"
        />
        <path d="M20 25 L10 25" stroke="currentColor" strokeWidth="2.5" />
        <path d="M14 20 L10 25 L14 30" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 25,
    name: 'Gravity',
    description: 'Mass warping the geometry of spacetime',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="25" cy="25" r="8" fill="currentColor" />
        <path d="M25 5 L25 13" stroke="currentColor" strokeWidth="2" />
        <path d="M25 37 L25 45" stroke="currentColor" strokeWidth="2" />
        <path d="M5 25 L13 25" stroke="currentColor" strokeWidth="2" />
        <path d="M37 25 L45 25" stroke="currentColor" strokeWidth="2" />
        <path d="M12 12 L17 17" stroke="currentColor" strokeWidth="2" />
        <path d="M33 33 L38 38" stroke="currentColor" strokeWidth="2" />
        <path d="M38 12 L33 17" stroke="currentColor" strokeWidth="2" />
        <path d="M17 33 L12 38" stroke="currentColor" strokeWidth="2" />
      </svg>
    ),
  },
  {
    id: 26,
    name: 'Interference',
    description: 'Waves colliding to amplify or cancel',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path
          d="M5 20 Q12.5 10, 20 20 T35 20"
          stroke="currentColor"
          strokeWidth="1.5"
          fill="none"
        />
        <path
          d="M15 30 Q22.5 20, 30 30 T45 30"
          stroke="currentColor"
          strokeWidth="1.5"
          fill="none"
        />
        <circle cx="22.5" cy="25" r="3" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 27,
    name: 'Conservation',
    description: 'Energy transformed but never destroyed',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="25" cy="25" r="15" stroke="currentColor" strokeWidth="2.5" fill="none" />
        <path d="M25 10 L25 25 L35 20" stroke="currentColor" strokeWidth="2" />
      </svg>
    ),
  },
  {
    id: 28,
    name: 'Oscillation',
    description: 'Periodic return to equilibrium',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path
          d="M5 25 L10 10 L15 40 L20 10 L25 40 L30 10 L35 40 L40 10 L45 25"
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
        />
      </svg>
    ),
  },
  {
    id: 29,
    name: 'Polarization',
    description: 'Light waves aligned in formation',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <line x1="25" y1="10" x2="25" y2="40" stroke="currentColor" strokeWidth="2" />
        <line
          x1="18"
          y1="15"
          x2="18"
          y2="35"
          stroke="currentColor"
          strokeWidth="1.5"
          opacity="0.6"
        />
        <line
          x1="32"
          y1="15"
          x2="32"
          y2="35"
          stroke="currentColor"
          strokeWidth="1.5"
          opacity="0.6"
        />
        <line x1="12" y1="20" x2="12" y2="30" stroke="currentColor" strokeWidth="1" opacity="0.3" />
        <line x1="38" y1="20" x2="38" y2="30" stroke="currentColor" strokeWidth="1" opacity="0.3" />
      </svg>
    ),
  },
  {
    id: 30,
    name: 'Kinetic',
    description: 'Energy of objects in motion',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="30" cy="25" r="8" fill="currentColor" />
        <path d="M5 25 L20 25" stroke="currentColor" strokeWidth="2.5" />
        <path d="M10 20 L5 25 L10 30" fill="currentColor" />
        <line x1="35" y1="20" x2="42" y2="15" stroke="currentColor" strokeWidth="1.5" />
        <line x1="35" y1="30" x2="42" y2="35" stroke="currentColor" strokeWidth="1.5" />
        <line x1="38" y1="25" x2="45" y2="25" stroke="currentColor" strokeWidth="1.5" />
      </svg>
    ),
  },
  {
    id: 31,
    name: 'Decay',
    description: 'Unstable matter seeking stability',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="25" cy="15" r="6" fill="currentColor" />
        <circle cx="18" cy="28" r="3" fill="currentColor" opacity="0.7" />
        <circle cx="32" cy="28" r="3" fill="currentColor" opacity="0.7" />
        <circle cx="15" cy="38" r="2" fill="currentColor" opacity="0.4" />
        <circle cx="25" cy="40" r="2" fill="currentColor" opacity="0.4" />
        <circle cx="35" cy="38" r="2" fill="currentColor" opacity="0.4" />
      </svg>
    ),
  },
  {
    id: 32,
    name: 'Vortex',
    description: 'Fluid spiraling into the center',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path
          d="M25 5 Q40 10, 40 25 Q40 40, 25 40 Q10 40, 10 25 Q10 15, 20 12"
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
        />
        <circle cx="25" cy="25" r="3" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 33,
    name: 'Fusion',
    description: 'Nuclei merging to release stellar fire',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="18" cy="25" r="6" stroke="currentColor" strokeWidth="2" fill="none" />
        <circle cx="32" cy="25" r="6" stroke="currentColor" strokeWidth="2" fill="none" />
        <circle cx="25" cy="25" r="4" fill="currentColor" />
        <line x1="22" y1="18" x2="18" y2="12" stroke="currentColor" strokeWidth="1.5" />
        <line x1="28" y1="18" x2="32" y2="12" stroke="currentColor" strokeWidth="1.5" />
        <line x1="28" y1="32" x2="32" y2="38" stroke="currentColor" strokeWidth="1.5" />
        <line x1="22" y1="32" x2="18" y2="38" stroke="currentColor" strokeWidth="1.5" />
      </svg>
    ),
  },
  {
    id: 34,
    name: 'Plasma',
    description: 'The fourth state dancing with ions',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path
          d="M15 10 Q20 20, 15 30 Q10 40, 15 45"
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
        />
        <path
          d="M25 5 Q30 15, 25 25 Q20 35, 25 45"
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
        />
        <path
          d="M35 10 Q30 20, 35 30 Q40 40, 35 45"
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
        />
        <circle cx="20" cy="15" r="2" fill="currentColor" />
        <circle cx="30" cy="35" r="2" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 35,
    name: 'Pressure',
    description: 'Force distributed across surface area',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="12" y="28" width="26" height="8" fill="currentColor" />
        <line x1="18" y1="25" x2="18" y2="15" stroke="currentColor" strokeWidth="2" />
        <line x1="25" y1="25" x2="25" y2="10" stroke="currentColor" strokeWidth="2" />
        <line x1="32" y1="25" x2="32" y2="15" stroke="currentColor" strokeWidth="2" />
        <path d="M15 18 L18 15 L21 18" fill="currentColor" />
        <path d="M22 13 L25 10 L28 13" fill="currentColor" />
        <path d="M29 18 L32 15 L35 18" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 36,
    name: 'Reflection',
    description: 'Incident angle equals angle of return',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <line x1="15" y1="5" x2="25" y2="25" stroke="currentColor" strokeWidth="2" />
        <line x1="25" y1="25" x2="35" y2="5" stroke="currentColor" strokeWidth="2" />
        <line x1="5" y1="25" x2="45" y2="25" stroke="currentColor" strokeWidth="3" />
        <circle cx="25" cy="25" r="2" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 37,
    name: 'Symmetry',
    description: 'Invariance under transformation',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <line
          x1="25"
          y1="5"
          x2="25"
          y2="45"
          stroke="currentColor"
          strokeWidth="1"
          strokeDasharray="2 2"
        />
        <polygon points="15,15 12,25 15,35 22,32 22,18" fill="currentColor" />
        <polygon points="35,15 38,25 35,35 28,32 28,18" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 38,
    name: 'Tension',
    description: 'Elastic force resisting deformation',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <line x1="10" y1="25" x2="18" y2="25" stroke="currentColor" strokeWidth="2" />
        <line x1="32" y1="25" x2="40" y2="25" stroke="currentColor" strokeWidth="2" />
        <path d="M18 25 Q25 20, 32 25" stroke="currentColor" strokeWidth="2" fill="none" />
        <circle cx="10" cy="25" r="3" fill="currentColor" />
        <circle cx="40" cy="25" r="3" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 39,
    name: 'Uncertainty',
    description: 'Position and momentum cannot both be known',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle
          cx="25"
          cy="25"
          r="10"
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
          strokeDasharray="3 3"
        />
        <circle cx="20" cy="20" r="2" fill="currentColor" opacity="0.3" />
        <circle cx="30" cy="25" r="2" fill="currentColor" opacity="0.5" />
        <circle cx="25" cy="30" r="2" fill="currentColor" opacity="0.7" />
      </svg>
    ),
  },
  {
    id: 40,
    name: 'Velocity',
    description: 'Displacement divided by time elapsed',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <line x1="5" y1="25" x2="40" y2="25" stroke="currentColor" strokeWidth="3" />
        <path d="M33 18 L42 25 L33 32" fill="currentColor" />
        <circle cx="5" cy="25" r="3" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 41,
    name: 'Elasticity',
    description: 'Matter returning to original form',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <rect x="8" y="20" width="6" height="10" fill="currentColor" />
        <path
          d="M14 25 Q20 15, 26 25 Q32 35, 38 25"
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
        />
        <rect x="38" y="20" width="6" height="10" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 42,
    name: 'Spectrum',
    description: 'White light dispersed into rainbow',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <line x1="5" y1="25" x2="20" y2="25" stroke="currentColor" strokeWidth="2" />
        <line
          x1="25"
          y1="15"
          x2="40"
          y2="10"
          stroke="currentColor"
          strokeWidth="1.5"
          opacity="0.3"
        />
        <line
          x1="25"
          y1="20"
          x2="42"
          y2="17"
          stroke="currentColor"
          strokeWidth="1.5"
          opacity="0.5"
        />
        <line x1="25" y1="25" x2="45" y2="25" stroke="currentColor" strokeWidth="1.5" />
        <line
          x1="25"
          y1="30"
          x2="42"
          y2="33"
          stroke="currentColor"
          strokeWidth="1.5"
          opacity="0.5"
        />
        <line
          x1="25"
          y1="35"
          x2="40"
          y2="40"
          stroke="currentColor"
          strokeWidth="1.5"
          opacity="0.3"
        />
        <path d="M20 15 L20 35 L25 25 Z" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 43,
    name: 'Turbulence',
    description: 'Chaotic flow in fluid dynamics',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path
          d="M5 25 Q10 15, 15 25 Q18 35, 20 25 Q23 15, 28 25 Q32 35, 35 25 Q38 15, 45 25"
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
        />
        <path
          d="M8 18 Q12 12, 16 18"
          stroke="currentColor"
          strokeWidth="1.5"
          fill="none"
          opacity="0.6"
        />
        <path
          d="M28 32 Q32 38, 36 32"
          stroke="currentColor"
          strokeWidth="1.5"
          fill="none"
          opacity="0.6"
        />
      </svg>
    ),
  },
  {
    id: 44,
    name: 'Frequency',
    description: 'Oscillations per unit of time',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path
          d="M5 25 Q10 15, 15 25 Q20 35, 25 25 Q30 15, 35 25 Q40 35, 45 25"
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
        />
        <line
          x1="15"
          y1="10"
          x2="15"
          y2="40"
          stroke="currentColor"
          strokeWidth="1"
          strokeDasharray="2 2"
        />
        <line
          x1="25"
          y1="10"
          x2="25"
          y2="40"
          stroke="currentColor"
          strokeWidth="1"
          strokeDasharray="2 2"
        />
      </svg>
    ),
  },
  {
    id: 45,
    name: 'Impulse',
    description: 'Force integrated over contact time',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="15" cy="25" r="6" fill="currentColor" />
        <circle cx="35" cy="25" r="6" stroke="currentColor" strokeWidth="2" fill="none" />
        <line x1="21" y1="25" x2="29" y2="25" stroke="currentColor" strokeWidth="3" />
        <path d="M27 20 L32 25 L27 30" stroke="currentColor" strokeWidth="2" />
      </svg>
    ),
  },
  {
    id: 46,
    name: 'Harmonic',
    description: 'Simple periodic motion about equilibrium',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path
          d="M5 25 Q15 5, 25 25 Q35 45, 45 25"
          stroke="currentColor"
          strokeWidth="2"
          fill="none"
        />
        <circle cx="25" cy="25" r="3" fill="currentColor" />
        <line
          x1="5"
          y1="25"
          x2="45"
          y2="25"
          stroke="currentColor"
          strokeWidth="0.5"
          strokeDasharray="2 2"
          opacity="0.5"
        />
      </svg>
    ),
  },
  {
    id: 47,
    name: 'Prism',
    description: 'Geometry refracting light into colors',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M15 35 L25 10 L35 35 Z" stroke="currentColor" strokeWidth="2" fill="none" />
        <line x1="5" y1="22" x2="15" y2="22" stroke="currentColor" strokeWidth="2" />
        <line
          x1="35"
          y1="18"
          x2="45"
          y2="15"
          stroke="currentColor"
          strokeWidth="1.5"
          opacity="0.5"
        />
        <line x1="35" y1="22" x2="45" y2="22" stroke="currentColor" strokeWidth="1.5" />
        <line
          x1="35"
          y1="26"
          x2="45"
          y2="29"
          stroke="currentColor"
          strokeWidth="1.5"
          opacity="0.5"
        />
      </svg>
    ),
  },
  {
    id: 48,
    name: 'Spin',
    description: 'Intrinsic angular momentum of particles',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="25" cy="25" r="12" stroke="currentColor" strokeWidth="2" fill="none" />
        <path d="M25 13 L25 25 L37 25" stroke="currentColor" strokeWidth="2" />
        <path d="M30 20 L37 25 L32 28" fill="currentColor" />
        <circle cx="25" cy="25" r="3" fill="currentColor" />
      </svg>
    ),
  },
  {
    id: 49,
    name: 'Entanglement',
    description: 'Quantum correlation across space',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <circle cx="15" cy="25" r="6" stroke="currentColor" strokeWidth="2" fill="none" />
        <circle cx="35" cy="25" r="6" stroke="currentColor" strokeWidth="2" fill="none" />
        <path d="M21 25 Q25 15, 29 25" stroke="currentColor" strokeWidth="1.5" fill="none" />
        <path d="M21 25 Q25 35, 29 25" stroke="currentColor" strokeWidth="1.5" fill="none" />
      </svg>
    ),
  },
  {
    id: 50,
    name: 'Geodesic',
    description: 'Shortest path through curved spacetime',
    svg: (
      <svg viewBox="0 0 50 50" fill="none" xmlns="http://www.w3.org/2000/svg">
        <path d="M5 40 Q25 10, 45 40" stroke="currentColor" strokeWidth="2" fill="none" />
        <circle cx="5" cy="40" r="3" fill="currentColor" />
        <circle cx="45" cy="40" r="3" fill="currentColor" />
        <line
          x1="5"
          y1="45"
          x2="45"
          y2="45"
          stroke="currentColor"
          strokeWidth="1"
          strokeDasharray="3 3"
          opacity="0.4"
        />
      </svg>
    ),
  },
];

interface PhysicsAvatarIconProps {
  size?: number;
  className?: string;
}

const STORAGE_KEY = 'selected-physics-icon';

const PhysicsAvatarIcon: React.FC<PhysicsAvatarIconProps> = ({ size = 50, className = '' }) => {
  const [isHovered, setIsHovered] = useState(false);
  const [showPicker, setShowPicker] = useState(false);
  const [selectedIconName, setSelectedIconName] = useState<string>('');

  // Initialize icon from localStorage or random
  useEffect(() => {
    const savedIconName = localStorage.getItem(STORAGE_KEY);
    if (savedIconName) {
      setSelectedIconName(savedIconName);
    } else {
      const randomIcon = physicsIcons[Math.floor(Math.random() * physicsIcons.length)];
      setSelectedIconName(randomIcon.name);
    }
  }, []);

  // Get the selected icon based on name
  const selectedIcon = useMemo(() => {
    const icon = physicsIcons.find((icon) => icon.name === selectedIconName);
    return icon || physicsIcons[0]; // Fallback to first icon if not found
  }, [selectedIconName]);

  const handleIconClick = (e: React.MouseEvent) => {
    e.stopPropagation();
    setShowPicker(true);
  };

  const handleIconSelect = (iconName: string) => {
    setSelectedIconName(iconName);
    localStorage.setItem(STORAGE_KEY, iconName);
    setShowPicker(false);
  };

  const handleClosePicker = () => {
    setShowPicker(false);
  };

  return (
    <>
      <div
        className={`inline-block cursor-pointer transition-transform hover:scale-110 ${className}`}
        style={{ width: size, height: size, position: 'relative' }}
        onMouseEnter={() => setIsHovered(true)}
        onMouseLeave={() => setIsHovered(false)}
        onClick={handleIconClick}
        role="button"
        aria-label={`${selectedIcon.name}: ${selectedIcon.description}. Click to change icon.`}
      >
        <div style={{ width: '100%', height: '100%' }}>{selectedIcon.svg}</div>
        {isHovered && (
          <>
            <div
              style={{
                position: 'absolute',
                top: '100%',
                right: '0',
                marginTop: '8px',
                padding: '8px 12px',
                backgroundColor: 'var(--bg-tertiary)',
                color: 'var(--text-primary)',
                borderRadius: '6px',
                fontSize: '14px',
                whiteSpace: 'nowrap',
                zIndex: 1000,
                pointerEvents: 'none',
                boxShadow: '0 2px 8px rgba(0, 0, 0, 0.3)',
              }}
            >
              <div
                style={{
                  position: 'absolute',
                  bottom: '100%',
                  right: '12px',
                  width: 0,
                  height: 0,
                  borderLeft: '6px solid transparent',
                  borderRight: '6px solid transparent',
                  borderBottom: '6px solid var(--bg-tertiary)',
                }}
              />
              <div style={{ fontWeight: 'bold', marginBottom: '4px' }}>{selectedIcon.name}</div>
              <div style={{ fontSize: '12px', opacity: 0.9 }}>{selectedIcon.description}</div>
              <div
                style={{ fontSize: '11px', opacity: 0.7, marginTop: '4px', fontStyle: 'italic' }}
              >
                Click to change icon
              </div>
            </div>
            <style>
              {`
                @keyframes pulse {
                  0%, 100% { opacity: 1; }
                  50% { opacity: 0.7; }
                }
              `}
            </style>
          </>
        )}
      </div>

      {/* Icon Picker Modal */}
      {showPicker && (
        <div
          style={{
            position: 'fixed',
            top: 0,
            left: 0,
            right: 0,
            bottom: 0,
            backgroundColor: 'rgba(0, 0, 0, 0.7)',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            zIndex: 10000,
            padding: '20px',
          }}
          onClick={handleClosePicker}
        >
          <div
            style={{
              backgroundColor: 'var(--bg-primary)',
              borderRadius: '12px',
              padding: '24px',
              maxWidth: '800px',
              maxHeight: '80vh',
              overflow: 'auto',
              boxShadow: '0 8px 32px rgba(0, 0, 0, 0.3)',
            }}
            onClick={(e) => e.stopPropagation()}
          >
            <div
              style={{
                display: 'flex',
                justifyContent: 'space-between',
                alignItems: 'center',
                marginBottom: '20px',
                borderBottom: '2px solid var(--border)',
                paddingBottom: '12px',
              }}
            >
              <h2 style={{ margin: 0, fontSize: '24px', fontWeight: 'bold' }}>
                Choose Your Physics Icon
              </h2>
              <button
                onClick={handleClosePicker}
                style={{
                  background: 'none',
                  border: 'none',
                  fontSize: '28px',
                  cursor: 'pointer',
                  color: 'var(--text-secondary)',
                  lineHeight: '1',
                  padding: '0 8px',
                }}
                aria-label="Close"
              >
                ×
              </button>
            </div>
            <div
              style={{
                display: 'grid',
                gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))',
                gap: '16px',
                marginTop: '16px',
              }}
            >
              {physicsIcons.map((icon) => (
                <div
                  key={icon.id}
                  onClick={() => handleIconSelect(icon.name)}
                  style={{
                    padding: '16px',
                    border:
                      selectedIconName === icon.name
                        ? '3px solid var(--accent)'
                        : '2px solid var(--border)',
                    borderRadius: '8px',
                    cursor: 'pointer',
                    transition: 'all 0.2s',
                    backgroundColor:
                      selectedIconName === icon.name ? 'var(--bg-selected)' : 'transparent',
                    display: 'flex',
                    flexDirection: 'column',
                    alignItems: 'center',
                    gap: '8px',
                  }}
                  onMouseEnter={(e) => {
                    if (selectedIconName !== icon.name) {
                      e.currentTarget.style.borderColor = 'var(--accent)';
                      e.currentTarget.style.backgroundColor = 'var(--bg-secondary)';
                    }
                  }}
                  onMouseLeave={(e) => {
                    if (selectedIconName !== icon.name) {
                      e.currentTarget.style.borderColor = 'var(--border)';
                      e.currentTarget.style.backgroundColor = 'transparent';
                    }
                  }}
                >
                  <div style={{ width: '50px', height: '50px' }}>{icon.svg}</div>
                  <div
                    style={{
                      fontSize: '12px',
                      fontWeight: selectedIconName === icon.name ? 'bold' : 'normal',
                      textAlign: 'center',
                      color: 'var(--text-primary)',
                    }}
                  >
                    {icon.name}
                  </div>
                  <div
                    style={{
                      fontSize: '10px',
                      color: 'var(--text-secondary)',
                      textAlign: 'center',
                      lineHeight: '1.3',
                    }}
                  >
                    {icon.description}
                  </div>
                </div>
              ))}
            </div>
          </div>
        </div>
      )}
    </>
  );
};

export default PhysicsAvatarIcon;
