/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import React, { useEffect, useState } from 'react';

import { Close as CloseIcon, Edit as EditIcon, Check as SaveIcon } from '@mui/icons-material';
import {
  Box,
  CircularProgress,
  IconButton,
  MenuItem,
  Paper,
  Select,
  Tab,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Tabs,
  Typography,
} from '@mui/material';

import { FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import { useUserCache } from '@/contexts/UserCacheContext';
import { updateItemAccess } from '@/screens/Browse/utils';
import type { AccessRelationsResponse } from '@/services/access.service';
import { getUsersGroups } from '@/services/access.service';
import {
  getBreadcrumbString,
  getBreadcrumbs,
  getCatalogItemById,
} from '@/services/catalog.service';
import { searchGroups } from '@/services/group.service';

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
    overflow: 'auto',
    bgcolor: 'transparent',
    boxShadow: 'none',
    borderRadius: 0,
    '& .MuiTableCell-root': {
      color: 'var(--text-primary)',
      borderColor: 'rgba(255, 255, 255, 0.08)',
      fontSize: FONT_SIZES.SM,
      py: 1.5,
      px: 2,
    },
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
};

type PermissionTabValue = 'own' | 'edit' | 'view';

export default function UsersGroupsTable() {
  const { userCache, fetchMissingUsers } = useUserCache();

  // --- State Setup ---
  const [allData, setAllData] = useState<AccessRelationsResponse[]>([]);
  const [activeTab, setActiveTab] = useState<PermissionTabValue>('own');
  const [loading, setLoading] = useState(true);
  const [breadcrumbs, setBreadcrumbs] = useState<Map<string, string>>(new Map());
  const [groupNameMap, setGroupNameMap] = useState<Map<string, string>>(new Map());
  const [editingId, setEditingId] = useState<string | null>(null);
  const [tempPermission, setTempPermission] = useState<string>('');
  const [actionLoading, setActionLoading] = useState<string | null>(null);

  // ---- Fetch access data based on Permission Tab ----
  const fetchAccessData = async (permissionLevel: PermissionTabValue) => {
    try {
      setLoading(true);
      const data = await getUsersGroups(permissionLevel);
      setAllData(data);

      const uniqueUserLauis = [
        ...new Set(data.filter((d) => d.subject_type === 'user').map((d) => d.subject_laui)),
      ];
      const uniqueGroupLauis = [
        ...new Set(data.filter((d) => d.subject_type === 'group').map((d) => d.subject_laui)),
      ];
      const uniqueItemLauis = [...new Set(data.map((item) => item.item_laui))];

      // 1. Pre-fetch missing user definitions for cache context
      if (uniqueUserLauis.length > 0) {
        fetchMissingUsers(uniqueUserLauis);
      }

      // 2. Pre-fetch group display labels
      if (uniqueGroupLauis.length > 0) {
        try {
          const groupsRes = await searchGroups({
            group_lauis: uniqueGroupLauis,
            page: 1,
            per_page: uniqueGroupLauis.length,
          });

          const nameMap = new Map<string, string>();
          (groupsRes.groups || []).forEach((g: any) => nameMap.set(g.laui || g.id, g.name));
          setGroupNameMap(nameMap);
        } catch (groupErr) {
          console.error('Failed to fetch groups data:', groupErr);
        }
      }

      // 3. Resolve path breadcrumbs
      const breadcrumbMap = new Map<string, string>();
      await Promise.all(
        uniqueItemLauis.map(async (itemLaui) => {
          try {
            const response = await getBreadcrumbs(itemLaui);
            const itemName = (await getCatalogItemById(itemLaui)).name;
            if (response.items && response.items.length > 0) {
              const catalogNode = response.items[0];
              let breadcrumbPath = getBreadcrumbString(catalogNode);
              breadcrumbPath += `/${itemName}`;
              breadcrumbMap.set(itemLaui, breadcrumbPath);
            } else {
              breadcrumbMap.set(itemLaui, `/${itemName}`);
            }
          } catch {
            breadcrumbMap.set(itemLaui, 'Unknown Path');
          }
        }),
      );
      setBreadcrumbs(breadcrumbMap);
    } catch (error) {
      console.error('Failed to fetch access data:', error);
    } finally {
      setLoading(false);
    }
  };

  useEffect(() => {
    void fetchAccessData(activeTab);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [activeTab]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: PermissionTabValue) => {
    setActiveTab(newValue);
    setEditingId(null);
  };

  // ---- Save/Permissions translation handlers ----
  const permissionRelationMap: Record<string, string> = {
    own: 'owners',
    edit: 'editors',
    view: 'viewers',
    revoke: '',
  };

  const handleSaveClick = async (item: AccessRelationsResponse) => {
    const uniqueId = `${item.item_laui}-${item.subject_laui}`;
    setActionLoading(uniqueId);
    try {
      await updateItemAccess({
        itemLaui: item.item_laui,
        userLaui: item.subject_type === 'group' ? 'G' + item.subject_laui : 'U' + item.subject_laui,
        currentRelation: permissionRelationMap[item.subject_permission],
        newRelation: permissionRelationMap[tempPermission],
      });
      setEditingId(null);
      await fetchAccessData(activeTab);
    } catch (error) {
      console.error('Save failed', error);
    } finally {
      setActionLoading(null);
    }
  };

  const getPermissionOptions = (currentPerm: string) => {
    if (currentPerm === 'own') return ['own', 'edit', 'view', 'revoke'];
    return ['edit', 'view', 'revoke'];
  };

  // ---- Group active data by Subject LAUI to match original nested row UI layout ----
  const groupedData = allData.reduce(
    (acc, item) => {
      if (!acc[item.subject_laui]) acc[item.subject_laui] = [];
      acc[item.subject_laui].push(item);
      return acc;
    },
    {} as Record<string, AccessRelationsResponse[]>,
  );

  const renderAccessTable = () => {
    const groupedEntries = Object.entries(groupedData);

    return (
      <TableContainer component={Paper} sx={styles.tableContainer}>
        <Table stickyHeader>
          <TableHead sx={styles.tableHead}>
            <TableRow>
              {/* Universal Header columns layout matching the target structure */}
              <TableCell>Identity Name</TableCell>
              <TableCell>Details / Email</TableCell>
              <TableCell>Item Path</TableCell>
              <TableCell>Permission</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {groupedEntries.length > 0 ? (
              groupedEntries.map(([subjectLaui, items]) => {
                // Peek first record properties to identify subject class type rules
                const isUser = items[0]?.subject_type === 'user';
                const cachedUser = userCache[subjectLaui] || {};

                const displayUsername = isUser ? cachedUser.username || 'Loading...' : null;
                const displayEmail = isUser ? cachedUser.email || 'Loading...' : null;
                const displayGroupName = !isUser
                  ? groupNameMap.get(subjectLaui) || 'Loading...'
                  : null;

                const headerLabel = isUser ? displayUsername : displayGroupName;
                const typeLabel = isUser ? 'User' : 'Group';

                return (
                  <React.Fragment key={`group-${subjectLaui}`}>
                    {/* Collapsible/Section grouping header block line identical to original UI */}
                    <TableRow sx={styles.groupHeaderRow}>
                      <TableCell colSpan={4}>
                        {typeLabel}: {headerLabel} ({items.length} items)
                      </TableCell>
                    </TableRow>

                    {/* Collection list mapped for child rows */}
                    {items.map((item, index) => {
                      const uniqueId = `${item.item_laui}-${item.subject_laui}`;
                      const isEditing = editingId === uniqueId;
                      const isRowLoading = actionLoading === uniqueId;
                      const hasChanged = tempPermission !== item.subject_permission;

                      return (
                        <TableRow key={`${uniqueId}-${index}`} sx={styles.tableRow}>
                          {/* Subject Identity Columns */}
                          <TableCell>{isUser ? displayUsername : displayGroupName}</TableCell>
                          <TableCell>
                            <Typography variant="body2" sx={{ color: 'var(--text-secondary)' }}>
                              {isUser ? displayEmail : '—'}
                            </Typography>
                          </TableCell>

                          {/* Breadcrumb Path Info */}
                          <TableCell>
                            {breadcrumbs.get(item.item_laui) || 'Loading path...'}
                          </TableCell>

                          {/* Inline Permission Change Controls */}
                          <TableCell>
                            <Box
                              sx={{
                                display: 'flex',
                                alignItems: 'center',
                                gap: 1,
                              }}
                            >
                              {isEditing ? (
                                <>
                                  <Select
                                    size="small"
                                    value={tempPermission}
                                    onChange={(e) => setTempPermission(e.target.value)}
                                    sx={{
                                      color: 'var(--text-primary)',
                                      height: 30,
                                      fontSize: FONT_SIZES.SM,
                                      '.MuiOutlinedInput-notchedOutline': {
                                        borderColor: 'var(--border)',
                                      },
                                    }}
                                  >
                                    {getPermissionOptions(item.item_permission).map((opt) => (
                                      <MenuItem key={opt} value={opt}>
                                        {opt}
                                      </MenuItem>
                                    ))}
                                  </Select>
                                  {isRowLoading ? (
                                    <CircularProgress size={20} />
                                  ) : (
                                    <>
                                      {hasChanged && (
                                        <IconButton
                                          size="small"
                                          onClick={() => void handleSaveClick(item)}
                                          sx={{
                                            color: 'var(--accent)',
                                          }}
                                        >
                                          <SaveIcon fontSize="small" />
                                        </IconButton>
                                      )}
                                      <IconButton
                                        size="small"
                                        onClick={() => setEditingId(null)}
                                        sx={{
                                          color: 'var(--text-secondary)',
                                        }}
                                      >
                                        <CloseIcon fontSize="small" />
                                      </IconButton>
                                    </>
                                  )}
                                </>
                              ) : (
                                <>
                                  {item.subject_permission}
                                  <IconButton
                                    size="small"
                                    onClick={() => {
                                      setEditingId(uniqueId);
                                      setTempPermission(item.subject_permission);
                                    }}
                                    sx={{
                                      ml: 1,
                                      color: 'var(--text-secondary)',
                                      opacity: 0.7,
                                    }}
                                  >
                                    <EditIcon sx={{ fontSize: 16 }} />
                                  </IconButton>
                                </>
                              )}
                            </Box>
                          </TableCell>
                        </TableRow>
                      );
                    })}
                  </React.Fragment>
                );
              })
            ) : (
              <TableRow>
                <TableCell colSpan={4}>
                  <Box sx={styles.emptyState}>
                    <Typography variant="body2">No records found for "{activeTab}"</Typography>
                  </Box>
                </TableCell>
              </TableRow>
            )}
          </TableBody>
        </Table>
      </TableContainer>
    );
  };

  if (loading) {
    return (
      <Box sx={styles.emptyState}>
        <Typography variant="body2">Loading...</Typography>
      </Box>
    );
  }

  return (
    <Box sx={styles.container}>
      <Box sx={styles.tabsContainer}>
        <Tabs
          value={activeTab}
          onChange={handleTabChange}
          sx={{
            '& .MuiTab-root': {
              color: 'var(--text-secondary)',
              '&.Mui-selected': { color: 'var(--accent)' },
              fontSize: FONT_SIZES.SM,
              textTransform: 'capitalize',
            },
            '& .MuiTabs-indicator': { backgroundColor: 'var(--accent)' },
          }}
        >
          <Tab label="Own" value="own" />
          <Tab label="Edit" value="edit" />
          <Tab label="View" value="view" />
        </Tabs>
      </Box>
      {renderAccessTable()}
    </Box>
  );
}
