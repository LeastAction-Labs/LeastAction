/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Box, CircularProgress, Typography } from '@mui/material';

import { FONT_SIZES } from '@/constants';

type LoadingStateProps = {
  message: string;
  size?: number;
};

const styles = {
  container: {
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    gap: 1.5,
    color: 'var(--text-secondary)',
    py: 2,
  },
};

export default function LoadingState({ message, size = 18 }: LoadingStateProps) {
  return (
    <Box sx={styles.container}>
      <CircularProgress size={size} sx={{ color: 'var(--text-secondary)' }} />
      <Typography variant="body2" sx={{ color: 'var(--text-secondary)', fontSize: FONT_SIZES.SM }}>
        {message}
      </Typography>
    </Box>
  );
}
