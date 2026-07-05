/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useMemo, useRef, useState } from 'react';

import { Box, Button, CircularProgress, ToggleButton, ToggleButtonGroup } from '@mui/material';

import FieldRenderer, { TabFields } from '@/components/browse/FieldRenderer';
import { LauiDropdown } from '@/components/browse/FieldRenderer/LauiDropdown';
import { getSchema } from '@/services/schema.service';

import { generateTabs } from './tabUtils';

export type AttachedConfigValue =
  | { mode: 'existing'; configLaui: string }
  | { mode: 'create'; configForm: Record<string, any> };

interface WorkflowConfigFieldProps {
  value: AttachedConfigValue | undefined;
  onChange: (fieldName: string, value: AttachedConfigValue | undefined) => void;
  defaultName?: string;
}

const FIELD_NAME = 'attached_config';

type PanelMode = 'existing' | 'create';

const toggleSx = {
  '& .MuiToggleButton-root': {
    textTransform: 'none',
    fontSize: '12px',
    color: 'var(--text-secondary)',
    borderColor: 'var(--border)',
    '&.Mui-selected': {
      bgcolor: 'var(--accent)',
      color: '#fff',
      '&:hover': { bgcolor: 'var(--accent)' },
    },
  },
};

/** Build initial create-form data from config schema columns (mirrors TabView create defaults). */
function buildInitialConfigForm(columns: any[], defaultName?: string): Record<string, any> {
  const data: Record<string, any> = {};
  columns.forEach((f: any) => {
    if (f.datatype === 'array') data[f.name] = f.default ?? [];
    else if (f.datatype === 'object') data[f.name] = f.default ?? f.sample_placeholder ?? {};
    else data[f.name] = f.default ?? '';
  });
  if (defaultName && !data.name) data.name = `${defaultName} config`;
  // Sensible default for a config attached to a workflow.
  if ('config_type' in data && !data.config_type) data.config_type = 'workflow';
  return data;
}

export const WorkflowConfigField = ({ value, onChange, defaultName }: WorkflowConfigFieldProps) => {
  const [schema, setSchema] = useState<any>(null);
  const [loadingSchema, setLoadingSchema] = useState(false);

  // Default to "Select existing". null = explicitly cleared (no toggle highlighted).
  const [panelMode, setPanelMode] = useState<PanelMode | null>(value?.mode ?? 'existing');
  const createFormRef = useRef<HTMLDivElement>(null);

  // When the create form opens, scroll it into view so the editor is visible.
  useEffect(() => {
    if (panelMode === 'create' && !loadingSchema) {
      createFormRef.current?.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
  }, [panelMode, loadingSchema]);

  useEffect(() => {
    let cancelled = false;
    setLoadingSchema(true);
    getSchema('config')
      .then((s) => {
        if (!cancelled) setSchema(s);
      })
      .catch((err) => console.error('WorkflowConfigField: failed to load config schema', err))
      .finally(() => {
        if (!cancelled) setLoadingSchema(false);
      });
    return () => {
      cancelled = true;
    };
  }, []);

  // The "create new config" fields, reusing the real Add Config form's Overview tab.
  const overviewFields = useMemo(() => {
    if (!schema) return [];
    const { tabFields } = generateTabs(schema, {
      mode: 'create',
      filterType: 'config',
      userUpdateFields: schema.user_update_fields,
    });
    // Drop the synthetic "attach existing config" field — this panel already provides
    // a "Select existing" toggle, so it would be redundant inside the create form.
    return (tabFields['Overview'] ?? []).filter((f: any) => f.name !== 'existing_config_laui');
  }, [schema]);

  const configForm = value?.mode === 'create' ? value.configForm : {};

  const handleModeChange = (_: React.MouseEvent<HTMLElement>, newMode: PanelMode | null) => {
    // Ignore deselect (clicking the active button) — use the Clear button to detach.
    if (!newMode || newMode === panelMode) return;
    setPanelMode(newMode);
    if (newMode === 'existing') {
      onChange(FIELD_NAME, { mode: 'existing', configLaui: '' });
    } else {
      onChange(FIELD_NAME, {
        mode: 'create',
        configForm: buildInitialConfigForm(overviewFields, defaultName),
      });
    }
  };

  const handleClear = () => {
    setPanelMode(null);
    onChange(FIELD_NAME, undefined);
  };

  const handleConfigFieldChange = (fieldName: string, fieldValue: any) => {
    onChange(FIELD_NAME, {
      mode: 'create',
      configForm: { ...configForm, [fieldName]: fieldValue },
    });
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={panelMode}
          onChange={handleModeChange}
          sx={toggleSx}
        >
          <ToggleButton value="existing">Select existing</ToggleButton>
          <ToggleButton value="create">Create new</ToggleButton>
        </ToggleButtonGroup>
        {panelMode && (
          <Button
            size="small"
            onClick={handleClear}
            sx={{ textTransform: 'none', fontSize: '12px', color: 'var(--text-secondary)' }}
          >
            Clear
          </Button>
        )}
      </Box>

      {panelMode === 'existing' && (
        <LauiDropdown
          fieldName="config_laui"
          value={value?.mode === 'existing' ? value.configLaui : ''}
          onChange={(_, configLaui) =>
            onChange(FIELD_NAME, { mode: 'existing', configLaui: configLaui || '' })
          }
        />
      )}

      {panelMode === 'create' &&
        (loadingSchema ? (
          <CircularProgress size={20} />
        ) : (
          <Box ref={createFormRef}>
            <TabFields
              fields={overviewFields}
              formData={configForm}
              mode="create"
              renderField={(field: any) => (
                <FieldRenderer
                  field={field}
                  value={configForm[field.name] ?? ''}
                  mode="create"
                  onChange={handleConfigFieldChange}
                  itemData={null}
                />
              )}
            />
          </Box>
        ))}
    </Box>
  );
};
