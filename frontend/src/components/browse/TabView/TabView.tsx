/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { type ReactNode, useEffect, useMemo, useState } from 'react';

import {
  Add as AddIcon,
  ChevronLeft as ChevronLeftIcon,
  ChevronRight as ChevronRightIcon,
  Close as CloseIcon,
  Edit as EditIcon,
  Download as ImportIcon,
  PlayArrow as PlayArrowIcon,
  CloudUpload as PublishIcon,
  Save as SaveIcon,
  WarningAmber as WarningAmberIcon,
} from '@mui/icons-material';
import {
  Box,
  Button,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
  DialogTitle,
  FormControl,
  IconButton,
  InputLabel,
  MenuItem,
  Select,
  Tab,
  Tabs,
  Typography,
} from '@mui/material';

import { ItemStatusChips, ItemTypeTooltip, TabPanel } from '@/components/ui';
import BaseModal from '@/components/ui/Modal/BaseModal';
import ValidationPanel from '@/components/validation/ValidationPanel';
import { BUTTON_SIZES, FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import { allowedItemTypes as allowedMartkeplaceItemTypes } from '@/constants/marketplace';
import type { RunActionModalDataType } from '@/contexts/ActionContext';
import { RunActionModalMode, useActionContext } from '@/contexts/ActionContext';
import { useCatalog } from '@/contexts/CatalogContext';
import { CatalogType, useGlobal } from '@/contexts/GlobalContext';
import { useMarketplace } from '@/contexts/MarketplaceContext';
import { useNotification } from '@/contexts/NotificationContext';
import type { TaskData } from '@/contexts/TaskModalContext';
import { TaskModalMode, useTaskModalContext } from '@/contexts/TaskModalContext';
import { useEditorHandlers } from '@/screens/Browse/handlers/editorHandlers';
import {
  getActualFilterType,
  getAvailableSubtypes,
  getTaskModalScopeType,
} from '@/screens/Browse/utils';
import { getCatalogItemById, getChildCatalogNodesByType } from '@/services/catalog.service';
import { publishItem as publishItemToMarketplace } from '@/services/marketplace.service';
import type { SchedulerResponse } from '@/services/scheduler.service';
import { dangerouslyResetTask } from '@/services/task.service';
import type { ValidationResult } from '@/services/validation.service';
import { validateCodeblock } from '@/services/validation.service';

import FieldRenderer, { TabFields } from '../FieldRenderer';
import { LauiDropdown } from '../FieldRenderer/LauiDropdown';
import SchedulerTab from '../SchedulerTab';
import OtherActionsDropdown from './OtherActionsDropdown';
import { WorkflowConfigField } from './WorkflowConfigField';
import { generateTabs, processFormData, renderHtmlTab } from './tabUtils';

// ===== STYLES =====
const styles = {
  // Main container
  container: {
    bgcolor: 'var(--bg-primary)',
    color: 'var(--text-primary)',
    height: 'calc(100vh - 150px)',
    display: 'flex',
    flexDirection: 'column',
    fontFamily: 'inherit',
  },

  // Header
  header: {
    px: 2.5,
    py: 2,
    borderBottom: '2px solid var(--border-color)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    gap: 2,
    bgcolor: 'var(--bg-secondary)',
    mb: 0,
  },
  headerTitle: {
    fontWeight: FONT_WEIGHTS.SEMIBOLD,
    fontSize: FONT_SIZES.BASE,
    color: 'var(--text-primary)',
  },
  headerButton: {
    borderColor: 'var(--border)',
    color: 'var(--text-primary)',
    fontSize: FONT_SIZES.BASE,
    textTransform: 'none',
    minWidth: 'auto',
    px: 2,
    py: 0,
    '&:hover': {
      borderColor: 'var(--accent)',
    },
  },
  saveButton: {
    bgcolor: 'var(--text-primary)',
    color: 'var(--bg-secondary)',
    textTransform: 'none' as const,
    fontWeight: FONT_WEIGHTS.SEMIBOLD,
    '&:hover': {
      bgcolor: 'var(--bg-secondary)',
      color: 'var(--text-primary)',
    },
    py: 0,
    px: 1.5,
  },

  // Tabs container
  tabsContainer: {
    borderBottom: 1,
    borderColor: 'var(--border)',
    overflowX: 'auto',
    bgcolor: 'var(--bg-secondary)',
    '&::-webkit-scrollbar': {
      height: '3px',
    },
    '&::-webkit-scrollbar-track': {
      background: 'var(--bg-secondary)',
    },
    '&::-webkit-scrollbar-thumb': {
      background: 'var(--border)',
      borderRadius: '2px',
    },
  },
  tabs: {
    minHeight: '32px',
    '& .MuiTab-root': {
      color: 'var(--text-secondary)',
      textTransform: 'none',
      fontSize: FONT_SIZES.XS,
      fontWeight: FONT_WEIGHTS.WEIGHT_400,
      minHeight: '32px',
      minWidth: 'auto',
      px: 2,
      py: 0,
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
  tabLabel: {
    fontSize: FONT_SIZES.XS,
  },

  // Content area
  content: {
    flex: 1,
    overflow: 'hidden',
    bgcolor: 'var(--bg-primary)',
    display: 'flex',
    flexDirection: 'column',
    minHeight: 0,
  },

  // Field containers
  arrayFieldContainer: {
    display: 'flex',
    flexDirection: 'column',
    gap: 1,
  },
  arrayItemContainer: {
    display: 'flex',
    gap: 1,
    alignItems: 'flex-start',
  },

  // TextField styles
  codeTextField: {
    '& .MuiOutlinedInput-root': {
      backgroundColor: 'var(--bg-tertiary)',
      color: 'var(--text-primary)',
      fontFamily: 'monospace',
      fontSize: FONT_SIZES.BASE,
      '& textarea': {
        fontSize: FONT_SIZES.BASE,
        lineHeight: '1.4',
      },
    },
  },
  readOnlyTextField: (isNameField: boolean) => ({
    '& .MuiOutlinedInput-root': {
      backgroundColor: isNameField ? 'var(--bg-secondary)' : 'var(--bg-tertiary)',
      color: 'var(--text-primary)',
      fontSize: FONT_SIZES.BASE,
    },
  }),
  textAreaField: (isCode: boolean, isReadOnly: boolean) => ({
    '& .MuiOutlinedInput-root': {
      backgroundColor: isReadOnly ? 'var(--bg-secondary)' : 'var(--bg-tertiary)',
      color: 'var(--text-primary)',
      fontFamily: isCode ? 'monospace' : 'inherit',
      fontSize: isCode ? FONT_SIZES.BASE : FONT_SIZES.MD,
      '& textarea': {
        fontSize: isCode ? FONT_SIZES.BASE : FONT_SIZES.MD,
        lineHeight: '1.4',
      },
    },
  }),

  // Typography styles
  fieldLabel: {
    mb: 1,
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
    fontSize: FONT_SIZES.BASE,
    color: 'var(--text-primary)',
  },
  fieldDescription: {
    mb: 2,
    color: 'var(--text-secondary)',
    fontSize: FONT_SIZES.BASE,
    lineHeight: '1.4',
  },
  viewModeText: {
    fontSize: FONT_SIZES.BASE,
    color: 'var(--text-primary)',
    whiteSpace: 'pre-wrap',
    lineHeight: '1.5',
  },
  emptyText: {
    color: 'var(--text-secondary)',
    fontStyle: 'italic',
  },

  // Button styles
  addButton: {
    alignSelf: 'flex-start',
    fontSize: FONT_SIZES.BASE,
  },

  // Dialog styles
  dialog: {
    '& .MuiDialog-paper': {
      bgcolor: 'var(--bg-secondary)',
      color: 'var(--text-primary)',
      fontSize: FONT_SIZES.BASE,
    },
  },
  dialogTitle: {
    fontSize: FONT_SIZES.BASE,
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
  },

  // Empty state
  emptyState: {
    textAlign: 'center',
    py: 4,
    color: 'var(--text-secondary)',
  },
  loadingContainer: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    height: '100vh',
    color: 'var(--text-secondary)',
  },
};
const isCodeBlockEmpty = (val: any): boolean => {
  if (!val) return true;
  if (typeof val === 'object' && !Array.isArray(val)) {
    return (
      Object.keys(val).length === 0 ||
      Object.values(val).every((v) => !v || (typeof v === 'string' && v.trim() === ''))
    );
  }
  if (Array.isArray(val)) return val.length === 0;
  return typeof val === 'string' && val.trim() === '';
};

const actionButtonStyle = {
  borderColor: 'var(--border)',
  color: 'var(--text-primary)',
  textTransform: 'none',
  fontSize: BUTTON_SIZES.FONT_SIZE,
  fontWeight: BUTTON_SIZES.FONT_WEIGHT,
  height: BUTTON_SIZES.HEIGHT,
  padding: BUTTON_SIZES.PADDING,
  borderRadius: BUTTON_SIZES.BORDER_RADIUS,
  '& .MuiSvgIcon-root': { fontSize: BUTTON_SIZES.ICON_FONT_SIZE },
  '&:hover': { borderColor: 'var(--accent)' },
};

const iconButtonStyle = {
  color: 'var(--text-primary)',
  '&:hover': { bgcolor: 'var(--bg-tertiary)' },
};

export default function TabView({ sidebar }: { sidebar?: ReactNode }) {
  const [tabValue, setTabValue] = useState(0);
  const [formData, setFormData] = useState<Record<string, any>>({});
  const [validationResult, setValidationResult] = useState<ValidationResult | null>(null);
  const [isValidating, setIsValidating] = useState(false);

  const { catalogType } = useGlobal();
  const { editorState, catalogState, setSaveConfirmModalState, setImportModalState } = useCatalog();
  const { showError, showSuccess } = useNotification();

  const schema = editorState.formSchema as any;
  const filterType = getActualFilterType(editorState, catalogState);
  const availableSubtypes = getAvailableSubtypes(
    filterType,
    editorState.formMode,
    catalogState.selectedItem!,
  );
  const mode = editorState.formMode;
  const itemData =
    editorState.formMode === 'edit' ? editorState.editingItem : editorState.viewingItem;

  const isMarketplaceCatalog = catalogType === CatalogType.MARKETPLACE;

  const { handleCancelCreate, handleEditorClose, handleEditItem } = useEditorHandlers();

  const { publishAccess } = useMarketplace();
  const isPublishable = allowedMartkeplaceItemTypes.includes(itemData?.item_type?.split('.')[0]);

  const [publishConfirmOpen, setPublishConfirmOpen] = useState(false);
  const [isPublishing, setIsPublishing] = useState(false);
  const [sidebarCollapsed, setSidebarCollapsed] = useState(false);

  const [resetConnectionModalOpen, setResetConnectionModalOpen] = useState(false);
  const [isResettingConnection, setIsResettingConnection] = useState(false);
  const [resetProgress, setResetProgress] = useState({ done: 0, total: 0 });

  const handleResetConnectionParallelism = async () => {
    if (!itemData?.laui) return;
    setIsResettingConnection(true);
    setResetProgress({ done: 0, total: 0 });
    try {
      const result = await getChildCatalogNodesByType(itemData.laui, 'task', 'own', false, 1, 1000);
      const taskItems = result.items ?? [];
      setResetProgress({ done: 0, total: taskItems.length });
      for (const taskItem of taskItems) {
        await dangerouslyResetTask(taskItem.item.laui);
        setResetProgress((prev) => ({ ...prev, done: prev.done + 1 }));
      }
      showSuccess(`Reset ${taskItems.length} task${taskItems.length !== 1 ? 's' : ''}`);
      setResetConnectionModalOpen(false);
      const updated = await getCatalogItemById(itemData.laui);
      setFormData(processFormData(updated));
    } catch {
      /* ignore */
    } finally {
      setIsResettingConnection(false);
    }
  };

  const handlePublishConfirmed = async () => {
    setPublishConfirmOpen(false);
    setIsPublishing(true);
    try {
      await publishItemToMarketplace(itemData);
      showSuccess('Item published to marketplace successfully');
    } catch (e: any) {
      showError(`Failed to publish: ${e.message}`);
    } finally {
      setIsPublishing(false);
    }
  };

  const baseFilterType = (filterType || '').split('.')[0];

  const { tabs, tabFields } = useMemo(
    () =>
      generateTabs(schema, {
        mode: mode ?? 'view',
        userUpdateFields: schema?.user_update_fields,
        filterType,
        includeScheduler: true,
        // Always show subtype for folder (may fall back to text input if no supported types loaded).
        // For other types (operator, connection), only show when subtypes actually exist.
        includeSubtypeField: filterType?.split('.')[0] === 'folder' || availableSubtypes.length > 0,
        viewSidebarTabs: ['Version', 'Metadata', 'Status', 'Marketplace Laui'],
      }),
    [schema, filterType, mode, availableSubtypes.length],
  );

  useEffect(() => {
    if (itemData?.item_type?.includes('html_report') && mode === 'view') {
      const htmlTabIndex = tabs.findIndex((t) => t === 'Html');
      if (htmlTabIndex !== -1) setTabValue(htmlTabIndex);
    }
  }, [tabs, itemData?.item_type, mode]);

  useEffect(() => {
    if ((mode === 'edit' || mode === 'view') && itemData) {
      setFormData(processFormData(itemData));
    } else if (mode === 'create') {
      const initialFormData: Record<string, any> = {};
      schema.columns.forEach((field: any) => {
        if (field.name === 'codeblock' || field.name === 'bashblock') {
          initialFormData[field.name] = field.default || {};
        } else if (field.datatype === 'array') {
          initialFormData[field.name] = field.default || [];
        } else if (field.datatype === 'object') {
          initialFormData[field.name] = field.default || field.sample_placeholder || {};
        } else if (field.name === 'item_type') {
          initialFormData[field.name] = filterType || field.default || '';
        } else {
          initialFormData[field.name] = field.default || '';
        }
      });
      if (availableSubtypes.length === 1) {
        const baseType = filterType?.split('.')[0] || '';
        const only = availableSubtypes[0];
        const subtypePart = only.startsWith(baseType + '.')
          ? only.slice(baseType.length + 1)
          : only;
        initialFormData['subtype'] = subtypePart;
      } else {
        initialFormData['subtype'] = '';
      }
      setFormData(initialFormData);
    }
  }, [schema, mode, itemData, filterType]);

  // Get the display name for the header
  const getDisplayName = () => {
    // Priority order for display name:
    // 1. Explicit itemName prop
    // 2. Name from formData (for edit/view modes)
    // 3. Fallback to schema name or filter type

    if (mode !== 'create' && formData?.name) {
      return formData.name;
    }
    return schema?.schemaName || filterType;
  };

  const displayName = getDisplayName();

  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    setTabValue(newValue);
    // Fetch fresh scheduler data when switching to the Scheduler tab
    if (tabs[newValue] === 'Scheduler' && itemData?.laui) {
      void getCatalogItemById(itemData.laui).then((updatedData) => {
        setFormData((prev) => ({
          ...prev,
          folder_metadata: updatedData.folder_metadata || null,
        }));
      });
    }
  };

  const handleFieldChange = (fieldName: string, value: any) => {
    setFormData((prev) => ({
      ...prev,
      [fieldName]: value,
    }));
    if (fieldName === 'codeblock') {
      // Invalidate prior validation when user edits the code
      setValidationResult(null);
    }
  };

  const handleValidateCodeblock = async () => {
    if (!formData?.codeblock) return;
    setIsValidating(true);
    try {
      const result = await validateCodeblock(formData.codeblock, filterType);
      setValidationResult(result);
    } catch (e: any) {
      const msg = (e?.message || '').includes('valid dictionary')
        ? 'Input should contain at least 1 valid file'
        : e?.message || 'Validation request failed';
      setValidationResult({
        valid: false,
        errors: [{ code: 'REQUEST_FAILED', message: msg, file: null, line: null }],
        warnings: [],
      });
    } finally {
      setIsValidating(false);
    }
  };

  const supportsCodeblockValidation = baseFilterType === 'operator' || baseFilterType === 'action';

  const handleSaveClick = () => {
    const processedData = { ...formData };
    if (filterType.startsWith('folder') && typeof processedData.folder_metadata === 'string') {
      try {
        processedData.folder_metadata = JSON.parse(processedData.folder_metadata);
      } catch {
        processedData.folder_metadata = { value: processedData.folder_metadata };
      }
    }
    // Construct item_type from base type + subtype for create and edit modes
    if (mode === 'create' || mode === 'edit') {
      const baseItemType = filterType?.split('.')[0] || filterType;
      const subtype = processedData.subtype?.trim();
      if (subtype && subtype !== 'default') {
        processedData.item_type = `${baseItemType}.${subtype}`;
      } else {
        processedData.item_type = baseItemType;
      }
      delete processedData.subtype;
    }
    // Ensure codeblock/bashblock are objects, not empty arrays
    ['codeblock', 'bashblock'].forEach((key) => {
      if (Array.isArray(processedData[key])) {
        processedData[key] = {};
      }
    });

    // Validate required codeblock/bashblock fields — block save if empty
    if (mode === 'create' || mode === 'edit') {
      const codeBlockFieldNames = new Set(['codeblock', 'bashblock']);
      const requiredCodeFields = (schema?.columns ?? []).filter(
        (f: any) => codeBlockFieldNames.has(f.name) && f.required,
      );
      for (const f of requiredCodeFields) {
        if (isCodeBlockEmpty(processedData[f.name])) {
          return;
        }
      }
    }

    if (mode === 'create') {
      if (catalogState.filteredFromItem) {
        processedData.parent_laui = catalogState.filteredFromItem.laui;
      } else if (catalogState.selectedItem?.item_type?.startsWith('folder')) {
        processedData.parent_laui = catalogState.selectedItem.laui;
      } else if (catalogState.openedFolder) {
        processedData.parent_laui = catalogState.openedFolder.laui;
      }
    } else if (mode === 'edit' && editorState.editingItem?.laui) {
      processedData.parent_laui = editorState.editingItem.parent_laui || null;
    }
    setSaveConfirmModalState({
      isOpen: true,
      itemName: displayName,
      itemType: filterType,
      saveData: processedData,
      mode: mode,
    });
  };

  const onImport = () => {
    setImportModalState({ isOpen: true, itemData: editorState.viewingItem });
  };

  const onCancel = () => {
    if (mode === 'view') handleEditorClose();
    else handleCancelCreate();
  };

  const { setTaskModalState } = useTaskModalContext();
  // Task button handlers
  const handleCreateTaskClick = () => {
    taskModalOpen(TaskModalMode.CREATE);
  };

  const taskModalOpen = (taskModalMode: TaskModalMode) => {
    let operatorLaui, payloadLaui, payloadValue, connectionLaui, initialTaskData;
    if (itemData) {
      operatorLaui =
        filterType === 'task'
          ? formData.operator_laui
          : filterType.includes('operator')
            ? itemData.laui
            : undefined;
      payloadLaui = filterType.includes('payload') ? itemData.laui : undefined;
      payloadValue = filterType.includes('payload')
        ? (() => {
            const raw = formData.content ?? formData.payload;
            if (raw == null || raw === '') return undefined;
            return typeof raw === 'string' ? raw : JSON.stringify(raw, null, 2);
          })()
        : undefined;
      connectionLaui = filterType.includes('connection') ? itemData.laui : undefined;
      initialTaskData =
        itemData?.item_type?.includes('workflow') &&
        itemData?.laui &&
        ((itemData as { parent_laui?: string })?.parent_laui ?? formData?.parent_laui)
          ? ({
              workflow_laui: itemData.laui,
              project_laui: String(
                (itemData as { parent_laui?: string }).parent_laui ?? formData.parent_laui,
              ),
            } as TaskData)
          : undefined;
    }
    setTaskModalState({
      isOpen: true,
      mode: taskModalMode,
      scope: {
        scopeType: getTaskModalScopeType(filterType),
        operatorLaui,
        connectionLaui,
        payloadLaui,
        payloadValue,
      },
      initialTaskData,
    });
  };

  const { setRunActionModalData } = useActionContext();
  const handleRunActionClick = async () => {
    if (!itemData) return;
    const actionData = await getCatalogItemById(itemData.laui);
    setRunActionModalData({
      actionLaui: itemData.laui,
      isOpen: true,
      actionVariables: actionData.action_variables,
      mode: RunActionModalMode.RUN,
    } as RunActionModalDataType);
  };

  const renderFieldInput = (field: any) => {
    const value = formData[field.name] ?? '';

    // Add Config flow: dropdown to attach an existing config instead of creating a new one
    if (field.name === 'existing_config_laui') {
      return (
        <LauiDropdown
          fieldName="config_laui"
          value={value}
          onChange={(_, configLaui) => handleFieldChange('existing_config_laui', configLaui)}
        />
      );
    }

    // Attach-config field: only meaningful for workflow folders during creation
    if (field.name === 'attached_config') {
      const baseType = filterType?.split('.')[0] || '';
      const isWorkflow =
        filterType === 'folder.workflow' ||
        (baseType === 'folder' && formData.subtype === 'workflow');
      if ((mode !== 'create' && mode !== 'edit') || !isWorkflow) return null;
      return (
        <WorkflowConfigField
          value={formData.attached_config}
          onChange={handleFieldChange}
          defaultName={formData.name}
        />
      );
    }

    // Subtype dropdown for folder/operator/connection when we have options
    const isSubtypeField = field.name === 'subtype';
    if (isSubtypeField && availableSubtypes.length > 0) {
      const baseType = filterType?.split('.')[0] || '';
      const options = availableSubtypes.map((fullType: string) => {
        const subtypePart = fullType.startsWith(baseType + '.')
          ? fullType.slice(baseType.length + 1)
          : fullType;
        return { value: subtypePart, label: subtypePart };
      });
      if (mode === 'create') {
        // Single option: auto-filled, show as read-only
        if (availableSubtypes.length === 1) {
          return (
            <Typography sx={{ ...styles.viewModeText, py: 1 }}>
              {value || options[0]?.label || '—'}
            </Typography>
          );
        }
        return (
          <FormControl fullWidth size="small" sx={{ minWidth: 200 }}>
            <InputLabel id="subtype-select-label">Subtype</InputLabel>
            <Select
              labelId="subtype-select-label"
              value={value || ''}
              label="Subtype"
              onChange={(e) => handleFieldChange('subtype', e.target.value)}
              sx={{
                bgcolor: 'var(--bg-tertiary)',
                color: 'var(--text-primary)',
                '& .MuiOutlinedInput-notchedOutline': {
                  borderColor: 'var(--border)',
                },
                '&:hover .MuiOutlinedInput-notchedOutline': {
                  borderColor: 'var(--accent)',
                },
              }}
            >
              <MenuItem value="">
                <em>Select subtype</em>
              </MenuItem>
              {options.map((opt: { value: string; label: string }) => (
                <MenuItem
                  key={opt.value}
                  value={opt.value}
                  sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}
                >
                  {opt.label}
                  <ItemTypeTooltip itemType={`${baseType}.${opt.value}`} />
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        );
      }
      // View: show as read-only text
      return <Typography sx={{ ...styles.viewModeText, py: 1 }}>{value || '—'}</Typography>;
    }

    const effectiveMode = isSubtypeField && mode === 'view' ? 'view' : mode;
    return (
      <FieldRenderer
        field={field}
        value={value}
        mode={effectiveMode!}
        onChange={handleFieldChange}
        itemData={itemData}
      />
    );
  };

  const renderTabContent = (tabName: string) => {
    if (tabName === 'Html' && mode === 'view') {
      return renderHtmlTab(itemData);
    }

    // Special handling for Scheduler tab
    if (tabName === 'Scheduler' && itemData?.laui) {
      const schedulerData: SchedulerResponse | null = formData?.folder_metadata || null;
      return (
        <SchedulerTab
          projectLaui={itemData.laui}
          schedulerData={schedulerData}
          onRefresh={() => {
            // Refresh the item data
            if (itemData?.laui) {
              void getCatalogItemById(itemData.laui).then((updatedData) => {
                setFormData((prev) => ({
                  ...prev,
                  folder_metadata: updatedData.folder_metadata || null,
                }));
              });
            }
          }}
        />
      );
    }

    let fields = tabFields[tabName] || [];

    // The synthetic attach-config field only applies to workflow folders during creation.
    // Drop it entirely (label + row) otherwise so no empty section is shown.
    if (fields.some((f: any) => f.name === 'attached_config')) {
      const baseType = filterType?.split('.')[0] || '';
      const isWorkflow =
        filterType === 'folder.workflow' ||
        (baseType === 'folder' && formData.subtype === 'workflow');
      if ((mode !== 'create' && mode !== 'edit') || !isWorkflow) {
        fields = fields.filter((f: any) => f.name !== 'attached_config');
      }
    }

    const hasCodeblockField = fields.some((f: any) => f.name === 'codeblock');
    const showValidate =
      hasCodeblockField && supportsCodeblockValidation && (mode === 'edit' || mode === 'create');

    const validationHeader = showValidate ? (
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1.5, mb: 0 }}>
        {validationResult && (
          <Box sx={{ flexGrow: 1, minWidth: 0 }}>
            <ValidationPanel result={validationResult} />
          </Box>
        )}
        <Button
          size="small"
          variant="outlined"
          onClick={() => void handleValidateCodeblock()}
          disabled={isValidating || !formData?.codeblock}
          sx={{
            textTransform: 'none',
            borderColor: 'var(--border)',
            color: 'var(--text-primary)',
            '&:hover': { borderColor: 'var(--primary-main)' },
            flexShrink: 0,
            marginLeft: 'auto',
          }}
        >
          {isValidating ? 'Validating...' : 'Validate'}
        </Button>
      </Box>
    ) : undefined;

    return (
      <TabFields
        fields={fields}
        formData={formData}
        mode={mode!}
        renderField={(field) => renderFieldInput(field)}
        headerContent={validationHeader}
      />
    );
  };

  if (!schema?.columns) {
    return (
      <Box sx={styles.loadingContainer}>
        <Typography>Loading schema...</Typography>
      </Box>
    );
  }

  let publishLabel = 'Publish';
  if (isPublishing) publishLabel = 'Publishing…';
  else if (itemData?.is_published) publishLabel = 'Publish New Version';

  return (
    <>
      <Box sx={styles.container}>
        {/* Header - UPDATED WITH ITEM NAME */}
        <Box sx={styles.header}>
          {/* Left: title + status chips */}
          <Box
            sx={{
              flex: 1,
              minWidth: 0,
              display: 'flex',
              flexDirection: 'column',
              gap: 0.75,
            }}
          >
            <Typography
              variant="h5"
              title={displayName}
              sx={{
                color: 'var(--text-primary)',
                fontWeight: 700,
                lineHeight: 1.2,
                overflow: 'hidden',
                textOverflow: 'ellipsis',
                whiteSpace: 'nowrap',
              }}
            >
              {mode === 'create' ? 'Create New' : mode === 'edit' ? 'Edit:' : ''} {displayName}
            </Typography>
            {itemData && (
              <ItemStatusChips
                itemType={itemData.item_type}
                marketplaceLaui={itemData.marketplace_laui}
                isPublished={itemData.is_published}
                hasUnpublishedChanges={itemData.has_unpublished_changes}
              />
            )}
          </Box>

          {/* Right: action buttons — never squeeze the title */}
          <Box sx={{ display: 'flex', gap: 1, alignItems: 'center', flexShrink: 0 }}>
            {mode === 'view' && itemData && !itemData.deleted_at && (
              <>
                {/* Operator / Payload / Connection Actions */}
                {!isMarketplaceCatalog &&
                  ['operator', 'payload', 'connection'].some((type) =>
                    filterType.includes(type),
                  ) && (
                    <Button
                      onClick={handleCreateTaskClick}
                      size="small"
                      variant="outlined"
                      startIcon={<AddIcon />}
                      sx={actionButtonStyle}
                    >
                      Create Task
                    </Button>
                  )}

                {/* Reset Connection Parallelism */}
                {!isMarketplaceCatalog && filterType.includes('connection') && (
                  <Button
                    onClick={() => setResetConnectionModalOpen(true)}
                    size="small"
                    variant="outlined"
                    startIcon={<WarningAmberIcon />}
                    sx={{
                      ...actionButtonStyle,
                      borderColor: '#ef4444',
                      color: '#ef4444',
                      '&:hover': {
                        borderColor: '#dc2626',
                        bgcolor: 'rgba(239,68,68,0.08)',
                      },
                    }}
                  >
                    Reset Parallelism
                  </Button>
                )}

                {/* Action Specific Run */}
                {!isMarketplaceCatalog && itemData.item_type?.split('.')[0] === 'action' && (
                  <Button
                    onClick={() => void handleRunActionClick()}
                    size="small"
                    variant="outlined"
                    startIcon={<PlayArrowIcon />}
                    sx={actionButtonStyle}
                  >
                    Run Action
                  </Button>
                )}

                {!isMarketplaceCatalog && publishAccess && isPublishable && (
                  <Button
                    onClick={() => setPublishConfirmOpen(true)}
                    disabled={isPublishing}
                    size="small"
                    variant="outlined"
                    startIcon={<PublishIcon />}
                    sx={{
                      ...actionButtonStyle,
                      color: '#4caf50',
                      borderColor: '#4caf50',
                      '&:hover': { borderColor: '#388e3c', color: '#388e3c' },
                    }}
                  >
                    {publishLabel}
                  </Button>
                )}

                {['edit', 'own'].includes(itemData.permission) && (
                  <>
                    <Button
                      onClick={() => void handleEditItem(itemData)}
                      size="small"
                      variant="outlined"
                      startIcon={<EditIcon />}
                      sx={actionButtonStyle}
                    >
                      Edit
                    </Button>
                    <OtherActionsDropdown item={itemData} />
                  </>
                )}
              </>
            )}

            {isMarketplaceCatalog && (
              <IconButton onClick={onImport} sx={iconButtonStyle}>
                <ImportIcon />
              </IconButton>
            )}

            {mode !== 'view' && (
              <>
                <IconButton onClick={onCancel} sx={iconButtonStyle}>
                  <CloseIcon />
                </IconButton>
                <IconButton onClick={handleSaveClick} sx={iconButtonStyle}>
                  <SaveIcon />
                </IconButton>
              </>
            )}
          </Box>
        </Box>

        {/* Tabs + sidebar below header */}
        <Box sx={{ display: 'flex', flex: 1, minHeight: 0 }}>
          <Box sx={{ flex: 1, minWidth: 0, display: 'flex', flexDirection: 'column' }}>
            {/* Dynamic Tabs — hidden when only one tab */}
            <Box sx={tabs.length <= 1 ? { display: 'none' } : styles.tabsContainer}>
              <Tabs
                value={tabValue}
                onChange={handleTabChange}
                variant="scrollable"
                scrollButtons="auto"
                sx={styles.tabs}
              >
                {tabs.map((tabName, index) => {
                  const hasRequired =
                    mode !== 'view' && (tabFields[tabName] || []).some((f: any) => f.required);
                  return (
                    <Tab
                      key={index}
                      label={
                        hasRequired ? (
                          <Box
                            component="span"
                            sx={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: 0.3,
                            }}
                          >
                            {tabName}
                            <Box
                              component="span"
                              sx={{
                                color: 'var(--error)',
                                lineHeight: 1,
                              }}
                            >
                              *
                            </Box>
                          </Box>
                        ) : (
                          tabName
                        )
                      }
                      sx={styles.tabLabel}
                    />
                  );
                })}
              </Tabs>
            </Box>

            {/* Tab Content */}
            <Box sx={styles.content}>
              {tabs.map((tabName, index) => (
                <TabPanel key={tabName} value={tabValue} index={index}>
                  {renderTabContent(tabName)}
                </TabPanel>
              ))}
            </Box>
          </Box>

          {/* Sidebar — rendered here so it starts below the header */}
          {sidebar && mode === 'view' && (
            <Box
              sx={{
                width: sidebarCollapsed ? 24 : 260,
                flexShrink: 0,
                borderLeft: '1px solid var(--border-color)',
                bgcolor: 'var(--bg-secondary)',
                overflow: 'hidden',
                display: 'flex',
                flexDirection: 'row',
                transition: 'width 0.2s ease',
              }}
            >
              {/* Collapse toggle strip */}
              <Box
                onClick={() => setSidebarCollapsed((v) => !v)}
                sx={{
                  width: 24,
                  flexShrink: 0,
                  display: 'flex',
                  alignItems: 'flex-start',
                  pt: 0.5,
                  cursor: 'pointer',
                  '&:hover': { bgcolor: 'var(--bg-primary)' },
                }}
              >
                <IconButton
                  size="small"
                  sx={{ p: 0.25, color: 'var(--text-secondary)' }}
                  tabIndex={-1}
                >
                  {sidebarCollapsed ? (
                    <ChevronLeftIcon fontSize="small" />
                  ) : (
                    <ChevronRightIcon fontSize="small" />
                  )}
                </IconButton>
              </Box>

              {/* Sidebar content */}
              {!sidebarCollapsed && (
                <Box sx={{ flex: 1, overflow: 'auto', minWidth: 0 }}>{sidebar}</Box>
              )}
            </Box>
          )}
        </Box>
      </Box>

      {/* Pre-publish confirmation */}
      <Dialog
        open={publishConfirmOpen}
        onClose={() => setPublishConfirmOpen(false)}
        PaperProps={{
          sx: { bgcolor: 'var(--bg-secondary)', color: 'var(--text-primary)' },
        }}
      >
        <DialogTitle sx={{ fontSize: '15px', fontWeight: 600 }}>
          {itemData?.is_published ? 'Publish new version?' : 'Make this item public?'}
        </DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
            {itemData?.is_published ? (
              <>
                Pushing a new version of{' '}
                <strong style={{ color: 'var(--text-primary)' }}>{itemData?.name}</strong> will
                update the listing for all Marketplace users.
              </>
            ) : (
              <>
                Publishing{' '}
                <strong style={{ color: 'var(--text-primary)' }}>{itemData?.name}</strong> will make
                it visible to all Marketplace users. This action cannot be undone from here.
              </>
            )}
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 2, pb: 2, gap: 1 }}>
          <Button
            size="small"
            variant="outlined"
            onClick={() => setPublishConfirmOpen(false)}
            sx={{ color: 'var(--text-secondary)', borderColor: 'var(--border)' }}
          >
            Cancel
          </Button>
          <Button
            size="small"
            variant="contained"
            onClick={() => void handlePublishConfirmed()}
            startIcon={<PublishIcon />}
            sx={{
              bgcolor: '#4caf50',
              color: '#fff',
              '&:hover': { bgcolor: '#388e3c' },
            }}
          >
            {itemData?.is_published ? 'Yes, Push Update' : 'Yes, Publish'}
          </Button>
        </DialogActions>
      </Dialog>
      <BaseModal
        open={resetConnectionModalOpen}
        onClose={() => !isResettingConnection && setResetConnectionModalOpen(false)}
        title="Reset Connection Parallelism"
        subtitle="This will reset all queued tasks back to scheduled"
        maxWidth="sm"
        actions={
          <>
            <Button
              onClick={() => setResetConnectionModalOpen(false)}
              disabled={isResettingConnection}
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
              onClick={() => void handleResetConnectionParallelism()}
              disabled={isResettingConnection}
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
              {isResettingConnection
                ? `Resetting… (${resetProgress.done}/${resetProgress.total})`
                : 'Reset Parallelism'}
            </Button>
          </>
        }
      >
        <Box sx={{ mt: 1 }}>
          <Typography sx={{ color: 'var(--text-primary)', mb: 1 }}>
            Reset <strong>{itemData?.name}</strong> and release all queued tasks back to{' '}
            <strong>scheduled</strong>.
          </Typography>
          {itemData?.current_parallelism != null && (
            <Typography sx={{ color: 'var(--text-secondary)', fontSize: '13px' }}>
              Current parallelism: <strong>{itemData.current_parallelism}</strong> — In queue:{' '}
              <strong>{itemData.in_queue ?? 0}</strong>
            </Typography>
          )}
        </Box>
      </BaseModal>
    </>
  );
}
