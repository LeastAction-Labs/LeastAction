/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import CheckCircleOutlineIcon from '@mui/icons-material/CheckCircleOutline';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import ErrorOutlineIcon from '@mui/icons-material/ErrorOutline';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { Box, Button, Collapse, IconButton, Stack, Typography } from '@mui/material';

import type { CodeblockValidationEntry, ValidationResult } from '@/services/validation.service';
import { formatValidationForClipboard } from '@/services/validation.service';

type ValidationPanelProps = {
  result: ValidationResult | null;
  onEntryClick?: (entry: CodeblockValidationEntry) => void;
};

export default function ValidationPanel({ result, onEntryClick }: ValidationPanelProps) {
  const [expanded, setExpanded] = useState(true);

  if (!result) return null;

  const { valid, errors, warnings } = result;
  const total = errors.length + warnings.length;

  const handleCopy = () => {
    const text = formatValidationForClipboard(result);
    if (text) void navigator.clipboard.writeText(text);
  };

  return (
    <Box
      sx={{
        border: '1px solid var(--border)',
        borderRadius: 1,
        bgcolor: 'var(--bg-secondary)',
        mt: 1,
      }}
    >
      <Stack
        direction="row"
        alignItems="center"
        sx={{
          px: 1.5,
          py: 0.75,
          cursor: 'pointer',
          borderBottom: expanded && total > 0 ? '1px solid var(--border)' : 'none',
        }}
        onClick={() => setExpanded((v) => !v)}
      >
        {valid && errors.length === 0 ? (
          <CheckCircleOutlineIcon sx={{ color: '#4caf50', fontSize: 18, mr: 1 }} />
        ) : errors.length > 0 ? (
          <ErrorOutlineIcon sx={{ color: '#f44336', fontSize: 18, mr: 1 }} />
        ) : (
          <WarningAmberIcon sx={{ color: '#ff9800', fontSize: 18, mr: 1 }} />
        )}
        <Typography variant="body2" sx={{ color: 'var(--text-primary)', fontWeight: 500 }}>
          {valid
            ? `Validation passed${warnings.length > 0 ? ` (${warnings.length} warning${warnings.length === 1 ? '' : 's'})` : ''}`
            : `Validation failed: ${errors.length} error${errors.length === 1 ? '' : 's'}${warnings.length > 0 ? `, ${warnings.length} warning${warnings.length === 1 ? '' : 's'}` : ''}`}
        </Typography>
        <Box sx={{ flexGrow: 1 }} />
        {total > 0 && (
          <Button
            size="small"
            startIcon={<ContentCopyIcon sx={{ fontSize: 14 }} />}
            onClick={(e) => {
              e.stopPropagation();
              handleCopy();
            }}
            sx={{
              textTransform: 'none',
              color: 'var(--text-secondary)',
              fontSize: '0.75rem',
              mr: 0.5,
            }}
          >
            Copy
          </Button>
        )}
        <IconButton size="small" sx={{ color: 'var(--text-secondary)' }}>
          {expanded ? <ExpandLessIcon fontSize="small" /> : <ExpandMoreIcon fontSize="small" />}
        </IconButton>
      </Stack>
      <Collapse in={expanded && total > 0}>
        <Box sx={{ px: 1.5, py: 1, maxHeight: 240, overflowY: 'auto' }}>
          {errors.map((e, idx) => (
            <EntryRow key={`err-${idx}`} entry={e} severity="error" onClick={onEntryClick} />
          ))}
          {warnings.map((w, idx) => (
            <EntryRow key={`warn-${idx}`} entry={w} severity="warning" onClick={onEntryClick} />
          ))}
        </Box>
      </Collapse>
    </Box>
  );
}

function EntryRow({
  entry,
  severity,
  onClick,
}: {
  entry: CodeblockValidationEntry;
  severity: 'error' | 'warning';
  onClick?: (e: CodeblockValidationEntry) => void;
}) {
  const color = severity === 'error' ? '#f44336' : '#ff9800';
  const loc = [entry.file, entry.line].filter(Boolean).join(':');
  return (
    <Box
      onClick={() => onClick?.(entry)}
      sx={{
        display: 'flex',
        alignItems: 'flex-start',
        py: 0.5,
        fontSize: '0.75rem',
        cursor: onClick ? 'pointer' : 'default',
        color: 'var(--text-primary)',
        '&:hover': onClick ? { bgcolor: 'var(--bg-tertiary)' } : undefined,
        borderRadius: 0.5,
        px: 0.5,
      }}
    >
      <Box
        component="span"
        sx={{
          color,
          fontFamily: 'monospace',
          fontWeight: 600,
          mr: 1,
          whiteSpace: 'nowrap',
        }}
      >
        [{entry.code}]
      </Box>
      <Box component="span" sx={{ flexGrow: 1 }}>
        {entry.message}
        {loc && (
          <Box
            component="span"
            sx={{ ml: 1, color: 'var(--text-secondary)', fontFamily: 'monospace' }}
          >
            — {loc}
          </Box>
        )}
      </Box>
    </Box>
  );
}
