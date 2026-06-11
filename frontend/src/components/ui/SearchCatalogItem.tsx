/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useMemo, useState } from 'react';

import { Autocomplete, CircularProgress, TextField } from '@mui/material';

import { type SearchCatalogFilters, searchCatalogItems } from '@/services/catalog.service';

type ReturnMode = 'laui' | 'object';

interface SearchCatalogItemProps {
  itemType: string;
  value?: string | null;
  onChange: (value: unknown) => void;
  label?: string;
  placeholder?: string;
  returnType?: ReturnMode;
  filters?: SearchCatalogFilters;
  minSearchLength?: number;
  disabled?: boolean;
}

interface SearchOption {
  label: string;
  value: string; // laui
  raw: unknown;
}

export function SearchCatalogItem({
  itemType,
  value = '',
  onChange,
  label,
  placeholder,
  returnType = 'laui',
  filters,
  // minSearchLength is kept in props for API compatibility, but no longer used
  disabled = false,
}: SearchCatalogItemProps) {
  const [inputValue, setInputValue] = useState<string>('');
  const [options, setOptions] = useState<SearchOption[]>([]);
  const [loading, setLoading] = useState(false);

  // Keep a stable selected option for controlled usage
  const selectedOption = useMemo(() => {
    if (!value) return null;
    return (
      options.find((opt) => opt.value === value) || {
        label: String(value),
        value: String(value),
        raw: null,
      }
    );
  }, [options, value]);

  // Fetch all items for the given itemType (and optional filters) once,
  // then let the Autocomplete handle client‑side filtering as the user types.
  useEffect(() => {
    let cancelled = false;

    const fetchItems = async () => {
      setLoading(true);
      try {
        const response = await searchCatalogItems(itemType, false, {
          filters,
        });

        const items = (response.items || response || []) as unknown[];
        if (!Array.isArray(items)) {
          if (!cancelled) setOptions([]);
          return;
        }

        const nextOptions: SearchOption[] = items.map((item) => {
          const anyItem = item as Record<string, unknown>;
          const actualItem = (anyItem.item as Record<string, unknown>) || anyItem;
          const itemLaui =
            (actualItem._laui as string | undefined) ||
            (actualItem.laui as string | undefined) ||
            (actualItem.id as string | undefined) ||
            '';
          const itemName = (actualItem.name as string | undefined) || itemLaui || 'Unnamed';

          return {
            label: `${itemName} (${itemLaui})`,
            value: String(itemLaui),
            raw: actualItem,
          };
        });

        if (!cancelled) {
          setOptions(nextOptions);
        }
      } catch (err) {
        console.error('Error searching catalog items:', err);
        if (!cancelled) {
          setOptions([]);
        }
      } finally {
        if (!cancelled) {
          setLoading(false);
        }
      }
    };

    void fetchItems();

    return () => {
      cancelled = true;
    };
  }, [itemType, filters]);

  return (
    <Autocomplete<SearchOption, false, false, false>
      fullWidth
      size="small"
      disabled={disabled}
      options={options}
      loading={loading}
      value={selectedOption}
      onChange={(_event, newValue) => {
        if (!newValue) {
          onChange(null);
          return;
        }
        if (returnType === 'object') {
          onChange(newValue.raw);
        } else {
          onChange(newValue.value);
        }
      }}
      inputValue={inputValue}
      onInputChange={(_event, newInputValue) => {
        setInputValue(newInputValue);
      }}
      getOptionLabel={(option) => option.label}
      isOptionEqualToValue={(option, val) => option.value === val.value}
      renderInput={(params) => (
        <TextField
          {...params}
          label={label}
          placeholder={placeholder || `Search ${itemType}`}
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
            '& .MuiInputLabel-root': {
              color: 'var(--text-secondary)',
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
}
