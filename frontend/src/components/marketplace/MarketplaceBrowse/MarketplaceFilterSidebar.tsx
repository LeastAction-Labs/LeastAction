/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import SearchIcon from '@mui/icons-material/Search';
import { Box, InputAdornment, TextField, Typography } from '@mui/material';

import { Chip } from '@/components/ui';
import { SectionTitle } from '@/components/ui/sidebarParts';
import type { ParsedMarketplaceQuery } from '@/utils/marketplaceSearch';
import { removeFieldFilter } from '@/utils/marketplaceSearch';

export interface MarketplaceFacets {
  types: string[];
  categories: string[];
  tags: string[];
}

interface MarketplaceFilterSidebarProps {
  searchQuery: string;
  onSearchChange: (query: string) => void;
  parsedQuery: ParsedMarketplaceQuery;
  facets: MarketplaceFacets;
  onToggleFilter: (field: string, value: string) => void;
}

function FacetSection({
  title,
  field,
  values,
  active,
  onToggle,
  variant,
}: Readonly<{
  title: string;
  field: string;
  values: string[];
  active: string[];
  onToggle: (field: string, value: string) => void;
  variant: 'type' | 'category' | 'tag';
}>) {
  if (values.length === 0) return null;
  return (
    <Box sx={{ mb: 2.5 }}>
      <SectionTitle>{title}</SectionTitle>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
        {values.map((value) => {
          const isActive = active.includes(value);
          return (
            <Chip
              key={value}
              label={variant === 'tag' ? `#${value}` : value}
              variant={variant}
              clickable
              onClick={() => onToggle(field, value)}
              sx={
                isActive
                  ? { bgcolor: 'var(--accent)', color: '#fff', fontWeight: 600, border: 'none' }
                  : {
                      bgcolor: 'var(--bg-primary)',
                      color: 'var(--text-secondary)',
                      fontWeight: 400,
                      border: '1px solid var(--border-color)',
                    }
              }
            />
          );
        })}
      </Box>
    </Box>
  );
}

export default function MarketplaceFilterSidebar({
  searchQuery,
  onSearchChange,
  parsedQuery,
  facets,
  onToggleFilter,
}: Readonly<MarketplaceFilterSidebarProps>) {
  const activeTypes = parsedQuery.fieldFilters.item_type ?? [];
  const activeCategories = parsedQuery.fieldFilters.category ?? [];
  const activeTags = parsedQuery.fieldFilters.tags ?? [];

  const handleToggle = (field: string, backendField: string, value: string, active: string[]) => {
    if (active.includes(value)) {
      onSearchChange(removeFieldFilter(searchQuery, backendField, value));
    } else {
      onToggleFilter(field, value);
    }
  };

  return (
    <Box
      sx={{
        width: 260,
        flexShrink: 0,
        height: '100%',
        overflow: 'auto',
        borderRight: 1,
        borderColor: 'var(--border-color)',
        bgcolor: 'var(--bg-secondary)',
        p: 2,
      }}
    >
      <Typography sx={{ fontSize: '15px', fontWeight: 700, color: 'var(--text-primary)', mb: 1.5 }}>
        Marketplace
      </Typography>

      <Box sx={{ mb: 2.5 }}>
        <SectionTitle>Search</SectionTitle>
        <TextField
          fullWidth
          size="small"
          placeholder='Search… or use tag:"x"'
          value={searchQuery}
          onChange={(e) => onSearchChange(e.target.value)}
          slotProps={{
            input: {
              startAdornment: (
                <InputAdornment position="start">
                  <SearchIcon sx={{ fontSize: 18, color: 'var(--text-secondary)' }} />
                </InputAdornment>
              ),
            },
          }}
          sx={{
            '& .MuiOutlinedInput-root': {
              fontSize: '13px',
              bgcolor: 'var(--bg-primary)',
              color: 'var(--text-primary)',
              '& fieldset': { borderColor: 'var(--border-color)' },
              '&:hover fieldset': { borderColor: 'var(--accent)' },
              '&.Mui-focused fieldset': { borderColor: 'var(--accent)' },
            },
          }}
        />
      </Box>

      <FacetSection
        title="Types"
        field="type"
        values={facets.types}
        active={activeTypes}
        variant="type"
        onToggle={(field, value) => handleToggle(field, 'item_type', value, activeTypes)}
      />
      <FacetSection
        title="Categories"
        field="category"
        values={facets.categories}
        active={activeCategories}
        variant="category"
        onToggle={(field, value) => handleToggle(field, 'category', value, activeCategories)}
      />
      <FacetSection
        title="Tags"
        field="tag"
        values={facets.tags}
        active={activeTags}
        variant="tag"
        onToggle={(field, value) => handleToggle(field, 'tags', value, activeTags)}
      />
    </Box>
  );
}
