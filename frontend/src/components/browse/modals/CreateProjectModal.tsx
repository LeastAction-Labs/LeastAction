/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import AddIcon from '@mui/icons-material/Add';
import {
  Box,
  Button,
  CircularProgress,
  FormControlLabel,
  Switch,
  TextField,
  Typography,
} from '@mui/material';

import BaseModal from '@/components/ui/Modal/BaseModal';
import { useCatalog } from '@/contexts/CatalogContext';
import { useGlobal } from '@/contexts/GlobalContext';
import { useNotification } from '@/contexts/NotificationContext';
import { bootstrapProject, createCatalogItem } from '@/services/catalog.service';
import { getChildCatalogNodes, getRootCatalogNodes } from '@/services/catalog.service';

interface CreateProjectModalProps {
  open: boolean;
  onClose: () => void;
  onSuccess?: (projectLaui: string) => void;
}

export default function CreateProjectModal({ open, onClose, onSuccess }: CreateProjectModalProps) {
  const { showSuccess, showError } = useNotification();
  const { accountLaui, setProjectLauis, setCurrentProjectLaui } = useGlobal();
  const { catalogState } = useCatalog();
  const { setItems, setIsLoading, setLoadedChildren, setExpandedItems } = catalogState;

  const [name, setName] = useState('');
  const [description, setDescription] = useState('');
  const [setupStructure, setSetupStructure] = useState(false);
  const [submitting, setSubmitting] = useState(false);

  const handleClose = () => {
    if (!submitting) {
      setName('');
      setDescription('');
      setSetupStructure(false);
      onClose();
    }
  };

  const handleCreate = async () => {
    if (!name.trim()) {
      showError('Project name is required');
      return;
    }
    if (!accountLaui) {
      showError('Account not loaded yet. Please try again.');
      return;
    }

    setSubmitting(true);
    try {
      // 1. Create the project folder
      const createResponse = await createCatalogItem({
        item_type: 'folder.project',
        name: name.trim(),
        description: description.trim(),
        parent_laui: accountLaui,
        account_laui: accountLaui,
      });

      const projectLaui: string = createResponse?.item_laui;
      if (!projectLaui) throw new Error('Failed to get project LAUI from response');

      // 2. Optionally bootstrap the folder structure
      if (setupStructure) {
        await bootstrapProject(projectLaui);
      }

      showSuccess(`Project "${name.trim()}" created successfully`);

      // 3. Refresh the sidebar tree
      try {
        setIsLoading(true);
        setLoadedChildren(new Set());
        setExpandedItems(new Set());
        const { items: root } = await getRootCatalogNodes(false);
        setItems(root);

        // Refresh project lauis
        if (root.length > 0 && root[0]?.item?.item_type === 'folder.account') {
          // Re-mark account folder as loaded so expandPathToItem won't overwrite
          // its children (which the root response already pre-nests fully) with a
          // paginated 10-item subset from loadChildren.
          setLoadedChildren((prev) => new Set([...prev, root[0].item.laui]));
          const { items: children } = await getChildCatalogNodes(
            root[0].item.laui,
            root[0].item.permission,
            false,
            1,
            10,
            'folder',
          );
          const projectLauis = children
            .filter((c) => c.item.item_type === 'folder.project')
            .map((c) => c.item.laui);
          setProjectLauis(projectLauis);
          setCurrentProjectLaui(projectLauis[0] ?? null);
          localStorage.setItem('la_project_lauis', JSON.stringify(projectLauis));
        }
      } catch {
        // non-critical – tree refresh failure shouldn't block the success message
      } finally {
        setIsLoading(false);
      }

      onSuccess?.(projectLaui);
      handleClose();
    } catch {
      /* ignore */
    } finally {
      setSubmitting(false);
    }
  };

  const ModalActions = (
    <>
      <Button
        onClick={handleClose}
        disabled={submitting}
        size="small"
        variant="outlined"
        sx={{
          color: 'var(--text-secondary)',
          borderColor: 'var(--border)',
          textTransform: 'none',
          '&:hover': {
            borderColor: 'var(--accent)',
            color: 'var(--text-primary)',
          },
        }}
      >
        Cancel
      </Button>
      <Button
        onClick={() => void handleCreate()}
        disabled={submitting || !name.trim()}
        size="small"
        variant="contained"
        startIcon={submitting ? <CircularProgress size={14} color="inherit" /> : <AddIcon />}
        sx={{
          bgcolor: 'var(--text-primary)',
          color: 'var(--bg-secondary)',
          textTransform: 'none',
          fontWeight: 'bold',
          '&:hover': {
            bgcolor: 'var(--bg-secondary)',
            color: 'var(--text-primary)',
          },
          '&:disabled': {
            bgcolor: 'var(--bg-tertiary)',
            color: 'var(--text-dim)',
          },
          py: 0.5,
          px: 1.5,
        }}
      >
        {submitting ? 'Creating…' : 'Create Project'}
      </Button>
    </>
  );

  return (
    <BaseModal
      open={open}
      onClose={handleClose}
      title="Create Project"
      subtitle="Add a new project to your account"
      actions={ModalActions}
      maxWidth="sm"
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5, mt: 1 }}>
        {/* Name */}
        <TextField
          label="Project Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={submitting}
          fullWidth
          size="small"
          required
          onKeyDown={(e) => {
            if (e.key === 'Enter') void handleCreate();
          }}
          InputLabelProps={{
            sx: {
              color: 'var(--text-secondary)',
              '&.Mui-focused': { color: 'var(--text-primary)' },
            },
          }}
          sx={{
            '& .MuiInputBase-root': { bgcolor: 'var(--bg-primary)' },
            '& .MuiInputBase-input': { color: 'var(--text-primary)' },
            '& .MuiOutlinedInput-notchedOutline': { borderColor: 'var(--text-dim)' },
            '& .MuiOutlinedInput-root:hover .MuiOutlinedInput-notchedOutline': {
              borderColor: 'var(--text-secondary)',
            },
            '& .MuiOutlinedInput-root.Mui-focused .MuiOutlinedInput-notchedOutline': {
              borderColor: 'var(--text-primary)',
            },
          }}
        />

        {/* Description */}
        <TextField
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          disabled={submitting}
          fullWidth
          size="small"
          multiline
          rows={3}
          InputLabelProps={{
            sx: {
              color: 'var(--text-secondary)',
              '&.Mui-focused': { color: 'var(--text-primary)' },
            },
          }}
          sx={{
            '& .MuiInputBase-root': { bgcolor: 'var(--bg-primary)' },
            '& .MuiInputBase-input': { color: 'var(--text-primary)' },
            '& .MuiOutlinedInput-notchedOutline': { borderColor: 'var(--text-dim)' },
            '& .MuiOutlinedInput-root:hover .MuiOutlinedInput-notchedOutline': {
              borderColor: 'var(--text-secondary)',
            },
            '& .MuiOutlinedInput-root.Mui-focused .MuiOutlinedInput-notchedOutline': {
              borderColor: 'var(--text-primary)',
            },
          }}
        />

        {/* Setup Structure toggle */}
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            px: 1.5,
            py: 1,
            border: '1px solid var(--text-dim)',
            borderRadius: 1,
            bgcolor: setupStructure ? 'var(--bg-depth-0)' : 'var(--bg-primary)',
            transition: 'background-color 0.15s ease',
          }}
        >
          <Box>
            <Typography
              variant="body2"
              sx={{ fontWeight: 600, color: 'var(--text-primary)', fontSize: '12px' }}
            >
              Setup Structure
            </Typography>
            <Typography variant="caption" sx={{ color: 'var(--text-secondary)', fontSize: '11px' }}>
              Auto-create standard folders: action_agents, assets, config, connection, operator,
              payload, workflow
            </Typography>
          </Box>
          <FormControlLabel
            control={
              <Switch
                checked={setupStructure}
                onChange={(e) => setSetupStructure(e.target.checked)}
                disabled={submitting}
                size="small"
                sx={{
                  '& .MuiSwitch-switchBase.Mui-checked': {
                    color: 'var(--accent)',
                  },
                  '& .MuiSwitch-switchBase.Mui-checked + .MuiSwitch-track': {
                    backgroundColor: 'var(--accent)',
                  },
                }}
              />
            }
            label=""
            sx={{ m: 0 }}
          />
        </Box>
      </Box>
    </BaseModal>
  );
}
