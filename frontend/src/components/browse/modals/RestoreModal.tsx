/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import { Button, Stack, Typography } from '@mui/material';

import BaseModal from '@/components/ui/Modal/BaseModal';
import { FONT_SIZES } from '@/constants';
import { useCatalog } from '@/contexts/CatalogContext';
import { useNotification } from '@/contexts/NotificationContext';
import { restoreItem } from '@/services';

import type { CatalogItem } from '../types';

export interface RestoreModalData {
  isOpen: boolean;
  item?: CatalogItem;
  /** Multiple items for a bulk restore; takes precedence over `item`. */
  items?: CatalogItem[];
  onSuccess?: () => void;
}

export const RestoreModal = () => {
  const { restoreModalState, setRestoreModalState } = useCatalog();
  const { isOpen, item, items } = restoreModalState;
  const { showSuccess, showError } = useNotification();

  const [restoring, setRestoring] = useState<boolean>(false);

  // Normalize single- and multi-item callers into one list of targets.
  const targets: CatalogItem[] = items && items.length > 0 ? items : item ? [item] : [];
  const isBulk = targets.length > 1;

  if (targets.length === 0) return;

  const handleClose = () => {
    setRestoreModalState({ isOpen: false });
  };

  const handleRestoreConfirm = async () => {
    setRestoring(true);
    // Restore sequentially: each restore is a backend transaction over shared links.
    const failed: string[] = [];
    let restored = 0;
    let lastMessage = '';
    for (const target of targets) {
      try {
        const response = await restoreItem(target.laui);
        lastMessage = response?.message ?? '';
        restored += 1;
      } catch {
        failed.push(target.name || target.laui);
      }
    }
    setRestoring(false);

    if (restored > 0) {
      showSuccess(isBulk ? `${restored} items restored` : lastMessage || 'Item restored');
    }
    if (failed.length > 0) {
      showError(`Failed to restore ${failed.length} item(s): ${failed.join(', ')}`);
    }
    setRestoreModalState({ isOpen: false });
    if (restored > 0) {
      restoreModalState.onSuccess?.();
    }
  };

  const ModalActions = (
    <>
      <Button onClick={handleClose} sx={{ fontSize: FONT_SIZES.BASE }}>
        Cancel
      </Button>
      <Button
        onClick={() => void handleRestoreConfirm()}
        variant="contained"
        sx={{
          bgcolor: 'var(--accent)',
          color: 'white',
          fontSize: FONT_SIZES.BASE,
        }}
        disabled={restoring}
      >
        {restoring ? 'Restoring' : isBulk ? `Restore ${targets.length} Items` : 'Restore'}
      </Button>
    </>
  );

  return (
    <BaseModal
      open={isOpen}
      actions={ModalActions}
      title={isBulk ? `Restore ${targets.length} items` : `Restore ${targets[0].name}`}
      onClose={handleClose}
    >
      <Typography sx={{ fontSize: FONT_SIZES.BASE }}>
        {isBulk
          ? `Are you sure you want to restore these ${targets.length} items?`
          : `Are you sure you want to restore ${targets[0].name}?`}
      </Typography>
      {isBulk && (
        <Stack spacing={0.5} sx={{ mt: 1.5, maxHeight: '200px', overflowY: 'auto' }}>
          {targets.map((target) => (
            <Typography
              key={target.laui}
              sx={{ fontSize: FONT_SIZES.SM, color: 'var(--text-secondary)' }}
            >
              • {target.name}
            </Typography>
          ))}
        </Stack>
      )}
    </BaseModal>
  );
};
