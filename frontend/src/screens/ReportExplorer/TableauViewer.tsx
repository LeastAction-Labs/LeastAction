/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import { Box, CircularProgress, Typography } from '@mui/material';

import type { CatalogItem } from '@/components/browse/types';
import { type EmbedToken, getEmbedToken } from '@/services/embed.service';

interface Props {
  item: CatalogItem;
}

export default function TableauViewer({ item }: Props) {
  const [token, setToken] = useState<EmbedToken | null>(null);
  const [error, setError] = useState<string | null>(null);
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null);

  const load = useCallback(async () => {
    setError(null);
    try {
      // Tableau Connected App JWT is valid for 10 min; refresh before expiry
      const t = await getEmbedToken(item.laui);
      setToken(t);
      if (timerRef.current) clearTimeout(timerRef.current);
      timerRef.current = setTimeout(
        () => void load(),
        Math.max((t.expires_in - 60) * 1000, 30_000),
      );
    } catch (e: any) {
      setError(e?.response?.data?.detail ?? e?.message ?? 'Failed to load Tableau embed.');
    }
  }, [item.laui]);

  useEffect(() => {
    void load();
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current);
    };
  }, [load]);

  if (error) {
    return (
      <Box sx={{ p: 3 }}>
        <Typography sx={{ color: 'var(--error, #ef4444)', fontSize: '0.875rem' }}>
          {error}
        </Typography>
      </Box>
    );
  }

  if (!token) {
    return (
      <Box
        sx={{
          display: 'flex',
          justifyContent: 'center',
          alignItems: 'center',
          flex: 1,
          height: '100%',
        }}
      >
        <CircularProgress size={32} sx={{ color: 'var(--text-secondary)' }} />
      </Box>
    );
  }

  return (
    <Box sx={{ flex: 1, display: 'flex', overflow: 'hidden' }}>
      <iframe
        src={token.embed_url}
        style={{ flex: 1, border: 'none' }}
        allowFullScreen
        title={item.name}
      />
    </Box>
  );
}
