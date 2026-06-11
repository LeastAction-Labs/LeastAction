/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import { Alert, Box, Button, CircularProgress, Typography } from '@mui/material';

import BaseModal from '@/components/ui/Modal/BaseModal';
import { FONT_SIZES } from '@/constants';
import { useCatalog } from '@/contexts/CatalogContext';
import { useEditorHandlers } from '@/screens/Browse/handlers/editorHandlers';
import { searchCatalogItems } from '@/services/catalog.service';

import type { FormMode } from '../types';

export interface SaveConfirmModalData {
  isOpen: boolean;
  mode?: FormMode;
  itemType?: string;
  itemName?: string;
  saveData?: any;
}

export const SaveConfirmModal = () => {
  const { saveConfirmModalState, setSaveConfirmModalState } = useCatalog();
  const { isOpen, itemName, itemType, mode, saveData } = saveConfirmModalState;
  const { handleSaveItem } = useEditorHandlers();
  const [isSaving, setIsSaving] = useState(false);
  const [duplicateItem, setDuplicateItem] = useState<any>(null);
  const [isCheckingDuplicate, setIsCheckingDuplicate] = useState(false);

  useEffect(() => {
    if (isOpen && mode === 'create' && saveData?.name && itemType) {
      setDuplicateItem(null);
      setIsCheckingDuplicate(true);
      const scalarFields = Object.fromEntries(
        Object.entries(saveData).filter(([, v]) => v === null || typeof v === 'string'),
      );
      searchCatalogItems(itemType, false, { filters: { ...scalarFields, get_by_pk: true } })
        .then((response) => {
          const items = response?.items || [];
          setDuplicateItem(items[0] || null);
        })
        .catch(() => setDuplicateItem(null))
        .finally(() => setIsCheckingDuplicate(false));
    } else {
      setDuplicateItem(null);
    }
  }, [isOpen, mode, saveData?.name, itemType]);

  if (!itemName || !itemType || !mode || !saveData) return;

  const handleClose = () => {
    if (!isSaving) {
      setSaveConfirmModalState({ isOpen: false });
      setDuplicateItem(null);
    }
  };

  const handleSaveConfirm = async () => {
    setIsSaving(true);
    try {
      await handleSaveItem(saveData, itemType);
      setSaveConfirmModalState({ isOpen: false });
    } finally {
      setIsSaving(false);
    }
  };

  const ModalActions = (
    <>
      <Button onClick={handleClose} disabled={isSaving} sx={{ fontSize: FONT_SIZES.BASE }}>
        Cancel
      </Button>
      <Button
        onClick={() => void handleSaveConfirm()}
        variant="contained"
        disabled={isSaving}
        sx={{
          bgcolor: 'var(--accent)',
          color: 'white',
          fontSize: FONT_SIZES.BASE,
          minWidth: 80,
        }}
      >
        {isSaving ? (
          <CircularProgress size={16} color="inherit" />
        ) : mode === 'create' && duplicateItem ? (
          'Update'
        ) : mode === 'create' ? (
          'Create'
        ) : (
          'Save'
        )}
      </Button>
    </>
  );

  const getDuplicateSummary = (item: any): string => {
    const parts: string[] = [];
    if (item.description) parts.push(`description: "${item.description}"`);
    if (item.item_type) parts.push(`type: ${item.item_type}`);
    if (item.laui) parts.push(`id: ${item.laui}`);
    return parts.length > 0 ? parts.join(', ') : 'no additional details available';
  };

  return (
    <BaseModal
      open={isOpen}
      actions={ModalActions}
      title={mode === 'create' ? `Create ${itemType}` : `Save ${itemType}`}
      onClose={handleClose}
    >
      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
        {mode === 'create' && isCheckingDuplicate && (
          <Typography
            sx={{
              fontSize: FONT_SIZES.BASE,
              color: 'var(--text-secondary)',
              fontStyle: 'italic',
            }}
          >
            Checking for existing items...
          </Typography>
        )}
        {mode === 'create' && duplicateItem && !isCheckingDuplicate && (
          <Alert severity="warning" sx={{ fontSize: FONT_SIZES.BASE }}>
            An item named <strong>"{duplicateItem.name}"</strong> already exists with{' '}
            {getDuplicateSummary(duplicateItem)}. This will{' '}
            <strong>update the existing item</strong>, not create a new one.
          </Alert>
        )}
        <Typography sx={{ fontSize: FONT_SIZES.BASE }}>
          {mode === 'create' && duplicateItem
            ? `Are you sure you want to update "${itemName}"?`
            : `Are you sure you want to ${mode === 'create' ? 'create' : 'save'} "${itemName}"?`}
        </Typography>
      </Box>
    </BaseModal>
  );
};
