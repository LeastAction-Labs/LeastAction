/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useNavigate } from '@tanstack/react-router';

import { Close as CloseIcon } from '@mui/icons-material';
import { Box, Button, IconButton, Typography } from '@mui/material';

import { COLORS, FONT_SIZES } from '@/constants';
import { CatalogType, useGlobal } from '@/contexts/GlobalContext';

// Matches item_type_visual_config colors from schema files
const TYPE_COLORS: Record<string, string> = {
  action: '#eab308',
  operator: '#f97316',
  payload: '#8b5cf6',
  skill: '#6366f1',
  usecase: '#6366f1',
  'folder.workflow': '#06b6d4',
  'folder.task': '#10b981',
};

function typeColor(item_type: string): string {
  const base = item_type.split('.')[0];
  return TYPE_COLORS[item_type] ?? TYPE_COLORS[base] ?? 'var(--accent)';
}

interface ItemTabBarProps {
  activeItemLaui: string | null;
}

export default function ItemTabBar({ activeItemLaui }: ItemTabBarProps) {
  const { openTabs, removeTab, clearTabs, setCatalogType } = useGlobal();
  const navigate = useNavigate();

  if (openTabs.length === 0) return null;

  const handleTabClick = (tab: (typeof openTabs)[0]) => {
    if (tab.source === 'marketplace') {
      setCatalogType(CatalogType.MARKETPLACE);
      void navigate({ to: '/marketplace', search: { laui: tab.laui } });
    } else {
      setCatalogType(CatalogType.BROWSE);
      void navigate({
        to: '/path',
        search: { laui: tab.laui, itemtype: tab.item_type, itemname: tab.name },
      });
    }
  };

  const handleClose = (e: React.MouseEvent, laui: string) => {
    e.stopPropagation();
    const idx = openTabs.findIndex((t) => t.laui === laui);
    removeTab(laui);

    if (laui !== activeItemLaui) return;

    const remaining = openTabs.filter((t) => t.laui !== laui);
    if (remaining.length === 0) {
      void navigate({ to: '/path', search: {} });
      return;
    }
    const next = remaining[idx] ?? remaining[idx - 1];
    if (next.source === 'marketplace') {
      void navigate({ to: '/marketplace', search: { laui: next.laui } });
    } else {
      void navigate({
        to: '/path',
        search: { laui: next.laui, itemtype: next.item_type, itemname: next.name },
      });
    }
  };

  const handleCloseAll = () => {
    clearTabs();
    void navigate({ to: '/path', search: {} });
  };

  return (
    <Box
      sx={{
        display: 'flex',
        alignItems: 'stretch',
        borderBottom: 1,
        borderColor: 'var(--border-color)',
        bgcolor: 'var(--bg-secondary)',
        flexShrink: 0,
        height: 32,
        overflow: 'hidden',
        px: '6px',
      }}
    >
      {/* Scrollable tabs area */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'stretch',
          overflowX: 'auto',
          overflowY: 'hidden',
          flex: 1,
          minWidth: 0,
          '&::-webkit-scrollbar': { height: 3 },
          '&::-webkit-scrollbar-thumb': {
            bgcolor: 'var(--border-color)',
            borderRadius: 2,
          },
        }}
      >
        {openTabs.map((tab) => {
          const isActive = tab.laui === activeItemLaui;
          return (
            <Box
              key={tab.laui}
              onClick={() => handleTabClick(tab)}
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 0.75,
                px: 1.25,
                cursor: 'pointer',
                flexShrink: 0,
                maxWidth: 180,
                minWidth: 80,
                position: 'relative',
                borderRight: '1px solid var(--border-color)',
                bgcolor: isActive ? 'var(--bg-primary)' : 'transparent',
                borderBottom: isActive ? '2px solid var(--accent)' : '2px solid transparent',
                '&:hover .tab-close': { visibility: 'visible' },
                '&:hover': { bgcolor: 'var(--bg-primary)' },
              }}
            >
              {/* Type color dot */}
              <Box
                sx={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  bgcolor: typeColor(tab.item_type),
                  flexShrink: 0,
                }}
              />

              {/* Name */}
              <Typography
                sx={{
                  fontSize: FONT_SIZES.XS,
                  fontWeight: isActive ? 600 : 400,
                  color: isActive ? 'var(--text-primary)' : 'var(--text-secondary)',
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  flex: 1,
                  lineHeight: 1,
                }}
              >
                {tab.name}
              </Typography>

              {/* Close button */}
              <IconButton
                className="tab-close"
                size="small"
                onClick={(e) => handleClose(e, tab.laui)}
                sx={{
                  visibility: isActive ? 'visible' : 'hidden',
                  p: 0.75,
                  flexShrink: 0,
                  color: 'var(--text-secondary)',
                  '&:hover': {
                    color: 'var(--text-primary)',
                    bgcolor: COLORS.SELECTED,
                    borderRadius: '4px',
                  },
                }}
              >
                <CloseIcon sx={{ fontSize: 12 }} />
              </IconButton>
            </Box>
          );
        })}
      </Box>

      {/* Close all tabs button — always visible at right end */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          px: 1,
          flexShrink: 0,
          borderLeft: '1px solid var(--border-color)',
          bgcolor: 'var(--bg-secondary)',
        }}
      >
        <Button
          size="small"
          variant="contained"
          color="error"
          onClick={handleCloseAll}
          sx={{
            fontSize: '11px',
            textTransform: 'none',
            minWidth: 0,
            px: 1.5,
            py: 0.5,
            m: '2px',
            lineHeight: 1,
          }}
        >
          close all tabs
        </Button>
      </Box>
    </Box>
  );
}
