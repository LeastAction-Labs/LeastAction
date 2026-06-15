/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import { createFileRoute } from '@tanstack/react-router';

import { Box, CircularProgress, Typography } from '@mui/material';

import AIWizard from '@/components/ai/AIWizard';
import type { AIItemType } from '@/contexts/AIContext';
import { AIMode, useAI } from '@/contexts/AIContext';
import { searchCatalogItems } from '@/services';

export const Route = createFileRoute('/ai/create')({
  validateSearch: (search: Record<string, unknown>) => ({
    sessionId: typeof search.sessionId === 'string' ? search.sessionId : undefined,
  }),
  component: RouteComponent,
});

function RouteComponent() {
  const { sessionId } = Route.useSearch();
  const { sessionLaui, setSessionLaui, setItemType, setConfig, setMode } = useAI();
  const [loading, setLoading] = useState(!!sessionId && !sessionLaui);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    setError(null);
    if (!sessionId) {
      setLoading(false);
      setSessionLaui(null);
      setMode(AIMode.ITEMTYPE);
      return;
    }
    if (sessionLaui) {
      setLoading(false);
      return;
    }
    setLoading(true);
    searchCatalogItems('generate_history', false, {
      filters: { name: sessionId },
      perPage: 1,
      projection: [
        'name',
        'created_item_type',
        'ai_provider',
        'connection_laui',
        'connection_name',
      ],
    })
      .then((response) => {
        const item = response?.items?.[0];
        if (!item) {
          setError('Session not found');
          setLoading(false);
          return;
        }
        setSessionLaui(item.laui);
        if (item.created_item_type) setItemType(item.created_item_type as AIItemType);
        if (item.ai_provider && item.connection_laui) {
          setConfig({
            aiProvider: item.ai_provider,
            aiChatLaui: '',
            aiChatName: '',
            connectionLaui: item.connection_laui,
            connectionName: item.connection_name || '',
            includeGuideDoc: false,
            includeInstallGuide: false,
          });
          setMode(AIMode.MANUALEDITOR);
        } else {
          setMode(AIMode.AICONFIG);
        }
        setLoading(false);
      })
      .catch(() => {
        setError('Failed to load session');
        setLoading(false);
      });
  }, [sessionId]);

  if (loading)
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh',
          bgcolor: 'var(--bg-primary)',
        }}
      >
        <CircularProgress sx={{ color: 'var(--accent)' }} />
      </Box>
    );
  if (error)
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          minHeight: '100vh',
          bgcolor: 'var(--bg-primary)',
        }}
      >
        <Typography sx={{ color: 'var(--text-secondary)' }}>{error}</Typography>
      </Box>
    );
  return <AIWizard />;
}
