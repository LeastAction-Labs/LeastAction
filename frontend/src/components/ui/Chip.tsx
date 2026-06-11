/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { type ReactElement } from 'react';

import { Chip as MuiChip, Tooltip } from '@mui/material';

export type ChipVariant =
  | 'tag'
  | 'type'
  | 'publisher'
  | 'category'
  | 'mp'
  | 'native'
  | 'version'
  | 'compatible'
  | 'incompatible'
  | 'deprecated'
  | 'official'
  | 'verified'
  | 'published'
  | 'draft';

const VARIANT_STYLES: Record<ChipVariant, object> = {
  tag: { bgcolor: 'var(--bg-primary)', color: 'var(--text-secondary)', fontSize: '10px' },
  type: { bgcolor: 'var(--accent)', color: '#fff', fontWeight: 600 },
  publisher: { bgcolor: 'var(--bg-primary)', color: 'var(--text-secondary)' },
  category: { bgcolor: 'var(--bg-primary)', color: 'var(--text-secondary)' },
  mp: { bgcolor: 'var(--accent)', color: '#fff', fontWeight: 700, fontSize: '10px' },
  native: {
    bgcolor: 'var(--bg-secondary)',
    color: 'var(--text-primary)',
    fontWeight: 600,
    fontSize: '10px',
    border: '1px solid var(--border-color)',
  },
  version: { bgcolor: 'var(--bg-primary)', color: 'var(--text-secondary)', fontWeight: 500 },
  compatible: { bgcolor: 'success.dark', color: '#fff', fontWeight: 500 },
  incompatible: { bgcolor: 'error.dark', color: '#fff', fontWeight: 500, cursor: 'help' },
  deprecated: { bgcolor: 'warning.dark', color: '#fff', fontWeight: 500 },
  official: { bgcolor: 'success.dark', color: '#fff', fontWeight: 600 },
  verified: { bgcolor: '#1976d2', color: '#fff', fontWeight: 600 },
  published: { bgcolor: 'success.dark', color: '#fff', fontWeight: 600, fontSize: '10px' },
  draft: {
    bgcolor: 'var(--bg-primary)',
    color: 'var(--text-secondary)',
    fontWeight: 600,
    fontSize: '10px',
    border: '1px dashed currentColor',
  },
};

interface ChipProps {
  label: string;
  variant?: ChipVariant;
  clickable?: boolean;
  onClick?: () => void;
  tooltip?: string;
  sx?: object;
  icon?: ReactElement;
}

export default function Chip({
  label,
  variant = 'tag',
  clickable = false,
  onClick,
  tooltip,
  sx,
  icon,
}: Readonly<ChipProps>) {
  const chip = (
    <MuiChip
      label={label}
      size="small"
      icon={icon}
      onClick={clickable && onClick ? onClick : undefined}
      sx={{
        fontSize: '11px',
        cursor: clickable ? 'pointer' : 'default',
        ...(clickable ? { '&:hover': { opacity: 0.75, filter: 'brightness(1.15)' } } : {}),
        '& .MuiChip-icon': { color: 'inherit' },
        ...VARIANT_STYLES[variant],
        ...sx,
      }}
    />
  );

  if (tooltip) {
    return (
      <Tooltip title={tooltip} placement="top" arrow>
        {chip}
      </Tooltip>
    );
  }
  return chip;
}
