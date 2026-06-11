/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import { Code as CodeIcon, TuneOutlined as TuneIcon } from '@mui/icons-material';
import { Alert, Box, ToggleButton, ToggleButtonGroup, Tooltip } from '@mui/material';

import { MonacoField } from '@/components/ui';

import type { FieldRendererProps } from '../types';
import { JsonFormRenderer } from './JsonFormRenderer';
import { useJsonState } from './useJsonState';

type EditorMode = 'json' | 'ui';

interface FancyJsonEditorProps extends Pick<FieldRendererProps, 'field' | 'value' | 'onChange'> {
  isReadOnly?: boolean;
  mode?: string;
}

export function FancyJsonEditor({
  field,
  value,
  onChange,
  isReadOnly = false,
  mode,
}: FancyJsonEditorProps) {
  const [editorMode, setEditorMode] = useState<EditorMode>('ui');

  const isEmpty = value == null || value === '' || value === '{}' || value === 'null';
  const defaultValue =
    isEmpty && (mode === 'edit' || mode === 'create')
      ? (field.default ?? field.sample_placeholder ?? null)
      : null;

  const state = useJsonState({
    initialValue: defaultValue ?? value,
    fieldName: field.name,
    onChange,
  });

  const readOnly = isReadOnly || mode === 'view';

  const handleModeChange = (_: React.MouseEvent<HTMLElement>, newMode: EditorMode | null) => {
    if (!newMode) return;
    if (newMode === 'ui' && state.parseError) return; // block switch on bad JSON
    setEditorMode(newMode);
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
      {/* Header row: toggle */}
      <Box sx={{ display: 'flex', justifyContent: 'flex-end' }}>
        <ToggleButtonGroup
          size="small"
          exclusive
          value={editorMode}
          onChange={handleModeChange}
          sx={{
            '& .MuiToggleButton-root': {
              color: 'var(--text-secondary)',
              borderColor: 'var(--border)',
              fontSize: '11px',
              gap: 0.5,
              px: 1.5,
              py: 0.5,
              textTransform: 'none',
              '&.Mui-selected': {
                bgcolor: 'var(--bg-tertiary)',
                color: 'var(--text-primary)',
              },
            },
          }}
        >
          <Tooltip title={state.parseError ? 'Fix JSON errors before switching' : 'Form editor'}>
            {/* span needed so Tooltip works on disabled button */}
            <span>
              <ToggleButton
                value="ui"
                aria-label="UI editor"
                disabled={!!state.parseError}
                sx={{ pointerEvents: state.parseError ? 'none' : undefined }}
              >
                <TuneIcon sx={{ fontSize: 14 }} />
                UI
              </ToggleButton>
            </span>
          </Tooltip>
          <Tooltip title="Raw JSON editor">
            <ToggleButton value="json" aria-label="JSON editor">
              <CodeIcon sx={{ fontSize: 14 }} />
              JSON
            </ToggleButton>
          </Tooltip>
        </ToggleButtonGroup>
      </Box>

      {/* Parse error banner (JSON mode only) */}
      {editorMode === 'json' && state.parseError && (
        <Alert
          severity="warning"
          sx={{
            py: 0.25,
            fontSize: '12px',
            bgcolor: 'var(--bg-tertiary)',
            color: 'var(--warning, #f59e0b)',
            '& .MuiAlert-icon': { color: 'var(--warning, #f59e0b)' },
          }}
        >
          {state.parseError}
        </Alert>
      )}

      {/* Editor area */}
      {editorMode === 'json' ? (
        <MonacoField
          field={field}
          value={state.jsonText}
          onChange={(_name, text) => state.handleMonacoChange(text as string)}
          isReadOnly={readOnly}
          mode={mode}
        />
      ) : (
        <Box
          sx={{
            border: '1px solid var(--border)',
            borderRadius: 1,
            bgcolor: 'var(--bg-primary)',
            p: 2,
            overflowY: 'auto',
            maxHeight: 'calc(100vh - 310px)',
          }}
        >
          <JsonFormRenderer
            parsedValue={state.parsedValue}
            readOnly={readOnly}
            onUiChange={state.handleUiChange}
            onAddKey={state.handleAddKey}
            onRemoveKey={state.handleRemoveKey}
            fieldSchema={field.properties}
          />
        </Box>
      )}
    </Box>
  );
}
