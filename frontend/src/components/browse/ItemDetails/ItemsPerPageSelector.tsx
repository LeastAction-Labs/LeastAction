/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Box, FormControl, MenuItem, Select, Typography } from '@mui/material';

interface ItemsPerPageSelectorProps {
  itemsPerPage: number;
  onChange: (value: number) => void;
}

const itemsPerPageOptions = [10, 20, 30, 50, 100];

export default function ItemsPerPageSelector({
  itemsPerPage,
  onChange,
}: ItemsPerPageSelectorProps) {
  return (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, ml: 2 }}>
      <Typography variant="body2" sx={{ color: 'var(--text-secondary)' }}>
        Items per page:
      </Typography>
      <FormControl size="small" sx={{ minWidth: 80 }}>
        <Select
          value={itemsPerPage}
          onChange={(e) => onChange(Number(e.target.value))}
          sx={{
            fontSize: '12px',
            height: '32px',
            backgroundColor: 'var(--bg-secondary)',
            '& .MuiSelect-select': {
              padding: '6px 12px',
            },
          }}
        >
          {itemsPerPageOptions.map((option) => (
            <MenuItem key={option} value={option} sx={{ fontSize: '12px' }}>
              {option}
            </MenuItem>
          ))}
        </Select>
      </FormControl>
    </Box>
  );
}
