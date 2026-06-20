/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// Companion to the "Monitor in 1 prompt" video script.
import ChatDemoCard, { type DemoMeta } from './_engine/ChatDemoCard';

export const meta: DemoMeta = { title: 'Monitor in 1 prompt', category: 'Operate', order: 3 };

export default function MonitorDemo({ playing }: { playing?: boolean }) {
  return (
    <ChatDemoCard
      playing={playing}
      title="Monitoring"
      chip="Pipeline Health"
      tools="get_task_history"
      question="What failed last night?"
      segments={[
        { kind: 'text', text: 'Checked last night’s runs across **3 workflows.** One task failed:' },
        {
          kind: 'list',
          items: [
            { status: 'error', text: 'load_sales — failed 02:14 (timeout after 30m)' },
            { status: 'ok', text: 'transform_sales — succeeded' },
            { status: 'ok', text: 'export_reports — succeeded' },
            { status: 'warn', text: 'validate_sales — skipped (parent failed)' },
          ],
        },
        {
          kind: 'callout',
          label: 'SUGGESTED',
          text: 'Re-run load_sales for 2026-06-19? validate_sales will follow automatically.',
          actions: [
            { label: 'Approve & rerun', variant: 'primary' },
            { label: 'Show logs', variant: 'secondary' },
            { label: 'Dismiss', variant: 'secondary' },
          ],
        },
      ]}
    />
  );
}
