# LeastAction Access & Permissions — Guide

LeastAction uses item-level permissions. Every item in the catalog (operator, connection, payload, action, config, workflow folder, task, skill) has its own access control. Permissions are granted to individual users or groups.

---

## Permission Levels

| Level | What it allows |
|---|---|
| `view` | Read the item and its contents |
| `edit` | View and modify the item |
| `own` | Edit the item and manage its permissions (share with others) |

You can only grant a permission level up to your own. An `edit` user cannot grant `own`.

---

## Sharing an Item

Open any item in the catalog and click **Share**. The share dialog lets you grant access to a **user** (by email) or a **group** (by group name).

**Steps:**
1. Choose entity type: **User** or **Group**
2. Enter the user email or group name and click **Confirm**
3. The dialog shows the entity's current permission on this item
4. Select the new permission level from the dropdown
5. Click **Share**

The new permission takes effect immediately. Access applies to the selected item and all child items beneath it in the catalog hierarchy.

**Who can share?** Only users with `edit` or `own` permission on the item. Owners can grant any level including `own`; editors can grant up to `edit`.

---

## Groups

Groups let you manage access for teams without granting permissions to each user individually. A permission granted to a group applies to all members of that group.

**To share with a group:** In the Share dialog, set entity type to **Group** and enter the group name.

Groups are managed from the admin area. See the API reference (`09-group.md`) for creating and managing groups programmatically.

---

## Permission Inheritance

Permissions set on a folder apply to all items inside that folder. If a user has `view` on a workflow folder, they can see all tasks inside it.

This makes it straightforward to lock down an entire workflow: share the workflow folder with the right users/groups and all tasks inside inherit that access.

---

## Connection-Operator Enforcement

The `enforce_connection_operator_mapping: true` flag in `config/system.yml` controls whether operator-connection subtype pairs are validated at task creation. This is separate from item permissions — it is a system-wide policy, not per-item access control. See [Config Guide](/path?laui=getting-started-advanced-task_managment-config&itemtype=doc.file&itemname=Config) for details.
