/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Download as DownloadIcon } from '@mui/icons-material';
import { Box, Button, Divider, Link, Tooltip, Typography } from '@mui/material';

import type { FullItemData } from '@/components/browse/types';
import { Chip } from '@/components/ui';
import { MetaRow, SectionTitle, formatRelativeDate } from '@/components/ui/sidebarParts';
import { getCoreVersion } from '@/config/version';
import { useCatalog } from '@/contexts/CatalogContext';
import { schemaExists } from '@/services/schema.service';
import { compatibilityMessage, isCoreCompatible } from '@/utils/semver';

interface ItemMetaProps {
  item: FullItemData;
  onAddFilter?: (field: string, value: string) => void;
}

type LicenseValue = string | { name: string; url?: string };

// ── Extracted sub-sections to keep ItemMeta's cognitive complexity in budget ──

function DepsSection({
  pythonReq,
  laInterfaceReq,
}: Readonly<{ pythonReq?: string; laInterfaceReq?: string }>) {
  if (!pythonReq && !laInterfaceReq) return null;
  return (
    <>
      <Divider sx={{ borderColor: 'var(--border-color)', my: 1.5 }} />
      <SectionTitle>Dependencies</SectionTitle>
      {pythonReq && (
        <MetaRow label="python">
          <Typography
            sx={{
              fontSize: '12px',
              color: 'var(--text-primary)',
              fontFamily: 'monospace',
            }}
          >
            ≥ {pythonReq}
          </Typography>
        </MetaRow>
      )}
      {laInterfaceReq && (
        <MetaRow label="la_interface">
          <Typography
            sx={{
              fontSize: '12px',
              color: 'var(--text-primary)',
              fontFamily: 'monospace',
            }}
          >
            ≥ {laInterfaceReq}
          </Typography>
        </MetaRow>
      )}
    </>
  );
}

function CategorySection({
  category,
  division,
  onAddFilter,
}: Readonly<{
  category?: string;
  division?: string;
  onAddFilter?: (field: string, value: string) => void;
}>) {
  if (!category && !division) return null;
  return (
    <>
      <Divider sx={{ borderColor: 'var(--border-color)', my: 1.5 }} />
      <SectionTitle>Category</SectionTitle>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
        {category && (
          <Chip
            label={category}
            variant="category"
            clickable={!!onAddFilter}
            onClick={onAddFilter ? () => onAddFilter('category', category) : undefined}
            tooltip={onAddFilter ? `category:"${category}"` : undefined}
          />
        )}
        {division && (
          <Chip
            label={division}
            variant="category"
            clickable={!!onAddFilter}
            onClick={onAddFilter ? () => onAddFilter('division', division) : undefined}
            tooltip={onAddFilter ? `division:"${division}"` : undefined}
          />
        )}
      </Box>
    </>
  );
}

function TagsSection({
  tags,
  onAddFilter,
}: Readonly<{
  tags?: string[];
  onAddFilter?: (field: string, value: string) => void;
}>) {
  if (!tags || tags.length === 0) return null;
  return (
    <>
      <Divider sx={{ borderColor: 'var(--border-color)', my: 1.5 }} />
      <SectionTitle>Tags</SectionTitle>
      <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.75 }}>
        {tags.map((tag) => (
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
    </>
  );
}

function PublisherSection({
  publisher,
  isOfficial,
  onAddFilter,
}: Readonly<{
  publisher?: string;
  isOfficial: boolean;
  onAddFilter?: (field: string, value: string) => void;
}>) {
  if (!publisher) return null;
  return (
    <>
      <Divider sx={{ borderColor: 'var(--border-color)', my: 1.5 }} />
      <SectionTitle>Publisher</SectionTitle>
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
        <Chip
          label={publisher}
          variant={isOfficial ? 'official' : 'publisher'}
          clickable={!!onAddFilter}
          onClick={onAddFilter ? () => onAddFilter('publisher', publisher) : undefined}
          tooltip={onAddFilter ? `publisher:"${publisher}"` : undefined}
        />
      </Box>
    </>
  );
}

function LicenseDisplay({ license }: Readonly<{ license: LicenseValue }>) {
  if (typeof license === 'string') {
    return (
      <Typography sx={{ fontSize: '12px', color: 'var(--text-primary)' }}>{license}</Typography>
    );
  }
  if (license.url) {
    return (
      <Link
        href={license.url}
        target="_blank"
        rel="noopener noreferrer"
        sx={{ fontSize: '12px', color: 'var(--accent)' }}
      >
        {license.name}
      </Link>
    );
  }
  return (
    <Typography sx={{ fontSize: '12px', color: 'var(--text-primary)' }}>{license.name}</Typography>
  );
}

function StatusChips({
  version,
  compatible,
  compatMsg,
  deprecated,
  deprecatedAt,
  isPublished,
  hasUnpublishedChanges,
  coreVersion,
}: Readonly<{
  version?: string;
  compatible: boolean;
  compatMsg?: string | null;
  deprecated: boolean;
  deprecatedAt?: string;
  isPublished?: boolean;
  hasUnpublishedChanges?: boolean;
  coreVersion: string;
}>) {
  return (
    <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mb: 1.5 }}>
      {version && <Chip label={`v${version}`} variant="version" />}
      <Chip
        label={compatible ? '✓ Compatible' : 'Incompatible'}
        variant={compatible ? 'compatible' : 'incompatible'}
        tooltip={compatible ? `Compatible with core ${coreVersion}` : (compatMsg ?? undefined)}
      />
      {deprecated && (
        <Chip
          label="Deprecated"
          variant="deprecated"
          tooltip={deprecatedAt ? `Since ${deprecatedAt}` : undefined}
        />
      )}
      {isPublished === true && !hasUnpublishedChanges && (
        <Chip label="Published" variant="published" tooltip="Published to Marketplace" />
      )}
      {isPublished === true && hasUnpublishedChanges && (
        <Chip
          label="Pending changes"
          variant="draft"
          tooltip="Local changes not yet published to Marketplace"
        />
      )}
      {isPublished === false && (
        <Chip label="Draft" variant="draft" tooltip="Not yet published to Marketplace" />
      )}
    </Box>
  );
}

// ─────────────────────────────────────────────────────────────────────────────

export default function ItemMeta({ item, onAddFilter }: Readonly<ItemMetaProps>) {
  const { setImportModalState } = useCatalog();
  const coreVersion = getCoreVersion();
  const compatible = isCoreCompatible(item.version_compatibility, coreVersion);
  const compatMsg = compatibilityMessage(item.version_compatibility, coreVersion);
  const version = item.version_details?.version;
  const isOfficial = item.publisher === 'LeastAction';
  const corePatterns = item.version_compatibility?.core;
  const tags = item.tags;

  const installs = item['installs'] as number | undefined;
  const rating = item['rating'] as number | string | undefined;
  const license = item['license'] as LicenseValue | undefined;

  const updatedAt = item.updated_at ?? item.version_details?.released_at;

  const deprecated = !!item.version_details?.deprecated;
  const typeSupported = schemaExists(item.item_type);
  let importDisabledReason: string | null = null;
  if (!typeSupported) {
    importDisabledReason = 'Item type not supported in this core version';
  } else if (!compatible) {
    importDisabledReason =
      compatibilityMessage(item.version_compatibility, coreVersion) ?? 'Incompatible core version';
  } else if (deprecated) {
    const since = item.version_details?.deprecated_at;
    importDisabledReason = since
      ? `This item is deprecated since ${since}`
      : 'This item is deprecated';
  }

  const handleInstall = () => {
    if (!importDisabledReason) {
      setImportModalState({ isOpen: true, itemData: item });
    }
  };

  const installButton = (
    <Button
      variant="contained"
      size="small"
      startIcon={<DownloadIcon fontSize="small" />}
      fullWidth
      disabled={!!importDisabledReason}
      onClick={handleInstall}
      sx={{
        mb: 1.5,
        textTransform: 'none',
        fontWeight: 600,
        fontSize: '13px',
        bgcolor: 'var(--accent)',
        '&:hover': { bgcolor: 'var(--accent)', filter: 'brightness(1.15)' },
        '&.Mui-disabled': { opacity: 0.5 },
      }}
    >
      Install
    </Button>
  );

  return (
    <Box sx={{ p: 2, overflow: 'auto', height: '100%' }}>
      <StatusChips
        version={version}
        compatible={compatible}
        compatMsg={compatMsg}
        deprecated={deprecated}
        deprecatedAt={item.version_details?.deprecated_at}
        isPublished={item.is_published}
        hasUnpublishedChanges={item.has_unpublished_changes}
        coreVersion={coreVersion}
      />

      {importDisabledReason ? (
        <Tooltip title={importDisabledReason} placement="bottom" arrow>
          <span style={{ display: 'block', width: '100%', marginBottom: 0 }}>{installButton}</span>
        </Tooltip>
      ) : (
        installButton
      )}

      {updatedAt && (
        <MetaRow label="Updated">
          <Typography sx={{ fontSize: '12px', color: 'var(--text-primary)' }}>
            {formatRelativeDate(updatedAt)}
          </Typography>
        </MetaRow>
      )}

      {corePatterns && corePatterns.length > 0 && (
        <MetaRow label="Core compat">
          <Typography
            sx={{
              fontSize: '12px',
              color: compatible ? 'success.dark' : 'error.dark',
              fontFamily: 'monospace',
            }}
          >
            {corePatterns.join(', ')}
          </Typography>
        </MetaRow>
      )}

      {installs !== undefined && (
        <MetaRow label="Installs">
          <Typography sx={{ fontSize: '12px', color: 'var(--text-primary)' }}>
            {installs.toLocaleString()}
          </Typography>
        </MetaRow>
      )}

      {rating !== undefined && (
        <MetaRow label="Rating">
          <Typography sx={{ fontSize: '12px', color: 'var(--text-primary)' }}>
            ★ {rating}
          </Typography>
        </MetaRow>
      )}

      {license !== undefined && (
        <MetaRow label="License">
          <LicenseDisplay license={license} />
        </MetaRow>
      )}

      <MetaRow label="Identifier">
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
      </MetaRow>

      <DepsSection
        pythonReq={item.version_compatibility?.python}
        laInterfaceReq={item.version_compatibility?.la_interface}
      />

      <TagsSection tags={tags} onAddFilter={onAddFilter} />

      <PublisherSection
        publisher={item.publisher}
        isOfficial={isOfficial}
        onAddFilter={onAddFilter}
      />

      <CategorySection
        category={item.category}
        division={item.division}
        onAddFilter={onAddFilter}
      />

      <Divider sx={{ borderColor: 'var(--border-color)', my: 1.5 }} />
      <SectionTitle>Versions</SectionTitle>
      {version && (
        <Typography
          sx={{
            fontSize: '12px',
            color: 'var(--text-primary)',
            mb: 1,
            fontFamily: 'monospace',
          }}
        >
          Current: v{version}
        </Typography>
      )}
      {/* check-for-updates: discuss with amogha — API shape + whether to auto-call on panel open */}
      <Button
        size="small"
        variant="outlined"
        onClick={() => {
          /* placeholder — hook later */
        }}
        sx={{
          fontSize: '11px',
          color: 'var(--text-secondary)',
          borderColor: 'var(--border-color)',
          textTransform: 'none',
          py: 0.25,
          '&:hover': {
            bgcolor: 'var(--bg-secondary)',
            borderColor: 'var(--text-secondary)',
          },
        }}
      >
        Check for updates
      </Button>
    </Box>
  );
}
