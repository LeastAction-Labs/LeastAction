/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import {
  Box,
  Button,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  TextField,
  Typography,
} from '@mui/material';

import UserSearch from '@/components/users/UserSearch';

interface GroupModalProps {
  open: boolean;
  onClose: () => void;
  onSave: (groupData: {
    name: string;
    description: string;
    members: string[];
    admins: string[];
  }) => Promise<void>;
  loading?: boolean;
}

const styles = {
  dialog: {
    '& .MuiDialog-paper': {
      backgroundColor: 'var(--bg-tertiary)',
      color: 'var(--text-primary)',
      minWidth: '600px',
      maxWidth: '700px',
    },
  },
  title: {
    fontSize: '12px',
    fontWeight: 600,
    bgcolor: 'var(--bg-secondary)',
    color: 'var(--text-primary)',
    py: 2,
    px: 3,
  },
  content: {
    py: 3,
    px: 3,
  },
  section: {
    mb: 3,
    '&:last-of-type': {
      mb: 0,
    },
  },
  sectionTitle: {
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    mb: 1.5,
  },
  textField: {
    mb: 0,
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
    },
    '& .MuiInputLabel-root': {
      color: 'var(--text-secondary)',
      fontSize: '12px',
    },
  },
  chipContainer: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: 1,
    minHeight: '40px',
    p: 1,
    border: '1px solid var(--border)',
    borderRadius: '4px',
    bgcolor: 'var(--bg-secondary)',
  },
  chip: {
    bgcolor: 'var(--bg-tertiary)',
    color: 'var(--text-primary)',
    fontSize: '11px',
    '& .MuiChip-deleteIcon': {
      color: 'var(--text-secondary)',
      '&:hover': {
        color: 'var(--text-primary)',
      },
    },
  },
  actions: {
    px: 3,
    pb: 3,
    gap: 1,
  },
  cancelButton: {
    color: 'var(--text-secondary)',
    borderColor: 'var(--border)',
    '&:hover': {
      borderColor: 'var(--primary-main)',
      color: 'var(--text-primary)',
    },
  },
  saveButton: {
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
  },
  errorText: {
    fontSize: '11px',
    color: 'var(--error)',
    mt: 1.5,
    display: 'block',
  },
  helperText: {
    fontSize: '11px',
    color: 'var(--text-secondary)',
    mt: 0.5,
  },
};

export default function GroupModal({ open, onClose, onSave, loading = false }: GroupModalProps) {
  const [name, setName] = useState<string>('');
  const [description, setDescription] = useState<string>('');

  // Keep arrays of objects to manage cleanly both display metadata and id tracking
  const [members, setMembers] = useState<any[]>([]);
  const [admins, setAdmins] = useState<any[]>([]);

  const [localError, setLocalError] = useState<string>('');

  // Reset core structures upon closing dialog safely
  useEffect(() => {
    if (!open) {
      setName('');
      setDescription('');
      setMembers([]);
      setAdmins([]);
      setLocalError('');
    }
  }, [open]);

  const handleRemoveMember = (id: string) => {
    setMembers(members.filter((m) => m.id !== id));
  };

  const handleRemoveAdmin = (id: string) => {
    setAdmins(admins.filter((a) => a.id !== id));
  };

  const handleSave = async () => {
    setLocalError('');

    if (!name.trim()) {
      setLocalError('Group name is required');
      return;
    }

    try {
      await onSave({
        name: name.trim(),
        description: description.trim(),
        // Format layout tracking to pass exact user ids down to platform endpoint
        members: members.map((m) => `U${m.id}`),
        admins: admins.map((a) => `U${a.id}`),
      });
    } catch (err: any) {
      const errorMessage =
        err.message || err.response?.data?.message || 'Failed to create group. Please try again.';
      setLocalError(errorMessage);
    }
  };

  const handleClose = () => {
    if (!loading) {
      onClose();
    }
  };

  return (
    <Dialog open={open} onClose={handleClose} maxWidth="sm" fullWidth sx={styles.dialog}>
      <DialogTitle sx={styles.title}>Create New Group</DialogTitle>

      <DialogContent sx={styles.content}>
        {loading ? (
          <Box sx={styles.loadingContainer}>
            <CircularProgress size={32} sx={{ color: 'var(--primary-main)' }} />
            <Typography sx={{ ml: 2, fontSize: '12px' }}>Creating group...</Typography>
          </Box>
        ) : (
          <>
            {/* Group Name */}
            <Box sx={styles.section}>
              <TextField
                fullWidth
                label="Group Name"
                value={name}
                onChange={(e) => {
                  setName(e.target.value);
                  setLocalError('');
                }}
                variant="outlined"
                size="small"
                sx={styles.textField}
                placeholder="Enter group name"
                required
                error={!!localError && !name.trim()}
              />
            </Box>

            {/* Group Description */}
            <Box sx={styles.section}>
              <TextField
                fullWidth
                label="Description"
                value={description}
                onChange={(e) => setDescription(e.target.value)}
                variant="outlined"
                size="small"
                multiline
                rows={3}
                sx={styles.textField}
                placeholder="Enter group description"
              />
            </Box>

            {/* Members Lookup engine section */}
            <Box sx={styles.section}>
              <Typography sx={styles.sectionTitle}>Members</Typography>
              <UserSearch
                existingUserIds={[]}
                queuedUsers={members}
                onQueueUser={(user) => setMembers([...members, user])}
                onRemoveQueuedUser={handleRemoveMember}
              />
            </Box>

            {/* Admins Lookup engine section */}
            <Box sx={styles.section}>
              <Typography sx={styles.sectionTitle}>Admins</Typography>
              <UserSearch
                existingUserIds={[]}
                queuedUsers={admins}
                onQueueUser={(user) => setAdmins([...admins, user])}
                onRemoveQueuedUser={handleRemoveAdmin}
              />
            </Box>

            {localError && <Typography sx={styles.errorText}>{localError}</Typography>}
          </>
        )}
      </DialogContent>

      <DialogActions sx={styles.actions}>
        <Button
          onClick={handleClose}
          size="small"
          variant="outlined"
          sx={styles.cancelButton}
          disabled={loading}
        >
          Cancel
        </Button>
        <Button
          onClick={() => void handleSave()}
          size="small"
          variant="contained"
          sx={styles.saveButton}
          disabled={!name.trim() || loading}
        >
          {loading ? 'Creating...' : 'Create Group'}
        </Button>
      </DialogActions>
    </Dialog>
  );
}
