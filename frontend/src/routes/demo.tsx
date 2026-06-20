/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// Demo gallery. Every *.tsx in components/demos/ that exports `default` + `meta`
// is auto-discovered here — drop a new demo file in and it shows up in the rail.
import { useMemo, useState } from 'react';

import { createFileRoute } from '@tanstack/react-router';

import type { DemoMeta } from '@/components/demos/_engine/ChatDemoCard';

export const Route = createFileRoute('/demo')({ component: DemoGallery });

type DemoModule = { default: React.ComponentType<{ playing?: boolean }>; meta?: DemoMeta };
type DemoEntry = {
  id: string;
  title: string;
  category: string;
  order: number;
  Component: React.ComponentType<{ playing?: boolean }>;
};

// Eagerly import every demo card (non-recursive — the _engine/ subfolder is skipped).
const modules = import.meta.glob<DemoModule>('../components/demos/*.tsx', { eager: true });

const ENTRIES: DemoEntry[] = Object.entries(modules)
  .map(([path, mod]) => {
    if (!mod?.default || !mod.meta) return null;
    const id = path.split('/').pop()!.replace(/\.tsx$/, '');
    return {
      id,
      title: mod.meta.title,
      category: mod.meta.category ?? 'Demos',
      order: mod.meta.order ?? 0,
      Component: mod.default,
    };
  })
  .filter((e): e is DemoEntry => e !== null)
  .sort(
    (a, b) =>
      a.category.localeCompare(b.category) || a.order - b.order || a.title.localeCompare(b.title),
  );

function DemoGallery() {
  const [selected, setSelected] = useState<string>(ENTRIES[0]?.id ?? '');
  const [query, setQuery] = useState('');

  const groups = useMemo(() => {
    const q = query.trim().toLowerCase();
    const filtered = q
      ? ENTRIES.filter((e) => e.title.toLowerCase().includes(q) || e.category.toLowerCase().includes(q))
      : ENTRIES;
    const map = new Map<string, DemoEntry[]>();
    for (const e of filtered) {
      if (!map.has(e.category)) map.set(e.category, []);
      map.get(e.category)!.push(e);
    }
    return [...map.entries()];
  }, [query]);

  const active = ENTRIES.find((e) => e.id === selected) ?? ENTRIES[0];

  return (
    <div style={{ display: 'flex', height: '100vh', background: 'var(--bg-primary)', color: 'var(--text-primary)' }}>
      {/* left rail */}
      <div
        style={{
          width: 248,
          flexShrink: 0,
          borderRight: '1px solid var(--border)',
          display: 'flex',
          flexDirection: 'column',
          background: 'var(--bg-secondary)',
        }}
      >
        <div style={{ padding: '14px 14px 10px', borderBottom: '1px solid var(--border)' }}>
          <div style={{ fontSize: 13, fontWeight: 700, marginBottom: 2 }}>Demo gallery</div>
          <div style={{ fontSize: 11, color: 'var(--text-secondary)' }}>{ENTRIES.length} examples</div>
          <input
            value={query}
            onChange={(e) => setQuery(e.target.value)}
            placeholder="Search demos…"
            style={{
              marginTop: 10,
              width: '100%',
              boxSizing: 'border-box',
              padding: '6px 9px',
              fontSize: 12,
              borderRadius: 6,
              border: '1px solid var(--border)',
              background: 'var(--bg-primary)',
              color: 'var(--text-primary)',
              outline: 'none',
            }}
          />
        </div>

        <div style={{ flex: 1, overflowY: 'auto', padding: '8px 0' }}>
          {groups.map(([category, items]) => (
            <div key={category} style={{ marginBottom: 10 }}>
              <div
                style={{
                  padding: '4px 14px',
                  fontSize: 10,
                  letterSpacing: '0.08em',
                  textTransform: 'uppercase',
                  color: 'var(--text-secondary)',
                  fontWeight: 700,
                }}
              >
                {category}
              </div>
              {items.map((e) => {
                const on = e.id === active?.id;
                return (
                  <button
                    key={e.id}
                    onClick={() => setSelected(e.id)}
                    style={{
                      display: 'block',
                      width: '100%',
                      textAlign: 'left',
                      padding: '7px 14px',
                      fontSize: 12.5,
                      cursor: 'pointer',
                      border: 'none',
                      borderLeft: `2px solid ${on ? 'var(--accent)' : 'transparent'}`,
                      background: on ? 'color-mix(in srgb, var(--accent) 12%, transparent)' : 'transparent',
                      color: on ? 'var(--accent)' : 'var(--text-primary)',
                      fontWeight: on ? 600 : 400,
                    }}
                  >
                    {e.title}
                  </button>
                );
              })}
            </div>
          ))}
          {groups.length === 0 && (
            <div style={{ padding: '14px', fontSize: 12, color: 'var(--text-secondary)' }}>No matching demos</div>
          )}
        </div>
      </div>

      {/* stage */}
      <div
        style={{
          flex: 1,
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'center',
          padding: 40,
          background: 'radial-gradient(120% 120% at 50% 0%, color-mix(in srgb, var(--accent) 6%, var(--bg-primary)) 0%, var(--bg-primary) 60%)',
          overflow: 'auto',
        }}
      >
        {active && <active.Component key={active.id} />}
      </div>
    </div>
  );
}
