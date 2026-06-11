/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { SelectProps } from '@mui/material';
import { FormControl, FormHelperText, InputLabel, MenuItem, Select } from '@mui/material';

interface StyledSelectProps extends Omit<SelectProps, 'label'> {
  label: string;
  options: Array<{ value: string; label: string }>;
  helperText?: string;
  loading?: boolean;
  loadingText?: string;
  error?: boolean;
}

const styles = {
  formControl: {
    mb: 3,
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
      '&.Mui-disabled': {
        backgroundColor: 'var(--bg-tertiary)',
      },
    },
    '& .MuiInputLabel-root': {
      color: 'var(--text-secondary)',
      fontSize: '12px',
      '&.Mui-focused': {
        color: 'var(--primary-main)',
      },
    },
    '& .MuiSelect-select': {
      color: 'var(--text-primary)',
    },
  },
  helperText: {
    fontSize: '11px',
    marginLeft: 0,
    '&.Mui-error': {
      color: 'var(--error)',
    },
  },
  menuItem: {
    fontSize: '12px',
  },
};

export default function StyledSelect({
  label,
  options,
  helperText,
  loading = false,
  loadingText = 'Loading...',
  error = false,
  ...props
}: StyledSelectProps) {
  return (
    <FormControl fullWidth size="small" sx={styles.formControl} error={error}>
      <InputLabel>{loading ? loadingText : label}</InputLabel>
      <Select label={loading ? loadingText : label} {...props}>
        {loading ? (
          <MenuItem value="" disabled>
            {loadingText}
          </MenuItem>
        ) : options.length === 0 ? (
          <MenuItem value="" disabled>
            No options available
          </MenuItem>
        ) : (
          options.map((option) => (
            <MenuItem key={option.value} value={option.value} sx={styles.menuItem}>
              {option.label}
            </MenuItem>
          ))
        )}
      </Select>
      {helperText && <FormHelperText sx={styles.helperText}>{helperText}</FormHelperText>}
    </FormControl>
  );
}
