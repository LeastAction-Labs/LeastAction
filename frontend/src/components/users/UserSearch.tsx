/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import { Box, Chip, ClickAwayListener, Paper, Stack, TextField, Typography } from '@mui/material';

import { useNotification } from '@/contexts/NotificationContext';
import { searchUsers } from '@/services/user.service';

interface UserSearchProps {
  /** Array of existing user identifiers already tied to the license */
  existingUserIds: string[];
  /** Array of currently staged users in the parent state */
  queuedUsers: any[];
  /** Callback fired when a user is successfully selected and staged */
  onQueueUser: (user: any) => void;
  /** Callback fired when a staged user chip is removed */
  onRemoveQueuedUser: (id: string) => void;
}

export default function UserSearch({
  existingUserIds = [],
  queuedUsers = [],
  onQueueUser,
  onRemoveQueuedUser,
}: UserSearchProps) {
  const { showWarning } = useNotification();
  const [userSearchQuery, setUserSearchQuery] = useState('');
  const [searchDropdownOpen, setSearchDropdownOpen] = useState(false);
  const [searchedUsersResults, setSearchedUsersResults] = useState<any[]>([]);

  const handleUserSearchChange = async (val: string) => {
    setUserSearchQuery(val);
    try {
      const res: any = await searchUsers({ username: val });
      setSearchedUsersResults(res.users || []);
    } catch (e) {
      console.error('Error fetching user catalog data:', e);
    }
  };

  const handleSelectUserFromSearch = (user: any) => {
    const userId = user.laui || user.id || user.username;

    if (existingUserIds.includes(userId) || queuedUsers.some((u) => u.id === userId)) {
      showWarning('User is already in the list.');
      return;
    }

    onQueueUser({ id: userId, ...user });
    setUserSearchQuery('');
    setSearchedUsersResults([]);
    setSearchDropdownOpen(false);
  };

  return (
    <Box
      sx={{
        my: 3,
        p: 2,
        borderRadius: 2,
        bgcolor: 'var(--bg-tertiary)',
        border: '1px solid var(--border)',
      }}
    >
      <Typography variant="subtitle2" sx={{ color: 'var(--text-primary)', mb: 1 }}>
        Search Users
      </Typography>

      <ClickAwayListener onClickAway={() => setSearchDropdownOpen(false)}>
        <Box sx={{ position: 'relative', maxWidth: 500, mb: 2 }}>
          <TextField
            fullWidth
            size="small"
            placeholder="Type username"
            value={userSearchQuery}
            onChange={(e) => void handleUserSearchChange(e.target.value)}
            onFocus={() => {
              setSearchDropdownOpen(true);
              void handleUserSearchChange(userSearchQuery);
            }}
            sx={{
              '& .MuiInputBase-root': {
                bgcolor: 'var(--bg-secondary)',
                color: 'var(--text-primary)',
              },
              '& .MuiOutlinedInput-notchedOutline': { borderColor: 'var(--border)' },
            }}
          />

          {searchDropdownOpen && searchedUsersResults.length > 0 && (
            <Paper
              elevation={4}
              sx={{
                position: 'absolute',
                top: '100%',
                left: 0,
                right: 0,
                mt: 0.5,
                maxHeight: 200,
                overflow: 'auto',
                zIndex: 30,
                bgcolor: 'var(--bg-primary)',
                border: '1px solid var(--border)',
              }}
            >
              {searchedUsersResults.map((u: any, idx: number) => {
                const displayId = u.laui || u.id || u.username;
                return (
                  <Box
                    key={idx}
                    onClick={() => handleSelectUserFromSearch(u)}
                    sx={{
                      px: 1.5,
                      py: 1,
                      cursor: 'pointer',
                      '&:hover': { bgcolor: 'var(--bg-tertiary)' },
                      borderBottom: '1px solid var(--border)',
                      '&:last-child': { borderBottom: 'none' },
                    }}
                  >
                    <Typography
                      variant="body2"
                      sx={{ color: 'var(--text-primary)', fontWeight: 500 }}
                    >
                      {u.username || u.name || 'Unknown User'}
                    </Typography>
                    <Typography
                      variant="caption"
                      sx={{
                        color: 'var(--text-secondary)',
                        fontFamily: 'monospace',
                      }}
                    >
                      {displayId} {u.email ? `• ${u.email}` : ''}
                    </Typography>
                  </Box>
                );
              })}
            </Paper>
          )}
        </Box>
      </ClickAwayListener>

      {/* QUEUED RECIPIENT CHIPS */}
      {queuedUsers.length > 0 && (
        <Box>
          <Stack direction="row" flexWrap="wrap" gap={1}>
            {queuedUsers.map((u) => (
              <Chip
                key={u.id}
                label={u.username || u.id}
                onDelete={() => onRemoveQueuedUser(u.id)}
                sx={{
                  bgcolor: 'var(--bg-secondary)',
                  color: 'var(--text-primary)',
                }}
              />
            ))}
          </Stack>
        </Box>
      )}
    </Box>
  );
}
