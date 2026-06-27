/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import {
  Box,
  Paper,
  Table,
  TableBody,
  TableCell,
  TableContainer,
  TableHead,
  TableRow,
  Typography,
} from '@mui/material';

import { FONT_SIZES, FONT_WEIGHTS } from '../../../constants';
import type { GroupItem, Relation } from '../../../services/group.service';
import Pagination from '../Pagination';
import type { GroupDetailsData } from './GroupDetails';

const styles = {
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
  expandedRow: {
    bgcolor: 'var(--bg-tertiary)',
  },
  membersCell: {
    bgcolor: 'var(--bg-secondary)',
    borderTop: '1px solid var(--border)',
  },
  emptyState: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    p: 4,
    color: 'var(--text-secondary)',
  },
};

interface GroupsTableProps {
  groups: GroupItem[];
  loading?: boolean;
  userRelation: Relation;
  selectedGroupLaui: string | null;
  onSelectGroup: (laui: string) => void;
  get_group: (laui: string) => Promise<GroupDetailsData>;
  update_group: (name: string, description: string, accessPatch: any) => Promise<void>;
  currentPage: number;
  hasNext: boolean;
  hasPrevious: boolean;
  onPageChange: (page: number) => void;
}

export default function GroupsTable({
  groups,
  loading = false,
  userRelation: _userRelation,
  selectedGroupLaui: _selectedGroupLaui,
  onSelectGroup,
  get_group: _get_group,
  update_group: _update_group,
  currentPage,
  hasNext,
  hasPrevious,
  onPageChange,
}: GroupsTableProps) {
  if (loading) {
    return (
      <Box sx={styles.emptyState}>
        <Typography variant="body2">Loading groups...</Typography>
      </Box>
    );
  }

  if (groups.length === 0) {
    return (
      <Box sx={styles.emptyState}>
        <Typography variant="body2">No groups found</Typography>
      </Box>
    );
  }

  return (
    <>
      <TableContainer component={Paper} sx={styles.tableContainer}>
        <Table stickyHeader>
          <TableHead sx={styles.tableHead}>
            <TableRow>
              <TableCell>Group Name</TableCell>
            </TableRow>
          </TableHead>
          <TableBody>
            {groups.map((group) => (
              <TableRow
                key={group.laui}
                sx={styles.tableRow}
                onClick={() => onSelectGroup(group.laui)}
              >
                <TableCell>
                  <Typography
                    variant="body2"
                    sx={{
                      fontWeight: FONT_WEIGHTS.MEDIUM,
                      color: 'var(--text-primary)',
                    }}
                  >
                    {group.name}
                  </Typography>
                </TableCell>
              </TableRow>
            ))}
          </TableBody>
        </Table>
      </TableContainer>
      <Pagination
        currentPage={currentPage}
        hasNext={hasNext}
        hasPrevious={hasPrevious}
        onPageChange={onPageChange}
      />
    </>
  );
}
