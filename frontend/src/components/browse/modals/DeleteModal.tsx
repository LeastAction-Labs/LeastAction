/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import DeleteIcon from '@mui/icons-material/Delete';
import { Box, Button, Stack, Typography } from '@mui/material';

import BaseModal from '@/components/ui/Modal/BaseModal';
import { useCatalog } from '@/contexts/CatalogContext';
import { CatalogType, useGlobal } from '@/contexts/GlobalContext';
import { useNotification } from '@/contexts/NotificationContext';
import {
  deleteCatalogItem,
  searchCatalogItems,
  searchCatalogLinks,
} from '@/services/catalog.service';

import LinkedItemRow from './LinkedItemRow';

export interface DeleteModalData {
  isOpen: boolean;
  itemLaui?: string;
  itemName?: string;
  parentLaui?: string;
  onSuccess?: () => void;
  /** True when the item is already in trash, so this delete is permanent. */
  isPermanent?: boolean;
}

export default function DeleteModal() {
  const { catalogType } = useGlobal();
  const { setDeleteModalState, deleteModalState } = useCatalog();
  const { isOpen, itemName, itemLaui, parentLaui, isPermanent } = deleteModalState;
  const { showSuccess } = useNotification();

  const isMarketplaceCatalog = catalogType === CatalogType.MARKETPLACE;

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [items, setItems] = useState<any[]>([]);

  const handleClose = () => {
    if (!submitting) {
      setDeleteModalState({ ...deleteModalState, isOpen: false });
    }
  };

  const handleDelete = async () => {
    setSubmitting(true);
    try {
      await deleteCatalogItem(itemLaui!, parentLaui!, isMarketplaceCatalog);
      showSuccess(isPermanent ? 'Item permanently deleted' : 'Item deleted successfully');
      handleClose();
      deleteModalState.onSuccess?.();
    } catch {
      /* ignore */
    } finally {
      setSubmitting(false);
    }
  };

  useEffect(() => {
    if (isOpen && itemLaui && !isMarketplaceCatalog) {
      const loadAssociatedItems = async () => {
        setLoading(true);
        try {
          const linksResponse = await searchCatalogLinks({
            child_laui: itemLaui,
            true_parent: 'false',
          });
          const links = linksResponse.links || [];

          if (links.length > 0) {
            const itemLauis = links.map((link: any) => link.parent_laui);
            const itemsResponse = await searchCatalogItems(undefined, false, {
              filters: { item_lauis: itemLauis },
            });
            setItems(itemsResponse.items || []);
          } else {
            setItems([]);
          }
        } catch (err) {
          console.error('Error fetching linked items:', err);
        } finally {
          setLoading(false);
        }
      };
      void loadAssociatedItems();
    }
  }, [isOpen, itemLaui]);

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
          '&:hover': {
            borderColor: 'var(--primary-main)',
            color: 'var(--text-primary)',
          },
        }}
      >
        Cancel
      </Button>
      <Button
        onClick={() => void handleDelete()}
        disabled={loading || submitting}
        size="small"
        variant="contained"
        startIcon={<DeleteIcon />}
        sx={{
          bgcolor: 'var(--error-main, #d32f2f)',
          color: '#fff',
          textTransform: 'none',
          fontWeight: 'bold',
          '&:hover': {
            bgcolor: '#b71c1c',
          },
          '&:disabled': {
            bgcolor: 'var(--bg-tertiary)',
            color: 'var(--text-disabled)',
          },
          py: 0.5,
          px: 1.5,
        }}
      >
        {submitting ? 'Deleting...' : isPermanent ? 'Delete Permanently' : 'Delete Item'}
      </Button>
    </>
  );

  return (
    <BaseModal
      open={isOpen}
      onClose={handleClose}
      title="Confirm Delete"
      subtitle={
        items.length > 0
          ? 'Potential impact on linked items'
          : isPermanent
            ? 'Permanently delete item'
            : 'Move item to trash'
      }
      actions={ModalActions}
      loading={loading}
      loadingText="Checking for linked items..."
      maxWidth="sm"
    >
      <Box sx={{ mt: 1 }}>
        <Typography sx={{ color: 'var(--text-primary)', mb: 2 }}>
          {isPermanent ? (
            <>
              Are you sure you want to permanently delete <strong>{itemName}</strong>? This action
              cannot be undone.
            </>
          ) : (
            <>
              Are you sure you want to move item <strong>{itemName}</strong> to trash?
            </>
          )}
          {items.length > 0 &&
            ' This item and its children are linked with the items below. These links will be permanently deleted.'}
        </Typography>

        {items.length > 0 && (
          <Stack spacing={1.5} sx={{ mt: 2, maxH: '300px', overflowY: 'auto' }}>
            {items.map((item, index) => (
              <LinkedItemRow key={item.laui || index} item={item} index={index} />
            ))}
          </Stack>
        )}
      </Box>
    </BaseModal>
  );
}
