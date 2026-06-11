/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import FolderOpenIcon from '@mui/icons-material/FolderOpen';
import InfoOutlinedIcon from '@mui/icons-material/InfoOutlined';
import { Box, CircularProgress, IconButton, Typography } from '@mui/material';

import type { CatalogItem } from '@/components/browse/types';

import SkillPreviewModal from './SkillPreviewModal';

interface FolderGridProps {
  folders: CatalogItem[];
  loading: boolean;
  onOpen: (folder: CatalogItem) => void;
}

const formatName = (name: string) =>
  name.replace(/_/g, ' ').replace(/\b\w/g, (c) => c.toUpperCase());

export default function FolderGrid({ folders, loading, onOpen }: FolderGridProps) {
  const [previewSkillLaui, setPreviewSkillLaui] = useState<string | null>(null);

  if (loading) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1 }}>
        <CircularProgress size={32} sx={{ color: 'var(--text-secondary)' }} />
      </Box>
    );
  }

  if (folders.length === 0) {
    return (
      <Box sx={{ display: 'flex', justifyContent: 'center', alignItems: 'center', flex: 1 }}>
        <Typography sx={{ color: 'var(--text-secondary)', fontSize: '0.875rem' }}>
          No folders available.
        </Typography>
      </Box>
    );
  }

  return (
    <>
      <Box
        sx={{
          display: 'grid',
          gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
          gap: 2,
          p: 3,
          alignContent: 'start',
        }}
      >
        {folders.map((folder) => (
          <Box
            key={folder.laui}
            onClick={() => onOpen(folder)}
            sx={{
              position: 'relative',
              p: 2.5,
              borderRadius: 2,
              border: '1px solid var(--border)',
              bgcolor: 'var(--bg-secondary)',
              cursor: 'pointer',
              display: 'flex',
              flexDirection: 'column',
              gap: 1,
              transition: 'box-shadow 0.15s, border-color 0.15s',
              '&:hover': {
                boxShadow: '0 4px 16px rgba(0,0,0,0.12)',
                borderColor: 'var(--text-secondary)',
              },
            }}
          >
            {folder.skill_laui && (
              <IconButton
                size="small"
                onClick={(e) => {
                  e.stopPropagation();
                  setPreviewSkillLaui(folder.skill_laui!);
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
            <FolderOpenIcon sx={{ fontSize: 28, color: '#e2a23b' }} />
            <Typography
              sx={{
                fontWeight: 600,
                fontSize: '0.875rem',
                color: 'var(--text-primary)',
                lineHeight: 1.3,
              }}
            >
              {formatName(folder.name)}
            </Typography>
          </Box>
        ))}
      </Box>

      <SkillPreviewModal
        open={Boolean(previewSkillLaui)}
        onClose={() => setPreviewSkillLaui(null)}
        skillLaui={previewSkillLaui}
      />
    </>
  );
}
