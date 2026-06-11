/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { InfoOutlined } from '@mui/icons-material';
import { Tooltip } from '@mui/material';

import descriptions from '../../../../config/schema/item_type_description.json';

type Props = {
  itemType: string;
};

export function ItemTypeTooltip({ itemType }: Props) {
  const description = (descriptions as Record<string, string>)[itemType];
  if (!description) return null;

  return (
    <Tooltip title={description} arrow placement="right">
      <InfoOutlined
        sx={{
          fontSize: 13,
          color: 'var(--text-secondary)',
          cursor: 'default',
          flexShrink: 0,
          '&:hover': { color: 'var(--text-primary)' },
        }}
      />
    </Tooltip>
  );
}
