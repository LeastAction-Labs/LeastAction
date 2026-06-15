/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import { useNavigate } from '@tanstack/react-router';

import {
  AutoAwesome as AutoAwesomeIcon,
  Code as CodeIcon,
  EditNote as EditNoteIcon,
  RocketLaunch as RocketLaunchIcon,
  Settings as SettingsIcon,
  SmartToy as SmartToyIcon,
} from '@mui/icons-material';
import DeleteOutlineIcon from '@mui/icons-material/DeleteOutline';
import HistoryIcon from '@mui/icons-material/History';
import {
  Box,
  Button,
  Card,
  CardContent,
  CircularProgress,
  Divider,
  IconButton,
  Typography,
} from '@mui/material';

import { QuickSearch } from '@/components/ui';
import { BORDER_RADIUS, FONT_SIZES, FONT_WEIGHTS, OPACITY, TRANSITIONS } from '@/constants';
import type { AIHistorySession } from '@/contexts/AIContext';
import { AIItemType, AIMode, useAI } from '@/contexts/AIContext';
import { deleteCatalogItem, searchCatalogItems } from '@/services';

type BaseItemCategory = 'action' | 'operator' | 'payload' | 'agent' | 'generate';

const ITEM_TYPES: {
  value: BaseItemCategory;
  label: string;
  description: string;
  icon: typeof RocketLaunchIcon;
}[] = [
  {
    value: 'action',
    label: 'Action',
    description: 'Create an action using AI Chat',
    icon: RocketLaunchIcon,
  },
  {
    value: 'operator',
    label: 'Operator',
    description: 'Create an operator using AI Chat',
    icon: SettingsIcon,
  },
  {
    value: 'payload',
    label: 'Payload',
    description: 'Create a payload for a specific operator using AI Chat',
    icon: CodeIcon,
  },
  {
    value: 'agent',
    label: 'AI Chat',
    description:
      'Create a AI Chat code for creating operators, actions or payloads (i.e for this page)',
    icon: SmartToyIcon,
  },
  {
    value: 'generate',
    label: 'AI Agent',
    description: 'Create a conversational AI agent with MCP tool-calling support',
    icon: SmartToyIcon,
  },
];

const CREATION_METHODS = [
  {
    id: 'ai',
    title: 'Create with AI',
    description: 'Describe your needs in natural language and let AI generate the item for you.',
    icon: AutoAwesomeIcon,
    mode: AIMode.AICONFIG,
  },
  {
    id: 'manual',
    title: 'Create Manually',
    description: 'Fill out a form with specific fields and parameters for full control.',
    icon: EditNoteIcon,
    mode: AIMode.MANUALITEM,
  },
];

const styles = {
  container: {
    width: '100%',
    maxWidth: 800,
    margin: '0 auto',
    p: 2,
    display: 'flex',
    flexDirection: 'column',
    // minHeight: "100vh",
    justifyContent: 'center',
    alignItems: 'center',
    backgroundColor: 'var(--bg-primary)',
  },
  contentWrapper: {
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
  },
  title: {
    color: 'var(--text-primary)',
    fontWeight: FONT_WEIGHTS.BOLD,
    fontSize: FONT_SIZES.MD,
    mb: 0.5,
    textAlign: 'center',
    width: '100%',
  },
  sectionTitle: {
    color: 'var(--text-secondary)',
    fontSize: FONT_SIZES.SM,
    fontWeight: FONT_WEIGHTS.WEIGHT_500,
    mb: 1,
    textAlign: 'left',
    width: '100%',
  },
  itemTypesContainer: {
    display: 'flex',
    gap: 2,
    flexWrap: { xs: 'wrap', sm: 'nowrap' },
    width: '100%',
    justifyContent: 'center',
  },
  itemTypeCard: (isSelected: boolean) => ({
    flex: 1,
    minWidth: { xs: 'calc(33.333% - 16px)', sm: 'auto' },
    maxWidth: { xs: '100%', sm: '240px' },
    cursor: 'pointer',
    border: '1.5px solid',
    borderColor: isSelected ? 'var(--accent)' : 'var(--border)',
    backgroundColor: isSelected ? 'var(--bg-selected)' : 'var(--bg-secondary)',
    borderRadius: BORDER_RADIUS.MD,
    p: 2,
    textAlign: 'center',
    transition: TRANSITIONS.EASE,
    boxShadow: isSelected ? `0 0 0 3px rgba(var(--color-accent), 0.1)` : 'none',
    '&:hover': {
      borderColor: 'var(--accent)',
      backgroundColor: isSelected ? 'var(--bg-selected)' : 'var(--bg-tertiary)',
    },
  }),
  itemTypeIcon: (isSelected: boolean) => ({
    fontSize: FONT_SIZES.ICON_LG,
    color: isSelected ? 'var(--accent)' : 'var(--text-secondary)',
    mb: 1,
  }),
  itemTypeLabel: (isSelected: boolean) => ({
    color: isSelected ? 'var(--accent)' : 'var(--text-primary)',
    fontSize: FONT_SIZES.SM,
    fontWeight: isSelected ? FONT_WEIGHTS.WEIGHT_600 : FONT_WEIGHTS.WEIGHT_500,
  }),
  creationMethodsContainer: {
    display: 'flex',
    gap: 3,
    flexDirection: { xs: 'column', md: 'row' },
    width: '100%',
    justifyContent: 'center',
  },
  creationMethodCard: (isSelected: boolean) => ({
    flex: 1,
    maxWidth: { xs: '100%', md: '380px' },
    cursor: 'pointer',
    border: '1.5px solid',
    borderColor: isSelected ? 'var(--accent)' : 'var(--border)',
    backgroundColor: isSelected ? 'var(--bg-selected)' : 'var(--bg-secondary)',
    borderRadius: BORDER_RADIUS.LG,
    p: 3,
    transition: TRANSITIONS.EASE,
    boxShadow: isSelected ? `0 0 0 3px rgba(var(--color-accent), 0.1)` : 'none',
    '&:hover': {
      borderColor: 'var(--accent)',
      backgroundColor: isSelected ? 'var(--bg-selected)' : 'var(--bg-tertiary)',
    },
  }),
  methodCardContent: {
    p: 0,
    '&:last-child': { pb: 0 },
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
  },
  methodHeader: {
    display: 'flex',
    alignItems: 'flex-start',
    mb: 2,
  },
  methodIcon: (isSelected: boolean) => ({
    fontSize: FONT_SIZES.ICON_LG,
    color: isSelected ? 'var(--accent)' : 'var(--text-secondary)',
    mr: 1.5,
    mt: 0.25,
  }),
  methodTitle: (isSelected: boolean) => ({
    color: isSelected ? 'var(--accent)' : 'var(--text-primary)',
    fontSize: FONT_SIZES.BASE,
    fontWeight: isSelected ? FONT_WEIGHTS.WEIGHT_600 : FONT_WEIGHTS.WEIGHT_500,
    flex: 1,
  }),
  methodDescription: {
    color: 'var(--text-secondary)',
    fontSize: FONT_SIZES.XS,
    lineHeight: 1.5,
    flex: 1,
  },
  actionsContainer: {
    pt: 1,
    mt: 1,
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    width: '100%',
  },
  cancelButton: {
    borderColor: 'var(--border)',
    color: 'var(--text-secondary)',
    fontSize: FONT_SIZES.SM,
    fontWeight: FONT_WEIGHTS.WEIGHT_500,
    px: 4,
    py: 0.75,
    borderRadius: BORDER_RADIUS.MD,
    textTransform: 'none',
    minWidth: 100,
    '&:hover': {
      borderColor: 'var(--accent)',
      backgroundColor: `rgba(var(--color-accent), 0.05)`,
    },
  },
  continueButton: {
    backgroundColor: 'var(--accent)',
    color: 'var(--text-primary)',
    fontSize: FONT_SIZES.SM,
    fontWeight: FONT_WEIGHTS.WEIGHT_500,
    px: 5,
    py: 0.75,
    borderRadius: BORDER_RADIUS.MD,
    textTransform: 'none',
    minWidth: 100,
    ml: 'auto',
    '&:hover': {
      backgroundColor: 'var(--accent)',
      opacity: OPACITY.HIGH,
    },
    '&.Mui-disabled': {
      backgroundColor: 'var(--bg-tertiary)',
      color: 'var(--text-secondary)',
    },
  },
  historySection: {
    width: '100%',
    mt: 2,
  },
  historyItem: (isSelected: boolean) => ({
    p: 1.5,
    cursor: 'pointer',
    border: '1px solid',
    borderColor: isSelected ? 'var(--accent)' : 'var(--border)',
    backgroundColor: isSelected ? 'var(--bg-selected)' : 'var(--bg-secondary)',
    borderRadius: BORDER_RADIUS.MD,
    transition: TRANSITIONS.EASE,
    '&:hover': {
      borderColor: 'var(--accent)',
      backgroundColor: isSelected ? 'var(--bg-selected)' : 'var(--bg-tertiary)',
    },
  }),
  historyName: {
    fontSize: FONT_SIZES.SM,
    fontWeight: FONT_WEIGHTS.WEIGHT_500,
    color: 'var(--text-primary)',
  },
  historyMeta: {
    fontSize: FONT_SIZES.XS,
    color: 'var(--text-secondary)',
  },
  historyLoading: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    p: 2,
  },
};

export default function ItemType() {
  const [selectedMethod, setSelectedMethod] = useState<AIMode | null>(null);
  const { itemType, setItemType, setMode, setSessionLaui, setConfig, userFolderLaui } = useAI();
  const navigate = useNavigate();

  const [selectedCategory, setSelectedCategory] = useState<BaseItemCategory>(
    itemType as BaseItemCategory,
  );

  const handleCategorySelect = (category: BaseItemCategory) => {
    setSelectedCategory(category);
    if (category === 'action') {
      setItemType(AIItemType.ACTION);
    } else if (category === 'operator') {
      setItemType(AIItemType.OPERATOR);
    } else if (category === 'payload') {
      setItemType(AIItemType.PAYLOAD);
    } else if (category === 'agent') {
      setItemType(AIItemType.AGENT);
    } else if (category === 'generate') {
      setItemType(AIItemType.GENERATE);
    }
  };

  const [historySessions, setHistorySessions] = useState<AIHistorySession[]>([]);
  const [loadingHistory, setLoadingHistory] = useState(false);

  useEffect(() => {
    const fetchHistory = async () => {
      setLoadingHistory(true);
      try {
        const response = await searchCatalogItems('generate_history', false, {
          filters: { created_item_type: itemType },
          perPage: 20,
          projection: [
            'name',
            'created_item_type',
            'ai_provider',
            'chat_laui',
            'updated_at',
            'messages',
          ],
        });
        const items = response.items || [];
        // Sort by updated_at descending (latest first)
        items.sort((a: any, b: any) => {
          const dateA = a.updated_at ? new Date(a.updated_at).getTime() : 0;
          const dateB = b.updated_at ? new Date(b.updated_at).getTime() : 0;
          return dateB - dateA;
        });
        const sessions: AIHistorySession[] = items.map((item: any) => {
          // Extract latest user prompt from messages
          const userMessages = Array.isArray(item.messages)
            ? item.messages.filter((m: any) => m.role === 'user')
            : [];
          const latestPrompt =
            userMessages.length > 0 ? userMessages[userMessages.length - 1].content || '' : '';
          return {
            laui: item.laui,
            name: item.name,
            created_item_type: item.created_item_type || itemType,
            ai_provider: item.ai_provider,
            chat_laui: item.chat_laui,
            latestPrompt,
          };
        });
        setHistorySessions(sessions);
      } catch {
        setHistorySessions([]);
      } finally {
        setLoadingHistory(false);
      }
    };
    void fetchHistory();
  }, [itemType]);

  const handleContinue = () => {
    setSessionLaui(null);
    setMode(selectedMethod!);
  };

  const handleSessionClick = (session: AIHistorySession) => {
    setSessionLaui(session.laui);
    if (session.chat_laui) {
      setConfig({
        aiChatLaui: session.chat_laui,
        aiChatName: session.chat_name || '',
        aiProvider: session.ai_provider || '',
        includeGuideDoc: false,
        includeInstallGuide: false,
      });
      setMode(AIMode.MANUALEDITOR);
    } else {
      setMode(AIMode.AICONFIG);
    }
    void navigate({ to: '/ai/create', search: { sessionId: session.name } });
  };

  const handleDeleteSession = async (session: AIHistorySession) => {
    try {
      await deleteCatalogItem(session.laui, userFolderLaui || '');
      setHistorySessions((prev) => prev.filter((s) => s.laui !== session.laui));
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  return (
    <Box sx={styles.container}>
      <Box sx={styles.contentWrapper}>
        <Box sx={{ mb: 1, width: '100%' }}>
          <Typography sx={styles.title}>Create New AI Item</Typography>
        </Box>

        <Box sx={{ mb: 2, width: '100%' }}>
          <Typography sx={styles.sectionTitle}>1. Select Item Type</Typography>

          <Box sx={styles.itemTypesContainer}>
            {ITEM_TYPES.map((type) => {
              const Icon = type.icon;
              const isSelected = selectedCategory === type.value;

              return (
                <Card
                  key={type.value}
                  sx={styles.itemTypeCard(isSelected)}
                  onClick={() => handleCategorySelect(type.value)}
                >
                  <Icon sx={styles.itemTypeIcon(isSelected)} />
                  <Typography sx={styles.itemTypeLabel(isSelected)}>{type.label}</Typography>
                  <Typography
                    sx={{
                      fontSize: FONT_SIZES.XS,
                      color: 'var(--text-secondary)',
                      mt: 0.5,
                      lineHeight: 1.3,
                    }}
                  >
                    {type.description}
                  </Typography>
                </Card>
              );
            })}
          </Box>
        </Box>

        <Box sx={{ width: '100%' }}>
          <Typography sx={styles.sectionTitle}>2. How would you like to create it?</Typography>

          <Box sx={styles.creationMethodsContainer}>
            {CREATION_METHODS.map((method) => {
              const Icon = method.icon;
              const isSelected = selectedMethod === method.mode;

              return (
                <Card
                  key={method.id}
                  sx={styles.creationMethodCard(isSelected)}
                  onClick={() => setSelectedMethod(method.mode)}
                >
                  <CardContent sx={styles.methodCardContent}>
                    <Box sx={styles.methodHeader}>
                      <Icon sx={styles.methodIcon(isSelected)} />
                      <Typography sx={styles.methodTitle(isSelected)}>{method.title}</Typography>
                    </Box>

                    <Typography sx={styles.methodDescription}>{method.description}</Typography>
                  </CardContent>
                </Card>
              );
            })}
          </Box>
        </Box>

        <Box sx={styles.actionsContainer}>
          <Button
            variant="outlined"
            onClick={() => {
              void navigate({ to: '/path' });
            }}
            sx={styles.cancelButton}
          >
            Cancel
          </Button>

          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, ml: 'auto' }}>
            <Button
              variant="contained"
              onClick={handleContinue}
              disabled={!selectedMethod}
              sx={styles.continueButton}
            >
              Continue
            </Button>
          </Box>
        </Box>

        <Divider sx={{ width: '100%', my: 2, borderColor: 'var(--border)' }} />

        <Box sx={styles.historySection}>
          <Typography sx={styles.sectionTitle}>
            <HistoryIcon sx={{ fontSize: FONT_SIZES.SM, mr: 0.5, verticalAlign: 'middle' }} />
            Previous AI Sessions ({itemType})
          </Typography>

          <Box sx={{ mb: 1.5 }}>
            <QuickSearch
              label="Search sessions"
              filters={{ item_type: 'generate_history', created_item_type: itemType }}
              onSelect={(item) => {
                const raw = item as Record<string, unknown>;
                const laui = (raw._laui ?? raw.laui ?? raw.id ?? '') as string;
                const name = (raw.name ?? '') as string;
                if (laui) {
                  setSessionLaui(laui);
                  const aiChatLaui = (raw.chat_laui ?? '') as string;
                  if (aiChatLaui) {
                    setConfig({
                      aiChatLaui,
                      aiChatName: (raw.chat_name ?? '') as string,
                      aiProvider: (raw.ai_provider ?? '') as string,
                      includeGuideDoc: false,
                      includeInstallGuide: false,
                    });
                    setMode(AIMode.MANUALEDITOR);
                  } else {
                    setMode(AIMode.AICONFIG);
                  }
                  if (name) void navigate({ to: '/ai/create', search: { sessionId: name } });
                }
              }}
              placeholder="Search previous sessions…"
            />
          </Box>

          {loadingHistory ? (
            <Box sx={styles.historyLoading}>
              <CircularProgress size={20} sx={{ color: 'var(--accent)' }} />
            </Box>
          ) : historySessions.length > 0 ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              {historySessions.map((session) => (
                <Box
                  key={session.laui}
                  sx={styles.historyItem(false)}
                  onClick={() => handleSessionClick(session)}
                >
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'flex-start',
                    }}
                  >
                    <Box sx={{ flex: 1, overflow: 'hidden' }}>
                      <Typography sx={styles.historyName}>{session.name}</Typography>
                      {session.latestPrompt && (
                        <Typography
                          sx={{
                            fontSize: FONT_SIZES.XS,
                            color: 'var(--text-secondary)',
                            mt: 0.5,
                            overflow: 'hidden',
                            textOverflow: 'ellipsis',
                            whiteSpace: 'nowrap',
                          }}
                        >
                          {session.latestPrompt}
                        </Typography>
                      )}
                      {session.ai_provider && (
                        <Typography sx={styles.historyMeta}>
                          Provider: {session.ai_provider}
                        </Typography>
                      )}
                    </Box>
                    <IconButton
                      size="small"
                      onClick={(e) => {
                        e.stopPropagation();
                        void handleDeleteSession(session);
                      }}
                      sx={{
                        color: 'var(--text-secondary)',
                        '&:hover': { color: 'var(--error)' },
                      }}
                    >
                      <DeleteOutlineIcon fontSize="small" />
                    </IconButton>
                  </Box>
                </Box>
              ))}
            </Box>
          ) : (
            <Typography
              sx={{
                fontSize: FONT_SIZES.XS,
                color: 'var(--text-secondary)',
                fontStyle: 'italic',
              }}
            >
              No previous sessions for {itemType}
            </Typography>
          )}
        </Box>
      </Box>
    </Box>
  );
}
