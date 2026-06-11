/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import AddIcon from '@mui/icons-material/Add';
import { Box, Button, Tab, Tabs, Tooltip, Typography } from '@mui/material';

import { FONT_SIZES, FONT_WEIGHTS } from '../../../constants';
import type { Relation } from '../../../services/group.service';
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
import type { Group } from './GroupsTable';
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
  const [groups, setGroups] = useState<Group[]>([]);
  const [loading, setLoading] = useState(true);
  const [isModalOpen, setIsModalOpen] = useState(false);
  const [modalLoading, setModalLoading] = useState(false);
  const [selectedGroupLaui, setSelectedGroupLaui] = useState<string | null>(null);

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

  // Fetch groups based on active tab
  useEffect(() => {
    const fetchGroups = async () => {
      try {
        setLoading(true);
        const relation = getRelationForTab(activeTab);

        const response = await getGroups(relation);

        // Transform the response to Group format
        // The backend returns { groups: { id, name }[], next_page_token: string }
        const transformedGroups: Group[] = response.groups.map((group) => ({
          laui: group.id,
          name: group.name,
          members: [], // Will be populated when viewing details
        }));

        setGroups(transformedGroups);
      } catch (error) {
        console.error('Failed to fetch groups:', error);
        setGroups([]);
      } finally {
        setLoading(false);
      }
    };

    void fetchGroups();
  }, [activeTab]);

  const handleTabChange = (_event: React.SyntheticEvent, newValue: TabValue) => {
    setActiveTab(newValue);
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

      // Refresh the groups list for the current tab
      const relation = getRelationForTab(activeTab);
      const response = await getGroups(relation);
      const transformedGroups: Group[] = response.groups.map((group) => ({
        laui: group.id,
        name: group.name,
        members: [],
      }));
      setGroups(transformedGroups);
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
                  sx={{
                    display: 'flex',
                    width: '100%',
                    justifyContent: 'center',
                  }}
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
                  sx={{
                    display: 'flex',
                    width: '100%',
                    justifyContent: 'center',
                  }}
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
                  sx={{
                    display: 'flex',
                    width: '100%',
                    justifyContent: 'center',
                  }}
                >
                  Member
                </Box>
              </Tooltip>
            }
          />
        </Tabs>
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
