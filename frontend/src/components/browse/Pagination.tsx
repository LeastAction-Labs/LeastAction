/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { Box, Typography } from '@mui/material';
import { styled } from '@mui/material/styles';

import {
  BORDER_RADIUS,
  FONT_SIZES,
  FONT_WEIGHTS,
  OPACITY,
  SPACING,
  TRANSITIONS,
} from '../../constants';

interface PaginationProps {
  currentPage: number;
  hasNext: boolean;
  hasPrevious?: boolean;
  onPageChange: (page: number) => void;
}

interface PageButtonProps {
  active?: boolean;
}

const PageButton = styled(Box, {
  shouldForwardProp: (prop) => prop !== 'active',
})<PageButtonProps>(({ active }) => ({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  minWidth: '32px',
  height: '32px',
  padding: `0 ${SPACING.ICON_BUTTON_MEDIUM / 2}px`, // 8px
  margin: '0 2px',
  borderRadius: `${BORDER_RADIUS.MD}rem`,
  cursor: 'pointer',
  userSelect: 'none',
  fontSize: FONT_SIZES.BASE,
  fontWeight: active ? FONT_WEIGHTS.WEIGHT_600 : FONT_WEIGHTS.NORMAL,
  color: active ? 'var(--text-primary)' : 'var(--text-secondary)',
  backgroundColor: active ? 'var(--bg-secondary)' : 'transparent',
  border: active ? '1px solid var(--border)' : '1px solid transparent',
  transition: `all ${TRANSITIONS.FAST} ${TRANSITIONS.EASE}`,

  '&:hover': {
    backgroundColor: active ? 'var(--bg-secondary)' : 'var(--bg-hover)',
    borderColor: 'var(--border)',
  },

  '&.disabled': {
    opacity: OPACITY.DISABLED,
    cursor: 'not-allowed',
    '&:hover': {
      backgroundColor: 'transparent',
      borderColor: 'transparent',
    },
  },
}));

const PaginationContainer = styled(Box)({
  display: 'flex',
  alignItems: 'center',
  justifyContent: 'center',
  gap: '4px',
  padding: `${SPACING.ICON_BUTTON_LARGE}px 0`, // 16px top/bottom
  marginTop: `${SPACING.ICON_BUTTON_LARGE}px`, // 16px
  borderTop: '1px solid var(--border)',
});

export default function Pagination({
  currentPage,
  hasNext,
  hasPrevious = currentPage > 1,
  onPageChange,
}: PaginationProps) {
  const showPagination = hasPrevious || hasNext;
  if (!showPagination) return null;

  const pageNumbers: number[] = [1];
  if (currentPage > 1 && !pageNumbers.includes(currentPage)) pageNumbers.push(currentPage);
  if (hasNext && currentPage + 1 > 1 && !pageNumbers.includes(currentPage + 1))
    pageNumbers.push(currentPage + 1);
  pageNumbers.sort((a, b) => a - b);

  return (
    <PaginationContainer>
      <PageButton
        className={!hasPrevious ? 'disabled' : ''}
        onClick={() => hasPrevious && onPageChange(currentPage - 1)}
      >
        <Typography
          variant="body2"
          sx={{
            fontWeight: FONT_WEIGHTS.NORMAL,
            fontSize: FONT_SIZES.SM,
          }}
        >
          Previous
        </Typography>
      </PageButton>

      {pageNumbers.map((page, index) => {
        const showEllipsis = index > 0 && pageNumbers[index] - pageNumbers[index - 1] > 1;
        return (
          <Box key={page} sx={{ display: 'flex', alignItems: 'center' }}>
            {showEllipsis && (
              <Typography
                variant="body2"
                sx={{
                  mx: 1,
                  color: 'var(--text-secondary)',
                  userSelect: 'none',
                  fontSize: FONT_SIZES.SM,
                  opacity: OPACITY.MEDIUM,
                }}
              >
                ...
              </Typography>
            )}
            <PageButton active={currentPage === page} onClick={() => onPageChange(page)}>
              <Typography
                variant="body2"
                sx={{
                  fontWeight: currentPage === page ? FONT_WEIGHTS.WEIGHT_600 : FONT_WEIGHTS.NORMAL,
                  fontSize: FONT_SIZES.SM,
                }}
              >
                {page}
              </Typography>
            </PageButton>
          </Box>
        );
      })}

      <PageButton
        className={!hasNext ? 'disabled' : ''}
        onClick={() => hasNext && onPageChange(currentPage + 1)}
      >
        <Typography
          variant="body2"
          sx={{
            fontWeight: FONT_WEIGHTS.NORMAL,
            fontSize: FONT_SIZES.SM,
          }}
        >
          Next
        </Typography>
      </PageButton>
    </PaginationContainer>
  );
}
