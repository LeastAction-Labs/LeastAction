/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import { Button, Typography } from '@mui/material';

import BaseModal from '@/components/ui/Modal/BaseModal';
import { FONT_SIZES } from '@/constants';
import { useCatalog } from '@/contexts/CatalogContext';
import { useNotification } from '@/contexts/NotificationContext';
import { restoreItem } from '@/services';

import type { CatalogItem } from '../types';

export interface RestoreModalData {
  isOpen: boolean;
  item?: CatalogItem;
}

export const RestoreModal = () => {
  const { restoreModalState, setRestoreModalState } = useCatalog();
  const { isOpen, item } = restoreModalState;
  const { showSuccess } = useNotification();

  const [restoring, setRestoring] = useState<boolean>(false);

  if (!item) return;

  const handleClose = () => {
    setRestoreModalState({ isOpen: false });
  };

  const handleRestoreConfirm = async () => {
    try {
      setRestoring(true);
      const response = await restoreItem(item.laui);
      showSuccess(response.message);
      handleClose();
    } catch {
      /* ignore */
    } finally {
      setRestoring(false);
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
        {restoring ? 'Restoring' : 'Restore'}
      </Button>
    </>
  );

  return (
    <BaseModal
      open={isOpen}
      actions={ModalActions}
      title={`Restore ${item.name}`}
      onClose={handleClose}
    >
      <Typography sx={{ fontSize: FONT_SIZES.BASE }}>
        Are you sure you want to restore {item.name}?
      </Typography>
    </BaseModal>
  );
};
