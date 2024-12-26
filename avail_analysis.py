import os
import ast

from typing import Generator
from collections import defaultdict
from scalpel.core.util import UnitWalker


class Analyzer:
    def __init__(self, package: str):
        self.package = package
        self.ast_walker: dict[str, Generator] = {}

        self.import_busy: dict[str, int] = defaultdict(int)
        self.external_libs: defaultdict[str, list[tuple[str, int]]] = defaultdict(list)
        self.avail_nodes: defaultdict[str, list[tuple[str, str, ast.AST]]] = defaultdict(list)

    def source_to_ast(self, path: str):
        if path not in self.ast_walker:
            with open(path) as file:
                src = file.read()

            module_node = ast.parse(src)

            # ---------------------------------------------
            # | I first leveraged UnitWalker from scalpel |
            # | but it doesn't work too well since I only |
            # | consider defs and imports at module level |
            # ---------------------------------------------
            # self.ast_walker[path] = UnitWalker(module_node)

            # -------------------------------------------------------
            # | So I tried this instead, but I don't like it though |
            # -------------------------------------------------------
            self.ast_walker[path] = iter(module_node.body)


    def _new_node_via_assignment(self, mod: str, node: ast.AST):
        if isinstance(node, list):
            for sub_node in node:
                self._new_node_via_assignment(mod, sub_node)
        elif isinstance(node, ast.Name):
            self.avail_nodes[mod].append((node.id, mod, node))
        elif isinstance(node, ast.Tuple):
            for sub_node in node.elts:
                self._new_node_via_assignment(mod, sub_node)
        else:
            raise Exception(
                f"`_new_node_via_assignment` got "
                f"unexpected argument `node` of type `{type(node)}`"
            )
        
    def _mod_to_path(self, mod: str):
        return os.path.join(self.package, mod.replace('.', '/') + '.py')
    
    def _path_to_mod(self, path: str):
        return os.path.splitext(os.path.relpath(path, self.package))[0].replace('/', '.')
    
    def _get_avail_node(self, mod: str, node_name: str):
        for e in reversed(self.avail_nodes[mod]):
            if e[0] == node_name:
                return (e[1], e[2])
        return None
    
    def _get_external_lib(self, mod: str, lib_name: str):
        for e in reversed(self.external_libs[mod]):
            if e[0] == lib_name:
                return e[1]
        return None

    def analyze(self, path: str):
        analyzer.source_to_ast(path)
        root_mod = self._path_to_mod(path)

        # busy = do nothing
        if self.import_busy[root_mod] > 0: return

        for unit in self.ast_walker[path]:
            node = unit # .node if using UnitWalker

            # AST nodes that create new available elements
            if isinstance(node, (ast.FunctionDef, ast.ClassDef)):
                self.avail_nodes[root_mod].append((node.name, root_mod, node))
            elif isinstance(node, ast.Assign):
                self._new_node_via_assignment(root_mod, node.targets)
            elif isinstance(node, ast.AugAssign):
                self._new_node_via_assignment(root_mod, node.target)

            # ast.Import node import elements from a (mayble partially) mod
            elif isinstance(node, ast.Import):
                self.import_busy[root_mod] += 1
                for mod_name in node.names:
                    mod_name = mod_name.name
                    mod_path = self._mod_to_path(mod_name)
                    if not os.path.isfile(mod_path):
                        self.external_libs[root_mod].append((mod_name, node.lineno))
                    else:
                        self.analyze(mod_path)
                        self.avail_nodes[root_mod].extend(
                            (f"{mod_name}.{sub_node[0]}", sub_node[1], sub_node[2])
                            for sub_node in self.avail_nodes[mod_name]
                        )
                        self.external_libs[root_mod].extend(
                            (f"{mod_name}.{sub_node[0]}", sub_node[1])
                            for sub_node in self.external_libs[mod_name]
                        )
                self.import_busy[root_mod] -= 1

            # ast.ImportFrom import a specified element by reading
            # everything from the beginning of the mod til the required element
            elif isinstance(node, ast.ImportFrom):
                self.import_busy[root_mod] += 1
                mod_name = node.module
                mod_path = self._mod_to_path(mod_name)

                if not os.path.isfile(mod_path):
                    self.external_libs[root_mod].append((mod_name, node.lineno))
                    for sub_node in node.names:
                        self.avail_nodes[root_mod].append((
                            sub_node.name, mod_name,
                            ast.Import([ast.alias(mod_name)], lineno=node.lineno)
                        ))
                else:
                    self.analyze(mod_path)

                    for sub_node in node.names:
                        sub_node_name = sub_node.name
                        sub_node = self._get_avail_node(mod_name, sub_node_name)
                        sub_lib = self._get_external_lib(mod_name, sub_node_name)
                        if sub_node and (not sub_lib or sub_node[1].lineno > sub_lib):
                            self.avail_nodes[root_mod].append((
                                sub_node_name,
                                sub_node[0],
                                ast.Import([ast.alias(mod_name)], lineno=node.lineno)
                            ))
                        elif sub_lib:
                            self.external_libs[root_mod].append((sub_node_name, sub_lib))
                        else:
                            err = f"`{mod_name}: from {mod_name} import {sub_node_name}` failed."
                            err += f"\nReason: Node {sub_node_name} not found in "
                            try:
                                next(self.ast_walker[mod_path])
                            except StopIteration:
                                err += f"partially imported {mod_path}."
                            else:
                                err += f"{mod_path}."
                            finally:
                                raise Exception(err)
                    
                self.import_busy[root_mod] -= 1


if __name__ == "__main__":
    selected_test = "test_3"
    package = os.path.join("./test-repo", selected_test)
    path = os.path.join(package, "input", "__main__.py")

    analyzer = Analyzer(package)

    analyzer.analyze(path)

    todo_paths = list(analyzer.ast_walker.keys())
    for path in todo_paths:
        analyzer.analyze(path)
        for path in analyzer.ast_walker.keys():
            if path not in todo_paths:
                todo_paths.append(path)

    for path in todo_paths:
        print(mod := analyzer._path_to_mod(path))
        print("│")
        print(f"├── Available nodes:")
        for node_name, node_source, node in analyzer.avail_nodes[mod]:
            print(f"│   > {node_name} ({node_source}): {node.lineno}")
        print("│")
        
        print(f"└── External libs:")
        for lib_name, lib_lineno in analyzer.external_libs[mod]:
            print(f"    > {lib_name}: {lib_lineno}")

        print()