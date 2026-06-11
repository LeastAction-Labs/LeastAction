/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { CatalogItem, CatalogNode } from '../../../components/browse/types';

/**
 * Locate a catalog item by id within a nested catalog node list
 */
export function findItemById(nodes: CatalogNode[], targetId: string): CatalogItem | null {
  const walk = (nodes: CatalogNode[], targetId: string): CatalogItem | null => {
    for (const node of nodes) {
      if (node.item.laui === targetId) return node.item;
      if (node.children.length > 0) {
        const found = walk(node.children, targetId);
        if (found) return found;
      }
    }
    return null;
  };
  return walk(nodes, targetId);
}

/**
 * Build path from root to selected item
 */
export function findPathById(nodes: CatalogNode[], targetId: string | null): CatalogItem[] {
  if (!targetId) return [];

  const walk = (
    nodes: CatalogNode[],
    targetId: string,
    acc: CatalogItem[],
  ): CatalogItem[] | null => {
    for (const node of nodes) {
      const nextAcc = [...acc, node.item];
      if (node.item.laui === targetId) return nextAcc;
      if (node.children.length > 0) {
        const found = walk(node.children, targetId, nextAcc);
        if (found) return found;
      }
    }
    return null;
  };

  const res = walk(nodes, targetId, []);
  return res ?? [];
}

/**
 * Extract all items from nested CatalogNode structure
 */
export function extractItems(nodes: CatalogNode[]): CatalogItem[] {
  const items: CatalogItem[] = [];
  nodes.forEach((node) => {
    items.push(node.item);
    if (node.children && node.children.length > 0) {
      items.push(...extractItems(node.children));
    }
  });
  return items;
}

/**
 * Deduplicate catalog items by laui (keeps first occurrence).
 * Use when displaying lists to avoid repeated rows when the same item
 * appears in multiple tree branches or the API returns duplicate nodes.
 */
export function deduplicateItemsByLaui(items: CatalogItem[]): CatalogItem[] {
  const seen = new Set<string>();
  return items.filter((item) => {
    const id = item.laui ?? '';
    if (seen.has(id)) return false;
    seen.add(id);
    return true;
  });
}

/**
 * Append new children to a node in a nested catalog node tree (deduplicates by laui)
 */
export function appendNodeChildren(
  nodes: CatalogNode[],
  itemId: string,
  newChildren: CatalogNode[],
): CatalogNode[] {
  return nodes.map((node) => {
    if (node.item.laui === itemId) {
      const existingLauis = new Set(node.children.map((c) => c.item.laui));
      const unique = newChildren.filter((c) => !existingLauis.has(c.item.laui));
      return { ...node, children: [...node.children, ...unique] };
    }
    if (node.children && node.children.length > 0) {
      return { ...node, children: appendNodeChildren(node.children, itemId, newChildren) };
    }
    return node;
  });
}

/**
 * Update a node's children in a nested catalog node tree
 */
export function updateNodeChildren(
  nodes: CatalogNode[],
  itemId: string,
  children: CatalogNode[],
): CatalogNode[] {
  return nodes.map((node) => {
    if (node.item.laui === itemId) {
      return { ...node, children };
    }
    if (node.children && node.children.length > 0) {
      return { ...node, children: updateNodeChildren(node.children, itemId, children) };
    }
    return node;
  });
}
