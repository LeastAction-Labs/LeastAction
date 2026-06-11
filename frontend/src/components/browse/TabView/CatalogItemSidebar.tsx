/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Box, Divider, Typography } from '@mui/material';

import { Chip } from '@/components/ui';
import { MetaRow, SectionTitle, formatRelativeDate } from '@/components/ui/sidebarParts';

interface CatalogItemSidebarProps {
  item: any;
  onAddFilter?: (field: string, value: string) => void;
}

const STATUS_COLORS: Record<string, string> = {
  published: '#4caf50',
  deprecated: '#f97316',
  archived: '#9e9e9e',
  security_warning: '#ef5350',
  security_hold: '#d32f2f',
  draft: '#9e9e9e',
};

function NA() {
  return (
    <Typography sx={{ fontSize: '12px', color: 'var(--text-secondary)', fontStyle: 'italic' }}>
      N/A
    </Typography>
  );
}

function normalizeStringOrArray(val: any): string | undefined {
  if (!val) return undefined;
  if (Array.isArray(val)) return val.length > 0 ? val.join(', ') : undefined;
  return String(val);
}

export default function CatalogItemSidebar({
  item,
  onAddFilter,
}: Readonly<CatalogItemSidebarProps>) {
  const version = item.version_details?.version;
  const updatedAt = item.updated_at;
  const tags: string[] = item.tags ?? [];
  const publisher = item.publisher ?? item.metadata?.publisher;
  const isOfficial = publisher === 'LeastAction';
  const category = normalizeStringOrArray(item.category ?? item.metadata?.category);
  const division = normalizeStringOrArray(item.division ?? item.metadata?.division);

  const hasPublishStatus = item.is_published !== undefined;

  const marketplaceLaui: string | undefined = item.marketplace_laui;
  const lifecycleStatus: string | undefined = item.status;
  const deprecatedReason: string | undefined = item.deprecated_reason;
  const deprecatedAt: string | undefined = item.deprecated_at;
  const sunsetDate: string | undefined = item.sunset_date;
  const successorItemId: string | undefined = item.successor_item_id;
  const verified: boolean | undefined = item.verified;
  const latestVersion: boolean | undefined = item.latest_version;
  const versionCompatibility: any = item.version_compatibility;
  const imageUrl: string | undefined = item.image_url;

  const itemTypeParts = (item.item_type ?? '').split('.');
  const baseType = itemTypeParts[0];
  const subtype = itemTypeParts.length > 1 ? itemTypeParts.slice(1).join('.') : undefined;
  const showSubtype = baseType === 'operator' || baseType === 'connection';

  return (
    <Box sx={{ p: 2, overflow: 'auto', height: '100%' }}>
      {/* Status chips */}
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 1.5 }}>
        {version && <Chip label={`v${version}`} variant="version" />}
        {hasPublishStatus && item.is_published === true && !item.has_unpublished_changes && (
          <Chip label="Published" variant="published" tooltip="Published to Marketplace" />
        )}
        {hasPublishStatus && item.is_published === true && item.has_unpublished_changes && (
          <Chip
            label="Pending changes"
            variant="draft"
            tooltip="Local changes not yet published to Marketplace"
          />
        )}
        {hasPublishStatus && item.is_published === false && (
          <Chip label="Draft" variant="draft" tooltip="Not yet published to Marketplace" />
        )}
        {verified && <Chip label="Verified" variant="official" tooltip="Verified by marketplace" />}
      </Box>

      {/* Meta rows */}
      <MetaRow label="Updated">
        {updatedAt ? (
          <Typography sx={{ fontSize: '12px', color: 'var(--text-primary)' }}>
            {formatRelativeDate(updatedAt)}
          </Typography>
        ) : (
          <NA />
        )}
      </MetaRow>

      <MetaRow label="Identifier">
        {item.laui ? (
          <Typography
            title={item.laui}
            sx={{
              fontSize: '11px',
              color: 'var(--text-secondary)',
              fontFamily: 'monospace',
              maxWidth: 130,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              cursor: 'default',
            }}
          >
            {item.laui}
          </Typography>
        ) : (
          <NA />
        )}
      </MetaRow>

      {showSubtype && (
        <MetaRow label="Subtype">
          <Typography
            sx={{
              fontSize: '12px',
              color: subtype ? 'var(--text-primary)' : 'var(--text-secondary)',
              fontFamily: 'monospace',
              fontStyle: subtype ? 'normal' : 'italic',
            }}
          >
            {subtype ?? 'N/A'}
          </Typography>
        </MetaRow>
      )}

      <MetaRow label="Mkt LAUI">
        {marketplaceLaui ? (
          <Typography
            title={marketplaceLaui}
            sx={{
              fontSize: '11px',
              color: 'var(--text-secondary)',
              fontFamily: 'monospace',
              maxWidth: 130,
              overflow: 'hidden',
              textOverflow: 'ellipsis',
              whiteSpace: 'nowrap',
              cursor: 'default',
            }}
          >
            {marketplaceLaui}
          </Typography>
        ) : (
          <NA />
        )}
      </MetaRow>

      {/* Status section */}
      <Divider sx={{ borderColor: 'var(--border-color)', my: 1.5 }} />
      <SectionTitle>Status</SectionTitle>
      {lifecycleStatus ? (
        <>
          <Box sx={{ display: 'flex', alignItems: 'center', gap: 1, mb: 0.75 }}>
            <Box
              sx={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                flexShrink: 0,
                bgcolor: STATUS_COLORS[lifecycleStatus] ?? 'var(--text-secondary)',
              }}
            />
            <Typography
              sx={{
                fontSize: '12px',
                color: 'var(--text-primary)',
                textTransform: 'capitalize',
              }}
            >
              {lifecycleStatus.replace(/_/g, ' ')}
            </Typography>
          </Box>
          {deprecatedReason && (
            <Typography sx={{ fontSize: '11px', color: 'var(--text-secondary)', mt: 0.5 }}>
              {deprecatedReason}
            </Typography>
          )}
          {deprecatedAt && (
            <MetaRow label="Deprecated">
              <Typography sx={{ fontSize: '12px', color: 'var(--text-primary)' }}>
                {formatRelativeDate(deprecatedAt)}
              </Typography>
            </MetaRow>
          )}
          {sunsetDate && (
            <MetaRow label="Sunset">
              <Typography sx={{ fontSize: '12px', color: 'var(--text-primary)' }}>
                {formatRelativeDate(sunsetDate)}
              </Typography>
            </MetaRow>
          )}
          {successorItemId && (
            <MetaRow label="Successor">
              <Typography
                title={successorItemId}
                sx={{
                  fontSize: '11px',
                  color: 'var(--text-secondary)',
                  fontFamily: 'monospace',
                  maxWidth: 130,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  cursor: 'default',
                }}
              >
                {successorItemId}
              </Typography>
            </MetaRow>
          )}
        </>
      ) : (
        <NA />
      )}

      {/* Tags section */}
      <Divider sx={{ borderColor: 'var(--border-color)', my: 1.5 }} />
      <SectionTitle>Tags</SectionTitle>
      {tags.length > 0 ? (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
          {tags.map((tag: string) => (
            <Chip
              key={tag}
              label={`#${tag}`}
              variant="tag"
              clickable={!!onAddFilter}
              onClick={onAddFilter ? () => onAddFilter('tag', tag) : undefined}
              tooltip={onAddFilter ? `tag:"${tag}"` : undefined}
            />
          ))}
        </Box>
      ) : (
        <NA />
      )}

      {/* Publisher section */}
      <Divider sx={{ borderColor: 'var(--border-color)', my: 1.5 }} />
      <SectionTitle>Publisher</SectionTitle>
      {publisher ? (
        <Box sx={{ display: 'flex', alignItems: 'center', gap: 1 }}>
          <Box
            sx={{
              width: 32,
              height: 32,
              borderRadius: 1,
              bgcolor: 'var(--bg-primary)',
              border: '1px solid var(--border-color)',
              display: 'flex',
              alignItems: 'center',
              justifyContent: 'center',
              flexShrink: 0,
            }}
          >
            <Typography sx={{ fontSize: '14px', fontWeight: 700, color: 'var(--text-primary)' }}>
              {publisher.charAt(0).toUpperCase()}
            </Typography>
          </Box>
          <Chip label={publisher} variant={isOfficial ? 'official' : 'publisher'} />
        </Box>
      ) : (
        <NA />
      )}

      {/* Category section */}
      <Divider sx={{ borderColor: 'var(--border-color)', my: 1.5 }} />
      <SectionTitle>Category</SectionTitle>
      {category || division ? (
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
          {category && <Chip label={category} variant="category" />}
          {division && <Chip label={division} variant="category" />}
        </Box>
      ) : (
        <NA />
      )}

      {/* Image section */}
      {imageUrl && (
        <>
          <Divider sx={{ borderColor: 'var(--border-color)', my: 1.5 }} />
          <SectionTitle>Image</SectionTitle>
          <Box
            component="img"
            src={imageUrl}
            alt="item icon"
            sx={{
              width: 48,
              height: 48,
              borderRadius: 1,
              objectFit: 'contain',
              border: '1px solid var(--border-color)',
            }}
          />
        </>
      )}

      {/* Version section */}
      <Divider sx={{ borderColor: 'var(--border-color)', my: 1.5 }} />
      <SectionTitle>Version</SectionTitle>
      <MetaRow label="Current">
        {version ? (
          <Typography
            sx={{
              fontSize: '12px',
              color: 'var(--text-primary)',
              fontFamily: 'monospace',
            }}
          >
            v{version}
          </Typography>
        ) : (
          <NA />
        )}
      </MetaRow>
      <MetaRow label="Latest">
        {latestVersion !== undefined ? (
          <Typography sx={{ fontSize: '12px', color: 'var(--text-primary)' }}>
            {latestVersion ? 'Yes' : 'No'}
          </Typography>
        ) : (
          <NA />
        )}
      </MetaRow>
      <MetaRow label="Core compat">
        {versionCompatibility?.core?.length > 0 ? (
          <Typography
            sx={{
              fontSize: '11px',
              color: 'var(--text-secondary)',
              fontFamily: 'monospace',
            }}
          >
            {(versionCompatibility.core as string[]).join(', ')}
          </Typography>
        ) : (
          <NA />
        )}
      </MetaRow>
    </Box>
  );
}
