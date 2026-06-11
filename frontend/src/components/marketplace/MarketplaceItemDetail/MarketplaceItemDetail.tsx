/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import { ContentCopy as CopyIcon } from '@mui/icons-material';
import { Box, CircularProgress, IconButton, Tooltip, Typography } from '@mui/material';

import type { FullItemData } from '@/components/browse/types';
import { Chip } from '@/components/ui';

import LAMarketplaceIcon from '../LAMarketplaceIcon/LAMarketplaceIcon';
import MarketplaceItemTabView from '../MarketplaceItemTabView/MarketplaceItemTabView';
import ItemMeta from './ItemMeta';

interface MarketplaceItemDetailProps {
  item: FullItemData | null;
  isLoading: boolean;
  onAddFilter?: (field: string, value: string) => void;
}

export default function MarketplaceItemDetail({
  item,
  isLoading,
  onAddFilter,
}: Readonly<MarketplaceItemDetailProps>) {
  const [copied, setCopied] = useState(false);

  if (isLoading) {
    return (
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          bgcolor: 'var(--bg-primary)',
        }}
      >
        <CircularProgress size={32} sx={{ color: 'var(--accent)' }} />
      </Box>
    );
  }

  if (!item) {
    return (
      <Box
        sx={{
          display: 'flex',
          flexDirection: 'column',
          alignItems: 'center',
          justifyContent: 'center',
          height: '100%',
          bgcolor: 'var(--bg-primary)',
          gap: 2,
        }}
      >
        <LAMarketplaceIcon size={48} seed="empty" />
        <Typography sx={{ color: 'var(--text-secondary)', fontSize: '14px' }}>
          Search and select an item to view details
        </Typography>
      </Box>
    );
  }

  const handleCopy = () => {
    void navigator.clipboard.writeText(item.laui).then(() => {
      setCopied(true);
      setTimeout(() => setCopied(false), 1500);
    });
  };

  return (
    <Box
      sx={{
        display: 'flex',
        height: '100%',
        bgcolor: 'var(--bg-primary)',
        overflow: 'hidden',
      }}
    >
      {/* ── Left: main content (grows to fill available space) ── */}
      <Box
        sx={{
          flex: 1,
          minWidth: 0,
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        {/* Header */}
        <Box
          sx={{
            p: 2.5,
            borderBottom: 1,
            borderColor: 'var(--border-color)',
            bgcolor: 'var(--bg-secondary)',
            display: 'flex',
            alignItems: 'center',
            gap: 2,
          }}
        >
          {/* Item icon */}
          <Box sx={{ flexShrink: 0 }}>
            {item.image_url ? (
              <Box
                component="img"
                src={item.image_url}
                sx={{
                  width: 40,
                  height: 40,
                  borderRadius: 1,
                  objectFit: 'cover',
                  display: 'block',
                }}
              />
            ) : (
              <LAMarketplaceIcon size={40} seed={item.laui} />
            )}
          </Box>

          {/* Title + primary chips */}
          <Box
            sx={{
              flex: 1,
              minWidth: 0,
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'space-between',
              flexWrap: 'wrap',
              gap: 1,
            }}
          >
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 0.75,
                flexWrap: 'wrap',
              }}
            >
              <Typography
                variant="h5"
                sx={{
                  color: 'var(--text-primary)',
                  fontWeight: 700,
                  lineHeight: 1.2,
                }}
              >
                {item.name || 'Unnamed'}
              </Typography>
              {/* Marketplace source badge */}
              <Chip label="MP" variant="mp" tooltip="Marketplace item" />
            </Box>

            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 0.75,
                flexWrap: 'wrap',
              }}
            >
              {/* Type — filterable */}
              {item.item_type && (
                <Chip
                  label={item.item_type}
                  variant="type"
                  clickable={!!onAddFilter}
                  onClick={onAddFilter ? () => onAddFilter('type', item.item_type) : undefined}
                  tooltip={onAddFilter ? `type:"${item.item_type}"` : undefined}
                />
              )}
            </Box>
          </Box>

          {/* Copy identifier action */}
          <Tooltip title={copied ? 'Copied!' : 'Copy identifier'} placement="top">
            <IconButton
              size="small"
              onClick={handleCopy}
              sx={{
                color: 'var(--text-secondary)',
                flexShrink: 0,
                '&:hover': { bgcolor: 'var(--bg-primary)' },
              }}
            >
              <CopyIcon fontSize="small" />
            </IconButton>
          </Tooltip>
        </Box>

        {/* Tab content */}
        <Box sx={{ flex: 1, overflow: 'hidden' }}>
          <MarketplaceItemTabView item={item} />
        </Box>
      </Box>

      {/* ── Right: metadata sidebar (fixed width) ── */}
      <Box
        sx={{
          flexShrink: 0,
          width: 260,
          minWidth: 200,
          borderLeft: '1px solid var(--border-color)',
          bgcolor: 'var(--bg-secondary)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'hidden',
        }}
      >
        <ItemMeta item={item} onAddFilter={onAddFilter} />
      </Box>
    </Box>
  );
}
