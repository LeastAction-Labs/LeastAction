/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// Companion to the "Build a pipeline from a data contract in 1 prompt" video script.
import ChatDemoCard, { type DemoMeta } from './_engine/ChatDemoCard';

export const meta: DemoMeta = { title: 'Build from a data contract', category: 'Build', order: 1 };

export default function BuildFromContractDemo({ playing }: { playing?: boolean }) {
  return (
    <ChatDemoCard
      playing={playing}
      title="AI Builder"
      chip="Data Contract"
      tools="create_catalog_item, run_task, inspect_data"
      question="Build a pipeline from this contract: orders → reports.daily_orders, daily at 2am"
      segments={[
        { kind: 'text', text: 'Generated a working pipeline from your contract:' },
        {
          kind: 'list',
          items: [
            { status: 'ok', text: 'Operator PostgresqlExecuteSQL created' },
            { status: 'ok', text: 'Connection sample + payload generated' },
            { status: 'ok', text: 'Task daily_orders scheduled', detail: '0 2 * * *' },
            { status: 'ok', text: 'First run → reports.daily_orders', detail: '48,210 rows' },
            { status: 'ok', text: 'Validated against contract — schema + counts match' },
          ],
        },
        {
          kind: 'callout',
          label: 'READY',
          text: 'Saved to your catalog as a versioned, shareable item. No provider packages, no per-worker deploy.',
          actions: [
            { label: 'Open the task', variant: 'primary' },
            { label: 'Publish to marketplace', variant: 'secondary' },
          ],
        },
      ]}
    />
  );
}
