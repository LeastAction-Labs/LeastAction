/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Typography } from '@mui/material';

type EmptyStateProps = {
  message: string;
};

const styles = {
  emptyState: {
    color: 'var(--text-primary)',
    mb: 2,
  },
};

export default function EmptyState({ message }: EmptyStateProps) {
  return (
    <Typography variant="body2" sx={styles.emptyState}>
      {message}
    </Typography>
  );
}
