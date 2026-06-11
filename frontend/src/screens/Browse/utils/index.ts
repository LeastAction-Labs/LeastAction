/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { CatalogItem, FormMode } from '@/components/browse';
import { TaskModalScopeType } from '@/contexts/TaskModalContext';
import {
  createCatalogItem,
  getCatalogItemById,
  getChildCatalogNodesByType,
} from '@/services/catalog.service';
import { getSubtypesFor } from '@/services/system.service';

import type { EditorStateType } from '../hooks/useCatalogEditor';
import type { CatalogStateType } from '../hooks/useCatalogState';
import type { AttachedActions } from '../interfaces/Workflow';

export {
  findItemById,
  findPathById,
  extractItems,
  deduplicateItemsByLaui,
  updateNodeChildren,
} from './catalogTreeUtils';
export { getBreadcrumbItemId, flattenBreadcrumbChain } from './breadcrumbUtils';

// Determine context type based on filterType
export const getTaskModalScopeType = (filterType: string): TaskModalScopeType => {
  if (filterType.includes('operator')) return TaskModalScopeType.OPERATOR;
  if (filterType.includes('payload')) return TaskModalScopeType.PAYLOAD;
  if (filterType.includes('connection')) return TaskModalScopeType.CONNECTION;
  if (filterType === 'task') return TaskModalScopeType.OPERATOR; // Task items have operator_laui read-only
  return TaskModalScopeType.DEFAULT;
};

export const getActualFilterType = (
  editorState: EditorStateType,
  catalogState: CatalogStateType,
) => {
  const { formMode, editingItem, viewingItem, createFilterType } = editorState;
  const { selectedItem, filteredItemsByType } = catalogState;
  return formMode === 'edit'
    ? editingItem?.item_type
    : formMode === 'view'
      ? viewingItem?.item_type
      : formMode === 'create' && createFilterType
        ? createFilterType
        : formMode === 'create' && selectedItem?.item_type.startsWith('folder')
          ? selectedItem?.item_type
          : filteredItemsByType || 'folder';
};

export const getAvailableSubtypes = (
  filterType: string,
  formMode: FormMode,
  selectedItem: CatalogItem,
) => {
  let availableSubtypes: string[] = [];
  const baseType = filterType?.split('.')[0] || '';
  if (
    (formMode === 'create' || formMode === 'edit') &&
    ['folder', 'operator', 'connection', 'action'].includes(baseType)
  ) {
    if (baseType === 'connection' || baseType === 'operator' || baseType === 'action') {
      availableSubtypes = getSubtypesFor(baseType as 'connection' | 'operator');
    } else if (baseType === 'folder' && selectedItem?.supported_types) {
      availableSubtypes = selectedItem.supported_types.filter((t: string) =>
        t.startsWith(baseType + '.'),
      );
    }
  }
  return availableSubtypes;
};

export const updateItemAccess = async (shareData: {
  itemLaui: string;
  userLaui: string;
  currentRelation?: string;
  newRelation: string;
}) => {
  const item_details = await getCatalogItemById(shareData.itemLaui);
  await createCatalogItem({
    ...item_details,
    access_patch: {
      ...(shareData.newRelation && {
        add: {
          [shareData.newRelation]: {
            [shareData.userLaui]: '',
          },
        },
      }),
      ...(shareData.currentRelation && {
        remove: {
          [shareData.currentRelation]: {
            [shareData.userLaui]: '',
          },
        },
      }),
    },
  });
};

export const getAttachedActions = async (item: CatalogItem) => {
  const attachedActions: AttachedActions = {
    uiActions: [],
    taskControlActions: [],
  };

  // 1. Fetch config children to get taskControlActions from defaults
  const { items: configChildren } = await getChildCatalogNodesByType(
    item.laui,
    'config',
    item.permission,
  );

  if (configChildren && configChildren.length > 0) {
    for (const configNode of configChildren) {
      const configItem = configNode.item;
      const content = (configItem.data as any)?.content || (configItem as any)?.content;
      if (content?.defaults?.taskControlActions) {
        const taskControlActionsFromConfig = content.defaults.taskControlActions;
        taskControlActionsFromConfig.forEach((action: any) => {
          attachedActions.taskControlActions.push({
            name: action.action,
            metadata: action.variables || {},
          });
        });
      }
      if (content?.defaults?.uiActions) {
        const uiActionsFromConfig = content.defaults.uiActions;
        uiActionsFromConfig.forEach((action: any) => {
          attachedActions.uiActions.push({
            name: action.action,
            metadata: action.variables || {},
          });
        });
      }
    }
  }

  // 2. Fetch action children from the workflow
  const { items: actionChildren } = await getChildCatalogNodesByType(
    item.laui,
    'action',
    item.permission,
  );

  if (actionChildren && actionChildren.length > 0) {
    actionChildren.forEach((actionNode: any) => {
      const actionItem = actionNode.item;
      attachedActions.taskControlActions.push({
        name: actionItem.name,
        metadata: {
          catalogState: [
            'created',
            'scheduled',
            'success',
            'error',
            'timeout',
            'cancelled',
            'fail',
          ],
        },
      });
    });
  }

  return attachedActions;
};
