/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCallback, useEffect, useRef, useState } from 'react';

import { Link as RouterLink, useNavigate, useSearch } from '@tanstack/react-router';

import {
  CalendarMonth as CalendarMonthIcon,
  Check as CheckIcon,
  Close as CloseIcon,
  ContentCopy as ContentCopyIcon,
  Edit as EditIcon,
  HelpOutline as HelpOutlineIcon,
  Monitor as MonitorIcon,
  OpenInFull as OpenInFullIcon,
  PlayArrow as PlayArrowIcon,
  Refresh as RefreshIcon,
  Schedule as ScheduleIcon,
  Stop as StopIcon,
  WarningAmber as WarningAmberIcon,
} from '@mui/icons-material';
import {
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
  Tab,
  Tabs,
  Tooltip,
  Typography,
} from '@mui/material';

import { FancyJsonEditor } from '@/components/browse/FieldRenderer/FancyJsonEditor';
import TaskAnalyticsTab from '@/components/browse/TaskAnalyticsTab.tsx';
import StreamLogViewer from '@/components/logs/StreamLogViewer';
import TaskLogsTab from '@/components/logs/TaskLogsTab.tsx';
import BaseModal from '@/components/ui/Modal/BaseModal';
import { MonacoWrapper } from '@/components/ui/MonacoWrapper.tsx';
import {
  BORDER_RADIUS,
  BUTTON_SIZES,
  FONT_FAMILIES,
  FONT_SIZES,
  FONT_WEIGHTS,
  LETTER_SPACING,
} from '@/constants/index.ts';
import { useCatalog } from '@/contexts/CatalogContext.tsx';
import { useNotification } from '@/contexts/NotificationContext.tsx';
import {
  TaskModalMode,
  TaskModalScopeType,
  useTaskModalContext,
} from '@/contexts/TaskModalContext.tsx';
import { useTimeFormat } from '@/contexts/TimeFormatContext';
import { getCatalogItemById } from '@/services/catalog.service.ts';
import { calculateTimeDelta } from '@/services/scheduler.service.ts';
import { getProjectionFieldsConfig } from '@/services/schema.service.ts';
import { buildLogApiUrl, consumeSSE } from '@/services/sseHelper';
import {
  cancelTask,
  dangerouslyResetTask,
  diagnoseTask,
  runTask,
} from '@/services/task.service.ts';
import type { TaskDiagnosticResponse } from '@/services/task.service.ts';
import { formatDateTime, formatDateTimeCompact, getTimeZoneLabel } from '@/utils/timeFormat';

import type { CatalogItem } from '../types.ts';

interface TaskViewProps {
  selectedItem: CatalogItem;
}

// Tab Panel Component
interface TabPanelProps {
  children?: React.ReactNode;
  index: number;
  value: number;
}

function TabPanel(props: TabPanelProps) {
  const { children, value, index, ...other } = props;
  if (value !== index) return null;
  return (
    <div
      role="tabpanel"
      id={`task-tabpanel-${index}`}
      aria-labelledby={`task-tab-${index}`}
      style={{ height: '100%' }}
      {...other}
    >
      <Box sx={{ height: '100%' }}>{children}</Box>
    </div>
  );
}

// ── Styles ──────────────────────────────────────────────────────────────────
const styles = {
  container: {
    flex: 1,
    bgcolor: 'var(--bg-primary)',
    overflow: 'auto',
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    scrollbarGutter: 'stable',
  },
  header: {
    px: 2.5,
    py: 2,
    borderBottom: 1,
    borderColor: 'var(--border)',
    bgcolor: 'var(--bg-secondary)',
  },
  headerTitle: {
    display: 'flex',
    alignItems: 'center',
    gap: 1.5,
    mb: 0.5,
  },
  title: {
    fontSize: '1.375rem',
    fontWeight: FONT_WEIGHTS.BOLD,
    color: 'var(--text-primary)',
  },
  subtitle: {
    color: 'var(--text-secondary)',
    fontSize: FONT_SIZES.XS,
    display: 'flex',
    alignItems: 'center',
    gap: 1,
  },
  tabsContainer: {
    borderBottom: 1,
    borderColor: 'var(--border)',
    bgcolor: 'var(--bg-secondary)',
  },
  tabs: {
    minHeight: '32px',
    '& .MuiTab-root': {
      color: 'var(--text-secondary)',
      textTransform: 'none',
      fontSize: FONT_SIZES.XS,
      fontWeight: FONT_WEIGHTS.WEIGHT_400,
      minHeight: '32px',
      '&.Mui-selected': {
        color: 'var(--accent)',
        fontWeight: FONT_WEIGHTS.WEIGHT_600,
      },
    },
    '& .MuiTabs-indicator': {
      bgcolor: 'var(--accent)',
      height: '2px',
    },
  },
  content: {
    flex: 1,
    overflow: 'auto',
    p: 2,
  },
  monacoContainer: {
    height: 'calc(100vh - 350px)',
    minHeight: '400px',
  },
  // ── Status bar ──
  statusBar: {
    display: 'flex',
    alignItems: 'center',
    gap: 1.5,
    px: 1.5,
    py: 0.875,
    mb: 1.5,
    borderRadius: BORDER_RADIUS.LG,
    bgcolor: 'var(--bg-secondary)',
    border: 1,
    borderColor: 'var(--border)',
    flexWrap: 'wrap' as const,
  },
  // ── Overview layout ──
  overviewGrid: {
    display: 'grid',
    gridTemplateColumns: 'minmax(190px, 23%) 1fr',
    gap: 1.5,
    alignItems: 'start',
  },
  leftColumn: {
    display: 'flex',
    flexDirection: 'column',
    gap: 1.5,
  },
  rightColumn: {
    display: 'flex',
    flexDirection: 'column',
    gap: 1.5,
  },
  // ── Card base ──
  card: {
    p: 2,
    borderRadius: BORDER_RADIUS.LG,
    bgcolor: 'var(--bg-secondary)',
    border: 1,
    borderColor: 'var(--border)',
  },
  // ── Section header ──
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: 0.875,
    mb: 1.25,
  },
  sectionHeaderText: {
    fontSize: FONT_SIZES.XS,
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
    color: 'var(--text-secondary)',
    textTransform: 'uppercase',
    letterSpacing: LETTER_SPACING.WIDER,
  },
  sectionDot: {
    width: 7,
    height: 7,
    borderRadius: '50%',
    flexShrink: 0,
  },
  // ── Metadata rows ──
  metadataRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    py: 0.625,
    borderBottom: 1,
    borderColor: 'var(--border)',
    '&:last-of-type': {
      borderBottom: 'none',
    },
  },
  metadataLabel: {
    fontSize: FONT_SIZES.XS,
    color: 'var(--text-dim)',
    minWidth: 68,
    flexShrink: 0,
  },
  metadataValue: {
    fontSize: FONT_SIZES.XS,
    fontWeight: FONT_WEIGHTS.WEIGHT_500,
    color: 'var(--text-primary)',
    textAlign: 'right' as const,
    overflow: 'hidden',
    textOverflow: 'ellipsis',
    whiteSpace: 'nowrap' as const,
    maxWidth: 150,
  },
  // ── Terminal output viewer ──
  terminalHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    px: 1.5,
    py: 0.75,
    bgcolor: 'var(--bg-tertiary)',
    borderBottom: 1,
    borderColor: 'var(--border)',
  },
  terminalDots: {
    display: 'flex',
    gap: 0.5,
  },
  terminalDot: {
    width: 8,
    height: 8,
    borderRadius: '50%',
  },
  // ── Actions columns ──
  actionColumnBody: {
    maxHeight: 130,
    overflow: 'auto',
    flex: 1,
  },
  actionColumnHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    px: 1.5,
    py: 0.875,
    borderBottom: 1,
    borderColor: 'var(--border)',
  },
  actionItem: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    px: 1.5,
    py: 0.75,
    borderBottom: 1,
    borderColor: 'var(--border)',
    '&:last-of-type': {
      borderBottom: 'none',
    },
  },
  // ── Timeline row ──
  timelineRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    py: 0.6,
    gap: 1,
  },
  timelineLabel: {
    fontSize: FONT_SIZES.XS,
    color: 'var(--text-dim)',
    flexShrink: 0,
    cursor: 'help',
  },
  timelineValue: {
    fontSize: FONT_SIZES.XS,
    fontWeight: FONT_WEIGHTS.WEIGHT_500,
    color: 'var(--accent)',
    fontFamily: FONT_FAMILIES.MONOSPACE,
    textAlign: 'right' as const,
  },
};

// ── Helper functions ────────────────────────────────────────────────────────

const formatDate = (dateString: string | null | undefined) => {
  return formatDateTime(dateString);
};

const formatDuration = (seconds: number | null | undefined) => {
  if (!seconds && seconds !== 0) return 'N/A';
  if (seconds < 1) return `${Math.round(seconds * 1000)}ms`;
  if (seconds < 60) return `${seconds.toFixed(2)}s`;
  if (seconds < 3600) return `${(seconds / 60).toFixed(2)}m`;
  return `${(seconds / 3600).toFixed(2)}h`;
};

const formatRetryInterval = (val: number | null | undefined) => {
  if (!val && val !== 0) return '0m';
  return `${val}m`;
};

const formatDateCompact = (dateString: string | null | undefined) => {
  return formatDateTimeCompact(dateString);
};

// Format JSON for display
const formatJSON = (data: any) => {
  if (!data) return '';
  if (typeof data === 'string') {
    try {
      return JSON.stringify(JSON.parse(data), null, 2);
    } catch {
      return data;
    }
  }
  return JSON.stringify(data, null, 2);
};

// ── Component ───────────────────────────────────────────────────────────────

export default function TaskView({ selectedItem }: TaskViewProps) {
  const { timeZone } = useTimeFormat();
  const tzLabel = timeZone === 'utc' ? 'UTC' : getTimeZoneLabel();
  const [tabValue, setTabValue] = useState(0);
  const [logsSessionId, setLogsSessionId] = useState<string | undefined>(undefined);
  const [stateColor, setStateColor] = useState<string | null>(null);
  const [currentItem, setCurrentItem] = useState<CatalogItem>(selectedItem);
  const [isRefreshing, setIsRefreshing] = useState(false);
  const [nameCopied, setNameCopied] = useState(false);
  const [descExpanded, setDescExpanded] = useState(false);
  const [nameExpanded, setNameExpanded] = useState(false);
  const nameRef = useRef<HTMLSpanElement>(null);
  const [nameTruncated, setNameTruncated] = useState(false);

  // URL params for deep-linking to logs tab & session
  const navigate = useNavigate();
  const urlSearch = useSearch({ strict: false });
  const urlTab = typeof urlSearch.itemTab === 'string' ? urlSearch.itemTab : undefined;
  const urlSessionId = typeof urlSearch.sessionId === 'string' ? urlSearch.sessionId : undefined;
  const urlTabRef = useRef(urlTab);
  urlTabRef.current = urlTab;
  const urlSessionIdRef = useRef(urlSessionId);
  urlSessionIdRef.current = urlSessionId;

  const updateUrlParams = useCallback(
    (updates: { tab?: string; sessionId?: string }) => {
      void navigate({
        to: '.',
        search: (prev: any) => {
          const next = { ...prev };
          if ('tab' in updates) {
            if (updates.tab) next.itemTab = updates.tab;
            else delete next.itemTab;
          }
          if ('sessionId' in updates) {
            if (updates.sessionId) next.sessionId = updates.sessionId;
            else delete next.sessionId;
          }
          return next;
        },
        replace: true,
      });
    },
    [navigate],
  );

  // Derive taskData from currentItem - handle both CatalogItem (with data property) and FullItemData (flat structure)
  const getTaskData = useCallback((item: CatalogItem): any => {
    // If item has a nested data property with task-specific fields, use it
    if (item.data && typeof item.data === 'object' && Object.keys(item.data).length > 2) {
      return { ...item, ...item.data };
    }
    // Otherwise, the item itself contains all fields (FullItemData format)
    return item;
  }, []);

  const taskData: any = getTaskData(currentItem);
  const { showSuccess, showError } = useNotification();
  const { editorState, catalogState, markNavigatedInAppRef } = useCatalog();
  const [metadataItems, setMetadataItems] = useState<{
    operator?: { name: string; itemType: string };
    connection?: { name: string; itemType: string };
    payload?: { name: string; itemType: string };
    attachedConfigs?: { laui: string; name: string; itemType: string }[];
  }>({});
  const [payloadLauiContent, setPayloadLauiContent] = useState<any>(null);
  const [payloadLauiLoading, setPayloadLauiLoading] = useState(false);
  const [outputCopied, setOutputCopied] = useState(false);
  const [outputExpanded, setOutputExpanded] = useState(false);
  const [schedulerStatus, setSchedulerStatus] = useState<
    'RUNNING' | 'STOPPED' | 'UNHEALTHY' | null
  >(null);
  const [dangerousResetModalOpen, setDangerousResetModalOpen] = useState(false);
  const [isResetting, setIsResetting] = useState(false);
  const [diagnosticModalOpen, setDiagnosticModalOpen] = useState(false);
  const [diagnosticData, setDiagnosticData] = useState<TaskDiagnosticResponse | null>(null);
  const [isDiagnosing, setIsDiagnosing] = useState(false);
  const [latestActionFiles, setLatestActionFiles] = useState<{ name: string; logUrl: string }[]>(
    [],
  );
  const [actionLogFile, setActionLogFile] = useState<{ name: string; logUrl: string } | null>(null);

  // Fetch latest action log files from the task's last-run date partition
  useEffect(() => {
    const taskLaui = taskData?.laui || selectedItem.laui;
    const dateStr = taskData?.logical_date;
    if (!taskLaui || !dateStr) {
      setLatestActionFiles([]);
      return;
    }
    const dateOnly = String(dateStr).split(/[T ]/)[0];
    const [y, m, d] = dateOnly.split('-');
    if (!y || !m || !d) {
      setLatestActionFiles([]);
      return;
    }
    const folderPath = `category=TASK_HISTORY/task_laui=${taskLaui}/yyyy=${y}/mm=${m}/dd=${d}`;
    const results: { name: string; logUrl: string }[] = [];
    const ctrl = consumeSSE(buildLogApiUrl(`listItems/${folderPath}`), {
      onEvent: (type, data: any) => {
        if (type === 'data' && data?.items) {
          for (const item of data.items) {
            if (
              item.type === 'file' &&
              item.name.startsWith('latest_') &&
              item.name.endsWith('.log')
            ) {
              results.push({
                name: item.name,
                logUrl: `file/${folderPath}/${item.name}`,
              });
            }
          }
        }
      },
      onDone: () => setLatestActionFiles([...results]),
      onError: () => setLatestActionFiles([]),
    });
    return () => ctrl.abort();
  }, [taskData?.laui, selectedItem.laui, taskData?.logical_date]);

  useEffect(() => {
    if (nameRef.current) {
      setNameTruncated(nameRef.current.scrollHeight > nameRef.current.clientHeight);
    }
  }, [taskData?.name, nameExpanded]);

  const TAB_NAME_TO_INDEX: Record<string, number> = {
    overview: 0,
    payload: 1,
    config: 2,
    actions: 3,
    logs: 4,
    analytics: 5,
  };
  const TAB_INDEX_TO_NAME: Record<number, string> = {
    0: 'overview',
    1: 'payload',
    2: 'config',
    3: 'actions',
    4: 'logs',
    5: 'analytics',
  };

  useEffect(() => {
    setCurrentItem(selectedItem);
    // Initialize from URL params or reset to overview
    const urlTabName = urlTabRef.current;
    if (urlTabName && urlTabName in TAB_NAME_TO_INDEX) {
      setTabValue(TAB_NAME_TO_INDEX[urlTabName]);
      if (urlTabName === 'logs') {
        setLogsSessionId(urlSessionIdRef.current || undefined);
      } else {
        setLogsSessionId(undefined);
      }
    } else {
      setTabValue(0);
      setLogsSessionId(undefined);
      updateUrlParams({ tab: undefined, sessionId: undefined });
    }
  }, [selectedItem]);

  // Fetch project scheduler status whenever the task's project changes
  useEffect(() => {
    const projectLaui = taskData.project_laui;
    if (!projectLaui) {
      setSchedulerStatus(null);
      return;
    }
    setSchedulerStatus(null);
    getCatalogItemById(projectLaui)
      .then((projectItem) => {
        if (!projectItem) return;
        const cronStatus: string | undefined = projectItem.folder_metadata?.cron_status;
        const latestHeartbeat: string | undefined = projectItem.folder_metadata?.latest_heartbeat;
        if (cronStatus === 'RUNNING') {
          const isUnhealthy = latestHeartbeat && calculateTimeDelta(latestHeartbeat) > 15; // 3 × 5s interval
          setSchedulerStatus(isUnhealthy ? 'UNHEALTHY' : 'RUNNING');
        } else {
          setSchedulerStatus('STOPPED');
        }
      })
      .catch(() => setSchedulerStatus(null));
  }, [taskData.project_laui]);

  // Fetch metadata items (operator, connection, payload) details
  useEffect(() => {
    const fetchMetadataItems = async () => {
      if (taskData.payload_laui) setPayloadLauiLoading(true);
      const attachedConfigLauis: string[] = taskData.attached_config_lauis || [];

      const [operatorResult, connectionResult, payloadResult, ...configResults] =
        await Promise.allSettled([
          taskData.operator_laui
            ? getCatalogItemById(taskData.operator_laui)
            : Promise.resolve(null),
          taskData.connection_laui
            ? getCatalogItemById(taskData.connection_laui)
            : Promise.resolve(null),
          taskData.payload_laui ? getCatalogItemById(taskData.payload_laui) : Promise.resolve(null),
          ...attachedConfigLauis.map((laui) => getCatalogItemById(laui)),
        ]);

      const items: typeof metadataItems = {};

      if (operatorResult.status === 'fulfilled' && operatorResult.value) {
        items.operator = {
          name: operatorResult.value.name,
          itemType: operatorResult.value.item_type,
        };
      } else if (operatorResult.status === 'rejected') {
        console.error('Error fetching operator:', operatorResult.reason);
      }

      if (connectionResult.status === 'fulfilled' && connectionResult.value) {
        items.connection = {
          name: connectionResult.value.name,
          itemType: connectionResult.value.item_type,
        };
      } else if (connectionResult.status === 'rejected') {
        console.error('Error fetching connection:', connectionResult.reason);
      }

      if (payloadResult.status === 'fulfilled' && payloadResult.value) {
        items.payload = {
          name: payloadResult.value.name,
          itemType: payloadResult.value.item_type,
        };
        const pItem = payloadResult.value as any;
        const content = pItem.content ?? pItem.payload ?? pItem.data ?? null;
        setPayloadLauiContent(content);
      } else if (payloadResult.status === 'rejected') {
        console.error('Error fetching payload:', payloadResult.reason);
        setPayloadLauiContent(null);
      } else {
        setPayloadLauiContent(null);
      }

      items.attachedConfigs = attachedConfigLauis.map((laui, idx) => {
        const result = configResults[idx];
        if (result.status === 'fulfilled' && result.value) {
          return { laui, name: result.value.name, itemType: result.value.item_type };
        }
        return {
          laui,
          name: laui.length > 20 ? `...${laui.slice(-15)}` : laui,
          itemType: 'config',
        };
      });

      setMetadataItems(items);
      setPayloadLauiLoading(false);
    };

    void fetchMetadataItems();
  }, [
    taskData.operator_laui,
    taskData.connection_laui,
    taskData.payload_laui,
    taskData.attached_config_lauis,
  ]);

  // Load state color from schema config
  useEffect(() => {
    const loadStateColor = async () => {
      try {
        const config = await getProjectionFieldsConfig('task');
        if (config?.state?.enum_colors) {
          if (taskData.state) {
            const color = config.state.enum_colors[taskData.state];
            setStateColor(color || null);
          }
        }
      } catch {
        setStateColor(null);
      }
    };

    void loadStateColor();
  }, [taskData.state]);

  const handleRefreshTask = async () => {
    setIsRefreshing(true);
    try {
      const itemLaui = taskData.laui || selectedItem.laui;
      if (!itemLaui) {
        showError('No task ID found');
        return;
      }

      const refreshedData = await getCatalogItemById(itemLaui);
      // API returns {items: [{item: {...}, children, parents}], pagination}
      // Extract the actual item from the response
      let extractedItem: any = refreshedData;
      if (
        (refreshedData as any).items &&
        Array.isArray((refreshedData as any).items) &&
        (refreshedData as any).items.length > 0
      ) {
        extractedItem = (refreshedData as any).items[0].item;
      }
      setCurrentItem(extractedItem as CatalogItem);
      editorState.setViewingItem(extractedItem);
      showSuccess('Task details refreshed');
    } catch {
      /* ignore */
    } finally {
      setIsRefreshing(false);
    }
  };

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    const tabName = TAB_INDEX_TO_NAME[newValue];
    if (newValue === 4) {
      updateUrlParams({ tab: 'logs', sessionId: logsSessionId });
    } else if (tabName && tabName !== 'overview') {
      updateUrlParams({ tab: tabName, sessionId: undefined });
    } else {
      updateUrlParams({ tab: undefined, sessionId: undefined });
    }
  };

  const handleRunTaskClick = async () => {
    // Directly run the task without opening modal
    // Only send item_type and laui
    try {
      const prevIntervalStart = taskData.prev_interval_start;
      const logicalDate = taskData.logical_date;
      const resolvedLogicalDate = prevIntervalStart || logicalDate;
      const runPayload: any = {
        item_type: 'task',
        item_laui: taskData.laui || selectedItem.laui,
        ...(resolvedLogicalDate ? { logical_date: resolvedLogicalDate } : {}),
      };
      await runTask(runPayload);
      showSuccess('Task sent to execute');
      await handleRefreshTask();
    } catch {
      /* ignore */
    }
  };

  const handleCancelTaskClick = async () => {
    try {
      const taskLaui = taskData.laui || selectedItem.laui;
      await cancelTask(taskLaui);
      showSuccess('Task cancellation requested');
      await handleRefreshTask();
    } catch {
      /* ignore */
    }
  };

  const handleDangerouslyReset = async () => {
    setIsResetting(true);
    try {
      const taskLaui = taskData.laui || selectedItem.laui;
      await dangerouslyResetTask(taskLaui);
      showSuccess('Task has been dangerously reset to scheduled');
      setDangerousResetModalOpen(false);
      await handleRefreshTask();
    } catch {
      /* ignore */
    } finally {
      setIsResetting(false);
    }
  };

  const handleDiagnoseTask = async () => {
    setDiagnosticModalOpen(true);
    setIsDiagnosing(true);
    setDiagnosticData(null);
    try {
      const taskLaui = taskData.laui || selectedItem.laui;
      const result = await diagnoseTask(taskLaui);
      setDiagnosticData(result);
    } catch {
      setDiagnosticModalOpen(false);
    } finally {
      setIsDiagnosing(false);
    }
  };

  const handleAdhocRunTaskClick = () => {
    openTaskModal(TaskModalMode.RUN);
  };

  const handleScheduleTaskClick = () => {
    openTaskModal(TaskModalMode.SCHEDULE);
  };

  const handleEditTaskClick = () => {
    openTaskModal(TaskModalMode.EDIT);
  };

  const { setTaskModalState } = useTaskModalContext();

  const openTaskModal = (taskModalMode: TaskModalMode) => {
    const operatorLaui = taskData.operator_laui;
    const serializePayload = (p: any) => (typeof p === 'string' ? p : JSON.stringify(p, null, 2));
    const payloadValue = taskData.payload ? serializePayload(taskData.payload) : undefined;
    const initialTaskData = {
      laui: taskData.laui || '',
      name: taskData.name || '',
      description: taskData.description || '',
      account_laui: taskData.account_laui || '',
      project_laui: taskData.project_laui || '',
      workflow_laui: taskData.parent_laui || taskData.workflow_laui || '',
      operator_laui: taskData.operator_laui || '',
      connection_laui: taskData.connection_laui || '',
      payload: taskData.payload ? serializePayload(taskData.payload) : '',
      payload_laui: taskData.payload_laui || undefined,
      config: taskData.config ? JSON.stringify(taskData.config, null, 2) : '',
      attached_config_lauis: taskData.attached_config_lauis || taskData.attached_config_laui || [],
      actions: taskData.actions || undefined,
      partition: taskData.partition,
      frequency: taskData.frequency || undefined,
      start_date: taskData.start_date || undefined,
      end_date: taskData.end_date || undefined,
    };

    setTaskModalState({
      isOpen: true,
      mode: taskModalMode,
      scope: {
        scopeType: TaskModalScopeType.TASK,
        operatorLaui,
        payloadValue,
      },
      initialTaskData,
      onSuccess: () => void handleRefreshTask(),
    });
  };

  // Prepare Monaco field structure for payload and config
  const monacoField = {
    editorMonacoFormat: 'json',
    fontSize: 12,
    minimap: true,
    wordWrap: true,
    lineNumbers: true,
  };

  // Parse actions into pre/running/post
  const actionsData = taskData.actions || {};
  const preActions = actionsData.pre_actions || actionsData.pre || [];
  const runningActions = actionsData.running_actions || actionsData.running || [];
  const postActions = actionsData.post_actions || actionsData.post || [];

  // Merge actions_status for display
  const actionsStatusData = taskData.actions_status || {};
  const getActionStatus = (sectionKey: string, actionName: string): string | null => {
    const statusEntries = actionsStatusData[sectionKey] || [];
    const entry = statusEntries.find((e: any) => e.name === actionName);
    return entry ? entry.status : null;
  };

  // Copy output to clipboard
  const handleCopyOutput = () => {
    const outputText = formatJSON(taskData.last_run_output);
    void navigator.clipboard.writeText(outputText).then(() => {
      setOutputCopied(true);
      setTimeout(() => setOutputCopied(false), 2000);
    });
  };

  // ── Render helpers ──

  const renderMetadataLink = (
    laui: string | null | undefined,
    resolvedItem: { name: string; itemType: string } | undefined,
    fallbackLabel: string,
  ) => {
    if (!laui)
      return (
        <Typography component="span" sx={styles.metadataValue}>
          N/A
        </Typography>
      );
    if (resolvedItem) {
      return (
        <Tooltip title={resolvedItem.name} placement="top">
          <RouterLink
            to="/path"
            search={{
              itemtype: resolvedItem.itemType,
              itemname: resolvedItem.name,
              laui: laui,
            }}
            style={{
              color: 'var(--accent)',
              textDecoration: 'none',
              fontSize: FONT_SIZES.XS,
              fontWeight: FONT_WEIGHTS.WEIGHT_500,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              maxWidth: 130,
              display: 'block',
            }}
          >
            {resolvedItem.name}
          </RouterLink>
        </Tooltip>
      );
    }
    return (
      <Typography component="span" sx={styles.metadataValue}>
        {fallbackLabel}
      </Typography>
    );
  };

  const renderActionItem = (action: any, _index: number, sectionKey?: string) => {
    const name =
      typeof action === 'string' ? action : action.name || action.action_name || 'unknown';
    const statusFromActions = sectionKey ? getActionStatus(sectionKey, name) : null;
    const status =
      statusFromActions || (typeof action === 'string' ? null : action.status || action.state);
    const isSuccess = status === 'success' || status === 'completed';
    const isFailed = status === 'failed' || status === 'error' || status === 'fail';

    // Match action name to its latest log file (latest_<name>.log)
    const logFile = latestActionFiles.find((f) => {
      const fileLabel = f.name.replace(/^latest_/, '').replace(/\.log$/, '');
      return fileLabel === name || name.includes(fileLabel) || fileLabel.includes(name);
    });

    const tooltipText = logFile
      ? `${status || 'pending'} — click to view action logs`
      : status || 'pending';

    return (
      <Box key={`${name}-${_index}`} sx={styles.actionItem}>
        <Typography
          sx={{
            fontSize: FONT_SIZES.XS,
            color: 'var(--text-primary)',
            flex: 1,
            minWidth: 0,
            overflow: 'hidden',
            textOverflow: 'ellipsis',
            whiteSpace: 'nowrap',
          }}
        >
          {name}
        </Typography>
        <Tooltip title={tooltipText} placement="left" arrow>
          <Box
            onClick={logFile ? () => setActionLogFile(logFile) : undefined}
            sx={{
              width: 18,
              height: 18,
              borderRadius: '50%',
              bgcolor: isSuccess ? '#4ade80' : isFailed ? '#f87171' : 'var(--text-dim)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
              cursor: logFile ? 'pointer' : 'default',
              transition: 'transform 0.1s, opacity 0.1s',
              '&:hover': logFile ? { opacity: 0.75, transform: 'scale(1.15)' } : {},
            }}
          >
            {isSuccess && <CheckIcon sx={{ fontSize: 12, color: '#fff' }} />}
            {isFailed && <CloseIcon sx={{ fontSize: 12, color: '#fff' }} />}
          </Box>
        </Tooltip>
      </Box>
    );
  };

  // Count success/failure in a section
  const getActionCounts = (actions: any[], sectionKey: string) => {
    let success = 0;
    let failed = 0;
    actions.forEach((action, idx) => {
      const name =
        typeof action === 'string' ? action : action.name || action.action_name || `action_${idx}`;
      const statusFromActions = getActionStatus(sectionKey, name);
      const status =
        statusFromActions || (typeof action === 'string' ? null : action.status || action.state);
      if (status === 'success' || status === 'completed') success++;
      else if (status === 'failed' || status === 'error' || status === 'fail') failed++;
    });
    return { success, failed };
  };

  // ── Button style (shared) ──
  const actionButtonSx = {
    borderColor: 'var(--border)',
    color: 'var(--text-primary)',
    textTransform: 'none',
    fontSize: BUTTON_SIZES.FONT_SIZE,
    fontWeight: BUTTON_SIZES.FONT_WEIGHT,
    height: BUTTON_SIZES.HEIGHT,
    padding: BUTTON_SIZES.PADDING,
    borderRadius: BUTTON_SIZES.BORDER_RADIUS,
    whiteSpace: 'nowrap',
    '& .MuiSvgIcon-root': { fontSize: BUTTON_SIZES.ICON_FONT_SIZE },
    '&:hover': { borderColor: 'var(--accent)' },
  };

  return (
    <>
      <Box sx={styles.container}>
        {/* ── Header ── */}
        <Box sx={styles.header}>
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: '1fr auto',
              alignItems: 'start',
              width: '100%',
              gap: 2,
            }}
          >
            <Box sx={{ minWidth: 0 }}>
              <Box sx={styles.headerTitle}>
                <Typography
                  ref={nameRef}
                  sx={{
                    ...styles.title,
                    wordBreak: 'break-word',
                    ...(!nameExpanded && {
                      overflow: 'hidden',
                      textOverflow: 'ellipsis',
                      display: '-webkit-box',
                      WebkitLineClamp: 2,
                      WebkitBoxOrient: 'vertical',
                    }),
                  }}
                >
                  {taskData.name || 'Unnamed Task'}
                </Typography>
                {(nameTruncated || nameExpanded) && (
                  <Box
                    component="span"
                    onClick={() => setNameExpanded(!nameExpanded)}
                    sx={{
                      color: 'var(--text-link, #1976d2)',
                      cursor: 'pointer',
                      fontSize: FONT_SIZES.SM,
                      fontWeight: FONT_WEIGHTS.SEMIBOLD,
                      whiteSpace: 'nowrap',
                      flexShrink: 0,
                    }}
                  >
                    {nameExpanded ? 'View less' : 'View more'}
                  </Box>
                )}
                <Tooltip title={nameCopied ? 'Copied!' : 'Copy name'}>
                  <IconButton
                    size="small"
                    onClick={() => {
                      void navigator.clipboard.writeText(taskData.name || '');
                      setNameCopied(true);
                      setTimeout(() => setNameCopied(false), 2000);
                    }}
                    sx={{ color: 'var(--text-secondary)', flexShrink: 0 }}
                  >
                    {nameCopied ? (
                      <CheckIcon fontSize="small" />
                    ) : (
                      <ContentCopyIcon fontSize="small" />
                    )}
                  </IconButton>
                </Tooltip>
              </Box>
            </Box>
            <Box
              sx={{
                display: 'flex',
                flexDirection: 'column',
                alignItems: 'flex-end',
                gap: 1,
                flexShrink: 0,
              }}
            >
              {!taskData.deleted_at && (
                <Box
                  sx={{
                    display: 'flex',
                    flexWrap: 'wrap',
                    gap: 1,
                    justifyContent: 'flex-end',
                    width: 520,
                  }}
                >
                  <Button
                    onClick={handleEditTaskClick}
                    size="small"
                    variant="outlined"
                    startIcon={<EditIcon />}
                    sx={actionButtonSx}
                  >
                    Edit
                  </Button>
                  <Button
                    onClick={() => void handleRunTaskClick()}
                    size="small"
                    variant="outlined"
                    startIcon={<PlayArrowIcon />}
                    sx={actionButtonSx}
                  >
                    Run Task
                  </Button>
                  <Button
                    onClick={handleAdhocRunTaskClick}
                    size="small"
                    variant="outlined"
                    startIcon={<ScheduleIcon />}
                    sx={actionButtonSx}
                  >
                    Adhoc Run Task
                  </Button>
                  <Button
                    onClick={handleScheduleTaskClick}
                    size="small"
                    variant="outlined"
                    startIcon={<ScheduleIcon />}
                    sx={actionButtonSx}
                  >
                    Schedule Task
                  </Button>
                  <Button
                    onClick={() => void handleCancelTaskClick()}
                    size="small"
                    variant="outlined"
                    startIcon={<StopIcon />}
                    sx={{
                      ...actionButtonSx,
                      borderColor: '#f87171',
                      color: '#f87171',
                      '&:hover': {
                        borderColor: '#ef4444',
                        bgcolor: 'rgba(248,113,113,0.08)',
                      },
                    }}
                  >
                    Cancel Task
                  </Button>
                  <Tooltip title="Forcefully remove from connection queue and reset to scheduled">
                    <Button
                      onClick={() => setDangerousResetModalOpen(true)}
                      size="small"
                      variant="outlined"
                      startIcon={<WarningAmberIcon />}
                      sx={{
                        ...actionButtonSx,
                        borderColor: '#ef4444',
                        color: '#ef4444',
                        '&:hover': {
                          borderColor: '#dc2626',
                          bgcolor: 'rgba(239,68,68,0.08)',
                        },
                      }}
                    >
                      Dangerously Reset
                    </Button>
                  </Tooltip>
                  <Tooltip title="Why hasn't my task run?">
                    <Button
                      onClick={() => void handleDiagnoseTask()}
                      size="small"
                      variant="outlined"
                      startIcon={<HelpOutlineIcon />}
                      sx={{
                        ...actionButtonSx,
                        borderColor: '#f59e0b',
                        color: '#f59e0b',
                        '&:hover': {
                          borderColor: '#d97706',
                          bgcolor: 'rgba(245,158,11,0.08)',
                        },
                      }}
                    >
                      Diagnose
                    </Button>
                  </Tooltip>
                  <IconButton
                    onClick={() => void handleRefreshTask()}
                    disabled={isRefreshing}
                    size="small"
                    sx={{
                      color: 'var(--text-primary)',
                      '&:hover': { bgcolor: 'var(--bg-primary)' },
                    }}
                    title="Refresh task details"
                  >
                    {isRefreshing ? (
                      <CircularProgress size={20} sx={{ color: 'var(--accent)' }} />
                    ) : (
                      <RefreshIcon />
                    )}
                  </IconButton>
                </Box>
              )}
            </Box>
          </Box>
          <Typography sx={{ ...styles.subtitle, display: 'block', width: '100%' }}>
            {(() => {
              const desc = taskData.description || 'No description';
              const maxLen = 200;
              if (desc.length <= maxLen || descExpanded) {
                return (
                  <>
                    {desc}
                    {desc.length > maxLen && (
                      <Box
                        component="span"
                        onClick={() => setDescExpanded(false)}
                        sx={{
                          color: 'var(--text-link, #1976d2)',
                          cursor: 'pointer',
                          ml: 0.5,
                          fontWeight: FONT_WEIGHTS.SEMIBOLD,
                          whiteSpace: 'nowrap',
                        }}
                      >
                        View less
                      </Box>
                    )}
                  </>
                );
              }
              return (
                <>
                  {desc.slice(0, maxLen)}…
                  <Box
                    component="span"
                    onClick={() => setDescExpanded(true)}
                    sx={{
                      color: 'var(--text-link, #1976d2)',
                      cursor: 'pointer',
                      ml: 0.5,
                      fontWeight: FONT_WEIGHTS.SEMIBOLD,
                      whiteSpace: 'nowrap',
                    }}
                  >
                    View more
                  </Box>
                </>
              );
            })()}
          </Typography>
        </Box>

        {/* ── Tabs ── */}
        <Box sx={styles.tabsContainer}>
          <Tabs value={tabValue} onChange={handleTabChange} sx={styles.tabs}>
            <Tab label="Overview" />
            <Tab label="Payload" />
            <Tab label="Config" />
            <Tab label="Actions" />
            <Tab label="Logs/Output" />
            <Tab label="Analytics" />
          </Tabs>
        </Box>

        {/* ── Tab Panels ── */}

        {/* Overview Tab */}
        <TabPanel value={tabValue} index={0}>
          <Box sx={styles.content}>
            {/* ── Status bar: pills + inline metrics ── */}
            <Box
              sx={{
                display: 'flex',
                alignItems: 'center',
                gap: 0.75,
                mb: 1.5,
                flexWrap: 'wrap',
              }}
            >
              {/* State pill */}
              <Box
                sx={{
                  display: 'inline-flex',
                  alignItems: 'center',
                  gap: 0.75,
                  px: 1.125,
                  py: 0.375,
                  borderRadius: '6px',
                  bgcolor: stateColor ? `${stateColor}18` : 'var(--bg-secondary)',
                  border: '1px solid',
                  borderColor: stateColor || 'var(--border)',
                  flexShrink: 0,
                }}
              >
                <Box
                  sx={{
                    width: 7,
                    height: 7,
                    borderRadius: '50%',
                    bgcolor: stateColor || 'var(--text-dim)',
                    flexShrink: 0,
                  }}
                />
                <Typography
                  sx={{
                    fontSize: FONT_SIZES.XS,
                    fontWeight: FONT_WEIGHTS.WEIGHT_700,
                    color: stateColor || 'var(--text-primary)',
                    textTransform: 'uppercase',
                    letterSpacing: LETTER_SPACING.WIDE,
                  }}
                >
                  {taskData.state || 'N/A'}
                </Typography>
              </Box>

              {/* Scheduler health pill — click to navigate to project scheduler tab */}
              {schedulerStatus && taskData.project_laui && (
                <Tooltip title="Go to project scheduler" placement="bottom" arrow>
                  <Box
                    onClick={() => {
                      void getCatalogItemById(taskData.project_laui).then((projectItem) => {
                        catalogState.setSelectedItem(projectItem as any);
                        markNavigatedInAppRef.current?.(projectItem.laui);
                        void navigate({
                          to: '/path',
                          search: {
                            laui: projectItem.laui,
                            itemtype: projectItem.item_type,
                            itemname: projectItem.name,
                            tab: 'scheduler',
                          },
                        });
                      });
                    }}
                    sx={{
                      display: 'inline-flex',
                      alignItems: 'center',
                      gap: 0.5,
                      px: 1,
                      py: 0.375,
                      borderRadius: '6px',
                      border: '1px solid',
                      borderColor:
                        schedulerStatus === 'RUNNING'
                          ? '#16a34a'
                          : schedulerStatus === 'UNHEALTHY'
                            ? '#ef4444'
                            : 'var(--border)',
                      bgcolor:
                        schedulerStatus === 'RUNNING'
                          ? '#16a34a18'
                          : schedulerStatus === 'UNHEALTHY'
                            ? '#ef444418'
                            : 'var(--bg-secondary)',
                      color:
                        schedulerStatus === 'RUNNING'
                          ? '#16a34a'
                          : schedulerStatus === 'UNHEALTHY'
                            ? '#ef4444'
                            : 'var(--text-dim)',
                      flexShrink: 0,
                      cursor: 'pointer',
                      '&:hover': { opacity: 0.75 },
                    }}
                  >
                    <Box
                      sx={{
                        width: 5,
                        height: 5,
                        borderRadius: '50%',
                        bgcolor: 'currentColor',
                        ...(schedulerStatus === 'RUNNING' && {
                          animation: 'pulse 2s infinite',
                        }),
                      }}
                    />
                    <Typography
                      sx={{
                        fontSize: FONT_SIZES.XXS,
                        fontWeight: FONT_WEIGHTS.WEIGHT_600,
                        textTransform: 'uppercase',
                        letterSpacing: LETTER_SPACING.WIDE,
                        color: 'inherit',
                      }}
                    >
                      {schedulerStatus === 'RUNNING'
                        ? 'Scheduler On'
                        : schedulerStatus === 'UNHEALTHY'
                          ? 'Unhealthy'
                          : 'Scheduler Off'}
                    </Typography>
                  </Box>
                </Tooltip>
              )}

              {/* Dot separator */}
              <Typography
                sx={{
                  color: 'var(--border)',
                  fontSize: FONT_SIZES.BASE,
                  lineHeight: 1,
                  flexShrink: 0,
                  userSelect: 'none',
                }}
              >
                ·
              </Typography>

              {/* Inline metrics — label dim, value bold, dot-separated, all with tooltips */}
              {(
                [
                  {
                    label: 'Last run',
                    value: taskData.last_run_date
                      ? formatDateCompact(taskData.last_run_date)
                      : 'N/A',
                    tooltip: `Wall-clock time of the most recent execution attempt (${tzLabel})\nFull: ${taskData.last_run_date ? formatDate(taskData.last_run_date) : 'N/A'}`,
                  },
                  {
                    label: 'Duration',
                    value: formatDuration(taskData.duration),
                    mono: true,
                    tooltip:
                      'How long the last execution took (wall-clock). Does not include queue wait time.',
                  },
                  {
                    label: 'Retries',
                    value: `${taskData.retry_number ?? 0} / ${taskData.total_retries ?? 0}`,
                    mono: true,
                    tooltip: `Retry attempt / max allowed. Interval between retries: ${formatRetryInterval(taskData.retry_interval)}. Resets to 0 on success.`,
                  },
                  {
                    label: 'Priority',
                    value: String(taskData.priority || 1),
                    accent: true,
                    tooltip:
                      'Queue execution priority — higher value means picked from the queue before lower-priority tasks.',
                  },
                  ...(taskData.start_date
                    ? [
                        {
                          label: 'Start',
                          value: formatDateCompact(taskData.start_date),
                          tooltip: `Task activation date — will not run before this date (${tzLabel})\nFull: ${formatDate(taskData.start_date)}`,
                        },
                      ]
                    : []),
                  {
                    label: 'End',
                    value: taskData.end_date ? formatDateCompact(taskData.end_date) : 'N/A',
                    warn: !!(taskData.end_date && new Date(taskData.end_date) < new Date()),
                    tooltip: taskData.end_date
                      ? `Task expiry date — will not run after this date (${tzLabel})\nFull: ${formatDate(taskData.end_date)}`
                      : 'No end date set',
                  },
                  ...(taskData.task_reschedule_count > 0
                    ? [
                        {
                          label: 'Reschedules',
                          value: String(taskData.task_reschedule_count),
                          warn: true,
                          tooltip:
                            'Number of times this task was dequeued but could not execute (e.g. connection busy, pre-condition unmet). High counts indicate queue congestion or a blocking dependency.',
                        },
                      ]
                    : []),
                  ...(taskData.iteration
                    ? [
                        {
                          label: 'Iteration',
                          value: String(taskData.iteration),
                          mono: true,
                          tooltip:
                            'Total executions of this task across all runs and retries. Useful for tracking backfill progress — each successful backfill date advances this counter.',
                        },
                      ]
                    : []),
                  ...(!taskData.can_retry &&
                  (taskData.state === 'ERROR' || taskData.state === 'FAIL')
                    ? [
                        {
                          label: 'Can retry',
                          value: 'No',
                          error: true,
                          tooltip:
                            'This task has exhausted all retry attempts or retries are disabled. Manual intervention required.',
                        },
                      ]
                    : []),
                  ...(taskData.user_set_state
                    ? [
                        {
                          label: 'User state',
                          value: taskData.user_set_state,
                          italic: true,
                          tooltip:
                            'State manually set by a user — overrides the automatic scheduler state.',
                        },
                      ]
                    : []),
                ] as Array<{
                  label: string;
                  value: string;
                  mono?: boolean;
                  accent?: boolean;
                  italic?: boolean;
                  warn?: boolean;
                  error?: boolean;
                  tooltip?: string;
                }>
              ).map((stat, i, arr) => (
                <Tooltip key={i} title={stat.tooltip || ''} placement="bottom" arrow>
                  <Box
                    sx={{
                      display: 'flex',
                      alignItems: 'baseline',
                      gap: 0.5,
                      flexShrink: 0,
                      cursor: 'help',
                    }}
                  >
                    <Typography
                      component="span"
                      sx={{
                        fontSize: FONT_SIZES.XS,
                        color: 'var(--text-dim)',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {stat.label}
                    </Typography>
                    <Typography
                      component="span"
                      sx={{
                        fontSize: FONT_SIZES.XS,
                        fontWeight: FONT_WEIGHTS.WEIGHT_700,
                        color: stat.error
                          ? '#ef4444'
                          : stat.warn
                            ? '#f59e0b'
                            : stat.accent
                              ? 'var(--accent)'
                              : 'var(--text-primary)',
                        fontFamily: stat.mono ? FONT_FAMILIES.MONOSPACE : 'inherit',
                        fontStyle: stat.italic ? 'italic' : 'normal',
                        whiteSpace: 'nowrap',
                      }}
                    >
                      {stat.value}
                    </Typography>
                    {i < arr.length - 1 && (
                      <Typography
                        component="span"
                        sx={{
                          color: 'var(--border)',
                          fontSize: FONT_SIZES.BASE,
                          lineHeight: 1,
                          ml: 0.25,
                          userSelect: 'none',
                        }}
                      >
                        ·
                      </Typography>
                    )}
                  </Box>
                </Tooltip>
              ))}
            </Box>

            {/* ── Main 2-column grid ── */}
            <Box sx={styles.overviewGrid}>
              {/* LEFT COLUMN: Identity + System */}
              <Box sx={styles.leftColumn}>
                {/* Identity */}
                <Box sx={styles.card}>
                  <Box sx={styles.sectionHeader}>
                    <Box
                      sx={{
                        ...styles.sectionDot,
                        bgcolor: stateColor || 'var(--accent)',
                      }}
                    />
                    <Typography sx={styles.sectionHeaderText}>Identity</Typography>
                  </Box>
                  <Box sx={styles.metadataRow}>
                    <Typography sx={styles.metadataLabel}>LAUI</Typography>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <Tooltip title={taskData.laui || ''} placement="top">
                        <Typography
                          sx={{
                            ...styles.metadataValue,
                            fontFamily: FONT_FAMILIES.MONOSPACE,
                            fontSize: '10px',
                          }}
                        >
                          {taskData.laui ? `…${taskData.laui.slice(-10)}` : 'N/A'}
                        </Typography>
                      </Tooltip>
                      {taskData.laui && (
                        <Tooltip title="Copy LAUI">
                          <IconButton
                            size="small"
                            sx={{ p: 0.25, color: 'var(--text-dim)' }}
                            onClick={() => void navigator.clipboard.writeText(taskData.laui)}
                          >
                            <ContentCopyIcon sx={{ fontSize: 10 }} />
                          </IconButton>
                        </Tooltip>
                      )}
                    </Box>
                  </Box>
                  <Box sx={styles.metadataRow}>
                    <Typography sx={styles.metadataLabel}>Partition</Typography>
                    <Chip
                      label={taskData.partition || 'ALL'}
                      size="small"
                      sx={{
                        bgcolor: 'var(--accent)',
                        color: 'var(--bg-primary)',
                        fontSize: '10px',
                        fontWeight: FONT_WEIGHTS.WEIGHT_700,
                        height: 18,
                      }}
                    />
                  </Box>
                  <Box sx={styles.metadataRow}>
                    <Typography sx={styles.metadataLabel}>Operator</Typography>
                    {renderMetadataLink(
                      taskData.operator_laui,
                      metadataItems.operator,
                      taskData.operator_laui,
                    )}
                  </Box>
                  <Box sx={styles.metadataRow}>
                    <Typography sx={styles.metadataLabel}>Connection</Typography>
                    {renderMetadataLink(
                      taskData.connection_laui,
                      metadataItems.connection,
                      taskData.connection_laui,
                    )}
                  </Box>
                  <Box sx={styles.metadataRow}>
                    <Typography sx={styles.metadataLabel}>Payload</Typography>
                    {renderMetadataLink(
                      taskData.payload_laui,
                      metadataItems.payload,
                      taskData.payload_laui,
                    )}
                  </Box>
                  <Box
                    sx={{
                      ...styles.metadataRow,
                      flexDirection: 'column',
                      alignItems: 'flex-start',
                      gap: 0.5,
                    }}
                  >
                    <Typography sx={styles.metadataLabel}>Configs</Typography>
                    {metadataItems.attachedConfigs && metadataItems.attachedConfigs.length > 0 ? (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {metadataItems.attachedConfigs.map((cfg, idx) => (
                          <Tooltip key={idx} title={cfg.laui} placement="top">
                            <RouterLink
                              to="/path"
                              search={{
                                itemtype: cfg.itemType,
                                itemname: cfg.name,
                                laui: cfg.laui,
                              }}
                              style={{ textDecoration: 'none' }}
                            >
                              <Chip
                                label={cfg.name}
                                size="small"
                                clickable
                                sx={{
                                  bgcolor: 'var(--bg-primary)',
                                  color: 'var(--accent)',
                                  fontSize: '10px',
                                  border: 1,
                                  borderColor: 'var(--border)',
                                  height: 18,
                                  cursor: 'pointer',
                                }}
                              />
                            </RouterLink>
                          </Tooltip>
                        ))}
                      </Box>
                    ) : taskData.attached_config_lauis &&
                      taskData.attached_config_lauis.length > 0 ? (
                      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5 }}>
                        {taskData.attached_config_lauis.map((configId: string, idx: number) => (
                          <Tooltip key={idx} title={configId} placement="top">
                            <Chip
                              label={configId.length > 16 ? `…${configId.slice(-12)}` : configId}
                              size="small"
                              sx={{
                                bgcolor: 'var(--bg-primary)',
                                color: 'var(--text-secondary)',
                                fontSize: '10px',
                                border: 1,
                                borderColor: 'var(--border)',
                                height: 18,
                              }}
                            />
                          </Tooltip>
                        ))}
                      </Box>
                    ) : (
                      <Typography sx={{ ...styles.metadataValue, textAlign: 'left' }}>
                        N/A
                      </Typography>
                    )}
                  </Box>
                </Box>

                {/* System */}
                <Box sx={styles.card}>
                  <Box sx={styles.sectionHeader}>
                    <MonitorIcon sx={{ fontSize: 12, color: 'var(--text-secondary)' }} />
                    <Typography sx={styles.sectionHeaderText}>System</Typography>
                  </Box>
                  <Box sx={styles.metadataRow}>
                    <Typography sx={styles.metadataLabel}>Updated</Typography>
                    <Typography sx={styles.metadataValue}>
                      {formatDate(taskData.last_system_updated_date)}
                    </Typography>
                  </Box>
                  <Box sx={styles.metadataRow}>
                    <Typography sx={styles.metadataLabel}>Heartbeat</Typography>
                    <Typography sx={styles.metadataValue}>
                      {formatDate(taskData.latest_heartbeat)}
                    </Typography>
                  </Box>
                  <Box sx={styles.metadataRow}>
                    <Typography sx={styles.metadataLabel}>Instance</Typography>
                    <Typography sx={styles.metadataValue}>
                      {taskData.project_instance || 'N/A'}
                    </Typography>
                  </Box>
                  {taskData.executor && (
                    <Box sx={styles.metadataRow}>
                      <Tooltip
                        title="Celery task ID — use this to look up the worker log directly"
                        placement="top"
                      >
                        <Typography sx={{ ...styles.metadataLabel, cursor: 'help' }}>
                          Executor
                        </Typography>
                      </Tooltip>
                      <Tooltip title={taskData.executor} placement="top">
                        <Typography
                          sx={{
                            ...styles.metadataValue,
                            fontFamily: FONT_FAMILIES.MONOSPACE,
                            fontSize: '10px',
                          }}
                        >
                          {taskData.executor.length > 12
                            ? `…${taskData.executor.slice(-10)}`
                            : taskData.executor}
                        </Typography>
                      </Tooltip>
                    </Box>
                  )}
                  <Box sx={{ pt: 0.625 }}>
                    <Typography
                      sx={{
                        fontSize: FONT_SIZES.XXS,
                        color: 'var(--text-dim)',
                        mb: 0.375,
                        textTransform: 'uppercase',
                        letterSpacing: LETTER_SPACING.WIDE,
                      }}
                    >
                      Last Session
                    </Typography>
                    <Typography
                      sx={{
                        fontSize: '10px',
                        fontFamily: FONT_FAMILIES.MONOSPACE,
                        wordBreak: 'break-all',
                        lineHeight: 1.5,
                        ...(taskData.last_run_session_id
                          ? {
                              color: 'var(--accent)',
                              cursor: 'pointer',
                              '&:hover': {
                                textDecoration: 'underline',
                              },
                            }
                          : { color: 'var(--text-dim)' }),
                      }}
                      onClick={
                        taskData.last_run_session_id
                          ? () => {
                              setLogsSessionId(taskData.last_run_session_id);
                              setTabValue(4);
                              updateUrlParams({
                                tab: 'logs',
                                sessionId: taskData.last_run_session_id,
                              });
                            }
                          : undefined
                      }
                    >
                      {taskData.last_run_session_id || 'N/A'}
                    </Typography>
                  </Box>
                </Box>

                {/* Actions */}
                <Box sx={{ ...styles.card, p: 0, overflow: 'hidden' }}>
                  {[
                    { label: 'Pre', color: '#fbbf24', actions: preActions, key: 'pre_actions' },
                    {
                      label: 'Running',
                      color: '#4ade80',
                      actions: runningActions,
                      key: 'running_actions',
                    },
                    { label: 'Post', color: '#f87171', actions: postActions, key: 'post_actions' },
                  ].map((col, colIdx, arr) => {
                    const counts = getActionCounts(col.actions, col.key);
                    return (
                      <Box
                        key={col.key}
                        sx={{
                          borderBottom: colIdx < arr.length - 1 ? 1 : 0,
                          borderColor: 'var(--border)',
                          display: 'flex',
                          flexDirection: 'column',
                        }}
                      >
                        <Box sx={styles.actionColumnHeader}>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
                            <Box sx={{ ...styles.sectionDot, bgcolor: col.color }} />
                            <Typography
                              sx={{
                                fontSize: '10px',
                                fontWeight: FONT_WEIGHTS.WEIGHT_600,
                                color: 'var(--text-secondary)',
                                textTransform: 'uppercase',
                                letterSpacing: LETTER_SPACING.WIDE,
                              }}
                            >
                              {col.label}
                            </Typography>
                          </Box>
                          <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                            {counts.success > 0 && (
                              <Chip
                                label={`${counts.success}`}
                                size="small"
                                sx={{
                                  bgcolor: '#4ade80',
                                  color: '#fff',
                                  fontSize: '10px',
                                  height: 16,
                                  minWidth: 16,
                                  fontWeight: 700,
                                  '& .MuiChip-label': { px: 0.5 },
                                }}
                              />
                            )}
                            {counts.failed > 0 && (
                              <Chip
                                label={`${counts.failed}`}
                                size="small"
                                sx={{
                                  bgcolor: '#f87171',
                                  color: '#fff',
                                  fontSize: '10px',
                                  height: 16,
                                  minWidth: 16,
                                  fontWeight: 700,
                                  '& .MuiChip-label': { px: 0.5 },
                                }}
                              />
                            )}
                            <Chip
                              label={col.actions.length}
                              size="small"
                              sx={{
                                bgcolor: 'var(--bg-primary)',
                                color: 'var(--text-secondary)',
                                fontSize: '10px',
                                height: 16,
                                minWidth: 16,
                                '& .MuiChip-label': { px: 0.5 },
                              }}
                            />
                          </Box>
                        </Box>
                        <Box sx={styles.actionColumnBody}>
                          {col.actions.map((action: any, idx: number) =>
                            renderActionItem(action, idx, col.key),
                          )}
                          {col.actions.length === 0 && (
                            <Box sx={{ p: 1.5 }}>
                              <Typography
                                sx={{ fontSize: FONT_SIZES.XS, color: 'var(--text-dim)' }}
                              >
                                None
                              </Typography>
                            </Box>
                          )}
                        </Box>
                      </Box>
                    );
                  })}
                </Box>
              </Box>

              {/* RIGHT COLUMN: Schedule, Timeline, Output */}
              <Box sx={styles.rightColumn}>
                {/* Schedule + Retry */}
                <Box sx={styles.card}>
                  <Box
                    sx={{
                      display: 'flex',
                      justifyContent: 'space-between',
                      alignItems: 'flex-start',
                      gap: 2,
                    }}
                  >
                    <Box sx={{ flex: 1 }}>
                      <Box sx={styles.sectionHeader}>
                        <ScheduleIcon sx={{ fontSize: 12, color: 'var(--accent)' }} />
                        <Typography sx={styles.sectionHeaderText}>Schedule</Typography>
                      </Box>
                      <Box sx={styles.metadataRow}>
                        <Tooltip
                          title={`The data period this task is computing — same concept as Airflow's logical_date (formerly execution_date pre-2.2). Floored to cron granularity (daily → midnight, monthly → 1st of month, 5-min → exact cron tick). Available as {{ds}} or {{logical_date}} in payloads. In ${tzLabel}.`}
                          placement="top"
                        >
                          <Typography
                            sx={{
                              ...styles.metadataLabel,
                              cursor: 'help',
                            }}
                          >
                            Logical Date ({tzLabel})
                          </Typography>
                        </Tooltip>
                        <Typography
                          sx={{
                            ...styles.metadataValue,
                            color: 'var(--accent)',
                            fontFamily: FONT_FAMILIES.MONOSPACE,
                            maxWidth: 240,
                          }}
                        >
                          {taskData.logical_date ? formatDate(taskData.logical_date) : 'N/A'}
                        </Typography>
                      </Box>
                      {taskData.frequency && taskData.frequency !== 'ADHOC' && (
                        <Box sx={styles.metadataRow}>
                          <Tooltip
                            title={`Scheduler trigger date (${tzLabel}) — when next_run_date ≤ wall clock, the cron dispatches this task (pre-actions then operator). Advances one cron interval from the previous next_run_date, not from the physical run time. This enables automatic catch-up: a scheduler that was down will immediately dispatch consecutive runs until next_run_date > now.`}
                            placement="top"
                          >
                            <Typography
                              sx={{
                                ...styles.metadataLabel,
                                cursor: 'help',
                              }}
                            >
                              Next Run ({tzLabel})
                            </Typography>
                          </Tooltip>
                          {(() => {
                            const isOverdue =
                              taskData.next_run_date &&
                              new Date(taskData.next_run_date) < new Date() &&
                              (taskData.state === 'error' ||
                                taskData.state === 'ERROR' ||
                                taskData.state === 'fail' ||
                                taskData.state === 'FAIL');
                            return (
                              <Tooltip
                                title={
                                  taskData.next_run_date
                                    ? formatDate(taskData.next_run_date)
                                    : 'Not set'
                                }
                                placement="top"
                              >
                                <Typography
                                  sx={{
                                    ...styles.metadataValue,
                                    fontFamily: FONT_FAMILIES.MONOSPACE,
                                    maxWidth: 240,
                                    color: isOverdue ? '#ef4444' : 'var(--text-primary)',
                                  }}
                                >
                                  {taskData.next_run_date
                                    ? formatDateCompact(taskData.next_run_date)
                                    : 'N/A'}
                                </Typography>
                              </Tooltip>
                            );
                          })()}
                        </Box>
                      )}
                      <Box sx={styles.metadataRow}>
                        <Tooltip
                          title="Retry policy: maximum attempts and wait interval between retries"
                          placement="top"
                        >
                          <Typography
                            sx={{
                              ...styles.metadataLabel,
                              cursor: 'help',
                            }}
                          >
                            Retry
                          </Typography>
                        </Tooltip>
                        <Typography
                          sx={{
                            ...styles.metadataValue,
                            color: 'var(--text-secondary)',
                            maxWidth: 240,
                          }}
                        >
                          max {taskData.total_retries || 0} · every{' '}
                          {formatRetryInterval(taskData.retry_interval)}
                        </Typography>
                      </Box>
                    </Box>
                    {/* Cron expression */}
                    <Box sx={{ textAlign: 'right', flexShrink: 0 }}>
                      <Typography
                        sx={{
                          fontSize: FONT_SIZES.XXS,
                          color: 'var(--text-dim)',
                          mb: 0.375,
                          textTransform: 'uppercase',
                          letterSpacing: LETTER_SPACING.WIDE,
                        }}
                      >
                        Cron
                      </Typography>
                      <Typography
                        sx={{
                          fontSize: '1.125rem',
                          fontWeight: FONT_WEIGHTS.BOLD,
                          color: 'var(--text-primary)',
                          fontFamily: FONT_FAMILIES.MONOSPACE,
                          letterSpacing: LETTER_SPACING.WIDE,
                        }}
                      >
                        {taskData.frequency || 'ADHOC'}
                      </Typography>
                    </Box>
                  </Box>
                </Box>

                {/* Timeline */}
                <Box sx={styles.card}>
                  <Box sx={styles.sectionHeader}>
                    <CalendarMonthIcon sx={{ fontSize: 12, color: 'var(--text-secondary)' }} />
                    <Typography sx={styles.sectionHeaderText}>Timeline</Typography>
                  </Box>
                  {(
                    [
                      {
                        label: 'Window',
                        tooltip: `Scheduled run window (${tzLabel}) — task only dispatches within this date range`,
                        start: taskData.start_date,
                        end: taskData.end_date,
                        expired: !!(taskData.end_date && new Date(taskData.end_date) < new Date()),
                      },
                      {
                        label: 'Data Interval',
                        tooltip: `Data interval (${tzLabel}) set at the start of this task run — the data slice being processed`,
                        start: taskData.data_interval_start,
                        end: taskData.data_interval_end,
                      },
                      {
                        label: 'Prev Interval',
                        tooltip: `Previous data interval (${tzLabel}), updated at the end of the last completed task run`,
                        start: taskData.prev_interval_start,
                        end: taskData.prev_interval_end,
                      },
                      {
                        label: 'Run Instance',
                        tooltip: `Actual wall-clock start and end times of this task execution (${tzLabel})`,
                        start: taskData.task_instance_start_date,
                        end: taskData.task_instance_end_date,
                      },
                    ] as Array<{
                      label: string;
                      tooltip: string;
                      start: any;
                      end: any;
                      expired?: boolean;
                    }>
                  ).map((row, i) => (
                    <Box
                      key={i}
                      sx={{
                        ...styles.timelineRow,
                        borderBottom: i < 3 ? 1 : 0,
                        borderColor: 'var(--border)',
                      }}
                    >
                      <Tooltip title={row.tooltip} placement="right">
                        <Typography
                          sx={{
                            ...styles.timelineLabel,
                            color: row.expired ? '#ef4444' : 'var(--text-dim)',
                          }}
                        >
                          {row.label}
                          {row.expired ? ' ⚠' : ''}
                        </Typography>
                      </Tooltip>
                      <Tooltip
                        title={`${formatDate(row.start)} – ${formatDate(row.end)}`}
                        placement="top"
                      >
                        <Typography sx={styles.timelineValue}>
                          {formatDateCompact(row.start)} – {formatDateCompact(row.end)}
                        </Typography>
                      </Tooltip>
                    </Box>
                  ))}
                </Box>

                {/* Output + Actions */}
                <Box sx={{ ...styles.card, p: 0, overflow: 'hidden' }}>
                  {/* Terminal header */}
                  <Box sx={styles.terminalHeader}>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5 }}>
                      <Box sx={styles.terminalDots}>
                        <Box
                          sx={{
                            ...styles.terminalDot,
                            bgcolor: '#f87171',
                          }}
                        />
                        <Box
                          sx={{
                            ...styles.terminalDot,
                            bgcolor: '#fbbf24',
                          }}
                        />
                        <Box
                          sx={{
                            ...styles.terminalDot,
                            bgcolor: '#4ade80',
                          }}
                        />
                      </Box>
                      <Box
                        sx={{
                          display: 'flex',
                          alignItems: 'center',
                          gap: 0.75,
                        }}
                      >
                        <MonitorIcon sx={{ fontSize: 11, color: 'var(--text-dim)' }} />
                        <Tooltip
                          title="The output message returned by the operator on success or failure of the last run. For full step-by-step execution logs, see the Logs tab."
                          placement="top"
                          arrow
                        >
                          <Typography
                            sx={{
                              fontSize: FONT_SIZES.XS,
                              color: 'var(--text-secondary)',
                              cursor: 'help',
                            }}
                          >
                            Last Run Output
                          </Typography>
                        </Tooltip>
                      </Box>
                    </Box>
                    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5 }}>
                      <Chip
                        label="READ-ONLY"
                        size="small"
                        sx={{
                          bgcolor: 'var(--bg-primary)',
                          color: 'var(--text-dim)',
                          fontSize: '10px',
                          height: 18,
                          border: 1,
                          borderColor: 'var(--border)',
                        }}
                      />
                      <Tooltip title={outputCopied ? 'Copied!' : 'Copy'}>
                        <IconButton
                          size="small"
                          onClick={handleCopyOutput}
                          sx={{ color: 'var(--text-dim)', p: 0.375 }}
                        >
                          {outputCopied ? (
                            <CheckIcon sx={{ fontSize: 13 }} />
                          ) : (
                            <ContentCopyIcon sx={{ fontSize: 13 }} />
                          )}
                        </IconButton>
                      </Tooltip>
                      <Tooltip title="Expand">
                        <IconButton
                          size="small"
                          onClick={() => setOutputExpanded(true)}
                          sx={{ color: 'var(--text-dim)', p: 0.375 }}
                        >
                          <OpenInFullIcon sx={{ fontSize: 13 }} />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </Box>

                  {/* Monaco output */}
                  {taskData.last_run_output ? (
                    <Box
                      sx={{
                        height: 150,
                        borderBottom: 1,
                        borderColor: 'var(--border)',
                      }}
                    >
                      <MonacoWrapper
                        content={formatJSON(taskData.last_run_output)}
                        field={{
                          ...monacoField,
                          minimap: false,
                          lineNumbers: true,
                        }}
                        readOnly={true}
                        height="100%"
                      />
                    </Box>
                  ) : (
                    <Box
                      sx={{
                        height: 48,
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        borderBottom: 1,
                        borderColor: 'var(--border)',
                      }}
                    >
                      <Typography
                        sx={{
                          fontSize: FONT_SIZES.XS,
                          color: 'var(--text-dim)',
                        }}
                      >
                        No output available
                      </Typography>
                    </Box>
                  )}

                  {/* Latest Action Logs — expanded by default, keyed to logical_date partition */}
                  {latestActionFiles.length > 0 && (
                    <Box sx={{ borderTop: 1, borderColor: 'var(--border)' }}>
                      <Box
                        sx={{
                          px: 1.5,
                          py: 0.75,
                          display: 'flex',
                          alignItems: 'center',
                          gap: 0.75,
                          borderBottom: 1,
                          borderColor: 'var(--border)',
                          bgcolor: 'var(--bg-tertiary)',
                        }}
                      >
                        <Typography
                          sx={{
                            fontSize: '10px',
                            fontWeight: FONT_WEIGHTS.WEIGHT_600,
                            color: 'var(--text-secondary)',
                            textTransform: 'uppercase',
                            letterSpacing: LETTER_SPACING.WIDE,
                          }}
                        >
                          Latest Action Logs
                        </Typography>
                        <Chip
                          label={latestActionFiles.length}
                          size="small"
                          sx={{
                            bgcolor: 'var(--bg-primary)',
                            color: 'var(--text-secondary)',
                            fontSize: '10px',
                            height: 16,
                            '& .MuiChip-label': { px: 0.5 },
                          }}
                        />
                      </Box>
                      {latestActionFiles.map((file) => (
                        <Box
                          key={file.name}
                          sx={{
                            borderBottom: 1,
                            borderColor: 'var(--border)',
                            '&:last-of-type': { borderBottom: 'none' },
                          }}
                        >
                          <Typography
                            sx={{
                              px: 1.5,
                              py: 0.5,
                              fontSize: FONT_SIZES.XS,
                              color: 'var(--text-dim)',
                              fontFamily: FONT_FAMILIES.MONOSPACE,
                              borderBottom: 1,
                              borderColor: 'var(--border)',
                            }}
                          >
                            {file.name.replace(/^latest_/, '').replace(/\.log$/, '')}
                          </Typography>
                          <StreamLogViewer
                            logFileUrl={file.logUrl}
                            showHeader={false}
                            showLevelFilter={false}
                            maxHeight={200}
                            paginated
                            pageSize={100}
                          />
                        </Box>
                      ))}
                    </Box>
                  )}
                </Box>
              </Box>
            </Box>
          </Box>
        </TabPanel>

        {/* Payload Tab */}
        <TabPanel value={tabValue} index={1}>
          <Box sx={styles.content}>
            {taskData.payload_laui ? (
              <>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    mb: 1,
                    p: 1,
                    bgcolor: 'var(--bg-secondary)',
                    borderRadius: 1,
                    border: 1,
                    borderColor: 'var(--border)',
                  }}
                >
                  <Typography
                    sx={{
                      fontSize: FONT_SIZES.XS,
                      color: 'var(--text-secondary)',
                    }}
                  >
                    Content of attached payload:{' '}
                    {metadataItems.payload ? (
                      <RouterLink
                        to="/path"
                        search={{
                          itemtype: metadataItems.payload.itemType,
                          itemname: metadataItems.payload.name,
                          laui: taskData.payload_laui,
                        }}
                        style={{
                          color: 'var(--accent)',
                          textDecoration: 'none',
                          fontWeight: 600,
                        }}
                      >
                        {metadataItems.payload.name}
                      </RouterLink>
                    ) : (
                      <Typography
                        component="span"
                        sx={{
                          fontFamily: 'monospace',
                          fontSize: FONT_SIZES.XS,
                          color: 'var(--accent)',
                        }}
                      >
                        {taskData.payload_laui}
                      </Typography>
                    )}{' '}
                    — config parameters are applied at runtime from source.
                  </Typography>
                </Box>
                <Box sx={styles.monacoContainer}>
                  {payloadLauiLoading ? (
                    <Box
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        height: '100%',
                      }}
                    >
                      <CircularProgress size={24} sx={{ color: 'var(--accent)' }} />
                    </Box>
                  ) : (
                    <MonacoWrapper
                      content={
                        payloadLauiContent != null
                          ? formatJSON(payloadLauiContent)
                          : '// No content found in attached payload item'
                      }
                      field={monacoField}
                      readOnly={true}
                      height="100%"
                    />
                  )}
                </Box>
              </>
            ) : (
              <>
                <Typography
                  sx={{
                    fontSize: FONT_SIZES.XS,
                    color: 'var(--text-secondary)',
                    mb: 1,
                  }}
                >
                  Inline payload — config parameters are applied at runtime.
                </Typography>
                <Box sx={styles.monacoContainer}>
                  <MonacoWrapper
                    content={formatJSON(taskData.payload)}
                    field={monacoField}
                    readOnly={true}
                    height="100%"
                  />
                </Box>
              </>
            )}
          </Box>
        </TabPanel>

        {/* Config Tab */}
        <TabPanel value={tabValue} index={2}>
          <Box sx={styles.content}>
            <FancyJsonEditor
              field={{ name: 'config', datatype: 'object' }}
              value={formatJSON(taskData.config)}
              onChange={() => {}}
              isReadOnly={true}
              mode="view"
            />
          </Box>
        </TabPanel>

        {/* Actions Tab */}
        <TabPanel value={tabValue} index={3}>
          <Box sx={styles.content}>
            <FancyJsonEditor
              field={{ name: 'actions', datatype: 'object' }}
              value={formatJSON(taskData.actions)}
              onChange={() => {}}
              isReadOnly={true}
              mode="view"
            />
          </Box>
        </TabPanel>

        {/* Logs/Output Tab */}
        <TabPanel value={tabValue} index={4}>
          <Box sx={styles.content}>
            <TaskLogsTab
              taskLaui={selectedItem.laui}
              logicalDate={taskData.logical_date}
              initialSessionId={logsSessionId}
              onSessionChange={(sessionId) => {
                updateUrlParams({ tab: 'logs', sessionId: sessionId ?? undefined });
              }}
            />
          </Box>
        </TabPanel>

        {/* Analytics Tab */}
        <TabPanel value={tabValue} index={5}>
          <Box sx={styles.content}>
            <TaskAnalyticsTab
              taskLaui={selectedItem.laui}
              logicalDate={taskData.logical_date}
              onNavigateToSession={(sessionId) => {
                setLogsSessionId(sessionId);
                setTabValue(4);
                updateUrlParams({ tab: 'logs', sessionId });
              }}
            />
          </Box>
        </TabPanel>
      </Box>

      {/* Expanded output dialog */}
      <Dialog
        open={outputExpanded}
        onClose={() => setOutputExpanded(false)}
        maxWidth="lg"
        fullWidth
        PaperProps={{ sx: { bgcolor: 'var(--bg-primary)', height: '80vh' } }}
      >
        <DialogTitle
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            borderBottom: 1,
            borderColor: 'var(--border)',
            py: 1.5,
            px: 2,
          }}
        >
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
            <Tooltip
              title="The output message returned by the operator on success or failure of the last run. For full step-by-step execution logs, see the Logs tab."
              placement="bottom"
              arrow
            >
              <Typography
                sx={{
                  fontSize: FONT_SIZES.SM,
                  fontWeight: FONT_WEIGHTS.WEIGHT_600,
                  color: 'var(--text-secondary)',
                  cursor: 'help',
                }}
              >
                Last Run Output
              </Typography>
            </Tooltip>
            <Chip
              label="READ-ONLY"
              size="small"
              sx={{
                bgcolor: 'var(--bg-secondary)',
                color: 'var(--text-dim)',
                fontSize: FONT_SIZES.XS,
                height: 20,
                border: 1,
                borderColor: 'var(--border)',
              }}
            />
          </Box>
          <IconButton
            size="small"
            onClick={() => setOutputExpanded(false)}
            sx={{ color: 'var(--text-dim)' }}
          >
            <CloseIcon sx={{ fontSize: FONT_SIZES.ICON_SM }} />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ p: 0, display: 'flex', flexDirection: 'column' }}>
          {taskData?.last_run_output ? (
            <MonacoWrapper
              content={formatJSON(taskData.last_run_output)}
              field={{ ...monacoField, minimap: false, lineNumbers: true }}
              readOnly={true}
              height="100%"
            />
          ) : (
            <Box
              sx={{
                flex: 1,
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
              }}
            >
              <Typography sx={{ fontSize: FONT_SIZES.SM, color: 'var(--text-dim)' }}>
                No output available
              </Typography>
            </Box>
          )}
        </DialogContent>
      </Dialog>

      {/* Action Log Dialog */}
      <Dialog
        open={!!actionLogFile}
        onClose={() => setActionLogFile(null)}
        maxWidth="md"
        fullWidth
        slotProps={{ paper: { sx: { bgcolor: 'var(--bg-primary)', height: '70vh' } } }}
      >
        <DialogTitle
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            py: 1.5,
            px: 2,
            borderBottom: 1,
            borderColor: 'var(--border)',
          }}
        >
          <Typography
            sx={{
              fontSize: FONT_SIZES.SM,
              fontFamily: FONT_FAMILIES.MONOSPACE,
              color: 'var(--text-primary)',
            }}
          >
            {actionLogFile?.name.replace(/^latest_/, '').replace(/\.log$/, '')}
          </Typography>
          <IconButton
            size="small"
            onClick={() => setActionLogFile(null)}
            sx={{ color: 'var(--text-dim)' }}
          >
            <CloseIcon sx={{ fontSize: FONT_SIZES.ICON_SM }} />
          </IconButton>
        </DialogTitle>
        <DialogContent sx={{ p: 0, display: 'flex', flexDirection: 'column' }}>
          {actionLogFile && (
            <StreamLogViewer
              logFileUrl={actionLogFile.logUrl}
              showHeader={false}
              maxHeight="100%"
              paginated
              pageSize={100}
            />
          )}
        </DialogContent>
      </Dialog>

      {/* Dangerously Reset Confirmation Modal */}
      <BaseModal
        open={dangerousResetModalOpen}
        onClose={() => !isResetting && setDangerousResetModalOpen(false)}
        title="Dangerously Reset Task"
        subtitle="This action cannot be undone"
        maxWidth="sm"
        actions={
          <>
            <Button
              onClick={() => setDangerousResetModalOpen(false)}
              disabled={isResetting}
              size="small"
              variant="outlined"
              sx={{
                color: 'var(--text-secondary)',
                borderColor: 'var(--border)',
                '&:hover': {
                  borderColor: 'var(--primary-main)',
                  color: 'var(--text-primary)',
                },
              }}
            >
              Cancel
            </Button>
            <Button
              onClick={() => void handleDangerouslyReset()}
              disabled={isResetting}
              size="small"
              variant="contained"
              startIcon={<WarningAmberIcon />}
              sx={{
                bgcolor: '#ef4444',
                color: '#fff',
                textTransform: 'none',
                fontWeight: 'bold',
                '&:hover': { bgcolor: '#dc2626' },
                '&:disabled': {
                  bgcolor: 'var(--bg-tertiary)',
                  color: 'var(--text-disabled)',
                },
                py: 0.5,
                px: 1.5,
              }}
            >
              {isResetting ? 'Resetting...' : 'Dangerously Reset'}
            </Button>
          </>
        }
      >
        <Box sx={{ mt: 1 }}>
          <Typography sx={{ color: 'var(--text-primary)', mb: 2 }}>
            This will forcefully remove the task <strong>{taskData.name}</strong> from the
            connection queue and reset its state to <strong>scheduled</strong>.
          </Typography>
          <Typography sx={{ color: 'var(--text-secondary)', fontSize: FONT_SIZES.SM }}>
            The task's output will be cleared and user_set_state will be reset. Use this only when a
            task is stuck in the connection queue.
          </Typography>
        </Box>
      </BaseModal>

      {/* Diagnose Task Modal */}
      <BaseModal
        open={diagnosticModalOpen}
        onClose={() => !isDiagnosing && setDiagnosticModalOpen(false)}
        title="Task Diagnostics"
        subtitle={
          diagnosticData
            ? `${diagnosticData.task_name} — ${diagnosticData.current_state}`
            : 'Analyzing task...'
        }
        loading={isDiagnosing}
        loadingText="Running diagnostic checks..."
        maxWidth="md"
        actions={
          <Button
            onClick={() => setDiagnosticModalOpen(false)}
            size="small"
            variant="outlined"
            sx={{
              color: 'var(--text-secondary)',
              borderColor: 'var(--border)',
              '&:hover': {
                borderColor: 'var(--primary-main)',
                color: 'var(--text-primary)',
              },
            }}
          >
            Close
          </Button>
        }
      >
        {diagnosticData && (
          <Box sx={{ mt: 1 }}>
            <Chip
              label={
                diagnosticData.issues_found > 0
                  ? `${diagnosticData.issues_found} issue(s) found`
                  : 'No issues found'
              }
              size="small"
              sx={{
                mb: 2,
                bgcolor:
                  diagnosticData.issues_found > 0 ? 'rgba(239,68,68,0.12)' : 'rgba(34,197,94,0.12)',
                color: diagnosticData.issues_found > 0 ? '#ef4444' : '#22c55e',
                fontWeight: 600,
              }}
            />

            {/* Detected issues */}
            {diagnosticData.diagnostics
              .filter((d) => d.detected)
              .map((diag) => {
                const severityColors: Record<string, { bg: string; border: string; text: string }> =
                  {
                    blocking: {
                      bg: 'rgba(239,68,68,0.08)',
                      border: '#ef4444',
                      text: '#ef4444',
                    },
                    warning: {
                      bg: 'rgba(245,158,11,0.08)',
                      border: '#f59e0b',
                      text: '#f59e0b',
                    },
                    info: {
                      bg: 'rgba(59,130,246,0.08)',
                      border: '#3b82f6',
                      text: '#3b82f6',
                    },
                  };
                const colors = severityColors[diag.severity] || severityColors.info;
                return (
                  <Box
                    key={diag.case_id}
                    sx={{
                      p: 1.5,
                      mb: 1,
                      borderRadius: 1,
                      bgcolor: colors.bg,
                      borderLeft: `3px solid ${colors.border}`,
                    }}
                  >
                    <Box
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1,
                        mb: 0.5,
                      }}
                    >
                      <Chip
                        label={diag.severity}
                        size="small"
                        sx={{
                          height: 20,
                          fontSize: '10px',
                          bgcolor: colors.border,
                          color: '#fff',
                          fontWeight: 600,
                        }}
                      />
                      <Typography
                        sx={{
                          fontSize: FONT_SIZES.SM,
                          fontWeight: 600,
                          color: 'var(--text-primary)',
                        }}
                      >
                        {diag.title}
                      </Typography>
                    </Box>
                    <Typography
                      sx={{
                        fontSize: FONT_SIZES.XS,
                        color: 'var(--text-secondary)',
                      }}
                    >
                      {diag.description}
                    </Typography>
                  </Box>
                );
              })}

            {/* All-clear checks (non-detected) */}
            {diagnosticData.diagnostics.filter((d) => !d.detected).length > 0 && (
              <Box sx={{ mt: 2 }}>
                <Typography
                  sx={{
                    fontSize: FONT_SIZES.XS,
                    color: 'var(--text-dim)',
                    mb: 1,
                    textTransform: 'uppercase',
                    letterSpacing: '0.05em',
                  }}
                >
                  Passed Checks
                </Typography>
                {diagnosticData.diagnostics
                  .filter((d) => !d.detected)
                  .map((diag) => (
                    <Box
                      key={diag.case_id}
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 1,
                        py: 0.5,
                      }}
                    >
                      <CheckIcon sx={{ fontSize: 14, color: '#22c55e' }} />
                      <Typography
                        sx={{
                          fontSize: FONT_SIZES.XS,
                          color: 'var(--text-secondary)',
                        }}
                      >
                        {diag.passed_title ?? diag.title}
                      </Typography>
                    </Box>
                  ))}
              </Box>
            )}
          </Box>
        )}
      </BaseModal>
    </>
  );
}
