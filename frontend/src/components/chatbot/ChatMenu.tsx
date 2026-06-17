/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import AddIcon from '@mui/icons-material/Add';
import CloudIcon from '@mui/icons-material/Cloud';
import HistoryIcon from '@mui/icons-material/History';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import {
  Autocomplete,
  Box,
  Button,
  CircularProgress,
  Divider,
  TextField,
  Typography,
} from '@mui/material';

import { BORDER_RADIUS, FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import { searchCatalogItems } from '@/services';

import {
  type ProviderConfig,
  autocompleteSx,
  buildProviderConfigFromHistory,
  buildProviderConfigFromSelection,
  formatSessionLabel,
  listboxSx,
} from './ProviderList';

interface ChatMenuProps {
  open: boolean;
  /** When false (no default MCP/chat config), the agent + connection pickers are shown. */
  showAgentSelector: boolean;
  onNewSession: () => void;
  onSelectConfig: (config: ProviderConfig) => void;
  onClose: () => void;
}

const HISTORY_PAGE_SIZE = 10;

export default function ChatMenu({
  open,
  showAgentSelector,
  onNewSession,
  onSelectConfig,
  onClose,
}: ChatMenuProps) {
  const [agents, setAgents] = useState<any[]>([]);
  const [connections, setConnections] = useState<any[]>([]);
  const [historyItems, setHistoryItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAiChat, setSelectedAiChat] = useState<any>(null);
  const [selectedConn, setSelectedConn] = useState<any>(null);

  // Re-fetch every time the menu is opened so newly created sessions show up
  // in Recents without needing a page reload.
  useEffect(() => {
    if (!open) return;
    let cancelled = false;
    const fetchAll = async () => {
      try {
        const [agentRes, connRes, histRes] = await Promise.all([
          searchCatalogItems('agent', false, {
            perPage: 20,
            projection: ['name', 'connection', 'item_type'],
          }),
          searchCatalogItems('connection', false, {
            perPage: 20,
            projection: ['name', 'content'],
          }),
          searchCatalogItems('chat_history', false, {
            perPage: 30,
            projection: [
              'name',
              'chat_laui',
              'connection_laui',
              'ai_provider',
              'messages',
              'updated_at',
            ],
            filters: { created_item_type: 'generate' },
          }),
        ]);
        if (cancelled) return;
        const agentItems = (agentRes?.items || []).map((i: any) => i.item || i);
        setAgents(agentItems);
        setConnections((connRes?.items || []).map((i: any) => i.item || i));
        const rawHistory = (histRes?.items || []).map((i: any) => i.item || i);
        rawHistory.sort(
          (a: any, b: any) =>
            (b.updated_at ? new Date(b.updated_at).getTime() : 0) -
            (a.updated_at ? new Date(a.updated_at).getTime() : 0),
        );
        setHistoryItems(
          rawHistory.map((item: any) => {
            const msgs = Array.isArray(item.messages) ? item.messages : [];
            const userMsgs = msgs.filter((m: any) => m.role === 'user');
            const latestPrompt =
              userMsgs.length > 0 ? userMsgs[userMsgs.length - 1].content || '' : '';
            return { ...item, latestPrompt };
          }),
        );
      } catch (err) {
        console.error('Failed to fetch chat menu data:', err);
      } finally {
        if (!cancelled) setLoading(false);
      }
    };
    void fetchAll();
    return () => {
      cancelled = true;
    };
  }, [open]);

  // Auto-start a chat as soon as both an agent and a connection are picked
  // (no explicit "Start Chat" button). Clear the selections afterwards so the
  // pickers reset and don't re-fire when the menu is reopened.
  useEffect(() => {
    if (!selectedAiChat || !selectedConn) return;
    onSelectConfig(buildProviderConfigFromSelection(selectedAiChat, selectedConn));
    setSelectedAiChat(null);
    setSelectedConn(null);
    onClose();
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedAiChat, selectedConn]);

  if (!open) return null;

  const recents = historyItems.slice(0, HISTORY_PAGE_SIZE);

  const labelSx = {
    fontSize: '0.7rem',
    fontWeight: FONT_WEIGHTS.WEIGHT_500,
    color: 'var(--text-secondary)',
    mb: 0.75,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.05em',
  };

  return (
    <>
      {/* Backdrop */}
      <Box
        onClick={onClose}
        sx={{
          position: 'absolute',
          inset: 0,
          bgcolor: 'rgba(0,0,0,0.35)',
          zIndex: 5,
        }}
      />
      {/* Drawer */}
      <Box
        sx={{
          position: 'absolute',
          top: 0,
          left: 0,
          bottom: 0,
          width: '78%',
          maxWidth: 320,
          zIndex: 6,
          bgcolor: 'var(--bg-primary)',
          borderRight: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          overflow: 'auto',
          boxShadow: '4px 0 16px rgba(0,0,0,0.25)',
        }}
      >
        {/* New session */}
        <Box sx={{ p: 1.5 }}>
          <Button
            fullWidth
            variant="contained"
            startIcon={<AddIcon />}
            onClick={() => {
              onNewSession();
              onClose();
            }}
            sx={{
              bgcolor: '#8b5cf6',
              color: '#fff',
              fontSize: FONT_SIZES.XS,
              fontWeight: FONT_WEIGHTS.WEIGHT_500,
              py: 1,
              borderRadius: BORDER_RADIUS.MD,
              textTransform: 'none',
              justifyContent: 'flex-start',
              '&:hover': { bgcolor: '#7c3aed' },
            }}
          >
            New session
          </Button>
        </Box>

        {/* Agent / Connection pickers (only when no default config). No labels
            and no start button — the chat starts as soon as both are chosen. */}
        {showAgentSelector && (
          <>
            <Divider sx={{ borderColor: 'var(--border)' }} />
            <Box sx={{ p: 1.5, display: 'flex', flexDirection: 'column', gap: 1.25 }}>
              <Autocomplete
                options={agents}
                getOptionLabel={(opt: any) => opt.name || 'Unnamed'}
                value={selectedAiChat}
                onChange={(_, val) => setSelectedAiChat(val)}
                isOptionEqualToValue={(opt: any, val: any) =>
                  (opt._laui || opt.laui) === (val._laui || val.laui)
                }
                noOptionsText="No AI agents available"
                sx={autocompleteSx}
                slotProps={{ paper: { sx: listboxSx } }}
                renderOption={(props, opt: any) => (
                  <li {...props} key={opt._laui || opt.laui}>
                    <SmartToyIcon sx={{ color: '#8b5cf6', fontSize: 16 }} />
                    {opt.name || 'Unnamed'}
                  </li>
                )}
                renderInput={(params) => (
                  <TextField {...params} placeholder="AI Agent..." size="small" />
                )}
              />
              <Autocomplete
                options={connections}
                getOptionLabel={(opt: any) => opt.name || 'Unnamed'}
                value={selectedConn}
                onChange={(_, val) => setSelectedConn(val)}
                isOptionEqualToValue={(opt: any, val: any) =>
                  (opt._laui || opt.laui) === (val._laui || val.laui)
                }
                noOptionsText="No connections available"
                sx={autocompleteSx}
                slotProps={{ paper: { sx: listboxSx } }}
                renderOption={(props, opt: any) => (
                  <li {...props} key={opt._laui || opt.laui}>
                    <CloudIcon sx={{ color: '#06b6d4', fontSize: 16 }} />
                    {opt.name || 'Unnamed'}
                  </li>
                )}
                renderInput={(params) => (
                  <TextField {...params} placeholder="AI Connection..." size="small" />
                )}
              />
            </Box>
          </>
        )}

        <Divider sx={{ borderColor: 'var(--border)' }} />

        {/* Recents */}
        <Box sx={{ px: 1.5, pt: 1.5, pb: 0.5 }}>
          <Typography sx={labelSx}>Recents</Typography>
        </Box>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', py: 3 }}>
            <CircularProgress size={20} sx={{ color: 'var(--accent)' }} />
          </Box>
        ) : recents.length === 0 ? (
          <Typography
            sx={{ px: 1.5, pb: 2, fontSize: FONT_SIZES.XS, color: 'var(--text-secondary)' }}
          >
            No recent sessions
          </Typography>
        ) : (
          <Box sx={{ pb: 1.5 }}>
            {recents.map((item) => (
              <Box
                key={item._laui || item.laui}
                onClick={() => {
                  onSelectConfig(buildProviderConfigFromHistory(item, agents));
                  onClose();
                }}
                sx={{
                  display: 'flex',
                  alignItems: 'flex-start',
                  gap: 1,
                  px: 1.5,
                  py: 1,
                  cursor: 'pointer',
                  '&:hover': { bgcolor: 'var(--bg-secondary)' },
                }}
              >
                <HistoryIcon
                  sx={{ color: 'var(--text-secondary)', fontSize: 16, mt: '2px', flexShrink: 0 }}
                />
                <Box sx={{ minWidth: 0, flex: 1 }}>
                  <Typography
                    sx={{
                      fontSize: FONT_SIZES.XS,
                      color: 'var(--text-primary)',
                      fontWeight: 500,
                      lineHeight: 1.3,
                    }}
                  >
                    {formatSessionLabel(item.name || '')}
                  </Typography>
                  {item.latestPrompt && (
                    <Typography
                      sx={{
                        fontSize: '10px',
                        color: 'var(--text-secondary)',
                        lineHeight: 1.3,
                        overflow: 'hidden',
                        textOverflow: 'ellipsis',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {item.latestPrompt}
                    </Typography>
                  )}
                </Box>
              </Box>
            ))}
          </Box>
        )}
      </Box>
    </>
  );
}
