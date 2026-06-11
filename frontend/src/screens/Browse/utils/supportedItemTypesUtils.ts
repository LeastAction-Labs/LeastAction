/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
/**
 * Process supported types for display
 *
 * Groups all folder.* types into a single "Folders" chip
 * Other types are shown as separate chips
 *
 * Example:
 *   Input: ["folder.root", "folder.nested", "action", "connection"]
 *   Output: [
 *     { display: "Folders", actualType: "folder.root", isFolderGroup: true },
 *     { display: "action", actualType: "action", isFolderGroup: false },
 *     { display: "connection", actualType: "connection", isFolderGroup: false }
 *   ]
 */
export type ProcessedType = {
  display: string;
  actualType: string;
  isFolderGroup: boolean;
};

export function processSupportedTypes(supportedTypes: string[]): ProcessedType[] {
  const folderTypes: string[] = [];
  const otherTypes: string[] = [];

  supportedTypes.forEach((type) => {
    if (type.toLowerCase().startsWith('folder.')) {
      folderTypes.push(type);
    } else {
      otherTypes.push(type);
    }
  });

  const result: ProcessedType[] = [];

  // Add grouped folder type if any exist
  // Use first folder type for API call (all folder types return same children)
  if (folderTypes.length > 0) {
    result.push({
      display: 'Folders',
      actualType: folderTypes[0],
      isFolderGroup: true,
    });
  }

  // Add other types as-is
  otherTypes.forEach((type) => {
    result.push({
      display: type,
      actualType: type,
      isFolderGroup: false,
    });
  });

  return result;
}
