/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { Box, Collapse, Stack, Typography } from '@mui/material';

import type { CodeblockValidationEntry, ValidationResult } from '@/services/validation.service';

type ValidationResultsViewProps = {
  value: unknown;
};

/** Parse the stored validation_results value (object or JSON string) into a ValidationResult. */
function parseValidationResult(value: unknown): ValidationResult | null {
  let obj: unknown = value;

  if (typeof value === 'string') {
    const trimmed = value.trim();
    if (!trimmed) return null;
    try {
      obj = JSON.parse(trimmed);
    } catch {
      return null;
    }
  }

  if (typeof obj !== 'object' || obj === null) return null;

  const record = obj as Record<string, unknown>;
  // Require at least the shape of a validation result.
  if (!('valid' in record) && !('errors' in record) && !('warnings' in record)) {
    return null;
  }

  return {
    valid: Boolean(record.valid),
    errors: Array.isArray(record.errors) ? (record.errors as CodeblockValidationEntry[]) : [],
    warnings: Array.isArray(record.warnings) ? (record.warnings as CodeblockValidationEntry[]) : [],
  };
}

const SEVERITY = {
  error: { color: '#f44336', Icon: ErrorOutlineIcon },
  warning: { color: '#ff9800', Icon: WarningAmberIcon },
} as const;

export default function ValidationResultsView({ value }: ValidationResultsViewProps) {
  const result = parseValidationResult(value);

  if (!result) {
    return (
      <Typography sx={{ color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: '14px' }}>
        No validation results
      </Typography>
    );
  }

  const { valid, errors, warnings } = result;
  const passed = valid && errors.length === 0;

  return (
    <Stack spacing={1}>
      {passed && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            border: '1px solid var(--border)',
            borderRadius: 1,
            bgcolor: 'var(--bg-secondary)',
            px: 1.5,
            py: 1,
          }}
        >
          <CheckCircleOutlineIcon sx={{ color: '#4caf50', fontSize: 18, mr: 1 }} />
          <Typography variant="body2" sx={{ color: 'var(--text-primary)', fontWeight: 500 }}>
            {warnings.length > 0
              ? `Validation passed (${warnings.length} warning${warnings.length === 1 ? '' : 's'})`
              : 'Validation passed'}
          </Typography>
        </Box>
      )}

      {errors.map((entry, idx) => (
        <ExpandableEntryRow key={`err-${idx}`} entry={entry} severity="error" />
      ))}
      {warnings.map((entry, idx) => (
        <ExpandableEntryRow key={`warn-${idx}`} entry={entry} severity="warning" />
      ))}
    </Stack>
  );
}

function ExpandableEntryRow({
  entry,
  severity,
}: {
  entry: CodeblockValidationEntry;
  severity: 'error' | 'warning';
}) {
  const [expanded, setExpanded] = useState(false);
  const { color, Icon } = SEVERITY[severity];

  return (
    <Box
      sx={{
        border: '1px solid var(--border)',
        borderRadius: 1,
        bgcolor: 'var(--bg-secondary)',
        overflow: 'hidden',
      }}
    >
      <Box
        onClick={() => setExpanded((v) => !v)}
        sx={{
          display: 'flex',
          alignItems: 'center',
          px: 1.5,
          py: 1,
          cursor: 'pointer',
          '&:hover': { bgcolor: 'var(--bg-tertiary)' },
        }}
      >
        <Icon sx={{ color, fontSize: 18, mr: 1, flexShrink: 0 }} />
        <Box
          component="span"
          sx={{
            color,
            fontFamily: 'monospace',
            fontWeight: 600,
            fontSize: '0.75rem',
            mr: 1,
            whiteSpace: 'nowrap',
          }}
        >
          [{entry.code}]
        </Box>
        <Typography
          variant="body2"
          sx={{
            color: 'var(--text-primary)',
            flexGrow: 1,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {entry.message}
        </Typography>
        {expanded ? (
          <ExpandLessIcon fontSize="small" sx={{ color: 'var(--text-secondary)', ml: 1 }} />
        ) : (
          <ExpandMoreIcon fontSize="small" sx={{ color: 'var(--text-secondary)', ml: 1 }} />
        )}
      </Box>
      <Collapse in={expanded}>
        <Box
          sx={{
            px: 1.5,
            py: 1,
            borderTop: '1px solid var(--border)',
            display: 'flex',
            flexDirection: 'column',
            gap: 0.75,
          }}
        >
          <DetailField label="Code" value={entry.code} mono />
          <DetailField label="Message" value={entry.message} />
          <DetailField label="File" value={entry.file ?? '—'} mono />
          <DetailField label="Line" value={entry.line != null ? String(entry.line) : '—'} mono />
        </Box>
      </Collapse>
    </Box>
  );
}

function DetailField({ label, value, mono }: { label: string; value: string; mono?: boolean }) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'flex-start', fontSize: '0.75rem' }}>
      <Box
        component="span"
        sx={{
          color: 'var(--text-secondary)',
          fontWeight: 600,
          minWidth: 64,
          flexShrink: 0,
        }}
      >
        {label}:
      </Box>
      <Box
        component="span"
        sx={{
          color: 'var(--text-primary)',
          fontFamily: mono ? 'monospace' : 'inherit',
          whiteSpace: 'pre-wrap',
          wordBreak: 'break-word',
        }}
      >
        {value}
      </Box>
    </Box>
  );
}
