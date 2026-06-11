/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */

export interface TourStep {
  id: string;
  title: string;
  description: string;
  navigateToFolderType?: string;
  navigateFilterType?: string;
  navigateToRoute?: { to: string; search?: Record<string, string> };
  highlightTarget?: string;
  autoClick?: boolean;
  autoClickDelay?: number; // ms to wait before auto-clicking (default 500)
  externalUrl?: string; // renders a "Download" / "Open" button
  internalUrl?: string; // renders an "Open page" button that navigates internally
  docLaui?: string; // renders "Open guide" CTA that navigates to doc
  docItemName?: string; // display name passed as itemname param
  suggestedItemType?: string; // direct API lookup by name → navigate to item
  suggestedItemName?: string;
  suggestedFilterType?: string; // filtertype passed when navigating to a suggested folder
  chatbotPrefill?: { chatName: string; connectionName: string };
  copyableBlock?: string; // renders a monospace copyable block
  taskPrefill?: {
    namePrefix: string; // name will be `namePrefix_XXXX` with a random 4-digit suffix
    operatorName: string; // looked up by name to resolve operator_laui
    connectionName: string; // looked up by name to resolve connection_laui
    payload: string; // SQL / payload content to pre-fill
  };
  submitOnNext?: boolean; // clicking Next clicks [data-tour-target="task-modal-submit"] instead of advancing
  refreshWorkflowOnFinish?: boolean; // on Finish, re-navigate to the workflow folder before closing the tour
}

export interface TourConfig {
  id: string;
  title: string;
  steps: TourStep[];
}

export const LANDING_SUBTITLE =
  'Orchestrate data pipelines without DAG files or YAML. Everything lives in a catalog — operators, connections, tasks, reports. AI generates code, deploys use cases, and answers questions about live pipeline state.';

export interface DocLink {
  laui: string;
  itemName: string;
  label: string;
  description: string;
  quickLink?: string;
  quickLinkLabel?: string;
  quickLinkAction?: 'navigate' | 'open-chat' | 'external';
  quickLinkFilter?: string;
  quickLink2?: string;
  quickLinkLabel2?: string;
  quickLinkAction2?: 'navigate' | 'open-chat' | 'external';
}

export interface AiCard {
  tourId: string;
  title: string;
  description: string;
}

export interface TaskOption {
  tourId: string;
  label: string;
  description: string;
}

export const DOC_LINKS: DocLink[] = [
  {
    laui: 'getting-started-task_intro',
    itemName: 'Task Intro',
    label: 'Tasks & Workflows',
    description: 'Connection + Operator + Payload = Task. Schedules, dependencies, partitions.',
    quickLink: 'folder.workflow',
    quickLinkLabel: 'Open Workflow Folder',
    quickLinkAction: 'navigate',
    quickLinkFilter: 'task',
  },
  {
    laui: 'getting-started-AI_tech_intro',
    itemName: 'AI Tech Intro',
    label: 'AI Integration',
    description: 'Three AI modes: built-in generator, Claude Code + MCP, server-side chat.',
    quickLinkLabel: 'Open Built-in Chat',
    quickLinkAction: 'open-chat',
    quickLink2: '/mcp-token',
    quickLinkLabel2: 'MCP Token',
    quickLinkAction2: 'navigate',
  },
  {
    laui: 'getting-started-marketplace_intro',
    itemName: 'Marketplace Intro',
    label: 'Marketplace',
    description: 'Import pre-built operators, use cases, actions, and skills in one click.',
    quickLink: '/marketplace',
    quickLinkLabel: 'Open Marketplace',
    quickLinkAction: 'navigate',
  },
  {
    laui: 'getting-started-advanced-AI_managment-app',
    itemName: 'AI App',
    label: 'AI App Guide',
    description: 'Full Claude Code + MCP setup, tool reference, and skills.',
    quickLink: 'https://github.com/LeastAction-Labs/LeastAction-App',
    quickLinkLabel: 'View on GitHub',
    quickLinkAction: 'external',
  },
];

export const AI_CARDS: AiCard[] = [
  {
    tourId: 'ai-chat',
    title: 'Native AI Agent',
    description:
      'Chat widget built into the UI. Run tasks, debug failures, and generate operators — uses your API key via a catalog connection.',
  },
  {
    tourId: 'claude-code',
    title: 'Claude Code + MCP',
    description:
      'Claude Code locally with direct catalog access. Search, run, deploy, and debug pipelines — uses your own Claude subscription.',
  },
];

export const TASK_OPTIONS: TaskOption[] = [
  {
    tourId: 'first-task-postgres',
    label: 'Postgres',
    description: 'SQL reporting with a PostgreSQL database',
  },
  {
    tourId: 'first-task-aws',
    label: 'AWS / Athena',
    description: 'Query S3 data with Athena — IAM or keys',
  },
  {
    tourId: 'create-first-task',
    label: 'Manual',
    description: 'Build any task from scratch end-to-end',
  },
  // add more below — each becomes a row in the scrollable list
  // { tourId: 'first-task-gcp',     label: 'GCP / BigQuery', description: '...' },
  // { tourId: 'first-task-azure',   label: 'Azure',          description: '...' },
  // { tourId: 'first-task-snowflake',label: 'Snowflake',     description: '...' },
  // { tourId: 'first-task-dbt',     label: 'dbt',            description: '...' },
];

export const TOURS: Record<string, TourConfig> = {
  'create-first-task': {
    id: 'create-first-task',
    title: 'Build a Task Manually',
    steps: [
      {
        id: 'welcome',
        title: 'End-to-End Task Setup',
        description:
          "Every task follows one formula: Connection + Operator + Payload = Task. We'll create a connection with your credentials, browse the pre-built operators, then wire everything into a task inside a workflow.",
      },
      {
        id: 'go-connections',
        title: 'Step 1: Browse Connections',
        description:
          'Opening the AWS connection folder. Connections hold credentials for external systems — API keys, IAM roles, database URLs. Browse the pre-created AWS connections or click "Add connection" to create your own.',
        suggestedItemType: 'folder.connection',
        suggestedItemName: 'AWS',
        suggestedFilterType: 'connection',
      },
      {
        id: 'create-connection',
        title: 'Add a Connection',
        description:
          'Click "Add connection", choose a subtype matching your system (e.g. AWSIAMRole, postgresql), give it a name, fill in the credentials, and save.',
        highlightTarget: 'create-item-button',
      },
      {
        id: 'go-operators',
        title: 'Step 2: Browse Operators',
        description:
          'Opening the AWS Lambda operator folder. Operators define how a task runs — invoke a Lambda, run SQL, process a file. Pick the operator that matches your use case.',
        suggestedItemType: 'folder.operator',
        suggestedItemName: 'Lambda',
        suggestedFilterType: 'operator',
      },
      {
        id: 'go-workflows',
        title: 'Step 3: Open a Workflow',
        description:
          'Navigating to your Workflows folder. Tasks live inside workflows — open one (or create a new workflow), then add your task inside it.',
        navigateToFolderType: 'folder.workflow',
        navigateFilterType: 'task',
      },
      {
        id: 'create-task',
        title: 'Create the Task',
        description:
          'The task form is opening. Select the operator you picked and the connection you created, give the task a name, then save. You can run it immediately or set a schedule.',
        highlightTarget: 'create-item-button',
        autoClick: true,
      },
      {
        id: 'done',
        title: 'Task Created',
        description:
          'Your task is live. Open it to run on demand, set a cron schedule, add payload parameters, or chain it to other tasks via dependencies.',
      },
    ],
  },

  docs: {
    id: 'docs',
    title: 'Explore Documentation',
    steps: [
      {
        id: 'welcome',
        title: 'Documentation',
        description:
          'LeastAction organises everything in a folder-based catalog: operators (how), connections (where), payloads (what), configs (rules), and tasks (instances). Use the guides below — the tour stays open so you can keep navigating after reading.',
      },
      {
        id: 'tasks',
        title: 'Tasks & Workflows',
        description: 'Learn how to create tasks, configure operators, and build workflows.',
        docLaui: 'getting-started-task_intro',
        docItemName: 'Task Intro',
      },
      {
        id: 'ai',
        title: 'AI Integration',
        description: 'Set up AI chats/Agents, connections, and skills for AI-powered workflows.',
        docLaui: 'getting-started-AI_tech_intro',
        docItemName: 'AI Tech Intro',
      },
      {
        id: 'marketplace',
        title: 'Marketplace',
        description: 'Browse and import pre-built use cases, operators, and actions.',
        docLaui: 'getting-started-marketplace_intro',
        docItemName: 'Marketplace Intro',
      },
      {
        id: 'mcp',
        title: 'MCP & Claude Code',
        description: 'Wire Claude Code or claude.ai to LeastAction using the MCP server.',
        docLaui: 'getting-started-advanced-AI_managment-app',
        docItemName: 'AI App',
      },
    ],
  },

  'ai-chat': {
    id: 'ai-chat',
    title: 'Native AI Agent Setup',
    steps: [
      {
        id: 'intro',
        title: 'AI Agent Overview',
        description:
          'LeastAction has a built-in chat widget that talks directly to your catalog. Ask it to run tasks, debug failures, or generate operators. You need two things already set up: an AI Agent item (which model to use) and a Connection (your API key). Both are pre-created — you just need to fill in your credentials.',
      },
      {
        id: 'find-chat',
        title: 'Open(Explore) Your AI Agent agent item',
        description:
          'Your AI folder has a pre-created "AnthropicAgent" chat agent item. Click below to open it and explore its code.',
        navigateToFolderType: 'folder.ai',
        navigateFilterType: 'agent',
        suggestedItemType: 'agent',
        suggestedItemName: 'AnthropicAgent',
      },
      {
        id: 'find-connection',
        title: 'Open(Update) Your Connection',
        description:
          'A pre-created "ClaudeApi" connection holds your Anthropic credentials. Click below to open it and fill in your API key.',
        navigateToFolderType: 'folder.connection',
        navigateFilterType: 'connection',
        suggestedItemType: 'connection.anthropic',
        suggestedItemName: 'ClaudeApi',
      },
      {
        id: 'open-chatbot',
        title: 'Open the Chat Widget',
        description:
          'The chat widget is opening with your AI Agent and connection pre-selected. Hit Start Chat to begin.',
        highlightTarget: 'chatbot-fab',
        autoClick: true,
        chatbotPrefill: { chatName: 'AnthropicAgent', connectionName: 'ClaudeApi' },
      },
      {
        id: 'view-report',
        title: 'View a Sample Report',
        description:
          'This is a pre-generated regional sales report — the kind your pipelines will produce. Browse the HTML, then ask the chat widget: "Summarise this regional report" or "Which region has the highest YoY growth?"',
        suggestedItemType: 'html_report',
        suggestedItemName: 'regional_summary',
      },
      {
        id: 'view-workflows',
        title: 'Explore Workflows',
        description:
          'These are the tasks that generate reports like the one you just saw. Ask the chat: "What tasks ran today?", "Show me any errors in the last run", or "Run the daily_revenue task now."',
        navigateToFolderType: 'folder.workflow',
        navigateFilterType: 'task',
      },
      {
        id: 'done',
        title: 'Chat is Ready',
        description:
          'Your AI Agent is configured. Use the widget any time — it remembers your provider and connection selections.',
      },
    ],
  },

  'claude-code': {
    id: 'claude-code',
    title: 'Claude Code + MCP Setup',
    steps: [
      {
        id: 'intro',
        title: 'Claude Code + MCP',
        description:
          'The LeastAction AI App is a Claude Code electron app (or CLI) with MCP tools wired directly to your catalog. It runs locally using your own Claude subscription — no server-side AI costs. You can search, run tasks, generate operators end-to-end, debug failures from logs, and deploy use cases — all by describing what you want in natural language.',
      },
      {
        id: 'download-config',
        title: 'Get Your MCP Config',
        description:
          'Your MCP config page shows your personal server URL and access token. Copy the config, place it in your project root or Claude Code config directory.',
        internalUrl: '/mcp-token',
      },
      {
        id: 'setup-guide',
        title: 'Setup Guide',
        description:
          'Follow the full setup guide to point Claude Code at the LeastAction MCP server and verify the connection.',
        docLaui: 'getting-started-advanced-AI_managment-mcp',
      },
      {
        id: 'view-report',
        title: 'View a Sample Report',
        description:
          'This regional sales report was generated by a pipeline task and stored directly in the catalog. Once Claude Code is connected, try: "Show me the regional_summary report" or "Which region has the highest YoY growth?" — Claude will read it live from your catalog.',
        suggestedItemType: 'html_report',
        suggestedItemName: 'regional_summary',
      },
      {
        id: 'view-workflows',
        title: 'Explore Workflows',
        description:
          'These are the tasks that generate and store reports like the one above. With MCP connected, ask Claude Code: "List all tasks in my workflow", "Show recent task errors", or "Run the daily_revenue task and wait for the result."',
        navigateToFolderType: 'folder.workflow',
        navigateFilterType: 'task',
      },
    ],
  },

  'first-task-postgres': {
    id: 'first-task-postgres',
    title: 'First Task — Postgres',
    steps: [
      {
        id: 'intro',
        title: 'Postgres Reporting Setup',
        description:
          "Every task follows one formula: Connection + Operator + Payload = Task. A Postgres connection and a SQL operator are already in your catalog. We'll fill in your database credentials, then import a pre-built reporting use case from the marketplace — tasks included.",
      },
      {
        id: 'open-connection',
        title: 'Fill in Your Postgres Credentials',
        description:
          'A "PostgresqlPlusClaude" connection is already in your catalog. Open it and fill in: host, port, user, password, and database name.',
        navigateToFolderType: 'folder.connection',
        navigateFilterType: 'connection',
        suggestedItemType: 'connection.postgresql',
        suggestedItemName: 'PostgresqlPlusClaude',
      },
      {
        id: 'create-task',
        title: 'Create Your First Task',
        description:
          'Opening your Workflows folder and pre-filling the task form — name, operator, connection, and SQL are already set. Hit Next to create it.',
        navigateToFolderType: 'folder.workflow',
        navigateFilterType: 'task',
        submitOnNext: true,
        taskPrefill: {
          namePrefix: 'your_first_postgres_task',
          operatorName: 'PostgresqlExecuteSQL',
          connectionName: 'PostgresqlPlusClaude',
          payload: `CREATE TABLE IF NOT EXISTS people (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100),
    age INT,
    logical_date DATE
);`,
        },
      },
      {
        id: 'done',
        title: 'Task Created',
        description:
          'Your task is live. Open it to run on demand, set a cron schedule, or chain it to other tasks via dependencies.',
        refreshWorkflowOnFinish: true,
      },
    ],
  },

  'first-task-aws': {
    id: 'first-task-aws',
    title: 'First Task — AWS',
    steps: [
      {
        id: 'intro',
        title: 'AWS Setup',
        description:
          "Every task follows one formula: Connection + Operator + Payload = Task. An AWS connection and an Athena operator are already in your catalog. If you're running on EC2, the IAM instance role is picked up automatically — no access keys needed. We'll configure the connection, then create your first Athena task.",
      },
      {
        id: 'open-connection',
        title: 'Configure Your AWS Connection',
        description:
          'An "AWSExecute" connection is pre-created in your catalog. On EC2: leave keys blank — the instance IAM role is used automatically. Locally: fill in access key ID and secret.',
        navigateToFolderType: 'folder.connection',
        navigateFilterType: 'connection',
        suggestedItemType: 'connection.AWS',
        suggestedItemName: 'AWSExecute',
      },
      {
        id: 'create-task',
        title: 'Create Your First Task',
        description:
          'Opening your Workflows folder and pre-filling the task form — name, operator, connection, and SQL are already set. Hit Next to create it.',
        navigateToFolderType: 'folder.workflow',
        navigateFilterType: 'task',
        submitOnNext: true,
        taskPrefill: {
          namePrefix: 'your_first_aws_task',
          operatorName: 'AWSAthenaExecuteSQL',
          connectionName: 'AWSExecute',
          payload: `SELECT current_date AS logical_date, 'hello from Athena' AS message`,
        },
      },
      {
        id: 'done',
        title: 'Task Created',
        description:
          'Your task is live. Open it to run on demand, set a cron schedule, or chain it to other tasks via dependencies.',
        refreshWorkflowOnFinish: true,
      },
    ],
  },
};
