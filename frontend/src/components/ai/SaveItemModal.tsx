/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import { Box, Button, FormControl, InputLabel, MenuItem, Select } from '@mui/material';

import { AIItemType, useAI } from '@/contexts/AIContext';
import { useGlobal } from '@/contexts/GlobalContext';
import { useNotification } from '@/contexts/NotificationContext';
import { createCatalogItem } from '@/services';
import { getOperatorSubtypes } from '@/services/system.service';
import { validateCodeblock } from '@/services/validation.service';

import BaseModal from '../ui/Modal/BaseModal';
import { QuickSearch } from '../ui/QuickSearch';
import StyledTextField from '../ui/StyledTextField/StyledTextField';

export default function SaveItemModal() {
  const { itemType, saveItemModalState, setSaveItemModalState } = useAI();
  const { isOpen, itemData } = saveItemModalState;

  const { showSuccess } = useNotification();

  const { accountLaui: accountLauiFromGlobal, projectLauis } = useGlobal();
  let accountLaui = accountLauiFromGlobal;

  if (!accountLaui) accountLaui = localStorage.getItem('la_account_laui');

  const projects =
    projectLauis.length != 0
      ? projectLauis
      : JSON.parse(localStorage.getItem('la_project_lauis') || '');

  const [name, setName] = useState<string>('');
  const [description, setDescription] = useState<string>('');
  const [selectedWorkflow, setSelectedWorkflow] = useState<string | null>(null);

  // Subtype for operator
  const [selectedSubtype, setSelectedSubtype] = useState<string>('');
  const operatorSubtypes = itemType === AIItemType.OPERATOR ? getOperatorSubtypes() : [];

  // State management
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const handleSave = async () => {
    if (!name.trim()) {
      setError('name is required');
      return;
    }
    if (!selectedWorkflow) {
      setError('Workflow is required');
      return;
    }
    if (
      itemType !== AIItemType.OPERATOR &&
      itemType !== AIItemType.PAYLOAD &&
      !accountLaui &&
      projects.length === 0
    )
      return;
    setSubmitting(true);
    try {
      itemData.name = name.trim();
      itemData.description = description.trim();
      itemData.parent_laui = selectedWorkflow;
      itemData.account_laui = accountLaui || '';
      itemData.project_laui = projects[0] || '';
      itemData.item_type =
        itemType === AIItemType.OPERATOR && selectedSubtype
          ? `${itemType}.${selectedSubtype}`
          : itemType;
      // Pre-save codeblock validation for operators and actions
      const base = (itemData.item_type || '').split('.')[0];
      if ((base === 'operator' || base === 'action') && itemData.codeblock) {
        const result = await validateCodeblock(itemData.codeblock, itemData.item_type);
        if (!result.valid) {
          setSubmitting(false);
          return;
        }
      }
      await createCatalogItem(itemData);
      showSuccess('Item saved');
      setSubmitting(false);
      handleClose();
    } catch {
      setSubmitting(false);
    }
  };

  const handleClose = () => {
    if (!submitting) {
      setError(null);
      setName('');
      setDescription('');
      setSelectedWorkflow(null);
      setSelectedSubtype('');
      setSaveItemModalState({ isOpen: false });
    }
  };

  const loading = submitting;

  const ModalActions = (
    <>
      <Button
        onClick={handleClose}
        disabled={loading}
        size="small"
        variant="outlined"
        sx={{
          color: 'var(--text-secondary)',
          borderColor: 'var(--border)',
          '&:hover': {
            borderColor: 'var(--primary-main)',
            color: 'var(--text-primary)',
          },
        }}
      >
        Cancel
      </Button>
      <Button
        onClick={() => void handleSave()}
        disabled={loading}
        size="small"
        variant="contained"
        sx={{
          bgcolor: 'var(--text-primary)',
          color: 'var(--bg-secondary)',
          textTransform: 'none',
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
        }}
      >
        {submitting ? 'Saving...' : `Save ${itemType}`}
      </Button>
    </>
  );

  return (
    <BaseModal
      open={isOpen}
      onClose={handleClose}
      title={'Save ' + itemType.toUpperCase()}
      actions={ModalActions}
      loadingText={submitting ? 'Running action...' : 'Loading data...'}
    >
      <Box sx={{ marginTop: '20px' }}>
        <StyledTextField
          label="Name"
          value={name}
          onChange={(e) => setName(e.target.value)}
          disabled={loading}
          placeholder="Enter action name"
          required
          error={!!error && !name.trim()}
        />

        <StyledTextField
          label="Description"
          value={description}
          onChange={(e) => setDescription(e.target.value)}
          disabled={loading}
          placeholder="Optional description"
          multiline
          rows={2}
        />
        {itemType === AIItemType.OPERATOR && operatorSubtypes.length > 0 && (
          <FormControl fullWidth size="small" sx={{ mb: 2 }}>
            <InputLabel id="subtype-select-label">Subtype</InputLabel>
            <Select
              labelId="subtype-select-label"
              value={selectedSubtype}
              label="Subtype"
              onChange={(e) => setSelectedSubtype(e.target.value)}
              disabled={loading}
            >
              <MenuItem value="">
                <em>Select subtype</em>
              </MenuItem>
              {operatorSubtypes.map((st) => (
                <MenuItem key={st} value={st}>
                  {st}
                </MenuItem>
              ))}
            </Select>
          </FormControl>
        )}
        <Box sx={{ mb: 2 }}>
          <QuickSearch
            label="Save to"
            placeholder="Search workflow or folder..."
            value={selectedWorkflow}
            onSelect={(item: any) => {
              const laui = item._laui || item.laui || item.id;
              setSelectedWorkflow(laui);
            }}
            disabled={loading}
          />
        </Box>
      </Box>
    </BaseModal>
  );
}
