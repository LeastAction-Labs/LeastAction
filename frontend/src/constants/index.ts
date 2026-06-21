/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// ============================================================================
// FONT FAMILIES
// ============================================================================
export const FONT_FAMILIES = {
  PRIMARY:
    "'Inter', ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, Helvetica, Arial, 'Apple Color Emoji', 'Segoe UI Emoji'",
  MONOSPACE: "Consolas, Monaco, 'Courier New', monospace",
  INHERIT: 'inherit',
} as const;

// ============================================================================
// FONT SIZES
// ============================================================================
export const FONT_SIZES = {
  // Extra extra small
  XXS: '0.6875rem', // 11px
  XXS_NUMERIC: 0.6875,

  // Extra small
  XS: '0.75rem', // 12px
  XS_NUMERIC: 0.75,

  // Small
  SM: '0.8125rem', // 13px
  SM_NUMERIC: 0.8125,

  // Base
  BASE: '0.875rem', // 14px
  BASE_NUMERIC: 0.875,

  // Medium
  MD: '1rem', // 16px
  MD_NUMERIC: 1,

  // Large
  LG: '1.125rem', // 18px
  LG_NUMERIC: 1.125,

  // Extra large
  XL: '1.25rem', // 20px
  XL_NUMERIC: 1.25,

  // Monaco editor font size (pixel values)
  MONACO: 15,

  // Icon sizes (numeric for Material-UI sx prop)
  ICON_XS: 10,
  ICON_SM: 14,
  ICON_MD: 16,
  ICON_LG: 18,
  ICON_XL: 20,
} as const;

// ============================================================================
// FONT WEIGHTS
// ============================================================================
export const FONT_WEIGHTS = {
  NORMAL: 'normal',
  MEDIUM: 'medium',
  SEMIBOLD: 'semibold',
  BOLD: 'bold',
  // Numeric weights
  WEIGHT_400: '400',
  WEIGHT_500: '500',
  WEIGHT_600: '600',
  WEIGHT_700: '700',
} as const;

// ============================================================================
// COLORS
// ============================================================================
export const COLORS = {
  // Green — success, INFO, active/selected indicators
  GREEN: '#11d452',
  GREEN_HOVER: '#0ab840',
  GREEN_BG: 'rgba(17,212,82,0.15)',

  // Red — error, failed, CRITICAL
  RED: '#ef4444',
  RED_BG_SOFT: 'rgba(239,68,68,0.08)',
  RED_BG: 'rgba(239,68,68,0.15)',
  RED_BORDER: 'rgba(239,68,68,0.2)',

  // Amber — warning, running
  AMBER: '#f59e0b',
  AMBER_BG: 'rgba(245,158,11,0.15)',

  // Blue — pending, queued, API, links
  BLUE: '#3b82f6',
  BLUE_BG: 'rgba(59,130,246,0.15)',
  BLUE_SUBTLE: 'rgba(59,130,246,0.1)',

  // Purple — DEBUG, cancelled
  PURPLE: '#8b5cf6',

  // Steel Blue / Sage — dependency-group accents (workflow Tasks DAG view)
  INDIGO: '#9BB8CD',
  INDIGO_BG: 'rgba(155,184,205,0.4)',
  TEAL: '#D4E2D4',
  TEAL_BG: 'rgba(212,226,212,0.4)',
  // Dark text for use on light/pastel accent fills (e.g. dependency-number badge)
  ON_ACCENT_DARK: 'rgba(0,0,0,0.82)',

  // Surface overlays — hover, selected, focus states
  HOVER: 'rgba(0, 0, 0, 0.08)',
  SELECTED: 'rgba(0, 0, 0, 0.12)',
  SELECTED_HOVER: 'rgba(0, 0, 0, 0.16)',

  // Neutral gray overlay — scrollbar thumbs, muted dividers (theme-agnostic)
  SCROLLBAR_THUMB: 'rgba(150, 150, 150, 0.35)',
} as const;

// ============================================================================
// LINE HEIGHTS
// ============================================================================
export const LINE_HEIGHTS = {
  TIGHT: 1.2,
  NORMAL: 1.5,
  RELAXED: 1.6,
  LOOSE: 2,
} as const;

// ============================================================================
// LETTER SPACING
// ============================================================================
export const LETTER_SPACING = {
  TIGHT: '-0.02em',
  NORMAL: '0',
  WIDE: '0.02em',
  WIDER: '0.05em',
  WIDEST: '0.1em',
} as const;

// ============================================================================
// BUTTON SIZES
// ============================================================================
export const BUTTON_SIZES = {
  // Standard action button (e.g. "Add Folder", "Other Actions")
  HEIGHT: '32px',
  PADDING: '4px 12px',
  FONT_SIZE: '13px',
  FONT_WEIGHT: 500,
  BORDER_RADIUS: '6px',
  // Icon inside button
  ICON_FONT_SIZE: '16px',
} as const;

// ============================================================================
// SPACING & SIZING
// ============================================================================
export const SPACING = {
  // Component dimensions
  LEFT_SIDEBAR_WIDTH: 48,
  FOLDER_SIDEBAR_WIDTH_PERCENT: '20%',
  BOTTOM_PANEL_HEIGHT_PERCENT: '100%',
  BOTTOM_PANEL_MIN_HEIGHT: 200,

  // Icon button sizes
  ICON_BUTTON_SMALL: 16,
  ICON_BUTTON_MEDIUM: 20,
  ICON_BUTTON_LARGE: 24,

  // Indentation for nested items
  INDENT_PER_LEVEL: 1, // in rem
} as const;

// ============================================================================
// TRANSITION DURATIONS
// ============================================================================
export const TRANSITIONS = {
  FAST: '0.2s',
  NORMAL: '0.3s',
  SLOW: '0.5s',
  EASE: 'ease',
} as const;

// ============================================================================
// BORDER RADIUS
// ============================================================================
export const BORDER_RADIUS = {
  NONE: 0,
  SM: 0.5,
  MD: 1,
  LG: 1.5,
  FULL: '50%',
} as const;

// ============================================================================
// TASK STATE COLORS
// ============================================================================
export const TASK_STATE_COLORS = {
  success: {
    bg: 'rgba(17,212,82,0.12)',
    text: '#0ab840',
    border: 'rgba(17,212,82,0.35)',
    dot: 'rgba(17,212,82,0.85)',
  },
  running: {
    bg: COLORS.BLUE_SUBTLE,
    text: COLORS.BLUE,
    border: 'rgba(59,130,246,0.3)',
    dot: 'rgba(59,130,246,0.8)',
  },
  queued_in_redis: {
    bg: COLORS.BLUE_SUBTLE,
    text: COLORS.BLUE,
    border: 'rgba(59,130,246,0.25)',
    dot: 'rgba(59,130,246,0.7)',
  },
  queued_for_connection: {
    bg: COLORS.AMBER_BG,
    text: COLORS.AMBER,
    border: 'rgba(245,158,11,0.35)',
    dot: 'rgba(245,158,11,0.8)',
  },
  error: {
    bg: COLORS.RED_BG,
    text: COLORS.RED,
    border: COLORS.RED_BORDER,
    dot: 'rgba(239,68,68,0.8)',
  },
  failed: {
    bg: COLORS.RED_BG,
    text: COLORS.RED,
    border: COLORS.RED_BORDER,
    dot: 'rgba(239,68,68,0.8)',
  },
  scheduled: {
    bg: 'rgba(148,163,184,0.1)',
    text: 'var(--text-secondary)',
    border: 'rgba(148,163,184,0.25)',
    dot: 'rgba(148,163,184,0.6)',
  },
  cancelled: {
    bg: 'rgba(139,92,246,0.1)',
    text: '#8b5cf6',
    border: 'rgba(139,92,246,0.3)',
    dot: 'rgba(139,92,246,0.8)',
  },
} as const;

// ============================================================================
// TASK DEPENDENCY GROUP COLORS
// Alternating styles for the workflow Tasks list so the user can see which tasks
// form a connected dependency group (DAG). Each group gets a solid left `bar`
// plus a very faint row `tint`; colors alternate (indigo / teal) per group.
// ============================================================================
export const TASK_DEPENDENCY_GROUP_COLORS = [
  { bar: COLORS.INDIGO, tint: COLORS.INDIGO_BG },
  { bar: COLORS.TEAL, tint: COLORS.TEAL_BG },
] as const;

// ============================================================================
// OPACITY
// ============================================================================
export const OPACITY = {
  FULL: 1,
  HIGH: 0.9,
  MEDIUM: 0.8,
  LOW: 0.5,
  DISABLED: 0.5,
} as const;
