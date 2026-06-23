/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import React, { useEffect, useState } from 'react';

import { Box } from '@mui/material';

import { useTheme } from '@/contexts/ThemeContext';

interface Props {
  /** Raw mermaid source (the body of a ```mermaid fenced block). */
  chart: string;
}

/** Read a CSS custom property off <html>, with a fallback for SSR/first paint. */
const cssVar = (name: string, fallback: string): string => {
  if (typeof window === 'undefined') return fallback;
  const v = getComputedStyle(document.documentElement).getPropertyValue(name).trim();
  return v || fallback;
};

/**
 * Renders a Mermaid diagram as themed SVG.
 *
 * Mermaid needs the DOM (it measures label text), so the library is dynamically
 * imported inside the effect — code-split out of the main bundle. Theme variables
 * are mapped to the app's CSS custom properties and re-resolved when the app
 * theme (black/white) changes. A parse failure falls back to the raw source so a
 * bad diagram never blanks the page.
 */
export default function MermaidDiagram({ chart }: Props) {
  const { theme } = useTheme();
  const [svg, setSvg] = useState<string | null>(null);
  const [failed, setFailed] = useState(false);

  useEffect(() => {
    let cancelled = false;

    void (async () => {
      try {
        const mermaid = (await import('mermaid')).default;

        const ink = cssVar('--text-primary', '#e6e6e6');
        const muted = cssVar('--text-secondary', '#9aa0a6');
        const line = cssVar('--border', '#3a3a3a');
        const panel = cssVar('--bg-secondary', '#1e1e1e');
        const bg = cssVar('--bg-primary', '#121212');
        const accent = cssVar('--accent', '#5b9bd5');

        mermaid.initialize({
          startOnLoad: false,
          // "loose" enables HTML labels (foreignObject) which size to their real
          // content so node text never clips. Safe here: docs are first-party
          // content from this repo, not user input.
          securityLevel: 'loose',
          theme: 'base',
          themeVariables: {
            fontFamily: 'inherit',
            fontSize: '14px',
            primaryColor: panel,
            primaryBorderColor: line,
            primaryTextColor: ink,
            lineColor: muted,
            secondaryColor: bg,
            tertiaryColor: bg,
            background: bg,
            mainBkg: panel,
            clusterBkg: bg,
            clusterBorder: line,
            nodeBorder: line,
            titleColor: ink,
            edgeLabelBackground: panel,
            // sequence + state diagram accents
            actorBkg: panel,
            actorBorder: line,
            actorTextColor: ink,
            signalColor: ink,
            signalTextColor: ink,
            labelBoxBkgColor: panel,
            labelBoxBorderColor: line,
            labelTextColor: ink,
            noteBkgColor: bg,
            noteBorderColor: accent,
            noteTextColor: ink,
          },
          flowchart: { useMaxWidth: true, htmlLabels: true },
        });

        // Wait for webfonts so Mermaid measures real text widths (otherwise the
        // fallback font is measured and labels can overflow their boxes).
        if (typeof document !== 'undefined' && document.fonts) {
          await document.fonts.ready;
        }

        // Fresh id per render avoids collisions under React StrictMode double-mount.
        const id = `mmd-${Math.random().toString(36).slice(2)}`;
        const { svg: rendered } = await mermaid.render(id, chart);
        if (!cancelled) {
          setSvg(rendered);
          setFailed(false);
        }
      } catch (err) {
        console.error('Mermaid render failed:', err);
        if (!cancelled) setFailed(true);
      }
    })();

    return () => {
      cancelled = true;
    };
  }, [chart, theme]);

  if (failed) {
    return (
      <Box component="pre" sx={{ overflow: 'auto' }}>
        <code>{chart}</code>
      </Box>
    );
  }

  if (svg === null) {
    return (
      <Box
        aria-hidden
        sx={{
          fontFamily: 'monospace',
          whiteSpace: 'pre',
          fontSize: 12,
          color: 'var(--text-secondary)',
          opacity: 0.5,
          overflow: 'auto',
          my: 2,
        }}
      >
        {chart}
      </Box>
    );
  }

  return (
    <Box
      role="img"
      dangerouslySetInnerHTML={{ __html: svg }}
      sx={{
        display: 'flex',
        justifyContent: 'center',
        my: 2,
        overflowX: 'auto',
        '& svg': { maxWidth: '100%', height: 'auto' },
      }}
    />
  );
}
