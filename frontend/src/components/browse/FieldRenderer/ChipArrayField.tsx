/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import { Box, Chip, Typography } from '@mui/material';

interface ChipArrayFieldProps {
  fieldName: string;
  value: unknown;
  onChange: (name: string, val: string[]) => void;
  readOnly?: boolean;
  placeholder?: string;
}

function toArray(value: unknown): string[] {
  if (Array.isArray(value)) return value.map(String);
  if (typeof value === 'string' && value.trim()) return [value];
  return [];
}

export function ChipArrayField({
  fieldName,
  value,
  onChange,
  readOnly = false,
  placeholder,
}: ChipArrayFieldProps) {
  const [input, setInput] = useState('');
  const chips = toArray(value);

  const commit = () => {
    const trimmed = input.trim();
    if (!trimmed || chips.includes(trimmed)) {
      setInput('');
      return;
    }
    onChange(fieldName, [...chips, trimmed]);
    setInput('');
  };

  const remove = (idx: number) =>
    onChange(
      fieldName,
      chips.filter((_, i) => i !== idx),
    );

  if (readOnly) {
    if (chips.length === 0)
      return (
        <Typography sx={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '13px' }}>
          —
        </Typography>
      );
    return (
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
        {chips.map((c, i) => (
          <Chip
            key={i}
            label={c}
            size="small"
            sx={{
              bgcolor: 'var(--bg-tertiary)',
              color: 'var(--text-primary)',
              fontSize: '12px',
              height: 24,
            }}
          />
        ))}
      </Box>
    );
  }

  return (
    <Box
      sx={{
        display: 'flex',
        flexWrap: 'wrap',
        alignItems: 'center',
        gap: 0.5,
        minHeight: 40,
        px: 1.5,
        py: 0.75,
        border: '1px solid var(--border)',
        borderRadius: 1,
        bgcolor: 'var(--bg-primary)',
        cursor: 'text',
        '&:focus-within': { borderColor: 'var(--accent)' },
      }}
      onClick={() => document.getElementById(`chip-input-${fieldName}`)?.focus()}
    >
      {chips.map((c, i) => (
        <Chip
          key={i}
          label={c}
          size="small"
          onDelete={() => remove(i)}
          sx={{
            bgcolor: 'var(--bg-tertiary)',
            color: 'var(--text-primary)',
            fontSize: '12px',
            height: 24,
            '& .MuiChip-deleteIcon': { color: 'var(--text-secondary)', fontSize: 14 },
          }}
        />
      ))}
      <input
        id={`chip-input-${fieldName}`}
        value={input}
        onChange={(e) => setInput(e.target.value)}
        onKeyDown={(e) => {
          if (e.key === 'Enter' || e.key === ',') {
            e.preventDefault();
            commit();
          }
          if (e.key === 'Backspace' && !input && chips.length) remove(chips.length - 1);
        }}
        onBlur={commit}
        placeholder={chips.length === 0 ? (placeholder ?? 'Type and press Enter…') : ''}
        style={{
          border: 'none',
          outline: 'none',
          background: 'transparent',
          color: 'var(--text-primary)',
          fontSize: '13px',
          flex: '1 1 80px',
          minWidth: 80,
          padding: '2px 0',
        }}
      />
    </Box>
  );
}
