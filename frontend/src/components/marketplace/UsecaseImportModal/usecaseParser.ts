/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { searchCatalogItems } from '@/services/catalog.service';

import type {
  ActionDef,
  DependencyStatus,
  ParsedPayload,
  PayloadDepGroup,
  PayloadItem,
  TaskMeta,
} from './types';

/**
 * Extracts JSON metadata from a slash-star ... star-slash comment block at the start of file content.
 * Mirrors parse_task_file() from LeastActionGitToTask.py (lines 281-362).
 */
export function parsePayloadMeta(content: string): { meta: TaskMeta | null; payload: string } {
  // 1. /* ... */ block — find the last */ to handle cron expressions like */3 * * * *
  const blockStart = content.indexOf('/*');
  const blockEnd = content.lastIndexOf('*/');
  if (blockStart !== -1 && blockEnd > blockStart + 1) {
    try {
      const inner = content.slice(blockStart + 2, blockEnd).trim();
      const meta = JSON.parse(inner) as TaskMeta;
      const payload = content.slice(blockEnd + 2).trim();
      return { meta, payload };
    } catch {
      // JSON parse failed, fall through
    }
  }

  // 2. Triple-quoted docstring (""" or ''')
  for (const quote of ['"""', "'''"]) {
    const startIdx = content.indexOf(quote);
    if (startIdx !== -1) {
      const endIdx = content.indexOf(quote, startIdx + 3);
      if (endIdx !== -1) {
        const block = content.slice(startIdx + 3, endIdx).trim();
        const js = block.indexOf('{');
        const je = block.lastIndexOf('}');
        if (js !== -1 && je > js) {
          try {
            const meta = JSON.parse(block.slice(js, je + 1)) as TaskMeta;
            const payload = content.slice(endIdx + 3).trim();
            return { meta, payload };
          } catch {
            // fall through
          }
        }
      }
    }
  }

  // 3. Leading # comment block (Python / YAML)
  const lines = content.split('\n');
  const commentLines: string[] = [];
  let i = 0;
  while (i < lines.length && lines[i].trimStart().startsWith('#')) {
    commentLines.push(lines[i].trimStart().slice(1).trim());
    i++;
  }
  const joined = commentLines.join('\n');
  const js = joined.indexOf('{');
  const je = joined.lastIndexOf('}');
  if (js !== -1 && je > js) {
    try {
      const meta = JSON.parse(joined.slice(js, je + 1)) as TaskMeta;
      const payload = lines.slice(i).join('\n').trim();
      return { meta, payload };
    } catch {
      // fall through
    }
  }

  // 4. Pure JSON content
  try {
    const meta = JSON.parse(content) as TaskMeta;
    return { meta, payload: '' };
  } catch {
    // fall through
  }

  return { meta: null, payload: content };
}

/**
 * Normalize a raw payload entry (may be a JSON string or an object) into a PayloadItem.
 */
function normalizePayload(raw: string | PayloadItem): PayloadItem {
  if (typeof raw === 'string') {
    try {
      return JSON.parse(raw) as PayloadItem;
    } catch {
      return { filename: 'unknown', content: raw };
    }
  }
  return raw;
}

/**
 * Parse all payloads and return structured results.
 * Handles both object payloads and JSON-string payloads (marketplace stores them as strings).
 */
export function parseAllPayloads(payloads: (string | PayloadItem)[]): ParsedPayload[] {
  return payloads.map((raw) => {
    const p = normalizePayload(raw);
    const { meta, payload } = parsePayloadMeta(p.content);
    return { filename: p.filename, meta, payload };
  });
}

/**
 * Extract unique dependency names from all parsed payloads.
 */
export function extractAllDependencies(parsed: ParsedPayload[]): {
  operators: string[];
  connections: string[];
  configs: string[];
  actions: string[];
} {
  const operators = new Set<string>();
  const connections = new Set<string>();
  const configs = new Set<string>();
  const actions = new Set<string>();

  for (const p of parsed) {
    if (!p.meta) continue;

    if (p.meta.operator_name) operators.add(p.meta.operator_name);
    if (p.meta.connection_name) connections.add(p.meta.connection_name);

    const configNames = p.meta.config_name;
    if (configNames) {
      const cfgArray = Array.isArray(configNames) ? configNames : [configNames];
      cfgArray.forEach((c) => c && configs.add(c));
    }

    const actionsBlock = p.meta.actions;
    if (actionsBlock) {
      const allActions: ActionDef[] = [
        ...(actionsBlock.pre_actions ?? []),
        ...(actionsBlock.running_actions ?? []),
        ...(actionsBlock.post_actions ?? []),
      ];
      allActions.forEach((a) => {
        if (a.name) actions.add(a.name);
      });
    }
  }

  return {
    operators: [...operators],
    connections: [...connections],
    configs: [...configs],
    actions: [...actions],
  };
}

/**
 * Search core catalog for an item by type and name. Returns laui or null.
 */
export async function resolveNameToLaui(itemType: string, name: string): Promise<string | null> {
  try {
    const data = await searchCatalogItems(itemType, false, {
      filters: { name },
      projection: ['name', 'laui'],
      perPage: 1,
    });
    const items = data?.items ?? [];
    if (items.length > 0) {
      const item = items[0].item ?? items[0];
      return item._laui ?? item.laui ?? item._id ?? null;
    }
  } catch {
    // search failed
  }
  return null;
}

/**
 * Resolve an operator by marketplace_laui.
 * Looks up the marketplace operator by name to get its laui (treated as marketplace_laui),
 * then searches local catalog for an operator whose marketplace_laui matches.
 * Compares marketplace_laui on the frontend to avoid backend ObjectId coercion mismatch.
 * Does NOT fall back to name matching.
 */
export async function resolveOperatorByMarketplaceLaui(
  name: string,
  marketplaceLaui?: string,
): Promise<string | null> {
  try {
    let mktLaui = marketplaceLaui;

    // If no marketplace_laui in meta, look up marketplace by name to get its laui
    if (!mktLaui) {
      const mktData = await searchCatalogItems('operator', true, {
        filters: { name },
        projection: ['name', 'laui'],
        perPage: 1,
      });
      const mktItems = mktData?.items ?? [];
      if (mktItems.length === 0) return null;
      const mktItem = mktItems[0].item ?? mktItems[0];
      mktLaui = mktItem._laui ?? mktItem.laui ?? mktItem._id;
    }

    if (!mktLaui) return null;

    // Search local catalog for operators by name, then compare marketplace_laui locally.
    // We avoid filtering by marketplace_laui in the backend because the backend coerces
    // _laui fields to ObjectId, but marketplace_laui is stored as a string.
    const localData = await searchCatalogItems('operator', false, {
      filters: { name },
      projection: ['name', 'laui', 'marketplace_laui'],
      perPage: 10,
    });
    const localItems = localData?.items ?? [];
    for (const entry of localItems) {
      const localItem = entry.item ?? entry;
      const localMktLaui = localItem.marketplace_laui;
      if (localMktLaui && String(localMktLaui) === String(mktLaui)) {
        return localItem._laui ?? localItem.laui ?? localItem._id ?? null;
      }
    }

    return null;
  } catch {
    return null;
  }
}

/**
 * Resolve an action by marketplace_laui.
 * Same approach as resolveOperatorByMarketplaceLaui — looks up the marketplace action
 * by name to get its laui, then searches local catalog for an action whose
 * marketplace_laui matches. Compares on the frontend to avoid backend ObjectId coercion.
 */
export async function resolveActionByMarketplaceLaui(
  name: string,
  marketplaceLaui?: string,
): Promise<string | null> {
  try {
    let mktLaui = marketplaceLaui;

    // If no marketplace_laui in meta, look up marketplace by name to get its laui
    if (!mktLaui) {
      const mktData = await searchCatalogItems('action', true, {
        filters: { name },
        projection: ['name', 'laui'],
        perPage: 1,
      });
      const mktItems = mktData?.items ?? [];
      if (mktItems.length === 0) return null;
      const mktItem = mktItems[0].item ?? mktItems[0];
      mktLaui = mktItem._laui ?? mktItem.laui ?? mktItem._id;
    }

    if (!mktLaui) return null;

    // Search local catalog for actions by name, then compare marketplace_laui locally.
    const localData = await searchCatalogItems('action', false, {
      filters: { name },
      projection: ['name', 'laui', 'marketplace_laui'],
      perPage: 10,
    });
    const localItems = localData?.items ?? [];
    for (const entry of localItems) {
      const localItem = entry.item ?? entry;
      const localMktLaui = localItem.marketplace_laui;
      if (localMktLaui && String(localMktLaui) === String(mktLaui)) {
        return localItem._laui ?? localItem.laui ?? localItem._id ?? null;
      }
    }

    return null;
  } catch {
    return null;
  }
}

/**
 * Check all dependencies against the core catalog.
 * Operators and actions are resolved by marketplace_laui (from meta or marketplace lookup).
 */
export async function checkDependencies(parsed: ParsedPayload[]): Promise<DependencyStatus[]> {
  const deps = extractAllDependencies(parsed);
  const results: DependencyStatus[] = [];

  // Build a map of operator_name → marketplace_laui from parsed metas
  const operatorMktLauiMap = new Map<string, string>();
  for (const p of parsed) {
    if (p.meta?.operator_name && p.meta?.marketplace_laui) {
      operatorMktLauiMap.set(p.meta.operator_name, p.meta.marketplace_laui);
    }
  }

  // Build a map of action_name → marketplace_laui from parsed metas
  const actionMktLauiMap = new Map<string, string>();
  for (const p of parsed) {
    if (!p.meta?.actions) continue;
    const allActions: ActionDef[] = [
      ...(p.meta.actions.pre_actions ?? []),
      ...(p.meta.actions.running_actions ?? []),
      ...(p.meta.actions.post_actions ?? []),
    ];
    for (const a of allActions) {
      if (a.name && a.marketplace_laui) {
        actionMktLauiMap.set(a.name, a.marketplace_laui);
      }
    }
  }

  // Connections and configs are never auto-resolved — user must select or create manually
  for (const name of deps.connections) {
    results.push({ name, type: 'connection', found: false });
  }
  for (const name of deps.configs) {
    results.push({ name, type: 'config', found: false });
  }

  // Resolve operators by marketplace_laui
  const operatorChecks = deps.operators.map(async (name) => {
    const mktLaui = operatorMktLauiMap.get(name);
    const laui = await resolveOperatorByMarketplaceLaui(name, mktLaui);
    return { name, type: 'operator' as const, found: !!laui, laui: laui ?? undefined };
  });

  // Resolve actions by marketplace_laui
  const actionChecks = deps.actions.map(async (name) => {
    const mktLaui = actionMktLauiMap.get(name);
    const laui = await resolveActionByMarketplaceLaui(name, mktLaui);
    return { name, type: 'action' as const, found: !!laui, laui: laui ?? undefined };
  });

  const settled = await Promise.allSettled([...operatorChecks, ...actionChecks]);

  for (const result of settled) {
    if (result.status === 'fulfilled') {
      results.push(result.value);
    } else {
      results.push({ name: '', type: 'operator', found: false });
    }
  }

  return results;
}

/**
 * Build action list for a task, resolving action_name to laui.
 * Mirrors build_action_list() from LeastActionGitToTask.py (lines 390-426).
 */
export function buildActionList(
  actionDefs: ActionDef[],
  depCache: Map<string, string>,
): { laui: string; action_variables: Record<string, any> }[] | null {
  const built: { laui: string; action_variables: Record<string, any> }[] = [];

  for (const action of actionDefs) {
    if (!action.name) return null;

    const laui = depCache.get(`action:${action.name}`);
    if (!laui) return null;

    built.push({
      laui,
      action_variables: { ...(action.action_variables ?? {}) },
    });
  }

  return built;
}

/**
 * Derive task name from meta and filename.
 * Uses the payload filename (catalog item name) as the base to ensure
 * uniqueness — meta.name can be identical across different payloads.
 */
export function deriveTaskName(meta: TaskMeta, filename: string): string {
  // Strip extension from filename (the payload's own catalog name)
  const dotIdx = filename.lastIndexOf('.');
  const baseName = dotIdx > 0 ? filename.slice(0, dotIdx) : filename;

  const parts = [baseName];
  if (meta.operator_name) parts.push(meta.operator_name);

  const actionNames: string[] = [];
  if (meta.actions) {
    for (const phase of [
      meta.actions.pre_actions,
      meta.actions.running_actions,
      meta.actions.post_actions,
    ]) {
      for (const a of phase ?? []) if (a.name) actionNames.push(a.name);
    }
  }
  if (actionNames.length) parts.push(actionNames.join('_'));

  return parts.join('__');
}

/**
 * Group parsed payloads by their dependency signature.
 * Payloads sharing the same {operator, connection, configs, actions} are grouped together.
 */
export function groupPayloadsByDeps(parsed: ParsedPayload[]): PayloadDepGroup[] {
  const groups = new Map<string, PayloadDepGroup>();

  for (const p of parsed) {
    if (!p.meta) continue;
    const op = p.meta.operator_name || '';
    const conn = p.meta.connection_name || '';
    const cfgs = p.meta.config_name
      ? (Array.isArray(p.meta.config_name) ? [...p.meta.config_name] : [p.meta.config_name]).sort()
      : [];
    const acts: string[] = [];
    if (p.meta.actions) {
      for (const phase of [
        p.meta.actions.pre_actions,
        p.meta.actions.running_actions,
        p.meta.actions.post_actions,
      ]) {
        for (const a of phase ?? []) if (a.name) acts.push(a.name);
      }
    }
    acts.sort();

    const key = JSON.stringify({ op, conn, cfgs, acts });
    const existing = groups.get(key);
    if (existing) {
      existing.payloadNames.push(p.meta.name || p.filename);
    } else {
      groups.set(key, {
        payloadNames: [p.meta.name || p.filename],
        operator_name: op,
        connection_name: conn,
        config_names: cfgs,
        action_names: acts,
      });
    }
  }

  return Array.from(groups.values());
}
