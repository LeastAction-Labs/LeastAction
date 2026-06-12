/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useMemo, useRef, useState } from 'react';

import { useNavigate } from '@tanstack/react-router';

import ArrowForwardIcon from '@mui/icons-material/ArrowForward';
import CancelIcon from '@mui/icons-material/Cancel';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import { Box, Button, LinearProgress, Stack, TextField, Tooltip, Typography } from '@mui/material';

import type {
  ParsedPayload,
  TaskCreationResult,
} from '@/components/marketplace/UsecaseImportModal/types';
import {
  buildActionList,
  deriveTaskName,
  parseAllPayloads,
} from '@/components/marketplace/UsecaseImportModal/usecaseParser';
import { QuickSearch } from '@/components/ui';
import BaseModal from '@/components/ui/Modal/BaseModal';
import { useCatalog } from '@/contexts/CatalogContext';
import { CatalogType, useGlobal } from '@/contexts/GlobalContext';
import { useNotification } from '@/contexts/NotificationContext';
import { createCatalogItem, getUniqueConstraints, searchCatalogItems } from '@/services';
import { createPK } from '@/services/utils';
import { validateCodeblock } from '@/services/validation.service';

import type { FullItemData } from '../types';

export interface ImportModalData {
  itemData?: FullItemData;
  isOpen: boolean;
  usecaseImportMode?: 'files' | 'tasks';
  usecaseDepCache?: Map<string, string>;
  usecaseDepsResolved?: boolean;
}

const styles = {
  textField: {
    mb: 2,
    '& .MuiOutlinedInput-root': {
      backgroundColor: 'var(--bg-secondary)',
      color: 'var(--text-primary)',
      fontSize: '12px',
      '& fieldset': {
        borderColor: 'var(--border)',
      },
      '&:hover fieldset': {
        borderColor: 'var(--primary-main)',
      },
      '&.Mui-focused fieldset': {
        borderColor: 'var(--primary-main)',
      },
    },
    '& .MuiInputBase-input.Mui-disabled': {
      color: 'var(--text-primary) !important',
      WebkitTextFillColor: 'var(--text-primary) !important',
      opacity: 1,
    },
    '& .MuiInputLabel-root': {
      color: 'var(--text-secondary)',
      fontSize: '12px',
    },
    '& .MuiFormHelperText-root': {
      fontSize: '11px',
      color: 'var(--text-secondary)',
      mt: 0.5,
    },
    '& .MuiAutocomplete-popupIndicator': {
      color: 'var(--text-secondary)',
    },
    '& .MuiAutocomplete-clearIndicator': {
      color: 'var(--text-secondary)',
    },
  },
};

export default function ImportModal() {
  const { accountLaui, currentProjectLaui, setCatalogType } = useGlobal();
  const { importModalState, setImportModalState } = useCatalog();
  const { showSuccess, showError } = useNotification();
  const navigate = useNavigate();

  const { itemData, isOpen, usecaseImportMode, usecaseDepCache, usecaseDepsResolved } =
    importModalState;

  const [requiredFields, setRequiredFields] = useState<string[]>([]);
  const [formValues, setFormValues] = useState<any>({});
  const [conflictItem, setConflictItem] = useState<any>(null);
  const [newName, setNewName] = useState('');
  const [mode, setMode] = useState<string | null>(null);
  const [parentLauiInPK, setParentLauiInPK] = useState(true);
  const [importedItem, setImportedItem] = useState<{
    name: string;
    parent_laui: string;
    item_type: string;
  } | null>(null);

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  // --- Usecase-specific state ---
  // usecaseMode is driven by usecaseImportMode from the modal state (set externally),
  // or falls back to local state for backward compat (e.g. search panel)
  const [usecaseModeFallback, setUsecaseModeFallback] = useState<'files' | 'tasks' | null>(null);
  const usecaseMode = usecaseImportMode ?? usecaseModeFallback;
  const [parsedPayloads, setParsedPayloads] = useState<ParsedPayload[]>([]);
  const [taskProjectLaui, setTaskProjectLaui] = useState('');
  const [importProjectLaui, setImportProjectLaui] = useState('');
  const [taskPartition, setTaskPartition] = useState('ALL');
  const [taskWorkflowLaui, setTaskWorkflowLaui] = useState('');
  const [taskStartDate, setTaskStartDate] = useState('');
  const [taskEndDate, setTaskEndDate] = useState('');
  const [taskResults, setTaskResults] = useState<TaskCreationResult[]>([]);
  const [taskProgress, setTaskProgress] = useState(0);
  const [creatingTasks, setCreatingTasks] = useState(false);
  // Use dep cache from the UsecaseDepsDialog (passed via importModalState)
  const depCacheRef = useRef<Map<string, string>>(new Map());

  const isUsecase = itemData?.item_type === 'usecase';
  const isSkillUsecase =
    isUsecase &&
    Array.isArray((itemData as any)?.tags) &&
    (itemData as any).tags.some(
      (t: string) => t.toLowerCase() === 'skill' || t.toLowerCase() === 'skills',
    );

  // Sync dep cache from external source (UsecaseDepsDialog)
  useEffect(() => {
    if (usecaseDepCache) {
      depCacheRef.current = new Map(usecaseDepCache);
    }
  }, [usecaseDepCache]);

  const getItemType = (fieldName: string): string => {
    const normalizedFieldName = fieldName.toLowerCase().replace(/[_\s]/g, '');

    if (normalizedFieldName === 'accountlaui') {
      return 'folder.account';
    } else if (normalizedFieldName === 'projectlaui') {
      return 'folder.project';
    } else if (normalizedFieldName === 'workflowfolderlaui') {
      return 'folder.workflow';
    } else {
      const match = fieldName.match(/^(.+?)(_?lauis?)$/i);
      if (match) {
        return match[1].toLowerCase();
      }
      return fieldName.replace(/_?lauis?$/i, '').toLowerCase();
    }
  };

  // State for payload parent folder (used in files & tasks modes)
  const [payloadParentLaui, setPayloadParentLaui] = useState('');
  // State for skill parent folder (used in skill usecase import)
  const [skillParentLaui, setSkillParentLaui] = useState('');

  // Determine target item type for constraints based on usecase mode
  const targetItemType = isUsecase
    ? usecaseMode === 'files'
      ? 'payload'
      : usecaseMode === 'tasks'
        ? 'task'
        : itemData?.item_type || ''
    : itemData?.item_type || '';

  useEffect(() => {
    if (isOpen) {
      const init = async () => {
        setLoading(true);
        try {
          const fields = await getUniqueConstraints(targetItemType);
          if (!fields.includes('parent_laui')) {
            fields.push('parent_laui');
            setParentLauiInPK(false);
          }

          setRequiredFields(fields);

          const initialValues: any = {};
          fields.forEach((field) => {
            initialValues[field] = field === 'account_laui' ? accountLaui : '';
          });
          initialValues.name = itemData?.name || '';

          setFormValues(initialValues);

          // Usecase: parse payloads
          if (isUsecase) {
            const payloads = (itemData as any)?.payloads ?? [];
            const parsed = parseAllPayloads(payloads);
            setParsedPayloads(parsed);
          }
        } finally {
          setLoading(false);
        }
      };

      void init();
    } else {
      setFormValues({});
      setConflictItem(null);
      setMode(null);
      setImportedItem(null);
      // Reset usecase state
      setUsecaseModeFallback(null);
      setParsedPayloads([]);
      setTaskPartition('ALL');
      setTaskWorkflowLaui('');
      setTaskStartDate('');
      setTaskEndDate('');
      setTaskResults([]);
      setTaskProgress(0);
      setCreatingTasks(false);
      setPayloadParentLaui('');
      setSkillParentLaui('');
      setImportProjectLaui('');
      setTaskProjectLaui('');
      depCacheRef.current.clear();
    }
  }, [isOpen, itemData, usecaseMode]);

  // Fields auto-handled by usecase-specific UI (don't show as generic form fields)
  const usecaseAutoFields = useMemo(() => {
    if (!isUsecase || !usecaseMode) return new Set<string>();
    const common = new Set(['name', 'account_laui', 'item_type', 'payload']);
    if (usecaseMode === 'files') {
      common.add('parent_laui');
    } else if (usecaseMode === 'tasks') {
      for (const f of [
        'parent_laui',
        'project_laui',
        'operator_laui',
        'connection_laui',
        'partition',
        'frequency',
        'start_date',
        'end_date',
        'actions',
        'attached_config_lauis',
      ])
        common.add(f);
    }
    return common;
  }, [isUsecase, usecaseMode]);

  const additionalUsecaseFields =
    isUsecase && usecaseMode ? requiredFields.filter((f) => !usecaseAutoFields.has(f)) : [];

  if (!itemData) return null;

  const handleChange = (field: string, value: any) => {
    setFormValues((prev: any) => ({
      ...prev,
      [field]: value,
    }));
  };

  const checkItemPresent = async () => {
    const filteredFormValues = { ...formValues };
    if (!parentLauiInPK) delete filteredFormValues['parent_laui'];
    filteredFormValues['item_type'] = itemData.item_type;

    const pk = createPK(filteredFormValues);

    const items = (await searchCatalogItems(itemData?.item_type, false, { filters: { pk } })).items;

    if (items && items.length > 0) {
      const existing = items[0];
      setConflictItem(existing);
      setNewName(formValues.name || '');
      return true;
    }

    return false;
  };

  const submitItem = async (values: any) => {
    try {
      const merged = { ...itemData, ...values };
      const itemType = merged.item_type || '';
      const base = itemType.split('.')[0];
      if ((base === 'operator' || base === 'action') && merged.codeblock) {
        const result = await validateCodeblock(merged.codeblock, itemType);
        if (!result.valid) {
          return;
        }
      }
      // Set marketplace_laui from the source marketplace item's laui
      if (itemData?.laui && !merged.marketplace_laui) {
        merged.marketplace_laui = itemData.laui;
      }
      const mergedItemType = merged.item_type || '';
      if (mergedItemType !== 'folder.account') merged.account_laui = accountLaui;
      if (mergedItemType !== 'folder.account' && mergedItemType !== 'folder.project')
        merged.project_laui = currentProjectLaui;
      await createCatalogItem(merged);
      setImportedItem({
        name: merged.name ?? '',
        parent_laui: merged.parent_laui ?? '',
        item_type: merged.item_type ?? '',
      });
    } catch {
      /* ignore */
    }
  };

  const handleConfirm = async () => {
    setSubmitting(true);
    try {
      const exists = await checkItemPresent();
      if (!exists) {
        await submitItem(formValues);
      }
    } finally {
      setSubmitting(false);
    }
  };

  const handleResolveConflict = async () => {
    setSubmitting(true);
    console.log(formValues);
    try {
      if (mode === 'overwrite') {
        await submitItem(formValues);
      }

      if (mode === 'rename') {
        await submitItem({
          ...formValues,
          name: newName,
        });
      }

      setConflictItem(null);
      setMode(null);
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!submitting && !creatingTasks) {
      setImportModalState({ isOpen: false });
      setParentLauiInPK(false);
      setRequiredFields([]);
      setFormValues({});
      setConflictItem(null);
      setNewName('');
      setMode(null);
      setParentLauiInPK(true);
      setImportProjectLaui('');
      setLoading(false);
      setSubmitting(false);
    }
  };

  const requiredDepsResolved = usecaseDepsResolved ?? false;

  // ---------------------------------------------------------------------------
  // Usecase: import payloads as individual payload items
  // ---------------------------------------------------------------------------

  const getExtraFields = (): Record<string, any> => {
    const extra: Record<string, any> = {};
    for (const f of additionalUsecaseFields) {
      if (formValues[f]) extra[f] = formValues[f];
    }
    return extra;
  };

  const importPayloadsAsItems = async (parentLaui: string): Promise<TaskCreationResult[]> => {
    const rawPayloads: ({ filename: string; content: string } | string)[] =
      (itemData as any)?.payloads ?? [];
    const results: TaskCreationResult[] = [];
    const extra = getExtraFields();

    for (let i = 0; i < rawPayloads.length; i++) {
      let raw = rawPayloads[i];
      if (typeof raw === 'string') {
        try {
          raw = JSON.parse(raw);
        } catch {
          raw = { filename: `payload_${i}`, content: raw as string };
        }
      }
      const p = raw as { filename: string; content: string };
      const name = p.filename?.replace(/\.[^.]+$/, '') || `payload_${i}`;

      try {
        const payloadBody: Record<string, any> = {
          item_type: 'payload',
          name,
          parent_laui: parentLaui,
          content: p.content,
          ...extra,
        };
        if (accountLaui) payloadBody.account_laui = accountLaui;
        if (currentProjectLaui) payloadBody.project_laui = currentProjectLaui;
        await createCatalogItem(payloadBody);
        results.push({ name, success: true });
      } catch (e: any) {
        results.push({ name, success: false, error: e?.message || 'Unknown error' });
      }
    }

    return results;
  };

  // ---------------------------------------------------------------------------
  // Usecase: "Import Files Only" handler
  // ---------------------------------------------------------------------------

  const handleImportFilesOnly = async () => {
    if (!payloadParentLaui) {
      showError('Please select a parent folder for the payloads');
      return;
    }
    setSubmitting(true);
    try {
      const results = await importPayloadsAsItems(payloadParentLaui);
      setTaskResults(results);

      const successCount = results.filter((r) => r.success).length;
      if (successCount === results.length) {
        showSuccess(`All ${successCount} payload(s) imported successfully`);
      } else if (successCount > 0) {
        showError(
          `${successCount}/${results.length} payloads imported. ${results.length - successCount} failed.`,
        );
      } else {
        showError('All payload imports failed');
      }
    } finally {
      setSubmitting(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Skill Usecase: import skills directly as skill items
  // ---------------------------------------------------------------------------

  const handleImportSkills = async () => {
    if (!skillParentLaui) {
      showError('Please select a parent folder for the skills');
      return;
    }
    setSubmitting(true);
    try {
      const rawPayloads: ({ filename: string; content: string } | string)[] =
        (itemData as any)?.payloads ?? [];
      const results: TaskCreationResult[] = [];

      for (let i = 0; i < rawPayloads.length; i++) {
        let raw = rawPayloads[i];
        if (typeof raw === 'string') {
          try {
            raw = JSON.parse(raw);
          } catch {
            raw = { filename: `skill_${i}`, content: raw as string };
          }
        }
        const p = raw as { filename: string; content: string };
        const name = p.filename?.replace(/\.[^.]+$/, '') || `skill_${i}`;

        try {
          // Parse the content as JSON to recover the original skill item data
          let skillData: Record<string, any>;
          try {
            skillData = JSON.parse(p.content);
          } catch {
            skillData = {};
          }

          const skillBody: Record<string, any> = {
            ...skillData,
            item_type: 'skill',
            name: skillData.name || name,
            parent_laui: skillParentLaui,
          };
          if (accountLaui) skillBody.account_laui = accountLaui;
          if (currentProjectLaui) skillBody.project_laui = currentProjectLaui;
          // Remove marketplace/catalog metadata that shouldn't be carried over
          delete skillBody.laui;
          delete skillBody._id;
          delete skillBody.pk;
          delete skillBody.created_at;
          delete skillBody.updated_at;
          delete skillBody.deleted_at;

          await createCatalogItem(skillBody);
          results.push({ name: skillBody.name, success: true });
        } catch (e: any) {
          results.push({ name, success: false, error: e?.message || 'Unknown error' });
        }
      }

      setTaskResults(results);
      const successCount = results.filter((r) => r.success).length;
      if (successCount === results.length) {
        showSuccess(`All ${successCount} skill(s) imported successfully`);
      } else if (successCount > 0) {
        showError(
          `${successCount}/${results.length} skills imported. ${results.length - successCount} failed.`,
        );
      } else {
        showError('All skill imports failed');
      }
    } finally {
      setSubmitting(false);
    }
  };

  // ---------------------------------------------------------------------------
  // Usecase: create tasks (also imports payloads as items)
  // ---------------------------------------------------------------------------

  const handleCreateTasks = async () => {
    if (!payloadParentLaui) {
      showError('Please select a parent folder for payloads');
      return;
    }
    setCreatingTasks(true);
    setTaskProgress(0);
    const results: TaskCreationResult[] = [];
    let count = 0;
    const extra = getExtraFields();

    // First: import payloads as individual payload items
    const payloadResults = await importPayloadsAsItems(payloadParentLaui);
    for (const r of payloadResults) {
      if (!r.success) {
        results.push({ name: `[payload] ${r.name}`, success: false, error: r.error });
      }
    }

    // Then: create tasks
    for (const p of parsedPayloads) {
      if (!p.meta) {
        results.push({ name: p.filename, success: false, error: 'No metadata found' });
        count++;
        setTaskProgress(count);
        continue;
      }

      const taskName = deriveTaskName(p.meta, p.filename);

      try {
        const resolvedPartition = taskPartition || p.meta.partition || 'ALL';
        const resolvedStartDate = taskStartDate || p.meta.start_date;
        const resolvedEndDate = taskEndDate || p.meta.end_date;

        const operatorLaui = depCacheRef.current.get(`operator:${p.meta.operator_name}`);
        if (!operatorLaui) {
          results.push({
            name: taskName,
            success: false,
            error: `Operator "${p.meta.operator_name}" not resolved`,
          });
          count++;
          setTaskProgress(count);
          continue;
        }

        const connectionLaui = depCacheRef.current.get(`connection:${p.meta.connection_name}`);
        if (!connectionLaui) {
          results.push({
            name: taskName,
            success: false,
            error: `Connection "${p.meta.connection_name}" not resolved`,
          });
          count++;
          setTaskProgress(count);
          continue;
        }

        // Configs — non-compulsory, skip missing
        const configNames = p.meta.config_name
          ? Array.isArray(p.meta.config_name)
            ? p.meta.config_name
            : [p.meta.config_name]
          : [];
        const attachedConfigLauis: string[] = [];
        for (const cfg of configNames) {
          const cfgLaui = depCacheRef.current.get(`config:${cfg}`);
          if (cfgLaui) attachedConfigLauis.push(cfgLaui);
        }

        // Build action lists
        const actionsBlock = p.meta.actions ?? {};
        const preActions = buildActionList(actionsBlock.pre_actions ?? [], depCacheRef.current);
        const runningActions = buildActionList(
          actionsBlock.running_actions ?? [],
          depCacheRef.current,
        );
        const postActions = buildActionList(actionsBlock.post_actions ?? [], depCacheRef.current);

        if (preActions === null || runningActions === null || postActions === null) {
          results.push({
            name: taskName,
            success: false,
            error: 'Failed to resolve action(s)',
          });
          count++;
          setTaskProgress(count);
          continue;
        }

        const taskBody: Record<string, any> = {
          item_type: 'task',
          name: taskName,
          project_laui: taskProjectLaui,
          parent_laui: taskWorkflowLaui,
          operator_laui: operatorLaui,
          connection_laui: connectionLaui,
          attached_config_lauis: attachedConfigLauis,
          frequency: p.meta.frequency || '*/3 * * * *',
          partition: resolvedPartition,
          ...extra,
        };
        if (accountLaui) taskBody.account_laui = accountLaui;

        if (p.payload) taskBody.payload = p.payload;

        if (String(taskBody.frequency).toLowerCase() !== 'adhoc') {
          if (resolvedStartDate) taskBody.start_date = resolvedStartDate;
          if (resolvedEndDate) taskBody.end_date = resolvedEndDate;
        }

        if (preActions.length || runningActions.length || postActions.length) {
          taskBody.actions = {
            create_actions: [],
            pre_actions: preActions,
            running_actions: runningActions,
            post_actions: postActions,
          };
        }

        await createCatalogItem(taskBody);
        results.push({ name: taskName, success: true });
      } catch (e: any) {
        results.push({
          name: taskName,
          success: false,
          error: e?.message || 'Unknown error',
        });
      }

      count++;
      setTaskProgress(count);
    }

    setTaskResults(results);
    setCreatingTasks(false);

    const successCount = results.filter((r) => r.success).length;
    if (successCount === results.length) {
      showSuccess(`All ${successCount} item(s) created successfully`);
    } else if (successCount > 0) {
      showError(
        `${successCount}/${results.length} items created. ${results.length - successCount} failed.`,
      );
    } else {
      showError('All creations failed');
    }
  };

  // ---------------------------------------------------------------------------
  // Usecase: import mode selector (only shown when mode not preset from outside)
  // ---------------------------------------------------------------------------

  const renderUsecaseModeSelector = () => {
    if (!isUsecase || usecaseImportMode || isSkillUsecase) return null;

    return (
      <Box sx={{ mb: 2 }}>
        <Typography sx={{ fontSize: '11px', color: 'var(--text-secondary)', mb: 1 }}>
          Import mode:
        </Typography>
        <Stack direction="row" spacing={1}>
          <Button
            size="small"
            variant={usecaseMode === 'files' || usecaseMode === null ? 'contained' : 'outlined'}
            onClick={() => setUsecaseModeFallback('files')}
            sx={{ fontSize: '11px', textTransform: 'none', flex: 1 }}
          >
            Import Files Only
          </Button>
          <Tooltip title={!requiredDepsResolved ? 'Resolve all required dependencies first' : ''}>
            <span style={{ flex: 1, display: 'flex' }}>
              <Button
                size="small"
                variant={usecaseMode === 'tasks' ? 'contained' : 'outlined'}
                onClick={() => setUsecaseModeFallback('tasks')}
                disabled={!requiredDepsResolved}
                sx={{ fontSize: '11px', textTransform: 'none', flex: 1 }}
              >
                Import & Create Tasks
              </Button>
            </span>
          </Tooltip>
        </Stack>
      </Box>
    );
  };

  // ---------------------------------------------------------------------------
  // Usecase: payload parent folder picker (shown in both files & tasks modes)
  // ---------------------------------------------------------------------------

  const renderSkillParentPicker = () => {
    if (!isSkillUsecase) return null;
    const rawPayloads: any[] = (itemData as any)?.payloads ?? [];
    return (
      <Box sx={{ border: '1px solid var(--border)', borderRadius: 1, p: 1.5, mb: 2 }}>
        <Typography sx={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', mb: 1 }}>
          Import Skills ({rawPayloads.length} skill{rawPayloads.length !== 1 ? 's' : ''})
        </Typography>
        <Typography sx={{ fontSize: '11px', color: 'var(--text-secondary)', mb: 1 }}>
          Each skill will be imported as an individual skill item.
        </Typography>
        <Box>
          <Typography variant="caption">Parent Folder (folder.skill)</Typography>
          <QuickSearch
            value={skillParentLaui}
            onSelect={(val) => {
              const raw = val as Record<string, unknown>;
              setSkillParentLaui((raw._laui ?? raw.laui ?? raw.id ?? '') as string);
            }}
            filters={{ item_type: 'folder.skill' }}
          />
        </Box>
      </Box>
    );
  };

  const renderPayloadParentPicker = () => {
    if (!isUsecase || !usecaseMode || isSkillUsecase) return null;

    return (
      <Box sx={{ border: '1px solid var(--border)', borderRadius: 1, p: 1.5, mb: 2 }}>
        <Typography sx={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', mb: 1 }}>
          Payload Import ({parsedPayloads.length} file
          {parsedPayloads.length !== 1 ? 's' : ''})
        </Typography>
        <Typography sx={{ fontSize: '11px', color: 'var(--text-secondary)', mb: 1 }}>
          Each payload will be imported as an individual payload item.
        </Typography>
        <Box>
          <Typography variant="caption">Parent Folder (folder.payload)</Typography>
          <QuickSearch
            value={payloadParentLaui}
            onSelect={(val) => {
              const raw = val as Record<string, unknown>;
              setPayloadParentLaui((raw._laui ?? raw.laui ?? raw.id ?? '') as string);
            }}
            filters={{ item_type: 'folder.payload' }}
          />
        </Box>
      </Box>
    );
  };

  // ---------------------------------------------------------------------------
  // Usecase: task configuration fields
  // ---------------------------------------------------------------------------

  const renderTaskConfigFields = () => {
    if (!isUsecase || usecaseMode !== 'tasks') return null;

    return (
      <Box sx={{ border: '1px solid var(--border)', borderRadius: 1, p: 1.5, mb: 2 }}>
        <Typography
          sx={{
            fontSize: '12px',
            fontWeight: 600,
            color: 'var(--text-primary)',
            mb: 1.5,
          }}
        >
          Task Configuration
        </Typography>

        <Box sx={{ mb: 1.5 }}>
          <Typography variant="caption">project_laui</Typography>
          <QuickSearch
            value={taskProjectLaui}
            onSelect={(val) => {
              const raw = val as Record<string, unknown>;
              setTaskProjectLaui((raw._laui ?? raw.laui ?? raw.id ?? '') as string);
            }}
            filters={{ item_type: 'folder.project' }}
          />
        </Box>

        <TextField
          label="partition"
          value={taskPartition}
          onChange={(e) => setTaskPartition(e.target.value)}
          fullWidth
          size="small"
          sx={styles.textField}
        />

        <Box sx={{ mb: 1.5 }}>
          <Typography variant="caption">workflow_folder_laui</Typography>
          <QuickSearch
            value={taskWorkflowLaui}
            onSelect={(val) => {
              const raw = val as Record<string, unknown>;
              setTaskWorkflowLaui((raw._laui ?? raw.laui ?? raw.id ?? '') as string);
            }}
            filters={{ item_type: 'folder.workflow' }}
          />
        </Box>

        <TextField
          label="start_date (optional override)"
          value={taskStartDate}
          onChange={(e) => setTaskStartDate(e.target.value)}
          fullWidth
          size="small"
          placeholder="YYYY-MM-DD"
          sx={styles.textField}
        />

        <TextField
          label="end_date (optional override)"
          value={taskEndDate}
          onChange={(e) => setTaskEndDate(e.target.value)}
          fullWidth
          size="small"
          placeholder="YYYY-MM-DD"
          sx={styles.textField}
        />
      </Box>
    );
  };

  // ---------------------------------------------------------------------------
  // Usecase: task creation progress/results
  // ---------------------------------------------------------------------------

  const renderTaskResults = () => {
    if (!isUsecase || taskResults.length === 0) return null;

    return (
      <Box sx={{ border: '1px solid var(--border)', borderRadius: 1, p: 1.5, mb: 2 }}>
        <Typography sx={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)', mb: 1 }}>
          Results: {taskResults.filter((r) => r.success).length}/{taskResults.length} succeeded
        </Typography>
        {taskResults.map((r, i) => (
          <Box key={i} sx={{ display: 'flex', alignItems: 'center', gap: 0.75, py: 0.25 }}>
            {r.success ? (
              <CheckCircleIcon sx={{ fontSize: 13, color: 'success.main' }} />
            ) : (
              <CancelIcon sx={{ fontSize: 13, color: 'error.main' }} />
            )}
            <Typography sx={{ fontSize: '11px', color: 'var(--text-primary)' }}>
              {r.name}
            </Typography>
            {r.error && (
              <Typography sx={{ fontSize: '10px', color: 'error.main', ml: 0.5 }}>
                — {r.error}
              </Typography>
            )}
          </Box>
        ))}
      </Box>
    );
  };

  // ---------------------------------------------------------------------------
  // Actions
  // ---------------------------------------------------------------------------

  const handleUsecaseConfirm = async () => {
    // Skill usecase: direct import
    if (isSkillUsecase) {
      await handleImportSkills();
      return;
    }

    // Validate additional required fields
    const missingExtra = additionalUsecaseFields.filter(
      (f) => f !== 'account_laui' && !formValues[f],
    );
    if (missingExtra.length > 0) {
      showError(`Missing required fields: ${missingExtra.join(', ')}`);
      return;
    }

    if (usecaseMode === 'tasks') {
      if (!taskProjectLaui || !taskWorkflowLaui) {
        showError('project_laui and workflow_folder_laui are required');
        return;
      }
      if (!payloadParentLaui) {
        showError('Please select a parent folder for payloads');
        return;
      }
      await handleCreateTasks();
    } else if (usecaseMode === 'files') {
      await handleImportFilesOnly();
    } else {
      return;
    }
  };

  const getUsecaseTitle = () => {
    if (isSkillUsecase) return `Import Skills: ${itemData.name}`;
    if (usecaseMode === 'files') return `Import Payloads: ${itemData.name}`;
    if (usecaseMode === 'tasks') return `Import & Create Tasks: ${itemData.name}`;
    return `Import Usecase: ${itemData.name}`;
  };

  const getUsecaseSubtitle = () => {
    if (isSkillUsecase) return 'Each skill will be imported as an individual skill item';
    if (usecaseMode === 'files')
      return 'Each payload will be imported as an individual payload item';
    if (usecaseMode === 'tasks') return 'Import payloads and create tasks from metadata';
    return 'Choose import mode';
  };

  const handleTakeMeThere = () => {
    if (!importedItem?.parent_laui) return;
    const baseType = importedItem.item_type.split('.')[0];
    const parentItemType =
      baseType === 'ai_skill' || baseType === 'ai_chat' ? 'folder.skill' : `folder.${baseType}`;
    setCatalogType(CatalogType.BROWSE);
    handleClose();
    void navigate({
      to: '/path',
      search: {
        laui: importedItem.parent_laui,
        itemtype: parentItemType,
        filtertype: importedItem.item_type,
      },
    });
  };

  const ModalActions = (
    <>
      <Button
        onClick={handleClose}
        disabled={submitting || creatingTasks}
        size="small"
        variant="outlined"
      >
        {importedItem ? 'Close' : 'Cancel'}
      </Button>

      {importedItem && (
        <Button
          onClick={handleTakeMeThere}
          size="small"
          variant="contained"
          endIcon={<ArrowForwardIcon sx={{ fontSize: 15 }} />}
        >
          Take me there
        </Button>
      )}

      {!importedItem && !conflictItem && !taskResults.length && (
        <Button
          onClick={() => void (isUsecase ? handleUsecaseConfirm() : handleConfirm())}
          disabled={
            loading ||
            submitting ||
            creatingTasks ||
            (isSkillUsecase && !skillParentLaui) ||
            (isUsecase && !isSkillUsecase && !usecaseMode) ||
            (isUsecase && !isSkillUsecase && usecaseMode === 'tasks' && !requiredDepsResolved) ||
            (isUsecase &&
              !isSkillUsecase &&
              usecaseMode === 'tasks' &&
              (!payloadParentLaui || !taskProjectLaui || !taskWorkflowLaui)) ||
            (isUsecase && !isSkillUsecase && usecaseMode === 'files' && !payloadParentLaui)
          }
          size="small"
          variant="contained"
        >
          {submitting || creatingTasks
            ? 'Importing...'
            : isSkillUsecase
              ? `Import ${((itemData as any)?.payloads ?? []).length} Skill${((itemData as any)?.payloads ?? []).length !== 1 ? 's' : ''}`
              : isUsecase && usecaseMode === 'tasks'
                ? 'Import & Create Tasks'
                : isUsecase && usecaseMode === 'files'
                  ? `Import ${parsedPayloads.length} Payload${parsedPayloads.length !== 1 ? 's' : ''}`
                  : 'Import'}
        </Button>
      )}

      {!importedItem && taskResults.length > 0 && (
        <Button onClick={handleClose} size="small" variant="contained">
          Done
        </Button>
      )}

      {conflictItem && mode && (
        <Button
          onClick={() => void handleResolveConflict()}
          disabled={submitting}
          size="small"
          variant="contained"
          color="warning"
        >
          Confirm Action
        </Button>
      )}
    </>
  );

  return (
    <BaseModal
      open={isOpen}
      onClose={handleClose}
      title={isUsecase ? getUsecaseTitle() : 'Import From Marketplace'}
      subtitle={isUsecase ? getUsecaseSubtitle() : 'Fill required fields to import item'}
      actions={ModalActions}
      loading={loading}
      loadingText="Preparing form..."
      maxWidth="sm"
    >
      {importedItem ? (
        <Box
          sx={{
            display: 'flex',
            flexDirection: 'column',
            alignItems: 'center',
            gap: 2,
            py: 2,
          }}
        >
          <CheckCircleIcon sx={{ fontSize: 48, color: 'success.main' }} />
          <Typography sx={{ fontSize: '14px', fontWeight: 600, color: 'var(--text-primary)' }}>
            Item imported successfully
          </Typography>
          <Typography
            sx={{
              fontSize: '12px',
              color: 'var(--text-secondary)',
              textAlign: 'center',
            }}
          >
            <strong>{importedItem.name}</strong> is now available in your catalog. Click{' '}
            <em>Take me there</em> to navigate to it.
          </Typography>
        </Box>
      ) : (
        <Stack spacing={2}>
          {/* Skill usecase: skill parent folder picker */}
          {renderSkillParentPicker()}

          {/* Usecase: mode selector (only when mode not preset) */}
          {renderUsecaseModeSelector()}

          {/* Usecase: payload parent folder picker */}
          {renderPayloadParentPicker()}

          {/* Usecase: task creation progress */}
          {creatingTasks && (
            <Box sx={{ mb: 2 }}>
              <Typography sx={{ fontSize: '11px', color: 'var(--text-secondary)', mb: 0.5 }}>
                Creating... {taskProgress}/{parsedPayloads.filter((p) => p.meta).length}
              </Typography>
              <LinearProgress
                variant="determinate"
                value={
                  parsedPayloads.filter((p) => p.meta).length > 0
                    ? (taskProgress / parsedPayloads.filter((p) => p.meta).length) * 100
                    : 0
                }
                sx={{ '& .MuiLinearProgress-bar': { bgcolor: 'var(--accent)' } }}
              />
            </Box>
          )}

          {/* Usecase: results */}
          {renderTaskResults()}

          {/* Usecase "tasks" mode: task config fields */}
          {renderTaskConfigFields()}

          {/* Usecase: additional required fields not handled by dedicated UI */}
          {isUsecase && usecaseMode && additionalUsecaseFields.length > 0 && (
            <Box
              sx={{
                border: '1px solid var(--border)',
                borderRadius: 1,
                p: 1.5,
                mb: 2,
              }}
            >
              <Typography
                sx={{
                  fontSize: '12px',
                  fontWeight: 600,
                  color: 'var(--text-primary)',
                  mb: 1,
                }}
              >
                Additional Required Fields
              </Typography>
              {additionalUsecaseFields.map((field) => {
                if (field === 'account_laui' || field === 'project_laui') {
                  return null;
                }
                if (field.endsWith('_laui')) {
                  return (
                    <Box key={field} sx={{ mb: 1.5 }}>
                      <Typography variant="caption">{field}</Typography>
                      <QuickSearch
                        value={formValues[field]}
                        onSelect={(val) => {
                          const raw = val as Record<string, unknown>;
                          handleChange(field, (raw._laui ?? raw.laui ?? raw.id ?? '') as string);
                        }}
                        filters={{ item_type: getItemType(field) }}
                      />
                    </Box>
                  );
                }
                return (
                  <TextField
                    key={field}
                    label={field}
                    value={formValues[field] || ''}
                    onChange={(e) => handleChange(field, e.target.value)}
                    fullWidth
                    size="small"
                    sx={styles.textField}
                  />
                );
              })}
            </Box>
          )}

          {/* Standard fields (shown for non-usecase items only) */}
          {!isUsecase && (
            <Box>
              <Typography variant="caption">Select Project</Typography>
              <QuickSearch
                value={importProjectLaui}
                onSelect={(val) => {
                  const raw = val as Record<string, unknown>;
                  setImportProjectLaui((raw._laui ?? raw.laui ?? raw.id ?? '') as string);
                }}
                filters={{ item_type: 'folder.project' }}
                ignoreProjectScope
              />
            </Box>
          )}
          {!isUsecase &&
            requiredFields.map((field) => {
              if (field === 'account_laui' || field === 'project_laui') {
                return null;
              }

              if (field.endsWith('_laui')) {
                const isParentField = field === 'parent_laui';
                return (
                  <Box key={field}>
                    <Typography variant="caption">
                      {isParentField ? 'Select folder' : field}
                    </Typography>
                    <QuickSearch
                      value={formValues[field]}
                      onSelect={(val) => {
                        const raw = val as Record<string, unknown>;
                        const laui = (raw._laui ?? raw.laui ?? raw.id ?? '') as string;
                        handleChange(field, laui);
                      }}
                      disabled={isParentField && !importProjectLaui}
                      placeholder={
                        isParentField && !importProjectLaui
                          ? 'Select project to view folders'
                          : 'Search…'
                      }
                      filters={
                        isParentField
                          ? {
                              item_type:
                                itemData.item_type === 'skill' || itemData.item_type === 'agent'
                                  ? 'folder.skill'
                                  : `folder.${itemData.item_type}`,
                              ...(importProjectLaui ? { project_laui: importProjectLaui } : {}),
                            }
                          : { item_type: getItemType(field) }
                      }
                    />
                  </Box>
                );
              }

              return (
                <TextField
                  key={field}
                  label={field}
                  value={formValues[field] || ''}
                  onChange={(e) => handleChange(field, e.target.value)}
                  fullWidth
                  sx={styles.textField}
                />
              );
            })}

          {conflictItem && (
            <Box sx={{ border: '1px solid', borderColor: 'warning.main', p: 2 }}>
              <Typography color="warning.main" fontWeight="bold">
                Conflict detected
              </Typography>

              <Typography variant="body2">Item with same PK already exists</Typography>

              <Typography variant="caption">PK: {conflictItem.pk}</Typography>
              <Typography variant="caption" display="block">
                Name: {conflictItem.name}
              </Typography>
              <Typography variant="caption" display="block">
                LAUI: {conflictItem.laui}
              </Typography>

              <Stack direction="row" spacing={1} mt={2}>
                <Button size="small" variant="outlined" onClick={() => setMode('overwrite')}>
                  Overwrite
                </Button>

                <Button size="small" variant="outlined" onClick={() => setMode('rename')}>
                  Rename
                </Button>
              </Stack>

              {mode === 'rename' && (
                <TextField
                  fullWidth
                  size="small"
                  sx={{ mt: 2 }}
                  placeholder="Enter new name"
                  value={newName}
                  onChange={(e) => setNewName(e.target.value)}
                />
              )}
            </Box>
          )}
        </Stack>
      )}
    </BaseModal>
  );
}
