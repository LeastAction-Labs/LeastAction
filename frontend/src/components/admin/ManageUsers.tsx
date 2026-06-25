/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useCallback, useEffect, useState } from 'react';

import {
  Block,
  Check,
  Close as CloseIcon,
  ContentCopy,
  Delete,
  Email,
  LockOpen,
  LockReset,
  // Added for Reset Password action
  Person,
  PersonAdd,
} from '@mui/icons-material';
import {
  Alert,
  Box,
  Button,
  Chip,
  CircularProgress,
  Dialog,
  DialogActions,
  DialogContent,
  DialogContentText,
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
  TableRow,
  TextField,
  Tooltip,
  Typography,
} from '@mui/material';

import Pagination from '@/components/browse/Pagination';
import { FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import { useAuth } from '@/contexts/AuthContext';
import { useNotification } from '@/contexts/NotificationContext';
import type { AdminCreateUserResponse, UserRecord } from '@/services/admin.service';
import { adminCreateUser, deleteUser, listUsers, updateUser } from '@/services/admin.service';

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    overflow: 'hidden',
  },
  tabsContainer: {
    borderBottom: 1,
    borderColor: 'var(--border)',
    bgcolor: 'var(--bg-secondary)',
  },
  tableContainer: {
    flex: 1,
    overflowX: 'auto',
    overflowY: 'auto',
    bgcolor: 'transparent',
    boxShadow: 'none',
    borderRadius: 0,
    '&::-webkit-scrollbar': {
      height: '8px',
      width: '8px',
    },
    '&::-webkit-scrollbar-track': {
      bgcolor: 'rgba(255, 255, 255, 0.02)',
    },
    '&::-webkit-scrollbar-thumb': {
      bgcolor: 'rgba(255, 255, 255, 0.15)',
      borderRadius: 'var(--radius-sm)',
      '&:hover': {
        bgcolor: 'rgba(255, 255, 255, 0.25)',
      },
    },
    '& .MuiTableCell-root': {
      color: 'var(--text-primary)',
      borderColor: 'rgba(255, 255, 255, 0.08)',
      fontSize: FONT_SIZES.SM,
      py: 1.5,
      px: 2,
    },
  },
  table: {
    tableLayout: 'fixed',
    minWidth: 830, // Marginally increased to cleanly accommodate 3 actions
  },
  tableHead: {
    '& .MuiTableCell-root': {
      fontWeight: FONT_WEIGHTS.WEIGHT_600,
      color: 'var(--text-primary)',
      textTransform: 'uppercase' as const,
      fontSize: FONT_SIZES.XS,
      letterSpacing: '0.08em',
      borderBottom: '1px solid var(--border)',
      bgcolor: 'transparent',
    },
  },
  tableRow: {
    transition: 'background-color 0.2s ease',
    '&:hover': {
      bgcolor: 'var(--bg-secondary)',
    },
    cursor: 'pointer',
  },
  wrappingTextCell: {
    wordBreak: 'break-word',
    whiteSpace: 'normal',
  },
  monospaceWrapCell: {
    fontFamily: 'monospace',
    fontSize: FONT_SIZES.XS,
    color: 'var(--text-secondary)',
    wordBreak: 'break-all',
    whiteSpace: 'normal',
  },
  groupHeaderRow: {
    bgcolor: 'var(--bg-tertiary)',
    '& .MuiTableCell-root': {
      fontWeight: FONT_WEIGHTS.WEIGHT_600,
      color: 'var(--accent)',
    },
  },
  emptyState: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    p: 4,
    color: 'var(--text-secondary)',
  },
  paginationContainer: {
    mt: 2,
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    px: 2,
    pb: 2,
  },
  paginationWrapper: {
    display: 'flex',
    justifyContent: 'center',
    flex: 1,
  },
  itemsPerPageContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: 1,
  },
  itemsPerPageSelect: {
    '& .MuiSvgIcon-root': {
      color: 'var(--text-primary)',
    },
    '& .MuiSelect-select': {
      py: 0.5,
      px: 1.5,
      fontSize: FONT_SIZES.SM,
      color: 'var(--text-primary)',
      bgcolor: 'var(--bg-secondary)',
    },
    '& .MuiOutlinedInput-notchedOutline': {
      borderColor: 'rgba(255, 255, 255, 0.1)',
    },
    '&:hover .MuiOutlinedInput-notchedOutline': {
      borderColor: 'rgba(255, 255, 255, 0.2)',
    },
    '&.Mui-focused .MuiOutlinedInput-notchedOutline': {
      borderColor: 'var(--primary-main)',
    },
  },
  itemsPerPageLabel: {
    fontSize: FONT_SIZES.SM,
    color: 'var(--text-secondary)',
  },
};

interface UserPagination {
  currentPage: number;
  hasNext: boolean;
  perPage: number;
}

const PAGE_SIZE_OPTIONS = [5, 10, 25, 50, 100];

const ManageUsers = () => {
  const { authState } = useAuth();
  const currentUserLaui = authState.user?.laui;
  const { showSuccess } = useNotification();

  const [userList, setUserList] = useState<UserRecord[]>([]);
  const [userPagination, setUserPagination] = useState<UserPagination>({
    currentPage: 1,
    hasNext: false,
    perPage: 10,
  });
  const [usersLoading, setUsersLoading] = useState(false);
  const [showCreateForm, setShowCreateForm] = useState(false);
  const [formData, setFormData] = useState({ username: '', email: '' });
  const [formErrors, setFormErrors] = useState({ username: '', email: '' });
  const [creating, setCreating] = useState(false);
  const [createResult, setCreateResult] = useState<AdminCreateUserResponse | null>(null);
  const [copied, setCopied] = useState(false);
  const [copiedField, setCopiedField] = useState<{
    laui: string;
    field: 'laui' | 'email';
  } | null>(null);

  const [deleteTarget, setDeleteTarget] = useState<UserRecord | null>(null);
  const [activationAlterTarget, setactivationAlterTarget] = useState<UserRecord | null>(null);
  const [resetPasswordTarget, setResetPasswordTarget] = useState<UserRecord | null>(null);
  const [newPassword, setNewPassword] = useState('');
  const [passwordError, setPasswordError] = useState('');
  const [userActionLoading, setUserActionLoading] = useState<string | null>(null);

  const fetchUsers = useCallback(async () => {
    setUsersLoading(true);
    try {
      const data = await listUsers(userPagination.currentPage, userPagination.perPage);
      setUserList(data.users);
      setUserPagination((prev) => ({ ...prev, hasNext: data.pagination.has_next }));
    } catch (error) {
      console.error('Failed to fetch user list:', error);
    } finally {
      setUsersLoading(false);
    }
  }, [userPagination.currentPage, userPagination.perPage]);

  useEffect(() => {
    void fetchUsers();
  }, [fetchUsers]);

  // ---- Create user helpers ----
  const validateForm = () => {
    const newErrors = { username: '', email: '' };
    if (!formData.username.trim()) newErrors.username = 'Username is required';
    if (!formData.email.trim()) {
      newErrors.email = 'Email is required';
    } else if (!/^[^\s@]+@[^\s@]+\.[^\s@]+$/.test(formData.email)) {
      newErrors.email = 'Enter a valid email address';
    }
    setFormErrors(newErrors);
    return !newErrors.username && !newErrors.email;
  };

  const handleCreateSubmit = async (e: React.FormEvent) => {
    e.preventDefault();
    if (!validateForm()) return;
    setCreating(true);
    setCreateResult(null);
    try {
      const res = await adminCreateUser(formData.username, formData.email);
      setCreateResult(res);
      setFormData({ username: '', email: '' });
      showSuccess('User created successfully');
      await fetchUsers();
    } catch (error: any) {
      console.error('Failed to create user:', error);
    } finally {
      setCreating(false);
    }
  };

  const handleCopy = () => {
    if (!createResult) return;
    void navigator.clipboard.writeText(createResult.temp_password);
    setCopied(true);
    setTimeout(() => setCopied(false), 2000);
  };

  // ---- User management helpers ----
  const handleDeleteConfirm = async () => {
    if (!deleteTarget) return;
    setUserActionLoading(deleteTarget.laui);
    setDeleteTarget(null);
    try {
      await deleteUser(deleteTarget.laui);
      showSuccess('User deleted successfully');
      await fetchUsers();
    } catch (error: any) {
      console.error('Failed to delete user:', error);
    } finally {
      setUserActionLoading(null);
    }
  };

  const handleActivationAlterConfirm = async () => {
    if (!activationAlterTarget) return;
    setUserActionLoading(activationAlterTarget.laui);
    const contextAction = activationAlterTarget.is_active ? 'deactivated' : 'activated';
    setactivationAlterTarget(null);
    try {
      await updateUser(activationAlterTarget.laui, {
        is_active: !activationAlterTarget.is_active,
      });
      showSuccess(`User ${contextAction} successfully`);
      await fetchUsers();
    } catch (error: any) {
      console.error(`Failed to ${contextAction} user:`, error);
    } finally {
      setUserActionLoading(null);
    }
  };

  const handleResetPasswordConfirm = async () => {
    if (!resetPasswordTarget) return;
    if (!newPassword.trim()) {
      setPasswordError('Password cannot be empty');
      return;
    }
    if (newPassword.trim().length < 6) {
      setPasswordError('Password must be of at least 6 characters');
      return;
    }

    setUserActionLoading(resetPasswordTarget.laui);
    const targetLaui = resetPasswordTarget.laui;
    setResetPasswordTarget(null);
    setPasswordError('');

    try {
      await updateUser(targetLaui, { password: newPassword.trim() });
      showSuccess('Password reset successfully');
      setNewPassword('');
    } catch (error: any) {
      console.error('Failed to reset password:', error);
    } finally {
      setUserActionLoading(null);
    }
  };

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%', overflow: 'hidden' }}>
      {/* Create user section */}
      <Box
        sx={{
          p: 2,
          borderBottom: '1px solid var(--border)',
          bgcolor: 'var(--bg-secondary)',
        }}
      >
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'space-between',
            mb: showCreateForm ? 2 : 0,
          }}
        >
          <Typography
            variant="subtitle2"
            sx={{ color: 'var(--text-primary)', fontWeight: FONT_WEIGHTS.WEIGHT_600 }}
          >
            User Management
          </Typography>
          <Button
            size="small"
            variant={showCreateForm ? 'outlined' : 'contained'}
            startIcon={showCreateForm ? <CloseIcon /> : <PersonAdd />}
            onClick={() => {
              setShowCreateForm(!showCreateForm);
              setCreateResult(null);
            }}
            sx={{ fontSize: FONT_SIZES.XS }}
          >
            {showCreateForm ? 'Cancel' : 'Create User'}
          </Button>
        </Box>

        {showCreateForm && (
          <Box component="form" onSubmit={(e) => void handleCreateSubmit(e)}>
            <Box sx={{ display: 'flex', gap: 1.5, mb: 1.5 }}>
              <TextField
                size="small"
                required
                fullWidth
                label="Username"
                value={formData.username}
                onChange={(e) => setFormData((p) => ({ ...p, username: e.target.value }))}
                error={!!formErrors.username}
                helperText={formErrors.username}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Person
                        sx={{
                          fontSize: 16,
                          color: 'var(--text-secondary)',
                        }}
                      />
                    </InputAdornment>
                  ),
                }}
                sx={{
                  '& .MuiOutlinedInput-root': { color: 'var(--text-primary)' },
                }}
              />
              <TextField
                size="small"
                required
                fullWidth
                label="Email"
                type="email"
                value={formData.email}
                onChange={(e) => setFormData((p) => ({ ...p, email: e.target.value }))}
                error={!!formErrors.email}
                helperText={formErrors.email}
                InputProps={{
                  startAdornment: (
                    <InputAdornment position="start">
                      <Email
                        sx={{
                          fontSize: 16,
                          color: 'var(--text-secondary)',
                        }}
                      />
                    </InputAdornment>
                  ),
                }}
                sx={{
                  '& .MuiOutlinedInput-root': { color: 'var(--text-primary)' },
                }}
              />
              <Button
                type="submit"
                variant="contained"
                disabled={creating}
                sx={{
                  whiteSpace: 'nowrap',
                  fontSize: FONT_SIZES.XS,
                  minWidth: 100,
                }}
              >
                {creating ? <CircularProgress size={16} /> : 'Create'}
              </Button>
            </Box>

            {createResult && (
              <>
                <Alert severity="success" sx={{ mb: 1, fontSize: FONT_SIZES.XS }}>
                  User <strong>{createResult.username}</strong> created — share the temporary
                  password securely.
                </Alert>
                <Box
                  sx={{
                    display: 'flex',
                    alignItems: 'center',
                    gap: 1,
                    p: 1.5,
                    bgcolor: 'var(--bg-tertiary)',
                    borderRadius: 1,
                    border: '1px solid var(--border)',
                  }}
                >
                  <Typography
                    variant="body2"
                    sx={{
                      flex: 1,
                      fontFamily: 'monospace',
                      fontWeight: 'bold',
                      wordBreak: 'break-all',
                      color: 'var(--text-primary)',
                    }}
                  >
                    {createResult.temp_password}
                  </Typography>
                  <Tooltip title={copied ? 'Copied!' : 'Copy password'}>
                    <IconButton
                      size="small"
                      onClick={handleCopy}
                      sx={{ color: 'var(--text-secondary)' }}
                    >
                      {copied ? (
                        <Check fontSize="small" color="success" />
                      ) : (
                        <ContentCopy fontSize="small" />
                      )}
                    </IconButton>
                  </Tooltip>
                </Box>
              </>
            )}
          </Box>
        )}
      </Box>

      {/* User list */}
      <Box sx={{ flex: 1, overflow: 'auto' }}>
        {usersLoading ? (
          <Box sx={styles.emptyState}>
            <CircularProgress size={24} />
          </Box>
        ) : (
          <>
            <TableContainer component={Paper} sx={styles.tableContainer}>
              <Table stickyHeader size="small" sx={styles.table}>
                <TableHead sx={styles.tableHead}>
                  <TableRow>
                    <TableCell sx={{ width: '160px' }}>Username</TableCell>
                    <TableCell sx={{ width: '160px' }}>LAUI</TableCell>
                    <TableCell sx={{ width: '240px' }}>Email</TableCell>
                    <TableCell sx={{ width: '110px' }}>Status</TableCell>
                    <TableCell sx={{ width: '130px' }}>Created</TableCell>
                    <TableCell sx={{ width: '130px' }} align="center">
                      Actions
                    </TableCell>
                  </TableRow>
                </TableHead>
                <TableBody>
                  {userList.length === 0 ? (
                    <TableRow>
                      <TableCell colSpan={6}>
                        <Box sx={styles.emptyState}>
                          <Typography variant="body2">No users found</Typography>
                        </Box>
                      </TableCell>
                    </TableRow>
                  ) : (
                    userList.map((user) => {
                      const isSelf = user.laui === currentUserLaui;
                      const isRoot = user.user_type === 'root';
                      const isDeleteAbleOrActivationAlterAble = !isRoot && !isSelf;
                      const isPasswordResetAble = isRoot ? isSelf : true;

                      const isActioning = userActionLoading === user.laui;
                      const statusLabel = user.is_active ? 'Active' : 'Inactive';
                      const statusColor: 'error' | 'success' | 'default' = user.is_active
                        ? 'success'
                        : 'default';

                      return (
                        <TableRow key={user.laui} sx={styles.tableRow}>
                          <TableCell sx={styles.wrappingTextCell}>{user.username}</TableCell>
                          <TableCell sx={styles.wrappingTextCell}>
                            <Box
                              sx={{
                                display: 'flex',
                                alignItems: 'flex-start',
                                gap: 0.5,
                              }}
                            >
                              <Typography variant="body2" sx={styles.monospaceWrapCell}>
                                {user.laui}
                              </Typography>
                              <Tooltip
                                title={
                                  copiedField?.laui === user.laui && copiedField.field === 'laui'
                                    ? 'Copied!'
                                    : 'Copy LAUI'
                                }
                              >
                                <IconButton
                                  size="small"
                                  onClick={() => {
                                    void navigator.clipboard.writeText(user.laui);
                                    setCopiedField({
                                      laui: user.laui,
                                      field: 'laui',
                                    });
                                    setTimeout(() => setCopiedField(null), 2000);
                                  }}
                                  sx={{
                                    color: 'var(--text-secondary)',
                                    p: 0.25,
                                    mt: -0.25,
                                  }}
                                >
                                  {copiedField?.laui === user.laui &&
                                  copiedField.field === 'laui' ? (
                                    <Check sx={{ fontSize: 12 }} />
                                  ) : (
                                    <ContentCopy sx={{ fontSize: 12 }} />
                                  )}
                                </IconButton>
                              </Tooltip>
                            </Box>
                          </TableCell>
                          <TableCell sx={styles.wrappingTextCell}>
                            <Box
                              sx={{
                                display: 'flex',
                                alignItems: 'flex-start',
                                gap: 0.5,
                              }}
                            >
                              <Typography
                                variant="body2"
                                sx={{
                                  fontSize: FONT_SIZES.SM,
                                  wordBreak: 'break-all',
                                  whiteSpace: 'normal',
                                }}
                              >
                                {user.email}
                              </Typography>
                              <Tooltip
                                title={
                                  copiedField?.laui === user.laui && copiedField.field === 'email'
                                    ? 'Copied!'
                                    : 'Copy email'
                                }
                              >
                                <IconButton
                                  size="small"
                                  onClick={() => {
                                    void navigator.clipboard.writeText(user.email);
                                    setCopiedField({
                                      laui: user.laui,
                                      field: 'email',
                                    });
                                    setTimeout(() => setCopiedField(null), 2000);
                                  }}
                                  sx={{
                                    color: 'var(--text-secondary)',
                                    p: 0.25,
                                    mt: -0.25,
                                  }}
                                >
                                  {copiedField?.laui === user.laui &&
                                  copiedField.field === 'email' ? (
                                    <Check sx={{ fontSize: 12 }} />
                                  ) : (
                                    <ContentCopy sx={{ fontSize: 12 }} />
                                  )}
                                </IconButton>
                              </Tooltip>
                            </Box>
                          </TableCell>
                          <TableCell>
                            <Chip
                              label={statusLabel}
                              color={statusColor}
                              size="small"
                              sx={{ fontSize: FONT_SIZES.XS }}
                            />
                          </TableCell>
                          <TableCell sx={styles.wrappingTextCell}>{user.created_at}</TableCell>
                          <TableCell align="center">
                            {isActioning ? (
                              <CircularProgress size={18} />
                            ) : (
                              <Box
                                sx={{
                                  display: 'flex',
                                  justifyContent: 'center',
                                  gap: 0.5,
                                }}
                              >
                                {isPasswordResetAble && (
                                  <Tooltip title={'Reset Password'}>
                                    <span>
                                      <IconButton
                                        size="small"
                                        color="info"
                                        onClick={() => {
                                          setPasswordError('');
                                          setNewPassword('');
                                          setResetPasswordTarget(user);
                                        }}
                                        disabled={isActioning}
                                      >
                                        <LockReset
                                          sx={{
                                            fontSize: 16,
                                          }}
                                        />
                                      </IconButton>
                                    </span>
                                  </Tooltip>
                                )}

                                {isDeleteAbleOrActivationAlterAble && (
                                  <>
                                    <Tooltip
                                      title={!user.is_active ? 'Activate user' : 'Deactivate user'}
                                    >
                                      <span>
                                        <IconButton
                                          size="small"
                                          color="warning"
                                          onClick={() => setactivationAlterTarget(user)}
                                          disabled={isActioning}
                                        >
                                          {user.is_active ? (
                                            <Block
                                              sx={{
                                                fontSize: 16,
                                              }}
                                            />
                                          ) : (
                                            <LockOpen
                                              sx={{
                                                fontSize: 16,
                                              }}
                                            />
                                          )}
                                        </IconButton>
                                      </span>
                                    </Tooltip>

                                    <Tooltip title="Delete user">
                                      <span>
                                        <IconButton
                                          size="small"
                                          color="error"
                                          disabled={isActioning}
                                          onClick={() => setDeleteTarget(user)}
                                        >
                                          <Delete
                                            sx={{
                                              fontSize: 16,
                                            }}
                                          />
                                        </IconButton>
                                      </span>
                                    </Tooltip>
                                  </>
                                )}
                              </Box>
                            )}
                          </TableCell>
                        </TableRow>
                      );
                    })
                  )}
                </TableBody>
              </Table>

              {/* Pagination Section Remaining Unchanged */}
              <Box sx={styles.paginationContainer}>
                <Box sx={styles.itemsPerPageContainer}>
                  <Typography sx={styles.itemsPerPageLabel}>Users per page:</Typography>
                  <FormControl size="small">
                    <Select
                      value={userPagination.perPage}
                      onChange={(e) => {
                        setUserPagination((prev) => ({
                          ...prev,
                          perPage: e.target.value,
                        }));
                      }}
                      sx={styles.itemsPerPageSelect}
                      MenuProps={{
                        PaperProps: {
                          sx: {
                            bgcolor: 'var(--bg-secondary)',
                            '& .MuiMenuItem-root': {
                              color: 'var(--text-primary)',
                              fontSize: FONT_SIZES.SM,
                              '&:hover': {
                                bgcolor: 'rgba(255, 255, 255, 0.08)',
                              },
                              '&.Mui-selected': {
                                bgcolor: 'rgba(255, 255, 255, 0.12)',
                                '&:hover': {
                                  bgcolor: 'rgba(255, 255, 255, 0.16)',
                                },
                              },
                            },
                          },
                        },
                      }}
                    >
                      {PAGE_SIZE_OPTIONS.map((size) => (
                        <MenuItem key={size} value={size}>
                          {size}
                        </MenuItem>
                      ))}
                    </Select>
                  </FormControl>
                </Box>

                <Box sx={styles.paginationWrapper}>
                  <Pagination
                    currentPage={userPagination.currentPage}
                    hasNext={userPagination.hasNext}
                    hasPrevious={userPagination.currentPage !== 1}
                    onPageChange={(page) =>
                      setUserPagination((prev) => ({
                        ...prev,
                        currentPage: page,
                      }))
                    }
                  />
                </Box>
                <Box sx={{ width: '140px' }} />
              </Box>
            </TableContainer>
          </>
        )}
      </Box>

      {/* Reset password dialog */}
      <Dialog
        open={!!resetPasswordTarget}
        onClose={() => setResetPasswordTarget(null)}
        fullWidth
        maxWidth="xs"
      >
        <DialogTitle>Reset Password</DialogTitle>
        <DialogContent>
          <DialogContentText sx={{ mb: 2 }}>
            Set a new password for user <strong>{resetPasswordTarget?.username}</strong>.
          </DialogContentText>
          <TextField
            autoFocus
            size="small"
            fullWidth
            label="New Password"
            type="password"
            value={newPassword}
            onChange={(e) => {
              setNewPassword(e.target.value);
              if (e.target.value.trim()) setPasswordError('');
            }}
            error={!!passwordError}
            helperText={passwordError}
          />
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setResetPasswordTarget(null)}>Cancel</Button>
          <Button
            onClick={() => void handleResetPasswordConfirm()}
            color="info"
            variant="contained"
          >
            Save Password
          </Button>
        </DialogActions>
      </Dialog>

      {/* Activation/Deactivation confirmation dialog */}
      <Dialog open={!!activationAlterTarget} onClose={() => setactivationAlterTarget(null)}>
        <DialogTitle>
          {activationAlterTarget?.is_active ? 'Deactivate' : 'Activate'} User
        </DialogTitle>
        <DialogContent>
          <DialogContentText>
            {activationAlterTarget?.is_active ? (
              <>
                Deactivate <strong>{activationAlterTarget?.username}</strong>? Their session will be
                terminated and they will not be able to log in until explicitly reactivated.
              </>
            ) : (
              <>
                Activate <strong>{activationAlterTarget?.username}</strong>? This will restore their
                system login privileges.
              </>
            )}
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setactivationAlterTarget(null)}>Cancel</Button>
          <Button
            onClick={() => void handleActivationAlterConfirm()}
            color="warning"
            variant="contained"
          >
            {activationAlterTarget?.is_active ? 'Deactivate' : 'Activate'}
          </Button>
        </DialogActions>
      </Dialog>

      {/* Delete confirmation dialog */}
      <Dialog open={!!deleteTarget} onClose={() => setDeleteTarget(null)}>
        <DialogTitle>Delete User</DialogTitle>
        <DialogContent>
          <DialogContentText>
            Delete <strong>{deleteTarget?.username}</strong>? Their account will be permanently
            deleted.
          </DialogContentText>
        </DialogContent>
        <DialogActions>
          <Button onClick={() => setDeleteTarget(null)}>Cancel</Button>
          <Button onClick={() => void handleDeleteConfirm()} color="error" variant="contained">
            Delete
          </Button>
        </DialogActions>
      </Dialog>
    </Box>
  );
};

export default ManageUsers;
