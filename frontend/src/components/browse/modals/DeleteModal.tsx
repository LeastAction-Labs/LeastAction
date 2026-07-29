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

/** A single item targeted by the delete modal. */
export interface DeleteModalTarget {
  laui: string;
  name: string;
}

export interface DeleteModalData {
  isOpen: boolean;
  itemLaui?: string;
  itemName?: string;
  /** Multiple targets for a bulk delete; takes precedence over itemLaui/itemName. */
  targets?: DeleteModalTarget[];
  parentLaui?: string;
  onSuccess?: () => void;
  /** True when the item is already in trash, so this delete is permanent. */
  isPermanent?: boolean;
}

export default function DeleteModal() {
  const { catalogType } = useGlobal();
  const { setDeleteModalState, deleteModalState } = useCatalog();
  const { isOpen, itemName, itemLaui, targets, parentLaui, isPermanent } = deleteModalState;
  const { showSuccess, showError } = useNotification();

  const isMarketplaceCatalog = catalogType === CatalogType.MARKETPLACE;

  const [loading, setLoading] = useState(false);
  const [submitting, setSubmitting] = useState(false);
  const [items, setItems] = useState<any[]>([]);

  // Normalize single- and multi-item callers into one list of targets.
  const deleteTargets: DeleteModalTarget[] =
    targets && targets.length > 0
      ? targets
      : itemLaui
        ? [{ laui: itemLaui, name: itemName ?? '' }]
        : [];
  const isBulk = deleteTargets.length > 1;
  const targetLauis = deleteTargets.map((t) => t.laui).join(',');

  const handleClose = () => {
    if (!submitting) {
      setDeleteModalState({ ...deleteModalState, isOpen: false });
    }
  };

  const handleDelete = async () => {
    setSubmitting(true);
    // Delete sequentially: each delete is a backend transaction over shared links.
    const failed: string[] = [];
    let deleted = 0;
    for (const target of deleteTargets) {
      try {
        await deleteCatalogItem(target.laui, parentLaui!, isMarketplaceCatalog);
        deleted += 1;
      } catch {
        failed.push(target.name || target.laui);
      }
    }
    setSubmitting(false);

    if (deleted > 0) {
      const noun = deleted === 1 ? 'Item' : `${deleted} items`;
      showSuccess(
        isPermanent ? `${noun} permanently deleted` : `${noun} moved to trash successfully`,
      );
    }
    if (failed.length > 0) {
      showError(`Failed to delete ${failed.length} item(s): ${failed.join(', ')}`);
    }
    setDeleteModalState({ ...deleteModalState, isOpen: false });
    if (deleted > 0) {
      deleteModalState.onSuccess?.();
    }
  };

  useEffect(() => {
    if (isOpen && deleteTargets.length > 0 && !isMarketplaceCatalog) {
      const loadAssociatedItems = async () => {
        setLoading(true);
        try {
          const linkResponses = await Promise.all(
            deleteTargets.map((target) =>
              searchCatalogLinks({ child_laui: target.laui, true_parent: 'false' }),
            ),
          );
          const links = linkResponses.flatMap((response: any) => response.links || []);

          if (links.length > 0) {
            const itemLauis = [...new Set(links.map((link: any) => link.parent_laui as string))];
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
  }, [isOpen, targetLauis]);

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
        {submitting
          ? 'Deleting...'
          : isPermanent
            ? 'Delete Permanently'
            : isBulk
              ? `Delete ${deleteTargets.length} Items`
              : 'Delete Item'}
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
            ? `Permanently delete ${isBulk ? 'items' : 'item'}`
            : `Move ${isBulk ? 'items' : 'item'} to trash`
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
              Are you sure you want to permanently delete{' '}
              <strong>
                {isBulk ? `these ${deleteTargets.length} items` : deleteTargets[0]?.name}
              </strong>
              ? This action cannot be undone.
            </>
          ) : (
            <>
              Are you sure you want to move {isBulk ? '' : 'item '}
              <strong>
                {isBulk ? `these ${deleteTargets.length} items` : deleteTargets[0]?.name}
              </strong>{' '}
              to trash?
            </>
          )}
          {items.length > 0 &&
            (isBulk
              ? ' These items and their children are linked with the items below. These links will be permanently deleted.'
              : ' This item and its children are linked with the items below. These links will be permanently deleted.')}
        </Typography>

        {isBulk && (
          <Stack spacing={0.5} sx={{ mb: 2, maxHeight: '200px', overflowY: 'auto' }}>
            {deleteTargets.map((target) => (
              <Typography
                key={target.laui}
                sx={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}
              >
                • {target.name}
              </Typography>
            ))}
          </Stack>
        )}

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
