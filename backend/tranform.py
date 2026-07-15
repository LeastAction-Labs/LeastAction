import ast
import sys


class CoreEEPurger(ast.NodeTransformer):

    def __init__(self):
        self.target_prefix = "src.core.ee"
        # Foundational terms we want to eliminate completely
        self.bound_names = {"access_reader", "AccessReader", "Permission", "permission"}

    def _should_purge_module(self, module_name):
        if not module_name:
            return False
        return (
            module_name == self.target_prefix
            or module_name.startswith(self.target_prefix + ".")
        )

    # ==========================================
    # IMPORT TRACKING
    # ==========================================

    def visit_Import(self, node):
        remaining_aliases = []
        for alias in node.names:
            if self._should_purge_module(alias.name):
                self.bound_names.add(alias.asname or alias.name.split(".")[-1])
            else:
                remaining_aliases.append(alias)
        if not remaining_aliases:
            return None
        node.names = remaining_aliases
        return node

    def visit_ImportFrom(self, node):
        if self._should_purge_module(node.module):
            for alias in node.names:
                self.bound_names.add(alias.asname or alias.name)
            return None
        return node

    def _contains_bound_name(self, node):
        if not node:
            return False
        node_str = ast.unparse(node).strip()
        if node_str in self.bound_names:
            return True
        return any(
            f" {name}" in f" {node_str}" or name in node_str
            for name in self.bound_names
        )

    # ==========================================
    # DATA STRUCTURE TRANSFORMATIONS
    # ==========================================

    def visit_Tuple(self, node):
        """Reduces 2-element tuples in data structures if one is an EE component."""
        self.generic_visit(node)

        # Only modify tuples used as actual data values (Load), not as assignment targets (Store)
        if hasattr(node, "ctx") and isinstance(node.ctx, ast.Load):
            if len(node.elts) == 2:
                is_ee_0 = self._contains_bound_name(node.elts[0])
                is_ee_1 = self._contains_bound_name(node.elts[1])

                # If one element is EE, return just the safe element, stripping the tuple wrapper
                if is_ee_1 and not is_ee_0:
                    return node.elts[0]
                elif is_ee_0 and not is_ee_1:
                    return node.elts[1]

        return node

    def visit_Subscript(self, node):
        """Transforms type hints like tuple[Safe, EE] -> Safe."""
        self.generic_visit(node)

        if isinstance(node.value, ast.Name) and node.value.id in ('tuple', 'Tuple'):
            slice_elts = []
            if isinstance(node.slice, ast.Tuple):
                slice_elts = node.slice.elts
            elif hasattr(node.slice, "value") and isinstance(node.slice.value, ast.Tuple):
                slice_elts = node.slice.value.elts

            if len(slice_elts) == 2:
                is_ee_0 = self._contains_bound_name(slice_elts[0])
                is_ee_1 = self._contains_bound_name(slice_elts[1])

                if is_ee_1 and not is_ee_0:
                    return slice_elts[0]
                elif is_ee_0 and not is_ee_1:
                    return slice_elts[1]

        return node

    # ==========================================
    # BLOCK CLEANUP LOGIC & LOOP UNPACKING
    # ==========================================

    def _clean_block(self, node):
        self.generic_visit(node)
        if hasattr(node, "body") and isinstance(node.body, list):
            if not node.body:
                return None
        return node

    def visit_For(self, node):
        if isinstance(node.target, ast.Tuple):
            elts = node.target.elts
            if len(elts) == 2:
                is_ee_0 = self._contains_bound_name(elts[0])
                is_ee_1 = self._contains_bound_name(elts[1])

                if is_ee_1 and not is_ee_0:
                    node.target = elts[0]
                    self.bound_names.add(ast.unparse(elts[1]).strip())
                elif is_ee_0 and not is_ee_1:
                    node.target = elts[1]
                    self.bound_names.add(ast.unparse(elts[0]).strip())

        return self._clean_block(node)

    def visit_AsyncFor(self, node): return self.visit_For(node)
    def visit_While(self, node): return self._clean_block(node)
    def visit_With(self, node): return self._clean_block(node)
    def visit_AsyncWith(self, node): return self._clean_block(node)

    def visit_If(self, node):
        self.generic_visit(node)
        if not node.body:
            if not getattr(node, "orelse", None):
                return None
            else:
                node.body = [ast.Pass()]
        return node

    # ==========================================
    # ASSIGNMENT & EXPRESSION LOGIC
    # ==========================================

    def visit_FunctionDef(self, node):
        node.args.args = [
            arg for arg in node.args.args
            if arg.arg not in self.bound_names
            and (not arg.annotation or ast.unparse(arg.annotation) not in self.bound_names)
        ]
        if hasattr(node.args, "kwonlyargs"):
            node.args.kwonlyargs = [
                arg for arg in node.args.kwonlyargs
                if arg.arg not in self.bound_names
            ]

        self.generic_visit(node)
        if not node.body:
            node.body = [ast.Pass()]
        return node

    def _handle_purge_logic(self, target_nodes, value_node):
        if self._contains_bound_name(value_node):
            for target in target_nodes:
                target_str = ast.unparse(target).strip()
                self.bound_names.add(target_str)
                if isinstance(target, ast.Attribute):
                    self.bound_names.add(target.attr)
            return None

        if any(self._contains_bound_name(t) for t in target_nodes):
            return None

        return True

    def visit_Assign(self, node):
        # 1. PRE-VISIT: Allow data structures (like tuples inside lists) to safely reduce themselves first
        if node.value:
            node.value = self.visit(node.value)

        # 2. CHECK: If the value STILL contains an EE dependency after reduction, wipe the line
        result = self._handle_purge_logic(node.targets, node.value)
        if result is None:
            return None

        return self.generic_visit(node)

    def visit_AnnAssign(self, node):
        if node.value:
            node.value = self.visit(node.value)

        result = self._handle_purge_logic([node.target], node.value)
        if result is None:
            return None

        return self.generic_visit(node)

    def visit_Expr(self, node):
        if self._contains_bound_name(node.value):
            return None
        return self.generic_visit(node)


def purge_ee_from_file(source_path, dest_path):
    try:
        with open(source_path, "r", encoding="utf-8") as f:
            source_code = f.read()

        tree = ast.parse(source_code)
        purger = CoreEEPurger()
        modified_tree = purger.visit(tree)
        ast.fix_missing_locations(modified_tree)

        clean_code = ast.unparse(modified_tree)

        with open(dest_path, "w", encoding="utf-8") as f:
            f.write(clean_code)

        print(f"Successfully processed {source_path}")

    except Exception as e:
        print(f"An error occurred: {e}")


if __name__ == "__main__":
    x = "src/core/catalog/service.py"
    purge_ee_from_file(x, f"../../LeastAction-Lite-POC/backend/{x}")
