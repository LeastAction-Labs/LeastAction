/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useMemo, useState } from 'react';

import { Box, Container, Tab, Tabs, Typography } from '@mui/material';

import FieldRenderer, { TabFields } from '@/components/browse/FieldRenderer';
import { generateTabs, processFormData } from '@/components/browse/TabView/tabUtils';
import type { FullItemData } from '@/components/browse/types';
import { TabPanel } from '@/components/ui';
import { getSchema } from '@/services/schema.service';

import Issues from './Issues';
import Reviews from './Reviews';

interface MarketplaceItemTabViewProps {
  item: FullItemData;
}

export default function MarketplaceItemTabView({ item }: MarketplaceItemTabViewProps) {
  const [tabValue, setTabValue] = useState(0);
  const [schema, setSchema] = useState<any>(null);

  const isUsecase = item?.item_type === 'usecase';
  const isSkillUsecase =
    isUsecase &&
    Array.isArray((item as any)?.tags) &&
    (item as any).tags.some(
      (t: string) => t.toLowerCase() === 'skill' || t.toLowerCase() === 'skills',
    );

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
      </Box>
    </Container>
  );
}
