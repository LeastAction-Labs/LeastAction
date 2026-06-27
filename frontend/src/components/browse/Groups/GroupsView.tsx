/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import AddIcon from '@mui/icons-material/Add';
import {
  Box,
  Button,
  FormControl,
  MenuItem,
  Select,
  type SelectChangeEvent,
  Tab,
  Tabs,
  Tooltip,
  Typography,
} from '@mui/material';

import { useAuth } from '@/contexts/AuthContext';

import { FONT_SIZES, FONT_WEIGHTS } from '../../../constants';
import type { GroupItem, Relation } from '../../../services/group.service';
import {
  createGroup,
  getGroup,
  getGroups,
  searchGroups,
  updateGroup,
} from '../../../services/group.service';
import type { GroupDetailsData } from './GroupDetails';
import GroupDetails from './GroupDetails';
import GroupModal from './GroupModal';
import GroupsTable from './GroupsTable';

const styles = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100%',
    overflow: 'hidden',
  },
  header: {
    px: 3,
    py: 2,
    borderBottom: 1,
    borderColor: 'var(--border)',
    bgcolor: 'var(--bg-secondary)',
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  headerContent: {
    display: 'flex',
    flexDirection: 'column',
  },
  headerTitle: {
    color: 'var(--text-primary)',
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
    fontSize: FONT_SIZES.LG,
  },
  headerSubtitle: {
    color: 'var(--text-secondary)',
    fontSize: FONT_SIZES.SM,
    mt: 0.5,
  },
  createButton: {
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
  },
  buttonIcon: {
    mr: 0.5,
    fontSize: '1.1rem',
  },
  tabsContainer: {
    borderBottom: 1,
    borderColor: 'var(--border)',
    bgcolor: 'var(--bg-secondary)',
    px: 3,
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  tabs: {
    minHeight: 32,
    '& .MuiTab-root': {
      color: 'var(--text-secondary)',
      textTransform: 'none' as const,
      fontWeight: FONT_WEIGHTS.WEIGHT_400,
      fontSize: FONT_SIZES.XS,
      minHeight: 32,
    },
    '& .Mui-selected': {
      color: 'var(--accent) !important',
      fontWeight: `${FONT_WEIGHTS.WEIGHT_600} !important`,
    },
    '& .MuiTabs-indicator': {
      backgroundColor: 'var(--accent)',
      height: '2px',
    },
  },
  perPageContainer: {
    display: 'flex',
    alignItems: 'center',
    gap: 1,
  },
  perPageLabel: {
    color: 'var(--text-secondary)',
    fontSize: FONT_SIZES.XS,
  },
  perPageSelect: {
    height: 28,
    fontSize: FONT_SIZES.XS,
    color: 'var(--text-primary)',
    borderColor: 'var(--border)',
    '& .MuiSelect-select': {
      py: 0.5,
      paddingLeft: 1,
      paddingRight: '24px !important',
    },
  },
  content: {
    flex: 1,
    overflow: 'hidden',
    display: 'flex',
    flexDirection: 'column',
  },
};

interface GroupsViewProps {
  onCreateGroup?: () => void;
}

type TabValue = 0 | 1 | 2;

export default function GroupsView({ onCreateGroup }: GroupsViewProps) {
  const [activeTab, setActiveTab] = useState<TabValue>(0);
  const [groups, setGroups] = useState<GroupItem[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalLoading, setModalLoading] = useState(false);
  const [selectedGroupLaui, setSelectedGroupLaui] = useState<string | null>(null);

  // Pagination state
  const [currentPage, setCurrentPage] = useState(1);
  const [perPage, setPerPage] = useState(5);
  const [hasNext, setHasNext] = useState(false);
  const [nextPageToken, setNextPageToken] = useState<string | null>(null);
  const [pageTokens, setPageTokens] = useState<(string | null)[]>([null]); // Stack for token-based pagination

  const { authState } = useAuth();
  const { user } = authState;
  const isRootUser = user?.user_type === 'root';

  // Map tab index to relation
  const getRelationForTab = (tab: TabValue): Relation => {
    switch (tab) {
      case 0:
        return 'owners';
      case 1:
        return 'editors';
      case 2:
        return 'viewers';
    }
  };

  // Fetch groups based on active tab and pagination
  const fetchGroups = async (page: number = 1, pageToken: string | null = null) => {
    try {
      setLoading(true);
      const relation = getRelationForTab(activeTab);

      // Build request params based on user type
      const params: any = {
        relation,
        per_page: perPage,
      };

      if (isRootUser) {
        // Root users: page-number based pagination
        params.page = page;
      } else {
        // Non-root users: token-based pagination
        if (pageToken) {
          params.page_token = pageToken;
        }
      }

      const response = await getGroups(params);

      setGroups(response.groups);
      setHasNext(response.has_next);
      setNextPageToken(response.next_page_token || null);
    } catch (error) {
      console.error('Failed to fetch groups:', error);
      setGroups([]);
      setHasNext(false);
      setNextPageToken(null);
    } finally {
      setLoading(false);
    }
  };

  // Reset pagination when tab or perPage changes
  useEffect(() => {
    setCurrentPage(1);
    setPageTokens([null]);
    setNextPageToken(null);
    setHasNext(false);
    void fetchGroups(1, null);
  }, [activeTab, perPage]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: TabValue) => {
    setActiveTab(newValue);
  };

  const handlePerPageChange = (event: SelectChangeEvent<number>) => {
    setPerPage(Number(event.target.value));
  };

  const handleOpenModal = () => {
    setIsModalOpen(true);
  };

  const handleCloseModal = () => {
    setIsModalOpen(false);
  };

  const handleSaveGroup = async (groupData: {
    name: string;
    description: string;
    members: string[];
    admins: string[];
  }) => {
    try {
      setModalLoading(true);

      const res: any = await searchGroups({ name: groupData.name, exact_match: true });

      if (res.groups.length) {
        setModalLoading(false);
        return;
      }

      // Call the createGroup service
      await createGroup(groupData);

      // Close modal
      handleCloseModal();

      // Refresh the groups list - reset to first page
      setCurrentPage(1);
      setPageTokens([null]);
      setNextPageToken(null);
      await fetchGroups(1, null);
    } catch (error: any) {
      console.error('Failed to create group:', error);
      throw error; // Re-throw so modal can handle the error
    } finally {
      setModalLoading(false);
    }
  };

  const handleCreateGroup = () => {
    if (onCreateGroup) {
      onCreateGroup();
    } else {
      handleOpenModal();
    }
  };

  // Pagination handler
  const handlePageChange = async (newPage: number) => {
    if (isRootUser) {
      // Root users: simple page number navigation
      setCurrentPage(newPage);
      await fetchGroups(newPage, null);
    } else {
      // Non-root users: token-based navigation
      if (newPage > currentPage) {
        // Going forward
        if (nextPageToken) {
          const newTokens = [...pageTokens, nextPageToken];
          setPageTokens(newTokens);
          setCurrentPage(newPage);
          await fetchGroups(newPage, nextPageToken);
        }
      } else if (newPage < currentPage) {
        // Going backward
        const tokenForPreviousPage = pageTokens[newPage - 1] || null;
        setCurrentPage(newPage);
        await fetchGroups(newPage, tokenForPreviousPage);
      }
    }
  };

  // Function to fetch group details by LAUI
  const get_group = async (laui: string): Promise<GroupDetailsData> => {
    try {
      const response = await getGroup(laui);
      return response;
    } catch (error) {
      console.error('Error fetching group details:', error);
      throw error;
    }
  };

  // Function to update group details using updateGroup with access_patch
  const update_group = async (
    name: string,
    description: string,
    accessPatch: any,
  ): Promise<void> => {
    try {
      await updateGroup(name, description, accessPatch);
    } catch (error) {
      console.error('Error updating group:', error);
      throw error;
    }
  };

  // Show GroupDetails if a group is selected
  if (selectedGroupLaui) {
    return (
      <Box sx={styles.container}>
        <GroupDetails
          groupLaui={selectedGroupLaui}
          onBack={() => setSelectedGroupLaui(null)}
          userRelation={getRelationForTab(activeTab)}
          get_group={get_group}
          update_group={update_group}
        />
      </Box>
    );
  }

  return (
    <Box sx={styles.container}>
      <Box sx={styles.header}>
        <Box sx={styles.headerContent}>
          <Typography sx={styles.headerTitle}>Manage Groups</Typography>
          <Typography sx={styles.headerSubtitle}>View and manage group memberships</Typography>
        </Box>
        <Button
          variant="contained"
          onClick={handleCreateGroup}
          sx={styles.createButton}
          startIcon={<AddIcon sx={styles.buttonIcon} />}
        >
          Create Group
        </Button>
      </Box>

      <Box sx={styles.tabsContainer}>
        {!isRootUser ? (
          <Tabs value={activeTab} onChange={handleTabChange} sx={styles.tabs}>
            <Tab
              label={
                <Tooltip
                  title="Groups where you are the owner and have full control"
                  placement="top"
                  arrow
                >
                  <Box
                    component="span"
                    sx={{ display: 'flex', width: '100%', justifyContent: 'center' }}
                  >
                    Owner
                  </Box>
                </Tooltip>
              }
            />
            <Tab
              label={
                <Tooltip
                  title="Groups where you have administrative privileges to manage settings"
                  placement="top"
                  arrow
                >
                  <Box
                    component="span"
                    sx={{ display: 'flex', width: '100%', justifyContent: 'center' }}
                  >
                    Admin
                  </Box>
                </Tooltip>
              }
            />
            <Tab
              label={
                <Tooltip
                  title="Groups where you are a standard participating member"
                  placement="top"
                  arrow
                >
                  <Box
                    component="span"
                    sx={{ display: 'flex', width: '100%', justifyContent: 'center' }}
                  >
                    Member
                  </Box>
                </Tooltip>
              }
            />
          </Tabs>
        ) : (
          <Box /> // Empty placeholder to keep layout consistent when tabs are hidden for root user
        )}

        <Box sx={styles.perPageContainer}>
          <Typography sx={styles.perPageLabel}>Rows per page:</Typography>
          <FormControl variant="outlined" size="small">
            <Select value={perPage} onChange={handlePerPageChange} sx={styles.perPageSelect}>
              <MenuItem value={5}>5</MenuItem>
              <MenuItem value={10}>10</MenuItem>
              <MenuItem value={25}>25</MenuItem>
              <MenuItem value={50}>50</MenuItem>
            </Select>
          </FormControl>
        </Box>
      </Box>

      <Box sx={styles.content}>
        <GroupsTable
          groups={groups}
          loading={loading}
          userRelation={getRelationForTab(activeTab)}
          selectedGroupLaui={selectedGroupLaui}
          onSelectGroup={setSelectedGroupLaui}
          get_group={get_group}
          update_group={update_group}
          currentPage={currentPage}
          hasNext={hasNext}
          hasPrevious={currentPage > 1}
          onPageChange={handlePageChange}
        />
      </Box>

      <GroupModal
        open={isModalOpen}
        onClose={handleCloseModal}
        onSave={handleSaveGroup}
        loading={modalLoading}
      />
    </Box>
  );
}
