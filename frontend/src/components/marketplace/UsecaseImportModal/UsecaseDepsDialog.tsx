/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useMemo, useRef, useState } from 'react';

import { Download as ImportIcon } from '@mui/icons-material';
import CancelIcon from '@mui/icons-material/Cancel';
import CheckCircleIcon from '@mui/icons-material/CheckCircle';
import WarningAmberIcon from '@mui/icons-material/WarningAmber';
import { Box, Button, Chip, LinearProgress, Stack, TextField, Typography } from '@mui/material';

import { QuickSearch } from '@/components/ui';
import BaseModal from '@/components/ui/Modal/BaseModal';
import { useCatalog } from '@/contexts/CatalogContext';
import { useGlobal } from '@/contexts/GlobalContext';
import { useNotification } from '@/contexts/NotificationContext';
import { createCatalogItem, getCatalogItemById, searchCatalogItems } from '@/services';

import type { DependencyStatus, ParsedPayload, PayloadDepGroup } from './types';
import { checkDependencies, groupPayloadsByDeps, parseAllPayloads } from './usecaseParser';

const fieldSx = {
  mb: 2,
  '& .MuiOutlinedInput-root': {
    backgroundColor: 'var(--bg-secondary)',
    color: 'var(--text-primary)',
    fontSize: '12px',
    '& fieldset': { borderColor: 'var(--border)' },
    '&:hover fieldset': { borderColor: 'var(--primary-main)' },
    '&.Mui-focused fieldset': { borderColor: 'var(--primary-main)' },
  },
  '& .MuiInputLabel-root': { color: 'var(--text-secondary)', fontSize: '12px' },
};

const typeChipColors: Record<string, string> = {
  operator: '#1e88e5',
  connection: '#43a047',
  action: '#8e24aa',
  config: '#6d6d6d',
};

interface UsecaseDepsDialogProps {
  open: boolean;
  onClose: () => void;
  itemName: string;
  payloads: (string | { filename: string; content: string })[];
  depCacheRef: React.MutableRefObject<Map<string, string>>;
  onStatusChange?: (statuses: DependencyStatus[], allRequiredResolved: boolean) => void;
}

export default function UsecaseDepsDialog({
  open,
  onClose,
  itemName,
  payloads,
  depCacheRef,
  onStatusChange,
}: UsecaseDepsDialogProps) {
  const { accountLaui } = useGlobal();
  const { showSuccess, showError } = useNotification();
  const { setImportModalState } = useCatalog();

  const [parsedPayloads, setParsedPayloads] = useState<ParsedPayload[]>([]);
  const [depStatuses, setDepStatuses] = useState<DependencyStatus[]>([]);
  const [depChecking, setDepChecking] = useState(false);

  // Manual dep resolution state
  const [depMode, setDepMode] = useState<Record<string, 'select' | 'manual'>>({});
  const [depManualValues, setDepManualValues] = useState<Record<string, Record<string, string>>>(
    {},
  );
  const [depManualName, setDepManualName] = useState<Record<string, string>>({});
  const [depManualParent, setDepManualParent] = useState<Record<string, string>>({});
  const [depTemplates, setDepTemplates] = useState<Record<string, Record<string, any>>>({});
  const [depCreating, setDepCreating] = useState<string | null>(null);

  const connToOperator = useMemo(() => {
    const map = new Map<string, string>();
    for (const p of parsedPayloads) {
      if (p.meta?.connection_name && p.meta?.operator_name) {
        map.set(p.meta.connection_name, p.meta.operator_name);
      }
    }
    return map;
  }, [parsedPayloads]);

  const payloadGroups = useMemo(() => groupPayloadsByDeps(parsedPayloads), [parsedPayloads]);

  const hasInitRef = useRef(false);

  useEffect(() => {
    if (!open) return;
    const parsed = parseAllPayloads(payloads);
    setParsedPayloads(parsed);
    if (!hasInitRef.current) {
      hasInitRef.current = true;
      void runDependencyCheck(parsed);
    }
  }, [open, payloads]);

  useEffect(() => {
    hasInitRef.current = false;
    setDepStatuses([]);
    depCacheRef.current.clear();
    setDepMode({});
    setDepManualValues({});
    setDepManualName({});
    setDepManualParent({});
    setDepTemplates({});
    setDepCreating(null);
  }, [itemName]);

  useEffect(() => {
    const allRequired =
      depStatuses.length > 0 &&
      depStatuses.filter((d) => d.type !== 'config').every((d) => d.found);
    onStatusChange?.(depStatuses, allRequired);
  }, [depStatuses]);

  // ---------------------------------------------------------------------------
  // Handlers
  // ---------------------------------------------------------------------------

  const runDependencyCheck = async (parsed: ParsedPayload[]) => {
    setDepChecking(true);
    try {
      const results = await checkDependencies(parsed);
      setDepStatuses(results);
      depCacheRef.current.clear();
      results.forEach((d) => {
        if (d.found && d.laui) depCacheRef.current.set(`${d.type}:${d.name}`, d.laui);
      });
    } catch {
      /* ignore */
    } finally {
      setDepChecking(false);
    }
  };

  const handleImportDependency = async (dep: DependencyStatus) => {
    try {
      const data = await searchCatalogItems(dep.type, true, {
        filters: { name: dep.name },
        projection: ['name', 'laui', 'item_type'],
        perPage: 1,
      });
      const items = data?.items ?? [];
      if (items.length > 0) {
        const mktItem = items[0].item ?? items[0];
        const fullItem = await getCatalogItemById(mktItem.laui ?? mktItem._id, true);
        onClose();
        setImportModalState({ isOpen: true, itemData: fullItem });
      } else {
        showError(`"${dep.name}" not found in marketplace`);
      }
    } catch {
      /* ignore */
    }
  };

  const handleSelectDep = (dep: DependencyStatus, selectedItem: unknown) => {
    const raw = selectedItem as Record<string, unknown>;
    const laui = (raw._laui ?? raw.laui ?? raw._id ?? '') as string;
    if (laui) {
      depCacheRef.current.set(`${dep.type}:${dep.name}`, laui);
      setDepStatuses((prev) =>
        prev.map((d) =>
          d.type === dep.type && d.name === dep.name ? { ...d, found: true, laui } : d,
        ),
      );
    }
  };

  const fetchDepTemplate = async (key: string, depType: string, depName: string) => {
    if (depType === 'connection') {
      const operatorName = connToOperator.get(depName);
      if (!operatorName) return;
      const operatorLaui = depCacheRef.current.get(`operator:${operatorName}`);
      if (!operatorLaui) {
        showError(`Operator "${operatorName}" not resolved yet — resolve it first`);
        return;
      }
      try {
        const operatorItem = await getCatalogItemById(operatorLaui);
        let template = (operatorItem as any)?.connection;
        if (typeof template === 'string') {
          try {
            template = JSON.parse(template);
          } catch {
            template = null;
          }
        }
        if (template && typeof template === 'object') {
          setDepTemplates((prev) => ({ ...prev, [key]: template }));
          const initial: Record<string, string> = {};
          for (const k of Object.keys(template))
            initial[k] = typeof template[k] === 'string' ? template[k] : '';
          setDepManualValues((prev) => ({ ...prev, [key]: initial }));
        } else {
          setDepTemplates((prev) => ({ ...prev, [key]: {} }));
          setDepManualValues((prev) => ({ ...prev, [key]: {} }));
        }
      } catch {
        showError(`Failed to fetch operator template for "${depName}"`);
      }
    } else {
      setDepTemplates((prev) => ({ ...prev, [key]: {} }));
      setDepManualValues((prev) => ({ ...prev, [key]: {} }));
    }
  };

  const handleCreateDep = async (dep: DependencyStatus) => {
    const key = `${dep.type}:${dep.name}`;
    const parentLaui = depManualParent[key];
    if (!parentLaui) {
      showError('Parent folder is required');
      return;
    }
    setDepCreating(key);
    try {
      const values = depManualValues[key] || {};
      const name = depManualName[key] || dep.name;
      const result = await createCatalogItem({
        item_type: dep.type,
        name,
        parent_laui: parentLaui,
        account_laui: accountLaui,
        content: values,
      });
      const laui = result?.laui ?? result?._id;
      if (laui) {
        depCacheRef.current.set(`${dep.type}:${dep.name}`, laui);
        setDepStatuses((prev) =>
          prev.map((d) =>
            d.type === dep.type && d.name === dep.name ? { ...d, found: true, laui } : d,
          ),
        );
        showSuccess(`${dep.type} "${name}" created`);
      }
    } catch (e: any) {
      showError(`Failed to create ${dep.type}: ${e?.message}`);
    } finally {
      setDepCreating(null);
    }
  };

  // ---------------------------------------------------------------------------
  // Render helpers
  // ---------------------------------------------------------------------------

  const findDep = (type: string, name: string): DependencyStatus | undefined =>
    depStatuses.find((d) => d.type === type && d.name === name);

  /** Render a single dependency row with status and resolution controls */
  const renderDepRow = (
    dep: DependencyStatus | undefined,
    canImport: boolean,
    required: boolean,
  ) => {
    if (!dep) return null;
    const key = `${dep.type}:${dep.name}`;
    const mode = depMode[key];
    const template = depTemplates[key];
    const manualValues = depManualValues[key] || {};
    const typeLabel = dep.type.charAt(0).toUpperCase() + dep.type.slice(1);
    const chipColor = typeChipColors[dep.type] || '#888';

    return (
      <Box key={key} sx={{ py: 0.4, pl: 0.5 }}>
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.75 }}>
          {dep.found ? (
            <CheckCircleIcon sx={{ fontSize: 14, color: 'success.main' }} />
          ) : required ? (
            <CancelIcon sx={{ fontSize: 14, color: 'error.main' }} />
          ) : (
            <WarningAmberIcon sx={{ fontSize: 14, color: 'warning.main' }} />
          )}
          <Chip
            label={typeLabel}
            size="small"
            sx={{
              height: 16,
              fontSize: '9px',
              fontWeight: 600,
              bgcolor: chipColor,
              color: '#fff',
              borderRadius: 'var(--radius-sm)',
            }}
          />
          <Typography sx={{ fontSize: '11px', color: 'var(--text-primary)', flex: 1 }}>
            {dep.name}
          </Typography>

          {/* Import button for operators/actions */}
          {!dep.found && canImport && !mode && (
            <Button
              size="small"
              variant="outlined"
              startIcon={<ImportIcon sx={{ fontSize: 12 }} />}
              onClick={() => void handleImportDependency(dep)}
              sx={{
                fontSize: '9px',
                textTransform: 'none',
                py: 0,
                px: 0.75,
                minHeight: 20,
              }}
            >
              Import
            </Button>
          )}
        </Box>

        {/* Manual resolution for connections/configs (or any unresolved dep) */}
        {!dep.found && !canImport && !mode && (
          <Stack direction="row" spacing={0.5} sx={{ pl: 2.5, mt: 0.5 }}>
            <Button
              size="small"
              variant="outlined"
              onClick={() => setDepMode((prev) => ({ ...prev, [key]: 'select' }))}
              sx={{
                fontSize: '9px',
                textTransform: 'none',
                py: 0,
                px: 0.75,
                minHeight: 20,
              }}
            >
              Select Existing
            </Button>
            <Button
              size="small"
              variant="outlined"
              onClick={() => {
                setDepMode((prev) => ({ ...prev, [key]: 'manual' }));
                if (!depManualName[key]) setDepManualName((prev) => ({ ...prev, [key]: dep.name }));
                void fetchDepTemplate(key, dep.type, dep.name);
              }}
              sx={{
                fontSize: '9px',
                textTransform: 'none',
                py: 0,
                px: 0.75,
                minHeight: 20,
              }}
            >
              Add Manually
            </Button>
          </Stack>
        )}

        {mode === 'select' && (
          <Box sx={{ pl: 2.5, mt: 0.5 }}>
            <QuickSearch
              filters={{ item_type: dep.type }}
              ignoreProjectScope={true}
              onSelect={(i) => handleSelectDep(dep, i)}
              placeholder={`Search ${dep.type}s...`}
            />
            <Button
              size="small"
              onClick={() =>
                setDepMode((prev) => {
                  const n = { ...prev };
                  delete n[key];
                  return n;
                })
              }
              sx={{ fontSize: '9px', textTransform: 'none', mt: 0.5 }}
            >
              Back
            </Button>
          </Box>
        )}

        {mode === 'manual' && (
          <Box
            sx={{
              pl: 2.5,
              mt: 0.5,
              border: '1px solid var(--border)',
              borderRadius: 1,
              p: 1,
            }}
          >
            <TextField
              label={`${typeLabel} Name`}
              value={depManualName[key] || ''}
              onChange={(e) => setDepManualName((prev) => ({ ...prev, [key]: e.target.value }))}
              fullWidth
              size="small"
              sx={fieldSx}
            />
            <Box sx={{ mb: 1 }}>
              <Typography variant="caption">Parent Folder</Typography>
              <QuickSearch
                value={depManualParent[key] || ''}
                ignoreProjectScope={true}
                onSelect={(val) => {
                  const raw = val as Record<string, unknown>;
                  setDepManualParent((prev) => ({
                    ...prev,
                    [key]: (raw._laui ?? raw.laui ?? raw.id ?? '') as string,
                  }));
                }}
                filters={{ item_type: `folder.${dep.type}` }}
              />
            </Box>
            {template ? (
              Object.keys(template).length > 0 ? (
                <>
                  <Typography
                    sx={{
                      fontSize: '10px',
                      color: 'var(--text-secondary)',
                      mb: 0.5,
                    }}
                  >
                    {typeLabel} Fields (from operator)
                  </Typography>
                  {Object.keys(template).map((fk) => (
                    <TextField
                      key={fk}
                      label={fk}
                      value={manualValues[fk] ?? ''}
                      onChange={(e) =>
                        setDepManualValues((prev) => ({
                          ...prev,
                          [key]: {
                            ...(prev[key] || {}),
                            [fk]: e.target.value,
                          },
                        }))
                      }
                      fullWidth
                      size="small"
                      sx={fieldSx}
                      placeholder={String(template[fk] ?? '')}
                    />
                  ))}
                </>
              ) : (
                <Typography
                  sx={{
                    fontSize: '10px',
                    color: 'var(--text-secondary)',
                    fontStyle: 'italic',
                    mb: 0.5,
                  }}
                >
                  No template found on operator
                </Typography>
              )
            ) : (
              <Typography
                sx={{
                  fontSize: '10px',
                  color: 'var(--text-secondary)',
                  fontStyle: 'italic',
                  mb: 0.5,
                }}
              >
                Loading template...
              </Typography>
            )}
            <Stack direction="row" spacing={0.5} sx={{ mt: 1 }}>
              <Button
                size="small"
                variant="contained"
                onClick={() => void handleCreateDep(dep)}
                disabled={depCreating === key || !depManualParent[key]}
                sx={{ fontSize: '9px', textTransform: 'none' }}
              >
                {depCreating === key ? 'Creating...' : `Create ${typeLabel}`}
              </Button>
              <Button
                size="small"
                onClick={() =>
                  setDepMode((prev) => {
                    const n = { ...prev };
                    delete n[key];
                    return n;
                  })
                }
                sx={{ fontSize: '9px', textTransform: 'none' }}
              >
                Back
              </Button>
            </Stack>
          </Box>
        )}
      </Box>
    );
  };

  const renderPayloadGroup = (group: PayloadDepGroup, index: number) => {
    const opDep = group.operator_name ? findDep('operator', group.operator_name) : undefined;
    const connDep = group.connection_name
      ? findDep('connection', group.connection_name)
      : undefined;

    return (
      <Box
        key={index}
        sx={{
          mb: 1.5,
          border: '1px solid var(--border)',
          borderRadius: 1,
          p: 1,
          bgcolor: 'var(--bg-secondary)',
        }}
      >
        {/* Payload names header */}
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 0.75 }}>
          {group.payloadNames.map((name, i) => (
            <Chip
              key={i}
              label={name}
              size="small"
              sx={{
                height: 18,
                fontSize: '10px',
                fontWeight: 600,
                bgcolor: 'var(--bg-primary)',
                color: 'var(--text-primary)',
                border: '1px solid var(--border)',
              }}
            />
          ))}
        </Box>

        {/* Dependencies for this group */}
        {opDep && renderDepRow(opDep, true, true)}
        {connDep && renderDepRow(connDep, false, true)}
        {group.action_names.map((a) => renderDepRow(findDep('action', a), true, true))}
        {group.config_names.map((c) => renderDepRow(findDep('config', c), false, false))}
      </Box>
    );
  };

  return (
    <BaseModal
      open={open}
      onClose={onClose}
      title={`Dependencies: ${itemName}`}
      subtitle="Resolve dependencies before importing"
      maxWidth="sm"
    >
      <Stack spacing={1}>
        <Box sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}>
          <Typography sx={{ fontSize: '12px', fontWeight: 600, color: 'var(--text-primary)' }}>
            {payloadGroups.length} group{payloadGroups.length !== 1 ? 's' : ''} from{' '}
            {parsedPayloads.filter((p) => p.meta).length} payload
            {parsedPayloads.filter((p) => p.meta).length !== 1 ? 's' : ''}
          </Typography>
          <Button
            size="small"
            onClick={() => void runDependencyCheck(parsedPayloads)}
            disabled={depChecking}
            sx={{ fontSize: '10px', textTransform: 'none', minHeight: 22 }}
          >
            {depChecking ? 'Checking...' : 'Recheck'}
          </Button>
        </Box>

        {depChecking ? (
          <LinearProgress sx={{ '& .MuiLinearProgress-bar': { bgcolor: 'var(--accent)' } }} />
        ) : (
          payloadGroups.map((group, i) => renderPayloadGroup(group, i))
        )}
      </Stack>
    </BaseModal>
  );
}
