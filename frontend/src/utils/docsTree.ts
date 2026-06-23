/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import type { CatalogNode } from '../components/browse/types';

// Dynamically import all markdown files from the docs directory
const docModules = import.meta.glob('../../../docs/**/*.md', {
  query: '?raw',
  import: 'default',
  eager: true,
});

// Helper function to convert file path to a readable name
const pathToName = (path: string): string => {
  const fileName = (path.split('/').pop()?.replace('.md', '') || '')
    // Strip a leading ordering prefix like "01-" / "02_" so folders/files
    // can be numbered for sidebar order while displaying a clean label.
    .replace(/^\d+[-_]/, '');
  // Convert kebab-case or snake_case to Title Case
  return fileName
    .split(/[-_]/)
    .map((word) => word.charAt(0).toUpperCase() + word.slice(1))
    .join(' ');
};

// Helper function to generate laui from path
const pathToLaui = (path: string, _isFolder: boolean = false): string => {
  const cleanPath = path
    .replace(/^.*\/docs\//, '')
    .replace('.md', '')
    .replace(/\//g, '-');
  return `getting-started-${cleanPath}`;
};

// Helper function to build tree structure from file paths
const buildTreeFromPaths = (): CatalogNode => {
  // Group files by directory structure
  interface FileNode {
    _isFile?: boolean;
    _path?: string;
    _content?: unknown;
    [key: string]: unknown;
  }

  const structure: { [key: string]: FileNode } = {};

  Object.keys(docModules).forEach((filePath) => {
    const relativePath = filePath.replace(/^.*\/docs\//, '');
    const parts = relativePath.split('/');

    let current: { [key: string]: FileNode } = structure;
    parts.forEach((part, index) => {
      const isFile = index === parts.length - 1;

      if (!current[part]) {
        current[part] = isFile
          ? {
              _isFile: true,
              _path: filePath,
              _content: docModules[filePath] as string | undefined,
            }
          : ({} as FileNode);
      }

      if (!isFile) {
        current = current[part] as { [key: string]: FileNode };
      }
    });
  });

  // Convert structure to CatalogNode format
  const convertToNodes = (obj: FileNode, name: string, basePath: string = ''): CatalogNode => {
    const currentPath = basePath ? `${basePath}/${name}` : name;
    const isFile = obj._isFile;

    if (isFile) {
      return {
        item: {
          laui: pathToLaui(currentPath, false),
          name: pathToName(name),
          item_type: 'doc.file',
          permission: 'view',
          data: {
            name: pathToName(name),
            description: obj._content as string,
          },
        },
        children: [],
        parents: [],
      };
    }

    // It's a folder
    const children: CatalogNode[] = [];
    Object.keys(obj).forEach((key) => {
      if (!key.startsWith('_')) {
        const value = obj[key];
        if (value && typeof value === 'object' && !Array.isArray(value)) {
          children.push(convertToNodes(value as FileNode, key, currentPath));
        }
      }
    });

    // Sort children: folders first, then files, alphabetically within each group
    children.sort((a, b) => {
      const aIsFolder = a.item.item_type === 'doc.folder';
      const bIsFolder = b.item.item_type === 'doc.folder';

      if (aIsFolder && !bIsFolder) return -1;
      if (!aIsFolder && bIsFolder) return 1;
      return a.item.name.localeCompare(b.item.name);
    });

    return {
      item: {
        laui: pathToLaui(currentPath, true),
        name: pathToName(name),
        item_type: 'doc.folder',
        permission: 'view',
      },
      children,
      parents: [],
    };
  };

  // Build the root node
  const rootChildren: CatalogNode[] = [];
  Object.keys(structure).forEach((key) => {
    rootChildren.push(convertToNodes(structure[key], key));
  });

  // Sort root children
  rootChildren.sort((a, b) => {
    const aIsFolder = a.item.item_type === 'doc.folder';
    const bIsFolder = b.item.item_type === 'doc.folder';

    if (aIsFolder && !bIsFolder) return -1;
    if (!aIsFolder && bIsFolder) return 1;
    // Sort by laui (keeps the numeric NN- ordering prefix) so the sidebar
    // follows the learning journey even though display names hide the number.
    return a.item.laui.localeCompare(b.item.laui);
  });

  return {
    item: {
      laui: 'getting-started-root',
      name: 'getting_started',
      item_type: 'doc.folder',
      permission: 'view',
      is_root: true,
    },
    children: rootChildren,
    parents: [],
  };
};

// Documentation tree structure - now dynamically generated
export const getDocsTree = (): CatalogNode => {
  return buildTreeFromPaths();
};

// Helper to check if an item is a documentation item
export const isDocItem = (laui: string): boolean => {
  return laui.startsWith('getting-started-');
};

// Single "Getting Started" file node for the sidebar
export const getGettingStartedNode = (): CatalogNode => {
  const filePath = '../../../docs/getting_started.md';
  const content = docModules[filePath] as string | undefined;
  return {
    item: {
      laui: 'getting-started-getting_started',
      name: 'Getting Started',
      item_type: 'doc.file',
      permission: 'view',
      data: {
        name: 'Getting Started',
        description: content ?? '',
      },
    },
    children: [],
    parents: [],
  };
};

// Helper to get doc content from laui
export const getDocContent = (laui: string): string | null => {
  const tree = getDocsTree();

  const findContent = (node: CatalogNode): string | null => {
    if (node.item.laui === laui && node.item.data) {
      const data = node.item.data as { name?: string; description?: string };
      // The markdown content is stored in the description field
      if (data.description) {
        return data.description;
      }
    }

    if (node.children) {
      for (const child of node.children) {
        const content = findContent(child);
        if (content) return content;
      }
    }

    return null;
  };

  return findContent(tree);
};
