# Copyright (c) 2026 LeastAction Labs, Inc.
# This file is part of LeastAction and is licensed under the
# LeastAction Sustainable Use License (see LICENSE.md) or, for files
# marked EE, the LeastAction Enterprise Edition License (see LICENSE_EE.md).
# Use of this file outside those terms is not permitted.
from __future__ import annotations

from bson import ObjectId
from pydantic import BaseModel

from src.core.catalog.item.schema import ItemProjection
from src.core.catalog.link.schema import LinkWithPermission


class ItemDirectory:
    """
    The item directory is levelled tree of item lauis that gets filled with
    real item objects using the fill_items method
    Flow:
    - Initialize with root item lauis
    - Add a new level of item_lauis using the add_level method
    - Get all the item lauis in the directory using the get_flattened_lauis method
    - Fill the item directory with item objects using the fill_items method
    """

    def __init__(self, root_nodes: list[tuple[ObjectId, Permission]]):
        if len(root_nodes) == 0:
            raise Exception("Root nodes are empty")
        self._dir: list[dict[ObjectId, ItemDirectoryIDNode]] = [
            {
                item_laui: ItemDirectoryIDNode(item_laui, permission)
                for item_laui, permission in root_nodes
            }
        ]
        self.current_level = 0

    def get_flattened_lauis(self) -> set[ObjectId]:
        """
        Get all the item lauis in the directory
        There could be duplicate item lauis in the directory, so we return a set
        Returns:
            Set of item lauis
        """
        return {item_laui for level in self._dir for item_laui in level.keys()}

    def add_child_level(self, links: list[LinkWithPermission]):
        """
        Pass the new links that are children of the current level item lauis
        For example:
        All Items = [item1->[item2, item3], item2->[item4, item5->[item6, item7]]]
        The root_nodes = [item1, item2]
        The first level links = [item2,item3,item4,item5] (Children of item1 and item2)
        The second level links = [item6,item7] (Children of item5)
        """
        for link in links:
            if link.parent_laui is None:
                continue
            if link.parent_laui not in self._dir[self.current_level]:
                raise Exception(
                    f"Parent {link.parent_laui} not found in current level for link {link} at level {self.current_level}"
                )
            self._dir[self.current_level][link.parent_laui].add_child(
                ItemDirectoryIDNode(link.child_laui, link.permission)
            )
        self._dir.append(
            {
                link.child_laui: ItemDirectoryIDNode(link.child_laui, link.permission)
                for link in links
            }
        )
        self.current_level += 1

    def add_parent_level(self, links: list[LinkWithPermission]):
        """
        Pass the new links that are children of the current level item lauis
        For example:
        All Items = [item1->[item2, item3], item2->[item4, item5->[item6, item7]]]
        The root_nodes = [item1, item2]
        The first level links = [item2,item3,item4,item5] (Children of item1 and item2)
        The second level links = [item6,item7] (Children of item5)
        """
        for link in links:
            if link.parent_laui is None:
                continue
            if link.child_laui not in self._dir[self.current_level]:
                raise Exception(
                    f"Child {link.child_laui} not found  at level {self.current_level} for link {link} "
                )
            self._dir[self.current_level][link.child_laui].add_parent(
                ItemDirectoryIDNode(link.parent_laui, link.permission)
            )
        self._dir.append(
            {
                link.parent_laui: ItemDirectoryIDNode(link.parent_laui, link.permission)
                for link in links
                if link.parent_laui
            }
        )
        self.current_level += 1

        # self._dir_level.append(nodes)

    def fill_items(self, item_dict: dict[ObjectId, ItemProjection]) -> list[ItemDirectoryItemNode]:
        """
        Fill the item directory with item objects using the item_dict
        Args:
            item_dict: Dictionary of item lauis and item objects

        Returns:
            List of ItemDirectoryItemNodes
        """

        def _fill_at_level(laui: ObjectId, permission: Permission, level: int):
            if level == len(self._dir):
                return None
            item = item_dict.get(laui)
            if item is None:
                # The link points to an item that no longer exists (a dangling
                # link, e.g. left by a hard-deleted child). Skip it rather than
                # failing the whole listing.
                return None
            item.permission = permission
            item_node = ItemDirectoryItemNode(item=item)
            for node in self._dir[level][laui].children:
                child = _fill_at_level(node.item_laui, node.permission, level + 1)
                if child is not None:
                    item_node.children.append(child)
            for node in self._dir[level][laui].parents:
                parent = _fill_at_level(node.item_laui, node.permission, level + 1)
                if parent is not None:
                    item_node.parents.append(parent)
            return item_node

        filled_root_items: list[ItemDirectoryItemNode] = []
        for laui, item_id_node in self._dir[0].items():
            filled = _fill_at_level(laui, item_id_node.permission, 0)
            # a missing root (dangling link) is skipped, not fatal — the rest of
            # the page still lists.
            if filled is not None:
                filled_root_items.append(filled)
        return filled_root_items

    def __str__(self):
        lines = [
            f"ItemDirectory(current_level={self.current_level}, total_levels={len(self._dir)})"
        ]
        for i, level_dict in enumerate(self._dir):
            lines.append(f"  Level {i}: ({len(level_dict)} items)")
            for obj_laui, node in level_dict.items():
                children_str = (
                    f"children=[{', '.join(str(c.item_laui) for c in node.children)}]"
                    if node.children
                    else "children=[]"
                )
                parents_str = (
                    f"parents=[{', '.join(str(p.item_laui) for p in node.parents)}]"
                    if node.parents
                    else "parents=[]"
                )
                lines.append(
                    f"    {obj_laui} (perm={node.permission}) -> {children_str}, {parents_str}"
                )
        return "\n".join(lines)


from src.core.ee.keto.schema import Permission


class ItemDirectoryIDNode:
    def __init__(self, item_laui: ObjectId, permission: Permission):
        self.item_laui: ObjectId = item_laui
        self.permission: Permission = permission
        self.parents: list[ItemDirectoryIDNode] = []
        self.children: list[ItemDirectoryIDNode] = []

    def add_child(self, child: ItemDirectoryIDNode):
        self.children.append(child)

    def add_parent(self, parent: ItemDirectoryIDNode):
        self.parents.append(parent)

    """
    The string representation is for debugging purposes only
    """

    def __str__(self):
        children_lauis = [str(child.item_laui) for child in self.children] if self.children else []
        parents_lauis = [str(parent.item_laui) for parent in self.parents] if self.parents else []
        return (
            f"ItemDirectoryIDNode(laui={self.item_laui}, perm={self.permission}, "
            f"children=[{', '.join(children_lauis)}], parents=[{', '.join(parents_lauis)}])"
        )

    def __repr__(self):
        return self.__str__()


class ItemDirectoryItemNode(BaseModel):
    item: ItemProjection
    children: list[ItemDirectoryItemNode] = []
    parents: list[ItemDirectoryItemNode] = []

    def __str__(self, depth=0, max_depth=10):
        """
        Recursive string representation showing full tree structure
        Args:
            depth: Current depth level for indentation
            max_depth: Maximum depth to prevent infinite recursion
        """
        if depth >= max_depth:
            return f"{'  ' * depth}... (max depth reached)"

        indent = "  " * depth
        item_laui = getattr(self.item, "laui", str(self.item))
        item_name = getattr(self.item, "name", "unnamed")
        perm = getattr(self.item, "permission", "no_perm")

        lines = [f"{indent}ItemNode(laui={item_laui}, name={item_name}, perm={perm})"]

        # Show children
        if self.children:
            lines.append(f"{indent}  Children ({len(self.children)}):")
            for child in self.children:
                child_str = child.__str__(depth=depth + 2, max_depth=max_depth)
                lines.append(child_str)

        # Show parents
        if self.parents:
            lines.append(f"{indent}  Parents ({len(self.parents)}):")
            for parent in self.parents:
                parent_str = parent.__str__(depth=depth + 2, max_depth=max_depth)
                lines.append(parent_str)

        return "\n".join(lines)

    def __repr__(self):
        return self.__str__()
