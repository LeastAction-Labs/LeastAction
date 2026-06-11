/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { InfoOutlined as InfoIcon } from '@mui/icons-material';
import { Box, FormControl, MenuItem, Select, Tooltip, Typography } from '@mui/material';

import { MonacoField, SimpleTextField, TextAreaField } from '@/components/ui';
import ValidationResultsView from '@/components/validation/ValidationResultsView';
import { FONT_SIZES, FONT_WEIGHTS } from '@/constants';

import { ArrayField } from './ArrayField';
import { ChipArrayField } from './ChipArrayField';
import { FancyJsonEditor } from './FancyJsonEditor';
import { LauiDropdown } from './LauiDropdown';
import { ViewModeRenderer } from './ViewModeRenderer';
import type { ArrayItem, FieldConfig, FieldRendererProps } from './types';

// Helper functions
const getFieldConfig = (field: any): FieldConfig => {
  return {
    editorType: field.editorType || 'textbox',
    editorMonacoFormat: field.editorMonacoFormat || 'auto',
    defaultFileName: field.defaultFileName || 'file',
    placeholder: field.placeholder || `Enter ${field.name}...`,
    fileNamePlaceholder: field.fileNamePlaceholder || `Enter file name...`,
    monacoHeight: field.monacoHeight || 'calc(100vh - 270px)',
    textAreaRows: field.textAreaRows || { min: 3, max: 6 },
    arrayTextAreaRows: field.arrayTextAreaRows || { min: 10, max: 20 },
  };
};

const shouldUseArrayFormat = (fieldName: string): boolean => {
  return (
    fieldName === 'codeblock' ||
    fieldName === 'bashblock' ||
    fieldName === 'payloads' ||
    fieldName === 'skills'
  );
};

const normalizeArrayValue = (value: any, defaultFileName: string): ArrayItem[] => {
  if (!value) return [];

  if (Array.isArray(value)) {
    return value.map((item, index) => {
      if (typeof item === 'object' && item !== null && 'fileName' in item && 'content' in item) {
        return item as ArrayItem;
      } else {
        return {
          fileName: `${defaultFileName}${index + 1}`,
          content: item || '',
        };
      }
    });
  } else if (typeof value === 'object' && value !== null) {
    return Object.entries(value).map(([fileName, content]) => ({
      fileName,
      content: content as string,
    }));
  } else if (typeof value === 'string') {
    return [
      {
        fileName: defaultFileName + '1',
        content: value,
      },
    ];
  }

  return [];
};

const convertToExternalFormat = (arrayItems: ArrayItem[], shouldUseArray: boolean): any => {
  if (!shouldUseArray) {
    return arrayItems.length > 0 ? arrayItems[0].content : '';
  }

  const result: { [key: string]: string } = {};
  arrayItems.forEach((item) => {
    if (item.fileName.trim()) {
      result[item.fileName] = item.content;
    }
  });
  return Object.keys(result).length > 0 ? result : {};
};

const shouldUseTextarea = (field: any): boolean => {
  return (
    field.max_length > 255 ||
    field.name.toLowerCase().includes('description') ||
    field.name.toLowerCase().includes('content') ||
    field.name.toLowerCase().includes('prompt') ||
    field.name.toLowerCase().includes('doc') ||
    field.name.toLowerCase().includes('guide')
  );
};

export default function FieldRenderer({
  field,
  value,
  mode,
  onChange,
  itemData,
}: FieldRendererProps) {
  const fieldConfig = getFieldConfig(field);
  const shouldUseArray = shouldUseArrayFormat(field.name);
  const arrayValue = normalizeArrayValue(value, fieldConfig.defaultFileName);

  const shouldUseMonaco = fieldConfig.editorType === 'monaco';
  const isNameField = field.name.toLowerCase() === 'name';
  const isReadOnly = mode === 'edit' && (isNameField || !!field.readOnly);
  const shouldUseTextareaField = shouldUseTextarea(field);

  // Matches "laui", "_laui", "lauis", or "_lauis" at the end of the string
  const isLauiField = /_?lauis?$/i.test(field.name);

  // Check if field type is object
  const isObjectField = field.datatype === 'object' || field.type === 'object';

  // Chip-array: datatype array with string items, not a code-block field
  const isChipArrayField =
    (field.datatype === 'array' || field.type === 'array') &&
    (!field.items || field.items === 'string') &&
    !shouldUseArray;

  const handleConvertToExternalFormat = (arrayItems: ArrayItem[]) => {
    return convertToExternalFormat(arrayItems, shouldUseArray);
  };

  // For object/any fields in edit mode, serialize to JSON string
  const getEditValue = () => {
    if (typeof value === 'object' && value !== null) {
      return JSON.stringify(value, null, 2);
    }
    return value;
  };

  // For object/any fields, parse JSON string back to object when saving
  const handleObjectChange = (fieldName: string, newValue: any) => {
    if ((isObjectField || field.datatype === 'any') && typeof newValue === 'string') {
      try {
        const parsed = JSON.parse(newValue);
        onChange(fieldName, parsed);
      } catch {
        // If JSON is invalid, store as string
        onChange(fieldName, newValue);
      }
    } else {
      onChange(fieldName, newValue);
    }
  };

  // Validation results — view mode shows a status list, not a JSON editor.
  // Edit/create keep the JSON editor (admins can edit the raw value).
  if (mode === 'view' && field.name === 'validation_results') {
    return <ValidationResultsView value={value} />;
  }

  // Fancy JSON editor (view + edit/create) — intercept before generic view mode
  const isFancyJsonField =
    shouldUseMonaco &&
    fieldConfig.editorMonacoFormat === 'json' &&
    (field.datatype === 'any' || field.datatype === 'object');

  if (isFancyJsonField) {
    return (
      <FancyJsonEditor
        field={field}
        value={getEditValue()}
        onChange={handleObjectChange}
        isReadOnly={isReadOnly}
        mode={mode}
      />
    );
  }

  if (isChipArrayField) {
    return (
      <ChipArrayField
        fieldName={field.name}
        value={value}
        onChange={onChange}
        readOnly={mode === 'view' || isReadOnly}
        placeholder={fieldConfig.placeholder}
      />
    );
  }

  // View mode
  if (mode === 'view') {
    return (
      <ViewModeRenderer
        field={field}
        value={value}
        arrayValue={arrayValue}
        shouldUseArrayFormat={shouldUseArray}
        shouldUseMonaco={shouldUseMonaco}
        shouldUseTextarea={shouldUseTextareaField}
        itemData={itemData}
      />
    );
  }

  // Edit/Create mode — boolean toggle boxes
  if (field.datatype === 'boolean') {
    const isTrue = value === true || value === 'true';
    const isFalse = value === false || value === 'false';
    const btnBase = {
      px: 3,
      py: 0.75,
      border: '1px solid var(--border)',
      cursor: 'pointer',
      fontSize: '0.875rem',
      fontWeight: 500,
      transition: 'background 0.15s, color 0.15s',
    };
    return (
      <Box sx={{ display: 'flex' }}>
        <Box
          component="button"
          onClick={() => onChange(field.name, isTrue ? null : true)}
          sx={{
            ...btnBase,
            borderRadius: '4px 0 0 4px',
            bgcolor: isTrue ? '#2e7d32' : 'transparent',
            color: isTrue ? '#fff' : 'var(--text-secondary)',
            borderColor: isTrue ? '#2e7d32' : 'var(--border)',
            '&:hover': { bgcolor: isTrue ? '#1b5e20' : 'var(--bg-tertiary)' },
          }}
        >
          True
        </Box>
        <Box
          component="button"
          onClick={() => onChange(field.name, isFalse ? null : false)}
          sx={{
            ...btnBase,
            borderRadius: '0 4px 4px 0',
            borderLeft: 'none',
            bgcolor: isFalse ? '#2e7d32' : 'transparent',
            color: isFalse ? '#fff' : 'var(--text-secondary)',
            borderColor: isFalse ? '#2e7d32' : 'var(--border)',
            '&:hover': { bgcolor: isFalse ? '#1b5e20' : 'var(--bg-tertiary)' },
          }}
        >
          False
        </Box>
      </Box>
    );
  }

  // Edit/Create mode — enum dropdown
  if (field.datatype === 'enum' && Array.isArray(field.enum_values)) {
    return (
      <FormControl fullWidth size="small">
        <Select
          value={value || ''}
          displayEmpty
          onChange={(e) => onChange(field.name, e.target.value)}
          sx={{
            bgcolor: 'var(--bg-tertiary)',
            color: 'var(--text-primary)',
            '& .MuiSelect-select': { color: 'var(--text-primary)' },
            '& .MuiOutlinedInput-notchedOutline': { borderColor: 'var(--border)' },
            '&:hover .MuiOutlinedInput-notchedOutline': {
              borderColor: 'var(--accent)',
            },
            '& .MuiSvgIcon-root': { color: 'var(--text-secondary)' },
          }}
          renderValue={(selected) =>
            selected ? (
              String(selected)
            ) : (
              <span style={{ color: 'var(--text-secondary)' }}>{field.name}</span>
            )
          }
          MenuProps={{
            PaperProps: {
              sx: {
                bgcolor: 'var(--bg-secondary)',
                color: 'var(--text-primary)',
                '& .MuiMenuItem-root': {
                  color: 'var(--text-primary)',
                  '&:hover': { bgcolor: 'var(--bg-tertiary)' },
                  '&.Mui-selected': { bgcolor: 'var(--bg-tertiary)' },
                },
              },
            },
          }}
        >
          {field.enum_values.map((opt: string) => (
            <MenuItem key={opt} value={opt}>
              {opt}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    );
  }

  // Edit/Create mode
  if (shouldUseArray) {
    return (
      <ArrayField
        field={field}
        arrayValue={arrayValue}
        fieldConfig={fieldConfig}
        onChange={onChange}
        convertToExternalFormat={handleConvertToExternalFormat}
      />
    );
  }

  if (shouldUseMonaco) {
    return (
      <MonacoField
        field={field}
        value={getEditValue()}
        onChange={handleObjectChange}
        isReadOnly={isReadOnly}
        mode={mode}
      />
    );
  }

  if (shouldUseTextareaField || isObjectField) {
    const isDescriptionLike = field.name.toLowerCase().includes('description');
    return (
      <TextAreaField
        field={field}
        value={isObjectField ? getEditValue() : value}
        onChange={handleObjectChange}
        isReadOnly={isReadOnly}
        placeholder={fieldConfig.placeholder}
        minRows={isObjectField ? 10 : isDescriptionLike ? 6 : fieldConfig.textAreaRows.min}
        maxRows={isObjectField ? 30 : isDescriptionLike ? 20 : fieldConfig.textAreaRows.max}
      />
    );
  }

  // Render dropdown for all laui fields in create mode
  if (mode === 'create' && isLauiField) {
    return <LauiDropdown fieldName={field.name} value={value || ''} onChange={onChange} />;
  }

  return (
    <SimpleTextField
      field={field}
      value={value}
      mode={mode}
      onChange={onChange}
      isReadOnly={isReadOnly}
      placeholder={fieldConfig.placeholder}
    />
  );
}

// ---------------------------------------------------------------------------
// TabFields — renders all fields for a single tab panel
// ---------------------------------------------------------------------------

interface TabFieldsProps {
  fields: any[];
  formData: Record<string, any>;
  mode: 'view' | 'edit' | 'create';
  renderField: (field: any) => React.ReactNode;
  /** Rendered above the fields list (e.g. validation panel) — edit/create only */
  headerContent?: React.ReactNode;
}

const tabFieldLabelStyle = {
  fontWeight: FONT_WEIGHTS.WEIGHT_600,
  fontSize: FONT_SIZES.BASE,
  color: 'var(--text-primary)',
};

/**
 * Renders the fields for a single tab panel.
 *
 * View mode  — if a `name` field is present it is elevated as a heading;
 *              remaining fields are shown with clean labels.
 * Edit/create — form mode: required indicators, optional headerContent above
 *              the field list (e.g. a validation panel).
 */
const toLabel = (name: string) => name.replace(/_/g, ' ').replace(/\b\w/g, (l) => l.toUpperCase());

export function TabFields({ fields, formData, mode, renderField, headerContent }: TabFieldsProps) {
  if (fields.length === 0) {
    return (
      <Typography
        sx={{
          color: 'var(--text-secondary)',
          fontSize: FONT_SIZES.BASE,
          fontStyle: 'italic',
        }}
      >
        No fields in this section
      </Typography>
    );
  }

  // ── View mode ────────────────────────────────────────────────────────────
  if (mode === 'view') {
    const nameField = fields.find((f: any) => f.name === 'name');
    const displayFields = nameField ? fields.filter((f: any) => f.name !== 'name') : fields;
    const nameValue: string = nameField ? (formData['name'] ?? '') : '';

    // Markdown fields whose content already starts with a heading own their own title
    const contentStartsWithHeading = (fieldName: string) =>
      typeof formData[fieldName] === 'string' && /^\s*#/.test(formData[fieldName].trim());

    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0 }}>
        {nameValue && (
          <Typography
            sx={{
              color: 'var(--text-primary)',
              fontWeight: 600,
              fontSize: '1.625rem',
              lineHeight: 1.3,
              mb: 1.5,
            }}
          >
            {nameValue}
          </Typography>
        )}
        {displayFields.map((field: any, idx: number) => {
          const isMarkdown = field.viewerType === 'markdown';
          const hasOwnHeading = isMarkdown && contentStartsWithHeading(field.name);

          return (
            <Box key={field.name} sx={{ mb: isMarkdown ? 0 : 1 }}>
              {displayFields.length > 1 &&
                !hasOwnHeading &&
                (isMarkdown ? (
                  <Typography
                    sx={{
                      fontSize: '1.03rem',
                      fontWeight: 600,
                      color: 'var(--text-primary)',
                      mt: idx === 0 ? 0 : 1.5,
                      mb: 0.5,
                      pb: 0.5,
                      borderBottom: '1px solid var(--border)',
                    }}
                  >
                    {toLabel(field.ui_display_name ?? field.name)}
                  </Typography>
                ) : (
                  <Typography
                    sx={{
                      fontSize: FONT_SIZES.XS,
                      fontWeight: FONT_WEIGHTS.WEIGHT_600,
                      color: 'var(--text-secondary)',
                      mb: 0.5,
                      textTransform: 'uppercase',
                      letterSpacing: '0.04em',
                    }}
                  >
                    {toLabel(field.ui_display_name ?? field.name)}
                  </Typography>
                ))}
              {renderField(field)}
            </Box>
          );
        })}
      </Box>
    );
  }

  // ── Edit / Create mode ───────────────────────────────────────────────────
  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
      {headerContent}
      {fields.map((field: any) => (
        <Box key={field.name} sx={{ mb: 0.5 }}>
          {fields.length > 1 && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.5, mb: 0.25 }}>
              <Typography variant="subtitle1" sx={{ ...tabFieldLabelStyle, mb: 0 }}>
                {toLabel(field.ui_display_name ?? field.name)}
                {field.required && (
                  <Box component="span" sx={{ color: 'var(--error)', ml: 0.5 }}>
                    *
                  </Box>
                )}
              </Typography>
              {field.tooltip && (
                <Tooltip
                  title={
                    <Box
                      sx={{
                        whiteSpace: 'pre-line',
                        fontSize: '12px',
                        lineHeight: 1.6,
                      }}
                    >
                      {field.tooltip}
                    </Box>
                  }
                  placement="right"
                  arrow
                >
                  <InfoIcon
                    sx={{
                      fontSize: 14,
                      color: 'var(--text-secondary)',
                      cursor: 'help',
                      flexShrink: 0,
                    }}
                  />
                </Tooltip>
              )}
            </Box>
          )}
          {fields.length === 1 && field.required && (
            <Typography variant="subtitle1" sx={{ ...tabFieldLabelStyle, mb: 0.25 }}>
              <Box component="span" sx={{ color: 'var(--error)', mr: 0.5 }}>
                *
              </Box>
              Required
            </Typography>
          )}
          {field.description && (
            <Typography
              sx={{
                fontSize: FONT_SIZES.XS,
                color: 'var(--text-secondary)',
                mb: 0.75,
              }}
            >
              {field.description}
              {field.max_length ? ` (max ${field.max_length} chars)` : ''}
            </Typography>
          )}
          {renderField(field)}
        </Box>
      ))}
    </Box>
  );
}
