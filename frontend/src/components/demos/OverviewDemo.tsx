/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// Companion to the "Overview" video script.
import ChatDemoCard, { type DemoMeta } from './_engine/ChatDemoCard';

export const meta: DemoMeta = { title: 'Overview', category: 'Overview', order: 1 };

export default function OverviewDemo({ playing }: { playing?: boolean }) {
  return (
    <ChatDemoCard
      playing={playing}
      title="LeastAction"
      chip="Getting Started"
      question="What is LeastAction?"
      segments={[
        {
          kind: 'text',
          text:
            'An **AI-powered orchestration platform.** The AI generates the operator, deploys it, runs it, reads the logs, queries the data, fixes itself, and reruns — the **full loop.**',
        },
        {
          kind: 'list',
          items: [
            { status: 'info', text: 'One catalog: operators, connections, payloads, tasks, reports' },
            { status: 'info', text: 'Orchestrate from the UI — no Python required' },
            { status: 'info', text: 'Works on your stack — Postgres, BigQuery, S3, dbt, Airflow' },
            { status: 'info', text: 'Self-hosted — no migration' },
          ],
        },
        {
          kind: 'actions',
          actions: [
            { label: 'Build my first pipeline', variant: 'primary' },
            { label: 'Browse the marketplace', variant: 'secondary' },
          ],
        },
      ]}
    />
  );
}
