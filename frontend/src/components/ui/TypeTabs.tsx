/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Box, Tab, Tabs } from '@mui/material';

import { FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import type { ProcessedType } from '@/screens/Browse/utils/supportedItemTypesUtils';

type TypeTabsProps = {
  types: ProcessedType[];
  selectedType: string | null;
  onTypeClick: (type: ProcessedType) => void;
  folderId: string;
};

const styles = {
  container: {
    display: 'flex',
    alignItems: 'center',
    flexShrink: 0,
    borderBottom: '1px solid var(--border)',
    minHeight: 32,
  },
  tabs: {
    minHeight: 32,
    '& .MuiTabs-indicator': {
      backgroundColor: 'var(--accent)',
      height: 2,
    },
    '& .MuiTabs-scroller': {
      overflow: 'auto !important',
    },
  },
  tab: {
    minHeight: 32,
    textTransform: 'none' as const,
    fontSize: FONT_SIZES.XS,
    fontWeight: FONT_WEIGHTS.WEIGHT_500,
    color: 'var(--text-primary)',
    opacity: 0.7,
    transition: 'all 0.2s ease',
    '&:hover': {
      opacity: 1,
      backgroundColor: 'var(--bg-tertiary)',
    },
  },
  tabSelected: {
    color: 'var(--accent) !important',
    opacity: 1,
    backgroundColor: 'var(--bg-tertiary)',
    fontWeight: FONT_WEIGHTS.WEIGHT_600,
  },
};

export default function TypeTabs({ types, selectedType, onTypeClick, folderId }: TypeTabsProps) {
  const handleTabChange = (_event: React.SyntheticEvent, newValue: number) => {
    const selectedTypeObj = types[newValue];
    if (selectedTypeObj) {
      onTypeClick(selectedTypeObj);
    }
  };

  // Find the index of the currently selected type
  const selectedTabIndex = types.findIndex((type) => type.display === selectedType);

  return (
    <Box sx={styles.container}>
      <Tabs
        value={selectedTabIndex !== -1 ? selectedTabIndex : false}
        onChange={handleTabChange}
        sx={styles.tabs}
        variant="scrollable"
        scrollButtons="auto"
      >
        {types.map((typeObj) => (
          <Tab
            key={`${folderId}-${typeObj.actualType}`}
            label={`Child ${typeObj.display}`}
            sx={{
              ...styles.tab,
              ...(selectedType === typeObj.display && styles.tabSelected),
            }}
          />
        ))}
      </Tabs>
    </Box>
  );
}
