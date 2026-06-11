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
  ClickAwayListener,
  FormControl,
  InputAdornment,
  InputLabel,
  MenuItem,
  Paper,
  Select,
  TextField,
  Typography,
} from '@mui/material';

import BaseModal from '@/components/ui/Modal/BaseModal';
import { useCatalog } from '@/contexts/CatalogContext';
import { useNotification } from '@/contexts/NotificationContext';
import { updateItemAccess } from '@/screens/Browse/utils';
import { searchGroups } from '@/services/group.service';
import { searchUsers } from '@/services/user.service';

import { getUserItemPermission } from '../../../services/access.service';
import type { CatalogItem } from '../types';

interface EntityData {
  displayName: string;
  laui: string;
  currentPermission?: string;
  newPermission?: string;
  inputDisabled: boolean;
}

export interface ShareModalData {
  isOpen: boolean;
  item?: CatalogItem;
}

const styles = {
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
    mb: 3,
    '& .MuiOutlinedInput-root': {
      backgroundColor: 'var(--bg-secondary)',
      color: 'var(--text-primary)',
      fontSize: '12px',

      '&.Mui-disabled': {
        backgroundColor: 'var(--bg-secondary)',
      },
      '& .MuiOutlinedInput-input.Mui-disabled': {
        color: 'var(--text-primary)',
        WebkitTextFillColor: 'var(--text-primary)',
        opacity: 1,
      },
      '& fieldset': {
        borderColor: 'var(--border)',
      },
      '&:hover fieldset': {
        borderColor: 'var(--primary-main)',
      },
      '&.Mui-focused fieldset': {
        borderColor: 'var(--primary-main)',
      },
      '&.Mui-disabled .MuiOutlinedInput-notchedOutline': {
        borderColor: 'var(--border)',
      },
    },
    '& .MuiInputLabel-root': {
      color: 'var(--text-secondary)',
      fontSize: '12px',
      '&.Mui-disabled': {
        color: 'var(--text-secondary)',
      },
    },
  },
  select: {
    mb: 3,
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
  dropdownPaper: {
    position: 'absolute',
    top: '100%',
    left: 0,
    right: 0,
    mt: -2,
    maxHeight: 200,
    overflow: 'auto',
    zIndex: 30,
    bgcolor: 'var(--bg-primary)',
    border: '1px solid var(--border)',
  },
  dropdownItem: {
    px: 1.5,
    py: 1,
    cursor: 'pointer',
    '&:hover': { bgcolor: 'var(--bg-tertiary)' },
    borderBottom: '1px solid var(--border)',
    '&:last-child': { borderBottom: 'none' },
  },
};

export default function ShareModal() {
  const { shareModalState, setShareModalState } = useCatalog();
  const { isOpen, item } = shareModalState;
  const { showSuccess } = useNotification();

  const [entityType, setEntityType] = useState<'user' | 'group'>('user');

  // Unified state structure using displayName to control the input text
  const [userData, setUserData] = useState<EntityData>({
    displayName: '',
    laui: '',
    inputDisabled: false,
  });
  const [groupData, setGroupData] = useState<EntityData>({
    displayName: '',
    laui: '',
    inputDisabled: false,
  });

  const [accessLevels, setAccessLevels] = useState<string[]>([]);
  const [localError, setLocalError] = useState<string>('');
  const [loading, setLoading] = useState(false);

  // Search State
  const [searchDropdownOpen, setSearchDropdownOpen] = useState(false);
  const [searchResults, setSearchResults] = useState<any[]>([]);

  useEffect(() => {
    if (!isOpen) {
      setEntityType('user');
      setUserData({ displayName: '', laui: '', inputDisabled: false });
      setGroupData({ displayName: '', laui: '', inputDisabled: false });
      setAccessLevels([]);
      setSearchResults([]);
      setSearchDropdownOpen(false);
    }
  }, [isOpen]);

  const handleEntityTypeChange = (newType: 'user' | 'group') => {
    setEntityType(newType);
    setAccessLevels([]);
    setLocalError('');
    setSearchResults([]);
    setSearchDropdownOpen(false);
    setUserData({ displayName: '', laui: '', inputDisabled: false });
    setGroupData({ displayName: '', laui: '', inputDisabled: false });
  };

  const handleSearchInputChange = async (val: string) => {
    // Update local input state and clear LAUI so the user is forced to select from the new list
    if (entityType === 'user') {
      setUserData((prev) => ({ ...prev, displayName: val, laui: '' }));
    } else {
      setGroupData((prev) => ({ ...prev, displayName: val, laui: '' }));
    }
    setLocalError('');

    try {
      if (entityType === 'user') {
        const res: any = await searchUsers({ username: val });
        setSearchResults(res.users || []);
      } else {
        const res: any = await searchGroups({ name: val });
        setSearchResults(res.groups || []);
      }
      setSearchDropdownOpen(true);
    } catch (e) {
      console.error(`Error fetching ${entityType} catalog data:`, e);
    }
  };

  const handleSelectFromSearch = (entity: any) => {
    const selectedLaui = entity.laui || entity.id;
    if (entityType === 'user') {
      setUserData((prev) => ({
        ...prev,
        displayName: entity.username || entity.email || entity.name,
        laui: selectedLaui,
      }));
    } else {
      setGroupData((prev) => ({ ...prev, displayName: entity.name, laui: selectedLaui }));
    }
    setSearchDropdownOpen(false);
    setSearchResults([]);
  };

  if (!item) return null;

  const loggedInUserPermission = item.permission;
  const allowed = ['edit', 'own'];
  if (!allowed.includes(loggedInUserPermission)) return null;

  const handleUserConfirm = async () => {
    if (!userData.laui) {
      setLocalError('Please select a user from the dropdown.');
      return;
    }

    try {
      setLoading(true);
      // Pass user.laui directly
      const response = await getUserItemPermission(item.laui.trim(), userData.laui, '');
      const currentPermission = response.permission;
      setUserData({ ...userData, currentPermission, inputDisabled: true });

      if (currentPermission === 'edit' && loggedInUserPermission === 'own')
        setAccessLevels(['own']);
      else if (currentPermission === 'view')
        setAccessLevels(loggedInUserPermission === 'own' ? ['edit', 'own'] : ['edit']);
      else if (currentPermission === 'none')
        setAccessLevels(
          loggedInUserPermission === 'own' ? ['view', 'edit', 'own'] : ['view', 'edit'],
        );
      else setAccessLevels([]);
    } catch (err: any) {
      setLocalError(err?.message || 'Failed to fetch user permissions');
    } finally {
      setLoading(false);
    }
  };

  const handleGroupConfirm = async () => {
    if (!groupData.laui) {
      setLocalError('Please select a group from the dropdown.');
      return;
    }

    try {
      setLoading(true);
      // Pass group.laui directly
      const response = await getUserItemPermission(item.laui.trim(), '', groupData.laui);
      const currentPermission = response.permission;
      setGroupData({ ...groupData, currentPermission, inputDisabled: true });

      if (currentPermission === 'edit' && loggedInUserPermission === 'own')
        setAccessLevels(['own']);
      else if (currentPermission === 'view')
        setAccessLevels(loggedInUserPermission === 'own' ? ['edit', 'own'] : ['edit']);
      else if (currentPermission === 'none')
        setAccessLevels(
          loggedInUserPermission === 'own' ? ['view', 'edit', 'own'] : ['view', 'edit'],
        );
      else setAccessLevels([]);
    } catch (err: any) {
      setLocalError(err?.message || 'Failed to fetch group permissions');
    } finally {
      setLoading(false);
    }
  };

  const handleClear = () => {
    if (entityType === 'user') {
      setUserData({ displayName: '', laui: '', inputDisabled: false });
    } else {
      setGroupData({ displayName: '', laui: '', inputDisabled: false });
    }
    setAccessLevels([]);
    setLocalError('');
    setSearchDropdownOpen(false);
    setSearchResults([]);
  };

  const permissionRelationMap: Record<string, string> = {
    own: 'owners',
    edit: 'editors',
    view: 'viewers',
  };

  const handleSave = async () => {
    setLocalError('');
    const currentData = entityType === 'user' ? userData : groupData;

    if (!currentData.laui.trim()) {
      setLocalError(
        entityType === 'user' ? 'User selection is required' : 'Group selection is required',
      );
      return;
    }
    if (!currentData.newPermission) return;

    try {
      setLoading(true);
      const prefix = entityType === 'user' ? 'U' : 'G';
      const currentRelation = currentData.currentPermission
        ? permissionRelationMap[currentData.currentPermission]
        : '';
      const newRelation = permissionRelationMap[currentData.newPermission];

      await updateItemAccess({
        itemLaui: item.laui,
        userLaui: `${prefix}${currentData.laui}`,
        newRelation,
        currentRelation,
      });

      showSuccess(`Granted ${newRelation} access successfully!`);
      handleClose();
    } catch (err: any) {
      const errorMessage = err.message || 'Failed to share. Please try again.';
      setLocalError(errorMessage);
    } finally {
      setLoading(false);
    }
  };

  const handleClose = () => {
    setLocalError('');
    setShareModalState({ isOpen: false });
  };

  const isInputDisabled = entityType === 'user' ? userData.inputDisabled : groupData.inputDisabled;

  return (
    <BaseModal
      open={isOpen}
      onClose={handleClose}
      actions={
        <>
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
            disabled={
              (entityType === 'user' ? !userData.newPermission : !groupData.newPermission) ||
              loading
            }
          >
            {loading ? 'Sharing...' : 'Share'}
          </Button>
        </>
      }
      title={`Grant access to ${entityType === 'user' ? 'user' : 'group'}`}
    >
      {loading && !isInputDisabled ? (
        <Box sx={styles.loadingContainer}>
          <CircularProgress size={32} sx={{ color: 'var(--primary-main)' }} />
          <Typography sx={{ ml: 2, fontSize: '12px' }}>Loading...</Typography>
        </Box>
      ) : (
        <>
          {/* Item Section */}
          <Box sx={styles.section}>
            <Typography sx={styles.sectionTitle}>Item</Typography>
            <Box sx={styles.selectedItemBox}>
              <Typography sx={styles.selectedItemName}>{item.name}</Typography>
              <Typography sx={styles.selectedItemDetails}>
                <span>LAUI: {item.laui}</span>
                <span>Type: {item.item_type}</span>
              </Typography>
            </Box>
          </Box>

          {/* Entity Type Selector */}
          <Box sx={styles.section}>
            <FormControl fullWidth size="small" sx={styles.select}>
              <InputLabel>Entity Type</InputLabel>
              <Select
                value={entityType}
                onChange={(e) => handleEntityTypeChange(e.target.value)}
                label="Entity Type"
                disabled={loading || isInputDisabled}
              >
                <MenuItem value="user">User</MenuItem>
                <MenuItem value="group">Group</MenuItem>
              </Select>
            </FormControl>
          </Box>

          {/* Input Field with Dropdown & Confirm/Clear Button */}
          <Box sx={styles.section}>
            <ClickAwayListener onClickAway={() => setSearchDropdownOpen(false)}>
              <Box sx={{ position: 'relative' }}>
                <TextField
                  fullWidth
                  label={entityType === 'user' ? 'Select user' : 'Select group'}
                  value={entityType === 'user' ? userData.displayName : groupData.displayName}
                  onChange={(e) => void handleSearchInputChange(e.target.value)}
                  onFocus={() => {
                    if (!isInputDisabled) {
                      const currentVal =
                        entityType === 'user' ? userData.displayName : groupData.displayName;
                      setSearchDropdownOpen(true);
                      void handleSearchInputChange(currentVal); // This triggers with "" if empty
                    }
                  }}
                  variant="outlined"
                  size="small"
                  sx={styles.textField}
                  placeholder={entityType === 'user' ? 'Select user...' : 'Select group...'}
                  error={!!localError}
                  disabled={loading || isInputDisabled}
                  InputProps={{
                    endAdornment: (
                      <InputAdornment position="end">
                        <Button
                          size="small"
                          onClick={
                            isInputDisabled
                              ? handleClear
                              : entityType === 'user'
                                ? handleUserConfirm
                                : handleGroupConfirm
                          }
                          sx={{ fontSize: '10px', textTransform: 'none' }}
                        >
                          {isInputDisabled ? `Clear ${entityType}` : `Confirm ${entityType}`}
                        </Button>
                      </InputAdornment>
                    ),
                  }}
                />

                {/* Dropdown Menu */}
                {!isInputDisabled && searchDropdownOpen && searchResults.length > 0 && (
                  <Paper elevation={4} sx={styles.dropdownPaper}>
                    {searchResults.map((entity: any, idx: number) => {
                      const displayId = entity.laui || entity.id || entity.username || entity.name;
                      return (
                        <Box
                          key={idx}
                          onClick={() => handleSelectFromSearch(entity)}
                          sx={styles.dropdownItem}
                        >
                          <Typography
                            variant="body2"
                            sx={{
                              color: 'var(--text-primary)',
                              fontWeight: 500,
                            }}
                          >
                            {entityType === 'user'
                              ? entity.username || entity.name || 'Unknown User'
                              : entity.name || 'Unknown Group'}
                          </Typography>
                          <Typography
                            variant="caption"
                            sx={{
                              color: 'var(--text-secondary)',
                              fontFamily: 'monospace',
                            }}
                          >
                            {displayId}{' '}
                            {entityType === 'user' && entity.email ? `• ${entity.email}` : ''}
                          </Typography>
                        </Box>
                      );
                    })}
                  </Paper>
                )}
              </Box>
            </ClickAwayListener>
          </Box>

          {/* Permissions Section - Shown only after Confirm */}
          {isInputDisabled && (
            <>
              <Box sx={styles.section}>
                <TextField
                  fullWidth
                  label="Current Permission"
                  value={
                    entityType === 'user' ? userData.currentPermission : groupData.currentPermission
                  }
                  variant="outlined"
                  size="small"
                  sx={styles.textField}
                  disabled
                />
              </Box>

              <Box sx={styles.section}>
                {accessLevels.length > 0 ? (
                  <FormControl fullWidth size="small" sx={styles.select}>
                    <InputLabel>Assign Permission</InputLabel>
                    <Select
                      value={
                        entityType === 'user'
                          ? userData.newPermission || ''
                          : groupData.newPermission || ''
                      }
                      onChange={(e) => {
                        const val = e.target.value;
                        if (entityType === 'user') {
                          setUserData((prev) => ({
                            ...prev,
                            newPermission: val,
                          }));
                        } else {
                          setGroupData((prev) => ({
                            ...prev,
                            newPermission: val,
                          }));
                        }
                        setLocalError('');
                      }}
                      label="Assign Permission"
                      disabled={loading}
                    >
                      {accessLevels.map((type) => (
                        <MenuItem key={type} value={type}>
                          {type}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                ) : (
                  <TextField
                    fullWidth
                    value="Access change not possible"
                    variant="outlined"
                    size="small"
                    sx={styles.textField}
                    disabled
                  />
                )}
              </Box>
            </>
          )}

          {localError && <Typography sx={styles.errorText}>{localError}</Typography>}
        </>
      )}
    </BaseModal>
  );
}
