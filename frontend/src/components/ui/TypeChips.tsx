/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Box, Chip } from '@mui/material';

import { FONT_SIZES, FONT_WEIGHTS } from '@/constants';
import type { ProcessedType } from '@/screens/Browse/utils/supportedItemTypesUtils';

type TypeChipsProps = {
  types: ProcessedType[];
  selectedType: string | null;
  onTypeClick: (type: ProcessedType) => void;
  folderId: string;
};

const styles = {
  container: {
    display: 'flex',
    flexWrap: 'wrap' as const,
    gap: 1,
    alignItems: 'center',
    flexShrink: 0,
    maxHeight: '80px',
    overflowY: 'auto' as const,
    paddingBottom: 0.5,
  },
  chip: {
    bgcolor: 'var(--bg-secondary)',
    color: 'var(--text-primary)',
    fontSize: FONT_SIZES.XS,
    fontWeight: FONT_WEIGHTS.WEIGHT_500,
    border: '1px solid rgba(255, 255, 255, 0.1)',
    cursor: 'pointer',
    transition: 'all 0.2s ease',
  },
  chipSelected: {
    bgcolor: 'var(--accent)',
    color: 'white',
    border: '1px solid var(--accent)',
  },
  chipHover: {
    bgcolor: 'var(--bg-tertiary)',
    borderColor: 'rgba(255, 255, 255, 0.2)',
  },
};

export default function TypeChips({ types, selectedType, onTypeClick, folderId }: TypeChipsProps) {
  return (
    <Box sx={styles.container}>
      {types.map((typeObj) => {
        const isSelected = selectedType === typeObj.display;
        return (
          <Chip
            key={`${folderId}-${typeObj.actualType}`}
            label={typeObj.display}
            onClick={() => onTypeClick(typeObj)}
            sx={{
              ...styles.chip,
              ...(isSelected && styles.chipSelected),
              '&:hover': {
                ...(isSelected ? styles.chipSelected : styles.chipHover),
              },
            }}
          />
        );
      })}
    </Box>
  );
}
