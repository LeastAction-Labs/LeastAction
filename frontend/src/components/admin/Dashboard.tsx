/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useMemo, useState } from 'react';

import AddIcon from '@mui/icons-material/Add';
import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import CancelIcon from '@mui/icons-material/Cancel';
import CheckIcon from '@mui/icons-material/Check';
import ContentCopyIcon from '@mui/icons-material/ContentCopy';
import DeleteIcon from '@mui/icons-material/Delete';
import EditIcon from '@mui/icons-material/Edit';
import SaveIcon from '@mui/icons-material/Save';
import SearchIcon from '@mui/icons-material/Search';
import {
  Box,
  Button,
  Checkbox,
  Chip,
  CircularProgress,
  ClickAwayListener,
  Divider,
  FormControlLabel,
  FormGroup,
  IconButton,
  InputAdornment,
  Paper,
  Stack,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TablePagination,
  TableRow,
  Tabs,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';

import { useAuth } from '@/contexts/AuthContext';
import { useMarketplace } from '@/contexts/MarketplaceContext';
import { useNotification } from '@/contexts/NotificationContext';
import { useUserCache, useUsers } from '@/contexts/UserCacheContext';
import { searchCatalogItems } from '@/services';
import {
  type UserRecord,
  getMcpToolGroups,
  type McpToolGroups,
  getLicenseByLaui,
  getLicenses,
  listUsers,
  updateLicense,
  updateUserMcpTools,
  uploadLicense,
} from '@/services/admin.service';
import { buyLicense } from '@/services/marketplace.service';
import { formatDateTime } from '@/utils/timeFormat';

import { BaseModal } from '../ui';
import UserSearch from '../users/UserSearch';
import ManageUsers from './ManageUsers';

type UserListAction = 'add' | 'remove';

//TODO : licenses pagination , sorting , quick search , delete licenses

export default function AdminDashboard() {
  const { authState } = useAuth();
  const { systemUserLaui } = authState;
  const { userAuthenticated: _userLoggedInToMarketplace } = useMarketplace();

  const { showWarning } = useNotification();

  // Access global user cache for local filtering
  const { userCache } = useUserCache();

  const [licenses, setLicenses] = useState<any[]>([]);

  // View state
  const [selectedLicense, setSelectedLicense] = useState<any>(null);

  // Edit users_list state
  const [editingUsers, setEditingUsers] = useState(false);
  const [selectedTableUsers, setSelectedTableUsers] = useState<string[]>([]);
  const [queuedUsersToAdd, setQueuedUsersToAdd] = useState<any[]>([]);

  // License User Table State (Pagination & Search)
  const [licenseUserPage, setLicenseUserPage] = useState(0);
  const [licenseUserRowsPerPage, setLicenseUserRowsPerPage] = useState(5);
  const [licenseUserSearchQuery, setLicenseUserSearchQuery] = useState('');

  // Buy / Upload
  const [buyOpen, setBuyOpen] = useState(false);
  const [uploadOpen, setUploadOpen] = useState(false);

  const [users, setUsers] = useState(1);
  const [duration, setDuration] = useState(1);

  const [licenseId, setLicenseId] = useState('');
  const [publicKey, setPublicKey] = useState('');

  const [copied, setCopied] = useState(false);

  // MCP Tools tab
  const [activeTab, setActiveTab] = useState(0);
  const [userList, setUserList] = useState<UserRecord[]>([]);
  const [allMcpTools, setAllMcpTools] = useState<string[]>([]);
  const [mcpToolGroups, setMcpToolGroups] = useState<McpToolGroups>({});
  const [editingUser, setEditingUser] = useState<UserRecord | null>(null);
  const [editingTools, setEditingTools] = useState<string[]>([]);

  // Chat config editing
  const [editingChatAgentLaui, setEditingChatAgentLaui] = useState('');
  const [editingChatAgentName, setEditingChatAgentName] = useState('');
  const [editingChatConnLaui, setEditingChatConnLaui] = useState('');
  const [editingChatConnName, setEditingChatConnName] = useState('');
  const [agentQuery, setAgentQuery] = useState('');
  const [agentResults, setAgentResults] = useState<any[]>([]);
  const [agentDropdownOpen, setAgentDropdownOpen] = useState(false);
  const [connQuery, setConnQuery] = useState('');
  const [connResults, setConnResults] = useState<any[]>([]);
  const [connDropdownOpen, setConnDropdownOpen] = useState(false);

  const handleCopy = async () => {
    try {
      if (!systemUserLaui) return;
      await navigator.clipboard.writeText(systemUserLaui);
      setCopied(true);
      setTimeout(() => setCopied(false), 2000);
    } catch (err) {
      console.error('Failed to copy!', err);
    }
  };

  useEffect(() => {
    void fetchLicenses();
    void fetchUsers();
    void fetchAllMcpToolsList();
  }, []);

  const fetchLicenses = async () => {
    const data = await getLicenses();
    setLicenses(data);
  };

  const fetchUsers = async () => {
    const data: any = await listUsers(1, 10);
    console.log(data);
    console.log(data.users);
    setUserList(data.users);
  };

  const fetchAllMcpToolsList = async () => {
    const { tools, groups } = await getMcpToolGroups();
    setAllMcpTools(tools);
    setMcpToolGroups(groups);
  };

  const handleOpenEditTools = (user: UserRecord) => {
    setEditingUser(user);
    setEditingTools(user.allowed_mcp_tools ?? allMcpTools);
    setEditingChatAgentLaui(user.chat_agent_laui ?? '');
    setEditingChatAgentName(user.chat_agent_name ?? '');
    setEditingChatConnLaui(user.chat_connection_laui ?? '');
    setEditingChatConnName('');
    setAgentQuery('');
    setConnQuery('');
    setAgentResults([]);
    setConnResults([]);
  };

  const searchAgents = async (q: string) => {
    const res = await searchCatalogItems('agent', false, { perPage: 10 });
    const items = (res?.items ?? []).map((raw: any) => {
      const item = raw.item || raw;
      return { laui: item._laui || item.laui, name: item.name || 'Unnamed' };
    });
    setAgentResults(
      q.trim() ? items.filter((i: any) => i.name.toLowerCase().includes(q.toLowerCase())) : items,
    );
  };

  const searchConns = async (q: string) => {
    const res = await searchCatalogItems('connection', false, { perPage: 10 });
    const items = (res?.items ?? []).map((raw: any) => {
      const item = raw.item || raw;
      return { laui: item._laui || item.laui, name: item.name || 'Unnamed' };
    });
    setConnResults(
      q.trim() ? items.filter((i: any) => i.name.toLowerCase().includes(q.toLowerCase())) : items,
    );
  };

  const handleToggleTool = (tool: string) => {
    setEditingTools((prev) =>
      prev.includes(tool) ? prev.filter((t) => t !== tool) : [...prev, tool],
    );
  };

  const handleToggleGroup = (groupTools: string[], enable: boolean) => {
    setEditingTools((prev) =>
      enable
        ? Array.from(new Set([...prev, ...groupTools]))
        : prev.filter((t) => !groupTools.includes(t)),
    );
  };

  const handleSaveMcpTools = async () => {
    if (!editingUser) return;
    const isAll = editingTools.length === allMcpTools.length;
    await updateUserMcpTools(
      editingUser.laui,
      isAll ? null : editingTools,
      editingChatAgentLaui || null,
      editingChatConnLaui || null,
      editingChatAgentName || null,
    );
    await fetchUsers();
    setEditingUser(null);
  };

  const handleRowClick = async (laui: string) => {
    const data: any = await getLicenseByLaui(laui);
    setSelectedLicense(data);
    setEditingUsers(false);
    setSelectedTableUsers([]);
    setQueuedUsersToAdd([]);
    setLicenseUserPage(0);
    setLicenseUserSearchQuery('');
  };

  const executeLicenseUpdatePayload = async (action: UserListAction, userIds: string[]) => {
    const payload: any = {
      laui: selectedLicense.laui,
      user_list_patch: {
        [action]: userIds,
      },
    };

    await updateLicense(payload);
    const updatedData = await getLicenseByLaui(selectedLicense.laui);
    setSelectedLicense(updatedData);
    setSelectedTableUsers([]);
    setQueuedUsersToAdd([]);
  };

  const handleAddQueuedUsersSubmit = async () => {
    const userIds = queuedUsersToAdd.map((u) => u.id);
    if (userIds.length === 0) return;

    const maxSeats =
      selectedLicense.tier === 'free'
        ? selectedLicense.trial_seats
        : selectedLicense.permanent_seats;
    const currentCount = selectedLicense.user_list?.length || 0;

    if (currentCount + userIds.length > maxSeats) {
      showWarning(`Cannot add users. Maximum capacity is ${maxSeats} seats.`);
      return;
    }

    await executeLicenseUpdatePayload('add', userIds);
    setEditingUsers(false);
  };

  const handleBatchRemoveUsers = async () => {
    if (selectedTableUsers.length === 0) return;
    await executeLicenseUpdatePayload('remove', selectedTableUsers);
  };

  const handleSingleRemoveUser = async (userId: string) => {
    await executeLicenseUpdatePayload('remove', [userId]);
  };

  const handleCancelEdit = () => {
    setEditingUsers(false);
    setQueuedUsersToAdd([]);
  };

  const handleBuy = async () => {
    try {
      if (!systemUserLaui) return;
      const res = await buyLicense({
        total_users: users,
        duration,
        instance_id: systemUserLaui,
      });
      setLicenseId(res.license_id);
      setPublicKey(res.public_key);
    } catch {
      // intentional
    }
  };

  const handleUpload = async () => {
    await uploadLicense({ licenseId, publicKey });
    setUploadOpen(false);
    await fetchLicenses();
  };

  // --- License User Table Logic (Search, Pagination, Context Fetching) ---
  const filteredLicenseUsers = useMemo(() => {
    if (!selectedLicense?.user_list) return [];
    let result = selectedLicense.user_list as string[];

    if (licenseUserSearchQuery.trim()) {
      const lowerQuery = licenseUserSearchQuery.toLowerCase();
      result = result.filter((laui) => {
        const cached = userCache[laui];
        return (
          laui.toLowerCase().includes(lowerQuery) ||
          (cached?.username && cached.username.toLowerCase().includes(lowerQuery)) ||
          (cached?.email && cached.email.toLowerCase().includes(lowerQuery))
        );
      });
    }
    return result;
  }, [selectedLicense?.user_list, licenseUserSearchQuery, userCache]);

  const paginatedLauis = useMemo(() => {
    const startIndex = licenseUserPage * licenseUserRowsPerPage;
    return filteredLicenseUsers.slice(startIndex, startIndex + licenseUserRowsPerPage);
  }, [filteredLicenseUsers, licenseUserPage, licenseUserRowsPerPage]);

  // Use our new context hook to resolve the current page's LAUIs into rich objects
  const paginatedUserDetails = useUsers(paginatedLauis);

  const handleSelectAllTableUsers = (checked: boolean) => {
    if (checked) {
      setSelectedTableUsers(filteredLicenseUsers);
    } else {
      setSelectedTableUsers([]);
    }
  };

  const handleSelectTableUserRow = (userId: string, checked: boolean) => {
    if (checked) {
      setSelectedTableUsers([...selectedTableUsers, userId]);
    } else {
      setSelectedTableUsers(selectedTableUsers.filter((id) => id !== userId));
    }
  };

  // ================= DETAIL VIEW =================
  if (selectedLicense) {
    const maxSeats =
      selectedLicense.tier === 'free'
        ? selectedLicense.trial_seats
        : selectedLicense.permanent_seats;
    const currentSeats = selectedLicense.user_list?.length || 0;

    return (
      <Box p={3} sx={{ bgcolor: 'var(--bg-primary)', minHeight: '100%' }}>
        {/* HEADER */}
        <Stack direction="row" alignItems="center" justifyContent="space-between" mb={3}>
          <Stack direction="row" alignItems="center" spacing={1}>
            <IconButton
              onClick={() => setSelectedLicense(null)}
              sx={{
                color: 'var(--text-primary)',
                bgcolor: 'var(--bg-secondary)',
                '&:hover': { bgcolor: 'var(--bg-tertiary)' },
              }}
            >
              <ArrowBackIcon />
            </IconButton>

            <Typography variant="h5" fontWeight={600} sx={{ color: 'var(--text-primary)' }}>
              License Details
            </Typography>
          </Stack>

          <Chip
            label={`${currentSeats} / ${maxSeats} seats used`}
            sx={{
              bgcolor: currentSeats >= maxSeats ? 'var(--accent)' : 'var(--bg-secondary)',
              color: 'var(--text-primary)',
              fontWeight: 600,
            }}
          />
        </Stack>

        {/* MAIN CONTENT - FULL WIDTH */}
        <Box
          sx={{
            bgcolor: 'var(--bg-secondary)',
            border: '1px solid',
            borderColor: 'var(--border)',
            borderRadius: 2,
            p: 3,
          }}
        >
          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' },
              gap: 3,
            }}
          >
            {/* License ID */}
            <Box>
              <Typography variant="subtitle2" sx={{ color: 'var(--text-secondary)' }} mb={1}>
                License ID
              </Typography>
              <Typography fontFamily="monospace" sx={{ color: 'var(--text-primary)' }}>
                ...{selectedLicense.license_id?.slice(-20)}
              </Typography>
            </Box>

            {/* LAUI */}
            <Box>
              <Typography variant="subtitle2" sx={{ color: 'var(--text-secondary)' }} mb={1}>
                LAUI
              </Typography>
              <Typography fontFamily="monospace" sx={{ color: 'var(--text-primary)' }}>
                {selectedLicense.laui}
              </Typography>
            </Box>
          </Box>

          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', md: 'repeat(4, 1fr)' },
              gap: 3,
              mt: 3,
            }}
          >
            {/* Tier */}
            <Box>
              <Typography variant="subtitle2" sx={{ color: 'var(--text-secondary)' }} mb={1}>
                Tier
              </Typography>
              <Chip
                label={selectedLicense.tier?.toUpperCase()}
                size="small"
                sx={{
                  bgcolor: 'var(--bg-tertiary)',
                  color: 'var(--text-primary)',
                  fontWeight: 600,
                }}
              />
            </Box>

            {/* Status */}
            <Box>
              <Typography variant="subtitle2" sx={{ color: 'var(--text-secondary)' }} mb={1}>
                Status
              </Typography>
              <Chip
                label={selectedLicense.status?.toUpperCase()}
                size="small"
                sx={{
                  bgcolor: selectedLicense.status === 'active' ? 'green' : 'var(--accent)',
                  color: 'white',
                  fontWeight: 600,
                }}
              />
            </Box>

            {/* Permanent Seats */}
            <Box>
              <Typography variant="subtitle2" sx={{ color: 'var(--text-secondary)' }} mb={1}>
                Permanent Seats
              </Typography>
              <Typography sx={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                {selectedLicense.permanent_seats}
              </Typography>
            </Box>

            {/* Trial Seats */}
            <Box>
              <Typography variant="subtitle2" sx={{ color: 'var(--text-secondary)' }} mb={1}>
                Trial Seats
              </Typography>
              <Typography sx={{ color: 'var(--text-primary)', fontWeight: 600 }}>
                {selectedLicense.trial_seats}
              </Typography>
            </Box>
          </Box>

          <Box
            sx={{
              display: 'grid',
              gridTemplateColumns: { xs: '1fr', md: 'repeat(2, 1fr)' },
              gap: 3,
              mt: 3,
            }}
          >
            {/* User LAUI */}
            <Box>
              <Typography variant="subtitle2" sx={{ color: 'var(--text-secondary)' }} mb={1}>
                User LAUI
              </Typography>
              <Typography fontFamily="monospace" sx={{ color: 'var(--text-primary)' }}>
                {selectedLicense.instance_id}
              </Typography>
            </Box>

            {/* Expiry Date */}
            <Box>
              <Typography variant="subtitle2" sx={{ color: 'var(--text-secondary)' }} mb={1}>
                Expiry Date
              </Typography>
              <Typography sx={{ color: 'var(--text-primary)' }}>
                {formatDateTime(selectedLicense.expiry_date)}
              </Typography>
            </Box>

            {/* Trial Start Date */}
            <Box>
              <Typography variant="subtitle2" sx={{ color: 'var(--text-secondary)' }} mb={1}>
                Trial Start Date
              </Typography>
              <Typography sx={{ color: 'var(--text-primary)' }}>
                {formatDateTime(selectedLicense.trial_start_date)}
              </Typography>
            </Box>

            {/* Trial End Date */}
            <Box>
              <Typography variant="subtitle2" sx={{ color: 'var(--text-secondary)' }} mb={1}>
                Trial End Date
              </Typography>
              <Typography sx={{ color: 'var(--text-primary)' }}>
                {formatDateTime(selectedLicense.trial_end_date)}
              </Typography>
            </Box>

            {/* Created At */}
            <Box>
              <Typography variant="subtitle2" sx={{ color: 'var(--text-secondary)' }} mb={1}>
                Created At
              </Typography>
              <Typography sx={{ color: 'var(--text-primary)' }}>
                {formatDateTime(selectedLicense.created_at)}
              </Typography>
            </Box>

            {/* Updated At */}
            <Box>
              <Typography variant="subtitle2" sx={{ color: 'var(--text-secondary)' }} mb={1}>
                Updated At
              </Typography>
              <Typography sx={{ color: 'var(--text-primary)' }}>
                {formatDateTime(selectedLicense.updated_at)}
              </Typography>
            </Box>
          </Box>

          {/* MANAGED USERS SECTION */}
          <Box sx={{ mt: 4 }}>
            <Divider sx={{ borderColor: 'var(--border)', my: 2 }} />

            <Stack
              direction="row"
              alignItems="center"
              justifyContent="space-between"
              mb={2}
              flexWrap="wrap"
              gap={2}
            >
              <Box sx={{ display: 'flex', alignItems: 'center', gap: 3 }}>
                <Typography variant="h6" sx={{ color: 'var(--text-primary)' }}>
                  Assigned License Users
                </Typography>

                {/* Search Input for Table */}
                <TextField
                  size="small"
                  placeholder="Search user or ID..."
                  value={licenseUserSearchQuery}
                  onChange={(e) => {
                    setLicenseUserSearchQuery(e.target.value);
                    setLicenseUserPage(0);
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
                    '& .MuiOutlinedInput-notchedOutline': {
                      borderColor: 'var(--border)',
                    },
                  }}
                />
              </Box>

              {!editingUsers ? (
                <Stack direction="row" spacing={1}>
                  {selectedTableUsers.length > 0 && (
                    <Button
                      size="small"
                      variant="outlined"
                      color="error"
                      startIcon={<DeleteIcon />}
                      onClick={() => {
                        void handleBatchRemoveUsers();
                      }}
                      sx={{ textTransform: 'none' }}
                    >
                      Remove Selected ({selectedTableUsers.length})
                    </Button>
                  )}
                  <Button
                    size="small"
                    startIcon={<AddIcon />}
                    variant="contained"
                    onClick={() => setEditingUsers(true)}
                    sx={{
                      textTransform: 'none',
                      bgcolor: 'var(--accent)',
                      '&:hover': { bgcolor: 'var(--accent)', opacity: 0.9 },
                    }}
                  >
                    Add Users
                  </Button>
                </Stack>
              ) : (
                <Stack direction="row" spacing={1}>
                  <Button
                    size="small"
                    startIcon={<CancelIcon />}
                    onClick={handleCancelEdit}
                    sx={{
                      textTransform: 'none',
                      color: 'var(--text-primary)',
                      '&:hover': { bgcolor: 'var(--bg-tertiary)' },
                    }}
                  >
                    Cancel
                  </Button>
                  <Button
                    size="small"
                    variant="contained"
                    startIcon={<SaveIcon />}
                    disabled={queuedUsersToAdd.length === 0}
                    onClick={() => {
                      void handleAddQueuedUsersSubmit();
                    }}
                    sx={{
                      textTransform: 'none',
                      bgcolor: 'var(--accent)',
                      '&:hover': { bgcolor: 'var(--accent)', opacity: 0.8 },
                    }}
                  >
                    Confirm & Add ({queuedUsersToAdd.length})
                  </Button>
                </Stack>
              )}
            </Stack>

            {/* DYNAMIC SEARCH COMPONENT INJECTED HERE */}
            {editingUsers && (
              <UserSearch
                existingUserIds={selectedLicense.user_list || []}
                queuedUsers={queuedUsersToAdd}
                onQueueUser={(user) => setQueuedUsersToAdd([...queuedUsersToAdd, user])}
                onRemoveQueuedUser={(id) =>
                  setQueuedUsersToAdd(queuedUsersToAdd.filter((u) => u.id !== id))
                }
              />
            )}

            {/* BASE CURRENT SEATS DATA TABLE */}
            <TableContainer
              component={Paper}
              sx={{
                bgcolor: 'var(--bg-tertiary)',
                border: '1px solid var(--border)',
              }}
            >
              <Table size="small">
                <TableHead>
                  <TableRow sx={{ bgcolor: 'var(--bg-secondary)' }}>
                    <TableCell padding="checkbox" sx={{ borderColor: 'var(--border)' }}>
                      <Checkbox
                        size="small"
                        disabled={editingUsers || filteredLicenseUsers.length === 0}
                        checked={
                          filteredLicenseUsers.length > 0 &&
                          selectedTableUsers.length === filteredLicenseUsers.length
                        }
                        indeterminate={
                          selectedTableUsers.length > 0 &&
                          selectedTableUsers.length < filteredLicenseUsers.length
                        }
                        onChange={(e) => handleSelectAllTableUsers(e.target.checked)}
                        sx={{
                          color: 'var(--text-secondary)',
                          '&.Mui-checked, &.MuiCheckbox-indeterminate': {
                            color: 'var(--accent)',
                          },
                        }}
                      />
                    </TableCell>
                    <TableCell
                      sx={{
                        color: 'var(--text-primary)',
                        borderColor: 'var(--border)',
                        fontWeight: 600,
                      }}
                    >
                      Username
                    </TableCell>
                    <TableCell
                      sx={{
                        color: 'var(--text-primary)',
                        borderColor: 'var(--border)',
                        fontWeight: 600,
                      }}
                    >
                      Email
                    </TableCell>
                    <TableCell
                      align="right"
                      sx={{
                        color: 'var(--text-primary)',
                        borderColor: 'var(--border)',
                        fontWeight: 600,
                      }}
                    >
                      Actions
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {paginatedUserDetails.length > 0 ? (
                    paginatedUserDetails.map((user) => {
                      const isRowChecked = selectedTableUsers.includes(user.laui);

                      return (
                        <TableRow
                          key={user.laui}
                          sx={{
                            '&:hover': {
                              bgcolor: 'var(--bg-secondary)',
                            },
                          }}
                        >
                          <TableCell padding="checkbox" sx={{ borderColor: 'var(--border)' }}>
                            <Checkbox
                              size="small"
                              disabled={editingUsers}
                              checked={isRowChecked}
                              onChange={(e) =>
                                handleSelectTableUserRow(user.laui, e.target.checked)
                              }
                              sx={{
                                color: 'var(--text-secondary)',
                                '&.Mui-checked': {
                                  color: 'var(--accent)',
                                },
                              }}
                            />
                          </TableCell>
                          <TableCell sx={{ borderColor: 'var(--border)' }}>
                            {!user.isLoading ? (
                              <Box
                                sx={{
                                  display: 'flex',
                                  flexDirection: 'column',
                                }}
                              >
                                <Typography
                                  sx={{
                                    fontSize: 14,
                                    fontWeight: 500,
                                    color: 'var(--text-primary)',
                                  }}
                                >
                                  {user.username}
                                </Typography>
                              </Box>
                            ) : (
                              <CircularProgress
                                size={16}
                                sx={{
                                  color: 'var(--text-secondary)',
                                }}
                              />
                            )}
                          </TableCell>
                          <TableCell
                            sx={{
                              color: 'var(--text-secondary)',
                              borderColor: 'var(--border)',
                              fontSize: 14,
                            }}
                          >
                            {!user.isLoading ? (
                              user.email
                            ) : (
                              <CircularProgress
                                size={16}
                                sx={{
                                  color: 'var(--text-secondary)',
                                }}
                              />
                            )}
                          </TableCell>
                          <TableCell align="right" sx={{ borderColor: 'var(--border)' }}>
                            <IconButton
                              size="small"
                              color="error"
                              disabled={editingUsers}
                              onClick={() => {
                                void handleSingleRemoveUser(user.laui);
                              }}
                              title="Delete user"
                              sx={{
                                '&:hover': {
                                  color: 'var(--error)',
                                },
                              }}
                            >
                              <DeleteIcon fontSize="small" />
                            </IconButton>
                          </TableCell>
                        </TableRow>
                      );
                    })
                  ) : (
                    <TableRow>
                      <TableCell
                        colSpan={4}
                        align="center"
                        sx={{ py: 4, borderColor: 'var(--border)' }}
                      >
                        <Typography
                          sx={{
                            color: 'var(--text-secondary)',
                            fontStyle: 'italic',
                          }}
                        >
                          No users found matching your criteria.
                        </Typography>
                      </TableCell>
                    </TableRow>
                  )}
                </TableBody>
              </Table>
            </TableContainer>

            <TablePagination
              rowsPerPageOptions={[5, 10, 25]}
              component="div"
              count={filteredLicenseUsers.length}
              rowsPerPage={licenseUserRowsPerPage}
              page={licenseUserPage}
              onPageChange={(_, newPage) => setLicenseUserPage(newPage)}
              onRowsPerPageChange={(e) => {
                setLicenseUserRowsPerPage(parseInt(e.target.value, 10));
                setLicenseUserPage(0);
              }}
              sx={{
                color: 'var(--text-primary)',
                '& .MuiTablePagination-selectLabel, & .MuiTablePagination-displayedRows': {
                  color: 'var(--text-primary)',
                },
                '& .MuiTablePagination-select': { color: 'var(--text-primary)' },
                '& .MuiTablePagination-selectIcon': {
                  color: 'var(--text-secondary)',
                },
                '& .MuiTablePagination-actions': {
                  color: 'var(--text-primary)',
                  '& .Mui-disabled': {
                    color: 'var(--text-secondary)',
                    opacity: 0.5,
                  },
                },
              }}
            />
          </Box>
        </Box>
      </Box>
    );
  }

  // ================= MAIN DASHBOARD =================
  return (
    <Box p={2} sx={{ bgcolor: 'var(--bg-primary)', minHeight: '100%' }}>
      <Tabs
        value={activeTab}
        onChange={(_, v) => setActiveTab(v)}
        sx={{
          mb: 2,
          borderBottom: '1px solid var(--border)',
          '& .MuiTab-root': { color: 'var(--text-secondary)' },
          '& .Mui-selected': { color: 'var(--text-primary)' },
        }}
      >
        <Tab label="Licenses" />
        <Tab label="MCP Access" />
        <Tab label="Manage Users" />
      </Tabs>

      {activeTab === 1 && (
        <Box>
          <Typography variant="h6" sx={{ color: 'var(--text-primary)', mb: 2 }}>
            MCP Tool Access per User (Root user by default has full access)
          </Typography>
          <TableContainer
            component={Paper}
            sx={{ bgcolor: 'var(--bg-secondary)', border: '1px solid var(--border)' }}
          >
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: 'var(--bg-tertiary)' }}>
                  <TableCell
                    sx={{
                      color: 'var(--text-primary)',
                      borderColor: 'var(--border)',
                    }}
                  >
                    Username
                  </TableCell>
                  <TableCell
                    sx={{
                      color: 'var(--text-primary)',
                      borderColor: 'var(--border)',
                    }}
                  >
                    Email
                  </TableCell>
                  <TableCell
                    sx={{
                      color: 'var(--text-primary)',
                      borderColor: 'var(--border)',
                    }}
                  >
                    MCP Access
                  </TableCell>
                  <TableCell
                    sx={{
                      color: 'var(--text-primary)',
                      borderColor: 'var(--border)',
                    }}
                  >
                    Chat Config
                  </TableCell>
                  <TableCell
                    sx={{
                      color: 'var(--text-primary)',
                      borderColor: 'var(--border)',
                    }}
                    align="right"
                  >
                    Edit
                  </TableCell>
                </TableRow>
              </TableHead>
              <TableBody>
                {userList.map((u) => (
                  <TableRow key={u.laui} sx={{ '&:hover': { bgcolor: 'var(--bg-tertiary)' } }}>
                    <TableCell
                      sx={{
                        color: 'var(--text-primary)',
                        borderColor: 'var(--border)',
                      }}
                    >
                      {u.username}
                    </TableCell>
                    <TableCell
                      sx={{
                        color: 'var(--text-secondary)',
                        borderColor: 'var(--border)',
                      }}
                    >
                      {u.email}
                    </TableCell>
                    <TableCell sx={{ borderColor: 'var(--border)' }}>
                      {u.allowed_mcp_tools === null ? (
                        <Chip
                          label="All tools"
                          size="small"
                          sx={{ bgcolor: 'green', color: 'white' }}
                        />
                      ) : (
                        <Chip
                          label={`${u.allowed_mcp_tools.length} / ${allMcpTools.length} tools`}
                          size="small"
                          sx={{
                            bgcolor: 'var(--bg-tertiary)',
                            color: 'var(--text-primary)',
                          }}
                        />
                      )}
                    </TableCell>
                    <TableCell sx={{ borderColor: 'var(--border)' }}>
                      {u.chat_agent_laui ? (
                        <Chip
                          label={u.chat_agent_name ?? 'Configured'}
                          size="small"
                          sx={{ bgcolor: 'green', color: 'white' }}
                        />
                      ) : (
                        <Chip
                          label="Not configured"
                          size="small"
                          sx={{
                            bgcolor: 'var(--bg-tertiary)',
                            color: 'var(--text-secondary)',
                          }}
                        />
                      )}
                    </TableCell>
                    <TableCell align="right" sx={{ borderColor: 'var(--border)' }}>
                      <IconButton
                        size="small"
                        onClick={() => handleOpenEditTools(u)}
                        sx={{
                          color: 'var(--text-secondary)',
                          '&:hover': { color: 'var(--text-primary)' },
                        }}
                      >
                        <EditIcon fontSize="small" />
                      </IconButton>
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {/* Edit MCP tools modal */}
          <BaseModal
            open={!!editingUser}
            onClose={() => setEditingUser(null)}
            title={`MCP Tools — ${editingUser?.username}`}
            subtitle="Select which tools this user can access. Selecting all restores full access."
            maxWidth="sm"
            actions={
              <Stack direction="row" spacing={1}>
                <Button onClick={() => setEditingUser(null)} sx={{ color: 'var(--text-primary)' }}>
                  Cancel
                </Button>
                <Button
                  variant="contained"
                  onClick={() => {
                    void handleSaveMcpTools();
                  }}
                  sx={{
                    bgcolor: 'var(--accent)',
                    '&:hover': { bgcolor: 'var(--accent)', opacity: 0.8 },
                  }}
                >
                  Save
                </Button>
              </Stack>
            }
          >
            <Stack direction="row" spacing={1} mb={1}>
              <Button
                size="small"
                onClick={() => setEditingTools([...allMcpTools])}
                sx={{ color: 'var(--text-secondary)' }}
              >
                Select all
              </Button>
              <Button
                size="small"
                onClick={() => setEditingTools([])}
                sx={{ color: 'var(--text-secondary)' }}
              >
                Clear all
              </Button>
            </Stack>
            {Object.entries(mcpToolGroups).map(([groupName, groupTools]) => {
              const selectedCount = groupTools.filter((t) => editingTools.includes(t)).length;
              const allSelected = selectedCount === groupTools.length;
              return (
                <Box key={groupName} sx={{ mb: 1.5 }}>
                  <Stack
                    direction="row"
                    alignItems="center"
                    justifyContent="space-between"
                    sx={{ mb: 0.5 }}
                  >
                    <Typography
                      variant="subtitle2"
                      sx={{ color: 'var(--text-secondary)', fontWeight: 600 }}
                    >
                      {groupName}{' '}
                      <Typography component="span" variant="caption" sx={{ opacity: 0.7 }}>
                        ({selectedCount}/{groupTools.length})
                      </Typography>
                    </Typography>
                    <Button
                      size="small"
                      onClick={() => handleToggleGroup(groupTools, !allSelected)}
                      sx={{ color: 'var(--text-secondary)', minWidth: 0 }}
                    >
                      {allSelected ? 'Clear' : 'Select'}
                    </Button>
                  </Stack>
                  <FormGroup sx={{ display: 'grid', gridTemplateColumns: '1fr 1fr', gap: 0 }}>
                    {groupTools.map((tool) => (
                      <FormControlLabel
                        key={tool}
                        control={
                          <Checkbox
                            checked={editingTools.includes(tool)}
                            onChange={() => handleToggleTool(tool)}
                            size="small"
                            sx={{
                              color: 'var(--text-secondary)',
                              '&.Mui-checked': { color: 'var(--accent)' },
                            }}
                          />
                        }
                        label={
                          <Typography
                            variant="body2"
                            sx={{ color: 'var(--text-primary)', fontFamily: 'monospace' }}
                          >
                            {tool}
                          </Typography>
                        }
                      />
                    ))}
                  </FormGroup>
                </Box>
              );
            })}

            <Divider sx={{ my: 2, borderColor: 'var(--border)' }} />
            <Typography variant="subtitle2" sx={{ color: 'var(--text-secondary)', mb: 1.5 }}>
              Chat Configuration
            </Typography>

            {/* Agent search */}
            <ClickAwayListener onClickAway={() => setAgentDropdownOpen(false)}>
              <Box sx={{ position: 'relative', mb: 2 }}>
                <TextField
                  fullWidth
                  size="small"
                  label="Agent"
                  placeholder={editingChatAgentName || 'Search agents...'}
                  value={agentQuery}
                  onChange={(e) => {
                    setAgentQuery(e.target.value);
                    void searchAgents(e.target.value);
                    setAgentDropdownOpen(true);
                  }}
                  onFocus={() => {
                    void searchAgents(agentQuery);
                    setAgentDropdownOpen(true);
                  }}
                  sx={{
                    '& .MuiInputBase-root': {
                      bgcolor: 'var(--bg-tertiary)',
                      color: 'var(--text-primary)',
                    },
                    '& .MuiInputLabel-root': { color: 'var(--text-secondary)' },
                    '& .MuiOutlinedInput-notchedOutline': {
                      borderColor: 'var(--border)',
                    },
                  }}
                />
                {agentDropdownOpen && agentResults.length > 0 && (
                  <Paper
                    elevation={4}
                    sx={{
                      position: 'absolute',
                      top: '100%',
                      left: 0,
                      right: 0,
                      mt: 0.5,
                      maxHeight: 160,
                      overflow: 'auto',
                      zIndex: 20,
                      bgcolor: 'var(--bg-primary)',
                      border: '1px solid var(--border)',
                    }}
                  >
                    {agentResults.map((a) => (
                      <Box
                        key={a.laui}
                        onClick={() => {
                          setEditingChatAgentLaui(a.laui);
                          setEditingChatAgentName(a.name);
                          setAgentQuery('');
                          setAgentDropdownOpen(false);
                        }}
                        sx={{
                          px: 1.5,
                          py: 0.75,
                          cursor: 'pointer',
                          '&:hover': { bgcolor: 'var(--bg-secondary)' },
                          borderBottom: '1px solid var(--border)',
                          '&:last-child': { borderBottom: 'none' },
                        }}
                      >
                        <Typography variant="body2" sx={{ color: 'var(--text-primary)' }}>
                          {a.name}
                        </Typography>
                        <Typography variant="caption" sx={{ color: 'var(--text-secondary)' }}>
                          {a.laui}
                        </Typography>
                      </Box>
                    ))}
                  </Paper>
                )}
                {editingChatAgentLaui && (
                  <Typography
                    variant="caption"
                    sx={{ color: 'var(--accent)', mt: 0.5, display: 'block' }}
                  >
                    Selected: {editingChatAgentName}
                  </Typography>
                )}
              </Box>
            </ClickAwayListener>

            {/* Connection search */}
            <ClickAwayListener onClickAway={() => setConnDropdownOpen(false)}>
              <Box sx={{ position: 'relative' }}>
                <TextField
                  fullWidth
                  size="small"
                  label="Connection"
                  placeholder={editingChatConnName || 'Search connections...'}
                  value={connQuery}
                  onChange={(e) => {
                    setConnQuery(e.target.value);
                    void searchConns(e.target.value);
                    setConnDropdownOpen(true);
                  }}
                  onFocus={() => {
                    void searchConns(connQuery);
                    setConnDropdownOpen(true);
                  }}
                  sx={{
                    '& .MuiInputBase-root': {
                      bgcolor: 'var(--bg-tertiary)',
                      color: 'var(--text-primary)',
                    },
                    '& .MuiInputLabel-root': { color: 'var(--text-secondary)' },
                    '& .MuiOutlinedInput-notchedOutline': {
                      borderColor: 'var(--border)',
                    },
                  }}
                />
                {connDropdownOpen && connResults.length > 0 && (
                  <Paper
                    elevation={4}
                    sx={{
                      position: 'absolute',
                      top: '100%',
                      left: 0,
                      right: 0,
                      mt: 0.5,
                      maxHeight: 160,
                      overflow: 'auto',
                      zIndex: 20,
                      bgcolor: 'var(--bg-primary)',
                      border: '1px solid var(--border)',
                    }}
                  >
                    {connResults.map((c) => (
                      <Box
                        key={c.laui}
                        onClick={() => {
                          setEditingChatConnLaui(c.laui);
                          setEditingChatConnName(c.name);
                          setConnQuery('');
                          setConnDropdownOpen(false);
                        }}
                        sx={{
                          px: 1.5,
                          py: 0.75,
                          cursor: 'pointer',
                          '&:hover': { bgcolor: 'var(--bg-secondary)' },
                          borderBottom: '1px solid var(--border)',
                          '&:last-child': { borderBottom: 'none' },
                        }}
                      >
                        <Typography variant="body2" sx={{ color: 'var(--text-primary)' }}>
                          {c.name}
                        </Typography>
                        <Typography variant="caption" sx={{ color: 'var(--text-secondary)' }}>
                          {c.laui}
                        </Typography>
                      </Box>
                    ))}
                  </Paper>
                )}
                {editingChatConnLaui && (
                  <Typography
                    variant="caption"
                    sx={{ color: 'var(--accent)', mt: 0.5, display: 'block' }}
                  >
                    Selected: {editingChatConnName}
                  </Typography>
                )}
              </Box>
            </ClickAwayListener>
          </BaseModal>
        </Box>
      )}
      {activeTab == 0 && (
        <Box>
          <Stack direction="row" justifyContent="space-between" mb={2}>
            <Typography variant="h6" sx={{ color: 'var(--text-primary)' }}>
              Licenses
            </Typography>
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
              <Typography variant="h6" sx={{ color: 'var(--text-primary)' }}>
                System User Laui: {systemUserLaui}
              </Typography>

              <Tooltip title={copied ? 'Copied!' : 'Copy to clipboard'}>
                <IconButton
                  onClick={() => {
                    void handleCopy();
                  }}
                  size="small"
                  sx={{ color: 'var(--text-primary)' }}
                >
                  {copied ? (
                    <CheckIcon fontSize="small" color="success" />
                  ) : (
                    <ContentCopyIcon fontSize="small" />
                  )}
                </IconButton>
              </Tooltip>
            </Box>

            <Stack direction="row" spacing={1}>
              {/*
                userLoggedInToMarketplace && (
                <Button
                  variant="contained"
                  onClick={() => setBuyOpen(true)}
                  sx={{
                    bgcolor: 'var(--accent)',
                    '&:hover': { bgcolor: 'var(--accent)', opacity: 0.8 },
                  }}
                >
                  Buy License
                </Button>
              )
              */}

              <Button
                variant="outlined"
                onClick={() => setUploadOpen(true)}
                sx={{
                  borderColor: 'var(--border)',
                  color: 'var(--text-primary)',
                  '&:hover': {
                    borderColor: 'var(--border)',
                    bgcolor: 'var(--bg-secondary)',
                  },
                }}
              >
                Upload License
              </Button>
            </Stack>
          </Stack>

          <TableContainer
            component={Paper}
            sx={{
              bgcolor: 'var(--bg-secondary)',
              border: '1px solid',
              borderColor: 'var(--border)',
            }}
          >
            {licenses.length === 0 && (
              <Typography variant="h6" sx={{ color: 'var(--text-primary)', padding: '10px' }}>
                {' '}
                0 Licenses
              </Typography>
            )}
            <Table>
              <TableHead>
                <TableRow sx={{ bgcolor: 'var(--bg-tertiary)' }}>
                  <TableCell
                    sx={{
                      color: 'var(--text-primary)',
                      borderColor: 'var(--border)',
                    }}
                  >
                    License ID
                  </TableCell>
                  <TableCell
                    sx={{
                      color: 'var(--text-primary)',
                      borderColor: 'var(--border)',
                    }}
                  >
                    Tier
                  </TableCell>
                  <TableCell
                    sx={{
                      color: 'var(--text-primary)',
                      borderColor: 'var(--border)',
                    }}
                  >
                    Status
                  </TableCell>
                </TableRow>
              </TableHead>

              <TableBody>
                {licenses.map((l) => (
                  <TableRow
                    key={l.laui}
                    hover
                    sx={{
                      cursor: 'pointer',
                      '&:hover': { bgcolor: 'var(--bg-tertiary)' },
                    }}
                    onClick={() => {
                      void handleRowClick(l.laui);
                    }}
                  >
                    <TableCell
                      sx={{
                        color: 'var(--text-primary)',
                        borderColor: 'var(--border)',
                      }}
                    >
                      {l.license_id.slice(-10)}
                    </TableCell>
                    <TableCell
                      sx={{
                        color: 'var(--text-primary)',
                        borderColor: 'var(--border)',
                      }}
                    >
                      {l.tier}
                    </TableCell>
                    <TableCell
                      sx={{
                        color: 'var(--text-primary)',
                        borderColor: 'var(--border)',
                      }}
                    >
                      {l.status}
                    </TableCell>
                  </TableRow>
                ))}
              </TableBody>
            </Table>
          </TableContainer>

          {/* BUY MODAL */}
          <BaseModal
            open={buyOpen}
            onClose={() => setBuyOpen(false)}
            title="Buy License"
            subtitle="Generate a new license"
            maxWidth="sm"
            actions={
              <Stack direction="row" spacing={1}>
                <Button onClick={() => setBuyOpen(false)} sx={{ color: 'var(--text-primary)' }}>
                  Cancel
                </Button>

                {/* Conditional Actions: Show Generate initially, switch to Upload on success */}
                {!licenseId ? (
                  <Button
                    variant="contained"
                    onClick={() => {
                      void handleBuy();
                    }}
                    sx={{
                      bgcolor: 'var(--accent)',
                      '&:hover': { bgcolor: 'var(--accent)', opacity: 0.8 },
                    }}
                  >
                    Generate
                  </Button>
                ) : (
                  <Button
                    variant="contained"
                    onClick={() => {
                      setBuyOpen(false);
                      setUploadOpen(true);
                    }}
                    sx={{
                      bgcolor: 'var(--accent)',
                      '&:hover': { bgcolor: 'var(--accent)', opacity: 0.8 },
                    }}
                  >
                    Upload
                  </Button>
                )}
              </Stack>
            }
          >
            <Stack spacing={2}>
              <TextField
                label="Total Users"
                type="number"
                value={users}
                onChange={(e) => setUsers(Number(e.target.value))}
                sx={{
                  '& .MuiInputBase-root': {
                    bgcolor: 'var(--bg-tertiary)',
                    color: 'var(--text-primary)',
                  },
                  '& .MuiInputLabel-root': { color: 'var(--text-secondary)' },
                  '& .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'var(--border)',
                  },
                }}
              />

              <TextField
                label="Duration (months)"
                type="number"
                value={duration}
                onChange={(e) => setDuration(Number(e.target.value))}
                sx={{
                  '& .MuiInputBase-root': {
                    bgcolor: 'var(--bg-tertiary)',
                    color: 'var(--text-primary)',
                  },
                  '& .MuiInputLabel-root': { color: 'var(--text-secondary)' },
                  '& .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'var(--border)',
                  },
                }}
              />

              {licenseId && (
                <Box
                  sx={{
                    bgcolor: 'var(--bg-tertiary)',
                    p: 2,
                    borderRadius: 2,
                    border: '1px solid',
                    borderColor: 'var(--border)',
                  }}
                >
                  <Stack spacing={1}>
                    {/* License ID Row */}
                    <Box
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        overflow: 'hidden',
                      }}
                    >
                      <Typography
                        variant="body2"
                        title={licenseId} // Shows full ID on hover
                        sx={{
                          color: 'var(--text-primary)',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          mr: 2,
                        }}
                      >
                        License ID: {licenseId}
                      </Typography>
                      <Tooltip title="Copy License ID">
                        <IconButton
                          size="small"
                          onClick={() => {
                            void navigator.clipboard.writeText(licenseId);
                          }}
                          sx={{
                            color: 'var(--text-primary)',
                            flexShrink: 0,
                          }}
                        >
                          <ContentCopyIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>

                    {/* Public Key Row */}
                    <Box
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        justifyContent: 'space-between',
                        overflow: 'hidden',
                      }}
                    >
                      <Typography
                        variant="body2"
                        title={publicKey} // Shows full key on hover
                        sx={{
                          color: 'var(--text-primary)',
                          whiteSpace: 'nowrap',
                          overflow: 'hidden',
                          textOverflow: 'ellipsis',
                          mr: 2,
                        }}
                      >
                        Public Key: {publicKey}
                      </Typography>
                      <Tooltip title="Copy Public Key">
                        <IconButton
                          size="small"
                          onClick={() => {
                            void navigator.clipboard.writeText(publicKey);
                          }}
                          sx={{
                            color: 'var(--text-primary)',
                            flexShrink: 0,
                          }}
                        >
                          <ContentCopyIcon fontSize="small" />
                        </IconButton>
                      </Tooltip>
                    </Box>
                  </Stack>
                </Box>
              )}
            </Stack>
          </BaseModal>

          {/* UPLOAD MODAL */}
          <BaseModal
            open={uploadOpen}
            onClose={() => setUploadOpen(false)}
            title="Upload License"
            subtitle="Provide credentials"
            maxWidth="sm"
            actions={
              <Stack direction="row" spacing={1}>
                <Button onClick={() => setUploadOpen(false)} sx={{ color: 'var(--text-primary)' }}>
                  Cancel
                </Button>
                <Button
                  variant="contained"
                  onClick={() => {
                    void handleUpload();
                  }}
                  sx={{
                    bgcolor: 'var(--accent)',
                    '&:hover': { bgcolor: 'var(--accent)', opacity: 0.8 },
                  }}
                >
                  Upload
                </Button>
              </Stack>
            }
          >
            <Stack spacing={2}>
              <TextField
                label="License ID"
                value={licenseId}
                onChange={(e) => setLicenseId(e.target.value)}
                fullWidth
                sx={{
                  '& .MuiInputBase-root': {
                    bgcolor: 'var(--bg-tertiary)',
                    color: 'var(--text-primary)',
                  },
                  '& .MuiInputLabel-root': { color: 'var(--text-secondary)' },
                  '& .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'var(--border)',
                  },
                }}
              />

              <TextField
                label="Public Key"
                value={publicKey}
                onChange={(e) => setPublicKey(e.target.value)}
                multiline
                rows={4}
                fullWidth
                sx={{
                  '& .MuiInputBase-root': {
                    bgcolor: 'var(--bg-tertiary)',
                    color: 'var(--text-primary)',
                  },
                  '& .MuiInputLabel-root': { color: 'var(--text-secondary)' },
                  '& .MuiOutlinedInput-notchedOutline': {
                    borderColor: 'var(--border)',
                  },
                }}
              />
            </Stack>
          </BaseModal>
        </Box>
      )}
      {activeTab == 2 && <ManageUsers />}
    </Box>
  );
}
