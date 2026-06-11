/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import { Autocomplete, Box, Button, CircularProgress, TextField, Typography } from '@mui/material';

import { QuickSearch } from '@/components/ui';
import BaseModal from '@/components/ui/Modal/BaseModal';
import { useLinkModalContext } from '@/contexts/LinkModalContext';
import { useNotification } from '@/contexts/NotificationContext';
import { createCatalogLink } from '@/services/catalog.service';

import type { CatalogItem } from '../types';

const styles = {
  dialog: {
    '& .MuiDialog-paper': {
      backgroundColor: 'var(--bg-tertiary)',
      color: 'var(--text-primary)',
      minWidth: '500px',
      maxWidth: '600px',
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
    mb: 2,
  },
  selectedItemBox: {
    bgcolor: 'var(--bg-secondary)',
    border: '1px solid var(--border)',
    borderRadius: '4px',
    p: 2,
    mb: 2,
  },
  selectedItemName: {
    fontSize: '13px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    mb: 1,
  },
  selectedItemDetails: {
    fontSize: '11px',
    color: 'var(--text-secondary)',
    '& span': {
      display: 'inline-block',
      mr: 2,
      '&:last-child': {
        mr: 0,
      },
    },
  },
  textField: {
    mb: 2,
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
    '& .MuiFormHelperText-root': {
      fontSize: '11px',
      color: 'var(--text-secondary)',
      mt: 0.5,
    },
    '& .MuiAutocomplete-popupIndicator': {
      color: 'var(--text-secondary)',
    },
    '& .MuiAutocomplete-clearIndicator': {
      color: 'var(--text-secondary)',
    },
  },
  autocompleteDropdown: {
    '& .MuiAutocomplete-paper': {
      backgroundColor: 'var(--bg-secondary)',
      color: 'var(--text-primary)',
      border: '1px solid var(--border)',
    },
    '& .MuiAutocomplete-listbox': {
      backgroundColor: 'var(--bg-secondary)',
      '& .MuiAutocomplete-option': {
        fontSize: '12px',
        '&:hover': {
          backgroundColor: 'var(--bg-tertiary)',
        },
        '&[aria-selected="true"]': {
          backgroundColor: 'var(--bg-tertiary)',
        },
      },
    },
  },
  suggestionsContainer: {
    border: '1px solid var(--border)',
    borderRadius: '4px',
    maxHeight: '150px',
    overflowY: 'auto',
    mt: 1,
    '&::-webkit-scrollbar': {
      width: '6px',
    },
    '&::-webkit-scrollbar-track': {
      bgcolor: 'var(--bg-secondary)',
    },
    '&::-webkit-scrollbar-thumb': {
      bgcolor: 'var(--border)',
      borderRadius: '3px',
    },
  },
  suggestionItem: {
    py: 1,
    px: 2,
    borderBottom: '1px solid var(--border)',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
    '&:last-child': {
      borderBottom: 'none',
    },
    '&:hover': {
      bgcolor: 'var(--bg-secondary)',
    },
  },
  suggestionLaui: {
    fontSize: '12px',
    fontWeight: 600,
    color: 'var(--text-primary)',
    mb: 0.25,
  },
  suggestionDetails: {
    fontSize: '11px',
    color: 'var(--text-secondary)',
  },
  suggestionsHeader: {
    fontSize: '11px',
    color: 'var(--text-secondary)',
    mb: 1,
    mt: 2,
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
    mt: 0.5,
    display: 'block',
  },
};

export default function LinkModal() {
  const [parentLaui, setParentLaui] = useState<string>('');
  const [localError, setLocalError] = useState<string>('');
  const [loading, setLoading] = useState(false);
  const { showSuccess } = useNotification();
  const { linkModalData, setLinkModalData } = useLinkModalContext();

  useEffect(() => {
    if (!open) {
      setParentLaui('');
      setLocalError('');
    }
  }, [open]);

  if (!linkModalData || !setLinkModalData) return;

  const { childItem, availableItems, itemTypeFilter, supportedParentTypes } = linkModalData;
  const useQuickSearch = !availableItems || availableItems.length === 0;
  const handleSave = async () => {
    setLocalError('');

    if (!parentLaui.trim()) {
      setLocalError('Parent LAUI is required');
      return;
    }

    if (!childItem) {
      setLocalError('Child item is required');
      return;
    }

    if (childItem.laui === parentLaui) {
      setLocalError('Parent and Child cannot be the same LAUI');
      return;
    }

    try {
      setLoading(true);
      const response = await createCatalogLink({
        parent_laui: parentLaui,
        child_laui: childItem.laui,
      });
      showSuccess(`Link created successfully! Link ID: ${response.link_laui}`);
      setLoading(false);
      handleClose();
    } catch (err: any) {
      const errorMessage =
        err.message || err.response?.data?.message || 'Failed to create link. Please try again.';
      setLocalError(errorMessage);
      setLoading(false);
    }
  };

  const handleClose = () => {
    setParentLaui('');
    setLocalError('');
    setLinkModalData({ ...linkModalData, isOpen: false });
  };

  const suggestionItems = (availableItems ?? []).filter(
    (item) => !childItem || item.laui !== childItem.laui,
  );

  const handleAutocompleteChange = (_event: any, newValue: CatalogItem | null) => {
    if (newValue) {
      setParentLaui(newValue.laui);
      setLocalError('');
      setLoading(false);
    } else {
      setParentLaui('');
    }
  };

  // Find the selected item from availableItems based on parentLaui
  const selectedItem = suggestionItems.find((item) => item.laui === parentLaui) || null;

  const ModalActions = (
    <>
      <Button onClick={handleClose} size="small" variant="outlined" disabled={loading}>
        Cancel
      </Button>
      <Button
        onClick={() => void handleSave()}
        size="small"
        variant="contained"
        disabled={!parentLaui.trim() || !childItem || loading}
      >
        {loading ? 'Creating...' : 'Create Link'}
      </Button>
    </>
  );
  return (
    <BaseModal
      open={linkModalData.isOpen}
      onClose={handleClose}
      title="Create Link"
      actions={ModalActions}
      loading={loading}
      loadingText="Checking for linked items..."
      maxWidth="sm"
    >
      {loading ? (
        <Box sx={styles.loadingContainer}>
          <CircularProgress size={32} sx={{ color: 'var(--primary-main)' }} />
          <Typography sx={{ ml: 2, fontSize: '12px' }}>Creating link...</Typography>
        </Box>
      ) : (
        <>
          <Box sx={styles.section}>
            <Typography sx={styles.sectionTitle}>Child Item</Typography>
            {childItem ? (
              <Box sx={styles.selectedItemBox}>
                <Typography sx={styles.selectedItemName}>
                  {childItem.name || 'Unnamed Item'}
                </Typography>
                <Typography sx={styles.selectedItemDetails}>
                  <span>LAUI: {childItem.laui}</span>
                  <span>Type: {childItem.item_type}</span>
                </Typography>
              </Box>
            ) : (
              <Typography
                sx={{
                  fontSize: '12px',
                  color: 'var(--text-secondary)',
                  fontStyle: 'italic',
                }}
              >
                No child item selected
              </Typography>
            )}
          </Box>

          <Box sx={styles.section}>
            <Typography sx={styles.sectionTitle}>Parent Item</Typography>

            {useQuickSearch ? (
              <QuickSearch
                label="Select Parent Item"
                placeholder="Search…"
                value={parentLaui}
                filters={
                  supportedParentTypes?.length
                    ? { item_types: supportedParentTypes }
                    : itemTypeFilter
                      ? { item_type: itemTypeFilter }
                      : undefined
                }
                onSelect={(raw: any) => {
                  const laui = raw._laui ?? raw.laui ?? '';
                  setParentLaui(laui);
                  setLocalError('');
                }}
                disabled={loading}
              />
            ) : suggestionItems.length > 0 ? (
              <Autocomplete
                fullWidth
                options={suggestionItems}
                value={selectedItem}
                onChange={handleAutocompleteChange}
                getOptionLabel={(option) => option.name || option.data?.name || option.laui}
                renderOption={(props, option) => (
                  <Box component="li" {...props} key={option.laui}>
                    <Box>
                      <Typography
                        sx={{
                          fontSize: '12px',
                          fontWeight: 600,
                          color: 'var(--text-primary)',
                        }}
                      >
                        {option.name || option.data?.name || 'Unnamed Item'}
                      </Typography>
                      <Typography
                        sx={{
                          fontSize: '11px',
                          color: 'var(--text-secondary)',
                        }}
                      >
                        {option.laui} • {option.item_type}
                      </Typography>
                    </Box>
                  </Box>
                )}
                renderInput={(params) => (
                  <TextField
                    {...params}
                    label="Select Parent Item"
                    placeholder="Search or select..."
                    variant="outlined"
                    size="small"
                    error={!!localError}
                    sx={styles.textField}
                  />
                )}
                disabled={loading}
                sx={styles.autocompleteDropdown}
                isOptionEqualToValue={(option, value) => option.laui === value.laui}
              />
            ) : (
              <TextField
                fullWidth
                label="Parent LAUI"
                value={parentLaui}
                onChange={(e) => {
                  setParentLaui(e.target.value);
                  setLocalError('');
                }}
                variant="outlined"
                size="small"
                sx={styles.textField}
                placeholder="Enter parent LAUI manually"
                error={!!localError}
                disabled={loading}
              />
            )}

            {localError && <Typography sx={styles.errorText}>{localError}</Typography>}
          </Box>
        </>
      )}
    </BaseModal>
  );
}
