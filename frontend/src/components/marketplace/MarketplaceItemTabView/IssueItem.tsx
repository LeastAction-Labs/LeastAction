/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useState } from 'react';

import { Box, Button, Paper, TextField, Typography } from '@mui/material';

import { createCatalogItem } from '@/services';

import { type Issue as IssueInterface } from './Issues';

interface IssueProps {
  issue: IssueInterface;
  editable?: boolean;
  parentLaui?: string;
}

export const IssueItem = ({ issue, editable = false, parentLaui }: IssueProps) => {
  const [isEditing, setIsEditing] = useState<boolean>(false);
  const [editedContent, setEditedContent] = useState<string>(issue.content);
  const [loading, setLoading] = useState<boolean>(false);

  const handleSave = async () => {
    setLoading(true);
    try {
      await createCatalogItem({ ...issue, content: editedContent, parent_laui: parentLaui }, true);
      setIsEditing(false);
    } catch {
      setEditedContent(issue.content);
    } finally {
      setLoading(false);
    }
  };

  const handleCancel = () => {
    setEditedContent(issue.content); // Revert local state
    setIsEditing(false);
  };

  return (
    <Paper
      variant="outlined"
      sx={{ p: 2, mb: 2, bgcolor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
    >
      <Box sx={{ display: 'flex', justifyContent: 'space-between', mb: 1 }}>
        <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'var(--accent)' }}>
          {issue.name}
        </Typography>
        <Typography variant="caption" sx={{ color: 'var(--text-secondary)' }}>
          By {issue.publisher || 'Anonymous'}
        </Typography>
      </Box>

      {isEditing ? (
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
          <TextField
            multiline
            rows={3}
            fullWidth
            size="small"
            value={editedContent}
            onChange={(e) => setEditedContent(e.target.value)}
            sx={{
              '& .MuiInputBase-root': {
                bgcolor: 'var(--bg-tertiary)',
                color: 'var(--text-primary)',
              },
              '& .MuiOutlinedInput-notchedOutline': {
                borderColor: 'var(--border)',
              },
              '& .MuiFormHelperText-root': {
                color: 'var(--text-secondary)',
              },
            }}
          />
          <Box sx={{ display: 'flex', gap: 1 }}>
            <Button
              variant="contained"
              size="small"
              onClick={() => void handleSave()}
              disabled={loading}
              sx={{ textTransform: 'none' }}
            >
              {loading ? 'Saving...' : 'Save Changes'}
            </Button>
            <Button size="small" onClick={handleCancel} sx={{ textTransform: 'none' }}>
              Cancel
            </Button>
          </Box>
        </Box>
      ) : (
        <Box>
          <Typography variant="body2" sx={{ color: 'var(--text-primary)', fontSize: '13px' }}>
            {editedContent}
          </Typography>

          {editable && (
            <Button
              size="small"
              onClick={() => setIsEditing(true)}
              sx={{
                mt: 1,
                textTransform: 'none',
                p: 0,
                minWidth: 0,
                color: 'var(--accent)',
              }}
            >
              Edit Issue
            </Button>
          )}
        </Box>
      )}
    </Paper>
  );
};
