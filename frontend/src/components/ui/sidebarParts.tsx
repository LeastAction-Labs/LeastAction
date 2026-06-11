/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { type ReactNode } from 'react';

import { Box, Typography } from '@mui/material';

export function MetaRow({ label, children }: Readonly<{ label: string; children: ReactNode }>) {
  return (
    <Box
      sx={{
        display: 'flex',
        justifyContent: 'space-between',
        alignItems: 'center',
        py: 0.625,
      }}
    >
      <Typography sx={{ color: 'var(--text-secondary)', fontSize: '12px', flexShrink: 0, mr: 1.5 }}>
        {label}
      </Typography>
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'flex-end',
          gap: 0.5,
          flexWrap: 'wrap',
        }}
      >
        {children}
      </Box>
    </Box>
  );
}

export function SectionTitle({ children }: Readonly<{ children: ReactNode }>) {
  return (
    <Typography
      sx={{
        color: 'var(--text-secondary)',
        fontSize: '10px',
        fontWeight: 700,
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
        mb: 1,
      }}
    >
      {children}
    </Typography>
  );
}

export function formatRelativeDate(dateStr: string | null | undefined): string {
  if (!dateStr) return '—';
  try {
    const diff = Date.now() - new Date(dateStr).getTime();
    const days = Math.floor(diff / 86_400_000);
    if (days === 0) return 'today';
    if (days === 1) return '1d ago';
    if (days < 30) return `${days}d ago`;
    if (days < 365) return `${Math.floor(days / 30)}mo ago`;
    return `${Math.floor(days / 365)}y ago`;
  } catch {
    return dateStr;
  }
}
