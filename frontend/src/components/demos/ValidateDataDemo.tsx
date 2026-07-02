/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// Companion to the "Validate data in 1 prompt" video script.
import ChatDemoCard, { type DemoMeta } from './_engine/ChatDemoCard';

export const meta: DemoMeta = { title: 'Validate data in 1 prompt', category: 'Operate', order: 1 };

export default function ValidateDataDemo({ playing }: { playing?: boolean }) {
  return (
    <ChatDemoCard
      playing={playing}
      title="Data Inspector"
      chip="Sales Data Inspector"
      tools="inspect_data"
      question="Did last night’s sales load land correctly?"
      segments={[
        {
          kind: 'text',
          text: 'Checked **reports.daily_sales** for 2026-06-17 — the load **completed,** but I found an **issue.**',
        },
        {
          kind: 'list',
          items: [
            { status: 'ok', text: '48,210 rows loaded' },
            { status: 'ok', text: 'No nulls in the revenue column' },
            { status: 'warn', text: '3 duplicate order_ids in today’s partition' },
          ],
        },
        {
          kind: 'callout',
          tone: 'warn',
          label: 'SELF-FIX — SUGGESTED',
          text: 'Re-run the dedupe step in load_sales and reload 2026-06-17.',
          actions: [{ label: 'Approve & rerun', variant: 'primary' }, { label: 'Dismiss', variant: 'secondary' }],
        },
      ]}
    />
  );
}
