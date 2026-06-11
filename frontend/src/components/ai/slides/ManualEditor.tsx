/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import React, { memo, useCallback, useEffect, useMemo, useRef, useState } from 'react';

import { useNavigate } from '@tanstack/react-router';

import {
  ArrowBack as ArrowBackIcon,
  ClearAll as ClearIcon,
  Delete as DeleteIcon,
  Refresh as RefreshIcon,
  Save as SaveIcon,
  Send as SendIcon,
} from '@mui/icons-material';
import {
  Box,
  Button,
  Checkbox,
  Chip,
  Divider,
  FormControlLabel,
  IconButton,
  Paper,
  Tab,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';

import RunActionModal from '@/components/modals/RunActionModal';
import RunTaskModal from '@/components/modals/RunTaskModal';
import { MonacoWrapper, QuickSearch } from '@/components/ui';
import ValidationPanel from '@/components/validation/ValidationPanel';
import { BORDER_RADIUS, FONT_SIZES, FONT_WEIGHTS, OPACITY } from '@/constants';
import { AIMode, useAI } from '@/contexts/AIContext';
import { RunActionModalMode, useActionContext } from '@/contexts/ActionContext';
import {
  TaskModalMode,
  TaskModalScopeType,
  useTaskModalContext,
} from '@/contexts/TaskModalContext';
import {
  createCatalogItem,
  deleteCatalogItem,
  getCatalogItemById,
  searchCatalogItems,
} from '@/services';
import type { ValidationResult } from '@/services/validation.service';
import { formatTimeOnly } from '@/utils/timeFormat';

import SaveItemModal from '../SaveItemModal';
import type { AIGenerationResponse } from '../types';

const TEXT = {
  BACK_BUTTON: 'Back',
  HOME_BUTTON: 'Home',
  AI_PROVIDER_LABEL: 'AI Provider',
  RUN_TEST: 'Run Test',
  RUN_ACTION: 'Run Action',
  SAVE_RESULTS: 'Save Results',
  CURRENT: 'Current',
  USER_LABEL: 'Operator',
  SYSTEM_LABEL: 'System AI',
  ASSISTANT_LABEL: 'AI Response',
  PROCESSING: 'Processing request...',
  INPUT_PLACEHOLDER: 'Message AI... (Press Enter to send)',
  INCLUDE_GUIDE_DOC: 'Include Guide Doc',
  INCLUDE_INSTALL_GUIDE: 'Include Install Guide',
  REGENERATE: 'Regenerate',
  CLEAR_CONTEXT: 'Clear Context',
  CONNECTED: 'Connected',
  PROVIDER_PREFIX: 'Provider',
  SESSION_INFO: 'AI Chat Test',
  SESSION_ACTIVE: 'Session Active',
  CONFIG_TOOLTIP: 'Configuration',
  API_DOCS_TOOLTIP: 'API Docs',
  HELP_TOOLTIP: 'Help',
  GENERATION_FAILED: 'Failed to generate AI response',
  DELETE_SESSION: 'Delete Session',
  COPY_SUCCESS: 'Code copied to clipboard!',
  NO_CONTENT: 'No content available',
  ACTION_VARIABLES: 'Action Variables',
  SKILLS_LABEL: 'Skill',
} as const;

const styles = {
  container: {
    height: 'calc(100vh - 50px)',
    width: '100%',
    display: 'flex',
    flexDirection: 'column',
    bgcolor: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    fontFamily: 'Inter, -apple-system, BlinkMacSystemFont, sans-serif',
  },
  mainContent: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
  },

  header: {
    p: 1.5,
    borderBottom: '1px solid',
    borderColor: 'var(--border-color)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    bgcolor: 'var(--bg-secondary)',
    minHeight: '55px',
    paddingBottom: 0,
  },
  headerLeft: {
    display: 'flex',
    alignItems: 'center',
    gap: 1.5,
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: 1.5,
  },

  // Navigation styles
  navButtons: {
    display: 'flex',
    alignItems: 'center',
    gap: 0.5,
  },
  homeButton: {
    p: 0.5,
    color: 'var(--text-secondary)',
    '&:hover': {
      color: 'var(--accent)',
      backgroundColor: 'rgba(var(--color-accent), 0.1)',
    },
    '& svg': {
      fontSize: '16px',
    },
  },
  backButton: {
    fontSize: FONT_SIZES.SM,
    fontWeight: FONT_WEIGHTS.WEIGHT_500,
    color: 'var(--text-secondary)',
    textTransform: 'none',
    minWidth: 'auto',
    p: 0.5,
    '& .MuiButton-startIcon': { marginRight: 0.5 },
    '&:hover': {
      color: 'var(--text-primary)',
      backgroundColor: 'rgba(var(--color-accent), 0.1)',
    },
  },

  typeBadge: {
    display: 'flex',
    alignItems: 'center',
    gap: 2,
    px: 1.5,
    py: 0.5,
    width: '225px',
    bgcolor: 'var(--bg-tertiary)',
    borderRadius: BORDER_RADIUS.SM,
    border: '1px solid var(--border-color)',
  },
  typeLabel: {
    fontSize: FONT_SIZES.SM,
    color: 'var(--text-secondary)',
    fontWeight: FONT_WEIGHTS.WEIGHT_500,
  },
  typeValue: {
    fontSize: FONT_SIZES.SM,
    color: 'var(--text-primary)',
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
  },

  tabChipsContainer: {
    display: 'flex',
    gap: 0.5,
    flexWrap: 'wrap',
    ml: 1,
  },
  tabChip: (isActive: boolean, hasContent: boolean) => ({
    height: 22,
    fontSize: FONT_SIZES.XS,
    fontWeight: FONT_WEIGHTS.WEIGHT_500,
    bgcolor: isActive ? 'var(--bg-selected)' : 'var(--bg-tertiary)',
    color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
    border: '1px solid',
    borderColor: isActive ? 'var(--accent)' : 'var(--border-color)',
    cursor: hasContent ? 'pointer' : 'not-allowed',
    opacity: hasContent ? 1 : 0.5,
    '&:hover': {
      bgcolor: hasContent
        ? isActive
          ? 'var(--bg-selected)'
          : 'var(--bg-hover)'
        : 'var(--bg-tertiary)',
    },
  }),

  connectionField: {
    minWidth: 250,
    '& .MuiOutlinedInput-root': {
      fontSize: FONT_SIZES.SM,
      color: 'var(--text-primary)',
      backgroundColor: 'var(--bg-primary)',
      '&:hover .MuiOutlinedInput-notchedOutline': {
        borderColor: 'var(--accent)',
      },
      '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
        borderColor: 'var(--accent)',
      },
      '&.Mui-disabled': {
        backgroundColor: 'var(--bg-tertiary)',
      },
    },
    '& .MuiInputLabel-root': {
      fontSize: FONT_SIZES.SM,
      color: 'var(--text-secondary)',
      '&.Mui-focused': {
        color: 'var(--accent)',
      },
      '&.Mui-disabled': {
        color: 'var(--text-disabled)',
      },
    },
    '& .MuiOutlinedInput-notchedOutline': {
      borderColor: 'var(--border-color)',
    },
  },

  connectionDropdown: {
    minWidth: 250,
    '& .MuiOutlinedInput-root': {
      fontSize: FONT_SIZES.SM,
      color: 'var(--text-primary)',
      backgroundColor: 'var(--bg-primary)',
      '&:hover .MuiOutlinedInput-notchedOutline': {
        borderColor: 'var(--accent)',
      },
      '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
        borderColor: 'var(--accent)',
      },
    },
    '& .MuiInputLabel-root': {
      fontSize: FONT_SIZES.SM,
      color: 'var(--text-secondary)',
      '&.Mui-focused': {
        color: 'var(--accent)',
      },
    },
    '& .MuiSelect-select': {
      padding: '8.5px 14px',
    },
  },

  runTestButton: {
    fontSize: FONT_SIZES.SM,
    fontWeight: FONT_WEIGHTS.WEIGHT_500,
    height: 32,
    minWidth: 80,
    textTransform: 'none',
    bgcolor: 'var(--accent)',
    color: '#fff',
    borderRadius: BORDER_RADIUS.SM,
    '&:hover': {
      bgcolor: 'var(--accent)',
      opacity: OPACITY.HIGH,
    },
    '&.Mui-disabled': {
      bgcolor: 'var(--bg-tertiary)',
      color: 'var(--text-secondary)',
    },
  },
  saveButton: {
    p: 0.5,
    color: 'var(--text-secondary)',
    '&:hover': {
      color: 'var(--text-primary)',
      backgroundColor: 'rgba(255, 255, 255, 0.05)',
    },
    '& svg': {
      fontSize: '16px',
    },
  },

  mainPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    bgcolor: 'var(--bg-primary)',
    overflow: 'hidden',
  },

  chatMessages: {
    flex: 1,
    overflow: 'auto',
    p: 2,
    display: 'flex',
    flexDirection: 'column',
    gap: 1.5,
  },
  messageContainer: {
    alignSelf: 'flex-end',
    maxWidth: '85%',
    minWidth: '200px',
  },
  messageBubble: (role: 'user' | 'assistant' | 'system') => ({
    p: 1.5,
    backgroundColor:
      role === 'user'
        ? 'var(--bg-depth-0)'
        : role === 'system'
          ? 'var(--bg-tertiary)'
          : 'var(--bg-secondary)',
    border: '1px solid',
    borderColor:
      role === 'user'
        ? 'var(--accent)'
        : role === 'system'
          ? 'var(--border-color)'
          : 'rgba(13, 101, 45, 0.3)',
    borderRadius: BORDER_RADIUS.LG,
    fontSize: FONT_SIZES.SM,
  }),
  messageHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    mb: 1,
  },
  messageRole: (role: 'user' | 'assistant' | 'system') => ({
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
    fontSize: FONT_SIZES.XS,
    color:
      role === 'user'
        ? 'var(--accent)'
        : role === 'system'
          ? 'var(--text-primary)'
          : 'rgb(13, 101, 45)',
  }),
  messageTime: {
    fontSize: FONT_SIZES.XS,
    color: 'var(--text-secondary)',
  },
  messageContent: {
    fontSize: FONT_SIZES.SM,
    lineHeight: 1.5,
    color: 'var(--text-primary)',
    whiteSpace: 'pre-wrap',
    wordBreak: 'break-word',
  },
  loadingMessage: {
    alignSelf: 'flex-start',
    maxWidth: '85%',
  },
  loadingBubble: {
    p: 1.5,
    backgroundColor: 'var(--bg-tertiary)',
    borderColor: 'var(--border-color)',
    borderRadius: BORDER_RADIUS.LG,
  },
  loadingText: {
    fontSize: FONT_SIZES.SM,
    display: 'flex',
    alignItems: 'center',
    gap: 1,
    color: 'var(--text-secondary)',
  },

  inputArea: {
    p: 1.5,
    borderTop: '1px solid',
    borderColor: 'var(--border-color)',
    bgcolor: 'var(--bg-secondary)',
    minHeight: 'auto',
  },
  inputContainer: {
    display: 'flex',
    gap: 1,
    alignItems: 'flex-start',
    mb: 1,
  },
  textInput: {
    '& .MuiOutlinedInput-root': {
      fontSize: FONT_SIZES.SM,
      backgroundColor: 'var(--bg-primary)',
      color: 'var(--text-primary)',
      '& textarea': {
        fontSize: FONT_SIZES.SM,
        padding: '8px',
        color: 'var(--text-primary)',
      },
      '& fieldset': {
        borderColor: 'var(--border-color)',
      },
      '&:hover fieldset': {
        borderColor: 'var(--accent)',
      },
      '&.Mui-focused fieldset': {
        borderColor: 'var(--accent)',
      },
    },
  },
  sendButton: {
    minWidth: 'auto',
    height: '40px',
    width: '40px',
    bgcolor: 'var(--accent)',
    color: '#fff',
    borderRadius: BORDER_RADIUS.SM,
    '&:hover': {
      bgcolor: 'var(--accent)',
      opacity: OPACITY.HIGH,
    },
    '&.Mui-disabled': {
      bgcolor: 'var(--bg-tertiary)',
      color: 'var(--text-secondary)',
    },
  },

  optionsArea: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    mt: 1,
  },
  leftOptions: {
    display: 'flex',
    alignItems: 'center',
    gap: 1.5,
  },
  checkboxLabel: {
    fontSize: FONT_SIZES.SM,
    color: 'var(--text-secondary)',
  },
  checkbox: {
    padding: '4px',
    color: 'var(--text-secondary)',
    '&.Mui-checked': {
      color: 'var(--accent)',
    },
    '& .MuiSvgIcon-root': { fontSize: '1rem' },
  },
  actionButton: {
    fontSize: FONT_SIZES.XS,
    fontWeight: FONT_WEIGHTS.WEIGHT_500,
    textTransform: 'none',
    color: 'var(--text-secondary)',
    minWidth: 'auto',
    p: 0.5,
    '&:hover': {
      color: 'var(--text-primary)',
      backgroundColor: 'rgba(var(--color-accent), 0.1)',
    },
    '&.Mui-disabled': {
      color: 'var(--bg-tertiary)',
    },
  },
  clearButton: {
    fontSize: FONT_SIZES.XS,
    fontWeight: FONT_WEIGHTS.WEIGHT_500,
    textTransform: 'none',
    color: '#dc3545',
    minWidth: 'auto',
    p: 0.5,
    '&:hover': {
      backgroundColor: 'rgba(220, 53, 69, 0.1)',
    },
  },
  connectionStatus: {
    fontSize: FONT_SIZES.XS,
    color: 'var(--text-secondary)',
  },

  monacoContainer: {
    height: '100%',
    width: '100%',
    borderColor: 'var(--border)',
    borderRadius: 1,
    position: 'relative',
    minHeight: '200px',
  },
  monacoLoading: {
    position: 'absolute',
    top: '50%',
    left: '50%',
    transform: 'translate(-50%, -50%)',
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: 1,
  },

  arrayFieldContainer: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    width: '100%',
  },
  arrayTabsContainer: {
    border: '1px solid',
    borderColor: 'var(--border)',
    borderRadius: 1,
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    overflow: 'hidden',
    width: '100%',
  },
  arrayTabs: {
    minHeight: '30px',
    '& .MuiTab-root': {
      color: 'var(--text-secondary)',
      textTransform: 'none',
      fontSize: '11px',
      fontWeight: 400,
      minHeight: '30px',
      minWidth: 'auto',
      px: 1,
      py: 0,
      '&.Mui-selected': {
        color: 'var(--accent)',
        fontWeight: 600,
      },
    },
    '& .MuiTabs-indicator': {
      bgcolor: 'var(--accent)',
    },
  },
  emptyContent: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100%',
    minHeight: '200px',
    color: 'var(--text-secondary)',
    flexDirection: 'column',
    gap: 1,
  },
  emptyText: {
    color: 'var(--text-secondary)',
    fontStyle: 'italic',
  },
};

interface Message {
  id: string;
  role: 'user' | 'assistant' | 'system';
  content: string;
  timestamp: Date;
  codeBlocks?: CodeBlock[];
}

interface CodeBlock {
  language: string;
  code: string;
}

interface GeneratedContent {
  codeblock: Record<string, string>;
  bashblock: Record<string, string>;
  connection: Record<string, any>;
  payload: Record<string, any>;
  action_variables?: Record<string, any>;
  guide: Record<string, string>;
  install_guide: Record<string, string>;
  prompt?: string;
}

interface RootData {
  account_laui: string;
  project_laui: string;
  folder_ai_laui: string;
}

type ContentTab =
  | 'chat'
  | 'codeblock'
  | 'bashblock'
  | 'connection'
  | 'payload'
  | 'action_variables'
  | 'install_guide'
  | 'guide';

interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

const TabPanel: React.FC<TabPanelProps> = ({ children, value, index }) => {
  return (
    <div
      role="tabpanel"
      hidden={value !== index}
      style={{
        flex: 1,
        display: value === index ? 'flex' : 'none',
        flexDirection: 'column',
        overflow: 'hidden',
        width: '100%',
        height: '100%',
      }}
    >
      {value === index && children}
    </div>
  );
};

const MessageBubble: React.FC<{ message: Message; itemType?: string }> = memo(
  ({ message, itemType }) => {
    const formatTime = useCallback((date: Date) => {
      return formatTimeOnly(date);
    }, []);

    const getRoleLabel = useCallback(
      (role: Message['role']) => {
        switch (role) {
          case 'user':
            return itemType
              ? itemType.charAt(0).toUpperCase() + itemType.slice(1)
              : TEXT.USER_LABEL;
          case 'system':
            return TEXT.SYSTEM_LABEL;
          case 'assistant':
            return TEXT.ASSISTANT_LABEL;
          default:
            return 'Unknown';
        }
      },
      [itemType],
    );

    return (
      <Box
        sx={
          message.role === 'user'
            ? styles.messageContainer
            : { ...styles.messageContainer, alignSelf: 'flex-start' }
        }
      >
        <Paper sx={styles.messageBubble(message.role)}>
          <Box sx={styles.messageHeader}>
            <Typography variant="caption" sx={styles.messageRole(message.role)}>
              {getRoleLabel(message.role)}
            </Typography>
            <Typography variant="caption" sx={styles.messageTime}>
              {formatTime(message.timestamp)}
            </Typography>
          </Box>

          <Typography variant="body2" sx={styles.messageContent}>
            {message.content}
          </Typography>
        </Paper>
      </Box>
    );
  },
);

MessageBubble.displayName = 'MessageBubble';

const ContentTabChip: React.FC<{
  label: string;
  tabType: ContentTab;
  activeTab: ContentTab;
  count: number;
  onClick: () => void;
}> = memo(({ label, tabType, activeTab, count, onClick }) => (
  <Chip
    label={`${label} ${count > 0 ? `(${count})` : ''}`}
    size="small"
    onClick={onClick}
    disabled={count === 0 && tabType !== 'chat'}
    sx={styles.tabChip(activeTab === tabType, count > 0 || tabType === 'chat')}
  />
));

ContentTabChip.displayName = 'ContentTabChip';

interface ManualEditorProps {
  onGenerate: (
    prompt: string,
    includeGuideDoc: boolean,
    includeInstallGuide: boolean,
    messages?: { role: string; content: string }[],
    generatedContent?: Record<string, any>,
    skillContent?: string,
  ) => Promise<AIGenerationResponse | undefined>;
}

const ManualEditor = ({ onGenerate }: ManualEditorProps) => {
  const {
    itemType,
    config,
    setSaveItemModalState,
    sessionLaui,
    setSessionLaui,
    userFolderLaui,
    setUserFolderLaui,
    setMode,
  } = useAI();
  const navigate = useNavigate();
  const { aiProvider, aiChatLaui, aiChatName, connectionLaui } = config!;

  const [messages, setMessages] = useState<Message[]>([]);
  const [inputMessage, setInputMessage] = useState('');
  const [isLoading, setIsLoading] = useState(false);
  const [includeGuideDoc, setIncludeGuideDoc] = useState(false);
  const [includeInstallGuide, setIncludeInstallGuide] = useState(false);
  const [activeContentTab, setActiveContentTab] = useState<ContentTab>('chat');
  const [generatedContent, setGeneratedContent] = useState<GeneratedContent>({
    codeblock: {},
    bashblock: {},
    connection: {},
    payload: {},
    guide: {},
    install_guide: {},
    action_variables: {},
    prompt: '',
  });
  const [aiValidationResult, setAiValidationResult] = useState<ValidationResult | null>(null);
  const [runTestLoading, _setRunTestLoading] = useState<boolean>(false);
  const [_rootData, _setRootData] = useState<RootData | null>(null);
  const [selectedSkills, setSelectedSkills] = useState<
    Array<{ laui: string; name: string; content: string }>
  >([]);

  const [selectedTabIndex, setSelectedTabIndex] = useState<number>(0);
  const messagesEndRef = useRef<HTMLDivElement>(null);
  const inputRef = useRef<HTMLInputElement>(null);
  const sessionLauiRef = useRef<string | null>(sessionLaui);
  const sessionNameRef = useRef<string | null>(null);

  const showActionVariables = useMemo(() => {
    return itemType !== 'operator' && itemType !== 'payload';
  }, [itemType]);

  const hasGeneratedContent = useMemo(() => {
    return Object.values(generatedContent).some(
      (content) => content && Object.keys(content).length > 0,
    );
  }, [generatedContent]);

  const currentContent = useMemo(() => {
    const contentMap: Record<ContentTab, any> = {
      chat: {},
      codeblock: generatedContent.codeblock,
      bashblock: generatedContent.bashblock,
      connection: generatedContent.connection,
      payload: showActionVariables ? generatedContent.action_variables : generatedContent.payload,
      action_variables: generatedContent.action_variables,
      guide: generatedContent.guide,
      install_guide: generatedContent.install_guide,
    };
    return contentMap[activeContentTab] || {};
  }, [activeContentTab, generatedContent, showActionVariables]);

  const contentCounts = useMemo(
    () => ({
      chat: messages.length,
      codeblock: Object.keys(generatedContent.codeblock).length,
      bashblock: Object.keys(generatedContent.bashblock).length,
      connection: Object.keys(generatedContent.connection).length,
      payload: showActionVariables
        ? Object.keys(generatedContent.action_variables || {}).length
        : Object.keys(generatedContent.payload).length,
      action_variables: Object.keys(generatedContent.action_variables || {}).length,
      guide: Object.keys(generatedContent.guide).length,
      install_guide: Object.keys(generatedContent.install_guide).length,
    }),
    [messages.length, generatedContent, showActionVariables],
  );

  const contentItems = useMemo(() => {
    if (activeContentTab === 'chat') {
      return [];
    }

    const content = currentContent;
    if (!content || Object.keys(content).length === 0) {
      return [];
    }

    const items: Array<{ fileName: string; content: string }> = [];

    if (
      activeContentTab === 'connection' ||
      activeContentTab === 'action_variables' ||
      activeContentTab === 'payload'
    ) {
      // Handle connection, action_variables, and payload as single JSON objects
      items.push({
        fileName: `${activeContentTab}.json`,
        content: typeof content === 'string' ? content : JSON.stringify(content, null, 2),
      });
    } else if (typeof content === 'object') {
      // Handle object with multiple files
      Object.entries(content).forEach(([key, value]) => {
        if (value !== undefined && value !== null) {
          const fileName =
            key.endsWith('.json') || key.includes('.')
              ? key
              : `${key}.${
                  activeContentTab === 'codeblock'
                    ? 'py'
                    : activeContentTab === 'bashblock'
                      ? 'sh'
                      : activeContentTab === 'guide'
                        ? 'md'
                        : activeContentTab === 'install_guide'
                          ? 'md'
                          : 'txt'
                }`;

          items.push({
            fileName,
            content: typeof value === 'string' ? value : JSON.stringify(value, null, 2),
          });
        }
      });
    } else if (typeof content === 'string' && content.trim() !== '') {
      // Handle string content
      items.push({
        fileName: `${activeContentTab}.txt`,
        content: content,
      });
    }

    return items;
  }, [activeContentTab, currentContent]);

  const { runActionModalData, setRunActionModalData } = useActionContext();
  const { setTaskModalState } = useTaskModalContext();

  useEffect(() => {
    setSelectedTabIndex(0);
  }, [activeContentTab]);

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' });
  }, [messages]);

  useEffect(() => {
    inputRef.current?.focus();
  }, []);

  // Resolve the user's folder.user laui for storing chat_history
  useEffect(() => {
    if (userFolderLaui) return;
    const resolveUserFolder = async () => {
      try {
        const response = await searchCatalogItems('folder.user', false, { perPage: 1 });
        const folder = response?.items?.[0];
        if (folder?.laui) {
          setUserFolderLaui(folder.laui);
        }
      } catch (err) {
        console.error('Failed to resolve user folder:', err);
      }
    };
    void resolveUserFolder();
  }, [userFolderLaui]);

  // Keep sessionLauiRef in sync with state/context
  useEffect(() => {
    sessionLauiRef.current = sessionLaui;
  }, [sessionLaui]);

  // Load existing session data when resuming a previous session
  useEffect(() => {
    if (!sessionLaui) return;
    const loadSession = async () => {
      try {
        const { getCatalogItemById } = await import('@/services/catalog.service');
        const response: any = await getCatalogItemById(sessionLaui);
        // getCatalogItemById returns FullItemData (flat object with all fields)
        const item = response;

        if (item?.name) {
          sessionNameRef.current = item.name;
        }
        if (item?.messages && Array.isArray(item.messages)) {
          const loadedMessages: Message[] = item.messages.map((m: any, i: number) => ({
            id: `loaded-${i}`,
            role: m.role || 'user',
            content: m.content || '',
            timestamp: m.timestamp ? new Date(m.timestamp) : new Date(),
          }));
          setMessages(loadedMessages);
          setActiveContentTab('chat');
        }
        if (item?.generated_content && typeof item.generated_content === 'object') {
          const gc = item.generated_content;
          setGeneratedContent({
            codeblock: gc.codeblock || {},
            bashblock: gc.bashblock || {},
            connection: gc.connection || {},
            payload: gc.payload || {},
            action_variables: gc.action_variables || {},
            guide: gc.guide || {},
            install_guide: gc.install_guide || {},
            prompt: gc.prompt || '',
          });
        }
      } catch (err) {
        console.error('Failed to load session:', err);
      }
    };
    void loadSession();
  }, [sessionLaui]);

  const saveAiHistory = async (
    allMessages: Message[],
    content?: GeneratedContent,
    tempFilePath?: string,
    shouldNavigate = false,
  ) => {
    // Generate session name only once per session
    if (!sessionNameRef.current) {
      sessionNameRef.current = `${itemType}_session_${new Date().toISOString().slice(0, 19).replace(/[:.]/g, '-')}`;
    }
    try {
      const historyData: any = {
        item_type: 'chat_history',
        name: sessionNameRef.current,
        parent_laui: userFolderLaui,
        created_item_type: itemType,
        ai_provider: aiProvider,
        chat_laui: aiChatLaui,
        ...(connectionLaui ? { connection_laui: connectionLaui } : {}),
        ...(tempFilePath && { temp_file_path: tempFilePath }),
        messages: allMessages.map((m) => ({
          role: m.role,
          content: m.content,
          timestamp: m.timestamp,
        })),
        generated_content: content || generatedContent,
      };
      const result = await createCatalogItem(historyData);
      if (!sessionLauiRef.current && result?.item_laui) {
        sessionLauiRef.current = result.item_laui;
        setSessionLaui(result.item_laui);
      }
      if (shouldNavigate && sessionNameRef.current) {
        await navigate({ to: '/ai/create', search: { sessionId: sessionNameRef.current } });
      }
    } catch (historyErr) {
      console.error('Failed to save chat_history:', historyErr);
    }
  };

  const handleSendMessage = async () => {
    if (!inputMessage.trim() || isLoading || !onGenerate) return;

    const userMessage: Message = {
      id: Date.now().toString(),
      role: 'user',
      content: inputMessage.trim(),
      timestamp: new Date(),
    };

    const updatedMessages = [...messages, userMessage];
    setMessages(updatedMessages);
    setInputMessage('');
    setIsLoading(true);

    // Save chat_history immediately with the user prompt (before AI responds)
    await saveAiHistory(updatedMessages, undefined, undefined, false);

    try {
      // Take last 5 pairs (10 messages) for context
      const historyMessages = updatedMessages.slice(-10).map((m) => ({
        role: m.role,
        content: m.content,
      }));
      const skillContent =
        selectedSkills.length > 0 ? selectedSkills.map((s) => s.content).join('\n\n') : undefined;
      const response = await onGenerate(
        inputMessage.trim(),
        includeGuideDoc,
        includeInstallGuide,
        historyMessages,
        generatedContent,
        skillContent,
      );
      if (!response) return;
      setSelectedSkills([]);

      // Extract generated content from response
      let generatedContentFromResponse: GeneratedContent = {
        codeblock: {},
        bashblock: {},
        connection: {},
        payload: {},
        action_variables: {},
        guide: {},
        install_guide: {},
        prompt: inputMessage.trim(),
      };

      // Handle different response structures
      if (response.generated_content) {
        generatedContentFromResponse = {
          ...generatedContentFromResponse,
          ...response.generated_content,
          prompt: inputMessage.trim(),
        };
      }

      // Clean up empty objects
      Object.keys(generatedContentFromResponse).forEach((key) => {
        const contentKey = key as keyof GeneratedContent;
        if (
          generatedContentFromResponse[contentKey] &&
          typeof generatedContentFromResponse[contentKey] === 'object' &&
          Object.keys(generatedContentFromResponse[contentKey] as object).length === 0
        ) {
          generatedContentFromResponse[contentKey] = {} as any;
        }
      });

      setGeneratedContent(generatedContentFromResponse);
      setAiValidationResult((response as any).validation || null);
      updateContentTab(generatedContentFromResponse);

      const assistantMessage: Message = {
        id: (Date.now() + 1).toString(),
        role: 'assistant',
        content: response.message || 'Content generated successfully',
        timestamp: new Date(),
      };

      const allMessages = [...updatedMessages, assistantMessage];
      setMessages(allMessages);

      // Update chat_history with AI response and generated content, navigate now that everything is ready
      await saveAiHistory(allMessages, generatedContentFromResponse, response.temp_file_path, true);
    } catch (error) {
      console.error(TEXT.GENERATION_FAILED, error);
      const errorMessage: Message = {
        id: (Date.now() + 2).toString(),
        role: 'assistant',
        content: `Error: ${error instanceof Error ? error.message : TEXT.GENERATION_FAILED}`,
        timestamp: new Date(),
      };
      const allMessages = [...updatedMessages, errorMessage];
      setMessages(allMessages);

      // Save chat_history even on error so the prompt is not lost
      await saveAiHistory(allMessages);
    } finally {
      setIsLoading(false);
    }
  };

  const updateContentTab = (content: GeneratedContent) => {
    // Determine which tab to show based on available content
    if (Object.keys(content.codeblock).length > 0) {
      setActiveContentTab('codeblock');
    } else if (showActionVariables && Object.keys(content.action_variables || {}).length > 0) {
      setActiveContentTab('action_variables');
    } else if (Object.keys(content.bashblock).length > 0) {
      setActiveContentTab('bashblock');
    } else if (Object.keys(content.connection).length > 0) {
      setActiveContentTab('connection');
    } else if (!showActionVariables && Object.keys(content.payload).length > 0) {
      setActiveContentTab('payload');
    } else if (Object.keys(content.guide).length > 0) {
      setActiveContentTab('guide');
    } else if (Object.keys(content.install_guide).length > 0) {
      setActiveContentTab('install_guide');
    }
  };

  const handleKeyPress = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault();
      void handleSendMessage();
    }
  };

  const handleRegenerate = useCallback(() => {
    if (messages.length < 2) return;

    const lastUserMessage = messages.filter((m) => m.role === 'user').slice(-1)[0];

    if (lastUserMessage) {
      setInputMessage(lastUserMessage.content);
      inputRef.current?.focus();
    }
  }, [messages]);

  const handleClearContext = useCallback(() => {
    setMessages(messages.filter((m) => m.role === 'system'));
  }, [messages]);

  const handleSkillSelect = async (item: unknown) => {
    const raw = item as Record<string, unknown>;
    const laui = (raw._laui ?? raw.laui ?? raw.id ?? '') as string;
    if (!laui) return;
    if (selectedSkills.some((s) => s.laui === laui)) return;
    try {
      const fullItem: any = await getCatalogItemById(laui);
      const content = fullItem?.content;
      if (!content) return;
      const name = fullItem?.name || laui;
      setSelectedSkills((prev) => [...prev, { laui, name, content }]);
    } catch (err) {
      console.error('Failed to fetch skill content:', err);
    }
  };

  const handleDeleteSession = async () => {
    const currentLaui = sessionLauiRef.current;
    if (!currentLaui) return;
    try {
      await deleteCatalogItem(currentLaui, userFolderLaui || '');
      sessionLauiRef.current = null;
      sessionNameRef.current = null;
      setSessionLaui(null);
      setMessages([]);
      setGeneratedContent({
        codeblock: {},
        bashblock: {},
        connection: {},
        payload: {},
        guide: {},
        install_guide: {},
        action_variables: {},
        prompt: '',
      });
      setAiValidationResult(null);
      setActiveContentTab('chat');
    } catch (err) {
      console.error('Failed to delete session:', err);
    }
  };

  const handleTestRunClick = () => {
    if (showActionVariables) {
      setRunActionModalData({
        actionVariables: generatedContent.action_variables || {},
        operatorData: {
          prompt: generatedContent.prompt || '',
          install_docs: generatedContent.install_guide || {},
          guide_docs: generatedContent.guide || {},
          codeblock: generatedContent.codeblock || {},
          bashblock: generatedContent.bashblock || {},
        },
        isOpen: true,
        mode: RunActionModalMode.CREATE,
      });
      return;
    }
    // Simply open the modal - it will fetch its own data
    setTaskModalState({
      isOpen: true,
      mode: TaskModalMode.RUN,
      scope: { scopeType: TaskModalScopeType.AI },
      operatorData: {
        codeblock: generatedContent.codeblock || {},
        bashblock: generatedContent.bashblock || {},
        connection: generatedContent.connection || {},
        payload: JSON.stringify(generatedContent.payload) || '',
        install_docs: generatedContent.install_guide || {},
        guide_docs: generatedContent.guide || {},
      },
    });
  };

  const handleSaveClick = () => {
    setSaveItemModalState({ isOpen: true, itemData: generatedContent });
  };

  const onBack = () => {
    setSessionLaui(null);
    setMode(AIMode.ITEMTYPE);
    void navigate({ to: '/ai/create', search: { sessionId: undefined } });
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setSelectedTabIndex(newValue);
  };

  const handleContentChange = useCallback(
    (newValue: string) => {
      if (activeContentTab === 'chat') return;

      const newContent = { ...generatedContent };

      if (
        activeContentTab === 'connection' ||
        activeContentTab === 'action_variables' ||
        activeContentTab === 'payload'
      ) {
        const key = activeContentTab;
        if (newValue.trim() === '') {
          newContent[key] = {};
        } else {
          try {
            newContent[key] = JSON.parse(newValue);
          } catch {
            // Invalid JSON, keep old value
          }
        }
      } else if (contentItems[selectedTabIndex]) {
        const fileName = contentItems[selectedTabIndex].fileName;
        const key = activeContentTab;
        if (typeof newContent[key] === 'object' && newContent[key] !== null) {
          newContent[key] = {
            ...newContent[key],
            [fileName]: newValue,
          };
        }
      }

      setGeneratedContent(newContent);
    },
    [activeContentTab, generatedContent, contentItems, selectedTabIndex],
  );

  const renderEditorContent = () => {
    if (activeContentTab === 'chat') {
      return (
        <>
          <Box sx={styles.chatMessages}>
            {messages.map((message) => (
              <MessageBubble key={message.id} message={message} itemType={itemType} />
            ))}

            {isLoading && (
              <Box sx={styles.loadingMessage}>
                <Paper sx={styles.loadingBubble}>
                  <Typography variant="body2" sx={styles.loadingText}>
                    <RefreshIcon
                      sx={{
                        animation: 'spin 1s linear infinite',
                        fontSize: '0.875rem',
                      }}
                    />
                    {TEXT.PROCESSING}
                  </Typography>
                </Paper>
              </Box>
            )}

            <div ref={messagesEndRef} />
          </Box>

          <Box sx={styles.inputArea}>
            <Box sx={styles.inputContainer}>
              <TextField
                inputRef={inputRef}
                fullWidth
                multiline
                maxRows={3}
                value={inputMessage}
                onChange={(e) => setInputMessage(e.target.value)}
                onKeyPress={handleKeyPress}
                placeholder={TEXT.INPUT_PLACEHOLDER}
                variant="outlined"
                size="small"
                disabled={isLoading}
                sx={styles.textInput}
              />

              <Button
                variant="contained"
                onClick={() => void handleSendMessage()}
                disabled={!inputMessage.trim() || isLoading}
                aria-label="Send message"
                sx={styles.sendButton}
              >
                <SendIcon fontSize="small" />
              </Button>
            </Box>

            <Box sx={styles.optionsArea}>
              <Box sx={styles.leftOptions}>
                <FormControlLabel
                  control={
                    <Checkbox
                      size="small"
                      checked={includeGuideDoc}
                      onChange={(e) => setIncludeGuideDoc(e.target.checked)}
                      sx={styles.checkbox}
                    />
                  }
                  label={
                    <Typography sx={styles.checkboxLabel}>{TEXT.INCLUDE_GUIDE_DOC}</Typography>
                  }
                />

                <FormControlLabel
                  control={
                    <Checkbox
                      size="small"
                      checked={includeInstallGuide}
                      onChange={(e) => setIncludeInstallGuide(e.target.checked)}
                      sx={styles.checkbox}
                    />
                  }
                  label={
                    <Typography sx={styles.checkboxLabel}>{TEXT.INCLUDE_INSTALL_GUIDE}</Typography>
                  }
                />

                <Box
                  sx={{
                    minWidth: 180,
                    display: 'flex',
                    alignItems: 'center',
                    gap: 0.5,
                    flexWrap: 'wrap',
                  }}
                >
                  <QuickSearch
                    label={TEXT.SKILLS_LABEL}
                    value={null}
                    filters={{ item_type: 'skill' }}
                    onSelect={() => void handleSkillSelect()}
                    placeholder="Search skill…"
                  />
                  {selectedSkills.map((skill) => (
                    <Chip
                      key={skill.laui}
                      label={skill.name}
                      size="small"
                      onDelete={() =>
                        setSelectedSkills((prev) => prev.filter((s) => s.laui !== skill.laui))
                      }
                      sx={{
                        backgroundColor: 'var(--bg-secondary)',
                        color: 'var(--text-primary)',
                        '& .MuiChip-deleteIcon': {
                          color: 'var(--text-secondary)',
                          '&:hover': { color: 'var(--text-primary)' },
                        },
                      }}
                    />
                  ))}
                </Box>

                <Divider
                  orientation="vertical"
                  flexItem
                  sx={{
                    height: 20,
                    backgroundColor: 'var(--border-color)',
                  }}
                />

                <Button
                  startIcon={<RefreshIcon />}
                  onClick={handleRegenerate}
                  size="small"
                  disabled={messages.length < 2}
                  aria-label="Regenerate last response"
                  sx={styles.actionButton}
                >
                  {TEXT.REGENERATE}
                </Button>

                <Button
                  startIcon={<ClearIcon />}
                  onClick={handleClearContext}
                  size="small"
                  aria-label="Clear conversation context"
                  sx={styles.clearButton}
                >
                  {TEXT.CLEAR_CONTEXT}
                </Button>

                <Button
                  startIcon={<DeleteIcon />}
                  onClick={() => void handleDeleteSession()}
                  size="small"
                  disabled={!sessionLaui}
                  aria-label="Delete chat session"
                  sx={styles.clearButton}
                >
                  {TEXT.DELETE_SESSION}
                </Button>
              </Box>

              <Typography variant="caption" sx={styles.connectionStatus}>
                {TEXT.CONNECTED} • {TEXT.PROVIDER_PREFIX}: {aiProvider || 'Not selected'}
              </Typography>
            </Box>
          </Box>
        </>
      );
    }

    return (
      <Box sx={styles.arrayFieldContainer}>
        {contentItems.length > 0 ? (
          <Box sx={styles.arrayTabsContainer}>
            <Box sx={{ flex: 1, display: 'flex', flexDirection: 'column' }}>
              {contentItems.length > 1 && (
                <Tabs
                  value={selectedTabIndex}
                  onChange={handleTabChange}
                  variant="scrollable"
                  scrollButtons="auto"
                  sx={styles.arrayTabs}
                >
                  {contentItems.map((item, index) => (
                    <Tab key={index} label={item.fileName} />
                  ))}
                </Tabs>
              )}

              <Box sx={{ flex: 1, overflow: 'hidden', width: '100%' }}>
                {contentItems.map((item, index) => (
                  <TabPanel key={index} value={selectedTabIndex} index={index}>
                    <MonacoWrapper
                      content={item.content}
                      fileName={item.fileName}
                      onChange={handleContentChange}
                      field={''}
                    />
                  </TabPanel>
                ))}
              </Box>
              {activeContentTab === 'codeblock' && aiValidationResult && (
                <Box sx={{ mt: 1 }}>
                  <ValidationPanel result={aiValidationResult} />
                </Box>
              )}
            </Box>
          </Box>
        ) : (
          <Box sx={styles.emptyContent}>
            <Typography sx={styles.emptyText}>{TEXT.NO_CONTENT}</Typography>
          </Box>
        )}
      </Box>
    );
  };

  return (
    <Box sx={styles.container}>
      <Box sx={styles.header}>
        <Box sx={styles.headerLeft}>
          <Box sx={styles.navButtons}>
            <Tooltip title={TEXT.BACK_BUTTON}>
              <IconButton size="small" onClick={onBack} sx={styles.backButton}>
                <ArrowBackIcon />
              </IconButton>
            </Tooltip>
          </Box>

          <Box sx={styles.typeBadge}>
            <Typography sx={styles.typeLabel}>Type:</Typography>
            <Typography sx={styles.typeValue}>{itemType?.toLowerCase() || 'unknown'}</Typography>
          </Box>
          <Box sx={styles.tabChipsContainer}>
            <ContentTabChip
              label="CHAT"
              tabType="chat"
              activeTab={activeContentTab}
              count={contentCounts.chat}
              onClick={() => setActiveContentTab('chat')}
            />
            <ContentTabChip
              label="CODEBLOCK"
              tabType="codeblock"
              activeTab={activeContentTab}
              count={contentCounts.codeblock}
              onClick={() => setActiveContentTab('codeblock')}
            />
            <ContentTabChip
              label="BASHBLOCK"
              tabType="bashblock"
              activeTab={activeContentTab}
              count={contentCounts.bashblock}
              onClick={() => setActiveContentTab('bashblock')}
            />
            <ContentTabChip
              label="CONNECTION"
              tabType="connection"
              activeTab={activeContentTab}
              count={contentCounts.connection}
              onClick={() => setActiveContentTab('connection')}
            />
            {showActionVariables ? (
              <ContentTabChip
                label={'ACTION_VARIABLES'}
                tabType="action_variables"
                activeTab={activeContentTab}
                count={contentCounts.action_variables}
                onClick={() => setActiveContentTab('action_variables')}
              />
            ) : (
              <ContentTabChip
                label="PAYLOAD"
                tabType="payload"
                activeTab={activeContentTab}
                count={contentCounts.payload}
                onClick={() => setActiveContentTab('payload')}
              />
            )}
            <ContentTabChip
              label="INSTALL DOCS"
              tabType="install_guide"
              activeTab={activeContentTab}
              count={contentCounts.install_guide}
              onClick={() => setActiveContentTab('install_guide')}
            />
            <ContentTabChip
              label="GUIDE DOCS"
              tabType="guide"
              activeTab={activeContentTab}
              count={contentCounts.guide}
              onClick={() => setActiveContentTab('guide')}
            />
          </Box>
        </Box>

        <Box sx={styles.headerRight}>
          {/* Action AI Info */}
          <Typography sx={styles.typeLabel}>Action AI:</Typography>
          <Typography sx={styles.typeValue}>{aiChatName}</Typography>

          <Button
            variant="contained"
            size="small"
            onClick={handleTestRunClick}
            disabled={!hasGeneratedContent || runTestLoading}
            aria-label="Run test"
            sx={styles.runTestButton}
          >
            {runTestLoading ? 'Loading...' : showActionVariables ? TEXT.RUN_ACTION : TEXT.RUN_TEST}
          </Button>

          <Tooltip
            title={
              hasGeneratedContent ? TEXT.SAVE_RESULTS : 'Generate content first to enable save'
            }
          >
            <span>
              <IconButton
                size="small"
                onClick={handleSaveClick}
                disabled={!hasGeneratedContent}
                aria-label="Save results"
                sx={styles.saveButton}
              >
                <SaveIcon />
              </IconButton>
            </span>
          </Tooltip>
        </Box>
      </Box>

      <Box sx={styles.mainContent}>
        <Box sx={styles.mainPanel}>{renderEditorContent()}</Box>
      </Box>

      <style>
        {`
          @keyframes spin {
            0% { transform: rotate(0deg); }
            100% { transform: rotate(360deg); }
          }

          :root {
            --border-color: rgba(var(--color-border), 0.2);
          }
        `}
      </style>

      <SaveItemModal />

      {showActionVariables ? (
        <RunActionModal open={runActionModalData?.isOpen || false} />
      ) : (
        <RunTaskModal />
      )}
    </Box>
  );
};

export default ManualEditor;
