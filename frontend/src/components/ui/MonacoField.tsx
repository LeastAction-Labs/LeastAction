/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useMemo } from 'react';

import { Box, Typography } from '@mui/material';

import type { FieldRendererProps } from '@/components/browse/FieldRenderer/types';

import { MonacoWrapper } from './MonacoWrapper';

interface MonacoFieldProps extends Pick<FieldRendererProps, 'field' | 'value' | 'onChange'> {
  isReadOnly?: boolean;
  maxHeight?: number;
  mode?: string;
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 1,
  },
  charCount: {
    fontSize: '11px',
    color: 'var(--text-secondary)',
  },
  warning: {
    fontSize: '11px',
    color: 'var(--warning, #f59e0b)',
    mt: 0.5,
  },
};

function validateAgainstPlaceholder(value: any, placeholder: Record<string, unknown>): string[] {
  const placeholderKeys = Object.keys(placeholder);
  let parsed: Record<string, unknown> | null = null;

  if (typeof value === 'string') {
    try {
      parsed = JSON.parse(value);
    } catch {
      return [];
    }
  } else if (typeof value === 'object' && value !== null) {
    parsed = value;
  }

  if (!parsed || typeof parsed !== 'object') return [];

  const missingKeys = placeholderKeys.filter((k) => !(k in parsed));
  const extraKeys = Object.keys(parsed).filter((k) => !placeholderKeys.includes(k));

  const warnings: string[] = [];
  if (missingKeys.length) warnings.push(`Missing keys: ${missingKeys.join(', ')}`);
  if (extraKeys.length) warnings.push(`Unexpected keys: ${extraKeys.join(', ')}`);
  return warnings;
}

export const MonacoField = ({
  field,
  value,
  onChange,
  isReadOnly,
  maxHeight,
  mode,
}: MonacoFieldProps) => {
  const placeholder = field.sample_placeholder as Record<string, unknown> | undefined;

  // Pre-fill with placeholder on create if value is empty
  const effectiveValue = useMemo(() => {
    if (mode === 'create' && !value && placeholder) {
      return JSON.stringify(placeholder, null, 2);
    }
    return value || '';
  }, [mode, placeholder]);

  const warnings = useMemo(() => {
    if (!placeholder || !value) return [];
    return validateAgainstPlaceholder(value, placeholder);
  }, [value, placeholder]);

  const handleChange = (newValue: string) => {
    // If we pre-filled with placeholder, fire the initial value up
    onChange(field.name, newValue);
  };

  return (
    <Box sx={styles.container}>
      <MonacoWrapper
        content={effectiveValue}
        fileName={undefined}
        readOnly={isReadOnly}
        field={field}
        maxHeight={maxHeight}
        onChange={isReadOnly ? undefined : handleChange}
      />
      {field.max_length && (
        <Box sx={styles.charCount}>
          {(value || '').length}/{field.max_length} characters
        </Box>
      )}
      {warnings.map((w, i) => (
        <Typography key={i} sx={styles.warning}>
          ⚠ {w}
        </Typography>
      ))}
    </Box>
  );
};
