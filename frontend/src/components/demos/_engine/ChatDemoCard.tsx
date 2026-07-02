/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */

/**
 * ChatDemoCard — the shared, scripted product-demo engine.
 *
 * A self-contained, dependency-free (no MUI / framer-motion) chat card that
 * replays a canned conversation on a loop. Every demo card is just *data*: a
 * question + a list of assistant `segments`. This keeps each demo to ~30 lines
 * so the library can scale to 100+ examples without copy-pasting the timeline.
 *
 * Styled to match the real ChatPanel (user bubble = accent, assistant bubble =
 * --bg-secondary + --border, italic meta line, input bar, skill chip). Uses the
 * app theme vars so it inherits the live theme when mounted in the app, with
 * fallbacks to the default black theme when rendered standalone.
 *
 * Remotion note: swap useLoopClock for useCurrentFrame() to render to video.
 */
import { useEffect, useMemo, useRef, useState } from 'react';

// ---- theme tokens (fall back to the default "black" theme when unthemed) ----
const ACCENT = 'var(--accent, rgb(255,82,86))';
const BG = 'var(--bg-primary, rgb(0,0,0))';
const CARD = 'var(--bg-secondary, rgb(20,20,20))';
const TEXT = 'var(--text-primary, rgb(255,255,255))';
const TEXT_DIM = 'var(--text-secondary, rgb(200,200,200))';
const BORDER = 'var(--border, rgba(255,255,255,0.14))';
const FONT = "'Roboto', system-ui, -apple-system, 'Segoe UI', Helvetica, Arial, sans-serif";
const WARN = '#f5a623';
const OK = 'rgb(17,212,82)';
const ERR = 'rgb(239,83,80)';

// ---- metadata every demo file exports (drives the /demo page) ---------------
export interface DemoMeta {
  title: string;
  category?: string;
  /** sort order within a category (lower first) */
  order?: number;
}

// ---- the declarative script -------------------------------------------------
export type ListStatus = 'ok' | 'warn' | 'error' | 'info' | 'pending';
export interface ListItem {
  status: ListStatus;
  text: string;
  /** optional trailing mono detail, e.g. a row count */
  detail?: string;
}
export interface ActionBtn {
  label: string;
  variant?: 'primary' | 'secondary';
}

export type Segment =
  | { kind: 'text'; text: string }
  | { kind: 'list'; items: ListItem[] }
  | { kind: 'callout'; tone?: 'accent' | 'warn'; label?: string; text: string; actions?: ActionBtn[] }
  | { kind: 'actions'; actions: ActionBtn[] };

export interface ChatDemoScript {
  /** chat panel header label */
  title: string;
  /** skill chip label */
  chip: string;
  /** the user's prompt */
  question: string;
  /** tools shown in the assistant meta line, e.g. "inspect_data" */
  tools?: string;
  segments: Segment[];
}

// ---- timeline tuning (ms) ---------------------------------------------------
const TL = {
  fadeIn: 300,
  userIn: [300, 650] as const,
  loading: [800, 1500] as const,
  assistantIn: [1550, 1800] as const,
  segStart: 1800,
  segGap: 250,
  wordStep: 65,
  itemStep: 260,
  itemFade: 230,
  calloutDur: 520,
  actionsDur: 450,
  hold: 2400,
  fadeOut: 450,
};

// ---- helpers ----------------------------------------------------------------
const clamp = (n: number, lo = 0, hi = 1) => Math.min(hi, Math.max(lo, n));
const ramp = (t: number, start: number, end: number) => clamp((t - start) / (end - start));
const easeOut = (p: number) => 1 - Math.pow(1 - p, 3);

/**
 * Split text into word tokens, tracking `**bold**` state across word
 * boundaries so multi-word spans (e.g. "**full loop.**") render correctly while
 * still streaming one word at a time. Markers are stripped from the output.
 */
function tokenizeWords(text: string): { text: string; bold: boolean }[] {
  const tokens: { text: string; bold: boolean }[] = [];
  let bold = false;
  for (const raw of text.split(' ')) {
    let cleaned = '';
    let contentBold = false;
    let i = 0;
    while (i < raw.length) {
      if (raw[i] === '*' && raw[i + 1] === '*') {
        bold = !bold;
        i += 2;
      } else {
        if (bold) contentBold = true;
        cleaned += raw[i];
        i += 1;
      }
    }
    tokens.push({ text: cleaned, bold: contentBold });
  }
  return tokens;
}

function segDuration(seg: Segment): number {
  switch (seg.kind) {
    case 'text':
      return Math.max(seg.text.split(' ').length * TL.wordStep, 450);
    case 'list':
      return seg.items.length * TL.itemStep + (TL.itemFade - TL.itemStep > 0 ? TL.itemFade - TL.itemStep : 0);
    case 'callout':
      return TL.calloutDur;
    case 'actions':
      return TL.actionsDur;
  }
}

/** looping rAF clock — swap for useCurrentFrame() in Remotion */
function useLoopClock(durationMs: number, playing: boolean) {
  const [t, setT] = useState(0);
  useEffect(() => {
    if (!playing) return;
    let raf = 0;
    let start: number | null = null;
    const tick = (now: number) => {
      if (start === null) start = now;
      setT((now - start) % durationMs);
      raf = requestAnimationFrame(tick);
    };
    raf = requestAnimationFrame(tick);
    return () => cancelAnimationFrame(raf);
  }, [durationMs, playing]);
  return t;
}

// ---- icons ------------------------------------------------------------------
const Sparkle = ({ size = 14, color = '#fff' }: { size?: number; color?: string }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill={color} aria-hidden>
    <path d="M12 2l1.9 5.6L19.5 9l-5.6 1.9L12 16l-1.9-5.1L4.5 9l5.6-1.4L12 2z" />
  </svg>
);
const Help = ({ color }: { color: string }) => (
  <svg width="18" height="18" viewBox="0 0 24 24" fill="none" aria-hidden style={{ color }}>
    <circle cx="12" cy="12" r="9" stroke="currentColor" strokeWidth="1.6" />
    <path d="M9.6 9.2a2.4 2.4 0 1 1 3.2 2.3c-.8.3-1.3.9-1.3 1.8" stroke="currentColor" strokeWidth="1.6" strokeLinecap="round" />
    <circle cx="11.5" cy="16.3" r="0.9" fill="currentColor" />
  </svg>
);
const Send = ({ color }: { color: string }) => (
  <svg width="20" height="20" viewBox="0 0 24 24" fill="currentColor" aria-hidden style={{ color }}>
    <path d="M3 20.5l18-8.5L3 3.5l.01 6.6L15 12 3.01 13.9 3 20.5z" />
  </svg>
);
function StatusIcon({ status }: { status: ListStatus }) {
  const c = { ok: OK, warn: WARN, error: ERR, info: ACCENT, pending: TEXT_DIM }[status];
  const common = { width: 14, height: 14, viewBox: '0 0 14 14', fill: 'none', style: { flexShrink: 0, color: c } } as const;
  if (status === 'ok')
    return (
      <svg {...common} aria-hidden>
        <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.2" opacity="0.45" />
        <path d="M4.2 7.1L6.1 9 9.8 5.1" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" strokeLinejoin="round" />
      </svg>
    );
  if (status === 'warn')
    return (
      <svg {...common} aria-hidden>
        <path d="M7 1.5L13 12H1L7 1.5Z" stroke="currentColor" strokeWidth="1.2" strokeLinejoin="round" opacity="0.75" />
        <path d="M7 5.2V7.8" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
        <circle cx="7" cy="9.8" r="0.75" fill="currentColor" />
      </svg>
    );
  if (status === 'error')
    return (
      <svg {...common} aria-hidden>
        <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.2" opacity="0.5" />
        <path d="M4.8 4.8l4.4 4.4M9.2 4.8l-4.4 4.4" stroke="currentColor" strokeWidth="1.5" strokeLinecap="round" />
      </svg>
    );
  if (status === 'pending')
    return (
      <svg {...common} aria-hidden style={{ ...common.style, animation: 'la-spin 0.9s linear infinite' }}>
        <circle cx="7" cy="7" r="5.5" stroke="currentColor" strokeWidth="1.4" opacity="0.3" />
        <path d="M7 1.5a5.5 5.5 0 0 1 5.5 5.5" stroke="currentColor" strokeWidth="1.4" strokeLinecap="round" />
      </svg>
    );
  // info
  return (
    <svg {...common} aria-hidden>
      <circle cx="7" cy="7" r="6" stroke="currentColor" strokeWidth="1.2" opacity="0.5" />
      <circle cx="7" cy="4.4" r="0.8" fill="currentColor" />
      <path d="M7 6.4V10" stroke="currentColor" strokeWidth="1.3" strokeLinecap="round" />
    </svg>
  );
}

function DemoButton({ a }: { a: ActionBtn }) {
  const primary = a.variant !== 'secondary';
  return (
    <span
      style={{
        fontFamily: FONT,
        fontSize: 11.5,
        fontWeight: primary ? 600 : 400,
        borderRadius: 6,
        padding: '5px 11px',
        cursor: 'default',
        ...(primary
          ? { background: ACCENT, color: '#fff', border: `1px solid ${ACCENT}` }
          : { background: 'transparent', color: TEXT_DIM, border: `1px solid ${BORDER}` }),
      }}
    >
      {a.label}
    </span>
  );
}

export interface ChatDemoCardProps extends ChatDemoScript {
  playing?: boolean;
}

export default function ChatDemoCard({ title, chip, question, tools, segments, playing = true }: ChatDemoCardProps) {
  // precompute each segment's start time from the ones before it
  const { starts, total } = useMemo(() => {
    const starts: number[] = [];
    let cursor = TL.segStart;
    for (const seg of segments) {
      starts.push(cursor);
      cursor += segDuration(seg) + TL.segGap;
    }
    const end = (starts.length ? cursor - TL.segGap : TL.segStart) + TL.hold + TL.fadeOut;
    return { starts, total: end };
  }, [segments]);

  const t = useLoopClock(total, playing);

  const shellOpacity = ramp(t, 0, TL.fadeIn);
  const convoOpacity = 1 - ramp(t, total - TL.fadeOut, total);
  const uReveal = ramp(t, TL.userIn[0], TL.userIn[1]);
  const loading = t >= TL.loading[0] && t < TL.loading[1];
  const aReveal = ramp(t, TL.assistantIn[0], TL.assistantIn[1]);

  // keep the message list pinned to the bottom as content streams in
  const scrollRef = useRef<HTMLDivElement>(null);
  useEffect(() => {
    const el = scrollRef.current;
    if (el) el.scrollTop = el.scrollHeight;
  }, [t]);

  const bubbleBase: React.CSSProperties = {
    maxWidth: '88%',
    padding: '8px 12px',
    borderRadius: 10,
    fontFamily: FONT,
    fontSize: 12.5,
    lineHeight: 1.55,
  };

  return (
    <div
      aria-label={`LeastAction demo: ${title}`}
      style={{
        display: 'flex',
        flexDirection: 'column',
        width: '100%',
        maxWidth: 400,
        height: 480,
        borderRadius: 12,
        border: `1px solid ${BORDER}`,
        background: BG,
        boxShadow: 'rgba(0,0,0,0.5) 0 24px 64px, rgba(0,0,0,0.3) 0 6px 20px',
        overflow: 'hidden',
        fontFamily: FONT,
        opacity: shellOpacity,
      }}
    >
      <style>{`
        @keyframes la-blink { 0%,49%{opacity:1} 50%,100%{opacity:0} }
        @keyframes la-spin { to { transform: rotate(360deg) } }
        .la-msgs { scrollbar-width: none; }
        .la-msgs::-webkit-scrollbar { display: none; }
      `}</style>

      {/* header */}
      <div style={{ display: 'flex', alignItems: 'center', gap: 8, padding: '10px 14px', borderBottom: `1px solid ${BORDER}`, flexShrink: 0 }}>
        <span style={{ width: 7, height: 7, borderRadius: 99, background: ACCENT }} />
        <span style={{ fontFamily: FONT, fontSize: 13, fontWeight: 600, color: TEXT }}>{title}</span>
      </div>

      {/* messages */}
      <div ref={scrollRef} className="la-msgs" style={{ flex: 1, overflowY: 'auto', padding: 12, display: 'flex', flexDirection: 'column', gap: 8, opacity: convoOpacity }}>
        {/* user bubble */}
        <div style={{ ...bubbleBase, alignSelf: 'flex-end', background: ACCENT, color: TEXT, opacity: uReveal, transform: `translateX(${(1 - easeOut(uReveal)) * 16}px)` }}>
          {question}
        </div>

        {/* loading spinner */}
        {loading && (
          <div style={{ alignSelf: 'flex-start', padding: 6 }}>
            <span style={{ display: 'inline-block', width: 18, height: 18, borderRadius: '50%', border: `2px solid color-mix(in srgb, ${ACCENT} 30%, transparent)`, borderTopColor: ACCENT, animation: 'la-spin 0.8s linear infinite' }} />
          </div>
        )}

        {/* assistant bubble */}
        {aReveal > 0 && (
          <div style={{ ...bubbleBase, maxWidth: '100%', alignSelf: 'flex-start', background: CARD, color: TEXT, border: `1px solid ${BORDER}`, opacity: aReveal }}>
            <div style={{ fontSize: 10, color: TEXT_DIM, marginBottom: 6, fontStyle: 'italic' }}>
              {tools ? `Used: ${tools}  ·  markdown` : 'markdown'}
            </div>

            <div style={{ display: 'flex', flexDirection: 'column', gap: 10 }}>
              {segments.map((seg, i) => (
                <SegmentView key={i} seg={seg} t={t} start={starts[i]} />
              ))}
            </div>
          </div>
        )}
      </div>

      {/* input bar (static) */}
      <div style={{ display: 'flex', gap: 4, alignItems: 'flex-end', padding: 8, borderTop: `1px solid ${BORDER}` }}>
        <div style={{ flex: 1, background: CARD, border: `1px solid ${BORDER}`, borderRadius: 8, padding: '8px 10px', fontFamily: FONT, fontSize: 12, color: TEXT_DIM }}>Type a message...</div>
        <span style={{ padding: 6, display: 'flex' }}><Help color={TEXT_DIM} /></span>
        <span style={{ padding: 6, display: 'flex' }}><Send color={ACCENT} /></span>
      </div>

      {/* skill chip + search row (static) */}
      <div style={{ padding: '0 8px 10px' }}>
        <div style={{ display: 'flex', flexWrap: 'wrap', gap: 6, marginBottom: 6 }}>
          <span style={{ display: 'inline-flex', alignItems: 'center', gap: 5, height: 24, padding: '0 9px', borderRadius: 12, background: ACCENT, color: '#fff', fontFamily: FONT, fontSize: 11 }}>
            <Sparkle size={13} color="#fff" />
            {chip}
          </span>
        </div>
        <div style={{ display: 'flex', alignItems: 'center', gap: 6, height: 30, padding: '0 10px', background: CARD, border: `1px solid ${BORDER}`, borderRadius: 6, fontFamily: FONT, fontSize: 11, color: TEXT_DIM }}>
          <Sparkle size={14} color={TEXT_DIM} />
          Search skills (12)...
        </div>
      </div>
    </div>
  );
}

// ---- per-segment renderer ---------------------------------------------------
function SegmentView({ seg, t, start }: { seg: Segment; t: number; start: number }) {
  if (seg.kind === 'text') {
    const tokens = tokenizeWords(seg.text);
    const count = t < start ? 0 : Math.min(tokens.length, Math.floor((t - start) / TL.wordStep) + 1);
    if (count === 0) return null;
    const streaming = t >= start && t < start + tokens.length * TL.wordStep;
    return (
      <p style={{ margin: 0, fontFamily: FONT, fontSize: 12.5, lineHeight: 1.6, color: TEXT }}>
        {tokens.slice(0, count).map((tok, i) => (
          <span key={i} style={{ fontWeight: tok.bold ? 700 : 400 }}>
            {tok.text}{' '}
          </span>
        ))}
        {streaming && (
          <span style={{ display: 'inline-block', width: 2, height: '1em', background: ACCENT, marginLeft: 1, verticalAlign: 'text-bottom', borderRadius: 1, animation: 'la-blink 1s step-end infinite' }} />
        )}
      </p>
    );
  }

  if (seg.kind === 'list') {
    return (
      <div style={{ display: 'flex', flexDirection: 'column', gap: 6 }}>
        {seg.items.map((it, i) => {
          const p = ramp(t, start + i * TL.itemStep, start + i * TL.itemStep + TL.itemFade);
          if (p === 0) return null;
          return (
            <div key={i} style={{ display: 'flex', alignItems: 'center', gap: 8, opacity: p, transform: `translateX(${(1 - easeOut(p)) * 8}px)` }}>
              <StatusIcon status={it.status} />
              <span style={{ fontFamily: FONT, fontSize: 12, color: it.status === 'ok' || it.status === 'pending' ? TEXT_DIM : TEXT }}>
                {it.text}
              </span>
              {it.detail && (
                <span style={{ marginLeft: 'auto', fontFamily: 'ui-monospace, monospace', fontSize: 11, color: TEXT_DIM }}>{it.detail}</span>
              )}
            </div>
          );
        })}
      </div>
    );
  }

  if (seg.kind === 'callout') {
    const p = ramp(t, start, start + TL.calloutDur);
    if (p === 0) return null;
    const tone = seg.tone ?? 'accent';
    const c = tone === 'warn' ? WARN : ACCENT;
    return (
      <div
        style={{
          borderRadius: 8,
          border: `1px solid color-mix(in srgb, ${c} 35%, transparent)`,
          background: `color-mix(in srgb, ${c} 8%, transparent)`,
          padding: '9px 11px',
          opacity: p,
          transform: `translateY(${(1 - easeOut(p)) * 10}px)`,
        }}
      >
        {seg.label && <div style={{ fontSize: 9.5, letterSpacing: '0.08em', color: c, marginBottom: 5, fontWeight: 700 }}>{seg.label}</div>}
        <div style={{ fontFamily: FONT, fontSize: 12, color: TEXT, lineHeight: 1.45, marginBottom: seg.actions?.length ? 9 : 0 }}>{seg.text}</div>
        {seg.actions?.length ? (
          <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8 }}>
            {seg.actions.map((a, i) => (
              <DemoButton key={i} a={a} />
            ))}
          </div>
        ) : null}
      </div>
    );
  }

  // actions
  const p = ramp(t, start, start + TL.actionsDur);
  if (p === 0) return null;
  return (
    <div style={{ display: 'flex', flexWrap: 'wrap', gap: 8, opacity: p, transform: `translateY(${(1 - easeOut(p)) * 8}px)` }}>
      {seg.actions.map((a, i) => (
        <DemoButton key={i} a={a} />
      ))}
    </div>
  );
}
