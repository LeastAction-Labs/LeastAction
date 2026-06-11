/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import ArrowBackIcon from '@mui/icons-material/ArrowBack';
import BoltIcon from '@mui/icons-material/Bolt';
import { Box, Button, Chip, CircularProgress, Tooltip, Typography } from '@mui/material';

import type { CatalogItem } from '@/components/browse/types';
import IframeContent from '@/components/ui/IframeContent';
import { getCatalogItemById } from '@/services/catalog.service';

import LookerViewer from './LookerViewer';
import PowerBIViewer from './PowerBIViewer';
import QuickSightViewer from './QuickSightViewer';
import TableauViewer from './TableauViewer';

interface ReportViewerProps {
  report: CatalogItem;
  currentFolder: CatalogItem | null;
  onBack: () => void;
}

const formatName = (name: string) =>
  name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

function formatDate(dateStr: string | null | undefined): string | null {
  if (!dateStr) return null;
  return new Date(dateStr).toLocaleDateString(undefined, {
    month: 'short',
    day: 'numeric',
    year: 'numeric',
  });
}

function HtmlReportViewer({
  report,
  onNotesLoaded,
}: {
  report: CatalogItem;
  onNotesLoaded: (notes: string) => void;
}) {
  const [html, setHtml] = useState<string>('');
  const [loading, setLoading] = useState(true);

  useEffect(() => {
    const load = async () => {
      setLoading(true);
      try {
        const full = await getCatalogItemById(report.laui);
        const rawHtml: string = (full as any).html || (full as any).data?.html || '';
        setHtml(rawHtml);
        const notes: string = (full as any).notes || (full as any).data?.notes || '';
        if (notes) onNotesLoaded(notes);
      } finally {
        setLoading(false);
      }
    };
    void load();
  }, [report.laui, onNotesLoaded]);

  return (
    <Box sx={{ flex: 1, minHeight: 0, overflow: 'hidden', bgcolor: 'var(--bg-primary)' }}>
      {loading ? (
        <Box
          sx={{
            display: 'flex',
            justifyContent: 'center',
            alignItems: 'center',
            height: '100%',
          }}
        >
          <CircularProgress size={32} sx={{ color: 'var(--text-secondary)' }} />
        </Box>
      ) : html ? (
        <IframeContent content={html} height="100%" />
      ) : (
        <Box sx={{ p: 3 }}>
          <Typography sx={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
            No content.
          </Typography>
        </Box>
      )}
    </Box>
  );
}

export default function ReportViewer({ report, currentFolder, onBack }: ReportViewerProps) {
  const [skillName, setSkillName] = useState<string | null>(null);
  const [notes, setNotes] = useState<string>('');

  const resolvedSkillLaui: string | null =
    (report as any).skill_laui ?? currentFolder?.skill_laui ?? null;

  const tags: string[] = report.tags ?? (report as any).data?.tags ?? [];
  const updatedAt = formatDate(report.updated_at);

  // Fetch skill name
  useEffect(() => {
    if (!resolvedSkillLaui) {
      setSkillName(null);
      return;
    }
    getCatalogItemById(resolvedSkillLaui)
      .then((item: any) => setSkillName(item?.name ?? null))
      .catch(() => setSkillName(null));
  }, [resolvedSkillLaui]);

  // For non-HTML report types, load notes directly
  useEffect(() => {
    if (report.item_type === 'html_report') return; // HtmlReportViewer handles it
    getCatalogItemById(report.laui)
      .then((full: any) => setNotes(full?.notes || full?.data?.notes || ''))
      .catch(() => {});
  }, [report.laui, report.item_type]);

  const hasMetadata = updatedAt || resolvedSkillLaui || tags.length > 0 || notes;

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', flex: 1, overflow: 'hidden' }}>
      {/* Toolbar */}
      <Box
        sx={{
          display: 'flex',
          alignItems: 'center',
          gap: 1.5,
          px: 2.5,
          py: 1.25,
          borderBottom: hasMetadata ? 'none' : '1px solid var(--border)',
          bgcolor: 'var(--bg-secondary)',
          flexShrink: 0,
        }}
      >
        <Button
          size="small"
          startIcon={<ArrowBackIcon sx={{ fontSize: 14 }} />}
          onClick={onBack}
          sx={{
            textTransform: 'none',
            fontSize: '0.75rem',
            color: 'var(--text-secondary)',
            '&:hover': { color: 'var(--text-primary)' },
          }}
        >
          Back
        </Button>
        <Box sx={{ width: '1px', height: 16, bgcolor: 'var(--border)', flexShrink: 0 }} />
        <Typography sx={{ fontWeight: 600, fontSize: '0.875rem', color: 'var(--text-primary)' }}>
          {formatName(report.name)}
        </Typography>
      </Box>

      {/* Metadata row */}
      {hasMetadata && (
        <Box
          sx={{
            display: 'flex',
            alignItems: 'center',
            flexWrap: 'wrap',
            gap: 1.5,
            px: 2.5,
            py: 0.75,
            borderBottom: '1px solid var(--border)',
            bgcolor: 'var(--bg-secondary)',
            flexShrink: 0,
          }}
        >
          {updatedAt && (
            <Typography sx={{ fontSize: '0.7rem', color: 'var(--text-secondary)' }}>
              Updated {updatedAt}
            </Typography>
          )}
          {resolvedSkillLaui && (
            <Box sx={{ display: 'flex', alignItems: 'center', gap: 0.4 }}>
              <BoltIcon sx={{ fontSize: 12, color: 'var(--accent, #7c3aed)' }} />
              <Typography
                sx={{
                  fontSize: '0.7rem',
                  color: 'var(--accent, #7c3aed)',
                  fontWeight: 600,
                }}
              >
                {skillName ?? 'Skill'}
              </Typography>
            </Box>
          )}
          {tags.map((tag) => (
            <Chip
              key={tag}
              label={tag}
              size="small"
              sx={{
                height: 18,
                fontSize: '0.62rem',
                bgcolor: 'var(--bg-tertiary)',
                color: 'var(--text-secondary)',
                border: '1px solid var(--border)',
              }}
            />
          ))}
          {notes && (
            <Tooltip title={notes} placement="bottom-start">
              <Typography
                sx={{
                  fontSize: '0.7rem',
                  color: 'var(--text-secondary)',
                  maxWidth: 320,
                  overflow: 'hidden',
                  textOverflow: 'ellipsis',
                  whiteSpace: 'nowrap',
                  cursor: 'default',
                  fontStyle: 'italic',
                }}
              >
                {notes}
              </Typography>
            </Tooltip>
          )}
        </Box>
      )}

      {/* Route to the correct viewer by item_type */}
      {report.item_type === 'powerbi_report' && <PowerBIViewer item={report} />}
      {report.item_type === 'looker_report' && <LookerViewer item={report} />}
      {report.item_type === 'looker_studio_report' && <LookerViewer item={report} />}
      {report.item_type === 'quicksight_report' && <QuickSightViewer item={report} />}
      {report.item_type === 'tableau_report' && <TableauViewer item={report} />}
      {(!report.item_type || report.item_type === 'html_report') && (
        <HtmlReportViewer report={report} onNotesLoaded={setNotes} />
      )}
    </Box>
  );
}
