/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// Companion to the "Backfill in 1 prompt" video script.
import ChatDemoCard, { type DemoMeta } from './_engine/ChatDemoCard';

export const meta: DemoMeta = { title: 'Backfill in 1 prompt', category: 'Operate', order: 2 };

export default function BackfillDemo({ playing }: { playing?: boolean }) {
  return (
    <ChatDemoCard
      playing={playing}
      title="Scheduler"
      chip="Backfill"
      tools="run_task"
      question="Backfill daily_sales for the last 110 days"
      segments={[
        {
          kind: 'text',
          text:
            'Catching up **reports.daily_sales** — replaying **110 missed daily runs in order.** Each slot advances as the previous one succeeds.',
        },
        {
          kind: 'list',
          items: [
            { status: 'ok', text: '2026-03-01', detail: '47,980 rows' },
            { status: 'ok', text: '2026-03-02', detail: '48,120 rows' },
            { status: 'pending', text: '2026-03-03 — running…' },
            { status: 'info', text: '107 more to replay, one slot at a time' },
          ],
        },
        {
          kind: 'text',
          text:
            '**Done** — 110 / 110 days replayed in sequence. Parallelism across **partitions and other tasks** is bounded by the connection’s max_parallelism.',
        },
      ]}
    />
  );
}
