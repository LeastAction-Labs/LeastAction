/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import CloudIcon from '@mui/icons-material/Cloud';
import HistoryIcon from '@mui/icons-material/History';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import SmartToyIcon from '@mui/icons-material/SmartToy';
import { Autocomplete, Box, Button, CircularProgress, TextField, Typography } from '@mui/material';

import { BORDER_RADIUS, FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import { searchCatalogItems } from '@/services';
import { formatDateTimeInline } from '@/utils/timeFormat';

export interface ProviderConfig {
  aiChatLaui: string;
  aiProvider: string;
  aiChatName: string;
  connectionLaui: string;
  initialMessages?: { role: 'user' | 'assistant'; content: string; timestamp: string }[];
}

interface ProviderListProps {
  onSelect: (config: ProviderConfig) => void;
  prefill?: { chatName: string; connectionName: string } | null;
}

export const autocompleteSx = {
  '& .MuiOutlinedInput-root': {
    fontSize: FONT_SIZES.XS,
    color: 'var(--text-primary)',
    bgcolor: 'var(--bg-primary)',
    border: '1px solid var(--border)',
    borderRadius: BORDER_RADIUS.MD,
    py: '0px !important',
    px: '8px !important',
    '& fieldset': { border: 'none' },
    '&:hover': { borderColor: 'var(--accent)' },
    '&.Mui-focused': { borderColor: 'var(--accent)' },
  },
  '& .MuiAutocomplete-input': {
    py: '10px !important',
    fontSize: FONT_SIZES.XS,
    color: 'var(--text-primary)',
    '&::placeholder': { color: 'var(--text-secondary)', opacity: 1 },
  },
  '& .MuiAutocomplete-popupIndicator': { color: 'var(--text-secondary)' },
  '& .MuiAutocomplete-clearIndicator': { color: 'var(--text-secondary)' },
};

export const listboxSx = {
  bgcolor: 'var(--bg-primary)',
  border: '1px solid var(--border)',
  borderRadius: BORDER_RADIUS.MD,
  mt: 0.5,
  maxHeight: 200,
  p: 0,
  '& .MuiAutocomplete-option': {
    fontSize: FONT_SIZES.XS,
    color: 'var(--text-primary)',
    py: '8px !important',
    px: '12px !important',
    gap: 1,
    '&:hover': { bgcolor: 'var(--bg-tertiary) !important' },
    '&[aria-selected="true"]': {
      bgcolor: 'rgba(139, 92, 246, 0.1) !important',
      '&:hover': { bgcolor: 'rgba(139, 92, 246, 0.15) !important' },
    },
  },
};

export function formatSessionLabel(name: string) {
  const match = name.match(/chat_session_(\d{4}-\d{2}-\d{2})T(\d{2})-(\d{2})-(\d{2})/);
  if (match) {
    const [, date, h, m] = match;
    return formatDateTimeInline(`${date}T${h}:${m}:00`);
  }
  return name;
}

const parseMessages = (raw: any) =>
  raw ? (typeof raw === 'string' ? JSON.parse(raw) : raw) : undefined;

// Build a ProviderConfig from a selected agent + connection (+ optional history
// to resume). Mirrors how a chat session is bootstrapped from the dropdowns.
export function buildProviderConfigFromSelection(
  selectedAiChat: any,
  selectedConn: any,
  selectedHistory?: any,
): ProviderConfig {
  const aiChatConnection = selectedAiChat.connection
    ? typeof selectedAiChat.connection === 'string'
      ? JSON.parse(selectedAiChat.connection)
      : selectedAiChat.connection
    : (() => {
        const c =
          typeof selectedAiChat.content === 'string'
            ? JSON.parse(selectedAiChat.content || '{}')
            : selectedAiChat.content || {};
        return c.connection || {};
      })();

  const connContent =
    typeof selectedConn.content === 'string'
      ? JSON.parse(selectedConn.content || '{}')
      : selectedConn.content || {};

  const merged = { ...aiChatConnection, ...connContent };
  const messages = parseMessages(selectedHistory?.messages);

  return {
    aiChatLaui: selectedAiChat._laui || selectedAiChat.laui,
    aiChatName: selectedAiChat.name || 'Unnamed AI Chat',
    aiProvider:
      merged.provider ||
      (selectedAiChat.item_type?.startsWith('chat.')
        ? selectedAiChat.item_type.replace('chat.', '')
        : 'anthropic'),
    connectionLaui: selectedConn._laui || selectedConn.laui,
    ...(messages?.length ? { initialMessages: messages } : {}),
  };
}

// Build a ProviderConfig directly from a saved chat_history item, resolving the
// agent name from the agents list when available.
export function buildProviderConfigFromHistory(histItem: any, agents: any[]): ProviderConfig {
  const matchedChat = agents.find((p) => (p._laui || p.laui) === histItem.chat_laui);
  const messages = parseMessages(histItem.messages);
  return {
    aiChatLaui: histItem.chat_laui,
    aiChatName: matchedChat?.name || 'AI Agent',
    aiProvider: histItem.ai_provider || 'anthropic',
    connectionLaui: histItem.connection_laui,
    ...(messages?.length ? { initialMessages: messages } : {}),
  };
}

export default function ProviderList({ onSelect, prefill }: ProviderListProps) {
  const [providers, setProviders] = useState<any[]>([]);
  const [connections, setConnections] = useState<any[]>([]);
  const [historyItems, setHistoryItems] = useState<any[]>([]);
  const [loading, setLoading] = useState(true);
  const [selectedAiChat, setSelectedAiChat] = useState<any>(null);
  const [selectedConn, setSelectedConn] = useState<any>(null);
  const [selectedHistory, setSelectedHistory] = useState<any>(null);

  useEffect(() => {
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
        setProviders((agentRes?.items || []).map((i: any) => i.item || i));
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
        if (prefill) {
          const matchedChat = (agentRes?.items || [])
            .map((i: any) => i.item || i)
            .find((p: any) => p.name === prefill.chatName);
          const matchedConn = (connRes?.items || [])
            .map((i: any) => i.item || i)
            .find((c: any) => c.name === prefill.connectionName);
          if (matchedChat) setSelectedAiChat(matchedChat);
          if (matchedConn) setSelectedConn(matchedConn);
        }
      } catch (err) {
        console.error('Failed to fetch data:', err);
      } finally {
        setLoading(false);
      }
    };
    void fetchAll();
  }, []);

  const handleHistorySelect = (histItem: any) => {
    setSelectedHistory(histItem);
    if (!histItem) return;
    const matchedChat = providers.find((p) => (p._laui || p.laui) === histItem.chat_laui);
    const matchedConn = connections.find((c) => (c._laui || c.laui) === histItem.connection_laui);
    if (matchedChat) setSelectedAiChat(matchedChat);
    if (matchedConn) setSelectedConn(matchedConn);
  };

  const handleStart = () => {
    if (!selectedAiChat || !selectedConn) return;
    onSelect(buildProviderConfigFromSelection(selectedAiChat, selectedConn, selectedHistory));
  };

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1 }}>
        <CircularProgress size={28} sx={{ color: 'var(--accent)' }} />
      </Box>
    );
  }

  const canStart = !!selectedAiChat && !!selectedConn;

  const labelSx = {
    fontSize: '0.7rem',
    fontWeight: FONT_WEIGHTS.WEIGHT_500,
    color: 'var(--text-secondary)',
    mb: 0.75,
    textTransform: 'uppercase' as const,
    letterSpacing: '0.05em',
  };

  return (
    <Box
      sx={{
        flex: 1,
        display: 'flex',
        flexDirection: 'column',
        justifyContent: 'center',
        px: 2.5,
        py: 3,
        gap: 2.5,
        overflow: 'auto',
      }}
    >
      {/* AI Chat Autocomplete */}
      <Box>
        <Typography sx={labelSx}>AI Agent</Typography>
        <Autocomplete
          options={providers}
          getOptionLabel={(opt: any) => opt.name || 'Unnamed'}
          value={selectedAiChat}
          onChange={(_, val) => {
            setSelectedAiChat(val);
            setSelectedHistory(null);
          }}
          isOptionEqualToValue={(opt: any, val: any) =>
            (opt._laui || opt.laui) === (val._laui || val.laui)
          }
          noOptionsText="No AI chats available"
          sx={autocompleteSx}
          slotProps={{ paper: { sx: listboxSx } }}
          renderOption={(props, opt: any) => (
            <li {...props} key={opt._laui || opt.laui}>
              <SmartToyIcon sx={{ color: '#8b5cf6', fontSize: 16 }} />
              {opt.name || 'Unnamed'}
            </li>
          )}
          renderInput={(params) => (
            <TextField {...params} placeholder="Search AI Agents..." size="small" />
          )}
        />
      </Box>

      {/* Connection Autocomplete */}
      <Box>
        <Typography sx={labelSx}>Connection</Typography>
        <Autocomplete
          options={connections}
          getOptionLabel={(opt: any) => opt.name || 'Unnamed'}
          value={selectedConn}
          onChange={(_, val) => {
            setSelectedConn(val);
            setSelectedHistory(null);
          }}
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
            <TextField {...params} placeholder="Search connections..." size="small" />
          )}
        />
      </Box>

      {/* OR divider */}
      {historyItems.length > 0 && (
        <>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
            <Box sx={{ flex: 1, height: '1px', bgcolor: 'var(--border)' }} />
            <Typography
              sx={{
                fontSize: '0.65rem',
                color: 'var(--text-secondary)',
                textTransform: 'uppercase',
                letterSpacing: '0.08em',
              }}
            >
              or
            </Typography>
            <Box sx={{ flex: 1, height: '1px', bgcolor: 'var(--border)' }} />
          </Box>

          {/* History Autocomplete */}
          <Box>
            <Typography sx={labelSx}>Recents</Typography>
            <Autocomplete
              options={historyItems}
              getOptionLabel={(opt: any) =>
                opt.latestPrompt
                  ? `${formatSessionLabel(opt.name || '')} — ${opt.latestPrompt}`
                  : formatSessionLabel(opt.name || '')
              }
              value={selectedHistory}
              onChange={(_, val) => handleHistorySelect(val)}
              isOptionEqualToValue={(opt: any, val: any) =>
                (opt._laui || opt.laui) === (val._laui || val.laui)
              }
              noOptionsText="No history available"
              sx={autocompleteSx}
              slotProps={{ paper: { sx: listboxSx } }}
              renderOption={(props, opt: any) => (
                <li {...props} key={opt._laui || opt.laui} style={{ alignItems: 'flex-start' }}>
                  <HistoryIcon
                    sx={{
                      color: 'var(--text-secondary)',
                      fontSize: 16,
                      mt: '2px',
                      flexShrink: 0,
                    }}
                  />
                  <Box
                    sx={{
                      display: 'flex',
                      flexDirection: 'column',
                      minWidth: 0,
                      flex: 1,
                    }}
                  >
                    <Typography
                      sx={{
                        fontSize: FONT_SIZES.XS,
                        color: 'var(--text-primary)',
                        lineHeight: 1.3,
                        fontWeight: 500,
                      }}
                    >
                      {formatSessionLabel(opt.name || '')}
                    </Typography>
                    {opt.latestPrompt && (
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
                        {opt.latestPrompt}
                      </Typography>
                    )}
                    {opt.ai_provider && (
                      <Typography
                        sx={{
                          fontSize: '10px',
                          color: 'var(--text-secondary)',
                          lineHeight: 1.2,
                          opacity: 0.7,
                        }}
                      >
                        {opt.ai_provider}
                      </Typography>
                    )}
                  </Box>
                </li>
              )}
              renderInput={(params) => (
                <TextField {...params} placeholder="Resume a past conversation..." size="small" />
              )}
            />
          </Box>
        </>
      )}

      {/* Start Button */}
      <Button
        fullWidth
        variant="contained"
        disabled={!canStart}
        onClick={handleStart}
        startIcon={selectedHistory ? <HistoryIcon /> : <PlayArrowIcon />}
        sx={{
          mt: 1,
          bgcolor: '#8b5cf6',
          color: '#fff',
          fontSize: FONT_SIZES.XS,
          fontWeight: FONT_WEIGHTS.WEIGHT_500,
          py: 1.25,
          borderRadius: BORDER_RADIUS.MD,
          textTransform: 'none',
          '&:hover': { bgcolor: '#7c3aed' },
          '&.Mui-disabled': {
            bgcolor: 'var(--bg-tertiary)',
            color: 'var(--text-secondary)',
          },
        }}
      >
        {selectedHistory ? 'Resume Chat' : 'Start Chat'}
      </Button>
    </Box>
  );
}
