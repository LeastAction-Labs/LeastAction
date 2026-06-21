/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import React, { useCallback, useEffect, useMemo, useState } from 'react';

import { useNavigate, useSearch } from '@tanstack/react-router';

import {
  ArrowDownward,
  ArrowDropDown,
  ArrowUpward,
  SaveAlt as CreateUsecaseIcon,
  Delete,
  FilterListOff,
  Download as ImportIcon,
  Pause,
  PlayArrow,
  Restore,
  Search as SearchIcon,
  Share,
  Storefront as StorefrontIcon,
  UnfoldMore,
  ViewColumn,
} from '@mui/icons-material';
import {
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Divider,
  FormControl,
  FormControlLabel,
  IconButton,
  InputAdornment,
  MenuItem,
  Paper,
  Popover,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  TextField,
  Toolbar,
  Tooltip,
  Typography,
} from '@mui/material';
import _ from 'lodash';

import BulkPublishUsecaseModal from '@/components/browse/modals/BulkPublishUsecaseModal';
import LAMarketplaceIcon from '@/components/marketplace/LAMarketplaceIcon/LAMarketplaceIcon';
import { Chip } from '@/components/ui';
import {
  BUTTON_SIZES,
  COLORS,
  FONT_SIZES,
  FONT_WEIGHTS,
  TASK_DEPENDENCY_GROUP_COLORS,
  TASK_STATE_COLORS,
} from '@/constants';
import { RunActionModalMode, useActionContext } from '@/contexts/ActionContext';
import { useCatalog } from '@/contexts/CatalogContext';
import { CatalogType, useGlobal } from '@/contexts/GlobalContext';
import { useNotification } from '@/contexts/NotificationContext';
import { useTimeFormat } from '@/contexts/TimeFormatContext';
import { useSidebarHandlers } from '@/screens/Browse/handlers';
import { useEditorHandlers } from '@/screens/Browse/handlers/editorHandlers';
import { usePaginationHandlers } from '@/screens/Browse/handlers/paginationHandlers';
import {
  getBreadcrumbString,
  getBreadcrumbs,
  getCatalogItemById,
  runAction,
  searchCatalogItems,
} from '@/services/catalog.service';
import type { ProjectionFieldsConfig } from '@/services/schema.service';
import {
  getItemTypeVisualConfig,
  getProjectionFieldsConfig,
  getSchemaUiPreviewFields,
} from '@/services/schema.service';
import { cancelTask, runTask, runTasks } from '@/services/task.service';
import { getIconComponent } from '@/utils/iconMapping';
import { formatDateValue as formatDateValueUtil, getTimeZoneLabel } from '@/utils/timeFormat';

import { QuickSearch } from '../../ui';
import { groupTasksByDependency } from '../Flows/WorkflowDiagram';
import Pagination from '../Pagination';
import type { CatalogItem } from '../types';
import EmptyState from './EmptyState';
import RecentRunsStrip from './RecentRunsStrip';

const PAGE_SIZE_OPTIONS = [5, 10, 25, 50, 100];

// Frontend-only virtual column showing a strip of a task's most recent runs.
// Not part of the schema preview fields — injected into the task column list.
const RUNS_COLUMN = 'recent_runs';

const styles = {
  tableContainer: {
    bgcolor: 'transparent',
    boxShadow: 'none',
    borderRadius: 0,
    '& .MuiTableCell-root': {
      color: 'var(--text-primary)',
      borderBottom: 'none',
      fontSize: FONT_SIZES.SM,
      py: 0.5,
      px: 0.25,
      '&:first-of-type': {
        pl: 1,
      },
      '&:last-of-type': {
        pr: 2,
      },
    },
  },
  taskTableContainer: {
    bgcolor: 'transparent',
    boxShadow: 'none',
    borderRadius: 0,
    '& .MuiTableCell-root': {
      color: 'var(--text-primary)',
      borderBottom: 'none',
      fontSize: FONT_SIZES.SM,
      py: 1.5,
      px: 1.5,
      '&:first-of-type': { pl: 2 },
      '&:last-of-type': { pr: 2 },
    },
  },
  tableHead: {
    bgcolor: 'var(--bg-secondary)',
    '& .MuiTableCell-root': {
      fontWeight: FONT_WEIGHTS.WEIGHT_500,
      color: 'var(--text-secondary)',
      fontSize: FONT_SIZES.SM,
    },
  },
  taskTableHead: {
    '& .MuiTableCell-root': {
      fontWeight: FONT_WEIGHTS.WEIGHT_600,
      color: 'var(--text-secondary)',
      fontSize: FONT_SIZES.XS,
      textTransform: 'uppercase',
      letterSpacing: '0.06em',
      borderBottom: '2px solid var(--border)',
      py: 1.5,
      px: 1.5,
      '&:first-of-type': { pl: 2 },
    },
  },
  tableRow: {
    transition: 'background-color 0.2s ease',
    '&:hover': {
      bgcolor: 'var(--bg-secondary)',
    },
    cursor: 'pointer',
  },
  taskTableRow: {
    cursor: 'pointer',
    '& .MuiTableCell-root': {
      borderBottom: '1px solid var(--border)',
    },
    '&:hover .MuiTableCell-root': {
      bgcolor: 'var(--bg-secondary)',
    },
    '&:last-child .MuiTableCell-root': {
      borderBottom: 'none',
    },
  },
  actionsCell: {
    width: 140,
    whiteSpace: 'nowrap',
  },
  actionButtons: {
    display: 'flex',
    gap: '4px',
    justifyContent: 'flex-end',
  },
  iconButton: {
    padding: '0px',
    '&:hover': {
      backgroundColor: 'rgba(255, 255, 255, 0.08)',
    },
  },
  editIcon: {
    color: 'var(--text-secondary)',
    '&:hover': {
      color: 'var(--warning-main)',
    },
  },
  deleteIcon: {
    color: 'var(--accent)',
    '&:hover': {
      color: 'var(--error-main)',
    },
  },
  paginationContainer: {
    mt: 2,
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    px: 2,
    pb: 2,
  },
  paginationWrapper: {
    display: 'flex',
    justifyContent: 'center',
    flex: 1,
  },
  itemsPerPageContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: 1,
  },
  itemsPerPageSelect: {
    '& .MuiSvgIcon-root': {
      color: 'var(--text-primary)',
    },
    '& .MuiSelect-select': {
      py: 0.5,
      px: 1.5,
      fontSize: FONT_SIZES.SM,
      color: 'var(--text-primary)',
      bgcolor: 'var(--bg-secondary)',
    },
    '& .MuiOutlinedInput-notchedOutline': {
      borderColor: 'rgba(255, 255, 255, 0.1)',
    },
    '&:hover .MuiOutlinedInput-notchedOutline': {
      borderColor: 'rgba(255, 255, 255, 0.2)',
    },
    '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
      borderColor: 'var(--primary-main)',
    },
  },
  itemsPerPageLabel: {
    fontSize: FONT_SIZES.SM,
    color: 'var(--text-secondary)',
  },
};

const DATE_COLUMNS = new Set([
  'logical_date',
  'last_run_date',
  'next_run_date',
  'prev_interval_start',
  'deleted_at',
  'last_system_updated_date',
  'latest_heartbeat',
]);

const DEFAULT_COLUMN_WIDTHS: Record<string, number> = {
  name: 200,
  logical_date: 160,
  last_run_date: 160,
  next_run_date: 160,
  prev_interval_start: 160,
  deleted_at: 160,
  last_system_updated_date: 180,
  latest_heartbeat: 160,
  state: 110,
  partition: 110,
  frequency: 110,
  priority: 90,
  duration: 90,
  actions_status: 110,
  [RUNS_COLUMN]: 160,
};
const DEFAULT_COLUMN_WIDTH_FALLBACK = 150;

const buildTaskDateColumnTooltips = (tz: string): Record<string, string> => ({
  logical_date: `The data period this task is computing — same concept as Airflow's logical_date (formerly execution_date). Floored to cron granularity (daily → midnight, monthly → 1st of month, sub-hourly → exact cron tick). Available as {{ds}} or {{logical_date}} in payloads. All times ${tz}.`,
  next_run_date: `Scheduler trigger date (${tz}) — when next_run_date ≤ wall clock, the cron dispatches this task. Advances one cron interval from the previous next_run_date (not from physical run time), enabling automatic catch-up for missed runs.`,
  prev_interval_start: `The logical_date (${tz}) of the most recently completed run — used to index logs and track the last successfully processed data period.`,
  last_run_date: `Wall-clock time (${tz}) when this task last executed.`,
  [RUNS_COLUMN]:
    'The most recent runs of this task (newest on the right), colored by status. Hover a box for its logical date; click to open that run in the Logs tab.',
});

function formatDateValue(value: string): string {
  return formatDateValueUtil(value);
}

function getColumnValue(item: CatalogItem, column: string): string {
  let value: unknown = null;

  if (item.data && typeof item.data === 'object' && column in item.data) {
    value = (item.data as Record<string, unknown>)[column];
  } else if (column in item) {
    value = (item as Record<string, unknown>)[column];
  }

  if (value === null || value === undefined) {
    return '';
  }

  if (Array.isArray(value)) {
    if (value.length === 0) {
      return '[]';
    }
    const preview = value.slice(0, 2).map(String).join(', ');
    return value.length > 2 ? `[${preview}, ...]` : `[${preview}]`;
  }

  if (typeof value === 'object') {
    return JSON.stringify(value);
  }

  const stringValue =
    typeof value === 'function'
      ? '[Function]'
      : String(value as string | number | boolean | bigint | symbol);

  if (DATE_COLUMNS.has(column) && stringValue.includes('T')) {
    return formatDateValue(stringValue);
  }

  if (stringValue.length > 100) {
    return stringValue.substring(0, 100) + '...';
  }

  return stringValue;
}

// Get raw column value without stringification (for complex types like actions_status)
// Tries multiple paths: item.data.column, item.column, or if item has nested data
function getRawColumnValue(item: CatalogItem, column: string): unknown {
  // First try item.data
  if (item.data && typeof item.data === 'object' && column in item.data) {
    return (item.data as Record<string, unknown>)[column];
  }
  // Then try directly on item
  if (column in item) {
    return (item as Record<string, unknown>)[column];
  }
  return null;
}

// Type for action status entry
interface ActionStatusEntry {
  laui: string;
  name: string;
  status?: string;
}

// Type for actions object (configured actions)
interface ActionsConfig {
  create_actions?: ActionStatusEntry[];
  pre_actions?: ActionStatusEntry[];
  running_actions?: ActionStatusEntry[];
  post_actions?: ActionStatusEntry[];
}

// Type for actions_status object (execution status)
interface ActionsStatus {
  pre_actions?: ActionStatusEntry[];
  running_actions?: ActionStatusEntry[];
  post_actions?: ActionStatusEntry[];
}

// Single pie chart for a section with count badge
function SectionPieChart({
  actions,
  label,
  size = 18,
}: {
  actions: ActionStatusEntry[];
  label: string;
  size?: number;
}) {
  // Color mapping: success (green), error (red), everything else (gray)
  const getStatusColor = (status?: string) => {
    const normalizedStatus = (status || 'pending').toLowerCase();

    // Success states - green
    if (
      normalizedStatus === 'success' ||
      normalizedStatus === 'completed' ||
      normalizedStatus === 'done'
    ) {
      return '#4ade80';
    }

    // Error states - red
    if (
      normalizedStatus === 'error' ||
      normalizedStatus === 'failed' ||
      normalizedStatus === 'failure' ||
      normalizedStatus === 'fail'
    ) {
      return '#f87171';
    }

    // Everything else (created, scheduled, pending, running, etc.) - gray
    return '#94a3b8';
  };

  // Ensure actions is a valid array
  const actionsList = Array.isArray(actions) ? actions : [];
  const totalActions = actionsList.length;

  if (totalActions === 0) {
    return (
      <Tooltip title={`${label}: No actions`} arrow>
        <Box
          sx={{
            width: size,
            height: size,
            borderRadius: '50%',
            bgcolor: 'var(--bg-secondary)',
            border: '1px solid var(--border)',
            opacity: 0.4,
          }}
        />
      </Tooltip>
    );
  }

  const radius = size / 2;
  const center = radius;

  // Generate SVG pie slices - handles any number of actions
  const generatePieSlices = () => {
    if (totalActions === 1) {
      // Single action = full circle
      const color = getStatusColor(actionsList[0].status);
      return <circle cx={center} cy={center} r={radius - 0.5} fill={color} />;
    }

    // Multiple actions = divide into equal slices
    const anglePerSlice = (2 * Math.PI) / totalActions;

    return actionsList.map((action, idx) => {
      const startAngle = idx * anglePerSlice - Math.PI / 2; // Start from top
      const endAngle = (idx + 1) * anglePerSlice - Math.PI / 2;

      const x1 = center + radius * Math.cos(startAngle);
      const y1 = center + radius * Math.sin(startAngle);
      const x2 = center + radius * Math.cos(endAngle);
      const y2 = center + radius * Math.sin(endAngle);

      // Large arc flag: 1 if slice is more than 180 degrees
      const largeArcFlag = anglePerSlice > Math.PI ? 1 : 0;

      const pathData = `M ${center} ${center} L ${x1} ${y1} A ${radius} ${radius} 0 ${largeArcFlag} 1 ${x2} ${y2} Z`;
      const color = getStatusColor(action.status);

      return (
        <path
          key={`${label}-${idx}-${action.laui || idx}`}
          d={pathData}
          fill={color}
          stroke="var(--bg-primary)"
          strokeWidth="0.5"
        />
      );
    });
  };

  // Count statuses for summary
  const statusCounts = actionsList.reduce(
    (acc, action) => {
      const status = action.status || 'pending';
      acc[status] = (acc[status] || 0) + 1;
      return acc;
    },
    {} as Record<string, number>,
  );

  // Build tooltip with detailed info
  const statusSummary = Object.entries(statusCounts)
    .map(([status, count]) => `${count} ${status}`)
    .join(', ');

  const tooltipLines = [
    `${label} (${totalActions}): ${statusSummary}`,
    ...actionsList.map((a) => `• ${a.name || 'Unknown'}: ${a.status || 'pending'}`),
  ];
  const tooltipContent = tooltipLines.join('\n');

  return (
    <Tooltip
      title={<Box sx={{ whiteSpace: 'pre-line', fontSize: '11px' }}>{tooltipContent}</Box>}
      arrow
    >
      <Box
        sx={{
          display: 'inline-flex',
          cursor: 'pointer',
          position: 'relative',
          minWidth: size,
          minHeight: size,
        }}
      >
        <svg
          width={size}
          height={size}
          viewBox={`0 0 ${size} ${size}`}
          style={{ display: 'block', overflow: 'visible' }}
        >
          {generatePieSlices()}
        </svg>
        {/* Count badge for multiple actions */}
        {totalActions > 1 && (
          <Box
            sx={{
              position: 'absolute',
              top: -4,
              right: -4,
              width: 10,
              height: 10,
              borderRadius: '50%',
              bgcolor: 'var(--bg-primary)',
              border: '1px solid var(--border)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              fontSize: '7px',
              fontWeight: 'bold',
              color: 'var(--text-primary)',
            }}
          >
            {totalActions}
          </Box>
        )}
      </Box>
    </Tooltip>
  );
}

// Render actions as three separate pie charts (Pre, Running, Post)
function ActionsStatusBar({
  actions,
  actionsStatus,
}: {
  actions: ActionsConfig | null;
  actionsStatus: ActionsStatus | null;
}) {
  // Merge configured actions with execution status
  const configuredActions = actions && typeof actions === 'object' ? actions : {};
  const executionStatus = actionsStatus && typeof actionsStatus === 'object' ? actionsStatus : {};

  // Build actions list with status for each section
  // Uses configured actions as base, merges with execution status
  const buildSectionActions = (section: string): ActionStatusEntry[] => {
    const configured = (configuredActions as any)[section];
    const executed = (executionStatus as any)[section];

    // Ensure we have arrays
    const configuredArr = Array.isArray(configured) ? configured : [];
    const executedArr = Array.isArray(executed) ? executed : [];

    // Create a map of laui -> status from executed actions
    const statusMap = new Map<string, string>();
    executedArr.forEach((action: any) => {
      if (action.laui) {
        statusMap.set(action.laui, action.status || 'pending');
      }
    });

    // Always use configured actions as the base to get full list
    // Then look up status from execution status
    if (configuredArr.length > 0) {
      return configuredArr.map((action: any) => ({
        laui: action.laui || '',
        name: action.name || 'Unknown',
        status: statusMap.get(action.laui) || action.status || 'pending',
      }));
    }

    // Fallback: if no configured but has executed, use executed
    if (executedArr.length > 0) {
      return executedArr.map((action: any) => ({
        laui: action.laui || '',
        name: action.name || 'Unknown',
        status: action.status || 'pending',
      }));
    }

    return [];
  };

  const preActions = buildSectionActions('pre_actions');
  const runningActions = buildSectionActions('running_actions');
  const postActions = buildSectionActions('post_actions');

  // Check if there are any actions at all
  const hasAnyActions =
    preActions.length > 0 || runningActions.length > 0 || postActions.length > 0;

  if (!hasAnyActions) {
    return <span style={{ color: 'var(--text-secondary)' }}>-</span>;
  }

  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
      {/* Pre Actions */}
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <SectionPieChart actions={preActions} label="Pre" size={16} />
        <Typography sx={{ fontSize: '8px', color: 'var(--text-secondary)', mt: 0.25 }}>
          Pre
        </Typography>
      </Box>
      {/* Running Actions */}
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <SectionPieChart actions={runningActions} label="Run" size={16} />
        <Typography sx={{ fontSize: '8px', color: 'var(--text-secondary)', mt: 0.25 }}>
          Run
        </Typography>
      </Box>
      {/* Post Actions */}
      <Box sx={{ display: 'flex', flexDirection: 'column', alignItems: 'center' }}>
        <SectionPieChart actions={postActions} label="Post" size={16} />
        <Typography sx={{ fontSize: '8px', color: 'var(--text-secondary)', mt: 0.25 }}>
          Post
        </Typography>
      </Box>
    </Box>
  );
}

function formatColumnName(name: string): string {
  if (name === RUNS_COLUMN) return 'Runs';
  return name
    .split('_')
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
}

interface ItemsTableProps {
  onSelectionChange?: (lauis: string[]) => void;
  // folderMode: render fixed 4-col layout (name, type, description, actions)
  // with search + type-filter built in, driven by callbacks from FolderView
  folderMode?: boolean;
  folderSearchValue?: string;
  onFolderSearchChange?: (v: string) => void;
  folderTypeOptions?: string[];
  folderTypeValue?: string | null;
  onFolderTypeChange?: (v: string | null) => void;
  // called instead of handleFilteredListPageChange when folderMode
  onPageChange?: (page: number) => void;
  onPerPageChange?: (perPage: number) => void;
  // parentLaui used for delete modal in folderMode
  folderParentLaui?: string;
  // callback to trigger refresh in parent after delete
  onDeleteSuccess?: () => void;
  // callback to trigger refresh in parent after usecase creation
  onUsecaseCreateSuccess?: () => void;
  loadingItems?: boolean;
  // When true (workflow Tasks tab), group & tint tasks by their dependency DAG
  // in the default (unsorted) view.
  dependencyGrouping?: boolean;
}

export default function ItemsTable({
  onSelectionChange,
  folderMode,
  folderSearchValue,
  onFolderSearchChange,
  folderTypeOptions,
  folderTypeValue,
  onFolderTypeChange,
  onPageChange,
  onPerPageChange,
  folderParentLaui,
  onDeleteSuccess,
  onUsecaseCreateSuccess,
  loadingItems,
  dependencyGrouping,
}: ItemsTableProps) {
  const { timeZone } = useTimeFormat();
  const tzLabel = timeZone === 'utc' ? 'UTC' : getTimeZoneLabel();
  const TASK_DATE_COLUMN_TOOLTIPS = buildTaskDateColumnTooltips(tzLabel);
  const { accountLaui, currentProjectLaui, catalogType } = useGlobal();
  const {
    catalogState,
    setDeleteModalState,
    setShareModalState,
    setRestoreModalState,
    setImportModalState,
  } = useCatalog();

  const filteredItems = catalogState.activeFilterType ? catalogState.filteredItemsByType : [];
  const filterType = catalogState.activeFilterType;
  // '__folder__' is an internal sentinel meaning "all children of a folder" — never a real item type
  const concreteFilterType = filterType === '__folder__' ? null : filterType;
  const deletePermission =
    catalogState.openedFolder?.permission === 'own' ||
    catalogState.openedFolder?.permission === 'edit';
  const restoreAble = catalogState.filteredFromItem?.item_type === 'folder.trash';

  const serverPagination = catalogState.filteredItemsPagination;
  const {
    handleFilteredListItemsPerPageChange,
    handleFilteredListPageChange,
    refreshFilteredList,
  } = usePaginationHandlers();
  const urlSearch = useSearch({ from: '/path' });
  const navigate = useNavigate();

  const [columns, setColumns] = useState<string[]>([]);
  const [projectionConfig, setProjectionConfig] = useState<ProjectionFieldsConfig | null>(null);
  const [loadingColumns, setLoadingColumns] = useState(true);
  const [visibleColumns, setVisibleColumns] = useState<string[] | null>(null);
  const [columnSelectorAnchor, setColumnSelectorAnchor] = useState<HTMLElement | null>(null);
  const [currentPage, setCurrentPage] = useState(1);
  const [itemsPerPage, setItemsPerPage] = useState(25);
  const [localItems, setLocalItems] = useState<CatalogItem[]>(filteredItems);
  const [selectedTasks, setSelectedTasks] = useState<string[]>([]);
  const [isRunningTasks, setIsRunningTasks] = useState(false);
  const [nameFilter, setNameFilter] = useState('');
  const [folderIconCache, setFolderIconCache] = useState<
    Record<string, { icon: React.ComponentType<any>; color: string }>
  >({});
  const [bulkUsecaseOpen, setBulkUsecaseOpen] = useState(false);
  // Bumped whenever the filtered list is (re)loaded (refresh button, create,
  // delete, …) so visible recent-run strips re-fetch their history.
  const [runsRefreshKey, setRunsRefreshKey] = useState(0);

  useEffect(() => {
    onSelectionChange?.(selectedTasks);
  }, [selectedTasks]);

  useEffect(() => {
    setRunsRefreshKey((k) => k + 1);
  }, [catalogState.filteredItemsByType]);
  const [selectedTaskControlAction, setSelectedTaskControlAction] = useState<string>('');
  const [taskControlSelectOpen, setTaskControlSelectOpen] = useState(false);
  const [showSelectTasksHint, setShowSelectTasksHint] = useState(false);
  const [selectedUIAction, setSelectedUIAction] = useState<string>('');
  const [sortBy, setSortBy] = useState<string | undefined>(urlSearch.sortBy);
  const [sortOrder, setSortOrder] = useState<'asc' | 'desc'>(
    (urlSearch.sortOrder as 'asc' | 'desc') ?? 'asc',
  );
  const [filterState, setFilterState] = useState<string>(urlSearch.filterState ?? '');
  const [itemPaths, setItemPaths] = useState<Record<string, string>>({});

  const SORTABLE_COLUMNS = new Set([
    'partition',
    'logical_date',
    'state',
    'last_run_date',
    'duration',
    'priority',
    'frequency',
  ]);
  const TASK_STATES = [
    'scheduled',
    'queued_for_connection',
    'queued_in_redis',
    'running',
    'success',
    'error',
    'cancelled',
  ];

  const isServerPaginated = serverPagination != null;

  const { showRunAction, setRunActionModalData, setShowRunAction, attachedActions } =
    useActionContext();
  const { showSuccess } = useNotification();

  const isMarketplaceCatalog = catalogType === CatalogType.MARKETPLACE;

  useEffect(() => {
    if (filterType === 'action') setShowRunAction(true);
    if (!_.isEqual(filteredItems, localItems)) {
      setLocalItems(filteredItems);
      setSelectedTasks([]);
    }
  }, [filteredItems]);

  useEffect(() => {
    if (folderMode) {
      setColumns(['item_type', 'description']);
      setVisibleColumns(null);
      setProjectionConfig(null);
      setLoadingColumns(false);
      return;
    }

    const loadColumns = async () => {
      let itemType: string | null = null;
      if (filteredItems.length > 0 && filteredItems[0].item_type) {
        itemType = filteredItems[0].item_type;
      } else if (concreteFilterType) {
        itemType = concreteFilterType;
      }

      if (!itemType) {
        setColumns([]);
        setProjectionConfig(null);
        setLoadingColumns(false);
        return;
      }

      setLoadingColumns(true);
      try {
        const [schemaColumns, config] = await Promise.all([
          getSchemaUiPreviewFields(itemType),
          getProjectionFieldsConfig(itemType),
        ]);

        // Inject the virtual "recent runs" column for tasks, right after `state`
        // (append if `state` isn't present). It's frontend-only, so it must be
        // added to the column list used both for display and prefs filtering.
        let allColumns = schemaColumns;
        if (itemType === 'task' && !schemaColumns.includes(RUNS_COLUMN)) {
          allColumns = [...schemaColumns];
          const stateIdx = allColumns.indexOf('state');
          allColumns.splice(
            stateIdx >= 0 ? stateIdx + 1 : allColumns.length,
            0,
            RUNS_COLUMN,
          );
        }
        setColumns(allColumns);

        const stored = localStorage.getItem(`column_prefs_${itemType}`);
        if (stored) {
          try {
            const parsed: string[] = JSON.parse(stored);
            setVisibleColumns(parsed.filter((c) => allColumns.includes(c)));
          } catch {
            setVisibleColumns(null);
          }
        } else {
          setVisibleColumns(null);
        }

        setProjectionConfig(config);
      } catch {
        setColumns([]);
        setProjectionConfig(null);
      } finally {
        setLoadingColumns(false);
      }
    };

    void loadColumns();
    setSortBy(undefined);
    setSortOrder('asc');
    setFilterState('');
    setNameFilter('');
  }, [filterType]);

  // Reset to page 1 when filtered items or items per page changes (client-side only)
  useEffect(() => {
    if (!isServerPaginated) setCurrentPage(1);
  }, [filteredItems, itemsPerPage, isServerPaginated]);

  // Fetch breadcrumb paths for trash items
  useEffect(() => {
    if (!restoreAble) {
      setItemPaths({});
      return;
    }
    const missingItems = filteredItems.filter((item) => !(item.laui in itemPaths));
    if (missingItems.length === 0) return;
    const fetchPaths = async () => {
      const newPaths: Record<string, string> = {};
      await Promise.all(
        missingItems.map(async (item) => {
          try {
            const originalParentLaui = item.parent_laui;
            if (!originalParentLaui) {
              newPaths[item.laui] = `/${item.name}`;
              return;
            }
            const [response, parentItem] = await Promise.all([
              getBreadcrumbs(originalParentLaui),
              getCatalogItemById(originalParentLaui),
            ]);
            // getBreadcrumbs returns the ancestors of originalParent (not the parent itself),
            // so we include parentItem.name explicitly before the item name
            if (response.items && response.items.length > 0) {
              const ancestorPath = getBreadcrumbString(response.items[0] as any);
              const pathWithoutAccount = ancestorPath.replace(/^\/[^/]+/, '');
              newPaths[item.laui] = `${pathWithoutAccount}/${parentItem.name}/${item.name}`;
            } else {
              newPaths[item.laui] = `/${parentItem.name}/${item.name}`;
            }
          } catch {
            newPaths[item.laui] = item.name;
          }
        }),
      );
      setItemPaths((prev) => ({ ...prev, ...newPaths }));
    };
    void fetchPaths();
  }, [filteredItems, restoreAble]);

  // Build icon cache for item_type column in folder mode
  useEffect(() => {
    if (!folderMode || filteredItems.length === 0) return;
    const uniqueTypes = [
      ...new Set(filteredItems.map((i) => i.item_type).filter(Boolean)),
    ] as string[];
    const missing = uniqueTypes.filter((t) => !folderIconCache[t]);
    if (missing.length === 0) return;
    void Promise.all(
      missing.map(async (t) => {
        const cfg = await getItemTypeVisualConfig(t);
        return cfg ? ([t, { icon: getIconComponent(cfg.icon), color: cfg.color }] as const) : null;
      }),
    ).then((results) => {
      const entries = results.filter(Boolean) as [
        string,
        { icon: React.ComponentType<any>; color: string },
      ][];
      if (entries.length > 0)
        setFolderIconCache((prev) => ({ ...prev, ...Object.fromEntries(entries) }));
    });
  }, [filteredItems, folderMode]);

  const isTaskType =
    filterType === 'task' || (filteredItems.length > 0 && filteredItems[0]?.item_type === 'task');

  const currentPageNum = isServerPaginated ? (serverPagination?.current_page ?? 1) : currentPage;
  const perPage = isServerPaginated ? (serverPagination?.per_page ?? 20) : itemsPerPage;

  const baseItems = isServerPaginated
    ? filteredItems
    : localItems.slice((currentPage - 1) * itemsPerPage, currentPage * itemsPerPage);

  const nameFilteredItems =
    isTaskType && nameFilter.trim()
      ? baseItems.filter((item) =>
          (item.name || '').toLowerCase().includes(nameFilter.trim().toLowerCase()),
        )
      : null;
  const currentItemsRaw = nameFilteredItems ?? baseItems;

  // DAG grouping (workflow Tasks tab default view): reorder so dependency-linked
  // tasks sit together in topological order, and expose a per-task group index
  // for alternating row tints. Disabled when the user applies a column sort.
  const groupingActive = !!dependencyGrouping && isTaskType && !sortBy;
  const dependencyGroups = useMemo(() => {
    if (!groupingActive) return null;
    const { orderedLauis, groupIndexByLaui } = groupTasksByDependency(currentItemsRaw);
    const byLaui = new Map(currentItemsRaw.map((it) => [it.laui, it]));
    const items = orderedLauis
      .map((laui) => byLaui.get(laui))
      .filter((it): it is CatalogItem => it != null);
    // Defensive: keep any rows the grouping didn't cover (e.g. name collisions).
    const seen = new Set(orderedLauis);
    for (const it of currentItemsRaw) if (!seen.has(it.laui)) items.push(it);

    // Per-task ordering for the row number badge: a global 1-based `number`
    // (position down the DAG-ordered list) plus the task's step within its
    // dependency group.
    const groupSize = new Map<number, number>();
    items.forEach((it) => {
      const g = groupIndexByLaui.get(it.laui) ?? -1;
      groupSize.set(g, (groupSize.get(g) ?? 0) + 1);
    });
    const posCounter = new Map<number, number>();
    const orderByLaui = new Map<
      string,
      { number: number; posInGroup: number; groupSize: number }
    >();
    items.forEach((it, i) => {
      const g = groupIndexByLaui.get(it.laui) ?? -1;
      const posInGroup = (posCounter.get(g) ?? 0) + 1;
      posCounter.set(g, posInGroup);
      orderByLaui.set(it.laui, { number: i + 1, posInGroup, groupSize: groupSize.get(g) ?? 1 });
    });

    // For each task, record the root task's (posInGroup=1) next_run_date and
    // laui so all tasks in a group share the same schedule anchor and the same
    // canonical run timeline, keeping the Runs columns aligned across the group.
    const rootNextRunDateByLaui = new Map<string, string>();
    const rootNextRunDateByGroup = new Map<number, string>();
    const rootLauiByGroup = new Map<number, string>();
    items.forEach((it) => {
      const g = groupIndexByLaui.get(it.laui) ?? -1;
      const pos = orderByLaui.get(it.laui)?.posInGroup ?? 1;
      if (pos === 1) {
        if (it.next_run_date) rootNextRunDateByGroup.set(g, it.next_run_date);
        rootLauiByGroup.set(g, it.laui);
      }
    });
    const rootLauiByLaui = new Map<string, string>();
    items.forEach((it) => {
      const g = groupIndexByLaui.get(it.laui) ?? -1;
      const root = rootNextRunDateByGroup.get(g) ?? it.next_run_date ?? '';
      rootNextRunDateByLaui.set(it.laui, root);
      rootLauiByLaui.set(it.laui, rootLauiByGroup.get(g) ?? it.laui);
    });

    return { items, groupIndexByLaui, orderByLaui, rootNextRunDateByLaui, rootLauiByLaui };
  }, [groupingActive, currentItemsRaw]);

  const currentItems = dependencyGroups?.items ?? currentItemsRaw;
  const serverHasNext = serverPagination?.has_next ?? false;
  const itemsReturned = filteredItems.length;
  const pageSize = isServerPaginated ? (serverPagination?.per_page ?? itemsPerPage) : itemsPerPage;
  const hasNext = isServerPaginated
    ? itemsReturned < pageSize
      ? false
      : serverHasNext
    : currentPage < Math.ceil(localItems.length / itemsPerPage);
  const hasPrevious = isServerPaginated
    ? (serverPagination?.has_previous ?? currentPageNum > 1)
    : currentPage > 1;

  const handleSortChange = (column: string) => {
    if (!isServerPaginated) return;
    const newOrder = sortBy === column && sortOrder === 'asc' ? 'desc' : 'asc';
    setSortBy(column);
    setSortOrder(newOrder);
    handleFilteredListPageChange(1, column, newOrder, filterState || undefined);
  };

  const handleStateFilterChange = (state: string) => {
    setFilterState(state);
    handleFilteredListPageChange(1, sortBy, sortOrder, state || undefined);
  };

  const hasActiveFilters = !!sortBy || !!filterState;

  const handleResetFilters = () => {
    setSortBy(undefined);
    setSortOrder('asc');
    setFilterState('');
    handleFilteredListPageChange(1, undefined, undefined, undefined);
  };

  const handlePageChange = (page: number) => {
    if (folderMode && onPageChange) {
      onPageChange(page);
    } else if (isServerPaginated) {
      handleFilteredListPageChange(page, sortBy, sortOrder, filterState || undefined);
    } else {
      setCurrentPage(page);
    }
    const tableContainer = document.querySelector('.MuiTableContainer-root');
    if (tableContainer) tableContainer.scrollTop = 0;
  };

  const handleItemsPerPageChange = (event: any) => {
    const value = Number(event.target.value);
    if (folderMode && onPerPageChange) {
      onPerPageChange(value);
    } else if (isServerPaginated) {
      handleFilteredListItemsPerPageChange(value, sortBy, sortOrder, filterState || undefined);
    } else {
      setItemsPerPage(value);
    }
  };

  const { handleViewItem } = useEditorHandlers();
  const { handleSelectItem } = useSidebarHandlers();

  const handleView = (item: CatalogItem, event: React.MouseEvent) => {
    event.stopPropagation();
    if (folderMode && item.item_type?.startsWith('folder')) {
      void handleSelectItem(item);
    } else {
      void handleViewItem(item);
    }
  };

  const handleDelete = (item: CatalogItem, event: React.MouseEvent) => {
    event.stopPropagation();
    const parentLaui =
      folderMode && folderParentLaui ? folderParentLaui : catalogState.lastFilteredFromItem!.laui;
    const onSuccess = folderMode && onDeleteSuccess ? onDeleteSuccess : refreshFilteredList;
    setDeleteModalState({
      isOpen: true,
      itemLaui: item.laui,
      parentLaui,
      itemName: item.name,
      onSuccess: () => void onSuccess(),
      isPermanent: !!item.deleted_at,
    });
  };

  const handleShare = (item: CatalogItem, event: React.MouseEvent) => {
    event.stopPropagation();
    setShareModalState({ isOpen: true, item: item });
  };

  const handleRestore = (item: CatalogItem, event: React.MouseEvent) => {
    event.stopPropagation();
    const onSuccess = folderMode && onDeleteSuccess ? onDeleteSuccess : refreshFilteredList;
    setRestoreModalState({ isOpen: true, item, onSuccess: () => void onSuccess() });
  };

  const handleImport = async (item: CatalogItem, event: React.MouseEvent) => {
    event.stopPropagation();
    const itemData = await getCatalogItemById(item.laui, isMarketplaceCatalog);
    setImportModalState({ isOpen: true, itemData: itemData });
  };

  const handleRunAction = async (item: CatalogItem, event: React.MouseEvent) => {
    event?.stopPropagation();
    const itemData = await getCatalogItemById(item.laui);
    try {
      setRunActionModalData({
        actionVariables: itemData.action_variables as object,
        isOpen: true,
        actionLaui: item.laui,
        mode: RunActionModalMode.RUN,
      });
    } catch {
      //console.log(e)
    }
  };

  const handleRunTask = async (item: CatalogItem, event: React.MouseEvent) => {
    event.stopPropagation();
    try {
      const prevIntervalStart =
        (item.data as any)?.prev_interval_start || (item as any).prev_interval_start;
      const itemLogicalDate = (item.data as any)?.logical_date || (item as any).logical_date;
      const runPayload: any = {
        item_type: 'task',
        item_laui: item.laui,
        logical_date: prevIntervalStart || itemLogicalDate,
      };
      if (!runPayload.logical_date) delete runPayload.logical_date;

      await runTask(runPayload);
      showSuccess('Task sent to execute');

      await refreshFilteredList();
    } catch (error: any) {
      console.error(`error running task`, error);
    }
  };

  const handlePauseTask = async (item: CatalogItem, event: React.MouseEvent) => {
    event.stopPropagation();
    try {
      await cancelTask(item.laui);
    } catch (error) {
      console.error('Error cancelling task:', error);
    }
  };

  const isTaskItem = (item: CatalogItem) => {
    return item.item_type === 'task';
  };

  const handleSelectUIAction = async (uiAction: string, metadata: Record<string, any> = {}) => {
    setSelectedUIAction(uiAction);
    //TODO use action's laui instead
    const searchResult = await searchCatalogItems('action', false, {
      filters: { name: uiAction },
    });
    if (searchResult.items && searchResult.items.length > 0) {
      const actionLaui = searchResult.items[0].laui;
      const actionVariables = searchResult.items[0].action_variables;

      // Map metadata values to action_variables based on matching property names
      Object.keys(metadata).forEach((key) => {
        if (key in actionVariables) {
          actionVariables[key] = metadata[key];
        }
      });

      if ('task_lauis' in actionVariables) {
        actionVariables['task_lauis'] = selectedTasks;
      }
      if ('lauis' in actionVariables) {
        actionVariables['lauis'] = selectedTasks; //#todo to change this to SelectedItems for proper naming
      }
      if ('parent_laui' in actionVariables) {
        const queryString = window.location.search;
        const urlParams = new URLSearchParams(queryString);
        const laui = urlParams.get('laui');
        actionVariables['parent_laui'] = laui;
      }

      if ('account_laui' in actionVariables) {
        actionVariables['account_laui'] = accountLaui || '';
      }

      if ('project_laui' in actionVariables) {
        actionVariables['project_laui'] = currentProjectLaui || '';
      }

      setRunActionModalData({
        isOpen: true,
        actionLaui,
        actionVariables,
        mode: RunActionModalMode.RUN,
      });
    } else {
      console.error(`Action ${uiAction} not found`);
    }
  };

  const shouldShowRunButton = (item: CatalogItem) => {
    if (item.item_type === 'chat_history' || item.item_type === 'generate_history') return true;
    if (isTaskItem(item)) {
      const state: string = (item.data as any)?.state || (item as any).state;
      return (
        !state ||
        state.toLowerCase() === 'scheduled' ||
        state.toLowerCase() === 'success' ||
        state.toLowerCase() === 'created' ||
        state.toLowerCase() === 'error'
      );
    }
    if (item.item_type?.split('.')[0] === 'action' && showRunAction) return true;
    return false;
  };

  const runButtonTooltipText = (item: CatalogItem) => {
    if (item.item_type === 'chat_history') return 'Open Chat Session';
    if (item.item_type === 'generate_history') return 'Open Generate Session';
    if (item.item_type?.split('.')[0] === 'action') return 'Run Action';
    return `Run task`;
  };

  const shouldShowPauseButton = (item: CatalogItem) => {
    if (!isTaskItem(item)) return false;
    const state = (item.data as any)?.state || (item as any).state;
    return (
      state &&
      state !== 'scheduled' &&
      state !== 'success' &&
      state !== 'created' &&
      state !== 'error'
    );
  };

  // Check if a task can be selected based on the current action's metadata
  const canSelectTask = (item: CatalogItem): boolean => {
    if (selectedTaskControlAction === 'run' || selectedTaskControlAction === '') return true; // Run action or no action selected allows all tasks

    const action =
      attachedActions &&
      attachedActions.taskControlActions.find((a) => a.name === selectedTaskControlAction);
    if (!action || !action.metadata || !action.metadata.state) return true;

    const taskState = (item.data as any)?.state || (item as any).state || 'created';
    const allowedStates = action.metadata.state;

    return allowedStates.includes(taskState.toLowerCase());
  };

  // Multi-select handlers for tasks
  const handleSelectTask = (taskLaui: string, event: React.MouseEvent) => {
    event.stopPropagation();

    // Find the task item
    const taskItem = currentItems.find((item) => item.laui === taskLaui);
    if (!taskItem || !canSelectTask(taskItem)) return;

    setSelectedTasks((prev) =>
      prev.includes(taskLaui) ? prev.filter((id) => id !== taskLaui) : [...prev, taskLaui],
    );
  };

  const handleSelectAllTasks = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) {
      setSelectedTasks(currentItems.map((item) => item.laui));
    } else {
      setSelectedTasks([]);
    }
  };

  const handleRunSelectedTasks = async () => {
    if (selectedTasks.length === 0 || selectedTaskControlAction === '') return;

    setIsRunningTasks(true);
    try {
      if (selectedTaskControlAction === 'run') {
        // Run action - use runTasks from task.service
        await runTasks(selectedTasks);
        //console.log('Selected tasks run successfully');
      } else {
        const taskDetails = await getCatalogItemById(selectedTasks[0]);
        // Search for the action by name
        const searchResult = await searchCatalogItems('action', false, {
          filters: {
            name: selectedTaskControlAction,
            account_laui: taskDetails.account_laui as string,
            project_laui: taskDetails.project_laui as string,
            get_by_pk: true,
          },
        });

        if (searchResult.items && searchResult.items.length > 0) {
          const actionLaui = searchResult.items[0].laui;

          // Call runAction with action_laui and task_lauis
          await runAction({
            item_laui: actionLaui,
            action_variables: { task_lauis: selectedTasks },
          });
          showSuccess(`Action ${selectedTaskControlAction} ran`);
        } else {
          console.error(`Action ${selectedTaskControlAction} not found`);
        }
      }

      // Clear selection
      setSelectedTasks([]);

      // Call callback to refresh items
    } catch (error) {
      console.error('Error running selected tasks:', error);
    } finally {
      setIsRunningTasks(false);
    }
  };

  // In folderMode: fixed columns are name + item_type + description (name rendered separately as first col)
  const displayColumns = folderMode
    ? ['name', 'item_type', 'description']
    : visibleColumns
      ? columns.filter((c) => visibleColumns.includes(c))
      : columns;

  const totalColumns =
    (isTaskType && !folderMode ? 2 : 1) +
    displayColumns.length +
    1 +
    (restoreAble ? 1 : 0) +
    (groupingActive ? 1 : 0);

  const [columnWidths, setColumnWidths] = useState<Record<string, number>>({});

  const handleResizeStart = useCallback((column: string, e: React.MouseEvent) => {
    e.preventDefault();
    e.stopPropagation();

    const th = (e.target as HTMLElement).closest('th');
    const startWidth = th ? th.getBoundingClientRect().width : 150;
    const startX = e.clientX;

    // Snapshot ALL column header widths right now so we can lock them all at once.
    // This prevents other columns from reflowing when one column changes width.
    const headerRow = th?.closest('tr');
    const allThs = headerRow ? Array.from(headerRow.querySelectorAll('th')) : [];
    const snapshotWidths: Record<string, number> = {};
    allThs.forEach((headerTh) => {
      const col = (headerTh as HTMLElement).dataset.col;
      if (col) snapshotWidths[col] = headerTh.getBoundingClientRect().width;
    });

    // Immediately lock all columns at their current rendered widths
    setColumnWidths((prev) => ({ ...prev, ...snapshotWidths }));

    const handleMouseMove = (moveEvent: MouseEvent) => {
      const diff = moveEvent.clientX - startX;
      const newWidth = Math.max(60, startWidth + diff);
      setColumnWidths((prev) => ({ ...prev, [column]: newWidth }));
    };

    const handleMouseUp = () => {
      document.removeEventListener('mousemove', handleMouseMove);
      document.removeEventListener('mouseup', handleMouseUp);
      document.body.style.cursor = '';
      document.body.style.userSelect = '';
    };

    document.addEventListener('mousemove', handleMouseMove);
    document.addEventListener('mouseup', handleMouseUp);
    document.body.style.cursor = 'col-resize';
    document.body.style.userSelect = 'none';
  }, []);

  const columnPrefKey = filterType ? `column_prefs_${filterType}` : null;

  const handleToggleColumn = (col: string) => {
    const current = visibleColumns ?? columns;
    const next = current.includes(col) ? current.filter((c) => c !== col) : [...current, col];
    const ordered = columns.filter((c) => next.includes(c));
    setVisibleColumns(ordered);
    if (columnPrefKey) localStorage.setItem(columnPrefKey, JSON.stringify(ordered));
  };

  const handleClearColumnPrefs = () => {
    setVisibleColumns(null);
    if (columnPrefKey) localStorage.removeItem(columnPrefKey);
  };

  return (
    <>
      <Toolbar
        disableGutters
        sx={{
          minHeight: '48px !important',
          display: 'flex',
          justifyContent: 'flex-start',
          alignItems: 'center',
          gap: 2,
        }}
      >
        <Box
          sx={{
            display: 'flex',
            width: folderMode ? 'auto' : 320,
            alignItems: 'center',
            gap: folderMode ? 1 : 0,
          }}
        >
          {folderMode ? (
            <>
              <TextField
                size="small"
                placeholder="Search by name..."
                value={folderSearchValue ?? ''}
                onChange={(e) => onFolderSearchChange?.(e.target.value)}
                slotProps={{
                  input: {
                    startAdornment: (
                      <InputAdornment position="start">
                        <SearchIcon
                          sx={{
                            fontSize: 16,
                            color: 'var(--text-secondary)',
                          }}
                        />
                      </InputAdornment>
                    ),
                  },
                }}
                sx={{
                  width: 240,
                  '& .MuiOutlinedInput-root': {
                    backgroundColor: 'var(--bg-secondary)',
                    color: 'var(--text-primary)',
                    fontSize: FONT_SIZES.SM,
                    '& fieldset': { borderColor: 'rgba(255,255,255,0.12)' },
                    '&:hover fieldset': {
                      borderColor: 'rgba(255,255,255,0.24)',
                    },
                    '&.Mui-focused fieldset': { borderColor: 'var(--accent)' },
                  },
                  '& input::placeholder': {
                    color: 'var(--text-secondary)',
                    opacity: 1,
                  },
                }}
              />
              {folderTypeOptions && folderTypeOptions.length > 0 && (
                <FormControl size="small" sx={{ minWidth: 140 }}>
                  <Select
                    value={folderTypeValue ?? ''}
                    displayEmpty
                    onChange={(e) => onFolderTypeChange?.(e.target.value || null)}
                    IconComponent={ArrowDropDown}
                    sx={styles.itemsPerPageSelect}
                    MenuProps={{
                      MenuListProps: { dense: true },
                      PaperProps: {
                        sx: {
                          bgcolor: 'var(--bg-secondary)',
                          '& .MuiMenuItem-root': {
                            color: 'var(--text-primary)',
                            fontSize: FONT_SIZES.SM,
                            whiteSpace: 'nowrap',
                            minHeight: 'unset',
                            py: '4px',
                            px: '12px',
                            lineHeight: 1.5,
                            '&:hover': { bgcolor: COLORS.HOVER },
                            '&.Mui-selected': {
                              bgcolor: COLORS.SELECTED,
                              '&:hover': {
                                bgcolor: COLORS.SELECTED_HOVER,
                              },
                            },
                          },
                        },
                      },
                    }}
                  >
                    <MenuItem value="">All Types</MenuItem>
                    {folderTypeOptions.map((t) => (
                      <MenuItem key={t} value={t}>
                        {t}
                      </MenuItem>
                    ))}
                  </Select>
                </FormControl>
              )}
            </>
          ) : isTaskType ? (
            <TextField
              size="small"
              placeholder="Search tasks by name..."
              value={nameFilter}
              onChange={(e) => setNameFilter(e.target.value)}
              slotProps={{
                input: {
                  startAdornment: (
                    <InputAdornment position="start">
                      <SearchIcon
                        sx={{
                          fontSize: 16,
                          color: 'var(--text-secondary)',
                        }}
                      />
                    </InputAdornment>
                  ),
                },
              }}
              sx={{
                width: '100%',
                '& .MuiOutlinedInput-root': {
                  backgroundColor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                  fontSize: FONT_SIZES.SM,
                  '& fieldset': { borderColor: 'rgba(255,255,255,0.12)' },
                  '&:hover fieldset': { borderColor: 'rgba(255,255,255,0.24)' },
                  '&.Mui-focused fieldset': { borderColor: 'var(--accent)' },
                },
                '& input::placeholder': {
                  color: 'var(--text-secondary)',
                  opacity: 1,
                },
              }}
            />
          ) : (
            <QuickSearch
              label={`Search ${concreteFilterType ?? 'items'}`}
              filters={{ item_type: concreteFilterType ?? '' }}
              returnUrl={true}
              onSelect={(url) => (window.location.href = url as string)}
              inputSx={{
                '& .MuiOutlinedInput-root': {
                  backgroundColor: 'var(--bg-secondary)',
                  '& fieldset': { borderColor: 'rgba(255,255,255,0.12)' },
                  '&:hover fieldset': { borderColor: 'rgba(255,255,255,0.24)' },
                },
              }}
            />
          )}
        </Box>
        {!folderMode && isTaskType && isServerPaginated && !restoreAble && (
          <FormControl size="small" sx={{ width: 150 }}>
            <Select
              value={filterState}
              displayEmpty
              onChange={(e) => handleStateFilterChange(e.target.value)}
              IconComponent={ArrowDropDown}
              sx={styles.itemsPerPageSelect}
              size="small"
              MenuProps={{
                MenuListProps: {
                  dense: true,
                },
                PaperProps: {
                  sx: {
                    bgcolor: 'var(--bg-secondary)',
                    '& .MuiMenuItem-root': {
                      color: 'var(--text-primary)',
                      fontSize: FONT_SIZES.SM,
                      whiteSpace: 'nowrap',
                      minHeight: 'unset',
                      py: '4px',
                      px: '12px',
                      lineHeight: 1.5,
                      '&:hover': { bgcolor: COLORS.HOVER },
                      '&.Mui-selected': {
                        bgcolor: COLORS.SELECTED,
                        '&:hover': { bgcolor: COLORS.SELECTED_HOVER },
                      },
                    },
                  },
                },
              }}
            >
              <MenuItem value="">All States</MenuItem>
              {TASK_STATES.map((s) => (
                <MenuItem key={s} value={s}>
                  {s.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase())}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
        {!folderMode && isServerPaginated && hasActiveFilters && (
          <Tooltip title="Reset all sorting and filters" arrow>
            <IconButton
              onClick={handleResetFilters}
              size="small"
              sx={{
                color: 'var(--text-secondary)',
                bgcolor: 'rgba(255, 255, 255, 0.05)',
                border: '1px solid rgba(255, 255, 255, 0.1)',
                borderRadius: 1,
                px: 1,
                py: 0.5,
                gap: 0.5,
                '&:hover': {
                  bgcolor: 'rgba(255, 255, 255, 0.1)',
                  color: 'var(--text-primary)',
                },
              }}
            >
              <FilterListOff sx={{ fontSize: 16 }} />
              <Typography sx={{ fontSize: FONT_SIZES.XS }}>Reset</Typography>
            </IconButton>
          </Tooltip>
        )}
        {!folderMode && columns.length > 0 && (
          <>
            <Tooltip title="Configure visible columns" arrow>
              <IconButton
                onClick={(e) => setColumnSelectorAnchor(e.currentTarget)}
                size="small"
                sx={{
                  color: visibleColumns ? 'var(--primary-main)' : 'var(--text-secondary)',
                  bgcolor: 'rgba(255, 255, 255, 0.05)',
                  border: '1px solid rgba(255, 255, 255, 0.1)',
                  borderRadius: 1,
                  px: 1,
                  py: 0.5,
                  gap: 0.5,
                  '&:hover': {
                    bgcolor: 'rgba(255, 255, 255, 0.1)',
                    color: 'var(--text-primary)',
                  },
                }}
              >
                <ViewColumn sx={{ fontSize: 16 }} />
                <Typography sx={{ fontSize: FONT_SIZES.XS }}>Columns</Typography>
              </IconButton>
            </Tooltip>
            <Popover
              open={Boolean(columnSelectorAnchor)}
              anchorEl={columnSelectorAnchor}
              onClose={() => setColumnSelectorAnchor(null)}
              anchorOrigin={{ vertical: 'bottom', horizontal: 'left' }}
              transformOrigin={{ vertical: 'top', horizontal: 'left' }}
              slotProps={{
                paper: {
                  sx: {
                    bgcolor: 'var(--bg-secondary)',
                    border: '1px solid rgba(255,255,255,0.1)',
                    borderRadius: 1,
                    p: 1,
                    minWidth: 180,
                  },
                },
              }}
            >
              <Typography
                sx={{
                  fontSize: FONT_SIZES.XS,
                  color: 'var(--text-secondary)',
                  px: 1,
                  pb: 0.5,
                }}
              >
                Toggle columns
              </Typography>
              <Divider sx={{ borderColor: 'rgba(255,255,255,0.08)', mb: 0.5 }} />
              {columns.map((col) => (
                <Box key={col} sx={{ px: 0.5 }}>
                  <FormControlLabel
                    control={
                      <Checkbox
                        size="small"
                        checked={(visibleColumns ?? columns).includes(col)}
                        onChange={() => handleToggleColumn(col)}
                        sx={{
                          p: 0.5,
                          color: 'var(--text-secondary)',
                          '&.Mui-checked': {
                            color: 'var(--primary-main)',
                          },
                        }}
                      />
                    }
                    label={
                      <Typography
                        sx={{
                          fontSize: FONT_SIZES.SM,
                          color: 'var(--text-primary)',
                        }}
                      >
                        {formatColumnName(col)}
                      </Typography>
                    }
                    sx={{ m: 0, width: '100%' }}
                  />
                </Box>
              ))}
              <Divider sx={{ borderColor: 'rgba(255,255,255,0.08)', mt: 0.5, mb: 0.5 }} />
              <Button
                size="small"
                onClick={handleClearColumnPrefs}
                disabled={!visibleColumns}
                sx={{
                  width: '100%',
                  fontSize: FONT_SIZES.XS,
                  color: 'var(--text-secondary)',
                  textTransform: 'none',
                  justifyContent: 'flex-start',
                  pl: 1,
                  '&:hover': {
                    color: 'var(--text-primary)',
                    bgcolor: 'rgba(255,255,255,0.05)',
                  },
                  '&.Mui-disabled': { color: 'rgba(255,255,255,0.2)' },
                }}
              >
                Reset to default
              </Button>
            </Popover>
          </>
        )}
        {/* Toolbar for task multi-select actions */}
        {!isMarketplaceCatalog &&
          catalogState.filteredFromItem?.item_type === 'folder.workflow' && (
            <>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 2, ml: 'auto' }}>
                <Typography sx={{ fontSize: FONT_SIZES.SM, color: 'var(--text-secondary)' }}>
                  UI actions
                </Typography>

                {/* Action Dropdown */}
                <FormControl size="small" sx={{ minWidth: 150 }}>
                  <Select
                    value={selectedUIAction}
                    IconComponent={ArrowDropDown}
                    sx={styles.itemsPerPageSelect}
                    MenuProps={{
                      MenuListProps: { dense: true },
                      PaperProps: {
                        sx: {
                          bgcolor: 'var(--bg-secondary)',
                          '& .MuiMenuItem-root': {
                            color: 'var(--text-primary)',
                            fontSize: FONT_SIZES.SM,
                            whiteSpace: 'nowrap',
                            minHeight: 'unset',
                            py: '4px',
                            px: '12px',
                            lineHeight: 1.5,
                            '&:hover': { bgcolor: COLORS.HOVER },
                            '&.Mui-selected': {
                              bgcolor: COLORS.SELECTED,
                              '&:hover': {
                                bgcolor: COLORS.SELECTED_HOVER,
                              },
                            },
                          },
                        },
                      },
                    }}
                  >
                    {attachedActions && attachedActions.uiActions.length === 0 ? (
                      <MenuItem
                        disabled
                        value=""
                        sx={{
                          fontStyle: 'italic',
                          color: 'var(--text-secondary)',
                        }}
                      >
                        No actions present, please check the config
                      </MenuItem>
                    ) : (
                      attachedActions?.uiActions.map((action) => (
                        <MenuItem
                          key={action.name}
                          value={action.name}
                          onClick={() => void handleSelectUIAction(action.name, action.metadata)}
                        >
                          {action.name}
                        </MenuItem>
                      ))
                    )}
                  </Select>
                </FormControl>
              </Box>
            </>
          )}

        {/* Bulk delete for folder mode — right-aligned to sit above the Actions column */}
        {folderMode && selectedTasks.length > 0 && (
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, ml: 'auto', mr: 2 }}>
            <Typography sx={{ fontSize: FONT_SIZES.SM, color: 'var(--text-secondary)' }}>
              {selectedTasks.length} selected
            </Typography>
            {!isMarketplaceCatalog &&
              currentItems.some(
                (i) =>
                  selectedTasks.includes(i.laui) &&
                  (i.item_type === 'payload' || i.item_type === 'skill'),
              ) && (
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={<CreateUsecaseIcon sx={{ fontSize: BUTTON_SIZES.ICON_FONT_SIZE }} />}
                  onClick={() => setBulkUsecaseOpen(true)}
                  sx={{
                    borderColor: '#4caf50',
                    color: '#4caf50',
                    textTransform: 'none',
                    fontSize: BUTTON_SIZES.FONT_SIZE,
                    fontWeight: BUTTON_SIZES.FONT_WEIGHT,
                    height: BUTTON_SIZES.HEIGHT,
                    padding: BUTTON_SIZES.PADDING,
                    borderRadius: BUTTON_SIZES.BORDER_RADIUS,
                    '& .MuiSvgIcon-root': {
                      fontSize: BUTTON_SIZES.ICON_FONT_SIZE,
                    },
                    '&:hover': {
                      borderColor: '#388e3c',
                      bgcolor: 'rgba(76,175,80,0.08)',
                    },
                  }}
                >
                  Create Usecase
                </Button>
              )}
            {deletePermission && (
              <Button
                variant="outlined"
                size="small"
                startIcon={<Delete sx={{ fontSize: BUTTON_SIZES.ICON_FONT_SIZE }} />}
                onClick={() => {
                  selectedTasks.forEach((laui) => {
                    const item = currentItems.find((i) => i.laui === laui);
                    if (item) {
                      const parentLaui = folderParentLaui ?? '';
                      const onSuccess = onDeleteSuccess ?? refreshFilteredList;
                      setDeleteModalState({
                        isOpen: true,
                        itemLaui: item.laui,
                        parentLaui,
                        itemName: item.name,
                        onSuccess: () => {
                          setSelectedTasks([]);
                          void onSuccess();
                        },
                        isPermanent: !!item.deleted_at,
                      });
                    }
                  });
                }}
                sx={{
                  borderColor: 'var(--error, #f44336)',
                  color: 'var(--error, #f44336)',
                  textTransform: 'none',
                  fontSize: BUTTON_SIZES.FONT_SIZE,
                  fontWeight: BUTTON_SIZES.FONT_WEIGHT,
                  height: BUTTON_SIZES.HEIGHT,
                  padding: BUTTON_SIZES.PADDING,
                  borderRadius: BUTTON_SIZES.BORDER_RADIUS,
                  '& .MuiSvgIcon-root': { fontSize: BUTTON_SIZES.ICON_FONT_SIZE },
                  '&:hover': {
                    borderColor: 'var(--error-dark, #d32f2f)',
                    bgcolor: 'rgba(244,67,54,0.08)',
                  },
                }}
              >
                Delete Selected
              </Button>
            )}
          </Box>
        )}

        {/* Toolbar for task multi-select actions */}
        {!isMarketplaceCatalog && isTaskType && !restoreAble && (
          <>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Typography sx={{ fontSize: FONT_SIZES.SM, color: 'var(--text-secondary)' }}>
                {selectedTasks.length > 0
                  ? `${selectedTasks.length} task(s) selected`
                  : 'Tasks control actions'}
              </Typography>

              {/* Action Dropdown */}
              <Tooltip
                open={showSelectTasksHint}
                title="Please select tasks first"
                placement="bottom"
                arrow
              >
                <FormControl size="small" sx={{ minWidth: 150 }}>
                  <Select
                    value={selectedTaskControlAction}
                    onChange={(e) => setSelectedTaskControlAction(e.target.value)}
                    open={taskControlSelectOpen}
                    onOpen={() => {
                      if (selectedTasks.length === 0) {
                        setShowSelectTasksHint(true);
                        setTimeout(() => setShowSelectTasksHint(false), 2000);
                      } else {
                        setTaskControlSelectOpen(true);
                      }
                    }}
                    onClose={() => setTaskControlSelectOpen(false)}
                    displayEmpty
                    IconComponent={ArrowDropDown}
                    sx={styles.itemsPerPageSelect}
                    MenuProps={{
                      MenuListProps: { dense: true },
                      PaperProps: {
                        sx: {
                          bgcolor: 'var(--bg-secondary)',
                          '& .MuiMenuItem-root': {
                            color: 'var(--text-primary)',
                            fontSize: FONT_SIZES.SM,
                            whiteSpace: 'nowrap',
                            minHeight: 'unset',
                            py: '4px',
                            px: '12px',
                            lineHeight: 1.5,
                            '&:hover': { bgcolor: COLORS.HOVER },
                            '&.Mui-selected': {
                              bgcolor: COLORS.SELECTED,
                              '&:hover': {
                                bgcolor: COLORS.SELECTED_HOVER,
                              },
                            },
                          },
                        },
                      },
                    }}
                  >
                    <MenuItem
                      value=""
                      disabled
                      sx={{
                        fontStyle: 'italic',
                        color: 'var(--text-secondary)',
                      }}
                    >
                      Select action
                    </MenuItem>
                    <MenuItem value="run">Run</MenuItem>
                    {attachedActions &&
                      attachedActions.taskControlActions.map((action) => (
                        <MenuItem key={action.name} value={action.name}>
                          {action.name}
                        </MenuItem>
                      ))}
                  </Select>
                </FormControl>
              </Tooltip>

              {selectedTasks.length > 0 && selectedTaskControlAction !== '' && (
                <Button
                  variant="outlined"
                  size="small"
                  startIcon={isRunningTasks ? <CircularProgress size={16} /> : <PlayArrow />}
                  onClick={() => void handleRunSelectedTasks()}
                  disabled={isRunningTasks}
                  sx={{
                    borderColor: 'var(--border)',
                    color: 'var(--text-primary)',
                    textTransform: 'none',
                    fontSize: BUTTON_SIZES.FONT_SIZE,
                    fontWeight: BUTTON_SIZES.FONT_WEIGHT,
                    height: BUTTON_SIZES.HEIGHT,
                    padding: BUTTON_SIZES.PADDING,
                    borderRadius: BUTTON_SIZES.BORDER_RADIUS,
                    '& .MuiSvgIcon-root': {
                      fontSize: BUTTON_SIZES.ICON_FONT_SIZE,
                    },
                    '&:hover': { borderColor: 'var(--accent)' },
                  }}
                >
                  {`${selectedTaskControlAction} Selected`}
                </Button>
              )}
            </Box>
          </>
        )}
      </Toolbar>
      <TableContainer
        component={Paper}
        sx={{
          ...(isTaskType ? styles.taskTableContainer : styles.tableContainer),
          overflowX: 'auto',
        }}
      >
        <Table sx={{ tableLayout: 'fixed', minWidth: '100%', width: 'max-content' }}>
          <TableHead sx={isTaskType ? styles.taskTableHead : styles.tableHead}>
            <TableRow>
              {!isMarketplaceCatalog && (
                <TableCell data-col="__checkbox__" padding="checkbox" sx={{ width: 40 }}>
                  <Checkbox
                    size="small"
                    checked={
                      currentItems.length > 0 && selectedTasks.length === currentItems.length
                    }
                    indeterminate={
                      selectedTasks.length > 0 && selectedTasks.length < currentItems.length
                    }
                    onChange={handleSelectAllTasks}
                    sx={{
                      p: 0.5,
                      color: 'var(--text-secondary)',
                      '&.Mui-checked': { color: 'var(--primary-main)' },
                      '&.MuiCheckbox-indeterminate': {
                        color: 'var(--primary-main)',
                      },
                    }}
                  />
                </TableCell>
              )}
              {groupingActive && (
                <TableCell data-col="__rownum__" align="center" sx={{ width: 44 }}>
                  #
                </TableCell>
              )}
              {displayColumns.map((column) => (
                <React.Fragment key={column}>
                  <TableCell
                    data-col={column}
                    sx={{
                      position: 'relative',
                      width:
                        columnWidths[column] ||
                        DEFAULT_COLUMN_WIDTHS[column] ||
                        DEFAULT_COLUMN_WIDTH_FALLBACK,
                    }}
                  >
                    <Box
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 0.25,
                      }}
                    >
                      {isTaskType && TASK_DATE_COLUMN_TOOLTIPS[column] ? (
                        <Tooltip title={TASK_DATE_COLUMN_TOOLTIPS[column]} placement="top" arrow>
                          <span
                            style={{
                              cursor: 'help',
                              borderBottom: '1px dotted currentColor',
                            }}
                          >
                            {formatColumnName(column)}
                          </span>
                        </Tooltip>
                      ) : (
                        formatColumnName(column)
                      )}
                      {isServerPaginated && SORTABLE_COLUMNS.has(column) && (
                        <IconButton
                          size="small"
                          onClick={() => handleSortChange(column)}
                          sx={{
                            p: 0.1,
                            color:
                              sortBy === column ? 'var(--primary-main)' : 'var(--text-secondary)',
                            '&:hover': {
                              color: 'var(--primary-main)',
                              bgcolor: 'transparent',
                            },
                          }}
                        >
                          {sortBy === column ? (
                            sortOrder === 'asc' ? (
                              <ArrowUpward sx={{ fontSize: 13 }} />
                            ) : (
                              <ArrowDownward sx={{ fontSize: 13 }} />
                            )
                          ) : (
                            <UnfoldMore sx={{ fontSize: 13 }} />
                          )}
                        </IconButton>
                      )}
                    </Box>
                    <Box
                      onMouseDown={(e) => handleResizeStart(column, e)}
                      sx={{
                        position: 'absolute',
                        right: 0,
                        top: '20%',
                        bottom: '20%',
                        width: 4,
                        cursor: 'col-resize',
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'center',
                        '&::before': {
                          content: '""',
                          position: 'absolute',
                          left: '50%',
                          top: 0,
                          bottom: 0,
                          width: 0.3,
                          backgroundColor: 'rgba(128,128,128,0.45)',
                          transform: 'translateX(-50%)',
                        },
                        '&:hover::before': {
                          backgroundColor: 'var(--primary-main)',
                          width: '1.5px',
                        },
                      }}
                    />
                  </TableCell>
                  {restoreAble && column === 'name' && <TableCell>Path</TableCell>}
                </React.Fragment>
              ))}
              <TableCell data-col="__actions__" sx={styles.actionsCell} align="right">
                Quick Actions
              </TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {loadingColumns || loadingItems ? (
              <TableRow>
                <TableCell colSpan={totalColumns} align="center" sx={{ py: 4 }}>
                  <CircularProgress size={24} sx={{ color: 'var(--text-secondary)' }} />
                </TableCell>
              </TableRow>
            ) : currentItems.length > 0 ? (
              currentItems.map((item, index) => {
                const groupStyle = dependencyGroups
                  ? TASK_DEPENDENCY_GROUP_COLORS[
                      (dependencyGroups.groupIndexByLaui.get(item.laui) ?? 0) %
                        TASK_DEPENDENCY_GROUP_COLORS.length
                    ]
                  : undefined;
                const orderInfo = dependencyGroups?.orderByLaui.get(item.laui);
                return (
                  <TableRow
                    key={item.laui || index}
                    sx={{
                      ...(isTaskType ? styles.taskTableRow : styles.tableRow),
                      ...(groupStyle
                        ? {
                            bgcolor: groupStyle.tint,
                            // solid left bar on the first cell; rows stack into one
                            // continuous bar per dependency group
                            '& > td:first-of-type': {
                              boxShadow: `inset 3px 0 0 0 ${groupStyle.bar}`,
                            },
                          }
                        : {}),
                    }}
                    onClick={(e) => handleView(item, e)}
                  >
                    {!isMarketplaceCatalog && (
                      <TableCell
                        padding="checkbox"
                        sx={{ width: 40 }}
                        onClick={(e) => e.stopPropagation()}
                      >
                        <Checkbox
                          size="small"
                          checked={selectedTasks.includes(item.laui)}
                          disabled={!canSelectTask(item)}
                          onChange={(e) => handleSelectTask(item.laui, e as any)}
                          onClick={(e) => e.stopPropagation()}
                          sx={{
                            p: 0.5,
                            color: 'var(--text-secondary)',
                            '&.Mui-checked': {
                              color: 'var(--primary-main)',
                            },
                            '&.Mui-disabled': {
                              color: 'var(--text-disabled)',
                              opacity: 0.3,
                            },
                          }}
                        />
                      </TableCell>
                    )}

                    {groupingActive && (
                      <TableCell
                        align="center"
                        sx={{
                          width: 44,
                          color: 'var(--text-secondary)',
                          fontSize: FONT_SIZES.XS,
                          fontVariantNumeric: 'tabular-nums',
                        }}
                      >
                        {index + 1}
                      </TableCell>
                    )}

                    {displayColumns.map((column) => {
                      const value = getColumnValue(item, column);
                      const fieldConfig = projectionConfig?.[column];
                      const shouldShowIcon =
                        fieldConfig?.display_type === 'status_icon' && fieldConfig?.enum_colors;
                      const isActionsStatus = column === 'actions_status';
                      const isStateCol = column === 'state' && isTaskType;
                      const isRecentRunsCol = column === RUNS_COLUMN && isTaskType;

                      const pillStyle =
                        isStateCol && value
                          ? (TASK_STATE_COLORS[
                              value.toLowerCase() as keyof typeof TASK_STATE_COLORS
                            ] ?? TASK_STATE_COLORS.scheduled)
                          : null;

                      const isFolderTypeCol = folderMode && column === 'item_type';
                      const folderTypeEntry = isFolderTypeCol
                        ? folderIconCache[item.item_type ?? '']
                        : undefined;
                      // For generate_history sessions, show the item type that was
                      // generated (action/operator/payload/agent/generate) instead of
                      // the literal "generate_history". chat_history is left untouched.
                      const folderTypeValue =
                        isFolderTypeCol && item.item_type === 'generate_history'
                          ? ((getRawColumnValue(item, 'created_item_type') as string) ?? value)
                          : value;

                      return (
                        <React.Fragment key={column}>
                          <TableCell
                            sx={{
                              overflow: 'hidden',
                              textOverflow: 'ellipsis',
                              whiteSpace: 'nowrap',
                              // Pin the runs column to its width so the strip
                              // scrolls inside the cell instead of widening it.
                              ...(isRecentRunsCol
                                ? (() => {
                                    const w =
                                      columnWidths[column] ||
                                      DEFAULT_COLUMN_WIDTHS[column] ||
                                      DEFAULT_COLUMN_WIDTH_FALLBACK;
                                    return { width: w, maxWidth: w };
                                  })()
                                : {}),
                            }}
                          >
                            {column === 'name' && orderInfo && (
                              <Tooltip
                                arrow
                                enterDelay={300}
                                title={
                                  orderInfo.groupSize > 1
                                    ? `Step ${orderInfo.posInGroup} of ${orderInfo.groupSize} in this dependency group — tasks run in this order; lower numbers are dependencies of the later ones.`
                                    : `Standalone task — no dependencies.`
                                }
                              >
                                <Box
                                  component="span"
                                  sx={{
                                    display: 'inline-flex',
                                    alignItems: 'center',
                                    justifyContent: 'center',
                                    minWidth: 18,
                                    height: 18,
                                    px: 0.5,
                                    mr: 0.75,
                                    borderRadius: '4px',
                                    bgcolor: groupStyle?.bar ?? 'var(--text-secondary)',
                                    color: COLORS.ON_ACCENT_DARK,
                                    fontSize: FONT_SIZES.XXS,
                                    fontWeight: FONT_WEIGHTS.WEIGHT_600,
                                    lineHeight: 1,
                                    verticalAlign: 'middle',
                                    flexShrink: 0,
                                  }}
                                >
                                  {orderInfo.posInGroup}
                                </Box>
                              </Tooltip>
                            )}
                            {isFolderTypeCol ? (
                              <Box
                                sx={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: 0.5,
                                }}
                              >
                                {folderTypeEntry?.icon
                                  ? React.createElement(folderTypeEntry.icon, {
                                      sx: {
                                        fontSize: 13,
                                        color: folderTypeEntry.color,
                                        flexShrink: 0,
                                      },
                                    })
                                  : item.item_type?.startsWith('folder') && (
                                      <Box
                                        component="span"
                                        sx={{
                                          fontSize: 13,
                                          color: 'var(--text-secondary)',
                                          flexShrink: 0,
                                          display: 'flex',
                                          alignItems: 'center',
                                        }}
                                      >
                                        📁
                                      </Box>
                                    )}
                                <Typography
                                  sx={{
                                    fontSize: FONT_SIZES.SM,
                                    color: folderTypeEntry?.color ?? 'var(--text-secondary)',
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap',
                                  }}
                                >
                                  {folderTypeValue}
                                </Typography>
                              </Box>
                            ) : !isMarketplaceCatalog && isActionsStatus ? (
                              <ActionsStatusBar
                                actions={getRawColumnValue(item, 'actions') as ActionsConfig | null}
                                actionsStatus={
                                  getRawColumnValue(item, 'actions_status') as ActionsStatus | null
                                }
                              />
                            ) : isStateCol && pillStyle ? (
                              <Box
                                sx={{
                                  display: 'inline-flex',
                                  alignItems: 'center',
                                  gap: 0.5,
                                  px: 1,
                                  py: 0.25,
                                  borderRadius: '999px',
                                  bgcolor: pillStyle.bg,
                                  border: `1px solid ${pillStyle.border}`,
                                }}
                              >
                                <Box
                                  sx={{
                                    width: 6,
                                    height: 6,
                                    borderRadius: '50%',
                                    bgcolor: pillStyle.dot,
                                    flexShrink: 0,
                                  }}
                                />
                                <Typography
                                  sx={{
                                    fontSize: FONT_SIZES.XS,
                                    fontWeight: FONT_WEIGHTS.WEIGHT_600,
                                    color: pillStyle.text,
                                    textTransform: 'uppercase',
                                    letterSpacing: '0.04em',
                                  }}
                                >
                                  {value}
                                </Typography>
                              </Box>
                            ) : isRecentRunsCol ? (
                              <RecentRunsStrip
                                taskLaui={item.laui}
                                refreshKey={runsRefreshKey}
                                frequency={item.frequency}
                                nextRunDate={item.next_run_date}
                                onRunClick={(sessionId) =>
                                  void handleViewItem(item, { itemTab: 'logs', sessionId })
                                }
                              />
                            ) : shouldShowIcon && value ? (
                              <Box
                                sx={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: 1,
                                }}
                              >
                                <Box
                                  sx={{
                                    width: 10,
                                    height: 10,
                                    borderRadius: '50%',
                                    backgroundColor: fieldConfig.enum_colors?.[value] || '#94a3b8',
                                    flexShrink: 0,
                                  }}
                                />
                                <span>{value}</span>
                              </Box>
                            ) : column === 'name' &&
                              item.marketplace_laui &&
                              !isMarketplaceCatalog ? (
                              <Box
                                sx={{
                                  display: 'flex',
                                  alignItems: 'center',
                                  gap: 1,
                                  minWidth: 0,
                                }}
                              >
                                <Box
                                  sx={{
                                    width: 28,
                                    height: 28,
                                    flexShrink: 0,
                                    borderRadius: 1,
                                    overflow: 'hidden',
                                  }}
                                >
                                  {item.image_url ? (
                                    <img
                                      src={item.image_url}
                                      width={28}
                                      height={28}
                                      style={{
                                        objectFit: 'cover',
                                        display: 'block',
                                      }}
                                    />
                                  ) : (
                                    <LAMarketplaceIcon
                                      size={28}
                                      color="var(--accent)"
                                      seed={item.marketplace_laui}
                                    />
                                  )}
                                </Box>
                                <Box sx={{ minWidth: 0 }}>
                                  <Typography
                                    sx={{
                                      fontSize: FONT_SIZES.SM,
                                      fontWeight: FONT_WEIGHTS.WEIGHT_600,
                                      color: 'var(--text-primary)',
                                      overflow: 'hidden',
                                      textOverflow: 'ellipsis',
                                      whiteSpace: 'nowrap',
                                      lineHeight: 1.3,
                                    }}
                                  >
                                    {value || '-'}
                                  </Typography>
                                  <Box
                                    sx={{
                                      display: 'flex',
                                      alignItems: 'center',
                                      gap: 0.5,
                                      mt: 0.25,
                                      flexWrap: 'wrap',
                                    }}
                                  >
                                    <Chip
                                      icon={
                                        <StorefrontIcon
                                          sx={{
                                            fontSize: '10px !important',
                                          }}
                                        />
                                      }
                                      label="From MP"
                                      variant="mp"
                                    />
                                    {item.publisher && (
                                      <Chip
                                        label={item.publisher}
                                        variant={
                                          item.publisher === 'LeastAction'
                                            ? 'official'
                                            : 'publisher'
                                        }
                                      />
                                    )}
                                  </Box>
                                </Box>
                              </Box>
                            ) : (
                              <Tooltip title={value || '-'} arrow enterDelay={500}>
                                <span>{value || '-'}</span>
                              </Tooltip>
                            )}
                          </TableCell>
                          {restoreAble && column === 'name' && (
                            <TableCell>
                              <Tooltip title={itemPaths[item.laui] || ''} arrow>
                                <Typography
                                  sx={{
                                    fontSize: FONT_SIZES.XS,
                                    color: 'var(--text-secondary)',
                                    maxWidth: 200,
                                    overflow: 'hidden',
                                    textOverflow: 'ellipsis',
                                    whiteSpace: 'nowrap',
                                  }}
                                >
                                  {itemPaths[item.laui] || '…'}
                                </Typography>
                              </Tooltip>
                            </TableCell>
                          )}
                        </React.Fragment>
                      );
                    })}
                    <TableCell sx={styles.actionsCell} align="right">
                      <Box sx={styles.actionButtons}>
                        {/* Run/Pause buttons for tasks */}
                        {!isMarketplaceCatalog && !item.deleted_at && shouldShowRunButton(item) && (
                          <Tooltip title={runButtonTooltipText(item)}>
                            <IconButton
                              sx={{
                                ...styles.iconButton,
                                color: 'var(--success-main)',
                                '&:hover': {
                                  color: 'var(--success-dark)',
                                },
                              }}
                              onClick={(e) => {
                                if (
                                  item.item_type === 'chat_history' ||
                                  item.item_type === 'generate_history'
                                ) {
                                  e.stopPropagation();
                                  void navigate({
                                    to: '/ai/create',
                                    search: {
                                      sessionId: item.name,
                                    },
                                  });
                                } else if (item.item_type === 'task') void handleRunTask(item, e);
                                else void handleRunAction(item, e);
                              }}
                              size="small"
                            >
                              <PlayArrow fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {!item.deleted_at && shouldShowPauseButton(item) && (
                          <Tooltip title="Pause Task">
                            <IconButton
                              sx={{
                                ...styles.iconButton,
                                color: 'var(--warning-main)',
                                '&:hover': {
                                  color: 'var(--warning-dark)',
                                },
                              }}
                              onClick={(e) => void handlePauseTask(item, e)}
                              size="small"
                            >
                              <Pause fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {/* Share button - shown for all items with permission */}
                        {!isMarketplaceCatalog &&
                          ['edit', 'own'].includes(item.permission) &&
                          !item.deleted_at && (
                            <Tooltip title="Share">
                              <IconButton
                                sx={{
                                  ...styles.iconButton,
                                  ...styles.editIcon,
                                }}
                                onClick={(e) => handleShare(item, e)}
                                size="small"
                              >
                                <Share fontSize="small" />
                              </IconButton>
                            </Tooltip>
                          )}
                        {deletePermission && !restoreAble && !item.deleted_at && (
                          <Tooltip title="Delete">
                            <IconButton
                              sx={{
                                ...styles.iconButton,
                                ...styles.deleteIcon,
                              }}
                              onClick={(e) => handleDelete(item, e)}
                              size="small"
                            >
                              <Delete fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {restoreAble && (
                          <Tooltip title="Restore">
                            <IconButton
                              sx={{
                                ...styles.iconButton,
                                ...styles.editIcon,
                              }}
                              onClick={(e) => handleRestore(item, e)}
                              size="small"
                            >
                              <Restore fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                        {isMarketplaceCatalog && (
                          <Tooltip title="Import">
                            <IconButton
                              sx={{
                                ...styles.iconButton,
                                ...styles.editIcon,
                              }}
                              onClick={(e) => void handleImport(item, e)}
                              size="small"
                            >
                              <ImportIcon fontSize="small" />
                            </IconButton>
                          </Tooltip>
                        )}
                      </Box>
                    </TableCell>
                  </TableRow>
                );
              })
            ) : (
              <TableRow>
                <TableCell colSpan={totalColumns} align="center" sx={{ py: 4 }}>
                  <EmptyState message="No items found" />
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>

        <Box sx={styles.paginationContainer}>
          <Box sx={styles.itemsPerPageContainer}>
            <Typography sx={styles.itemsPerPageLabel}>Items per page:</Typography>
            <FormControl size="small">
              <Select
                value={perPage}
                onChange={handleItemsPerPageChange}
                sx={styles.itemsPerPageSelect}
                MenuProps={{
                  PaperProps: {
                    sx: {
                      bgcolor: 'var(--bg-secondary)',
                      '& .MuiMenuItem-root': {
                        color: 'var(--text-primary)',
                        fontSize: FONT_SIZES.SM,
                        '&:hover': {
                          bgcolor: 'rgba(255, 255, 255, 0.08)',
                        },
                        '&.Mui-selected': {
                          bgcolor: 'rgba(255, 255, 255, 0.12)',
                          '&:hover': {
                            bgcolor: 'rgba(255, 255, 255, 0.16)',
                          },
                        },
                      },
                    },
                  },
                }}
              >
                {PAGE_SIZE_OPTIONS.map((size) => (
                  <MenuItem key={size} value={size}>
                    {size}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
          </Box>

          <Box sx={styles.paginationWrapper}>
            <Pagination
              currentPage={currentPageNum}
              hasNext={hasNext}
              hasPrevious={hasPrevious}
              onPageChange={handlePageChange}
            />
          </Box>

          {/* Empty box for flex spacing */}
          <Box sx={{ width: '140px' }} />
        </Box>
      </TableContainer>

      {folderMode && (
        <BulkPublishUsecaseModal
          open={bulkUsecaseOpen}
          onClose={() => {
            setBulkUsecaseOpen(false);
            setSelectedTasks([]);
          }}
          onSuccess={onUsecaseCreateSuccess}
          selectedLauis={selectedTasks}
          sourceType={
            currentItems.some((i) => selectedTasks.includes(i.laui) && i.item_type === 'skill')
              ? 'skill'
              : 'payload'
          }
          parentLaui={folderParentLaui}
          projectLaui={currentProjectLaui ?? undefined}
          accountLaui={accountLaui ?? undefined}
          mode="create"
        />
      )}
    </>
  );
}
