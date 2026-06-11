/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Box, TextField } from '@mui/material';

import type { FieldRendererProps } from '@/components/browse/FieldRenderer/types';

interface TextAreaFieldProps extends Pick<FieldRendererProps, 'field' | 'value' | 'onChange'> {
  isReadOnly?: boolean;
  placeholder?: string;
  minRows?: number;
  maxRows?: number;
}

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: 1,
  },
  textField: {
    '& .MuiOutlinedInput-root': {
      backgroundColor: 'var(--bg-tertiary)',
      color: 'var(--text-primary)',
      fontSize: '12px',
    },
  },
  readOnlyField: {
    '& .MuiOutlinedInput-root': {
      backgroundColor: 'var(--bg-secondary)',
      color: 'var(--text-primary)',
      fontSize: '12px',
    },
  },
  charCount: {
    fontSize: '11px',
    color: 'var(--text-secondary)',
  },
};

export const TextAreaField = ({
  field,
  value,
  onChange,
  isReadOnly,
  placeholder,
  minRows = 4,
  maxRows = 8,
}: TextAreaFieldProps) => {
  return (
    <Box sx={styles.container}>
      <TextField
        value={value || ''}
        onChange={(e) => onChange(field.name, e.target.value)}
        inputProps={{
          readOnly: isReadOnly,
          maxLength: field.max_length,
        }}
        multiline
        minRows={minRows}
        maxRows={maxRows}
        fullWidth
        variant="outlined"
        size="small"
        sx={isReadOnly ? styles.readOnlyField : styles.textField}
        placeholder={placeholder || `Enter ${field.name}...`}
      />
      {field.max_length && (
        <Box sx={styles.charCount}>
          {(value || '').length}/{field.max_length} characters
        </Box>
      )}
    </Box>
  );
};
