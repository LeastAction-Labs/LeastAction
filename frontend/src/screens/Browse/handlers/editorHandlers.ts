/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { useNavigate } from '@tanstack/react-router';

import type { CatalogItem, FormSchema } from '@/components/browse';
import { useCatalog } from '@/contexts/CatalogContext';
import { CatalogType, useGlobal } from '@/contexts/GlobalContext';
import { useNotification } from '@/contexts/NotificationContext';
import {
  createCatalogItem,
  createCatalogLink,
  getCatalogItemById,
} from '@/services/catalog.service';
import { getSchema } from '@/services/schema.service';
import { validateCodeblock } from '@/services/validation.service';
import { getDocContent, isDocItem } from '@/utils/docsTree';

import { usePaginationHandlers } from './paginationHandlers';
import { useRefreshHandlers } from './refreshHandlers';

export function useEditorHandlers() {
  const { catalogType, addTab, accountLaui, currentProjectLaui } = useGlobal();
  const { catalogState, editorState, markNavigatedInAppRef } = useCatalog();
  const { setSelectedItem, setSchemaError, setIsBreadcrumbLocked } = catalogState;
  const {
    formMode,
    editingItem,
    viewingItem,
    setFormMode,
    setCreateFilterType,
    setViewingItem,
    setEditingItem,
    setFormSchema,
    setIsEditorActive,
  } = editorState;
  const { showWarning, showSuccess } = useNotification();
  const navigate = useNavigate();
  const { handleRefreshItem } = useRefreshHandlers();
  const { refreshFilteredList } = usePaginationHandlers();

  const isMarketplaceCatalog = catalogType === CatalogType.MARKETPLACE;

  const loadSchemaForType = async (filterType: string): Promise<void> => {
    try {
      const schema = await getSchema(filterType);
      if (schema) {
        const formSchema: FormSchema = {
          columns: schema.columns,
          projection_fields: schema.projection_fields || [],
          unique_constraints: schema.unique_constraints || [],
          indexes: schema.indexes || [],
          user_update_fields: schema.user_update_fields || [],
          form_excluded_fields: schema.form_excluded_fields || [],
        };
        setFormSchema(formSchema);
      } else {
        showWarning(`No schema found for type: ${filterType}. Using fallback schema.`);
        setFormSchema(getFallbackSchema(filterType));
      }
    } catch {
      const errorMsg = `Failed to load schema for ${filterType}`;
      setSchemaError(errorMsg);
      setFormSchema(getFallbackSchema(filterType));
    }
  };

  function getFallbackSchema(type: string): FormSchema {
    return {
      columns: [
        {
          name: 'name',
          datatype: 'string',
          required: true,
          description: `${type} name`,
        },
        {
          name: 'description',
          datatype: 'string',
          required: false,
          description: `${type} description`,
        },
      ],
      projection_fields: [],
      unique_constraints: [],
      indexes: [],
    };
  }

  const handleCreateNewItem = async (
    filterType: string,
    editingItem: CatalogItem | null = null,
  ) => {
    await loadSchemaForType(filterType);
    setFormMode(editingItem ? 'edit' : 'create');
    setCreateFilterType(editingItem ? null : filterType);
    setEditingItem(editingItem);
    setIsEditorActive(true);
  };

  const handleEditItem = async (item: CatalogItem) => {
    try {
      const fullItemData = await getCatalogItemById(item.laui, isMarketplaceCatalog);
      try {
        await loadSchemaForType(item.item_type);
        setFormMode('edit');
        setEditingItem(fullItemData);
        setIsEditorActive(true);
      } catch {
        showWarning(`Could not load full item data. Editing with available data.`);
        await loadSchemaForType(item.item_type);
        setFormMode('edit');
        setEditingItem(item);
        setIsEditorActive(true);
      }
    } catch {
      /* ignore */
    }
  };

  const handleSaveItem = async (data: any, filterType: string) => {
    try {
      const processedData = { ...data };

      // Synthetic UI-only fields — never sent to the backend as item fields.
      // attached_config: set when creating a folder.workflow (attach a config to it).
      const attachedConfig = processedData.attached_config;
      delete processedData.attached_config;
      // existing_config_laui: set in the Add Config flow to link an existing config instead of creating one.
      const existingConfigLaui = processedData.existing_config_laui;
      delete processedData.existing_config_laui;

      let parent_laui: string | null = null;

      if (formMode === 'create') {
        if (catalogState.filteredFromItem) {
          parent_laui = catalogState.filteredFromItem.laui;
        } else if (catalogState.selectedItem?.item_type?.startsWith('folder')) {
          parent_laui = catalogState.selectedItem.laui;
        } else if (catalogState.openedFolder) {
          parent_laui = catalogState.openedFolder.laui;
        }
      } else if (formMode === 'edit' && editingItem?.laui) {
        parent_laui = editingItem.parent_laui || null;
      }

      const itemData: Record<string, any> = {
        item_type: filterType,
        ...processedData,
        parent_laui: parent_laui,
      };

      // Resolved type after subtype is applied (e.g. generic "folder" + subtype → "folder.workflow").
      const resolvedItemType: string = itemData.item_type || filterType;

      if (filterType !== 'folder.account') {
        itemData.account_laui = accountLaui;
      }
      if (filterType !== 'folder.account' && filterType !== 'folder.project') {
        itemData.project_laui = currentProjectLaui;
      }

      // Pre-save codeblock validation for operators and actions
      const base = (filterType || '').split('.')[0];
      if ((base === 'operator' || base === 'action') && processedData.codeblock) {
        const result = await validateCodeblock(processedData.codeblock, filterType);
        if (!result.valid) {
          return;
        }
      }

      // In edit mode, convert empty strings to null so backend $set can clear optional fields.
      // removeEmptyStrings (in preprocessItemData) only strips "", not null, so null passes through.
      if (formMode === 'edit') {
        for (const key of Object.keys(itemData)) {
          if (itemData[key] === '') itemData[key] = null;
        }
      }

      // Add Config flow: user picked an existing config to attach instead of creating a new one.
      // Link it as a child of the parent (e.g. the workflow folder) and skip item creation.
      if (
        formMode === 'create' &&
        resolvedItemType.split('.')[0] === 'config' &&
        existingConfigLaui
      ) {
        if (!parent_laui) {
          showWarning('No parent folder to attach the config to.');
          return;
        }
        await createCatalogLink({ parent_laui, child_laui: existingConfigLaui });
        showSuccess('Config attached successfully!');
        setIsEditorActive(false);
        await handleRefreshItem(parent_laui, 'own');
        return;
      }

      // Attach a config (link existing or create new) to a workflow folder identified by workflowLaui.
      // Used in both create (new folder laui) and edit (existing folder laui) flows.
      const attachConfigToWorkflow = async (workflowLaui: string | undefined) => {
        if (resolvedItemType !== 'folder.workflow' || !attachedConfig || !workflowLaui) return;
        try {
          if (attachedConfig.mode === 'existing' && attachedConfig.configLaui) {
            await createCatalogLink({
              parent_laui: workflowLaui,
              child_laui: attachedConfig.configLaui,
            });
          } else if (attachedConfig.mode === 'create' && attachedConfig.configForm?.name) {
            await createCatalogItem(
              {
                item_type: 'config',
                ...attachedConfig.configForm,
                parent_laui: workflowLaui,
                account_laui: accountLaui,
                project_laui: currentProjectLaui,
              },
              isMarketplaceCatalog,
            );
          } else if (attachedConfig.mode === 'create') {
            showWarning('Config name is required — workflow saved without attaching a config.');
          }
        } catch {
          showWarning('Workflow saved, but attaching the config failed.');
        }
      };

      let createdItem: any = null;
      if (formMode === 'create') {
        createdItem = await createCatalogItem(itemData, isMarketplaceCatalog);
        showSuccess(`${filterType} created successfully!`);
        if (filterType.startsWith('folder')) setIsEditorActive(false);
        await attachConfigToWorkflow(
          createdItem?._laui ?? createdItem?.laui ?? createdItem?.item_laui,
        );
      } else if (formMode === 'edit' && editingItem?.laui) {
        await createCatalogItem(itemData, isMarketplaceCatalog);
        await attachConfigToWorkflow(editingItem.laui);
        showSuccess(`${editingItem.name || filterType} updated successfully!`);
        setFormMode('view');
        setEditingItem(null);
        if (filterType.startsWith('folder')) setIsEditorActive(false);
      }
      if (formMode === 'create') {
        if (!filterType.startsWith('folder')) {
          const laui = createdItem?._laui ?? createdItem?.laui ?? createdItem?.item_laui;
          if (laui) {
            await handleViewItem({
              laui,
              name: createdItem?.name ?? itemData.name,
              item_type: createdItem?.item_type ?? filterType,
            } as CatalogItem);
          } else {
            setIsEditorActive(false);
            await refreshFilteredList();
          }
        } else {
          await handleRefreshItem(parent_laui || '', 'own');
        }
        return;
      }
      const newData = await getCatalogItemById(editingItem.laui, isMarketplaceCatalog);
      setViewingItem(newData);
      setSelectedItem(newData as CatalogItem);
    } catch {
      /* ignore */
    }
  };

  const handleViewItem = async (
    item: CatalogItem,
    opts?: { itemTab?: string; sessionId?: string },
  ) => {
    if (item.item_type === 'folder.account') return;
    setIsBreadcrumbLocked(false);

    // Doc items are in-memory only — skip API fetch
    if (isDocItem(item.laui)) {
      markNavigatedInAppRef.current?.(item.laui);
      void navigate({
        to: '/path',
        search: {
          itemtype: item.item_type ?? '',
          itemname: item.name ?? '',
          laui: item.laui,
        },
      });
      // Only add doc.file items to the tab bar, not folders
      if (item.item_type === 'doc.file') {
        addTab({
          laui: item.laui,
          name: item.name ?? '',
          item_type: item.item_type ?? '',
          source: 'browse',
        });
      }
      const content = getDocContent(item.laui);
      const docFullItem = { ...item, data: { name: item.name, description: content ?? '' } };
      setFormMode('view');
      setViewingItem(docFullItem);
      setSelectedItem(docFullItem as CatalogItem);
      setIsEditorActive(false);
      return;
    }

    try {
      markNavigatedInAppRef.current?.(item.laui);
      void navigate({
        to: '/path',
        search: (prev: any) => {
          const next: any = {
            itemtype: item.item_type ?? '',
            itemname: item.name ?? '',
            laui: item.laui,
          };
          // Preserve tab (and sessionId for logs) when navigating to the same item
          // (e.g. deep link resolution). Clear them when switching to a different item.
          if (prev.laui === item.laui) {
            if (prev.tab) next.tab = prev.tab;
            if (prev.sessionId) next.sessionId = prev.sessionId;
          }
          // Explicit deep-link target (e.g. opening a specific run's logs) wins.
          if (opts?.itemTab) next.itemTab = opts.itemTab;
          if (opts?.sessionId) next.sessionId = opts.sessionId;
          return next;
        },
      });
      addTab({
        laui: item.laui,
        name: item.name ?? '',
        item_type: item.item_type ?? '',
        source: 'browse',
      });
      const fullItemData = await getCatalogItemById(item.laui, isMarketplaceCatalog);
      await loadSchemaForType(item.item_type);
      setFormMode('view');
      setViewingItem(fullItemData);
      setSelectedItem(fullItemData as CatalogItem);
      setIsEditorActive(!item.item_type.startsWith('folder'));
    } catch {
      showWarning(`Could not load full item data. Viewing with available data.`);
      await loadSchemaForType(item.item_type);
      setFormMode('view');
      setViewingItem(item);
      setSelectedItem(item);
      setIsEditorActive(!item.item_type.startsWith('folder'));
    }
  };

  const handleCancelCreate = () => {
    setCreateFilterType(null);
    setEditingItem(null);
    setFormMode('view');
    if (!viewingItem) setIsEditorActive(false);
  };

  const handleEditorReset = () => {
    setFormMode(null);
    setCreateFilterType(null);
    setEditingItem(null);
    setViewingItem(null);
    setFormSchema(null);
    setIsEditorActive(false);
  };

  const handleEditorClose = () => {
    setIsEditorActive(false);
  };

  return {
    handleCreateNewItem,
    handleEditItem,
    handleSaveItem,
    handleViewItem,
    handleCancelCreate,
    handleEditorReset,
    handleEditorClose,
  };
}
