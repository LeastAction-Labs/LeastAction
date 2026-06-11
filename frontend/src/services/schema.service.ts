/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
// services/schema.service.ts
/**
 * Schema Service - Loads and manages schema definitions from JSON files
 */

export type SchemaColumn = {
  name: string;
  datatype: string;
  required?: boolean;
  min_length?: number;
  max_length?: number;
  regex?: string;
  description?: string;
  default?: unknown;
  items?: string;
};

export type EnumColorConfig = {
  [enumValue: string]: string; // enum value -> color hex code
};

export type ProjectionFieldConfig = {
  display_type?: 'status_icon' | 'text' | 'badge';
  enum_colors?: EnumColorConfig;
};

export type ProjectionFieldsConfig = {
  [fieldName: string]: ProjectionFieldConfig;
};

export type ItemTypeVisualConfig = {
  icon: string; // MUI icon name
  color: string; // Hex color code
};

export type Schema = {
  columns: SchemaColumn[];
  projection_fields?: string[];
  ui_preview_fields?: string[];
  form_excluded_fields?: string[];
  projection_fields_config?: ProjectionFieldsConfig;
  item_type_visual_config?: ItemTypeVisualConfig;
  unique_constraints?: string[];
  indexes?: unknown[];
  validation_rules?: unknown[];
  user_update_fields?: string[];
};

// Dynamically import all schema files from config/schema/
const schemaModules = import.meta.glob('../../../config/schema/*.json', { eager: true });

const SCHEMA_CACHE = new Map<string, Schema>();

// Dynamic schema map populated from imported modules
const SCHEMA_MAP: Record<string, Schema> = Object.entries(schemaModules).reduce(
  (map, [path, module]) => {
    // Extract schema name from path (e.g., '../../../config/schema/action.json' -> 'action')
    const fileName = path.split('/').pop()?.replace('.json', '');
    if (fileName) {
      map[fileName] = module as Schema;
    }
    return map;
  },
  {} as Record<string, Schema>,
);

// Available types for validation
export const AVAILABLE_TYPES = Object.keys(SCHEMA_MAP);

/**
 * Maps item type to schema file name
 */
function getSchemaBaseType(itemType: string): string {
  // Handle all folder types (folder.standard, folder.*) -> "folder"
  if (itemType.startsWith('folder.')) {
    return 'folder';
  }
  return itemType.split('.')[0].toLowerCase();
}

/**
 * Check if a schema exists for the given type
 */
export function schemaExists(itemType: string): boolean {
  const baseType = getSchemaBaseType(itemType);
  return Object.prototype.hasOwnProperty.call(SCHEMA_MAP, baseType);
}

/**
 * Loads a schema file directly from config/schema/ folder
 */
export function loadSchema(itemType: string): Promise<Schema | null> {
  // Check cache first
  if (SCHEMA_CACHE.has(itemType)) {
    return Promise.resolve(SCHEMA_CACHE.get(itemType)!);
  }

  try {
    const baseType = getSchemaBaseType(itemType);

    if (!SCHEMA_MAP[baseType]) {
      console.warn(`Schema file not found for type: ${itemType} (base: ${baseType})`);

      // Try to find a fallback schema
      if (baseType.startsWith('folder')) {
        //console.log('Using folder schema as fallback for', itemType);
        return Promise.resolve(SCHEMA_MAP['folder']);
      }

      return Promise.resolve(null);
    }

    const schema = SCHEMA_MAP[baseType];
    SCHEMA_CACHE.set(itemType, schema);

    //console.log(`Loaded schema for ${itemType}:`, schema);
    return Promise.resolve(schema);
  } catch (error) {
    console.error(`Error loading schema for type ${itemType}:`, error);
    return Promise.resolve(null);
  }
}

/**
 * Gets columns for a given item type
 */
export async function getSchemaColumns(itemType: string): Promise<SchemaColumn[]> {
  const schema = await loadSchema(itemType);
  return schema?.columns || [];
}

export async function getSchemaProjectionFields(itemType: string): Promise<string[]> {
  const schema = await loadSchema(itemType);
  return schema?.projection_fields || [];
}

export async function getSchemaUiPreviewFields(itemType: string): Promise<string[]> {
  const schema = await loadSchema(itemType);
  return schema?.ui_preview_fields ?? schema?.projection_fields ?? [];
}

/**
 * Gets the projection fields configuration for a given item type
 */
export async function getProjectionFieldsConfig(
  itemType: string,
): Promise<ProjectionFieldsConfig | null> {
  const schema = await loadSchema(itemType);
  return schema?.projection_fields_config || null;
}

/**
 * Gets the item type visual configuration for a given item type
 */
export async function getItemTypeVisualConfig(
  itemType: string,
): Promise<ItemTypeVisualConfig | null> {
  const schema = await loadSchema(itemType);
  return schema?.item_type_visual_config || null;
}

/**
 * Gets the full schema for a given item type
 */
export async function getSchema(itemType: string): Promise<Schema | null> {
  return loadSchema(itemType);
}

export async function getUniqueConstraints(itemType: string): Promise<string[]> {
  const schema = await loadSchema(itemType);
  const unique_constraints = schema?.unique_constraints || [];
  return unique_constraints.map((u) => u.trim());
}

/**
 * Gets table columns to display for a given item type
 * Returns ALL columns from the schema file
 */
export async function getTableColumns(itemType: string): Promise<SchemaColumn[]> {
  return await getSchemaColumns(itemType);
}

/**
 * Preload all schemas for better performance
 */
export async function preloadAllSchemas(): Promise<void> {
  const types = Object.keys(SCHEMA_MAP);
  await Promise.all(types.map((type) => loadSchema(type)));
}

/**
 * Clear schema cache (useful for development/hot reloading)
 */
export function clearSchemaCache(): void {
  SCHEMA_CACHE.clear();
}
