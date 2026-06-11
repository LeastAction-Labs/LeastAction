/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import { Autocomplete, CircularProgress, TextField } from '@mui/material';

import { CatalogType, useGlobal } from '@/contexts/GlobalContext';
import { searchCatalogItems } from '@/services/catalog.service';

interface LauiDropdownProps {
  fieldName: string;
  value: string;
  onChange: (fieldName: string, value: any) => void;
}

interface DropdownOption {
  label: string;
  value: string;
}

export const LauiDropdown = ({ fieldName, value, onChange }: LauiDropdownProps) => {
  const { catalogType } = useGlobal();

  const isMarketplaceCatalog = catalogType === CatalogType.MARKETPLACE;

  const [loading, setLoading] = useState(false);
  const [options, setOptions] = useState<DropdownOption[]>([]);

  // Determine item_type from field name
  const getItemType = (fieldName: string): string => {
    const normalizedFieldName = fieldName.toLowerCase().replace(/[_\s]/g, '');

    if (normalizedFieldName === 'accountlaui') {
      return 'folder.account';
    } else if (normalizedFieldName === 'projectlaui') {
      return 'folder.project';
    } else if (normalizedFieldName === 'workflowfolderlaui') {
      return 'folder.workflow';
    } else {
      // For other fields like "operator_laui", "connection_laui", etc.
      // Extract the prefix before "_laui" or "laui"
      // Extract the prefix before "_laui", "laui", "_lauis", or "lauis"
      const match = fieldName.match(/^(.+?)(_?lauis?)$/i);
      if (match) {
        // match[1] contains everything before the laui suffix
        return match[1].toLowerCase();
      }
      // Fallback replacement using the same optional underscore and optional 's'
      return fieldName.replace(/_?lauis?$/i, '').toLowerCase();
    }
  };

  useEffect(() => {
    const fetchItems = async () => {
      setLoading(true);
      try {
        const itemType = getItemType(fieldName);
        const response = await searchCatalogItems(itemType, isMarketplaceCatalog);

        //console.log('Search response for', fieldName, ':', response);

        // The search endpoint returns items directly, not wrapped in CatalogNode
        const items = response.items || response;

        const formattedOptions = items.map((item: any) => {
          // Handle both formats: direct item or CatalogNode
          const actualItem = item.item || item;
          const itemLaui = actualItem._laui || actualItem.laui;
          const itemName = actualItem.name || itemLaui;

          return {
            label: `${itemName} (${itemLaui})`,
            value: itemLaui,
          };
        });

        //console.log('Formatted options:', formattedOptions);
        setOptions(formattedOptions);
      } catch (error) {
        console.error(`Error fetching items for ${fieldName}:`, error);
        setOptions([]);
      } finally {
        setLoading(false);
      }
    };

    void fetchItems();
  }, [fieldName]);

  const selectedOption = options.find((opt) => opt.value === value) || null;

  return (
    <Autocomplete
      fullWidth
      size="small"
      options={options}
      loading={loading}
      value={selectedOption}
      onChange={(_, newValue) => {
        onChange(fieldName, newValue?.value || '');
      }}
      getOptionLabel={(option) => option.label}
      isOptionEqualToValue={(option, value) => option.value === value.value}
      renderInput={(params) => (
        <TextField
          {...params}
          placeholder={`Select ${fieldName}...`}
          InputProps={{
            ...params.InputProps,
            endAdornment: (
              <>
                {loading ? <CircularProgress color="inherit" size={20} /> : null}
                {params.InputProps.endAdornment}
              </>
            ),
          }}
          sx={{
            '& .MuiOutlinedInput-root': {
              backgroundColor: 'var(--bg-tertiary)',
              color: 'var(--text-primary)',
              fontSize: '12px',
              minHeight: '32px',
            },
            '& .MuiInputBase-input': {
              padding: '6px 12px',
              fontSize: '12px',
            },
          }}
        />
      )}
      sx={{
        '& .MuiAutocomplete-popupIndicator': {
          color: 'var(--text-secondary)',
        },
        '& .MuiAutocomplete-clearIndicator': {
          color: 'var(--text-secondary)',
        },
      }}
    />
  );
};
