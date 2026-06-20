/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import { Box, Button } from '@mui/material';

import { BORDER_RADIUS } from '@/constants';

/**
 * Inline chat actions (quick replies) — pure frontend, reusing the existing
 * content-type marker. The AI signals output type with a `[content_type:X]`
 * prefix that the backend strips into `response.content_type` (see
 * backend/src/core/ai/service.py `_parse_content_type_marker`, matches any
 * `\w+`). So an assistant turn that emits:
 *
 *   [content_type:actions]
 *   {
 *     "text": "Found 3 duplicate order_ids in today's partition. Fix it?",
 *     "actions": [
 *       { "label": "Approve & rerun", "variant": "primary",
 *         "send": "Yes — re-run the dedupe step in load_sales and reload 2026-06-17" },
 *       { "label": "Show me the dupes first", "send": "List the duplicate order_ids first" },
 *       { "label": "Dismiss", "dismiss": true }
 *     ]
 *   }
 *
 * arrives here as `content_type: 'actions'` with the JSON body as `content`.
 *
 * Clicking a button does NOT call run endpoints directly — it posts `send` back
 * into the conversation as the next user turn, so the AI executes the action via
 * its own tools and stays in the loop: it sees the result, surfaces any error,
 * and can retry or follow up. Direct API calls would skip the AI and hide
 * failures from it. `dismiss` buttons just close the row and send nothing.
 *
 * No backend change required — the only thing that teaches the AI to emit this
 * block is a skill (prompt text).
 */
export interface ChatAction {
  label: string;
  /** message posted to the AI as the next user turn; defaults to `label` */
  send?: string;
  variant?: 'primary' | 'secondary';
  /** local-only: closes the row and sends nothing */
  dismiss?: boolean;
}

function isAction(a: unknown): a is ChatAction {
  return !!a && typeof a === 'object' && typeof (a as ChatAction).label === 'string';
}

/**
 * Parse an `actions` content-type message into display text + buttons.
 *
 * Accepts a bare array of actions, or `{ text, actions }`. If the body is not
 * valid JSON, the raw string is returned as text and `actions` is empty (so a
 * malformed reply degrades to plain text instead of vanishing).
 */
export function parseActionMessage(content: string): { text: string; actions: ChatAction[] } {
  try {
    const parsed = JSON.parse(content);
    if (Array.isArray(parsed)) return { text: '', actions: parsed.filter(isAction) };
    if (parsed && typeof parsed === 'object') {
      const text = typeof parsed.text === 'string' ? parsed.text : '';
      const actions = Array.isArray(parsed.actions) ? parsed.actions.filter(isAction) : [];
      return { text, actions };
    }
  } catch {
    // not JSON — show it as-is
  }
  return { text: content, actions: [] };
}

interface ChatActionsProps {
  actions: ChatAction[];
  /** posts the chosen action's message as the next user turn */
  onSend: (message: string) => void;
  /** true while a turn is in flight — blocks clicks */
  disabled?: boolean;
}

export default function ChatActions({ actions, onSend, disabled }: ChatActionsProps) {
  // a chat action is a one-shot decision: once chosen, lock the row
  const [chosen, setChosen] = useState<string | null>(null);

  if (!actions.length) return null;

  const handle = (a: ChatAction) => {
    if (chosen || disabled) return;
    setChosen(a.label);
    if (!a.dismiss) onSend(a.send ?? a.label);
  };

  return (
    <Box sx={{ mt: 1, display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
      {actions.map((a) => {
        const isPrimary = a.variant !== 'secondary' && !a.dismiss;
        const isChosen = chosen === a.label;
        return (
          <Button
            key={a.label}
            size="small"
            onClick={() => handle(a)}
            disabled={(!!chosen && !isChosen) || disabled}
            variant={isPrimary ? 'contained' : 'outlined'}
            sx={{
              textTransform: 'none',
              fontSize: '11px',
              py: 0.4,
              borderRadius: BORDER_RADIUS.SM,
              ...(isPrimary
                ? {
                    bgcolor: 'var(--accent)',
                    color: '#fff',
                    boxShadow: 'none',
                    '&:hover': { bgcolor: 'var(--accent)', opacity: 0.9, boxShadow: 'none' },
                  }
                : {
                    color: 'var(--text-secondary)',
                    borderColor: 'var(--border)',
                    '&:hover': { borderColor: 'var(--accent)', color: 'var(--accent)' },
                  }),
              '&.Mui-disabled': { opacity: 0.4 },
            }}
          >
            {a.label}
          </Button>
        );
      })}
    </Box>
  );
}
