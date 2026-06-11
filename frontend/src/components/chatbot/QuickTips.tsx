/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useRouterState } from '@tanstack/react-router';

import { Box, Chip, Typography } from '@mui/material';

import { BORDER_RADIUS, FONT_SIZES } from '@/constants';

const EXPLORER_HIDDEN_LABELS = new Set([
  'Operator Dev',
  'Deploy Usecase',
  'Create Usecase',
  'Run a Task',
  'Task Status',
  'Docs Lookup',
  'Run Action',
  'List Tasks',
]);

export interface Tip {
  label: string;
  prompt: string;
  emoji: string;
}

export const QUICK_TIPS: Tip[] = [
  { emoji: '⚙️', label: 'Operator Dev', prompt: 'Create a new operator' },
  { emoji: '📊', label: 'Get Report', prompt: 'Get the latest report' },
  { emoji: '👥', label: 'Customer Query', prompt: 'Show top customers by revenue' },
  { emoji: '🚀', label: 'Deploy Usecase', prompt: 'Deploy usecase' },
  { emoji: '📝', label: 'Create Usecase', prompt: 'Create a usecase for my pipeline' },
  { emoji: '▶️', label: 'Run a Task', prompt: 'Run a task' },
  { emoji: '🔍', label: 'Task Status', prompt: 'Get the status of a task' },
  { emoji: '💬', label: 'Send Slack', prompt: 'Send a Slack message' },
  { emoji: '📧', label: 'Send Email', prompt: 'Send an email' },
  { emoji: '📚', label: 'Docs Lookup', prompt: 'How do operators work?' },
  { emoji: '🔗', label: 'Run Action', prompt: 'Run an action' },
  { emoji: '📋', label: 'List Tasks', prompt: 'List all tasks and their status' },
];

interface QuickTipsProps {
  onSelect: (prompt: string) => void;
  compact?: boolean;
}

export default function QuickTips({ onSelect, compact = false }: QuickTipsProps) {
  const pathname = useRouterState({ select: (s) => s.location.pathname });
  const isExplorer = pathname === '/explore';
  const tips = isExplorer
    ? QUICK_TIPS.filter((t) => !EXPLORER_HIDDEN_LABELS.has(t.label))
    : QUICK_TIPS;

  return (
    <Box>
      {!compact && (
        <Typography
          sx={{
            fontSize: FONT_SIZES.XS,
            color: 'var(--text-secondary)',
            mb: 1.5,
            textAlign: 'center',
          }}
        >
          What would you like to do?
        </Typography>
      )}
      <Box
        sx={{
          display: 'flex',
          flexWrap: 'wrap',
          gap: 0.75,
          justifyContent: compact ? 'flex-start' : 'center',
        }}
      >
        {tips.map((tip) => (
          <Chip
            key={tip.label}
            label={`${tip.emoji} ${tip.label}`}
            onClick={() => onSelect(tip.prompt)}
            size="small"
            sx={{
              fontSize: FONT_SIZES.XS,
              bgcolor: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border)',
              borderRadius: BORDER_RADIUS.MD,
              cursor: 'pointer',
              transition: 'all 0.15s ease',
              '&:hover': {
                bgcolor: 'var(--bg-tertiary)',
                borderColor: 'var(--accent)',
                color: 'var(--accent)',
              },
              '& .MuiChip-label': { px: 1 },
            }}
          />
        ))}
      </Box>
    </Box>
  );
}
