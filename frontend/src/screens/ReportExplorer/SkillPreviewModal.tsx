/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import CloseIcon from '@mui/icons-material/Close';
import {
  Box,
  CircularProgress,
  Dialog,
  DialogContent,
  DialogTitle,
  IconButton,
} from '@mui/material';

import MarkdownRenderer from '@/components/browse/MarkdownRenderer';
import { getCatalogItemById } from '@/services/catalog.service';

interface SkillPreviewModalProps {
  open: boolean;
  onClose: () => void;
  skillLaui: string | null;
}

export default function SkillPreviewModal({ open, onClose, skillLaui }: SkillPreviewModalProps) {
  const [skill, setSkill] = useState<{ name: string; content: string } | null>(null);
  const [loading, setLoading] = useState(false);

  useEffect(() => {
    if (!open || !skillLaui) {
      setSkill(null);
      return;
    }
    setLoading(true);
    getCatalogItemById(skillLaui)
      .then((item: any) => setSkill({ name: item?.name ?? 'Skill', content: item?.content ?? '' }))
      .catch(() => setSkill({ name: 'Skill', content: '_Could not load skill content._' }))
      .finally(() => setLoading(false));
  }, [open, skillLaui]);

  return (
    <Dialog
      open={open}
      onClose={onClose}
      maxWidth="md"
      fullWidth
      PaperProps={{
        sx: {
          bgcolor: 'var(--bg-primary)',
          color: 'var(--text-primary)',
          maxHeight: '80vh',
        },
      }}
    >
      <DialogTitle
        sx={{
          display: 'flex',
          justifyContent: 'space-between',
          alignItems: 'center',
          borderBottom: '1px solid var(--border)',
          fontSize: '0.875rem',
          fontWeight: 600,
          py: 1.5,
          color: 'var(--text-primary)',
        }}
      >
        {skill?.name ?? 'Skill Preview'}
        <IconButton
          onClick={onClose}
          size="small"
          sx={{
            color: 'var(--text-secondary)',
            '&:hover': { color: 'var(--text-primary)' },
          }}
        >
          <CloseIcon sx={{ fontSize: 18 }} />
        </IconButton>
      </DialogTitle>
      <DialogContent sx={{ p: 0, overflow: 'auto' }}>
        {loading ? (
          <Box sx={{ display: 'flex', justifyContent: 'center', p: 4 }}>
            <CircularProgress size={28} sx={{ color: 'var(--text-secondary)' }} />
          </Box>
        ) : (
          <Box sx={{ minHeight: 300 }}>
            <MarkdownRenderer content={skill?.content ?? ''} />
          </Box>
        )}
      </DialogContent>
    </Dialog>
  );
}
