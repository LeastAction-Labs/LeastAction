/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { startTransition, useEffect, useRef } from 'react';

import type { CatalogItem, CatalogNode } from '@/components/browse/types';
import { useCatalog } from '@/contexts/CatalogContext';
import { CatalogType, useGlobal } from '@/contexts/GlobalContext';
import {
  getBreadcrumbs,
  getCatalogItemById,
  getChildCatalogNodes,
} from '@/services/catalog.service';
import { getDocContent, getDocsTree, isDocItem } from '@/utils/docsTree';

import { useCatalogActions, useCatalogTree } from '.';
import { useEditorHandlers } from '../handlers/editorHandlers';
import { flattenBreadcrumbChain, updateNodeChildren } from '../utils';

interface UseDeepLinkProps {
  itemtype: string | undefined;
  itemname: string | undefined;
  laui: string | undefined;
  filtertype?: string | undefined;
  page?: number;
  perPage?: number;
  sortBy?: string;
  sortOrder?: 'asc' | 'desc';
  isAuthReady?: boolean;
}

export interface UseDeepLinkResult {
  /**
   * Call this before navigating to a new item via in-app interaction (sidebar click,
   * breadcrumb click, etc.) so that useDeepLink skips re-resolving when the URL
   * updates — the view is already correct, no API fetch needed.
   */
  markNavigatedInApp: (laui: string) => void;
}

/**
 * Resolve deep link: load parent chain into tree (in memory, then set once),
 * expand sidebar, set breadcrumb and view.
 */
export function useDeepLink({
  itemtype,
  itemname,
  laui,
  filtertype,
  page,
  perPage,
  sortBy,
  sortOrder,
  isAuthReady,
}: UseDeepLinkProps): UseDeepLinkResult {
  const { catalogType } = useGlobal();
  const { catalogState } = useCatalog();
  const { handleViewItem, handleEditorReset } = useEditorHandlers();
  const { findItem, findPath } = useCatalogTree();
  const { loadChildrenByType } = useCatalogActions(findItem, findPath);

  const {
    setItems,
    setLoadedChildren,
    setSelectedItem,
    setOpenedFolder,
    setExpandedItems,
    setDeepLinkBreadcrumbPath,
    setIsLoading,
    setError,
    setFilteredFromItem,
    setActiveFilterType,
    setIsItemFromTable,
    setLastFilterType,
    setLastFilteredFromItem,
    setItemNotFound,
  } = catalogState;

  const isMarketplaceCatalog = catalogType === CatalogType.MARKETPLACE;

  // Track the last laui that was fully resolved so in-app folder navigation
  // (which updates the URL to the current folder) does not re-trigger a full
  // API fetch and tree rebuild for a view that is already showing correctly.
  const lastResolvedLaui = useRef<string | null>(null);

  // Keep a ref to the latest items array so resolveDeepLink can read it without
  // being in the dependency array (avoids re-firing when tree state changes).
  const itemsRef = useRef(catalogState.items);
  itemsRef.current = catalogState.items;

  // Pagination/sort refs — these change on in-app sort/page actions (handled by
  // paginationHandlers) and must NOT re-trigger the deep-link effect.
  const pageRef = useRef(page);
  pageRef.current = page;
  const perPageRef = useRef(perPage);
  perPageRef.current = perPage;
  const sortByRef = useRef(sortBy);
  sortByRef.current = sortBy;
  const sortOrderRef = useRef(sortOrder);
  sortOrderRef.current = sortOrder;

  useEffect(() => {
    if (!laui || !itemtype) {
      setDeepLinkBreadcrumbPath([]);
      setItemNotFound(false);
      lastResolvedLaui.current = null;
      return;
    }
    // Don't resolve until auth is confirmed — avoids firing resolveDeepLink with an
    // empty item tree (loadItems only runs once isAuthenticated is true).
    if (!isAuthReady) return;

    // Skip re-resolving if this laui was already resolved (e.g. URL was just updated
    // by an in-app navigation action that already set the correct view state).
    if (laui === lastResolvedLaui.current) return;

    // Poll until root items are available. Don't gate on isLoading — that state update
    // may not have flushed yet when this effect first fires. Cap at 60 polls (~3s) so
    // an empty catalog still eventually proceeds (resolveDeepLink fetches item directly).
    let retryCount = 0;
    const waitForItemsAndResolve = () => {
      if (itemsRef.current.length === 0 && retryCount < 60) {
        retryCount++;
        const timer = setTimeout(waitForItemsAndResolve, 50);
        return () => clearTimeout(timer);
      }
      void resolveDeepLink();
      return undefined;
    };

    const resolveDeepLink = async () => {
      // Re-check guard inside async path (another navigation may have fired meanwhile)
      if (laui === lastResolvedLaui.current) return;

      // Doc items are client-side only — resolve from in-memory tree, no API call
      if (isDocItem(laui)) {
        const tree = getDocsTree();
        const findPath = (
          node: CatalogNode,
          target: string,
          path: string[] = [],
        ): string[] | null => {
          if (node.item.laui === target) return path;
          for (const c of node.children) {
            const r = findPath(c, target, [...path, node.item.laui]);
            if (r) return r;
          }
          return null;
        };
        const findNode = (node: CatalogNode): CatalogNode | null => {
          if (node.item.laui === laui) return node;
          for (const c of node.children) {
            const f = findNode(c);
            if (f) return f;
          }
          return null;
        };
        const found = findNode(tree);
        const ancestorLauis = findPath(tree, laui) ?? [];
        if (found) {
          const content = getDocContent(laui);
          const docItem = {
            ...found.item,
            data: { name: found.item.name, description: content ?? '' },
          };
          startTransition(() => {
            setExpandedItems(new Set(ancestorLauis));
            setDeepLinkBreadcrumbPath([docItem as CatalogItem]);
          });
          await handleViewItem(found.item);
          lastResolvedLaui.current = laui;
        }
        setIsLoading(false);
        return;
      }

      try {
        setIsLoading(true);
        setError('');
        setItemNotFound(false);

        // Fetch item metadata and breadcrumbs in parallel — they are independent
        const [targetItem, breadcrumbData] = await Promise.all([
          getCatalogItemById(laui, isMarketplaceCatalog),
          getBreadcrumbs(laui, isMarketplaceCatalog),
        ]);

        const targetAsItem: CatalogItem = {
          laui: targetItem.laui,
          name: targetItem.name,
          item_type: targetItem.item_type,
          permission: targetItem.permission ?? 'view',
          supported_types: targetItem.supported_types,
          deleted_at: targetItem.deleted_at ?? undefined,
        };

        const rawItems: CatalogNode[] = breadcrumbData.items ?? [];
        const ancestorNodes = flattenBreadcrumbChain(rawItems);

        const currentItems = itemsRef.current;
        const rootLauis = new Set(currentItems.map((n) => n.item.laui));
        const firstIsRoot = ancestorNodes.length > 0 && rootLauis.has(ancestorNodes[0].item.laui);
        let ancestorsOrdered: CatalogNode[] =
          ancestorNodes.length > 0
            ? firstIsRoot
              ? [...ancestorNodes]
              : [...ancestorNodes].reverse()
            : [];

        // If API didn't return root (e.g. nested folder), prepend root so we can load root's children first
        if (
          ancestorsOrdered.length > 0 &&
          currentItems.length > 0 &&
          !rootLauis.has(ancestorsOrdered[0].item.laui)
        ) {
          ancestorsOrdered = [currentItems[0], ...ancestorsOrdered];
        }

        const expandedSet = new Set<string>();
        ancestorsOrdered.forEach((node) => expandedSet.add(node.item.laui));
        if (itemtype.startsWith('folder')) {
          expandedSet.add(laui);
        }

        // Build the full list of nodes whose children we need to fetch
        const nodesToFetch: Array<{ id: string; perm: string }> = ancestorsOrdered.map((node) => ({
          id: node.item.laui,
          perm: node.item.permission ?? 'view',
        }));
        if (itemtype.startsWith('folder')) {
          nodesToFetch.push({ id: laui, perm: targetAsItem.permission });
        }

        // Fetch all children in parallel — none of these calls depend on each other
        const fetchChildren = ({ id, perm }: { id: string; perm: string }) =>
          getChildCatalogNodes(id, perm, isMarketplaceCatalog, 1, 10, 'folder').then(
            ({ items }) => ({ id, items }),
          );
        const fetchResults = await Promise.all(nodesToFetch.map(fetchChildren));

        // Apply results to the in-memory tree in order
        let tree: CatalogNode[] = currentItems;
        const loadedIds = new Set<string>();
        for (const { id, items: children } of fetchResults) {
          tree = updateNodeChildren(tree, id, children);
          loadedIds.add(id);
        }

        // Path from root to current context (folder or filter parent) for breadcrumb; include target for non-folder
        const pathItems = ancestorsOrdered.map((n) => n.item);
        const breadcrumbPathForView = itemtype.startsWith('folder')
          ? pathItems
          : [...pathItems, targetAsItem];

        // Batch all state updates so sidebar gets new tree and expanded set in one render
        startTransition(() => {
          setItems(tree);
          setLoadedChildren((prev) => new Set([...prev, ...loadedIds]));
          setExpandedItems(new Set(expandedSet));
          setDeepLinkBreadcrumbPath(breadcrumbPathForView);
        });

        if (itemtype.startsWith('folder')) {
          handleEditorReset();
          setSelectedItem(targetAsItem);
          setOpenedFolder(targetAsItem);
          if (filtertype) {
            await loadChildrenByType(
              laui,
              filtertype,
              targetAsItem.permission,
              pageRef.current ?? 1,
              perPageRef.current ?? 25,
              sortByRef.current,
              sortOrderRef.current,
              undefined,
              targetAsItem,
            );
          } else {
            setFilteredFromItem(null);
            setActiveFilterType(null);
            setIsItemFromTable(false);
          }
        } else {
          // Deep link to a single non-folder item: show Item Details (TabView), not the item table.
          const immediateParent =
            ancestorsOrdered.length > 0 ? ancestorsOrdered[ancestorsOrdered.length - 1] : null;
          const parentItem = immediateParent?.item;

          if (parentItem) {
            setOpenedFolder(parentItem);
            setFilteredFromItem(null);
            setActiveFilterType(null);
            // Keep parent + type so breadcrumb shows "action" and clicking it goes back to action list
            setLastFilterType(itemtype);
            setLastFilteredFromItem(parentItem);
          } else {
            setOpenedFolder(null);
            setLastFilterType(null);
            setLastFilteredFromItem(null);
          }

          setSelectedItem(targetAsItem);
          setIsItemFromTable(true);
          await handleViewItem(targetAsItem);
        }

        // Mark as resolved so in-app URL updates don't re-trigger this effect
        lastResolvedLaui.current = laui;
      } catch (err: unknown) {
        const errStatus =
          typeof err === 'object' && err !== null && 'status' in err
            ? (err as { status: number }).status
            : 0;
        const isNotFound = errStatus === 404 || errStatus === 400 || errStatus === 422;
        if (isNotFound) {
          setItemNotFound(true);
        }
        const message = err instanceof Error ? err.message : 'Failed to resolve deep link';
        console.error('Deep link resolution failed:', err);
        setError(message);
      } finally {
        setIsLoading(false);
      }
    };

    // Doc items are client-side only — resolve immediately without waiting for catalog
    if (isDocItem(laui)) {
      void resolveDeepLink();
      return;
    }

    return waitForItemsAndResolve();
    // eslint-disable-next-line react-hooks/exhaustive-deps -- intentionally omit state.items and pagination/sort params (handled by paginationHandlers)
  }, [laui, itemtype, itemname, filtertype, isAuthReady]);

  return {
    markNavigatedInApp: (targetLaui: string) => {
      lastResolvedLaui.current = targetLaui;
    },
  };
}
