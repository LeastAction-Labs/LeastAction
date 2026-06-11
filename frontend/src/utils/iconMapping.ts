/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
/**
 * Icon Mapping Utility
 * Maps icon name strings from schema configs to actual MUI icon components
 */
import {
  Build as BuildIcon,
  Cloud as CloudIcon,
  InsertDriveFile as DocumentIcon,
  FlashOn as FlashOnIcon,
  Folder as FolderIcon,
  Memory as MemoryIcon,
  SettingsApplications as SettingsApplicationsIcon,
  Storage as StorageIcon,
  Task as TaskIcon,
} from '@mui/icons-material';

// Map of icon names to MUI icon components
const ICON_MAP: Record<string, React.ComponentType<any>> = {
  Folder: FolderIcon,
  InsertDriveFile: DocumentIcon,
  Build: BuildIcon,
  Storage: StorageIcon,
  Memory: MemoryIcon,
  FlashOn: FlashOnIcon,
  Cloud: CloudIcon,
  Task: TaskIcon,
  SettingsApplications: SettingsApplicationsIcon,
};

/**
 * Get MUI icon component by name
 * @param iconName - Name of the icon (e.g., "Build", "Storage")
 * @returns MUI icon component or default DocumentIcon
 */
export function getIconComponent(iconName: string): React.ComponentType<any> {
  return ICON_MAP[iconName] || DocumentIcon;
}

/**
 * Get all available icon names
 * @returns Array of icon names
 */
export function getAvailableIcons(): string[] {
  return Object.keys(ICON_MAP);
}
