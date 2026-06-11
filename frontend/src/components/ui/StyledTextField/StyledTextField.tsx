/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { forwardRef } from 'react';

import type { TextFieldProps } from '@mui/material';
import { TextField } from '@mui/material';

const styles = {
  root: {
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
    '& .MuiInputBase-input': {
      color: 'var(--text-primary)',
      WebkitTextFillColor: 'var(--text-primary)',
    },
    '& .MuiInputBase-input.Mui-disabled': {
      WebkitTextFillColor: 'var(--text-primary)',
      opacity: 0.6,
    },
    '& .MuiInputLabel-root': {
      color: 'var(--text-secondary)',
      fontSize: '12px',
      '&.Mui-focused': {
        color: 'var(--primary-main)',
      },
    },
    '& .MuiFormHelperText-root': {
      fontSize: '11px',
      marginLeft: 0,
      '&.Mui-error': {
        color: 'var(--error)',
      },
    },
  },
};

const StyledTextField = forwardRef<HTMLDivElement, TextFieldProps>(({ sx, ...props }, ref) => {
  return (
    <TextField
      ref={ref}
      variant="outlined"
      size="small"
      fullWidth
      sx={[styles.root, ...(Array.isArray(sx) ? sx : [sx])]}
      {...props}
    />
  );
});

StyledTextField.displayName = 'StyledTextField';
export default StyledTextField;
