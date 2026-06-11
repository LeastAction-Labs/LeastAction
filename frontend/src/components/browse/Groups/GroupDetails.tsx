/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useMemo, useState } from 'react';

import {
  Add as AddIcon,
  ArrowBack as BackIcon,
  Close as CloseIcon,
  Delete as DeleteIcon,
  Edit as EditIcon,
  FilterList as FilterIcon,
  Save as SaveIcon,
  Search as SearchIcon,
} from '@mui/icons-material';
import {
  Box,
  Button,
  Checkbox,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogTitle,
  FormControl,
  IconButton,
  InputAdornment,
  MenuItem,
  Paper,
  Select,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';

import UserSearch from '@/components/users/UserSearch';
import { FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import { useNotification } from '@/contexts/NotificationContext';
// --- Import the new Context hooks ---
import { useUserCache, useUsers } from '@/contexts/UserCacheContext';
import type { Relation } from '@/services/group.service';

const styles = {
  container: { flex: 1, overflow: 'auto', bgcolor: 'transparent', p: 3 },
  header: {
    display: 'flex',
    alignItems: 'center',
    gap: 2,
    mb: 3,
    pb: 2,
    borderBottom: '1px solid var(--border)',
  },
  backButton: { color: 'var(--text-primary)', '&:hover': { bgcolor: 'var(--bg-secondary)' } },
  section: { mb: 3, p: 2, bgcolor: 'var(--bg-secondary)', borderRadius: 1 },
  sectionHeader: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'space-between',
    mb: 2,
  },
  sectionTitle: {
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
    color: 'var(--accent)',
    fontSize: FONT_SIZES.MD,
  },
  tableContainer: {
    bgcolor: 'var(--bg-tertiary)',
    borderRadius: 1,
    mt: 2,
    '& .MuiTableCell-root': { color: 'var(--text-primary)', borderColor: 'var(--border)' },
    '& .MuiTableCell-head': {
      fontWeight: FONT_WEIGHTS.WEIGHT_600,
      bgcolor: 'var(--bg-secondary)',
    },
  },
  controlsRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    mb: 2,
    gap: 2,
    flexWrap: 'wrap',
  },
  bulkToolbar: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    mb: 2,
    p: 1.5,
    bgcolor: 'rgba(25, 118, 210, 0.08)',
    borderRadius: 1,
    border: '1px solid rgba(25, 118, 210, 0.2)',
  },
  button: {
    bgcolor: '#1976d2',
    color: '#ffffff',
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
    '&:hover': { bgcolor: '#1565c0' },
    '&.Mui-disabled': { bgcolor: '#1976d2', color: 'rgba(255,255,255,0.4)', opacity: 0.5 },
  },
  cancelButton: {
    color: 'var(--text-secondary)',
    borderColor: 'var(--border)',
    '&:hover': { bgcolor: 'var(--bg-tertiary)', borderColor: 'var(--text-secondary)' },
  },
  emptyText: { color: 'var(--text-secondary)', fontStyle: 'italic', fontSize: FONT_SIZES.SM },
  pagination: {
    color: 'var(--text-primary)',
    '& .MuiTablePagination-selectLabel, & .MuiTablePagination-displayedRows': {
      color: 'var(--text-primary)',
    },
    '& .MuiTablePagination-select': { color: 'var(--text-primary)' },
    '& .MuiTablePagination-selectIcon': { color: 'var(--text-secondary)' },
    '& .MuiTablePagination-actions': {
      color: 'var(--text-primary)',
      '& .Mui-disabled': { color: 'var(--text-secondary)', opacity: 0.5 },
    },
  },
};

export interface GroupDetailsData {
  name: string;
  description: string;
  admins: string[];
  members: string[];
  owners: string[];
  laui: string;
}

interface GroupDetailsProps {
  groupLaui: string;
  onBack: () => void;
  userRelation: Relation;
  get_group: (laui: string) => Promise<GroupDetailsData>;
  update_group: (name: string, description: string, accessPatch: any) => Promise<void>;
}

type PatchRole = 'viewers' | 'editors' | 'owners';
type InternalRole = 'members' | 'admins' | 'owners';

interface AccessPatch {
  add: Record<PatchRole, Record<string, string>>;
  remove: Record<PatchRole, Record<string, string>>;
}

type BaseUser = {
  laui: string;
  role: InternalRole;
};

const API_ROLES: Record<InternalRole, PatchRole> = {
  members: 'viewers',
  admins: 'editors',
  owners: 'owners',
};

export default function GroupDetails({
  groupLaui,
  onBack,
  userRelation,
  get_group,
  update_group,
}: GroupDetailsProps) {
  const { showSuccess } = useNotification();

  // Expose the raw cache specifically for the local search filter
  const { userCache } = useUserCache();

  const canEdit = userRelation === 'owners' || userRelation === 'editors';
  const canEditOwners = userRelation === 'owners';

  const [loading, setLoading] = useState(true);
  const [saving, setSaving] = useState(false);
  const [groupData, setGroupData] = useState<GroupDetailsData | null>(null);

  // Description State
  const [isEditingDesc, setIsEditingDesc] = useState(false);
  const [descriptionValue, setDescriptionValue] = useState('');

  // Table State
  const [roleFilter, setRoleFilter] = useState<'all' | InternalRole>('all');
  const [searchQuery, setSearchQuery] = useState('');
  const [page, setPage] = useState(0);
  const [rowsPerPage, setRowsPerPage] = useState(5);

  // Bulk Actions State
  const [selectedLauis, setSelectedLauis] = useState<string[]>([]);
  const [bulkRoleTarget, setBulkRoleTarget] = useState<InternalRole | ''>('');

  // Modal State
  const [isAddModalOpen, setIsAddModalOpen] = useState(false);
  const [queuedUsers, setQueuedUsers] = useState<any[]>([]);
  const [modalTargetRole, setModalTargetRole] = useState<InternalRole>('members');

  useEffect(() => {
    void loadGroupData();
  }, [groupLaui]);

  const loadGroupData = async () => {
    try {
      setLoading(true);
      const data = await get_group(groupLaui);
      setGroupData(data);
      setDescriptionValue(data.description || '');
    } catch (error) {
      console.error('Error loading group data:', error);
    } finally {
      setLoading(false);
      setSelectedLauis([]);
    }
  };

  const formatLauiKey = (laui: string) =>
    laui.includes('@') ? laui : laui.startsWith('U') ? laui : `U${laui}`;

  const createEmptyPatch = (): AccessPatch => ({
    add: { viewers: {}, editors: {}, owners: {} },
    remove: { viewers: {}, editors: {}, owners: {} },
  });

  const executeAccessPatch = async (patch: AccessPatch, successMsg: string) => {
    if (!groupData) return;
    try {
      setSaving(true);
      await update_group(groupData.name, groupData.description, patch);
      showSuccess(successMsg);
      await loadGroupData();
    } catch {
      /* ignore */
    } finally {
      setSaving(false);
    }
  };

  // --- SINGLE ACTIONS ---
  const handleRoleChangeSingle = async (
    laui: string,
    oldRole: InternalRole,
    newRole: InternalRole,
  ) => {
    const patch = createEmptyPatch();
    const key = formatLauiKey(laui);
    patch.remove[API_ROLES[oldRole]][key] = '';
    patch.add[API_ROLES[newRole]][key] = '';
    await executeAccessPatch(patch, `Role updated to ${newRole}`);
  };

  const handleDeleteSingle = async (laui: string, role: InternalRole) => {
    const patch = createEmptyPatch();
    patch.remove[API_ROLES[role]][formatLauiKey(laui)] = '';
    await executeAccessPatch(patch, 'User removed from group');
  };

  // --- BULK ACTIONS ---
  const handleBulkRoleChange = async () => {
    if (!bulkRoleTarget || selectedLauis.length === 0) return;
    const patch = createEmptyPatch();

    selectedLauis.forEach((laui) => {
      const user = flattenedUsers.find((u) => u.laui === laui);
      if (user && user.role !== bulkRoleTarget) {
        const key = formatLauiKey(laui);
        patch.remove[API_ROLES[user.role]][key] = '';
        patch.add[API_ROLES[bulkRoleTarget]][key] = '';
      }
    });

    await executeAccessPatch(patch, `Roles updated for ${selectedLauis.length} users`);
    setBulkRoleTarget('');
  };

  const handleBulkDelete = async () => {
    if (selectedLauis.length === 0) return;
    const patch = createEmptyPatch();

    selectedLauis.forEach((laui) => {
      const user = flattenedUsers.find((u) => u.laui === laui);
      if (user) {
        const key = formatLauiKey(laui);
        patch.remove[API_ROLES[user.role]][key] = '';
      }
    });

    await executeAccessPatch(patch, `Removed ${selectedLauis.length} users from group`);
  };

  // --- ADD MULTIPLE (MODAL) ---
  const handleAddMultiple = async () => {
    if (queuedUsers.length === 0) return;
    const patch = createEmptyPatch();
    queuedUsers.forEach((u) => {
      const key = formatLauiKey(u.laui || u.id);
      patch.add[API_ROLES[modalTargetRole]][key] = '';
    });

    await executeAccessPatch(patch, `Added ${queuedUsers.length} user(s) as ${modalTargetRole}`);
    setQueuedUsers([]);
    setIsAddModalOpen(false);
  };

  // --- DESCRIPTION UPDATE ---
  const handleSaveDescription = async () => {
    if (!groupData) return;
    try {
      setSaving(true);
      await update_group(groupData.name, descriptionValue, createEmptyPatch());
      setIsEditingDesc(false);
      showSuccess('Description updated');
      await loadGroupData();
    } catch {
      /* ignore */
    } finally {
      setSaving(false);
    }
  };

  // --- BASE FLATTENING ---
  const flattenedUsers = useMemo<BaseUser[]>(() => {
    if (!groupData) return [];
    const allUsers: BaseUser[] = [];

    const pushLauis = (lauis: string[], role: InternalRole) => {
      lauis.forEach((laui) => allUsers.push({ laui, role }));
    };

    pushLauis(groupData.members || [], 'members');
    pushLauis(groupData.admins || [], 'admins');
    pushLauis(groupData.owners || [], 'owners');

    return allUsers;
  }, [groupData]);

  // --- FILTERING UTILIZING GLOBAL CACHE ---
  const filteredUsers = useMemo(() => {
    let result = flattenedUsers;

    if (roleFilter !== 'all') {
      result = result.filter((u) => u.role === roleFilter);
    }

    if (searchQuery.trim()) {
      const lowerQuery = searchQuery.toLowerCase();
      result = result.filter((u) => {
        const cached = userCache[u.laui];
        return (
          u.laui.toLowerCase().includes(lowerQuery) ||
          (cached?.username && cached.username.toLowerCase().includes(lowerQuery)) ||
          (cached?.email && cached.email.toLowerCase().includes(lowerQuery))
        );
      });
    }

    return result;
  }, [flattenedUsers, roleFilter, searchQuery, userCache]);

  // --- PAGINATION & CONTEXT FETCHING ---
  const paginatedUsersBase = useMemo(() => {
    const startIndex = page * rowsPerPage;
    return filteredUsers.slice(startIndex, startIndex + rowsPerPage);
  }, [filteredUsers, page, rowsPerPage]);

  const paginatedLauis = useMemo(() => paginatedUsersBase.map((u) => u.laui), [paginatedUsersBase]);

  // Request the current page's user details from the cache/API
  const paginatedUserDetails = useUsers(paginatedLauis.map((u) => u.substring(1)));

  // Merge the base role data with the enriched context data for the view
  const displayUsers = useMemo(() => {
    return paginatedUsersBase.map((baseUser, idx) => ({
      ...baseUser,
      details: paginatedUserDetails[idx],
    }));
  }, [paginatedUsersBase, paginatedUserDetails]);

  const handleChangePage = (_event: unknown, newPage: number) => setPage(newPage);
  const handleChangeRowsPerPage = (event: React.ChangeEvent<HTMLInputElement>) => {
    setRowsPerPage(parseInt(event.target.value, 10));
    setPage(0);
  };

  // --- CHECKBOX LOGIC ---
  const handleSelectAll = (event: React.ChangeEvent<HTMLInputElement>) => {
    if (event.target.checked) setSelectedLauis(filteredUsers.map((u) => u.laui));
    else setSelectedLauis([]);
  };

  const handleSelectOne = (laui: string) => {
    if (selectedLauis.includes(laui)) setSelectedLauis(selectedLauis.filter((id) => id !== laui));
    else setSelectedLauis([...selectedLauis, laui]);
  };

  if (loading && !groupData) {
    return (
      <Box sx={styles.container}>
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100%',
          }}
        >
          <CircularProgress sx={{ color: 'var(--accent)' }} />
        </Box>
      </Box>
    );
  }

  if (!groupData)
    return <Typography sx={styles.emptyText}>Failed to load group dataset</Typography>;

  return (
    <Box sx={styles.container}>
      {/* Header */}
      <Box sx={styles.header}>
        <IconButton onClick={onBack} sx={styles.backButton}>
          <BackIcon />
        </IconButton>
        <Box sx={{ flex: 1 }}>
          <Typography
            variant="h5"
            sx={{ fontWeight: FONT_WEIGHTS.BOLD, color: 'var(--text-primary)' }}
          >
            {groupData.name}
          </Typography>
          <Typography
            variant="body2"
            sx={{
              color: 'var(--text-secondary)',
              fontFamily: 'monospace',
              fontSize: FONT_SIZES.XS,
              mt: 0.5,
            }}
          >
            {groupData.laui || groupLaui}
          </Typography>
        </Box>
      </Box>

      {/* Description Section */}
      <Box sx={styles.section}>
        <Box sx={styles.sectionHeader}>
          <Typography sx={styles.sectionTitle}>Description</Typography>
          {!isEditingDesc && canEdit && (
            <IconButton
              size="small"
              onClick={() => setIsEditingDesc(true)}
              sx={{ color: 'var(--text-primary)' }}
            >
              <EditIcon fontSize="small" />
            </IconButton>
          )}
        </Box>
        {isEditingDesc ? (
          <Box sx={{ display: 'flex', gap: 2, alignItems: 'flex-start' }}>
            <TextField
              fullWidth
              multiline
              rows={3}
              value={descriptionValue}
              onChange={(e) => setDescriptionValue(e.target.value)}
              disabled={saving}
              sx={{
                '& .MuiOutlinedInput-root': {
                  bgcolor: 'var(--bg-tertiary)',
                  color: 'var(--text-primary)',
                },
              }}
            />
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1 }}>
              <Button
                size="small"
                variant="contained"
                onClick={() => void handleSaveDescription()}
                disabled={saving}
                sx={styles.button}
              >
                Save
              </Button>
              <Button
                size="small"
                variant="outlined"
                onClick={() => setIsEditingDesc(false)}
                disabled={saving}
                sx={styles.cancelButton}
              >
                Cancel
              </Button>
            </Box>
          </Box>
        ) : (
          <Typography
            sx={{
              color: 'var(--text-primary)',
              fontSize: FONT_SIZES.SM,
              whiteSpace: 'pre-wrap',
            }}
          >
            {groupData.description || (
              <span style={{ fontStyle: 'italic', color: 'var(--text-secondary)' }}>
                No description available
              </span>
            )}
          </Typography>
        )}
      </Box>

      {/* Roster Management Section */}
      <Box sx={styles.section}>
        {/* Dynamic Toolbar */}
        {selectedLauis.length > 0 && canEdit ? (
          <Box sx={styles.bulkToolbar}>
            <Typography
              sx={{
                color: '#1976d2',
                fontWeight: FONT_WEIGHTS.MEDIUM,
                fontSize: FONT_SIZES.SM,
              }}
            >
              {selectedLauis.length} user(s) selected
            </Typography>
            <Box sx={{ display: 'flex', gap: 2, alignItems: 'center' }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <FormControl size="small" sx={{ minWidth: 150 }}>
                  <Select
                    displayEmpty
                    value={bulkRoleTarget}
                    onChange={(e) => setBulkRoleTarget(e.target.value as any)}
                    sx={{
                      bgcolor: 'var(--bg-primary)',
                      color: 'var(--text-primary)',
                      fontSize: FONT_SIZES.SM,
                    }}
                  >
                    <MenuItem value="" disabled>
                      Assign new role...
                    </MenuItem>
                    <MenuItem value="members">Members (Viewers)</MenuItem>
                    <MenuItem value="admins">Admins (Editors)</MenuItem>
                    {canEditOwners && <MenuItem value="owners">Owners</MenuItem>}
                  </Select>
                </FormControl>
                <Button
                  variant="contained"
                  size="small"
                  onClick={() => void handleBulkRoleChange()}
                  disabled={saving || !bulkRoleTarget}
                  sx={styles.button}
                >
                  Apply
                </Button>
              </Box>

              <Button
                variant="outlined"
                color="error"
                size="small"
                startIcon={<DeleteIcon />}
                onClick={() => void handleBulkDelete()}
                disabled={saving}
                sx={{ bgcolor: 'var(--bg-primary)' }}
              >
                Remove Selected
              </Button>
            </Box>
          </Box>
        ) : (
          <Box sx={styles.controlsRow}>
            {/* Search Input */}
            <TextField
              size="small"
              placeholder="Search user or ID..."
              value={searchQuery}
              onChange={(e) => {
                setSearchQuery(e.target.value);
                setPage(0);
              }}
              InputProps={{
                startAdornment: (
                  <InputAdornment position="start">
                    <SearchIcon fontSize="small" sx={{ color: 'var(--text-secondary)' }} />
                  </InputAdornment>
                ),
              }}
              sx={{
                minWidth: 250,
                '& .MuiOutlinedInput-root': {
                  bgcolor: 'var(--bg-tertiary)',
                  color: 'var(--text-primary)',
                },
              }}
            />

            <Box sx={{ display: 'flex', alignItems: 'center', gap: 2 }}>
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
                <FilterIcon sx={{ color: 'var(--text-secondary)' }} fontSize="small" />
                <FormControl variant="standard" sx={{ minWidth: 150 }}>
                  <Select
                    value={roleFilter}
                    onChange={(e) => {
                      setRoleFilter(e.target.value as any);
                      setPage(0);
                    }}
                    sx={{
                      color: 'var(--text-primary)',
                      fontSize: FONT_SIZES.SM,
                    }}
                  >
                    <MenuItem value="all">All Roles</MenuItem>
                    <MenuItem value="members">Members</MenuItem>
                    <MenuItem value="admins">Admins</MenuItem>
                    <MenuItem value="owners">Owners</MenuItem>
                  </Select>
                </FormControl>
              </Box>

              {canEdit && (
                <Button
                  variant="contained"
                  sx={styles.button}
                  startIcon={<AddIcon />}
                  onClick={() => setIsAddModalOpen(true)}
                >
                  Add Users
                </Button>
              )}
            </Box>
          </Box>
        )}

        {/* Data Table */}
        <TableContainer component={Paper} sx={styles.tableContainer}>
          <Table aria-label="group elements table" size="small">
            <TableHead>
              <TableRow>
                {canEdit && (
                  <TableCell padding="checkbox">
                    <Checkbox
                      size="small"
                      checked={
                        filteredUsers.length > 0 && selectedLauis.length === filteredUsers.length
                      }
                      indeterminate={
                        selectedLauis.length > 0 && selectedLauis.length < filteredUsers.length
                      }
                      onChange={handleSelectAll}
                      sx={{
                        color: 'var(--text-secondary)',
                        '&.Mui-checked, &.MuiCheckbox-indeterminate': {
                          color: 'var(--accent)',
                        },
                      }}
                    />
                  </TableCell>
                )}
                <TableCell>Username</TableCell>
                <TableCell>Email</TableCell>
                <TableCell>Role Assignment</TableCell>
                {canEdit && <TableCell align="right">Actions</TableCell>}
              </TableRow>
            </TableHead>
            <TableBody>
              {displayUsers.length > 0 ? (
                displayUsers.map(({ laui, role, details }) => {
                  const isOwnerRow = role === 'owners';
                  const disableRowActions = saving || !canEdit || (isOwnerRow && !canEditOwners);
                  const isSelected = selectedLauis.includes(laui);

                  return (
                    <TableRow key={laui} hover selected={isSelected}>
                      {canEdit && (
                        <TableCell padding="checkbox">
                          <Checkbox
                            size="small"
                            checked={isSelected}
                            onChange={() => handleSelectOne(laui)}
                            disabled={disableRowActions}
                            sx={{
                              color: 'var(--text-secondary)',
                              '&.Mui-checked': {
                                color: 'var(--accent)',
                              },
                            }}
                          />
                        </TableCell>
                      )}
                      <TableCell>
                        {!details.isLoading ? (
                          <Box
                            sx={{
                              display: 'flex',
                              flexDirection: 'column',
                            }}
                          >
                            <Typography
                              sx={{
                                fontSize: FONT_SIZES.SM,
                                fontWeight: FONT_WEIGHTS.MEDIUM,
                                color: 'var(--text-primary)',
                              }}
                            >
                              {details.username}
                            </Typography>
                          </Box>
                        ) : (
                          <CircularProgress size={16} sx={{ color: 'var(--text-secondary)' }} />
                        )}
                      </TableCell>
                      <TableCell sx={{ fontSize: FONT_SIZES.SM }}>
                        {!details.isLoading ? (
                          details.email
                        ) : (
                          <CircularProgress size={16} sx={{ color: 'var(--text-secondary)' }} />
                        )}
                      </TableCell>
                      <TableCell>
                        <FormControl variant="standard" sx={{ minWidth: 140 }}>
                          <Select
                            value={role}
                            disabled={disableRowActions}
                            onChange={(e) =>
                              void handleRoleChangeSingle(laui, role, e.target.value as any)
                            }
                            sx={{
                              color: 'var(--text-primary)',
                              fontSize: FONT_SIZES.SM,
                              '& .MuiSvgIcon-root': {
                                color: 'var(--text-secondary)',
                              },
                              '&:before': {
                                borderBottomColor: 'transparent',
                              },
                            }}
                          >
                            <MenuItem value="members">Member</MenuItem>
                            <MenuItem value="admins">Admin</MenuItem>
                            <MenuItem value="owners" disabled={!canEditOwners}>
                              Owner
                            </MenuItem>
                          </Select>
                        </FormControl>
                      </TableCell>
                      {canEdit && (
                        <TableCell align="right">
                          <Tooltip title="Remove User">
                            <span>
                              <IconButton
                                onClick={() => void handleDeleteSingle(laui, role)}
                                disabled={disableRowActions}
                                size="small"
                                sx={{
                                  color: 'var(--text-secondary)',
                                  '&:hover': {
                                    color: 'var(--error)',
                                  },
                                }}
                              >
                                <DeleteIcon fontSize="small" />
                              </IconButton>
                            </span>
                          </Tooltip>
                        </TableCell>
                      )}
                    </TableRow>
                  );
                })
              ) : (
                <TableRow>
                  <TableCell colSpan={canEdit ? 5 : 4} align="center" sx={{ py: 4 }}>
                    <Typography sx={styles.emptyText}>No users matched your criteria.</Typography>
                  </TableCell>
                </TableRow>
              )}
            </TableBody>
          </Table>
        </TableContainer>

        <TablePagination
          rowsPerPageOptions={[5, 10, 25]}
          component="div"
          count={filteredUsers.length}
          rowsPerPage={rowsPerPage}
          page={page}
          onPageChange={handleChangePage}
          onRowsPerPageChange={handleChangeRowsPerPage}
          sx={styles.pagination}
        />
      </Box>

      {/* Add Users Modal */}
      <Dialog
        open={isAddModalOpen}
        onClose={() => !saving && setIsAddModalOpen(false)}
        maxWidth="md"
        fullWidth
        PaperProps={{ sx: { bgcolor: 'var(--bg-primary)', color: 'var(--text-primary)' } }}
      >
        <DialogTitle
          sx={{ display: 'flex', justifyContent: 'space-between', alignItems: 'center' }}
        >
          Add Users to Group
          <IconButton
            onClick={() => setIsAddModalOpen(false)}
            disabled={saving}
            size="small"
            sx={{ color: 'var(--text-primary)' }}
          >
            <CloseIcon />
          </IconButton>
        </DialogTitle>
        <DialogContent dividers sx={{ borderColor: 'var(--border)' }}>
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, py: 1 }}>
            <Box>
              <Typography
                sx={{
                  fontSize: FONT_SIZES.SM,
                  fontWeight: FONT_WEIGHTS.MEDIUM,
                  mb: 1,
                }}
              >
                1. Select Target Role
              </Typography>
              <FormControl fullWidth size="small">
                <Select
                  value={modalTargetRole}
                  onChange={(e) => setModalTargetRole(e.target.value as any)}
                  disabled={saving}
                  sx={{
                    bgcolor: 'var(--bg-tertiary)',
                    color: 'var(--text-primary)',
                  }}
                >
                  <MenuItem value="members">Members</MenuItem>
                  <MenuItem value="admins">Admins</MenuItem>
                  {canEditOwners && <MenuItem value="owners">Owners</MenuItem>}
                </Select>
              </FormControl>
            </Box>
            <Box>
              <Typography
                sx={{
                  fontSize: FONT_SIZES.SM,
                  fontWeight: FONT_WEIGHTS.MEDIUM,
                  mb: 1,
                }}
              >
                2. Search and Queue Users
              </Typography>
              <UserSearch
                existingUserIds={flattenedUsers.map((u) => u.laui)}
                queuedUsers={queuedUsers}
                onQueueUser={(u) => setQueuedUsers([...queuedUsers, u])}
                onRemoveQueuedUser={(id) =>
                  setQueuedUsers(queuedUsers.filter((u) => (u.id || u.laui) !== id))
                }
              />
            </Box>
          </Box>
        </DialogContent>
        <DialogActions sx={{ p: 2, borderColor: 'var(--border)' }}>
          <Button
            variant="outlined"
            onClick={() => setIsAddModalOpen(false)}
            disabled={saving}
            sx={styles.cancelButton}
          >
            Cancel
          </Button>
          <Button
            variant="contained"
            onClick={() => void handleAddMultiple()}
            disabled={saving || queuedUsers.length === 0}
            sx={styles.button}
            startIcon={saving ? <CircularProgress size={16} /> : <SaveIcon />}
          >
            Apply Role Assignment
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
}
