/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import React, { useEffect, useRef, useState } from 'react';

import { useNavigate } from '@tanstack/react-router';

import { Box, Typography } from '@mui/material';
import ReactMarkdown, { type ExtraProps } from 'react-markdown';
import remarkGfm from 'remark-gfm';

import { FONT_FAMILIES, FONT_SIZES } from '@/constants';

import MermaidDiagram from './MermaidDiagram';

interface TocEntry {
  id: string;
  text: string;
  level: number;
}

interface MarkdownRendererProps {
  content?: string;
  loadFromFile?: string; // Path to markdown file to load
  containerSx?: object; // Allow custom container styles
  showToc?: boolean;
}

const slugify = (text: string): string =>
  text
    .toLowerCase()
    .replace(/[^\w\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-');

const extractToc = (markdown: string): TocEntry[] => {
  const entries: TocEntry[] = [];
  const lines = markdown.split('\n');
  for (const line of lines) {
    const match = line.match(/^(#{1,3})\s+(.+)/);
    if (match) {
      const level = match[1].length;
      const text = match[2].replace(/\*\*/g, '').replace(/`/g, '').trim();
      entries.push({ id: slugify(text), text, level });
    }
  }
  return entries;
};

const styles = {
  markdownContainer: {
    p: 2,
    maxWidth: '900px',
    mx: 'auto',
    fontFamily: FONT_FAMILIES.PRIMARY,

    '& h1': {
      color: 'var(--text-primary)',
      fontSize: FONT_SIZES.LG,
      fontWeight: 700,
      mb: 2,
      mt: 3,
      pb: 1,
      borderBottom: '1px solid var(--border)',
      '&:first-of-type': { mt: 0 },
    },
    '& h2': {
      color: 'var(--text-primary)',
      fontSize: FONT_SIZES.MD,
      fontWeight: 600,
      mb: 1.5,
      mt: 2.5,
      pb: 0.5,
      borderBottom: '1px solid var(--border)',
    },
    '& h3': {
      color: 'var(--text-primary)',
      fontSize: FONT_SIZES.BASE,
      fontWeight: 600,
      mb: 1,
      mt: 2,
    },
    '& h4': {
      color: 'var(--text-primary)',
      fontSize: FONT_SIZES.SM,
      fontWeight: 600,
      mb: 1,
      mt: 1.5,
    },
    '& h5, & h6': {
      color: 'var(--text-primary)',
      fontSize: FONT_SIZES.XS,
      fontWeight: 600,
      mb: 0.75,
      mt: 1.5,
    },
    '& p': {
      color: 'var(--text-primary)',
      lineHeight: 1.6,
      mb: 1.5,
      fontSize: FONT_SIZES.BASE,
    },
    '& ul, & ol': {
      color: 'var(--text-primary)',
      pl: 3,
      mb: 1.5,
      '& li': {
        mb: 0.5,
        lineHeight: 1.6,
      },
      '& ul, & ol': {
        mt: 0.5,
        mb: 0.5,
      },
    },
    '& blockquote': {
      borderLeft: '4px solid var(--border)',
      pl: 2,
      py: 0.25,
      my: 1.5,
      color: 'var(--text-secondary)',
      fontStyle: 'italic',
      '& p': { mb: 0.5 },
    },
    '& code': {
      bgcolor: 'rgba(128,128,128,0.1)',
      color: 'var(--text-primary)',
      px: 0.75,
      py: 0.25,
      borderRadius: '3px',
      fontSize: FONT_SIZES.BASE,
      fontFamily: FONT_FAMILIES.MONOSPACE,
    },
    '& pre': {
      bgcolor: 'var(--bg-secondary)',
      p: 2,
      borderRadius: '3px',
      overflow: 'auto',
      mb: 1.5,
      '& code': {
        bgcolor: 'transparent',
        color: 'var(--text-primary)',
        p: 0,
        fontSize: FONT_SIZES.BASE,
      },
    },
    '& a': {
      color: 'var(--accent)',
      textDecoration: 'underline',
      fontWeight: 400,
      '&:hover': { color: 'var(--accent)', opacity: 0.75 },
    },
    '& table': {
      width: '100%',
      borderCollapse: 'collapse',
      mb: 1.5,
      fontSize: FONT_SIZES.BASE,
      '& th, & td': {
        border: '1px solid var(--border)',
        px: 1.5,
        py: 0.75,
        textAlign: 'left',
      },
      '& th': {
        bgcolor: 'var(--bg-secondary)',
        fontWeight: 600,
        color: 'var(--text-primary)',
      },
      '& td': { color: 'var(--text-primary)' },
      '& tr:nth-of-type(even) td': {
        bgcolor: 'var(--bg-secondary)',
      },
    },
    '& hr': {
      border: 'none',
      borderTop: '1px solid var(--border)',
      my: 2,
    },
    '& img': {
      maxWidth: '100%',
      height: 'auto',
      borderRadius: '3px',
      my: 1.5,
    },
    '& strong': {
      fontWeight: 600,
      color: 'var(--text-primary)',
    },
    '& em': { fontStyle: 'italic' },
  },
  simpleText: {
    color: 'var(--text-primary)',
    whiteSpace: 'pre-line',
    lineHeight: 1.6,
    fontSize: FONT_SIZES.BASE,
  },
  emptyText: {
    color: 'var(--text-secondary)',
    fontStyle: 'italic',
  },
};

export default function MarkdownRenderer({
  content,
  loadFromFile,
  containerSx = {},
  showToc = false,
}: MarkdownRendererProps) {
  const [markdownContent, setMarkdownContent] = useState<string>(content || '');
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [activeId, setActiveId] = useState<string>('');
  const contentRef = useRef<HTMLDivElement>(null);

  // Load markdown file if loadFromFile is provided
  useEffect(() => {
    if (loadFromFile) {
      setLoading(true);
      setError(null);

      fetch(loadFromFile)
        .then((response) => {
          if (!response.ok) {
            throw new Error('Failed to load markdown file');
          }
          return response.text();
        })
        .then((text) => {
          setMarkdownContent(text);
          setLoading(false);
        })
        .catch((err) => {
          console.error('Error loading markdown:', err);
          setError('Failed to load content');
          setLoading(false);
        });
    } else if (content !== undefined) {
      setMarkdownContent(content);
    }
  }, [loadFromFile, content]);

  const navigate = useNavigate();
  const toc = showToc ? extractToc(markdownContent) : [];

  useEffect(() => {
    if (!showToc || !contentRef.current) return;

    // Find the nearest scrollable ancestor
    let scrollEl: HTMLElement | null = contentRef.current.parentElement;
    while (scrollEl) {
      const { overflow, overflowY } = window.getComputedStyle(scrollEl);
      if (
        overflow.includes('auto') ||
        overflow.includes('scroll') ||
        overflowY.includes('auto') ||
        overflowY.includes('scroll')
      )
        break;
      scrollEl = scrollEl.parentElement;
    }
    if (!scrollEl) return;

    const updateActive = () => {
      const headings = Array.from(
        contentRef.current?.querySelectorAll('h1[id], h2[id], h3[id]') ?? [],
      );
      if (!headings.length) return;

      const threshold = scrollEl.getBoundingClientRect().top + 80;
      let active = headings[0].id;
      for (const h of headings) {
        if (h.getBoundingClientRect().top <= threshold) {
          active = h.id;
        }
      }
      setActiveId(active);
    };

    scrollEl.addEventListener('scroll', updateActive, { passive: true });
    updateActive();
    return () => scrollEl.removeEventListener('scroll', updateActive);
  }, [markdownContent, showToc]);

  const scrollToHeading = (id: string) => {
    const el = contentRef.current?.querySelector(`#${CSS.escape(id)}`);
    if (el) el.scrollIntoView({ behavior: 'smooth', block: 'start' });
  };

  const makeHeading =
    (level: 1 | 2 | 3 | 4 | 5 | 6) =>
    ({ children, ...props }: { children?: React.ReactNode; [key: string]: any }) => {
      const text =
        typeof children === 'string'
          ? children
          : Array.isArray(children)
            ? children.map((c) => (typeof c === 'string' ? c : '')).join('')
            : '';
      const id = slugify(text);
      const Tag = `h${level}` as unknown as React.ElementType;
      return (
        <Tag id={id} {...props}>
          {children}
        </Tag>
      );
    };

  const components = {
    h1: makeHeading(1),
    h2: makeHeading(2),
    h3: makeHeading(3),
    // A ```mermaid block renders as a diagram (the same source GitHub renders
    // natively). All other code blocks keep their default styling.
    code: ({
      className,
      children,
      ...rest
    }: React.HTMLAttributes<HTMLElement> & { children?: React.ReactNode }) => {
      if (/\blanguage-mermaid\b/.test(className ?? '')) {
        const code =
          typeof children === 'string'
            ? children
            : Array.isArray(children)
              ? children.join('')
              : '';
        return <MermaidDiagram chart={code.replace(/\n$/, '')} />;
      }
      return (
        <code className={className} {...rest}>
          {children}
        </code>
      );
    },
    // Unwrap the <pre> around a mermaid block so it doesn't inherit the styled
    // code-block background; everything else renders as a normal <pre>.
    pre: ({ node, children, ...rest }: React.HTMLAttributes<HTMLPreElement> & ExtraProps) => {
      const first = node?.children?.[0];
      const childClass = first && first.type === 'element' ? first.properties?.className : undefined;
      const isMermaid = Array.isArray(childClass) && childClass.includes('language-mermaid');
      if (isMermaid) return <>{children}</>;
      return <pre {...rest}>{children}</pre>;
    },
    a: ({ href, children }: { href?: string; children?: React.ReactNode }) => {
      const isInternal = href?.startsWith('/path?') || href?.startsWith('/marketplace?');
      if (isInternal) {
        return (
          <a
            href={href}
            onClick={(e) => {
              e.preventDefault();
              void navigate({ to: href as any });
            }}
          >
            {children}
          </a>
        );
      }
      return (
        <a href={href} target="_blank" rel="noopener noreferrer">
          {children}
        </a>
      );
    },
  };

  // Loading state
  if (loading) {
    return (
      <Typography variant="body2" sx={styles.emptyText}>
        Loading...
      </Typography>
    );
  }

  // Error state
  if (error) {
    return (
      <Typography variant="body2" color="error">
        {error}
      </Typography>
    );
  }

  // Empty content
  if (!markdownContent || markdownContent.trim() === '') {
    return (
      <Typography variant="body2" sx={styles.emptyText}>
        No description available
      </Typography>
    );
  }

  const hasMarkdownSyntax = /[#*`[\]_~>-]|\n\n/.test(markdownContent);

  if (!hasMarkdownSyntax) {
    return (
      <Typography variant="body2" sx={styles.simpleText}>
        {markdownContent}
      </Typography>
    );
  }

  const markdownBody = (
    <Box ref={contentRef} sx={{ ...styles.markdownContainer, ...containerSx }}>
      <ReactMarkdown remarkPlugins={[remarkGfm]} components={components}>
        {markdownContent}
      </ReactMarkdown>
    </Box>
  );

  if (!showToc || toc.length === 0) {
    return markdownBody;
  }

  return (
    <Box sx={{ display: 'flex', width: '100%', position: 'relative' }}>
      <Box sx={{ flex: 1, minWidth: 0 }}>{markdownBody}</Box>
      {/* Right TOC */}
      <Box
        sx={{
          width: 220,
          flexShrink: 0,
          position: 'sticky',
          top: 16,
          alignSelf: 'flex-start',
          maxHeight: 'calc(100vh - 80px)',
          overflowY: 'auto',
          pr: 2,
          pt: 4,
        }}
      >
        <Typography
          sx={{
            fontSize: FONT_SIZES.XXS,
            fontWeight: 600,
            color: 'var(--text-secondary)',
            textTransform: 'uppercase',
            letterSpacing: '0.08em',
            mb: 1.5,
            display: 'flex',
            alignItems: 'center',
            gap: 0.75,
          }}
        >
          <span style={{ fontSize: FONT_SIZES.ICON_SM }}>☰</span> On this page
        </Typography>
        <Box sx={{ display: 'flex', flexDirection: 'column', gap: 0.25 }}>
          {toc.map((entry) => {
            const isActive = activeId === entry.id;
            return (
              <Box
                key={entry.id}
                onClick={() => scrollToHeading(entry.id)}
                sx={{
                  position: 'relative',
                  pl: entry.level === 1 ? 0 : entry.level === 2 ? 1.5 : 3,
                  cursor: 'pointer',
                }}
              >
                {isActive && (
                  <Box
                    sx={{
                      position: 'absolute',
                      left: -8,
                      top: 0,
                      bottom: 0,
                      width: 2,
                      bgcolor: 'var(--accent)',
                      borderRadius: '0 2px 2px 0',
                    }}
                  />
                )}
                <Typography
                  sx={{
                    fontSize: FONT_SIZES.XS,
                    lineHeight: 1.6,
                    color: isActive ? 'var(--accent)' : 'var(--text-secondary)',
                    fontWeight: isActive ? 500 : 400,
                    transition: 'color 0.15s ease',
                    '&:hover': { color: 'var(--text-primary)' },
                    overflow: 'hidden',
                    textOverflow: 'ellipsis',
                    whiteSpace: 'nowrap',
                  }}
                >
                  {entry.text}
                </Typography>
              </Box>
            );
          })}
        </Box>
      </Box>
    </Box>
  );
}
