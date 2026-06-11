/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { ReactElement } from 'react';
import { useState } from 'react';

import ArticleIcon from '@mui/icons-material/Article';
import BarChartIcon from '@mui/icons-material/BarChart';
import BoltIcon from '@mui/icons-material/Bolt';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import InsightsIcon from '@mui/icons-material/Insights';
import PieChartIcon from '@mui/icons-material/PieChart';
import TableChartIcon from '@mui/icons-material/TableChart';
import { Box, Chip, CircularProgress, IconButton, Tooltip, Typography } from '@mui/material';

import type { CatalogItem } from '@/components/browse/types';

import SkillPreviewModal from './SkillPreviewModal';

const TYPE_CONFIG: Record<string, { icon: ReactElement; label: string; color: string }> = {
  powerbi_report: {
    icon: <BarChartIcon sx={{ fontSize: 28, color: '#f2c811' }} />,
    label: 'Power BI',
    color: '#f2c811',
  },
  looker_report: {
    icon: <InsightsIcon sx={{ fontSize: 28, color: '#4285f4' }} />,
    label: 'Looker',
    color: '#4285f4',
  },
  looker_studio_report: {
    icon: <InsightsIcon sx={{ fontSize: 28, color: '#34a853' }} />,
    label: 'Looker Studio',
    color: '#34a853',
  },
  quicksight_report: {
    icon: <PieChartIcon sx={{ fontSize: 28, color: '#ff9900' }} />,
    label: 'QuickSight',
    color: '#ff9900',
  },
  tableau_report: {
    icon: <TableChartIcon sx={{ fontSize: 28, color: '#e8762d' }} />,
    label: 'Tableau',
    color: '#e8762d',
  },
};

interface ReportGridProps {
  reports: CatalogItem[];
  loading: boolean;
  onOpen: (report: CatalogItem) => void;
}

const formatName = (name: string) =>
  name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

function relativeTime(dateStr: string | null | undefined): string | null {
  if (!dateStr) return null;
  const diff = Date.now() - new Date(dateStr).getTime();
  const mins = Math.floor(diff / 60000);
  if (mins < 1) return 'just now';
  if (mins < 60) return `${mins}m ago`;
  const hrs = Math.floor(mins / 60);
  if (hrs < 24) return `${hrs}h ago`;
  const days = Math.floor(hrs / 24);
  if (days < 30) return `${days}d ago`;
  const months = Math.floor(days / 30);
  if (months < 12) return `${months}mo ago`;
  return `${Math.floor(months / 12)}y ago`;
}

export default function ReportGrid({ reports, loading, onOpen }: ReportGridProps) {
  const [previewSkillLaui, setPreviewSkillLaui] = useState<string | null>(null);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1 }}>
        <CircularProgress size={32} sx={{ color: 'var(--text-secondary)' }} />
      </Box>
    );
  }

  if (reports.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1 }}>
        <Typography sx={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
          No reports in this folder.
        </Typography>
      </Box>
    );
  }

  return (
    <>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(220px, 1fr))',
          gap: 2,
          p: 3,
          alignContent: 'start',
        }}
      >
        {reports.map((report) => {
          const description =
            (report as any).description || (report as any).data?.description || '';
          const typeConfig = TYPE_CONFIG[report.item_type ?? ''];
          const icon = typeConfig?.icon ?? <ArticleIcon sx={{ fontSize: 28, color: '#6366f1' }} />;
          const tags: string[] = report.tags ?? (report as any).data?.tags ?? [];
          const updatedAt = relativeTime(report.updated_at);
          const skillLaui: string | undefined =
            report.skill_laui ?? (report as any).data?.skill_laui;

          return (
            <Box
              key={report.laui}
              onClick={() => onOpen(report)}
              sx={{
                position: 'relative',
                p: 2.5,
                borderRadius: 2,
                border: '1px solid var(--border)',
                bgcolor: 'var(--bg-secondary)',
                cursor: 'pointer',
                display: 'flex',
                flexDirection: 'column',
                gap: 0.75,
                transition: 'box-shadow 0.15s, border-color 0.15s',
                '&:hover': {
                  boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
                  borderColor: 'var(--text-secondary)',
                },
              }}
            >
              {skillLaui && (
                <IconButton
                  size="small"
                  onClick={(e) => {
                    e.stopPropagation();
                    setPreviewSkillLaui(skillLaui);
                  }}
                  sx={{
                    position: 'absolute',
                    top: 6,
                    right: 6,
                    color: 'var(--text-secondary)',
                    opacity: 0.5,
                    '&:hover': {
                      opacity: 1,
                      color: 'var(--accent, #7c3aed)',
                      bgcolor: 'transparent',
                    },
                  }}
                >
                  <InfoOutlinedIcon sx={{ fontSize: 15 }} />
                </IconButton>
              )}
              {icon}
              <Typography
                sx={{
                  fontWeight: 600,
                  fontSize: '0.875rem',
                  color: 'var(--text-primary)',
                  lineHeight: 1.3,
                }}
              >
                {formatName(report.name)}
              </Typography>
              {typeConfig && (
                <Typography
                  sx={{
                    fontSize: '0.65rem',
                    color: typeConfig.color,
                    fontWeight: 600,
                    letterSpacing: '0.04em',
                    textTransform: 'uppercase',
                  }}
                >
                  {typeConfig.label}
                </Typography>
              )}
              {description && (
                <Typography
                  sx={{
                    fontSize: '0.75rem',
                    color: 'var(--text-secondary)',
                    lineHeight: 1.4,
                    display: '-webkit-box',
                    WebkitLineClamp: 2,
                    WebkitBoxOrient: 'vertical',
                    overflow: 'hidden',
                  }}
                >
                  {description}
                </Typography>
              )}

              {/* Tags */}
              {tags.length > 0 && (
                <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 0.5, mt: 0.25 }}>
                  {tags.slice(0, 3).map((tag) => (
                    <Chip
                      key={tag}
                      label={tag}
                      size="small"
                      sx={{
                        height: 16,
                        fontSize: '0.6rem',
                        bgcolor: 'var(--bg-tertiary)',
                        color: 'var(--text-secondary)',
                        border: '1px solid var(--border)',
                      }}
                    />
                  ))}
                  {tags.length > 3 && (
                    <Chip
                      label={`+${tags.length - 3}`}
                      size="small"
                      sx={{
                        height: 16,
                        fontSize: '0.6rem',
                        bgcolor: 'var(--bg-tertiary)',
                        color: 'var(--text-secondary)',
                        border: '1px solid var(--border)',
                      }}
                    />
                  )}
                </Box>
              )}

              {/* Footer: updated time + skill badge */}
              <Box
                sx={{
                  display: 'flex',
                  alignItems: 'center',
                  justifyContent: 'space-between',
                  mt: 'auto',
                  pt: 0.5,
                }}
              >
                {updatedAt && (
                  <Typography sx={{ fontSize: '0.62rem', color: 'var(--text-secondary)' }}>
                    {updatedAt}
                  </Typography>
                )}
                {skillLaui && (
                  <Tooltip title="Skill pre-configured for AI chat — click ⓘ to preview">
                    <Box
                      sx={{
                        display: 'flex',
                        alignItems: 'center',
                        gap: 0.25,
                      }}
                    >
                      <BoltIcon
                        sx={{
                          fontSize: 11,
                          color: 'var(--accent, #7c3aed)',
                        }}
                      />
                      <Typography
                        sx={{
                          fontSize: '0.6rem',
                          color: 'var(--accent, #7c3aed)',
                          fontWeight: 600,
                        }}
                      >
                        skill
                      </Typography>
                    </Box>
                  </Tooltip>
                )}
              </Box>
            </Box>
          );
        })}
      </Box>

      <SkillPreviewModal
        open={Boolean(previewSkillLaui)}
        onClose={() => setPreviewSkillLaui(null)}
        skillLaui={previewSkillLaui}
      />
    </>
  );
}
