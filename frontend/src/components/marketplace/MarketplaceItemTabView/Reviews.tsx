/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useEffect, useState } from 'react';

import { Box, Button, Paper, Rating, TextField, Typography } from '@mui/material';

import type { FullItemData } from '@/components/browse';
import { useMarketplace } from '@/contexts/MarketplaceContext';
import { createCatalogItem, searchCatalogItems } from '@/services';

export interface Review {
  content: string;
  rating: number;
  publisher: string;
}

interface ItemReviews {
  userReview: Review | null;
  reviews: Review[];
  hasNext: boolean;
  counter: number;
}

interface ReviewsProps {
  item: FullItemData;
}

const Reviews = ({ item }: ReviewsProps) => {
  const [itemReviews, setItemReviews] = useState<ItemReviews>({
    userReview: null,
    reviews: [],
    hasNext: false,
    counter: 1,
  });
  const [isEditing, setIsEditing] = useState(false);
  const [reviewForm, setReviewForm] = useState({ rating: 5, content: '' });

  const { user: marketplaceUser } = useMarketplace();

  const setUserReview = async () => {
    if (marketplaceUser) {
      const response = await searchCatalogItems('review', true, {
        filters: { parent_laui: item.laui, publisher: marketplaceUser.username },
        projection: ['content', 'rating', 'publisher'],
        page: itemReviews.counter,
      });

      if (response.items.length > 0) {
        const existingReview = response.items[0];
        setItemReviews((prev) => ({ ...prev, userReview: existingReview }));
        setReviewForm({
          rating: existingReview.rating || 5,
          content: existingReview.content || '',
        });
      } else {
        setItemReviews((prev) => ({ ...prev, userReview: null }));
        setReviewForm({ rating: 5, content: '' });
      }
    }
  };

  useEffect(() => {
    void setUserReview();
  }, [item.laui, marketplaceUser]);

  useEffect(() => {
    const getReviews = async () => {
      const response = await searchCatalogItems('review', true, {
        filters: { parent_laui: item.laui },
        projection: ['content', 'rating', 'publisher'],
        page: itemReviews.counter,
      });
      setItemReviews((prev) => ({
        ...prev,
        reviews: [...prev.reviews, ...response.items],
        hasNext: response.pagination.has_next,
      }));
    };
    void getReviews();
  }, [item.laui, itemReviews.counter]);

  return (
    <Box sx={{ display: 'flex', flexDirection: 'column', gap: 3, p: 1 }}>
      {marketplaceUser && (
        <Paper
          variant="outlined"
          sx={{
            p: 2,
            bgcolor: 'var(--bg-secondary)',
            borderColor: 'var(--border-color)',
          }}
        >
          <Typography
            variant="subtitle2"
            sx={{ mb: 1, fontWeight: 700, color: 'var(--text-primary)' }}
          >
            {itemReviews.userReview ? 'Your Review' : 'Write a Review'}
          </Typography>

          {!itemReviews.userReview || isEditing ? (
            <Box sx={{ display: 'flex', flexDirection: 'column', gap: 1.5 }}>
              <Rating
                value={reviewForm.rating}
                onChange={(_, val) => setReviewForm((p) => ({ ...p, rating: val || 5 }))}
                size="small"
              />
              <TextField
                multiline
                rows={3}
                fullWidth
                placeholder="Tell others what you think (max 100 characters)..."
                value={reviewForm.content}
                onChange={(e) =>
                  setReviewForm((p) => ({
                    ...p,
                    content: e.target.value.slice(0, 100),
                  }))
                }
                helperText={`${reviewForm.content.length}/100`}
                sx={{
                  '& .MuiInputBase-root': {
                    fontSize: '13px',
                    color: 'var(--text-primary)',
                  },
                  '& .MuiFormHelperText-root': { textAlign: 'right' },
                }}
              />
              <Box sx={{ display: 'flex', gap: 1 }}>
                <Button
                  variant="contained"
                  size="small"
                  sx={{ textTransform: 'none', bgcolor: 'var(--accent)' }}
                  onClick={() => {
                    void (async () => {
                      try {
                        await createCatalogItem(
                          {
                            ...reviewForm,
                            item_type: 'review',
                            parent_laui: item.laui,
                          },
                          true,
                        );
                        void setUserReview();
                        setIsEditing(false);
                      } catch {
                        /* ignore */
                      }
                    })();
                  }}
                >
                  {itemReviews.userReview ? 'Update' : 'Submit'}
                </Button>
                {isEditing && (
                  <Button
                    size="small"
                    sx={{ textTransform: 'none' }}
                    onClick={() => setIsEditing(false)}
                  >
                    Cancel
                  </Button>
                )}
              </Box>
            </Box>
          ) : (
            <Box>
              <Rating value={itemReviews.userReview.rating} readOnly size="small" />
              <Typography variant="body2" sx={{ mt: 1, color: 'var(--text-primary)' }}>
                {itemReviews.userReview.content}
              </Typography>
              <Button
                size="small"
                sx={{ mt: 1, textTransform: 'none', color: 'var(--accent)', p: 0 }}
                onClick={() => setIsEditing(true)}
              >
                Edit Review
              </Button>
            </Box>
          )}
        </Paper>
      )}

      <Box sx={{ display: 'flex', flexDirection: 'column', gap: 2 }}>
        <Typography variant="subtitle1" sx={{ fontWeight: 600, color: 'var(--text-primary)' }}>
          Community Reviews
        </Typography>
        {itemReviews.reviews
          .filter((review) => review.publisher !== marketplaceUser?.username)
          .map((review, index) => (
            <Box key={index} sx={{ borderBottom: '1px solid var(--border-color)', pb: 2 }}>
              <Box
                sx={{
                  display: 'flex',
                  justifyContent: 'space-between',
                  alignItems: 'center',
                  mb: 0.5,
                }}
              >
                <Typography variant="caption" sx={{ fontWeight: 700, color: 'var(--accent)' }}>
                  {review.publisher}
                </Typography>
                <Rating value={review.rating} readOnly size="small" />
              </Box>
              <Typography variant="body2" sx={{ color: 'var(--text-primary)', fontSize: '13px' }}>
                {review.content}
              </Typography>
            </Box>
          ))}

        {itemReviews.hasNext && (
          <Button
            size="small"
            onClick={() => setItemReviews((prev) => ({ ...prev, counter: prev.counter + 1 }))}
            sx={{
              alignSelf: 'center',
              textTransform: 'none',
              color: 'var(--text-secondary)',
            }}
          >
            Load More Reviews
          </Button>
        )}

        {itemReviews.reviews.length === 0 && !itemReviews.userReview && (
          <Typography variant="body2" sx={{ fontStyle: 'italic', color: 'var(--text-secondary)' }}>
            No reviews yet.
          </Typography>
        )}
      </Box>
    </Box>
  );
};

export default Reviews;
