/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { ReactNode } from 'react';

import CloseIcon from '@mui/icons-material/Close';
import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  Typography,
} from '@mui/material';

export interface BaseModalProps {
  open: boolean;
  onClose: () => void;
  title: string;
  subtitle?: string;
  children: ReactNode;
  actions?: ReactNode;
  loading?: boolean;
  loadingText?: string;
  showCloseIcon?: boolean;
  maxWidth?: 'xs' | 'sm' | 'md' | 'lg' | 'xl';
  fullWidth?: boolean;
}

const styles = {
  dialog: {
    '& .MuiDialog-paper': {
      backgroundColor: 'var(--bg-tertiary)',
      color: 'var(--text-primary)',
      borderRadius: 'var(--radius-md)',
    },
  },
  titleContainer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    bgcolor: 'var(--bg-secondary)',
    py: 2,
    px: 3,
    borderBottom: '1px solid var(--border)',
  },
  title: {
    fontSize: '14px',
    fontWeight: 600,
    color: 'var(--text-primary)',
  },
  subtitle: {
    fontSize: '11px',
    color: 'var(--text-secondary)',
    mt: 0.5,
  },
  closeButton: {
    minWidth: 'auto',
    color: 'var(--text-secondary)',
    '&:hover': {
      color: 'var(--text-primary)',
      backgroundColor: 'transparent',
    },
  },
  content: {
    py: 3,
    px: 3,
  },
  actions: {
    px: 3,
    pb: 3,
    gap: 1,
    borderTop: '1px solid var(--border)',
    pt: 2,
  },
  cancelButton: {
    color: 'var(--text-secondary)',
    borderColor: 'var(--border)',
    '&:hover': {
      borderColor: 'var(--primary-main)',
      color: 'var(--text-primary)',
    },
  },
  primaryButton: {
    bgcolor: 'var(--text-primary)',
    color: 'var(--bg-secondary)',
    textTransform: 'none' as const,
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
  },
  loadingContainer: {
    display: 'flex',
    justifyContent: 'center',
    alignItems: 'center',
    py: 4,
    flexDirection: 'column' as const,
    gap: 2,
  },
  loadingText: {
    fontSize: '12px',
    color: 'var(--text-secondary)',
  },
};

export default function BaseModal({
  open,
  onClose,
  title,
  subtitle,
  children,
  actions,
  loading = false,
  loadingText = 'Loading...',
  showCloseIcon = true,
  maxWidth = 'sm',
  fullWidth = true,
}: BaseModalProps) {
  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth={maxWidth}
      fullWidth={fullWidth}
      sx={styles.dialog}
    >
      <DialogTitle sx={{ p: 0 }}>
        <Box sx={styles.titleContainer}>
          <Box>
            <Typography sx={styles.title}>{title}</Typography>
            {subtitle && <Typography sx={styles.subtitle}>{subtitle}</Typography>}
          </Box>
          {showCloseIcon && (
            <Button onClick={onClose} disabled={loading} sx={styles.closeButton} size="small">
              <CloseIcon fontSize="small" />
            </Button>
          )}
        </Box>
      </DialogTitle>

      <DialogContent sx={styles.content}>
        {loading ? (
          <Box sx={styles.loadingContainer}>
            <CircularProgress size={32} sx={{ color: 'var(--primary-main)' }} />
            <Typography sx={styles.loadingText}>{loadingText}</Typography>
          </Box>
        ) : (
          children
        )}
      </DialogContent>

      {actions && <DialogActions sx={styles.actions}>{actions}</DialogActions>}
    </Dialog>
  );
}
