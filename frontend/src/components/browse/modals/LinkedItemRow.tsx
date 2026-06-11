/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Box, Typography } from '@mui/material';

interface LinkedItemRowProps {
  item: { laui?: string; name?: string; item_type?: string };
  index?: number;
}

export default function LinkedItemRow({ item, index = 0 }: LinkedItemRowProps) {
  return (
    <Box
      key={item.laui || index}
      sx={{
        borderLeft: '3px solid',
        borderColor: 'error.main',
        pl: 2,
        py: 0.5,
      }}
    >
      <Typography variant="subtitle1" sx={{ fontWeight: 'bold', lineHeight: 1.2 }}>
        {item.name}
      </Typography>
      <Typography variant="caption" sx={{ color: 'var(--text-secondary)', display: 'block' }}>
        Type: {item.item_type} • LAUI: {item.laui}
      </Typography>
    </Box>
  );
}
