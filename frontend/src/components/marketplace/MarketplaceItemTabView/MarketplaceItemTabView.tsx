/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useMemo, useRef, useState } from 'react';

import { Download as ImportIcon } from '@mui/icons-material';
import ListAltIcon from '@mui/icons-material/ListAlt';
import { Box, Container, IconButton, Tab, Tabs, Tooltip, Typography } from '@mui/material';

import FieldRenderer, { TabFields } from '@/components/browse/FieldRenderer';
import { generateTabs, processFormData } from '@/components/browse/TabView/tabUtils';
import type { FullItemData } from '@/components/browse/types';
// ← incoming fix: getCoreVersion() not CORE_VERSION
import UsecaseDepsDialog from '@/components/marketplace/UsecaseImportModal/UsecaseDepsDialog';
import type { DependencyStatus } from '@/components/marketplace/UsecaseImportModal/types';
import { TabPanel } from '@/components/ui';
import { getCoreVersion } from '@/config/version';
import { useCatalog } from '@/contexts/CatalogContext';
import { getSchema, schemaExists } from '@/services/schema.service';
import { compatibilityMessage, isCoreCompatible } from '@/utils/semver';

import Issues from './Issues';
import Reviews from './Reviews';

interface MarketplaceItemTabViewProps {
  item: FullItemData;
}

export default function MarketplaceItemTabView({ item }: MarketplaceItemTabViewProps) {
  const [tabValue, setTabValue] = useState(0);
  const [schema, setSchema] = useState<any>(null);
  const { setImportModalState } = useCatalog();

  const isUsecase = item?.item_type === 'usecase';
  const isSkillUsecase =
    isUsecase &&
    Array.isArray((item as any)?.tags) &&
    (item as any).tags.some(
      (t: string) => t.toLowerCase() === 'skill' || t.toLowerCase() === 'skills',
    );

  const [depsDialogOpen, setDepsDialogOpen] = useState(false);
  const depCacheRef = useRef<Map<string, string>>(new Map());
  const [requiredDepsResolved, setRequiredDepsResolved] = useState(false);

  useEffect(() => {
    setTabValue(0);
  }, [item?.laui]);

  useEffect(() => {
    if (!item?.item_type) return;
    getSchema(item.item_type)
      .then((s) => setSchema(s))
      .catch(() => setSchema(null));
  }, [item?.item_type]);

  const formData = useMemo(() => processFormData(item as Record<string, any>), [item]);

  const { tabs, tabFields } = useMemo(
    () =>
      generateTabs(schema, {
        mode: 'view',
        filterType: item?.item_type ?? '',
        incudeMarketplaceTabs: true,
      }),
    [schema, item?.item_type],
  );

  console.log(tabs, tabFields);

  const coreVersion = getCoreVersion();
  const typeSupported = schemaExists(item.item_type);
  const compatible = isCoreCompatible(item.version_compatibility, coreVersion);
  const deprecated = !!item.version_details?.deprecated;

  const importDisabledReason: string | null = !typeSupported
    ? 'Item type not supported in this core version'
    : !compatible
      ? (compatibilityMessage(item.version_compatibility, coreVersion) ??
        'Incompatible core version')
      : deprecated
        ? `This item is deprecated${item.version_details?.deprecated_at ? ` since ${item.version_details.deprecated_at}` : ''}`
        : null;

  const handleDepStatusChange = (_statuses: DependencyStatus[], allResolved: boolean) => {
    setRequiredDepsResolved(allResolved);
  };

  const importButton = (
    <IconButton
      size="small"
      disabled={!!importDisabledReason}
      onClick={() =>
        !importDisabledReason &&
        setImportModalState({
          isOpen: true,
          itemData: item,
          ...(isUsecase && !isSkillUsecase
            ? {
                usecaseDepCache: new Map(depCacheRef.current),
                usecaseDepsResolved: requiredDepsResolved,
              }
            : {}),
        })
      }
      sx={{
        color: importDisabledReason ? 'var(--text-secondary)' : 'var(--text-primary)',
        '&:hover': { bgcolor: 'var(--bg-primary)' },
      }}
    >
      <ImportIcon fontSize="small" />
    </IconButton>
  );

  const depsButton =
    isUsecase && !isSkillUsecase ? (
      <Tooltip title="Dependencies" placement="left">
        <IconButton
          size="small"
          onClick={() => setDepsDialogOpen(true)}
          sx={{
            color: 'var(--text-primary)',
            '&:hover': { bgcolor: 'var(--bg-primary)' },
          }}
        >
          <ListAltIcon fontSize="small" />
        </IconButton>
      </Tooltip>
    ) : null;

  const _importButtonArea = (
    <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.25 }}>
      {depsButton}
      {importDisabledReason ? (
        <Tooltip title={importDisabledReason} placement="left">
          {importButton}
        </Tooltip>
      ) : (
        <Tooltip title={`Import "${item.name}"`} placement="left">
          {importButton}
        </Tooltip>
      )}
    </Box>
  );

  // payloads may arrive as an array OR as an object { filename: content }
  const normalizePayloads = (raw: any): { filename: string; content: string }[] => {
    if (!raw) return [];
    if (Array.isArray(raw)) {
      return raw.map((p) => {
        if (typeof p === 'string') {
          try {
            return JSON.parse(p) as { filename: string; content: string };
          } catch {
            return { filename: 'unknown', content: p };
          }
        }
        return p as { filename: string; content: string };
      });
    }
    if (typeof raw === 'object') {
      return Object.entries(raw).map(([filename, content]) => ({
        filename,
        content: content as string,
      }));
    }
    return [];
  };

  const renderTabContent = (tabName: string) => {
    const fields = tabFields[tabName] ?? [];
    if (fields.length === 0 && tabName !== 'Reviews' && tabName !== 'Issues') {
      return (
        <Typography sx={{ color: 'var(--text-secondary)', fontSize: '12px', fontStyle: 'italic' }}>
          No fields in this section
        </Typography>
      );
    }

    if (tabName === 'Overview') {
      const nameValue = formData['name'] ?? '';
      const otherFields = fields.filter((f: any) => f.name !== 'name');
      return (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          {nameValue && (
            <Typography
              variant="h6"
              sx={{ color: 'var(--text-primary)', fontWeight: 600, lineHeight: 1.3 }}
            >
              {nameValue}
            </Typography>
          )}
          {otherFields.map((field: any) => (
            <Box key={field.name} sx={{ mb: 0.5 }}>
              <FieldRenderer
                field={field}
                value={formData[field.name] ?? ''}
                mode="view"
                onChange={() => {}}
                itemData={item}
              />
            </Box>
          ))}
        </Box>
      );
    } else if (tabName === 'Reviews') return <Reviews item={item} />;
    else if (tabName === 'Issues') return <Issues item={item} />;

    return (
      <TabFields
        fields={fields}
        formData={formData}
        mode="view"
        renderField={(field: any) => (
          <FieldRenderer
            field={field}
            value={formData[field.name] ?? ''}
            mode="view"
            onChange={() => {}}
            itemData={item}
          />
        )}
      />
    );
  };

  if (!schema?.columns) {
    return (
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'flex-end',
            borderBottom: 1,
            borderColor: 'var(--border-color)',
            p: 0.5,
          }}
        />
        <Box sx={{ flex: 1, overflow: 'auto', p: 2 }}>
          <Box
            component="pre"
            sx={{
              color: 'var(--text-primary)',
              fontSize: '12px',
              fontFamily: 'monospace',
              bgcolor: 'var(--bg-secondary)',
              p: 2,
              borderRadius: 1,
              whiteSpace: 'pre-wrap',
              wordBreak: 'break-all',
              m: 0,
            }}
          >
            {JSON.stringify(item, null, 2)}
          </Box>
        </Box>
        {isUsecase && !isSkillUsecase && (
          <UsecaseDepsDialog
            open={depsDialogOpen}
            onClose={() => setDepsDialogOpen(false)}
            itemName={item.name}
            payloads={normalizePayloads((item as any).payloads)}
            depCacheRef={depCacheRef}
            onStatusChange={handleDepStatusChange}
          />
        )}
      </Box>
    );
  }

  const displayTabs = isSkillUsecase ? tabs.map((t) => (t === 'Payloads' ? 'Skills' : t)) : tabs;

  return (
    <Container maxWidth="lg" sx={{ height: '100%' }}>
      <Box sx={{ display: 'flex', flexDirection: 'column', height: '100%' }}>
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            borderBottom: 1,
            borderColor: 'var(--border-color)',
            bgcolor: 'var(--bg-secondary)',
          }}
        >
          <Box sx={{ flex: 1, overflowX: 'auto' }}>
            <Tabs
              value={tabValue}
              onChange={(_, v) => setTabValue(v)}
              variant="scrollable"
              scrollButtons="auto"
              sx={{
                minHeight: '32px',
                '& .MuiTab-root': {
                  minHeight: '32px',
                  fontSize: '12px',
                  fontWeight: 400,
                  color: 'var(--text-secondary)',
                  textTransform: 'none',
                  px: 2,
                  py: 0,
                  '&.Mui-selected': { color: 'var(--accent)', fontWeight: 600 },
                },
                '& .MuiTabs-indicator': { bgcolor: 'var(--accent)', height: '2px' },
              }}
            >
              {displayTabs.map((tabName, i) => (
                <Tab key={i} label={tabName} />
              ))}
            </Tabs>
          </Box>
        </Box>

        <Box sx={{ flex: 1, overflow: 'auto', bgcolor: 'var(--bg-primary)' }}>
          {displayTabs.map((tabName, i) => (
            <TabPanel key={tabName} value={tabValue} index={i}>
              {renderTabContent(tabName)}
            </TabPanel>
          ))}
        </Box>

        {isUsecase && !isSkillUsecase && (
          <UsecaseDepsDialog
            open={depsDialogOpen}
            onClose={() => setDepsDialogOpen(false)}
            itemName={item.name}
            payloads={normalizePayloads((item as any).payloads)}
            depCacheRef={depCacheRef}
            onStatusChange={handleDepStatusChange}
          />
        )}
      </Box>
    </Container>
  );
}
