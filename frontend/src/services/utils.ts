/*
 * Copyright (c) 2026 LeastAction Labs, Inc.
 * This file is part of LeastAction and is licensed under the
 * LeastAction Sustainable Use License (see LICENSE.md) or, for files
 * marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
 * Use of this file outside those terms is not permitted.
 */
import { getSchemaColumns } from './schema.service';

// Helper function to remove properties with empty strings recursively
function removeEmptyStrings(obj: any): any {
  if (obj === null || obj === undefined) {
    return obj;
  }

  if (Array.isArray(obj)) {
    return obj.map((item) => removeEmptyStrings(item));
  }

  if (typeof obj === 'object') {
    const result: any = {};
    for (const key in obj) {
      if (Object.prototype.hasOwnProperty.call(obj, key)) {
        const value = obj[key];
        // Skip properties with empty string values
        if (value === '') {
          continue;
        }
        result[key] = value;
      }
    }
    return result;
  }

  return obj;
}

// Helper function to parse string values to objects based on schema
async function parseFieldsBySchema(itemData: any, itemType: string): Promise<any> {
  try {
    // Get schema columns for the item type
    const columns = await getSchemaColumns(itemType);

    // Create a map of column names to their datatypes for quick lookup
    const schemaMap = new Map<string, string>();
    columns.forEach((col) => {
      schemaMap.set(col.name, col.datatype.toLowerCase());
    });

    // Process each field in itemData
    const result: any = {};
    for (const key in itemData) {
      if (Object.prototype.hasOwnProperty.call(itemData, key)) {
        const value = itemData[key];
        const expectedType = schemaMap.get(key);

        // If schema expects an object and value is a string, try to parse it
        if (
          ['object', 'array'].includes(expectedType || '') &&
          typeof value === 'string' &&
          value.trim() !== ''
        ) {
          try {
            result[key] = JSON.parse(value);
          } catch (e) {
            console.warn(`Failed to parse field "${key}" as JSON object:`, e);
            // Keep the original value if parsing fails
            result[key] = value;
          }
        } else {
          result[key] = value;
        }
      }
    }

    return result;
  } catch (error) {
    console.error('Error parsing fields by schema:', error);
    // Return original data if schema loading fails
    return itemData;
  }
}

export const preprocessItemData = async (itemData: any) => {
  const itemType = itemData.item_type || itemData.itemType;

  let processedData = itemData;

  // Parse string values to objects based on schema if item type is available
  if (itemType) {
    processedData = await parseFieldsBySchema(itemData, itemType);
  }

  // Remove empty strings
  return removeEmptyStrings(processedData);
};

export const createPK = (uniqueConstraintsDict: any): string => {
  if (!uniqueConstraintsDict || typeof uniqueConstraintsDict !== 'object') {
    return '';
  }
  const sortedKeys = Object.keys(uniqueConstraintsDict).sort();
  const values = sortedKeys.map((key) => uniqueConstraintsDict[key]);
  return values.join('-');
};
