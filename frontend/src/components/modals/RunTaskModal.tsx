/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useRef, useState } from 'react';

import { useNavigate } from '@tanstack/react-router';

import AddIcon from '@mui/icons-material/Add';
import CloseIcon from '@mui/icons-material/Close';
import DeleteIcon from '@mui/icons-material/Delete';
import ExpandLessIcon from '@mui/icons-material/ExpandLess';
import ExpandMoreIcon from '@mui/icons-material/ExpandMore';
import PlayArrowIcon from '@mui/icons-material/PlayArrow';
import {
  Alert,
  Autocomplete,
  Box,
  Button,
  Chip,
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
  TextField,
  Typography,
} from '@mui/material';
import { AdapterDayjs } from '@mui/x-date-pickers/AdapterDayjs';
import { DateTimePicker } from '@mui/x-date-pickers/DateTimePicker';
import { LocalizationProvider } from '@mui/x-date-pickers/LocalizationProvider';
import type { Dayjs } from 'dayjs';
import dayjs from 'dayjs';

import { CRON_EXPRESSIONS } from '@/constants/cronExpressions';
import { useGlobal } from '@/contexts/GlobalContext';
import type { TaskData } from '@/contexts/TaskModalContext';
import {
  TaskModalMode,
  TaskModalScopeType,
  useTaskModalContext,
} from '@/contexts/TaskModalContext';
import { useTimeFormat } from '@/contexts/TimeFormatContext';
import { getLastSessionId } from '@/services/api';
import {
  createCatalogItem,
  fetchAccounts,
  getCatalogItemById,
  runTask,
  searchCatalogItems,
} from '@/services/index';
import { validateCodeblock } from '@/services/validation.service';
import { getTimeZoneLabel } from '@/utils/timeFormat';

import { useNotification } from '../../contexts/NotificationContext';
import SessionDetailView from '../logs/SessionDetailView';
import { BaseModal, ModalForm, QuickSearch, StyledTextField } from '../ui';

interface TaskAction {
  lifecycleType: string;
  actionLaui: string;
  actionName: string;
  variables: Record<string, any>;
  sla: string | null;
  connection_laui?: string | null;
}

interface TaskFormData {
  name: string;
  description: string;
  account_laui: string;
  project_laui: string;
  workflow_laui: string;
  partition?: string;
  operator_laui: string;
  connection_laui: string;
  payload: string;
  payload_laui: string;
  config: string;
  attached_config_laui: string[];
  actions?: Record<string, any[]>;
  logical_date?: string;
  frequency?: string;
  start_date?: string;
  end_date?: string;
  total_retries?: number;
  retry_interval?: number;
}

export default function RunTaskModal() {
  const { accountLaui, currentProjectLaui } = useGlobal();
  const { timeZone } = useTimeFormat();
  const tzLabel = timeZone === 'utc' ? 'UTC' : getTimeZoneLabel();
  const { taskModalState, setTaskModalState } = useTaskModalContext();
  const navigate = useNavigate();

  const scope = taskModalState?.scope;
  const initialTaskData = taskModalState?.initialTaskData;
  const operatorData = taskModalState?.operatorData;

  const [duplicateTask, setDuplicateTask] = useState<any>(null);
  const skipDuplicateCheckRef = useRef(false);

  const [formData, setFormData] = useState<TaskFormData>({
    name: '',
    description: '',
    account_laui: '',
    project_laui: '',
    workflow_laui: '',
    partition: '',
    operator_laui: '',
    connection_laui: '',
    payload: '',
    payload_laui: '',
    config: '',
    attached_config_laui: [],
    total_retries: undefined,
    retry_interval: undefined,
  });

  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [configError, setConfigError] = useState<string | null>(null);

  // Loading states
  const [loadingPayloadContent, setLoadingPayloadContent] = useState(false);

  // Form state
  const [configInput, setConfigInput] = useState<string>('');
  const [_selectedOperator, setSelectedOperator] = useState<string>('');
  const [selectedPayload, setSelectedPayload] = useState<string>('');
  const [selectedConfigs, setSelectedConfigs] = useState<string[]>([]);
  const [selectedConfigLabels, setSelectedConfigLabels] = useState<Record<string, string>>({});

  // Session logs
  const [sessionId, setSessionId] = useState<string | null>(null);
  const [sessionDate, setSessionDate] = useState<string>('');
  // Per-create_action session logs (one tab per unique create_action name)
  const [createActionSessions, setCreateActionSessions] = useState<
    { sessionId: string; actionName: string; instanceIndex: number; occurrenceLabel: number }[]
  >([]);
  const [activeSessionTab, setActiveSessionTab] = useState(0);

  // Task Actions
  const [availableActions, setAvailableActions] = useState<any[]>([]);
  const [taskActions, setTaskActions] = useState<TaskAction[]>([]);
  const [selectedLifecycle, setSelectedLifecycle] = useState<string>('create_actions');
  const [selectedActionLaui, setSelectedActionLaui] = useState<string>('');
  const [selectedActionName, setSelectedActionName] = useState<string>('');
  const [_currentActionVars, setCurrentActionVars] = useState<Record<string, any>>({});
  const [loadingActionVars, setLoadingActionVars] = useState(false);
  const [expandedActionIndex, setExpandedActionIndex] = useState<number | null>(null);
  const [tempActionVars, setTempActionVars] = useState<Record<string, any>>({});
  const [tempEditActionVars, setTempEditActionVars] = useState<Record<number, Record<string, any>>>(
    {},
  );
  const [tempActionSla, setTempActionSla] = useState<string>('');
  const [tempEditActionSla, setTempEditActionSla] = useState<Record<number, string>>({});
  const [tempActionConnection, setTempActionConnection] = useState<string>('');
  const [tempEditActionConnection, setTempEditActionConnection] = useState<Record<number, string>>(
    {},
  );
  // Index of the action currently being configured in the form (auto-added to taskActions)
  const [currentActionIndex, setCurrentActionIndex] = useState<number | null>(null);

  // Scheduling
  const [_isScheduling] = useState(taskModalState?.mode === TaskModalMode.SCHEDULE);
  const [frequency, setFrequency] = useState('');
  const [startDate, setStartDate] = useState<Dayjs | null>(null);
  const [stopDate, setStopDate] = useState<Dayjs | null>(null);

  // Logical Date
  const [logicalDate, setLogicalDate] = useState<Dayjs | null>(null);

  // Track if editing a scheduled task vs ADHOC task
  const [isScheduledTask, setIsScheduledTask] = useState(false);

  // AI context: auto-create operator
  const [_createdOperatorLaui, setCreatedOperatorLaui] = useState<string | null>(null);
  const [creatingOperator] = useState(false);

  // Resolved account/project LAUIs (fallback when GlobalContext values are null)
  const [resolvedAccountLaui, setResolvedAccountLaui] = useState<string | null>(accountLaui);
  const [resolvedProjectLaui, setResolvedProjectLaui] = useState<string | null>(currentProjectLaui);

  // Track if we've already populated actions for this task to prevent re-population
  const lastPopulatedActionsRef = useRef<string | null>(null);
  // Track which workflow_laui we already auto-attached configs for, to run the fetch once per open
  const autoAttachedForWorkflowRef = useRef<string | null>(null);

  const { showSuccess, showError } = useNotification();

  // Resolve account/project LAUIs when GlobalContext values are missing
  useEffect(() => {
    const resolveAccountProject = async () => {
      if (!taskModalState?.isOpen) return;

      let acct = accountLaui;
      const proj = currentProjectLaui;

      if (!acct && proj) {
        // parent_laui of the project is the account_laui
        try {
          const projectItem = await getCatalogItemById(proj);
          acct = projectItem.parent_laui ?? null;
        } catch (err) {
          console.error('Failed to fetch project item for account resolution', err);
        }
      }

      if (!acct) {
        try {
          const accounts = await fetchAccounts();
          if (accounts.length > 0) {
            acct = accounts[0].laui;
          }
        } catch (err) {
          console.error('Failed to fetch accounts', err);
        }
      }

      if (acct) setResolvedAccountLaui(acct);
      if (proj) setResolvedProjectLaui(proj);
    };

    void resolveAccountProject();
  }, [taskModalState?.isOpen, accountLaui, currentProjectLaui]);

  // Fetch accounts and operators on modal taskModalState.isOpen
  useEffect(() => {
    const fetchInitialData = async () => {
      if (taskModalState?.isOpen) {
        // Fetch available actions for task actions
        try {
          const response = await searchCatalogItems('action');
          if (Array.isArray(response?.items)) {
            setAvailableActions(response.items);
          }
        } catch (err) {
          console.error('Failed to fetch actions', err);
        }
      }
    };

    void fetchInitialData();
  }, [taskModalState?.isOpen, scope?.scopeType]);

  // Don't auto-select connection - user must choose
  // useEffect(() => {
  //   if (connections.length > 0 && !selectedConnection) {
  //     const firstConnection = connections[0];
  //     setSelectedConnection(firstConnection.value);
  //     setFormData(prev => ({ ...prev, connection_laui: firstConnection.value }));
  //   }
  // }, [connections, selectedConnection]);

  // Handle context-based prefilling
  useEffect(() => {
    const handleContextPrefill = async () => {
      if (taskModalState?.isOpen && scope) {
        // Operator context: prefill operator and autofill payload from operator
        if (scope.scopeType === TaskModalScopeType.OPERATOR && scope.operatorLaui) {
          setSelectedOperator(scope.operatorLaui);
          setFormData((prev) => ({ ...prev, operator_laui: scope.operatorLaui! }));
          void loadOperatorPayload(scope.operatorLaui);
        }

        // Payload context: prefill payload and payload dropdown
        if (scope.scopeType === TaskModalScopeType.PAYLOAD) {
          if (scope.payloadLaui) {
            setSelectedPayload(scope.payloadLaui);
            // So submit sends payload_laui (reference) instead of full item as payload
            setFormData((prev) => ({
              ...prev,
              payload_laui: scope.payloadLaui!,
              payload: scope.payloadValue ?? '',
            }));
          } else if (scope.payloadValue) {
            setFormData((prev) => ({ ...prev, payload: scope.payloadValue! }));
          }
        }

        // Connection context: prefill connection
        if (scope.scopeType === TaskModalScopeType.CONNECTION && scope.connectionLaui) {
          setFormData((prev) => ({ ...prev, connection_laui: scope.connectionLaui! }));
        }

        // Task context (or workflow context): prefill with initial task data
        if (initialTaskData) {
          if (scope.scopeType === 'task') {
            // Exclude actions from formData - actions are managed separately via taskActions state
            const { actions: _actions, ...taskDataWithoutActions } = initialTaskData;
            setFormData((prev) => ({
              ...prev,
              ...(taskDataWithoutActions as TaskData),
            }));
            if (initialTaskData.config) setConfigInput(initialTaskData.config);
          }
          // Prefill partition if provided (e.g. when adding a task from the workflow diagram)
          if (initialTaskData.partition)
            setFormData((prev) => ({ ...prev, partition: initialTaskData.partition! }));
          // Prefill workflow_laui if provided (e.g. when adding a task from within a workflow)
          if (initialTaskData.workflow_laui)
            setFormData((prev) => ({
              ...prev,
              workflow_laui: initialTaskData.workflow_laui!,
            }));

          // Set selected values for dropdowns (task context or when opening from workflow with workflow_laui/project_laui)
          if (initialTaskData.operator_laui) setSelectedOperator(initialTaskData.operator_laui);
          if (initialTaskData.connection_laui)
            setFormData((prev) => ({
              ...prev,
              connection_laui: initialTaskData.connection_laui!,
            }));
          if (initialTaskData.payload_laui) {
            // Use handlePayloadChange to fetch and display payload content
            await handlePayloadChange(initialTaskData.payload_laui);
          }
          if (initialTaskData.attached_config_lauis)
            setSelectedConfigs(initialTaskData.attached_config_lauis);

          // Set schedule fields if present in initial task data (for scheduled tasks)
          if (initialTaskData.frequency) {
            setIsScheduledTask(true);
            setFrequency(initialTaskData.frequency);
            if (initialTaskData.start_date) {
              try {
                // Strip timezone offset so dayjs renders the UTC wall-clock time (no local conversion)
                const startDateValue = dayjs(
                  initialTaskData.start_date.replace(/Z$|[+-]\d{2}:\d{2}$/, ''),
                );
                setStartDate(startDateValue);
              } catch (err) {
                console.error('Failed to parse start_date:', err);
              }
            }
            if (initialTaskData.end_date) {
              try {
                // Strip timezone offset so dayjs renders the UTC wall-clock time (no local conversion)
                const endDateValue = dayjs(
                  initialTaskData.end_date.replace(/Z$|[+-]\d{2}:\d{2}$/, ''),
                );
                setStopDate(endDateValue);
              } catch (err) {
                console.error('Failed to parse end_date:', err);
              }
            }
          } else {
            setIsScheduledTask(false);
          }

          // Pre-populate retry fields
          if (initialTaskData.total_retries !== undefined) {
            setFormData((prev) => ({
              ...prev,
              total_retries: initialTaskData.total_retries,
            }));
          }
          if (initialTaskData.retry_interval !== undefined) {
            setFormData((prev) => ({
              ...prev,
              retry_interval: initialTaskData.retry_interval,
            }));
          }
        }

        // AI context: Operator will be auto-created during submit
        // No need to create it here
      }
    };

    void handleContextPrefill();
  }, [
    taskModalState?.isOpen,
    scope?.scopeType,
    scope?.operatorLaui,
    scope?.payloadValue,
    scope?.connectionLaui,
    initialTaskData,
  ]);

  // Pre-populate Attached Configs with all config children of the selected workflow when creating a task
  useEffect(() => {
    if (!taskModalState?.isOpen || taskModalState.mode !== TaskModalMode.CREATE) return;
    const workflowLaui = formData.workflow_laui;
    if (!workflowLaui || autoAttachedForWorkflowRef.current === workflowLaui) return;

    autoAttachedForWorkflowRef.current = workflowLaui;

    const fetchAndPrefill = async () => {
      try {
        const response = await searchCatalogItems('config', false, {
          filters: { parent_laui: workflowLaui },
          perPage: 100,
          projection: ['name'],
        });
        const items: unknown[] = Array.isArray(response?.items)
          ? response.items
          : Array.isArray(response)
            ? response
            : [];
        if (items.length === 0) return;
        const lauis: string[] = [];
        const labels: Record<string, string> = {};
        items.forEach((item) => {
          const anyItem = item as Record<string, unknown>;
          const actual = (anyItem.item as Record<string, unknown>) ?? anyItem;
          const laui =
            (actual._laui as string) ?? (actual.laui as string) ?? (actual.id as string) ?? '';
          const name = (actual.name as string) ?? laui;
          if (laui) {
            lauis.push(laui);
            labels[laui] = name;
          }
        });
        if (lauis.length === 0) return;
        setSelectedConfigLabels((prev) => ({ ...prev, ...labels }));
        setSelectedConfigs(lauis);
        setFormData((prev) => ({ ...prev, attached_config_laui: lauis }));
      } catch (err) {
        console.error('Failed to pre-populate workflow configs', err);
      }
    };

    void fetchAndPrefill();
  }, [taskModalState?.isOpen, taskModalState?.mode, formData.workflow_laui]);

  // Populate task actions from initialTaskData when available actions are loaded
  useEffect(() => {
    if (taskModalState?.isOpen && initialTaskData?.actions && availableActions.length > 0) {
      // Create a unique key for this task's actions to track if we've already populated
      const actionsKey = JSON.stringify(initialTaskData.actions);

      // Only populate if we haven't already populated for this exact task data
      if (lastPopulatedActionsRef.current !== actionsKey) {
        const parsedActions: TaskAction[] = [];
        const actionsData =
          typeof initialTaskData.actions === 'string'
            ? JSON.parse(initialTaskData.actions)
            : initialTaskData.actions;

        // Iterate through each lifecycle type
        const lifecycleTypes = ['create_actions', 'pre_actions', 'post_actions', 'running_actions'];
        lifecycleTypes.forEach((lifecycleType) => {
          const actionsArray = actionsData[lifecycleType];
          if (Array.isArray(actionsArray)) {
            actionsArray.forEach((action: any) => {
              // Match by laui first, fall back to name for pre-configured actions (e.g. from workflow diagram)
              const actionItem =
                availableActions.find((a) => a.laui === action.laui) ||
                (action.name ? availableActions.find((a) => a.name === action.name) : undefined);
              if (actionItem) {
                parsedActions.push({
                  lifecycleType,
                  actionLaui: actionItem.laui,
                  actionName: actionItem.name,
                  variables: action.action_variables || {},
                  sla: action.sla || null,
                  connection_laui: action.connection_laui || null,
                });
              }
            });
          }
        });

        setTaskActions(parsedActions);
        lastPopulatedActionsRef.current = actionsKey;
      }
    }
  }, [taskModalState?.isOpen, initialTaskData, availableActions]);

  // Fetch action details when an action is selected, and auto-add to taskActions
  useEffect(() => {
    const fetchActionDetails = async () => {
      if (selectedActionLaui) {
        setLoadingActionVars(true);
        try {
          const item = await getCatalogItemById(selectedActionLaui);
          let vars: Record<string, any> = {};
          if (item.action_variables) {
            const parsed =
              typeof item.action_variables === 'string'
                ? JSON.parse(item.action_variables)
                : item.action_variables;
            const { connection_laui: _conn, ...rest } = parsed;
            vars = rest;
          }
          setCurrentActionVars(vars);
          setTempActionVars(vars);
          // Auto-add the action to taskActions
          const newAction: TaskAction = {
            lifecycleType: selectedLifecycle,
            actionLaui: selectedActionLaui,
            actionName: selectedActionName,
            variables: vars,
            sla: null,
            connection_laui: null,
          };
          setTaskActions((prev) => {
            const newIndex = prev.length;
            setCurrentActionIndex(newIndex);
            return [...prev, newAction];
          });
        } catch (err) {
          console.error('Failed to fetch action details', err);
          setCurrentActionVars({});
          setTempActionVars({});
        } finally {
          setLoadingActionVars(false);
        }
      } else {
        setCurrentActionVars({});
        setTempActionVars({});
        setCurrentActionIndex(null);
      }
    };
    void fetchActionDetails();
  }, [selectedActionLaui]);

  // Auto-sync variable/sla/connection changes to the current action in taskActions
  useEffect(() => {
    if (currentActionIndex === null) return;
    setTaskActions((prev) => {
      if (currentActionIndex >= prev.length) return prev;
      const updated = [...prev];
      updated[currentActionIndex] = {
        ...updated[currentActionIndex],
        lifecycleType: selectedLifecycle,
        variables: tempActionVars,
        sla: selectedLifecycle === 'running_actions' ? tempActionSla || null : null,
        connection_laui: tempActionConnection || null,
      };
      return updated;
    });
  }, [tempActionVars, tempActionSla, tempActionConnection, selectedLifecycle, currentActionIndex]);

  // "Add Action" now just resets the form so user can add another action
  const handleAddTaskAction = () => {
    if (!selectedActionLaui) return;
    setCurrentActionIndex(null);
    setSelectedActionLaui('');
    setSelectedActionName('');
    setCurrentActionVars({});
    setTempActionVars({});
    setTempActionSla('');
    setTempActionConnection('');
  };

  const handleRemoveTaskAction = (index: number) => {
    setTaskActions(taskActions.filter((_, i) => i !== index));
    if (expandedActionIndex === index) {
      setExpandedActionIndex(null);
      // Clean up temp vars for this index
      const newTempVars = { ...tempEditActionVars };
      delete newTempVars[index];
      setTempEditActionVars(newTempVars);
      const newTempConn = { ...tempEditActionConnection };
      delete newTempConn[index];
      setTempEditActionConnection(newTempConn);
    }
    // Update currentActionIndex if the removed action affects it
    if (currentActionIndex !== null) {
      if (index === currentActionIndex) {
        // The action being edited in the form was removed - reset form
        setCurrentActionIndex(null);
        setSelectedActionLaui('');
        setSelectedActionName('');
        setCurrentActionVars({});
        setTempActionVars({});
        setTempActionSla('');
        setTempActionConnection('');
      } else if (index < currentActionIndex) {
        setCurrentActionIndex(currentActionIndex - 1);
      }
    }
  };

  const handleExpandAction = (index: number) => {
    if (expandedActionIndex === index) {
      // Collapsing - save the temp vars, sla, and connection to the actual action
      const updated = [...taskActions];
      if (tempEditActionVars[index]) {
        updated[index] = { ...updated[index], variables: tempEditActionVars[index] };
        const newTempVars = { ...tempEditActionVars };
        delete newTempVars[index];
        setTempEditActionVars(newTempVars);
      }
      if (tempEditActionSla[index] !== undefined) {
        updated[index] = { ...updated[index], sla: tempEditActionSla[index] || null };
        const newTempSla = { ...tempEditActionSla };
        delete newTempSla[index];
        setTempEditActionSla(newTempSla);
      }
      if (tempEditActionConnection[index] !== undefined) {
        updated[index] = {
          ...updated[index],
          connection_laui: tempEditActionConnection[index] || null,
        };
        const newTempConn = { ...tempEditActionConnection };
        delete newTempConn[index];
        setTempEditActionConnection(newTempConn);
      }
      setTaskActions(updated);
      setExpandedActionIndex(null);
    } else {
      // Expanding - initialize temp vars with current action vars
      setTempEditActionVars((prev) => ({
        ...prev,
        [index]: taskActions[index].variables,
      }));
      setTempEditActionSla((prev) => ({
        ...prev,
        [index]: taskActions[index].sla || '',
      }));
      setTempEditActionConnection((prev) => ({
        ...prev,
        [index]: taskActions[index].connection_laui || '',
      }));
      setExpandedActionIndex(index);
    }
  };

  const handleChange = (field: keyof TaskData, value: string | string[]) => {
    setFormData((prev) => {
      const updated = { ...prev, [field]: value };
      // If user is typing in payload field and had selected a payload from dropdown,
      // clear the payload_laui selection to allow manual editing
      if (field === 'payload' && selectedPayload) {
        updated.payload_laui = '';
      }
      return updated;
    });

    // If user is editing payload field after selecting from dropdown, clear the dropdown selection
    if (field === 'payload' && selectedPayload) {
      setSelectedPayload('');
    }

    setError(null);
    if (field === 'config') {
      setConfigError(null);
    }
  };

  const handleWorkflowChange = (value: string) => {
    handleChange('workflow_laui', value);
  };

  const handleConnectionChange = (value: string) => {
    handleChange('connection_laui', value || '');
  };

  // Fetch the operator's payload and fill the payload field.
  // Skipped when the user has explicitly selected a catalog payload (payload_laui).
  const loadOperatorPayload = async (operatorLaui: string) => {
    if (!operatorLaui) return;
    try {
      const operatorItem = await getCatalogItemById(operatorLaui);
      const payload = operatorItem.payload;
      if (payload) {
        const payloadString =
          typeof payload === 'string' ? payload : JSON.stringify(payload, null, 2);
        setFormData((prev) => ({ ...prev, payload: payloadString }));
      }
    } catch (err) {
      console.error('Failed to fetch operator payload:', err);
    }
  };

  const handleOperatorChange = (value: string) => {
    setSelectedOperator(value);
    handleChange('operator_laui', value);
    if (!formData.payload_laui) void loadOperatorPayload(value);
  };

  const handlePayloadChange = async (value: string) => {
    setSelectedPayload(value || '');

    if (value) {
      // Set payload_laui immediately so it's ready for submission (like when creating from operator)
      setFormData((prev) => ({
        ...prev,
        payload_laui: value,
        payload: '', // Will be fetched in background for display
      }));
      //console.log('Payload selected - LAUI:', value);

      // Fetch content in background for display purposes only
      setLoadingPayloadContent(true);
      try {
        const payloadItem = await getCatalogItemById(value);
        // Backend may return content in 'content', 'payload', or nested; support laui as _id
        const payloadContent =
          (payloadItem as Record<string, unknown>).content ??
          (payloadItem as Record<string, unknown>).payload ??
          (payloadItem as Record<string, unknown>).data ??
          '';
        const payloadString =
          typeof payloadContent === 'string'
            ? payloadContent
            : JSON.stringify(payloadContent, null, 2);

        setError(null);
        // Update with fetched content for display
        setFormData((prev) => ({
          ...prev,
          payload: payloadString,
        }));
        //console.log('Payload content loaded - Length:', payloadString.length);
      } catch (err: any) {
        console.error('Failed to fetch payload content:', err);
      } finally {
        setLoadingPayloadContent(false);
      }
    } else {
      setFormData((prev) => ({ ...prev, payload_laui: '', payload: '' }));
    }
  };

  const handleConfigInputChange = (value: string) => {
    setConfigInput(value);
    setConfigError(null);
  };

  const handleConfigsChange = (values: string[]) => {
    setSelectedConfigs(values);
    handleChange('attached_config_laui', values);
  };

  const validateConfigJson = (jsonString: string): boolean => {
    if (!jsonString.trim()) return true;
    try {
      JSON.parse(jsonString);
      return true;
    } catch {
      return false;
    }
  };

  const validateForm = (): boolean => {
    if (!taskModalState || !scope) return false;
    // Adhoc run: task data comes from initialTaskData; only logical date is user input (optional)
    if (taskModalState.mode === TaskModalMode.RUN) return true;

    if (!formData.name.trim()) {
      showError('Name is required');
      return false;
    }

    // Determine if we're dealing with a scheduled task or ADHOC task
    const isScheduling = taskModalState.mode === TaskModalMode.SCHEDULE;

    if (!formData.workflow_laui.trim()) {
      showError('Workflow is required');
      return false;
    }

    // Operator is not required in AI context (will be auto-created)
    if (scope.scopeType !== 'ai' && !formData.operator_laui.trim()) {
      showError('Operator is required');
      return false;
    }

    if (!formData.connection_laui.trim()) {
      showError('Connection is required');
      return false;
    }

    // Payload is required unless payload_laui is selected
    if (!formData.payload_laui && !formData.payload.trim()) {
      showError('Payload is required');
      return false;
    }

    if (configInput.trim() && !validateConfigJson(configInput)) {
      showError('Invalid JSON format for config');
      return false;
    }

    // Schedule validation for both schedule mode and editing scheduled tasks
    if (isScheduling) {
      if (!frequency.trim()) {
        showError('Frequency is required for scheduled tasks');
        return false;
      }

      if (!startDate) {
        showError('Start Date is required for scheduled tasks');
        return false;
      }
    }

    return true;
  };

  const handleSubmit = async () => {
    if (!taskModalState) return;
    setError(null);
    setConfigError(null);

    if (!validateForm()) {
      return;
    }

    /*console.log('handleSubmit - formData state:', {
      payload_laui: formData.payload_laui || '(not set)',
      payload_length: formData.payload?.length || 0,
      logical_date: logicalDate ? logicalDate.format('YYYY-MM-DDTHH:mm:ss') : '(not set)'
    });
    */

    // Duplicate check for create mode
    if (taskModalState.mode === 'create' && !skipDuplicateCheckRef.current && formData.name) {
      try {
        const response = await searchCatalogItems('task', false, {
          filters: { name: formData.name },
        });
        const existing = (response?.items || []).find((it: any) => it.name === formData.name);
        if (existing) {
          setDuplicateTask(existing);
          return;
        }
      } catch {
        // ignore check errors, proceed with creation
      }
    }
    skipDuplicateCheckRef.current = false;

    const configStr = configInput.trim() ? configInput : '';
    handleChange('config', configStr);

    setSubmitting(true);
    // Hoisted so the catch block can read it — `const`s declared inside `try`
    // are not visible in `catch` (separate block scope).
    let createActionNamesForLogs: string[] = [];
    try {
      // Parse config to JSON object when non-empty (form already validated JSON)
      let configValue: string | object = configStr;
      if (configStr) {
        try {
          configValue = JSON.parse(configStr);
        } catch {
          configValue = configStr;
        }
      }

      const submitData: TaskFormData = {
        ...formData,
        config: configValue as string,
        account_laui: resolvedAccountLaui ?? accountLaui ?? '',
        project_laui: resolvedProjectLaui ?? currentProjectLaui ?? '',
      };

      // Payload: send only one of payload_laui (dropdown) or payload (typed)
      const payloadFromDropdown = submitData.payload_laui && submitData.payload_laui.trim();
      if (payloadFromDropdown) {
        // Selected from dropdown → send only payload_laui; backend fetches content from catalog
        delete (submitData as any).payload;
        //console.log('Sending payload_laui only:', submitData.payload_laui);
      } else {
        // Explicitly typed → send payload as-is: JSON object/array if parseable, string otherwise
        (submitData as any).payload_laui = '';
        if (
          submitData.payload &&
          typeof submitData.payload === 'string' &&
          submitData.payload.trim()
        ) {
          try {
            // Try to parse as JSON
            (submitData as any).payload = JSON.parse(submitData.payload);
          } catch {
            // Not valid JSON → keep as plain string
          }
        } else {
          delete (submitData as any).payload;
        }
      }

      // Pack task actions from UI state (always override formData.actions)
      // First, ensure any currently expanded action's temp vars are included
      const actionsToSubmit = [...taskActions];
      if (expandedActionIndex !== null) {
        if (tempEditActionVars[expandedActionIndex]) {
          actionsToSubmit[expandedActionIndex] = {
            ...actionsToSubmit[expandedActionIndex],
            variables: tempEditActionVars[expandedActionIndex],
          };
        }
        if (tempEditActionSla[expandedActionIndex] !== undefined) {
          actionsToSubmit[expandedActionIndex] = {
            ...actionsToSubmit[expandedActionIndex],
            sla: tempEditActionSla[expandedActionIndex] || null,
          };
        }
      }

      const actionsPayload: Record<string, any[]> = {
        pre_actions: [],
        post_actions: [],
        running_actions: [],
        create_actions: [],
      };
      actionsToSubmit.forEach((ta) => {
        if (actionsPayload[ta.lifecycleType]) {
          actionsPayload[ta.lifecycleType].push({
            laui: ta.actionLaui,
            action_variables: ta.variables,
            sla: ta.sla,
            connection_laui: ta.connection_laui || null,
          });
        }
      });
      // Always set actions from UI state - this ensures deleted actions are not sent
      submitData.actions = actionsPayload;

      // Capture create_action names so we can render one tab per action in the
      // side-by-side logs panel (driven by the response session_id).
      createActionNamesForLogs =
        taskModalState.mode !== 'run'
          ? actionsToSubmit
              .filter((ta) => ta.lifecycleType === 'create_actions')
              .map((ta) => ta.actionName)
          : [];

      // Determine if we're dealing with a scheduled task or ADHOC task
      const isScheduling =
        taskModalState.mode === 'schedule' || (taskModalState.mode === 'edit' && isScheduledTask);

      // Add schedule data if scheduling (create/schedule mode or editing a scheduled task)
      if (isScheduling) {
        submitData.frequency = frequency;
        // Format dates as UTC without timezone conversion (treat input as UTC)
        submitData.start_date = startDate?.format('YYYY-MM-DDTHH:mm:ss.SSS[Z]');
        submitData.end_date = stopDate?.format('YYYY-MM-DDTHH:mm:ss.SSS[Z]');
      } else if (taskModalState.mode === 'run' && logicalDate) {
        // Add logical date for run mode (adhoc run)
        submitData.logical_date = logicalDate.format('YYYY-MM-DDTHH:mm:ss.SSS[Z]');
        //console.log('Adding logical_date to submitData for run mode:', submitData.logical_date);
      }

      const result = await handleRunTaskSubmit(submitData, taskModalState.mode!);

      if (
        taskModalState.mode === 'schedule' ||
        taskModalState.mode === 'create' ||
        taskModalState.mode === 'edit'
      ) {
        const successMessage =
          taskModalState.mode === 'schedule'
            ? 'Task scheduled successfully!'
            : taskModalState.mode === 'edit'
              ? 'Task updated successfully!'
              : 'Task created successfully!';
        showSuccess(successMessage);

        // Notify the opener (e.g. ItemsView) so it can refresh the list and
        // show the just-created/updated task. Capture before handleClose, which
        // resets taskModalState.
        taskModalState.onSuccess?.();

        handleClose();
      } else if (taskModalState.mode === 'run') {
        // Run mode - show logs
        if (result?.session_id) {
          setSessionId(result.session_id);
          setSessionDate(new Date().toISOString().split('T')[0]);
        }
      }
    } catch (err: any) {
      if (createActionNamesForLogs.length > 0) {
        const sid = getLastSessionId();
        if (sid) {
          const perName = new Map<string, number>();
          const tabs = createActionNamesForLogs.map((actionName) => {
            const instanceIndex = perName.get(actionName) ?? 0;
            perName.set(actionName, instanceIndex + 1);
            return {
              sessionId: sid,
              actionName,
              instanceIndex,
              occurrenceLabel: instanceIndex + 1,
            };
          });
          setSessionId(sid);
          setCreateActionSessions(tabs);
          setActiveSessionTab(0);
          setSessionDate(new Date().toISOString().split('T')[0]);
        }
      }
      showError(err.message || `Failed to ${taskModalState.mode} task`, err.details);
    } finally {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    // Reset all form state
    setError(null);
    setConfigError(null);
    setSessionId(null);
    setSessionDate('');
    setCreateActionSessions([]);
    setActiveSessionTab(0);
    setFormData({
      name: '',
      description: '',
      account_laui: '',
      project_laui: '',
      workflow_laui: '',
      operator_laui: '',
      connection_laui: '',
      payload: '',
      payload_laui: '',
      config: '',
      attached_config_laui: [],
      total_retries: undefined,
      retry_interval: undefined,
    });
    setConfigInput('');

    setSelectedOperator('');
    setSelectedPayload('');
    setSelectedConfigs([]);
    autoAttachedForWorkflowRef.current = null;
    setCreatedOperatorLaui(null);
    setTaskActions([]);
    setCurrentActionIndex(null);
    setSelectedActionLaui('');
    setSelectedActionName('');
    setCurrentActionVars({});
    setTempActionVars({});
    setTempEditActionVars({});
    setTempActionSla('');
    setTempEditActionSla({});
    setTempActionConnection('');
    setTempEditActionConnection({});
    setFrequency('');
    setStartDate(null);
    setStopDate(null);
    setLogicalDate(null);
    setIsScheduledTask(false);
    setSubmitting(false);
    // Reset the actions population tracker
    lastPopulatedActionsRef.current = null;
    setTaskModalState({ isOpen: false });
  };

  if (!taskModalState || !setTaskModalState) return null;
  if (!scope || !taskModalState.mode) return null;

  const loading = submitting || creatingOperator;

  const logsActions = (
    <Button
      onClick={handleClose}
      size="small"
      variant="contained"
      sx={{
        bgcolor: 'var(--text-primary)',
        color: 'var(--bg-secondary)',
        textTransform: 'none',
        fontWeight: 'bold',
        '&:hover': {
          bgcolor: 'var(--bg-secondary)',
          color: 'var(--text-primary)',
        },
        py: 0.5,
        px: 1.5,
      }}
    >
      Close
    </Button>
  );

  const getButtonText = () => {
    if (submitting) {
      if (taskModalState.mode === 'create') return 'Creating...';
      if (taskModalState.mode === 'schedule') return 'Scheduling...';
      if (taskModalState.mode === 'edit') return 'Updating...';
      return 'Running...';
    }
    if (creatingOperator) return 'Creating Operator...';
    if (taskModalState.mode === 'create') return 'Create Task';
    if (taskModalState.mode === 'schedule') return 'Schedule Task';
    if (taskModalState.mode === 'edit') return 'Update Task';
    return 'Run Task';
  };

  const isRunLogsView = !!sessionId && taskModalState.mode === 'run';
  const isSideBySideLogs = createActionSessions.length > 0 && taskModalState.mode !== 'run';
  const activeCreateSession = createActionSessions[activeSessionTab];

  const handleCloseLogsPanel = () => {
    setCreateActionSessions([]);
    setActiveSessionTab(0);
    setSessionDate('');
  };

  const modalActions = isRunLogsView ? (
    logsActions
  ) : (
    <>
      <Button
        onClick={handleClose}
        disabled={loading}
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
        onClick={() => void handleSubmit()}
        disabled={loading}
        size="small"
        variant="contained"
        startIcon={<PlayArrowIcon />}
        data-tour-target="task-modal-submit"
        sx={{
          bgcolor: 'var(--text-primary)',
          color: 'var(--bg-secondary)',
          textTransform: 'none',
          fontWeight: 'bold',
          '&:hover': {
            bgcolor: 'var(--bg-secondary)',
            color: 'var(--text-primary)',
          },
          py: 0.5,
          px: 1.5,
          '&:disabled': {
            bgcolor: 'var(--bg-tertiary)',
            color: 'var(--text-disabled)',
          },
        }}
      >
        {getButtonText()}
      </Button>
    </>
  );

  const isOperatorDisabled = scope.scopeType === 'operator' || scope.scopeType === 'task';
  const isPayloadDisabled = scope.scopeType === 'payload';
  const isConnectionDisabled = scope.scopeType === 'connection';
  // Payload field is only disabled while loading, not when a dropdown selection is made
  // When user selects from dropdown, they can still edit (which will clear the dropdown selection)
  const isPayloadFieldDisabled = loading;

  const getModalTitle = () => {
    if (isRunLogsView) return 'Execution Logs';
    if (taskModalState.mode === 'edit') return 'Edit Task';
    if (taskModalState.mode === 'schedule') return 'Schedule Task';
    if (taskModalState.mode === 'create') return 'Create Task';
    return 'Run Task';
  };

  const getModalSubtitle = () => {
    if (isRunLogsView) return `Session: ${sessionId}`;
    if (taskModalState.mode === 'edit') return 'Update task configuration';
    if (taskModalState.mode === 'schedule') return 'Schedule the task';
    if (taskModalState.mode === 'create') return 'Create a new task';
    return 'Configure and run the task';
  };

  // manual editor ai and default
  const handleRunTaskSubmit = async (
    formData: TaskFormData,
    mode: TaskModalMode,
  ): Promise<{ session_id?: string; item?: any }> => {
    try {
      let operatorLaui = formData.operator_laui;
      if (scope.scopeType === TaskModalScopeType.AI) {
        // For AI context, create operator first

        // If no operator selected, create one from generated content
        if (!operatorLaui) {
          const connectionItem = await getCatalogItemById(formData.connection_laui);
          if (!connectionItem || !connectionItem.item_type) {
            throw new Error('Could not fetch connection item details');
          }
          const operatorType = connectionItem.item_type.replace('connection.', 'operator.');

          const operatorPayload: any = {
            item_type: operatorType,
            name: formData.name,
            description: formData.description,
            parent_laui: formData.workflow_laui,
            account_laui: formData.account_laui,
            project_laui: formData.project_laui,
            codeblock: operatorData?.codeblock || {},
            bashblock: operatorData?.bashblock || {},
            connection: operatorData?.connection || {},
            payload: operatorData?.payload || {},
            install_doc: operatorData?.install_docs || {},
            guide_doc: operatorData?.guide_docs || {},
          };

          // Pre-save codeblock validation for the operator
          if (operatorPayload.codeblock && Object.keys(operatorPayload.codeblock).length > 0) {
            const validation = await validateCodeblock(
              operatorPayload.codeblock,
              operatorPayload.item_type,
            );
            if (!validation.valid) {
              showError(`Codeblock validation failed: ${validation.errors.length} error(s)`, {
                errors: validation.errors,
                warnings: validation.warnings,
              } as any);
              return {};
            }
          }
          const operatorResponse = await createCatalogItem(operatorPayload);
          operatorLaui =
            operatorResponse._laui || operatorResponse.laui || operatorResponse.item_laui;

          if (!operatorLaui) {
            throw new Error('Operator created but laui not found in response');
          }
          setCreatedOperatorLaui(operatorLaui);
        }
      }

      const taskPayload: any = {
        ...(initialTaskData || {}),
        item_type: 'task',
        name: formData.name,
        description: formData.description,
        operator_laui: operatorLaui,
        connection_laui: formData.connection_laui,
        parent_laui: formData.workflow_laui,
        project_laui: formData.project_laui,
        account_laui: formData.account_laui,
      };

      // Handle payload: use payload_laui if selected, otherwise use edited payload text
      if (formData.payload_laui && formData.payload_laui.trim()) {
        taskPayload.payload_laui = formData.payload_laui;
        delete taskPayload.payload;
      } else if (formData.payload) {
        taskPayload.payload = formData.payload;
        taskPayload.payload_laui = '';
      }
      // Add optional fields
      if (formData.config) {
        try {
          taskPayload.config = JSON.parse(formData.config);
        } catch {
          console.warn('Invalid config JSON, skipping');
        }
      }
      if (formData.attached_config_laui && formData.attached_config_laui.length > 0) {
        taskPayload.attached_config_lauis = formData.attached_config_laui;
      }
      if (formData.actions) {
        taskPayload.actions = formData.actions;
      }
      if (formData.logical_date) {
        taskPayload.logical_date = formData.logical_date;
      }
      if (formData.description) {
        taskPayload.description = formData.description;
      }
      // Partition: if provided, set it; otherwise default to "ALL" when creating new tasks
      if (formData.partition && formData.partition.trim()) {
        taskPayload.partition = formData.partition.trim();
      } else if (!taskPayload.partition) {
        taskPayload.partition = 'ALL';
      }
      // Retry configuration — always include so 0 can explicitly reset retries
      taskPayload.total_retries = formData.total_retries ?? 0;
      taskPayload.retry_interval = formData.retry_interval ?? 0;
      // Handle different modes
      if (mode === 'run') {
        taskPayload.state = 'scheduled';
        taskPayload.frequency = 'ADHOC';

        const taskResponse = await runTask(taskPayload);
        const sessionId = taskResponse.session_id;
        return { session_id: sessionId };
      } else if (mode === 'schedule') {
        taskPayload.state = 'scheduled';
        taskPayload.frequency = formData.frequency;
        taskPayload.start_date = formData.start_date;
        taskPayload.end_date = formData.end_date;

        const scheduleResponse = await createCatalogItem(taskPayload);
        return { item: scheduleResponse };
      } else if (mode === 'edit') {
        await createCatalogItem(taskPayload);
        return {};
      } else {
        // create mode
        const createResponse = await createCatalogItem(taskPayload);
        return { item: createResponse };
      }
    } catch (error) {
      console.error('Failed to submit task:', error);
      throw error;
    }
  };

  return (
    <>
      <BaseModal
        open={taskModalState.isOpen}
        onClose={handleClose}
        title={getModalTitle()}
        subtitle={getModalSubtitle()}
        actions={modalActions}
        loading={loading && !sessionId && !isSideBySideLogs}
        loadingText={getButtonText()}
        maxWidth={isRunLogsView ? 'md' : isSideBySideLogs ? 'xl' : 'sm'}
      >
        {isRunLogsView ? (
          <Box sx={{ height: '500px', overflow: 'hidden' }}>
            <SessionDetailView sessionId={sessionId} sessionDate={sessionDate} />
          </Box>
        ) : (
          <Box
            sx={{
              display: 'flex',
              gap: 2,
              pt: 2,
              height: isSideBySideLogs ? '70vh' : 'auto',
            }}
          >
            <Box
              sx={{
                flex: isSideBySideLogs ? '0 0 40%' : 1,
                minWidth: 0,
                display: 'flex',
                flexDirection: 'column',
                gap: 2,
                overflowY: isSideBySideLogs ? 'auto' : 'visible',
                pr: isSideBySideLogs ? 1 : 0,
              }}
            >
              {(taskModalState.mode == 'create' ||
                (scope.scopeType == 'ai' && taskModalState.mode !== 'run')) && (
                <StyledTextField
                  label="Name"
                  value={formData.name}
                  onChange={(e) => handleChange('name', e.target.value)}
                  disabled={loading || taskModalState.mode === 'edit'}
                  placeholder="Enter task name"
                  required
                  error={!!error && !formData.name.trim()}
                  inputProps={{ maxLength: 255 }}
                  helperText={`${formData.name.length}/255`}
                  sx={{ mb: 0 }}
                />
              )}

              {(taskModalState.mode == 'create' ||
                taskModalState.mode == 'edit' ||
                (scope.scopeType == 'ai' && taskModalState.mode !== 'run')) && (
                <StyledTextField
                  label="Description"
                  value={formData.description}
                  onChange={(e) => handleChange('description', e.target.value)}
                  disabled={loading}
                  placeholder="Optional description"
                  multiline
                  minRows={2}
                  maxRows={10}
                  inputProps={{ maxLength: 10000 }}
                  helperText={`${formData.description.length}/10000`}
                  sx={{ mb: 0 }}
                />
              )}

              {(taskModalState.mode == 'create' ||
                taskModalState.mode == 'edit' ||
                (scope.scopeType == 'ai' && taskModalState.mode !== 'run')) && (
                <StyledTextField
                  label="Partition (optional)"
                  value={formData.partition || ''}
                  onChange={(e) => handleChange('partition', e.target.value)}
                  disabled={loading}
                  placeholder='e.g. "abc", "daily_batch"; leave blank for "ALL"'
                  sx={{ mb: 0 }}
                />
              )}

              {/* Show logical date field only for run mode (adhoc run) */}
              {taskModalState.mode === 'run' && (
                <LocalizationProvider dateAdapter={AdapterDayjs}>
                  <DateTimePicker
                    label={`Logical Date (${tzLabel}, Optional)`}
                    value={logicalDate}
                    onChange={(newValue) => setLogicalDate(newValue)}
                    disabled={loading}
                    ampm={false}
                    slotProps={{
                      textField: {
                        fullWidth: true,
                        size: 'small',
                        sx: {
                          '& .MuiOutlinedInput-root': {
                            fontSize: '14px',
                            backgroundColor: 'var(--bg-primary)',
                            color: 'var(--text-primary) !important',
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
                            fontSize: '14px',
                            color: 'var(--text-secondary)',
                            '&.Mui-focused': {
                              color: 'var(--accent)',
                            },
                            '&.Mui-disabled': {
                              color: 'var(--text-disabled)',
                            },
                          },
                          '& .MuiOutlinedInput-notchedOutline': {
                            borderColor: 'var(--border)',
                          },
                          '& .MuiPickersSectionList-sectionContent, & .MuiPickersSectionList-sectionSeparator':
                            {
                              color: 'var(--text-primary)',
                            },
                          '& .MuiIconButton-root': {
                            color: 'var(--text-secondary)',
                          },
                        },
                      },
                    }}
                  />
                </LocalizationProvider>
              )}
              {(taskModalState.mode == 'create' ||
                (scope.scopeType == 'ai' && taskModalState.mode !== 'run')) && (
                <QuickSearch
                  label="Workflow *"
                  value={formData.workflow_laui}
                  filters={{ item_type: 'folder.workflow' }}
                  disabled={loading}
                  onSelect={(item) => {
                    const raw = item as Record<string, unknown>;
                    const laui = (raw._laui ?? raw.laui ?? raw.id ?? '') as string;
                    handleWorkflowChange(laui);
                  }}
                  placeholder="Search workflow…"
                />
              )}
              {/* Hide operator dropdown in AI context */}
              {taskModalState.mode == 'create' && scope.scopeType !== 'ai' && (
                <QuickSearch
                  label="Operator *"
                  value={formData.operator_laui}
                  filters={{ item_type: 'operator' }}
                  disabled={loading || isOperatorDisabled}
                  onSelect={(item) => {
                    const raw = item as Record<string, unknown>;
                    const laui = (raw._laui ?? raw.laui ?? raw.id ?? '') as string;
                    void handleOperatorChange(laui);
                  }}
                  placeholder="Search operator…"
                />
              )}

              {(taskModalState.mode == 'create' ||
                taskModalState.mode == 'edit' ||
                (scope.scopeType == 'ai' && taskModalState.mode !== 'run')) && (
                <QuickSearch
                  label="Connection *"
                  value={formData.connection_laui}
                  filters={{ item_type: 'connection' }}
                  disabled={loading || isConnectionDisabled}
                  onSelect={(item) => {
                    const raw = item as Record<string, unknown>;
                    const laui = (raw._laui ?? raw.laui ?? raw.id ?? '') as string;
                    handleConnectionChange(laui);
                  }}
                  placeholder="Search connection…"
                />
              )}

              {/* Retry Configuration */}
              {(taskModalState.mode === 'create' ||
                taskModalState.mode == 'edit' ||
                taskModalState.mode === 'schedule') && (
                <Box
                  sx={{
                    mt: 2,
                    p: 2,
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    bgcolor: 'var(--bg-secondary)',
                  }}
                >
                  <Typography
                    sx={{
                      fontSize: '12px',
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      mb: 2,
                    }}
                  >
                    Retry Configuration
                  </Typography>
                  <Box sx={{ display: 'flex', gap: 2 }}>
                    <StyledTextField
                      label="Total Retries"
                      value={formData.total_retries !== undefined ? formData.total_retries : ''}
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val === '' || /^\d+$/.test(val)) {
                          setFormData((prev) => ({
                            ...prev,
                            total_retries: val === '' ? undefined : parseInt(val, 10),
                          }));
                        }
                      }}
                      disabled={loading}
                      placeholder="0"
                      slotProps={{
                        htmlInput: {
                          inputMode: 'numeric',
                          pattern: '[0-9]*',
                          min: 0,
                        },
                      }}
                      sx={{ flex: 1, mb: 0 }}
                    />
                    <StyledTextField
                      label="Retry Interval (minutes)"
                      value={formData.retry_interval !== undefined ? formData.retry_interval : ''}
                      onChange={(e) => {
                        const val = e.target.value;
                        if (val === '' || /^\d+$/.test(val)) {
                          setFormData((prev) => ({
                            ...prev,
                            retry_interval: val === '' ? undefined : parseInt(val, 10),
                          }));
                        }
                      }}
                      disabled={loading}
                      placeholder="0"
                      slotProps={{
                        htmlInput: {
                          inputMode: 'numeric',
                          pattern: '[0-9]*',
                          min: 0,
                        },
                      }}
                      sx={{ flex: 1, mb: 0 }}
                    />
                  </Box>
                </Box>
              )}
              {(taskModalState.mode == 'create' ||
                taskModalState.mode == 'edit' ||
                (scope.scopeType == 'ai' && taskModalState.mode !== 'run')) && (
                <Box>
                  <QuickSearch
                    label="Attached Configs (Optional)"
                    filters={{ item_type: 'config' }}
                    disabled={loading}
                    onSelect={(rawItem) => {
                      const raw = rawItem as Record<string, unknown>;
                      const laui = (raw._laui ?? raw.laui ?? raw.id ?? '') as string;
                      const name = (raw.name as string) ?? laui;
                      if (laui && !selectedConfigs.includes(laui)) {
                        const next = [...selectedConfigs, laui];
                        setSelectedConfigLabels((prev) => ({
                          ...prev,
                          [laui]: name,
                        }));
                        handleConfigsChange(next);
                      }
                    }}
                    placeholder="Search and add configs…"
                  />
                  {selectedConfigs.length > 0 && (
                    <Box
                      sx={{
                        display: 'flex',
                        flexWrap: 'wrap',
                        gap: 0.5,
                        mb: 1,
                        mt: 0.5,
                      }}
                    >
                      {selectedConfigs.map((laui) => (
                        <Chip
                          key={laui}
                          label={selectedConfigLabels[laui] ?? laui}
                          onClick={() =>
                            void navigate({
                              to: '/path',
                              search: {
                                itemtype: 'config',
                                itemname: selectedConfigLabels[laui] ?? laui,
                                laui,
                              },
                            })
                          }
                          onDelete={() => {
                            const next = selectedConfigs.filter((c) => c !== laui);
                            handleConfigsChange(next);
                          }}
                          size="small"
                          sx={{
                            backgroundColor: 'var(--bg-secondary)',
                            color: 'var(--text-primary)',
                            fontSize: '12px',
                            cursor: 'pointer',
                          }}
                        />
                      ))}
                    </Box>
                  )}
                </Box>
              )}

              {(taskModalState.mode == 'create' ||
                taskModalState.mode == 'edit' ||
                (scope.scopeType == 'ai' && taskModalState.mode !== 'run')) && (
                <StyledTextField
                  label="Config (JSON)"
                  value={configInput}
                  onChange={(e) => handleConfigInputChange(e.target.value)}
                  disabled={loading}
                  placeholder='{"key": "value"}'
                  multiline
                  rows={4}
                  error={!!configError}
                  helperText={
                    <span style={{ color: 'var(--text-primary)' }}>
                      Optional JSON config merged with connection config at runtime
                    </span>
                  }
                  inputProps={{
                    style: {
                      fontFamily: 'monospace',
                      fontSize: '12px',
                      color: 'var(--text-primary)',
                    },
                  }}
                  sx={{
                    mb: 0,
                    '& .MuiInputBase-root': {
                      color: 'var(--text-primary)',
                    },
                    '& .MuiInputBase-input': {
                      color: 'var(--text-primary)',
                    },
                    '& textarea': {
                      color: 'var(--text-primary)',
                    },
                  }}
                />
              )}

              {/* Payload Dropdown - Select existing payload or enter manually */}
              {(taskModalState.mode == 'create' ||
                taskModalState.mode == 'edit' ||
                (scope.scopeType == 'ai' && taskModalState.mode !== 'run')) && (
                <Typography
                  sx={{
                    fontSize: '12px',
                    color: 'var(--text-secondary)',
                    mt: 0.5,
                  }}
                >
                  Enter a payload below or select from the dropdown. At least one is required.
                </Typography>
              )}
              {(taskModalState.mode == 'create' ||
                taskModalState.mode == 'edit' ||
                (scope.scopeType == 'ai' && taskModalState.mode !== 'run')) && (
                <QuickSearch
                  label="Payload (Optional)"
                  value={formData.payload_laui}
                  filters={{ item_type: 'payload' }}
                  disabled={loading || isPayloadDisabled}
                  onSelect={(item) => {
                    const raw = item as Record<string, unknown>;
                    const laui = (raw._laui ?? raw.laui ?? raw.id ?? '') as string;
                    void handlePayloadChange(laui);
                  }}
                  placeholder="Search payload…"
                />
              )}

              {(taskModalState.mode == 'create' ||
                taskModalState.mode == 'edit' ||
                (scope.scopeType == 'ai' && taskModalState.mode !== 'run')) && (
                <StyledTextField
                  label="Payload"
                  value={formData.payload}
                  onChange={(e) => handleChange('payload', e.target.value)}
                  disabled={isPayloadFieldDisabled}
                  placeholder={
                    selectedPayload && loadingPayloadContent
                      ? 'Loading payload content...'
                      : selectedPayload
                        ? 'Payload content loaded from selection (clear dropdown to type custom payload)'
                        : 'Enter payload string or select from dropdown above'
                  }
                  multiline
                  rows={4}
                  error={!!error && !formData.payload.trim()}
                  inputProps={{
                    style: {
                      fontFamily: 'monospace',
                      fontSize: '12px',
                      color: 'var(--text-primary)',
                    },
                  }}
                  sx={{
                    mb: 0,
                    '& .MuiInputBase-root': {
                      color: 'var(--text-primary)',
                    },
                    '& .MuiInputBase-input': {
                      color: 'var(--text-primary)',
                    },
                    '& textarea': {
                      color: 'var(--text-primary)',
                    },
                    '& .MuiInputBase-input.Mui-disabled': {
                      WebkitTextFillColor: isPayloadFieldDisabled
                        ? 'var(--text-primary)'
                        : 'inherit',
                    },
                    '& .MuiInputBase-root.Mui-disabled textarea': {
                      WebkitTextFillColor: isPayloadFieldDisabled
                        ? 'var(--text-primary)'
                        : 'inherit',
                    },
                  }}
                />
              )}
              {/* Task Actions Section */}

              {(taskModalState.mode == 'create' ||
                taskModalState.mode == 'edit' ||
                (scope.scopeType == 'ai' && taskModalState.mode !== 'run')) && (
                <Box
                  sx={{
                    p: 2,
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    bgcolor: 'var(--bg-secondary)',
                  }}
                >
                  <Typography
                    sx={{
                      fontSize: '12px',
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      mb: 1.5,
                    }}
                  >
                    Task Actions (Optional)
                  </Typography>

                  <Box
                    sx={{
                      display: 'flex',
                      gap: 1,
                      alignItems: 'center',
                      mb: 1,
                    }}
                  >
                    <FormControl size="small" sx={{ minWidth: 130 }}>
                      <InputLabel
                        sx={{
                          fontSize: '12px',
                          color: 'var(--text-secondary)',
                          '&.Mui-focused': { color: 'var(--accent)' },
                        }}
                      >
                        When
                      </InputLabel>
                      <Select
                        value={selectedLifecycle}
                        label="When"
                        onChange={(e) => setSelectedLifecycle(e.target.value)}
                        sx={{
                          fontSize: '12px',
                          bgcolor: 'var(--bg-tertiary)',
                          color: 'var(--text-primary)',
                          '& .MuiOutlinedInput-notchedOutline': {
                            borderColor: 'var(--border)',
                          },
                          '&:hover .MuiOutlinedInput-notchedOutline': {
                            borderColor: 'var(--accent)',
                          },
                          '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                            borderColor: 'var(--accent)',
                          },
                          '& .MuiSelect-icon': {
                            color: 'var(--text-secondary)',
                          },
                        }}
                        MenuProps={{
                          PaperProps: {
                            sx: {
                              bgcolor: 'var(--bg-secondary)',
                              border: '1px solid var(--border)',
                              '& .MuiMenuItem-root': {
                                color: 'var(--text-primary)',
                                fontSize: '12px',
                                '&:hover': {
                                  bgcolor: 'var(--bg-tertiary)',
                                },
                                '&.Mui-selected': {
                                  bgcolor: 'var(--bg-tertiary)',
                                  '&:hover': {
                                    bgcolor: 'var(--bg-tertiary)',
                                  },
                                },
                              },
                            },
                          },
                        }}
                      >
                        <MenuItem value="create_actions">Create Action</MenuItem>
                        <MenuItem value="pre_actions">Pre Action</MenuItem>
                        <MenuItem value="post_actions">Post Action</MenuItem>
                        <MenuItem value="running_actions">Running Action</MenuItem>
                      </Select>
                    </FormControl>
                    <Box sx={{ flex: 1 }}>
                      <QuickSearch
                        label="Select Action"
                        value={selectedActionLaui}
                        filters={{ item_type: 'action' }}
                        onSelect={(item) => {
                          const raw = item as Record<string, unknown>;
                          setSelectedActionLaui((raw._laui ?? raw.laui ?? raw.id ?? '') as string);
                          setSelectedActionName((raw.name ?? '') as string);
                        }}
                        placeholder="Search action…"
                      />
                    </Box>
                  </Box>

                  {selectedActionLaui && (
                    <Box
                      sx={{
                        p: 1.5,
                        mb: 1.5,
                        bgcolor: 'var(--bg-tertiary)',
                        borderRadius: '6px',
                        borderLeft: '3px solid var(--accent)',
                      }}
                    >
                      <Typography
                        sx={{
                          fontSize: '11px',
                          color: 'var(--text-secondary)',
                          mb: 1,
                        }}
                      >
                        Configure Variables:
                      </Typography>
                      <QuickSearch
                        label="Connection (Optional)"
                        value={tempActionConnection}
                        filters={{ item_type: 'connection' }}
                        onSelect={(item) => {
                          const raw = item as Record<string, unknown>;
                          setTempActionConnection(
                            (raw._laui ?? raw.laui ?? raw.id ?? '') as string,
                          );
                        }}
                        placeholder="Search connection…"
                      />
                      <Box sx={{ mb: 1.5 }} />
                      {loadingActionVars ? (
                        <Typography
                          sx={{
                            fontSize: '11px',
                            color: 'var(--text-secondary)',
                          }}
                        >
                          Loading...
                        </Typography>
                      ) : (
                        <ModalForm formValues={tempActionVars} setFormValues={setTempActionVars} />
                      )}
                      {selectedLifecycle === 'running_actions' && (
                        <StyledTextField
                          label="SLA"
                          value={tempActionSla}
                          onChange={(e) => {
                            const val = e.target.value;
                            if (val === '' || /^[1-9]\d*$/.test(val)) setTempActionSla(val);
                          }}
                          placeholder="e.g. 30"
                          slotProps={{
                            htmlInput: {
                              inputMode: 'numeric',
                              pattern: '[0-9]*',
                            },
                          }}
                          sx={{ mt: 1 }}
                        />
                      )}
                      <Button
                        startIcon={<AddIcon fontSize="small" />}
                        onClick={handleAddTaskAction}
                        size="small"
                        variant="outlined"
                        sx={{
                          mt: 1,
                          fontSize: '11px',
                          textTransform: 'none',
                          color: 'var(--accent)',
                          borderColor: 'var(--accent)',
                        }}
                      >
                        Add Another Action
                      </Button>
                    </Box>
                  )}

                  {taskActions.length > 0 && (
                    <Box
                      sx={{
                        display: 'flex',
                        flexDirection: 'column',
                        gap: 0.75,
                      }}
                    >
                      <Typography
                        sx={{
                          fontSize: '11px',
                          color: 'var(--text-secondary)',
                          mb: 0.5,
                        }}
                      >
                        Configured Actions:
                      </Typography>
                      {taskActions.map((action, index) => (
                        <Box
                          key={index}
                          sx={{
                            bgcolor: 'var(--bg-tertiary)',
                            borderRadius: '6px',
                            border: '1px solid var(--border)',
                            overflow: 'hidden',
                          }}
                        >
                          <Box
                            sx={{
                              display: 'flex',
                              justifyContent: 'space-between',
                              alignItems: 'center',
                              p: 1,
                              cursor: 'pointer',
                              '&:hover': {
                                bgcolor: 'var(--bg-secondary)',
                              },
                            }}
                            onClick={() => handleExpandAction(index)}
                          >
                            <Box
                              sx={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 1,
                              }}
                            >
                              <Chip
                                label={action.lifecycleType.replace('_', ' ')}
                                size="small"
                                sx={{
                                  fontSize: '10px',
                                  height: '20px',
                                  bgcolor:
                                    action.lifecycleType === 'create_actions'
                                      ? '#9C27B0'
                                      : action.lifecycleType === 'pre_actions'
                                        ? '#4CAF50'
                                        : action.lifecycleType === 'post_actions'
                                          ? 'orange'
                                          : '#2196F3',
                                  color: 'white',
                                }}
                              />
                              <Typography
                                sx={{
                                  fontSize: '12px',
                                  fontWeight: 500,
                                  color: 'var(--text-primary)',
                                }}
                              >
                                {action.actionName}
                              </Typography>
                              <Typography
                                sx={{
                                  fontSize: '10px',
                                  color: 'var(--text-secondary)',
                                }}
                              >
                                ({Object.keys(action.variables).length} vars)
                              </Typography>
                            </Box>
                            <Box
                              sx={{
                                display: 'flex',
                                alignItems: 'center',
                              }}
                            >
                              <IconButton
                                size="small"
                                sx={{
                                  color: 'var(--text-secondary)',
                                  p: 0.5,
                                }}
                              >
                                {expandedActionIndex === index ? (
                                  <ExpandLessIcon fontSize="small" />
                                ) : (
                                  <ExpandMoreIcon fontSize="small" />
                                )}
                              </IconButton>
                              <IconButton
                                size="small"
                                onClick={(e) => {
                                  e.stopPropagation();
                                  handleRemoveTaskAction(index);
                                }}
                                sx={{
                                  color: 'var(--error)',
                                  p: 0.5,
                                }}
                              >
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </Box>
                          </Box>
                          {expandedActionIndex === index && (
                            <Box
                              sx={{
                                p: 1.5,
                                pt: 0.5,
                                borderTop: '1px solid var(--border)',
                              }}
                            >
                              <QuickSearch
                                label="Connection (Optional)"
                                value={
                                  tempEditActionConnection[index] ?? action.connection_laui ?? ''
                                }
                                filters={{
                                  item_type: 'connection',
                                }}
                                onSelect={(item) => {
                                  const raw = item as Record<string, unknown>;
                                  setTempEditActionConnection((prev) => ({
                                    ...prev,
                                    [index]: (raw._laui ?? raw.laui ?? raw.id ?? '') as string,
                                  }));
                                }}
                                placeholder="Search connection…"
                              />
                              <Box sx={{ mb: 1.5 }} />
                              <ModalForm
                                formValues={tempEditActionVars[index] || action.variables}
                                setFormValues={(newVars) =>
                                  setTempEditActionVars((prev) => ({
                                    ...prev,
                                    [index]:
                                      typeof newVars === 'function'
                                        ? newVars(prev[index] || action.variables)
                                        : newVars,
                                  }))
                                }
                              />
                              {action.lifecycleType === 'running_actions' && (
                                <StyledTextField
                                  label="SLA"
                                  value={tempEditActionSla[index] ?? action.sla ?? ''}
                                  onChange={(e) => {
                                    const val = e.target.value;
                                    if (val === '' || /^[1-9]\d*$/.test(val))
                                      setTempEditActionSla((prev) => ({
                                        ...prev,
                                        [index]: val,
                                      }));
                                  }}
                                  placeholder="e.g. 30"
                                  slotProps={{
                                    htmlInput: {
                                      inputMode: 'numeric',
                                      pattern: '[0-9]*',
                                    },
                                  }}
                                  sx={{ mt: 1 }}
                                />
                              )}
                            </Box>
                          )}
                        </Box>
                      ))}
                    </Box>
                  )}
                </Box>
              )}

              {/* Scheduling Section - show for schedule mode or when editing a scheduled task */}
              {taskModalState.mode === 'schedule' && (
                <Box
                  sx={{
                    mt: 2,
                    p: 2,
                    border: '1px solid var(--border)',
                    borderRadius: '8px',
                    bgcolor: 'var(--bg-secondary)',
                  }}
                >
                  <Typography
                    sx={{
                      fontSize: '12px',
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      mb: 2,
                    }}
                  >
                    Schedule Configuration
                  </Typography>

                  <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
                    <Autocomplete
                      freeSolo
                      disabled={loading}
                      options={CRON_EXPRESSIONS}
                      getOptionLabel={(opt) => (typeof opt === 'string' ? opt : opt.value)}
                      inputValue={frequency}
                      onInputChange={(_e, val) => setFrequency(val)}
                      onChange={(_e, val) => {
                        if (val && typeof val !== 'string') setFrequency(val.value);
                      }}
                      renderOption={(props, opt) => (
                        <li
                          {...props}
                          key={opt.value}
                          style={{
                            flexDirection: 'column',
                            alignItems: 'flex-start',
                            padding: '8px 16px',
                          }}
                        >
                          <Box
                            sx={{
                              display: 'flex',
                              alignItems: 'center',
                              gap: 1,
                            }}
                          >
                            <Typography
                              sx={{
                                fontSize: '13px',
                                fontWeight: 500,
                                color: 'var(--text-primary)',
                              }}
                            >
                              {opt.label}
                            </Typography>
                            <Typography
                              sx={{
                                fontSize: '11px',
                                color: 'var(--accent)',
                                fontFamily: 'monospace',
                                bgcolor: 'var(--bg-primary)',
                                px: 0.75,
                                py: 0.25,
                                borderRadius: '4px',
                              }}
                            >
                              {opt.value}
                            </Typography>
                          </Box>
                          <Typography
                            sx={{
                              fontSize: '11px',
                              color: 'var(--text-secondary)',
                            }}
                          >
                            {opt.description}
                          </Typography>
                        </li>
                      )}
                      componentsProps={{
                        paper: {
                          sx: {
                            bgcolor: 'var(--bg-secondary)',
                            border: '1px solid var(--border)',
                            zIndex: 1400,
                          },
                        },
                      }}
                      renderInput={(params) => (
                        <TextField
                          {...params}
                          label="Frequency *"
                          size="small"
                          required
                          placeholder="Select or type a cron expression"
                          inputProps={{
                            ...params.inputProps,
                            style: {
                              fontFamily: 'monospace',
                              fontSize: '13px',
                              color: 'var(--text-primary)',
                            },
                          }}
                          sx={{
                            '& .MuiOutlinedInput-root': {
                              fontSize: '14px',
                              bgcolor: 'var(--bg-tertiary)',
                              color: 'var(--text-primary)',
                              '&:hover .MuiOutlinedInput-notchedOutline': {
                                borderColor: 'var(--accent)',
                              },
                              '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
                                borderColor: 'var(--accent)',
                              },
                            },
                            '& .MuiInputLabel-root': {
                              color: 'var(--text-secondary)',
                              fontSize: '14px',
                              '&.Mui-focused': {
                                color: 'var(--accent)',
                              },
                            },
                            '& .MuiOutlinedInput-notchedOutline': {
                              borderColor: 'var(--border)',
                            },
                            '& .MuiSvgIcon-root': {
                              color: 'var(--text-secondary)',
                            },
                          }}
                        />
                      )}
                    />

                    <LocalizationProvider dateAdapter={AdapterDayjs}>
                      <DateTimePicker
                        label={`Start Date (${tzLabel})`}
                        value={startDate}
                        onChange={(newValue) => setStartDate(newValue)}
                        disabled={loading}
                        ampm={false}
                        slotProps={{
                          textField: {
                            fullWidth: true,
                            size: 'small',
                            required: true,
                            sx: {
                              '& .MuiOutlinedInput-root': {
                                fontSize: '14px',
                                backgroundColor: 'var(--bg-primary)',
                                color: 'var(--text-primary) !important',
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
                                fontSize: '14px',
                                color: 'var(--text-secondary)',
                                '&.Mui-focused': {
                                  color: 'var(--accent)',
                                },
                                '&.Mui-disabled': {
                                  color: 'var(--text-disabled)',
                                },
                              },
                              '& .MuiOutlinedInput-notchedOutline': {
                                borderColor: 'var(--border)',
                              },
                              '& .MuiPickersSectionList-sectionContent, & .MuiPickersSectionList-sectionSeparator':
                                { color: 'var(--text-primary)' },
                              '& .MuiIconButton-root': {
                                color: 'var(--text-secondary)',
                              },
                            },
                          },
                        }}
                      />

                      <DateTimePicker
                        label={`End Date (${tzLabel})`}
                        value={stopDate}
                        onChange={(newValue) => setStopDate(newValue)}
                        disabled={loading}
                        ampm={false}
                        slotProps={{
                          textField: {
                            fullWidth: true,
                            size: 'small',
                            sx: {
                              '& .MuiOutlinedInput-root': {
                                fontSize: '14px',
                                backgroundColor: 'var(--bg-primary)',
                                color: 'var(--text-primary) !important',
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
                                fontSize: '14px',
                                color: 'var(--text-secondary)',
                                '&.Mui-focused': {
                                  color: 'var(--accent)',
                                },
                                '&.Mui-disabled': {
                                  color: 'var(--text-disabled)',
                                },
                              },
                              '& .MuiOutlinedInput-notchedOutline': {
                                borderColor: 'var(--border)',
                              },
                              '& .MuiPickersSectionList-sectionContent, & .MuiPickersSectionList-sectionSeparator':
                                { color: 'var(--text-primary)' },
                              '& .MuiIconButton-root': {
                                color: 'var(--text-secondary)',
                              },
                            },
                          },
                        }}
                      />
                    </LocalizationProvider>
                  </Box>
                </Box>
              )}
            </Box>
            {isSideBySideLogs && (
              <Box
                sx={{
                  flex: '1 1 60%',
                  minWidth: 0,
                  borderLeft: '1px solid var(--border)',
                  pl: 2,
                  display: 'flex',
                  flexDirection: 'column',
                }}
              >
                <Box
                  sx={{
                    display: 'flex',
                    justifyContent: 'space-between',
                    alignItems: 'center',
                    mb: 1,
                  }}
                >
                  <Typography
                    sx={{
                      fontSize: '13px',
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                    }}
                  >
                    Create Action Logs
                  </Typography>
                  <IconButton
                    size="small"
                    onClick={handleCloseLogsPanel}
                    sx={{ color: 'var(--text-secondary)' }}
                  >
                    <CloseIcon fontSize="small" />
                  </IconButton>
                </Box>
                {createActionSessions.length > 1 && (
                  <Tabs
                    value={activeSessionTab}
                    onChange={(_e, v) => setActiveSessionTab(v)}
                    variant="scrollable"
                    scrollButtons="auto"
                    sx={{
                      minHeight: '32px',
                      borderBottom: '1px solid var(--border)',
                      '& .MuiTab-root': {
                        minHeight: '32px',
                        fontSize: '11px',
                        textTransform: 'none',
                        color: 'var(--text-secondary)',
                        py: 0.5,
                      },
                      '& .Mui-selected': {
                        color: 'var(--text-primary) !important',
                      },
                      '& .MuiTabs-indicator': {
                        backgroundColor: 'var(--accent)',
                      },
                    }}
                  >
                    {createActionSessions.map((s, i) => {
                      const totalSameName = createActionSessions.filter(
                        (x) => x.actionName === s.actionName,
                      ).length;
                      const base = s.actionName || `Action ${i + 1}`;
                      const label = totalSameName > 1 ? `${base} #${s.occurrenceLabel}` : base;
                      return <Tab key={`${s.actionName}-${s.instanceIndex}`} label={label} />;
                    })}
                  </Tabs>
                )}
                {activeCreateSession && (
                  <Typography
                    sx={{
                      fontSize: '10px',
                      color: 'var(--text-secondary)',
                      wordBreak: 'break-all',
                      my: 0.5,
                    }}
                  >
                    Session: {activeCreateSession.sessionId}
                  </Typography>
                )}
                <Box sx={{ flex: 1, minHeight: 0, overflow: 'hidden' }}>
                  {activeCreateSession && (
                    <SessionDetailView
                      key={`${activeCreateSession.sessionId}-${activeCreateSession.actionName}-${activeCreateSession.instanceIndex}`}
                      sessionId={activeCreateSession.sessionId}
                      sessionDate={sessionDate}
                      pollUntilStable
                      actionFilter={activeCreateSession.actionName}
                      instanceIndex={activeCreateSession.instanceIndex}
                    />
                  )}
                </Box>
              </Box>
            )}
          </Box>
        )}
      </BaseModal>

      {/* Duplicate task confirmation */}
      <Dialog
        open={!!duplicateTask}
        onClose={() => setDuplicateTask(null)}
        PaperProps={{
          sx: { bgcolor: 'var(--bg-secondary)', color: 'var(--text-primary)' },
        }}
      >
        <DialogTitle sx={{ fontSize: '15px', fontWeight: 600 }}>Task Already Exists</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ color: 'var(--text-secondary)', fontSize: '13px', mb: 1 }}>
            A task named{' '}
            <strong style={{ color: 'var(--text-primary)' }}>"{duplicateTask?.name}"</strong>{' '}
            already exists with the following values:
          </DialogContentText>
          {duplicateTask && (
            <Alert severity="warning" sx={{ fontSize: '13px' }}>
              {[
                duplicateTask.item_type && `type: ${duplicateTask.item_type}`,
                duplicateTask.state && `state: ${duplicateTask.state}`,
                duplicateTask.laui && `id: ${duplicateTask.laui}`,
              ]
                .filter(Boolean)
                .join(' · ')}
            </Alert>
          )}
          <DialogContentText sx={{ color: 'var(--text-secondary)', fontSize: '13px', mt: 1.5 }}>
            Do you want to create a new task anyway?
          </DialogContentText>
        </DialogContent>
        <DialogActions sx={{ px: 2, pb: 2, gap: 1 }}>
          <Button
            size="small"
            variant="outlined"
            onClick={() => setDuplicateTask(null)}
            sx={{ color: 'var(--text-secondary)', borderColor: 'var(--border)' }}
          >
            Cancel
          </Button>
          <Button
            size="small"
            variant="contained"
            onClick={() => {
              skipDuplicateCheckRef.current = true;
              setDuplicateTask(null);
              void handleSubmit();
            }}
            sx={{
              bgcolor: 'var(--accent)',
              color: '#fff',
              '&:hover': { opacity: 0.9 },
            }}
          >
            Create
          </Button>
        </DialogActions>
      </Dialog>
    </>
  );
}
