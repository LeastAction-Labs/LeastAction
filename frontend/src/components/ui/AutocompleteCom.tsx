/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// AutocompleteCom/AutocompleteCom.tsx
import React from 'react';

import {
  AccountTree as AccountTreeIcon,
  Api as ApiIcon,
  Cloud as CloudIcon,
  CloudQueue as CloudQueueIcon,
  Code as CodeIcon,
  Dataset as DatabaseIcon,
  Hub as HubIcon,
  Link as LinkIcon,
  Settings as SettingsIcon,
  Storage as StorageIcon,
  Terminal as TerminalIcon,
} from '@mui/icons-material';
import type { AutocompleteProps } from '@mui/material';
import {
  Autocomplete,
  Box,
  CircularProgress,
  InputAdornment,
  TextField,
  Typography,
} from '@mui/material';

import { BORDER_RADIUS, OPACITY } from '@/constants';

interface SelectOption {
  value: string;
  label: string;
  disabled?: boolean;
  icon?: string; // Optional icon name for individual options
}

interface AutocompleteComProps extends Omit<
  AutocompleteProps<SelectOption, false, false, false>,
  'renderInput' | 'onChange' | 'options' | 'value'
> {
  label: string;
  value: string;
  options: SelectOption[];
  onChange: (value: string) => void;
  loading?: boolean;
  loadingText?: string;
  helperText?: string;
  error?: boolean;
  errorText?: string;
  fullWidth?: boolean;
  disabled?: boolean;
  required?: boolean;
  placeholder?: string;
  fieldType?: string; // To determine which icon to show based on field name
  sx?: any; // Added sx prop for custom styling
}

// Icon mapping based on field type/label
const getFieldIcon = (fieldType?: string) => {
  if (!fieldType) return CloudIcon;

  const fieldTypeLower = fieldType.toLowerCase();

  if (
    fieldTypeLower.includes('provider') ||
    fieldTypeLower.includes('ai') ||
    fieldTypeLower.includes('model')
  ) {
    return CloudIcon;
  } else if (
    fieldTypeLower.includes('connection') ||
    fieldTypeLower.includes('endpoint') ||
    fieldTypeLower.includes('api')
  ) {
    return LinkIcon;
  } else if (
    fieldTypeLower.includes('storage') ||
    fieldTypeLower.includes('database') ||
    fieldTypeLower.includes('db')
  ) {
    return DatabaseIcon;
  } else if (fieldTypeLower.includes('service') || fieldTypeLower.includes('microservice')) {
    return ApiIcon;
  } else if (fieldTypeLower.includes('action') || fieldTypeLower.includes('function')) {
    return TerminalIcon;
  } else if (fieldTypeLower.includes('operator') || fieldTypeLower.includes('processor')) {
    return SettingsIcon;
  } else if (fieldTypeLower.includes('payload') || fieldTypeLower.includes('data')) {
    return CodeIcon;
  } else if (fieldTypeLower.includes('workflow') || fieldTypeLower.includes('pipeline')) {
    return AccountTreeIcon;
  } else if (fieldTypeLower.includes('integration') || fieldTypeLower.includes('hub')) {
    return HubIcon;
  } else if (
    fieldTypeLower.includes('cloud') ||
    fieldTypeLower.includes('aws') ||
    fieldTypeLower.includes('azure') ||
    fieldTypeLower.includes('gcp')
  ) {
    return CloudQueueIcon;
  }

  return CloudIcon; // Default icon
};

// Icon mapping for option icons
const getOptionIcon = (iconName?: string) => {
  if (!iconName) return null;

  const iconMap: Record<string, React.ComponentType> = {
    cloud: CloudIcon,
    settings: SettingsIcon,
    link: LinkIcon,
    api: ApiIcon,
    storage: StorageIcon,
    database: DatabaseIcon,
    terminal: TerminalIcon,
    code: CodeIcon,
    workflow: AccountTreeIcon,
    hub: HubIcon,
    cloudqueue: CloudQueueIcon,
  };

  return iconMap[iconName.toLowerCase()] || null;
};

const AutocompleteCom: React.FC<AutocompleteComProps> = ({
  label,
  value,
  options,
  onChange,
  loading = false,
  loadingText = 'Loading...',
  helperText,
  error = false,
  errorText,
  fullWidth = true,
  disabled = false,
  required = false,
  placeholder,
  fieldType,
  sx = {},
  ...autocompleteProps
}) => {
  // Find the current option based on value
  const currentOption = options.find((option) => option.value === value) || null;

  // Get icon based on field type
  const FieldIcon = getFieldIcon(fieldType || label);

  const handleChange = (_: any, newValue: SelectOption | null) => {
    if (newValue) {
      onChange(newValue.value);
    } else {
      onChange('');
    }
  };

  return (
    <Box sx={{ width: fullWidth ? '100%' : 'auto', ...sx }}>
      <Autocomplete
        value={currentOption}
        onChange={handleChange}
        options={options}
        getOptionLabel={(option) => option.label}
        isOptionEqualToValue={(option, val) => (val == null ? false : option.value === val.value)}
        disabled={disabled || loading}
        loading={loading}
        disableClearable={false}
        size="small" // Added size="small" to match other fields
        slotProps={{
          popper: {
            sx: { zIndex: 1400 },
          },
        }}
        renderInput={(params) => (
          <TextField
            {...params}
            label={label}
            required={required}
            error={error}
            placeholder={placeholder}
            size="small" // Added size="small" to match other fields
            InputProps={{
              ...params.InputProps,
              startAdornment: (
                <>
                  <InputAdornment position="start" sx={{ mr: 1 }}>
                    <FieldIcon
                      sx={{
                        color: error ? 'var(--error)' : 'var(--text-secondary)',
                        fontSize: 18, // Smaller icon
                      }}
                    />
                  </InputAdornment>
                  {params.InputProps.startAdornment}
                </>
              ),
              endAdornment: params.InputProps.endAdornment,
            }}
            sx={{
              '& .MuiOutlinedInput-root': {
                backgroundColor: 'var(--bg-secondary)',
                borderRadius: BORDER_RADIUS.MD,
                paddingLeft: '8px', // Reduced padding for smaller height
                '& fieldset': {
                  borderColor: error ? 'var(--error)' : 'var(--border-color)',
                },
                '&:hover fieldset': {
                  borderColor: error ? 'var(--error)' : 'var(--accent)',
                },
                '&.Mui-focused fieldset': {
                  borderColor: error ? 'var(--error)' : 'var(--accent)',
                  borderWidth: error ? '1px' : '2px',
                },
                '&.Mui-disabled': {
                  opacity: OPACITY.DISABLED,
                  '& fieldset': {
                    borderColor: 'var(--border-color)',
                  },
                },
              },
              '& .MuiInputLabel-root': {
                color: 'var(--text-secondary)',
                fontSize: '12px', // Smaller font size to match other fields
                '&.Mui-focused': {
                  color: error ? 'var(--error)' : 'var(--accent)',
                },
                '&.Mui-error': {
                  color: 'var(--error)',
                },
                '&.MuiInputLabel-shrink': {
                  fontSize: '12px', // Keep same size when shrunk
                },
              },
              '& .MuiInputBase-input': {
                color: value ? 'var(--text-primary)' : 'var(--text-secondary)',
                fontSize: '12px', // Smaller font size to match other fields
                padding: '8.5px 14px 8.5px 0', // Adjust padding for smaller height
                '&::placeholder': {
                  color: 'var(--text-secondary)',
                  opacity: 0.7,
                },
              },
              '& .MuiAutocomplete-endAdornment .MuiSvgIcon-root': {
                color: error ? 'var(--error)' : 'var(--text-secondary)',
                fontSize: 18, // Smaller icon
              },
            }}
          />
        )}
        renderOption={(props, option) => {
          const OptionIcon = option.icon ? getOptionIcon(option.icon) : null;
          return (
            <li {...props} key={option.value}>
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  width: '100%',
                  py: 0.5,
                }}
              >
                {' '}
                {/* Reduced padding */}
                {OptionIcon && (
                  <Box
                    component={OptionIcon}
                    sx={{
                      mr: 1,
                      fontSize: 16,
                      color: option.disabled ? 'var(--text-secondary)' : 'var(--text-primary)',
                      opacity: option.disabled ? OPACITY.DISABLED : 1,
                    }}
                  />
                )}
                <Typography
                  sx={{
                    fontSize: '12px', // Smaller font size
                    color: option.disabled ? 'var(--text-secondary)' : 'var(--text-primary)',
                    opacity: option.disabled ? OPACITY.DISABLED : 1,
                    flex: 1,
                  }}
                >
                  {option.label}
                </Typography>
              </Box>
            </li>
          );
        }}
        PaperComponent={({ children }) => (
          <Box
            sx={{
              backgroundColor: 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              border: '1px solid var(--border-color)',
              borderRadius: BORDER_RADIUS.MD,
              mt: 0.5, // Reduced margin
              overflow: 'hidden',
              '& .MuiAutocomplete-listbox': {
                padding: 0,
                maxHeight: 250, // Reduced max height
                '& .MuiAutocomplete-option': {
                  minHeight: 'auto',
                  padding: '6px 12px', // Reduced padding
                  '&:hover': {
                    backgroundColor: 'var(--bg-selected) !important',
                  },
                  '&.Mui-focused': {
                    backgroundColor: 'var(--bg-selected)',
                  },
                  "&[aria-selected='true']": {
                    backgroundColor: 'var(--bg-selected)',
                    '&.Mui-focused': {
                      backgroundColor: 'var(--bg-selected)',
                    },
                  },
                  '&.Mui-disabled': {
                    opacity: OPACITY.DISABLED,
                  },
                },
              },
            }}
          >
            {children}
          </Box>
        )}
        {...autocompleteProps}
      />

      {/* Loading state */}
      {loading && (
        <Box sx={{ display: 'flex', alignItems: 'center', mt: 0.5 }}>
          {' '}
          {/* Reduced margin */}
          <CircularProgress
            size={14} // Smaller progress indicator
            sx={{
              color: 'var(--accent)',
              mr: 0.5, // Reduced margin
            }}
          />
          <Typography
            sx={{
              color: 'var(--text-secondary)',
              fontSize: '11px', // Smaller font
            }}
          >
            {loadingText}
          </Typography>
        </Box>
      )}

      {/* Helper text */}
      {helperText && !error && (
        <Typography
          sx={{
            color: 'var(--text-secondary)',
            fontSize: '11px', // Smaller font
            fontStyle: 'italic',
            mt: 0.5, // Reduced margin
          }}
        >
          {helperText}
        </Typography>
      )}

      {/* Error text */}
      {error && errorText && (
        <Typography
          sx={{
            color: 'var(--error)',
            fontSize: '11px', // Smaller font
            mt: 0.5, // Reduced margin
          }}
        >
          {errorText}
        </Typography>
      )}
    </Box>
  );
};

export default AutocompleteCom;
