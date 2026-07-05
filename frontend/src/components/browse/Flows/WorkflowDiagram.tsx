/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
/**
 * WorkflowDiagram.tsx
 *
 * A self-contained ReactFlow workflow-diagram component with a built-in
 * auto-layout engine.  Drop it into any project that already has
 * `react-flow-renderer` (v11) and `@mui/material` installed.
 *
 * ─────────────────────────────────────────────────────────────────────
 *  PUBLIC API
 * ─────────────────────────────────────────────────────────────────────
 *
 *  import WorkflowDiagram, {
 *    NodeData,           // shape of every node's payload
 *    WorkflowInput,      // { items, connections } you pass to the component
 *    SAMPLE_WORKFLOW,    // original 6-node sales pipeline
 *    SAMPLE_LARGE,       // 50-node sample: ML Pipeline (20) + E-Commerce (30)
 *  } from './WorkflowDiagram';
 *
 *  <WorkflowDiagram items={...} connections={...} />
 *
 * ─────────────────────────────────────────────────────────────────────
 */
import React, { useCallback, useMemo, useState } from 'react';

import AddIcon from '@mui/icons-material/Add';
import { Box, IconButton, Typography } from '@mui/material';
import type { Connection, Edge, Node } from 'reactflow';
import ReactFlow, {
  Background,
  Controls,
  Handle,
  MarkerType,
  Position,
  addEdge,
  useEdgesState,
  useNodesState,
} from 'reactflow';
import 'reactflow/dist/style.css';

import RunTaskModal from '@/components/modals/RunTaskModal';
import {
  TaskModalMode,
  TaskModalScopeType,
  useTaskModalContext,
} from '@/contexts/TaskModalContext';
import { useTimeFormat } from '@/contexts/TimeFormatContext';
import { formatDateTimeCompact } from '@/utils/timeFormat';

// ═══════════════════════════════════════════════════════════════════════
// 1.  PUBLIC TYPES
// ═══════════════════════════════════════════════════════════════════════

export type NodeStatus =
  | 'created'
  | 'scheduled'
  | 'queued'
  | 'queued_for_connection'
  | 'queued_in_redis'
  | 'running'
  | 'success'
  | 'error'
  | 'timeout'
  | 'cancelled'
  | 'fail';

export interface ActionItem {
  state: string;
  action: string;
  name: string;
  last_run_date: string;
  status?: string; // from task.actions_status keyed by action name
}

export interface ActionGroups {
  create_actions: ActionItem[];
  pre_actions: ActionItem[];
  running_actions: ActionItem[];
  post_actions: ActionItem[];
}

export interface NodeData {
  name: string;
  operator: string;
  status: NodeStatus;
  partition?: string; // used for grouping into partition lanes
  icon?: React.ReactNode; // optional SVG / emoji
  logical_date?: { value: string };
  last_run_date?: { value: string };
  sql?: string; // "View Payload" content
  connection?: string;
  actions?: ActionGroups;
  onAddTask?: () => void; // callback to open create task modal
}

/**
 * Raw task item from the API (array format)
 */
export interface TaskItem {
  laui: string;
  item_type: string;
  name: string;
  partition?: string | null; // e.g. "ALL" or "2026-03-05" — used for unique edge resolution
  logical_date?: string | null;
  last_run_date?: string | null;
  state: string;
  duration?: number;
  retry_number?: number;
  priority?: number;
  supported_types?: string[];
  permission?: string;
  actions?: {
    create_actions?: Array<{
      name?: string;
      state: string;
      action: string;
      last_run_date?: string;
      action_variables?: Record<string, any>;
    }>;
    pre_actions?: Array<{
      name?: string;
      state: string;
      action: string;
      last_run_date?: string;
      action_variables?: Record<string, any>;
    }>;
    running_actions?: Array<{
      name?: string;
      state: string;
      action: string;
      last_run_date?: string;
      action_variables?: Record<string, any>;
    }>;
    post_actions?: Array<{
      name?: string;
      state: string;
      action: string;
      last_run_date?: string;
      action_variables?: Record<string, any>;
    }>;
  };
  actions_status?: Record<string, Array<{ name: string; status: string }>>; // section → [{name, status}]
}

/**
 * The two things you hand the component.
 *   items       – keyed by node id, every node's data
 *   connections – adjacency list: parent id → child ids
 *
 * NOTE: the field is called `connections` (not `edges`) on purpose —
 * `edges` collides with ReactFlow's own internal prop name and can be
 * silently swallowed by wrappers / routers.
 */
export interface WorkflowInput {
  items: Record<string, NodeData>;
  connections: Record<string, string[]>;
}

// ═══════════════════════════════════════════════════════════════════════
// 2.  DATA TRANSFORMATION UTILITIES
// ═══════════════════════════════════════════════════════════════════════

/**
 * Minimal task shape needed to derive dependency edges. Shared by the graph and
 * the Tasks list so both agree on how tasks are wired. `TaskItem` and the
 * catalog list item both satisfy this structurally.
 */
export interface DependencyTask {
  laui: string;
  name: string;
  partition?: string | null;
  actions?: {
    pre_actions?: Array<{
      name?: string;
      action?: string;
      action_variables?: { parents?: Array<{ task_name?: string; partition?: string | null }> };
    }>;
  };
}

/**
 * Builds the parent → child adjacency list for a set of tasks from their
 * `LeastActionCheckIfParentsAreDone` pre-actions. Node id = "name__partition".
 */
export function extractTaskConnections(tasks: DependencyTask[]): Record<string, string[]> {
  const connections: Record<string, string[]> = {};
  tasks.forEach((task) => {
    const nodeId = `${task.name}__${task.partition}`;
    task.actions?.pre_actions?.forEach((action) => {
      const actionName = action.name || action.action;
      if (actionName !== 'LeastActionCheckIfParentsAreDone') return;
      const parents = action.action_variables?.parents;
      if (!Array.isArray(parents)) return;
      parents.forEach((parentObj) => {
        if (!parentObj.task_name) return;
        // Parent and child share the same partition — use the child task's partition.
        const parentId = `${parentObj.task_name}__${task.partition}`;
        if (!connections[parentId]) connections[parentId] = [];
        if (!connections[parentId].includes(nodeId)) {
          connections[parentId].push(nodeId);
        }
      });
    });
  });
  return connections;
}

/**
 * Transforms an array of TaskItem objects into WorkflowInput format.
 * Extracts parent-child relationships from pre_actions with LeastActionCheckIfParentsAreDone.
 */
export function transformTaskArrayToWorkflowInput(tasks: TaskItem[]): WorkflowInput {
  const items: Record<string, NodeData> = {};

  // Node ID = "name__partition" — unique, readable, matches edge references directly.

  // Build a per-section lookup: section key → Map<name, status>
  const makeStatusLookup = (
    actionsStatus?: Record<string, Array<{ name: string; status: string }>>,
    sectionKey?: string,
  ): Map<string, string> => {
    const entries = actionsStatus?.[sectionKey ?? ''] ?? [];
    return new Map(entries.map((e) => [e.name, e.status]));
  };

  const makeMapAction =
    (statusLookup: Map<string, string>) =>
    (a: { name?: string; state: string; action: string; last_run_date?: string }): ActionItem => {
      const actionName = a.name || a.action || 'Unknown';
      return {
        state: a.state,
        action: a.action,
        name: actionName,
        last_run_date: a.last_run_date || '',
        status: statusLookup.get(actionName),
      };
    };

  tasks.forEach((task) => {
    const nodeId = `${task.name}__${task.partition}`;

    items[nodeId] = {
      name: `${task.name} (${task.partition})`,
      partition: task.partition ?? undefined,
      operator: task.item_type || 'Unknown',
      status: task.state as NodeStatus,
      logical_date: task.logical_date ? { value: task.logical_date } : undefined,
      last_run_date: task.last_run_date ? { value: task.last_run_date } : undefined,
      actions: task.actions
        ? {
            create_actions: (task.actions.create_actions || []).map(
              makeMapAction(makeStatusLookup(task.actions_status, 'create_actions')),
            ),
            pre_actions: (task.actions.pre_actions || []).map(
              makeMapAction(makeStatusLookup(task.actions_status, 'pre_actions')),
            ),
            running_actions: (task.actions.running_actions || []).map(
              makeMapAction(makeStatusLookup(task.actions_status, 'running_actions')),
            ),
            post_actions: (task.actions.post_actions || []).map(
              makeMapAction(makeStatusLookup(task.actions_status, 'post_actions')),
            ),
          }
        : undefined,
    };
  });

  return { items, connections: extractTaskConnections(tasks) };
}

/**
 * Computes the dependency topology shared by the graph layout and the Tasks list:
 *   – connected components (undirected BFS over parent/child links)
 *   – per-node topological level (depth = max parent level + 1 within its component)
 *
 * Exposed so the Tasks list can group/order tasks exactly the way the graph wires them.
 */
export function computeTopology(
  nodeIds: string[],
  connections: Record<string, string[]>,
): {
  components: string[][];
  level: Map<string, number>;
  parents: Map<string, string[]>;
  children: Map<string, string[]>;
} {
  const edgeMap = connections;

  const allIds = new Set<string>([
    ...nodeIds,
    ...Object.keys(edgeMap),
    ...Object.values(edgeMap).flat(),
  ]);

  // ── adjacency ────────────────────────────────────────────────────
  const children = new Map<string, string[]>();
  const parents = new Map<string, string[]>();
  allIds.forEach((id) => {
    children.set(id, []);
    parents.set(id, []);
  });
  for (const [parent, kids] of Object.entries(edgeMap)) {
    for (const child of kids) {
      children.get(parent)!.push(child);
      parents.get(child)!.push(parent);
    }
  }

  // ── connected components (BFS on undirected graph) ───────────────
  const visited = new Set<string>();
  const components: string[][] = [];
  for (const id of allIds) {
    if (visited.has(id)) continue;
    const component: string[] = [];
    const queue = [id];
    visited.add(id);
    while (queue.length) {
      const cur = queue.shift()!;
      component.push(cur);
      const neighbors = [...(children.get(cur) || []), ...(parents.get(cur) || [])];
      for (const n of neighbors) {
        if (!visited.has(n)) {
          visited.add(n);
          queue.push(n);
        }
      }
    }
    components.push(component);
  }

  // ── topological level per component (level = max parent level + 1) ─
  const level = new Map<string, number>();
  for (const comp of components) {
    const inComponent = new Set(comp);
    comp.forEach((id) => level.set(id, 0));
    let changed = true;
    while (changed) {
      changed = false;
      for (const id of comp) {
        const myParents = (parents.get(id) || []).filter((p) => inComponent.has(p));
        if (myParents.length === 0) continue;
        const needed = Math.max(...myParents.map((p) => level.get(p)!)) + 1;
        if (needed !== level.get(id)) {
          level.set(id, needed);
          changed = true;
        }
      }
    }
  }

  return { components, level, parents, children };
}

/**
 * Groups tasks the same way the workflow graph wires them, for the Tasks list.
 * Connected tasks are returned adjacent and in dependency (topological) order;
 * each connected component — including a standalone task — is one group with a
 * running index, so the list can tint groups with alternating colors.
 */
export function groupTasksByDependency(tasks: DependencyTask[]): {
  orderedLauis: string[];
  groupIndexByLaui: Map<string, number>;
} {
  // nodeId ("name__partition") → laui, plus the task's original index for stable ordering
  const lauiByNodeId = new Map<string, string>();
  const orderByNodeId = new Map<string, number>();
  tasks.forEach((task, idx) => {
    const nodeId = `${task.name}__${task.partition}`;
    if (!lauiByNodeId.has(nodeId)) {
      lauiByNodeId.set(nodeId, task.laui);
      orderByNodeId.set(nodeId, idx);
    }
  });

  const nodeIds = tasks.map((task) => `${task.name}__${task.partition}`);
  const { components, level } = computeTopology(nodeIds, extractTaskConnections(tasks));

  // Order components by the earliest original index of their members (stable, predictable).
  const orderOf = (nodeId: string) => orderByNodeId.get(nodeId) ?? Number.MAX_SAFE_INTEGER;
  const sortedComponents = components
    .map((comp) => ({ comp, minOrder: Math.min(...comp.map(orderOf)) }))
    .sort((a, b) => a.minOrder - b.minOrder);

  const orderedLauis: string[] = [];
  const groupIndexByLaui = new Map<string, number>();

  sortedComponents.forEach(({ comp }, groupIndex) => {
    // Within a component: dependency order (level), then original order.
    const sorted = [...comp].sort((a, b) => {
      const lv = (level.get(a) ?? 0) - (level.get(b) ?? 0);
      return lv !== 0 ? lv : orderOf(a) - orderOf(b);
    });
    for (const nodeId of sorted) {
      const laui = lauiByNodeId.get(nodeId);
      if (!laui) continue; // edge-only node (parent referenced but not on this page)
      orderedLauis.push(laui);
      groupIndexByLaui.set(laui, groupIndex);
    }
  });

  return { orderedLauis, groupIndexByLaui };
}

// ═══════════════════════════════════════════════════════════════════════
// 3.  LAYOUT CONSTANTS
// ═══════════════════════════════════════════════════════════════════════

const COLUMN_WIDTH = 320; // card 240 + h-gap 80
const ROW_HEIGHT = 340; // card ~280 + v-gap 60
const COMPONENT_GAP_Y = 100;
const MAX_NODES = 100;
const COLLISION_ITERS = 3;

// ═══════════════════════════════════════════════════════════════════════
// 4.  AUTO-LAYOUT ENGINE  (pure functions, no side-effects)
// ═══════════════════════════════════════════════════════════════════════

/**
 * Given a WorkflowInput, returns fully-positioned ReactFlow nodes & edges.
 * Throws if > MAX_NODES or if input is invalid.
 */
export function computeLayout(input: WorkflowInput): {
  nodes: Node[];
  edges: Edge[];
} {
  const { items, connections: edgeMap } = input;

  // ── quick guards ──────────────────────────────────────────────────
  const allIds = new Set<string>([
    ...Object.keys(items || {}),
    ...Object.keys(edgeMap || {}),
    ...Object.values(edgeMap || {}).flat(),
  ]);

  if (allIds.size === 0) return { nodes: [], edges: [] };
  if (allIds.size > MAX_NODES)
    throw new Error(`Too many nodes (${allIds.size}). Max is ${MAX_NODES}.`);

  // ── Phases 1 & 2: connected components + topological levels ──────
  // Shared with the Tasks list via computeTopology so both agree on wiring.
  const { components, level, parents, children } = computeTopology(Object.keys(items), edgeMap);

  // ── Phase 3: within-component X/Y layout ─────────────────────────
  // Group nodes by component, then by level
  interface PositionMap {
    [id: string]: { x: number; y: number };
  }
  const positions: PositionMap = {};

  // We'll collect per-component bounding boxes for Phase 4
  interface CompBox {
    ids: string[];
    totalWidth: number;
    totalHeight: number;
  }
  const compBoxes: CompBox[] = [];

  const BARYCENTER_ITERS = 6;

  for (const comp of components) {
    const compSet = new Set(comp);

    // Build level buckets
    const levelBuckets = new Map<number, string[]>();
    for (const id of comp) {
      const lv = level.get(id)!;
      if (!levelBuckets.has(lv)) levelBuckets.set(lv, []);
      levelBuckets.get(lv)!.push(id);
    }

    const sortedLevels = Array.from(levelBuckets.keys()).sort((a, b) => a - b);
    const maxLevel = sortedLevels[sortedLevels.length - 1];

    // Seed: naive vertical stacking so every node has an initial Y
    for (const [lv, ids] of levelBuckets) {
      ids.forEach((id, idx) => {
        positions[id] = {
          x: lv * COLUMN_WIDTH,
          y: idx * ROW_HEIGHT,
        };
      });
    }

    // Helper: resolve collisions within a single level
    const resolveLevel = (ids: string[]) => {
      for (let iter = 0; iter < COLLISION_ITERS; iter++) {
        ids.sort((a, b) => positions[a].y - positions[b].y);
        for (let i = 1; i < ids.length; i++) {
          const overlap = positions[ids[i - 1]].y + ROW_HEIGHT - positions[ids[i]].y;
          if (overlap > 0) {
            positions[ids[i - 1]].y -= overlap / 2;
            positions[ids[i]].y += overlap / 2;
          }
        }
      }
    };

    // Barycenter relaxation: alternate top-down and bottom-up passes.
    // Top-down pulls each node toward avg-Y of its parents.
    // Bottom-up pulls each node toward avg-Y of its children.
    // Alternating converges even for diamonds and multi-parent fan-ins.
    for (let pass = 0; pass < BARYCENTER_ITERS; pass++) {
      // Top-down
      for (const lv of sortedLevels) {
        const ids = levelBuckets.get(lv)!;
        for (const id of ids) {
          const myParents = (parents.get(id) || []).filter((p) => compSet.has(p));
          if (myParents.length === 0) continue;
          positions[id].y = myParents.reduce((s, p) => s + positions[p].y, 0) / myParents.length;
        }
        resolveLevel(ids);
      }
      // Bottom-up
      for (let i = sortedLevels.length - 1; i >= 0; i--) {
        const ids = levelBuckets.get(sortedLevels[i])!;
        for (const id of ids) {
          const myChildren = (children.get(id) || []).filter((c) => compSet.has(c));
          if (myChildren.length === 0) continue;
          positions[id].y = myChildren.reduce((s, c) => s + positions[c].y, 0) / myChildren.length;
        }
        resolveLevel(ids);
      }
    }

    // Normalise: shift so min-y in this component = 0
    const ys = comp.map((id) => positions[id].y);
    const minY = Math.min(...ys);
    comp.forEach((id) => {
      positions[id].y -= minY;
    });

    const maxY = Math.max(...comp.map((id) => positions[id].y));
    compBoxes.push({
      ids: comp,
      totalWidth: (maxLevel + 1) * COLUMN_WIDTH,
      totalHeight: maxY + ROW_HEIGHT,
    });
  }

  // ── Phase 4: global component placement ──────────────────────────
  // Sort components by partition name so same-partition groups stack together top-to-bottom.
  compBoxes.sort((a, b) => {
    const partA = items[a.ids[0]]?.partition ?? '';
    const partB = items[b.ids[0]]?.partition ?? '';
    return partA.localeCompare(partB);
  });

  let globalYOffset = 0;
  for (const box of compBoxes) {
    // apply y offset to every node in this component
    for (const id of box.ids) {
      positions[id].y += globalYOffset;
    }
    globalYOffset += box.totalHeight + COMPONENT_GAP_Y;
  }

  // Centre the whole layout so fitView works nicely
  const allXs = Object.values(positions).map((p) => p.x);
  const allYs = Object.values(positions).map((p) => p.y);
  const centreX = (Math.min(...allXs) + Math.max(...allXs)) / 2;
  const centreY = (Math.min(...allYs) + Math.max(...allYs)) / 2;
  for (const id of Object.keys(positions)) {
    positions[id].x -= centreX;
    positions[id].y -= centreY;
  }

  // ── Phase 5: build partition background boxes ─────────────────────
  const BOX_PAD_X = 50;
  const BOX_PAD_TOP = 40; // extra room for the label
  const BOX_PAD_BOTTOM = 30;
  const CARD_W = 240;
  const CARD_H = 280;

  const partitionNodeIds = new Map<string, string[]>();
  for (const id of Array.from(allIds)) {
    const p = items[id]?.partition;
    if (!p) continue;
    if (!partitionNodeIds.has(p)) partitionNodeIds.set(p, []);
    partitionNodeIds.get(p)!.push(id);
  }

  const partitionBoxNodes: Node[] = Array.from(partitionNodeIds.entries()).map(
    ([partition, ids]) => {
      const xs = ids.map((id) => positions[id]?.x ?? 0);
      const ys = ids.map((id) => positions[id]?.y ?? 0);
      const x = Math.min(...xs) - BOX_PAD_X;
      const y = Math.min(...ys) - BOX_PAD_TOP;
      const w = Math.max(...xs) + CARD_W + BOX_PAD_X - x;
      const h = Math.max(...ys) + CARD_H + BOX_PAD_BOTTOM - y;
      return {
        id: `__partition_box__${partition}`,
        type: 'partitionBox',
        position: { x, y },
        data: { label: partition, width: w, height: h },
        zIndex: -1,
        draggable: false,
        selectable: false,
        focusable: false,
      };
    },
  );

  // ── Phase 5b: build task nodes ────────────────────────────────────
  const rfNodes: Node[] = [
    ...partitionBoxNodes,
    ...Array.from(allIds).map((id) => ({
      id,
      type: 'workflow',
      position: positions[id] || { x: 0, y: 0 },
      data: items[id] || {
        name: id,
        operator: 'Unknown',
        status: 'created' as NodeStatus,
      },
    })),
  ];

  // ── Phase 5c: build ReactFlow Edge[] ─────────────────────────────
  const rfEdges: Edge[] = [];
  for (const [parent, kids] of Object.entries(edgeMap)) {
    for (const child of kids) {
      const parentLevel = level.get(parent) ?? 0;
      const childLevel = level.get(child) ?? 0;
      const skips = childLevel - parentLevel;

      rfEdges.push({
        id: `e_${parent}_${child}`,
        source: parent,
        target: child,
        type: skips > 1 ? 'entityRelation' : 'smoothstep',
        style: {
          stroke: '#5B9BD5',
          strokeWidth: 3,
          ...(skips > 1 ? { strokeDasharray: '6 3' } : {}),
        },
        markerEnd: {
          type: MarkerType.ArrowClosed,
          color: '#5B9BD5',
          width: 20,
          height: 20,
        },
      });
    }
  }

  return { nodes: rfNodes, edges: rfEdges };
}

// ═══════════════════════════════════════════════════════════════════════
// 7.  WORKFLOW NODE  (custom ReactFlow node renderer)
// ═══════════════════════════════════════════════════════════════════════

// Colors from task.json projection_graph_card_config.header.enum_colors
const STATUS_COLORS: Record<string, string> = {
  created: '#94a3b8',
  scheduled: '#60a5fa',
  queued: '#a78bfa',
  queued_for_connection: '#a78bfa',
  queued_in_redis: '#c084fc',
  running: '#fbbf24',
  success: '#4ade80',
  error: '#f87171',
  timeout: '#fb923c',
  cancelled: '#64748b',
  fail: '#dc2626',
};

const STATUS_LABELS: Record<string, string> = {
  created: 'Created',
  scheduled: 'Scheduled',
  queued: 'Queued',
  queued_for_connection: 'Queued (Connection)',
  queued_in_redis: 'Queued (Redis)',
  running: 'Running',
  success: 'Success',
  error: 'Error',
  timeout: 'Timeout',
  cancelled: 'Cancelled',
  fail: 'Failed',
};

const ACTION_STYLES: Record<string, { color: string; label: string }> = {
  pre: { color: '#4ade80', label: 'preAction' },
  run: { color: '#fb923c', label: 'runningInterval' },
  sla: { color: '#60a5fa', label: 'runningSLA' },
  post: { color: '#67e8f9', label: 'postAction' },
};

const ACTION_STATUS_COLORS: Record<string, string> = {
  success: '#4ade80',
  running: '#fbbf24',
  pending: '#94a3b8',
  error: '#f87171',
};

const WorkflowNode = ({ data }: { data: NodeData }) => {
  // Check if we have any actions to display
  const hasActions =
    data.actions &&
    ((data.actions.pre_actions && data.actions.pre_actions.length > 0) ||
      (data.actions.running_actions && data.actions.running_actions.length > 0) ||
      (data.actions.post_actions && data.actions.post_actions.length > 0));

  // Check if we have date information to display
  const hasDates = data.logical_date || data.last_run_date;

  return (
    <>
      <Handle type="target" position={Position.Left} />
      <Box
        sx={{
          position: 'relative',
          width: 240,
          background: 'var(--bg-secondary)',
          borderRadius: 'var(--radius-lg)',
          border: '2px solid rgba(var(--color-border), 0.15)',
          boxShadow: '0 4px 12px rgba(0,0,0,0.15)',
          overflow: 'hidden',
          transition: 'all 0.2s',
          '&:hover': {
            boxShadow: '0 8px 24px rgba(0,0,0,0.25)',
            transform: 'translateY(-2px)',
          },
          '&:hover .add-task-button': {
            opacity: 1,
          },
        }}
      >
        {/* Add Task Button - positioned on right side, middle */}
        {data.onAddTask && (
          <IconButton
            className="add-task-button"
            onClick={(e) => {
              e.stopPropagation();
              data.onAddTask?.();
            }}
            sx={{
              position: 'absolute',
              right: 0,
              top: '50%',
              transform: 'translateY(-50%)',
              width: 24,
              height: 24,
              bgcolor: '#4ade80',
              color: '#ffffff',
              opacity: 0,
              transition: 'opacity 0.2s, background-color 0.2s',
              zIndex: 10,
              '&:hover': {
                bgcolor: '#22c55e',
              },
              boxShadow: '0 2px 8px rgba(0,0,0,0.15)',
            }}
            size="small"
          >
            <AddIcon sx={{ fontSize: 16 }} />
          </IconButton>
        )}
        {/* Header Status Bar */}
        <Box
          sx={{
            height: 24,
            background: STATUS_COLORS[data.status] || '#94a3b8',
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            px: 1,
          }}
        >
          <Typography
            sx={{
              fontSize: '9px',
              fontWeight: 700,
              color: '#fff',
              textTransform: 'uppercase',
              letterSpacing: '0.5px',
            }}
          >
            {STATUS_LABELS[data.status] || 'Unknown'}
          </Typography>
        </Box>

        {/* Body 1 */}
        <Box sx={{ p: 1.5, display: 'flex', gap: 1, alignItems: 'flex-start' }}>
          {data.icon && (
            <Box
              sx={{
                width: 36,
                height: 36,
                borderRadius: 'var(--radius-md)',
                background: 'var(--bg-tertiary)',
                display: 'flex',
                alignItems: 'center',
                justifyContent: 'center',
                flexShrink: 0,
              }}
            >
              {data.icon}
            </Box>
          )}
          <Box sx={{ flex: 1, minWidth: 0 }}>
            <Typography
              sx={{
                fontSize: '13px',
                fontWeight: 700,
                color: 'var(--text-primary)',
                lineHeight: 1.3,
                mb: 0.3,
              }}
            >
              {data.name}
            </Typography>
            <Typography
              sx={{ fontSize: '10px', color: 'var(--text-dim)', fontFamily: 'monospace' }}
            >
              {data.operator}
            </Typography>
          </Box>
        </Box>

        {/* Body 2 - Only show if we have date information */}
        {hasDates && (
          <Box sx={{ mt: 0.8, p: 1 }}>
            {data.logical_date && (
              <Typography sx={{ fontSize: '10px', color: 'var(--text-dim)', lineHeight: 1.4 }}>
                <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
                  logical_date:
                </span>{' '}
                {formatDateTimeCompact(data.logical_date.value)}
              </Typography>
            )}
            {data.last_run_date && (
              <Typography
                sx={{
                  fontSize: '10px',
                  color: 'var(--text-dim)',
                  mt: 0.5,
                  lineHeight: 1.4,
                }}
              >
                <span style={{ color: 'var(--text-secondary)', fontWeight: 600 }}>
                  last_run_date:
                </span>{' '}
                {formatDateTimeCompact(data.last_run_date.value)}
              </Typography>
            )}
          </Box>
        )}

        {/* Bottom - Only show if we have actions */}
        {hasActions && (
          <Box
            sx={{
              display: 'flex',
              flexWrap: 'wrap',
              gap: 0.5,
              p: 1,
              pt: 1.5,
              borderTop: '1px solid var(--bg-tertiary)',
            }}
          >
            {[
              ...(data.actions!.pre_actions || []).map((a) => ({
                ...a,
                type: 'pre',
              })),
              ...(data.actions!.running_actions || []).map((a) => ({
                ...a,
                type: 'run',
              })),
              ...(data.actions!.post_actions || []).map((a) => ({
                ...a,
                type: 'post',
              })),
            ].map((actionItem, idx) => {
              const style = ACTION_STYLES[actionItem.type] || ACTION_STYLES.run;
              const actStatus = actionItem.status || actionItem.state || 'pending';
              // Handle both 'action' and 'name' fields for action name
              const actionName = actionItem.action || actionItem.name || 'Unknown';

              return (
                <Box
                  key={idx}
                  sx={{
                    position: 'relative',
                    display: 'inline-flex',
                    alignItems: 'center',
                    gap: 0.4,
                    px: 0.8,
                    py: 0.3,
                    borderRadius: 'var(--radius-lg)',
                    background: `color-mix(in srgb, ${style.color} 15%, var(--bg-secondary))`,
                    border: `1px solid color-mix(in srgb, ${style.color} 35%, transparent)`,
                    fontSize: '8px',
                    fontWeight: 600,
                    color: style.color,
                    whiteSpace: 'nowrap',
                    '&:hover .status-tooltip': {
                      opacity: 1,
                      visibility: 'visible',
                    },
                  }}
                >
                  {actionName}
                  <Box
                    sx={{
                      width: 4,
                      height: 4,
                      borderRadius: '50%',
                      background: ACTION_STATUS_COLORS[actStatus],
                      ml: 0.5,
                    }}
                  />

                  {/* Tooltip */}
                  <Box
                    className="status-tooltip"
                    sx={{
                      position: 'absolute',
                      bottom: '100%',
                      left: '50%',
                      transform: 'translateX(-50%)',
                      mb: 0.5,
                      px: 1,
                      py: 0.5,
                      background: 'var(--bg-primary)',
                      color: 'var(--text-primary)',
                      border: '1px solid rgba(var(--color-border), 0.2)',
                      fontSize: '8px',
                      borderRadius: 'var(--radius-sm)',
                      whiteSpace: 'nowrap',
                      opacity: 0,
                      visibility: 'hidden',
                      transition: 'opacity 0.2s, visibility 0.2s',
                      pointerEvents: 'none',
                      zIndex: 1000,
                      '&::after': {
                        content: '""',
                        position: 'absolute',
                        top: '100%',
                        left: '50%',
                        transform: 'translateX(-50%)',
                        borderWidth: '4px',
                        borderStyle: 'solid',
                        borderColor: 'var(--bg-primary) transparent transparent transparent',
                      },
                    }}
                  >
                    <Box sx={{ fontWeight: 600, mb: 0.3 }}>{style.label}</Box>
                    <Box>Status: {actStatus}</Box>
                  </Box>
                </Box>
              );
            })}
          </Box>
        )}
      </Box>
      <Handle type="source" position={Position.Right} />
    </>
  );
};

// ── Partition lane background node ────────────────────────────────────
const PartitionBoxNode = ({ data }: { data: { label: string; width: number; height: number } }) => (
  <Box
    sx={{
      width: data.width,
      height: data.height,
      border: '2px solid rgba(var(--color-border), 0.12)',
      borderRadius: '16px',
      background: 'rgba(var(--color-card-muted), 0.4)',
      pointerEvents: 'none',
      position: 'relative',
    }}
  >
    <Typography
      sx={{
        position: 'absolute',
        top: 8,
        left: 14,
        fontSize: '10px',
        fontWeight: 700,
        color: 'var(--text-dim)',
        textTransform: 'uppercase',
        letterSpacing: '1.5px',
      }}
    >
      {data.label}
    </Typography>
  </Box>
);

const NODE_TYPES = { workflow: WorkflowNode, partitionBox: PartitionBoxNode };

// ═══════════════════════════════════════════════════════════════════════
// 8.  MAIN COMPONENT
// ═══════════════════════════════════════════════════════════════════════

interface WorkflowDiagramProps {
  /** override canvas height (default 600) */
  height?: number;
  /** Array of task items (will be auto-transformed) */
  tasks: TaskItem[];
  /** laui of the workflow being viewed — pre-filled on "add task" */
  workflowLaui?: string;
  /** Called after a task is successfully created from the diagram */
  onTaskCreated?: () => void;
}

const WorkflowDiagram: React.FC<WorkflowDiagramProps> = ({
  tasks,
  height = 600,
  workflowLaui,
  onTaskCreated,
}) => {
  // Subscribe to timezone changes so the diagram re-renders when the user toggles.
  const { timeZone } = useTimeFormat();
  // Modal state
  const [_selectedNodeId, setSelectedNodeId] = useState<string | null>(null);

  // Transform tasks array to workflow input
  const workflowInput = useMemo(() => {
    return transformTaskArrayToWorkflowInput(tasks);
  }, [tasks]);

  // Run layout once whenever workflowInput changes
  const { nodes: layoutNodes, edges: layoutEdges } = useMemo(
    () => computeLayout(workflowInput),
    [workflowInput],
  );

  const [nodes, setNodes, onNodesChange] = useNodesState(layoutNodes);
  const [edges, setEdges, onEdgesChange] = useEdgesState(layoutEdges);

  const { setTaskModalState } = useTaskModalContext();

  // Handler to open modal for a specific node
  const handleOpenModal = useCallback(
    (nodeId: string, nodeData: NodeData) => {
      // Node ID format is "taskname__partition" — extract the raw task name
      const taskName = nodeId.split('__')[0];
      const partition = nodeData.partition;

      setTaskModalState({
        isOpen: true,
        scope: {
          scopeType: TaskModalScopeType.DEFAULT,
        },
        mode: TaskModalMode.CREATE,
        onSuccess: onTaskCreated,
        initialTaskData: {
          partition,
          ...(workflowLaui ? { workflow_laui: workflowLaui } : {}),
          actions: {
            pre_actions: [
              {
                name: 'LeastActionCheckIfParentsAreDone',
                action_variables: {
                  parents: [
                    {
                      task_name: taskName,
                      project_laui: '{{project_laui}}',
                      account_laui: '{{account_laui}}',
                      partition: '{{partition}}',
                    },
                  ],
                },
              },
            ],
          },
        },
      });
      setSelectedNodeId(nodeId);
    },
    [setTaskModalState, workflowLaui, onTaskCreated],
  );

  // Handler to close modal

  // Handler for task submission

  // Re-sync when layout output changes and inject onAddTask callback.
  // `timeZone` is intentionally in the dep list so toggling UTC↔local rebuilds
  // node data objects — ReactFlow re-renders nodes only when `data` identity changes.
  React.useEffect(() => {
    const nodesWithCallback = layoutNodes.map((node) => ({
      ...node,
      data: {
        ...node.data,
        onAddTask: () => handleOpenModal(node.id, node.data),
      },
    }));
    setNodes(nodesWithCallback);
    setEdges(layoutEdges);
  }, [layoutNodes, layoutEdges, setNodes, setEdges, handleOpenModal, timeZone]);

  const onConnect = useCallback(
    (params: Connection) => setEdges((eds) => addEdge(params, eds)),
    [setEdges],
  );

  // Get selected task data for modal
  return (
    <Box>
      {/* RunTaskModal */}
      <RunTaskModal />

      {/* Legend */}
      <Box
        sx={{
          mt: 3,
          p: 2,
          background: 'var(--bg-secondary)',
          borderRadius: 'var(--radius-md)',
          border: '1px solid rgba(var(--color-border), 0.15)',
        }}
      >
        <Typography
          sx={{ fontSize: '12px', fontWeight: 700, color: 'var(--text-primary)', mb: 1.5 }}
        >
          Action Types Legend
        </Typography>
        <Box sx={{ display: 'flex', flexWrap: 'wrap', gap: 2 }}>
          {Object.entries(ACTION_STYLES).map(([key, style]) => (
            <Box
              key={key}
              sx={{
                display: 'inline-flex',
                alignItems: 'center',
                gap: 0.5,
                px: 1,
                py: 0.5,
                borderRadius: 'var(--radius-lg)',
                background: `color-mix(in srgb, ${style.color} 15%, var(--bg-secondary))`,
                border: `1px solid color-mix(in srgb, ${style.color} 35%, transparent)`,
                fontSize: '10px',
                fontWeight: 600,
                color: style.color,
              }}
            >
              <Box
                sx={{
                  width: 6,
                  height: 6,
                  borderRadius: '50%',
                  background: style.color,
                }}
              />
              {style.label}
            </Box>
          ))}
        </Box>
      </Box>

      {/* Canvas */}
      <Box
        sx={{
          width: '100%',
          height: `${height}px`,
          background: 'var(--bg-tertiary)',
          borderRadius: 'var(--radius-lg)',
          border: '1px solid rgba(var(--color-border), 0.15)',
          overflow: 'hidden',
        }}
      >
        <ReactFlow
          nodes={nodes}
          edges={edges}
          onNodesChange={onNodesChange}
          onEdgesChange={onEdgesChange}
          onConnect={onConnect}
          nodeTypes={NODE_TYPES}
          fitView
          minZoom={0.3}
          maxZoom={1.5}
          defaultViewport={{ x: 0, y: 0, zoom: 0.7 }}
          proOptions={{ hideAttribution: true }}
          edgesUpdatable={false}
          edgesFocusable={false}
          nodesDraggable={true}
          nodesConnectable={false}
          elementsSelectable={true}
        >
          <Background color="rgba(var(--color-border), 0.2)" gap={16} />
          <Controls />
        </ReactFlow>
      </Box>
    </Box>
  );
};

export default WorkflowDiagram;
