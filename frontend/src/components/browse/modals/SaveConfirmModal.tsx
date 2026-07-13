/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useMemo, useState } from 'react';

import {
  Alert,
  Box,
  Button,
  CircularProgress,
  FormControl,
  InputLabel,
  MenuItem,
  Select,
  Typography,
} from '@mui/material';

import BaseModal from '@/components/ui/Modal/BaseModal';
import { FONT_SIZES } from '@/constants';
import { useCatalog } from '@/contexts/CatalogContext';
import { useEditorHandlers } from '@/screens/Browse/handlers/editorHandlers';
import { searchCatalogItems } from '@/services/catalog.service';
import { nextVersionOptions } from '@/utils/semver';

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

  // ── Forced version bump when editing an already-published item ──
  // Editing a published item MUST increment its Item version (version_details.version)
  // by one step. This bump IS the increment that later gets pushed on publish.
  const currentVersion = saveData?.version_details?.version as string | undefined;
  const requiresVersionBump = mode === 'edit' && saveData?.is_published === true;
  const bumpOptions = useMemo(() => nextVersionOptions(currentVersion), [currentVersion]);
  const [bumpedVersion, setBumpedVersion] = useState('');
  useEffect(() => {
    if (isOpen && requiresVersionBump) {
      setBumpedVersion(bumpOptions[0]?.version ?? '');
    } else {
      setBumpedVersion('');
    }
  }, [isOpen, requiresVersionBump, bumpOptions]);

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
      // Inject the forced version bump for published items before saving.
      const finalSaveData = requiresVersionBump
        ? {
            ...saveData,
            version_details: { ...(saveData.version_details ?? {}), version: bumpedVersion },
          }
        : saveData;
      await handleSaveItem(finalSaveData, itemType);
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
        disabled={isSaving || (requiresVersionBump && !bumpedVersion)}
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

        {requiresVersionBump && (
          <Box
            sx={{
              border: '1px solid var(--border-color)',
              borderRadius: 1,
              p: 1.5,
              display: 'flex',
              flexDirection: 'column',
              gap: 1,
            }}
          >
            <Alert severity="info" sx={{ fontSize: FONT_SIZES.BASE, py: 0 }}>
              This item is published. Editing it requires a new <strong>Item version</strong>. The
              bump you pick here is what gets pushed the next time you publish.
            </Alert>
            <FormControl fullWidth size="small">
              <InputLabel id="edit-bump-label">New item version</InputLabel>
              <Select
                labelId="edit-bump-label"
                label="New item version"
                value={bumpedVersion}
                onChange={(e) => setBumpedVersion(e.target.value)}
              >
                {bumpOptions.map((opt) => (
                  <MenuItem key={opt.version} value={opt.version}>
                    v{opt.version} — {opt.label}
                  </MenuItem>
                ))}
              </Select>
            </FormControl>
            <Typography sx={{ fontSize: '11px', color: 'var(--text-secondary)' }}>
              Item version {currentVersion ? `v${currentVersion}` : '(unset)'} → v
              {bumpedVersion || '…'}. Core version compatibility is separate and unchanged.
            </Typography>
          </Box>
        )}
      </Box>
    </BaseModal>
  );
};
