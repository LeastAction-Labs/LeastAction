/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import { Box, Button, Divider, Paper, TextField, Typography } from '@mui/material';

import type { FullItemData } from '@/components/browse';
import { useMarketplace } from '@/contexts/MarketplaceContext';
import { createAnonymousCatalogItem, createCatalogItem, searchCatalogItems } from '@/services';

import { IssueItem } from './IssueItem';

export interface Issue {
  name: string;
  content: string;
  publisher?: string;
}

interface IssuesGroup {
  items: Issue[];
  counter: number;
  hasNext: boolean;
}

interface IssuesState {
  user: IssuesGroup;
  community: IssuesGroup;
}

interface IssuesProps {
  item: FullItemData;
}

const Issues = ({ item }: IssuesProps) => {
  const [issuesState, setIssuesState] = useState<IssuesState>({
    user: { items: [], counter: 1, hasNext: false },
    community: { items: [], counter: 1, hasNext: false },
  });

  // Form States
  const [isAdding, setIsAdding] = useState(false);
  const [newIssue, setNewIssue] = useState({ name: '', content: '' });
  const [isSubmitting, setIsSubmitting] = useState(false);

  const { user: marketplaceUser } = useMarketplace();

  const getUserIssues = async (reset = false) => {
    if (!marketplaceUser) return;

    const page = reset ? 1 : issuesState.user.counter;
    try {
      const response: any = await searchCatalogItems('issue', true, {
        filters: { parent_laui: item.laui, publisher: marketplaceUser.username },
        projection: ['content', 'name', 'publisher'],
        page: page,
      });

      setIssuesState((prev) => ({
        ...prev,
        user: {
          items: page === 1 ? response.items : [...prev.user.items, ...response.items],
          counter: page,
          hasNext: response.pagination.has_next,
        },
      }));
    } catch {
      /* ignore */
    }
  };

  const getCommunityIssues = async (reset = false) => {
    const page = reset ? 1 : issuesState.community.counter;
    try {
      const response: any = await searchCatalogItems('issue', true, {
        filters: { parent_laui: item.laui },
        projection: ['content', 'name', 'publisher', 'laui'],
        page: page,
      });

      setIssuesState((prev) => ({
        ...prev,
        community: {
          items: page === 1 ? response.items : [...prev.community.items, ...response.items],
          counter: page,
          hasNext: response.pagination.has_next,
        },
      }));
    } catch {
      /* ignore */
    }
  };

  const handleAddIssue = async () => {
    if (!newIssue.name || !newIssue.content) return;
    setIsSubmitting(true);
    try {
      const payload = {
        ...newIssue,
        item_type: 'issue',
        parent_laui: item.laui,
      };

      if (marketplaceUser) {
        await createCatalogItem(payload, true);
      } else {
        await createAnonymousCatalogItem(payload, true);
      }

      setNewIssue({ name: '', content: '' });
      setIsAdding(false);
      await getUserIssues(true);
      await getCommunityIssues(true); // Refresh community list as well
    } catch {
      /* ignore */
    } finally {
      setIsSubmitting(false);
    }
  };

  useEffect(() => {
    void getUserIssues(true);
  }, [item.laui, issuesState.user.counter]);

  useEffect(() => {
    void getCommunityIssues(true);
  }, [item.laui, issuesState.community.counter]);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 4, p: 1 }}>
      {/* SECTION: ADD NEW ISSUE */}
      <Paper
        variant="outlined"
        sx={{ p: 2, bgcolor: 'var(--bg-secondary)', borderColor: 'var(--border-color)' }}
      >
        {!isAdding ? (
          <Button
            variant="contained"
            size="small"
            onClick={() => setIsAdding(true)}
            sx={{ textTransform: 'none', bgcolor: 'var(--accent)' }}
          >
            Report a New Issue
          </Button>
        ) : (
          <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
            <Typography variant="subtitle2" sx={{ fontWeight: 700, color: 'var(--text-primary)' }}>
              New Issue Report
            </Typography>
            <TextField
              label="Title"
              fullWidth
              size="small"
              value={newIssue.name}
              onChange={(e) => setNewIssue((prev) => ({ ...prev, name: e.target.value }))}
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
            <TextField
              label="Description"
              multiline
              rows={3}
              fullWidth
              size="small"
              value={newIssue.content}
              onChange={(e) => setNewIssue((prev) => ({ ...prev, content: e.target.value }))}
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
                disabled={isSubmitting}
                onClick={() => void handleAddIssue()}
                sx={{ textTransform: 'none' }}
              >
                {isSubmitting ? 'Submitting...' : 'Submit Issue'}
              </Button>
              <Button
                size="small"
                onClick={() => setIsAdding(false)}
                sx={{ textTransform: 'none' }}
              >
                Cancel
              </Button>
            </Box>
          </Box>
        )}
      </Paper>

      {/* SECTION: USER ISSUES */}
      {marketplaceUser && (
        <Box>
          <Typography
            variant="subtitle1"
            sx={{ fontWeight: 700, mb: 2, color: 'var(--text-primary)' }}
          >
            Your Reported Issues
          </Typography>
          {issuesState.user.items.length > 0 ? (
            issuesState.user.items.map((issue, idx) => (
              <IssueItem key={idx} issue={issue} editable={true} parentLaui={item.laui} />
            ))
          ) : (
            <Typography
              variant="body2"
              sx={{ color: 'var(--text-secondary)', fontStyle: 'italic' }}
            >
              No issues reported by you.
            </Typography>
          )}

          {issuesState.user.hasNext && (
            <Button
              size="small"
              onClick={() => {
                setIssuesState((p) => ({
                  ...p,
                  user: { ...p.user, counter: p.user.counter + 1 },
                }));
                void getUserIssues();
              }}
              sx={{ mt: 1, textTransform: 'none' }}
            >
              Load More of My Issues
            </Button>
          )}
        </Box>
      )}

      <Divider />

      {/* SECTION: COMMUNITY ISSUES */}
      <Box>
        <Typography
          variant="subtitle1"
          sx={{ fontWeight: 700, mb: 2, color: 'var(--text-primary)' }}
        >
          Community Issues
        </Typography>
        {issuesState.community.items
          .filter((issue) => issue.publisher !== marketplaceUser?.username)
          .map((issue, idx) => (
            <IssueItem key={idx} issue={issue} editable={false} />
          ))}

        {issuesState.community.hasNext && (
          <Box sx={{ display: 'flex', justifyContent: 'center', mt: 2 }}>
            <Button
              variant="outlined"
              size="small"
              onClick={() => {
                setIssuesState((p) => ({
                  ...p,
                  community: { ...p.community, counter: p.community.counter + 1 },
                }));
                void getCommunityIssues();
              }}
              sx={{ textTransform: 'none', color: 'var(--text-secondary)' }}
            >
              Load More Community Issues
            </Button>
          </Box>
        )}
      </Box>
    </Box>
  );
};

export default Issues;
