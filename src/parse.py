import os
import hashlib

from scalpel.cfg import CFGBuilder, CFG
from scalpel.call_graph.pycg import CallGraphGenerator
from scalpel.import_graph.import_graph import ImportGraph, Tree
from scalpel.typeinfer.typeinfer import TypeInference


def _get_folder_tree(path: str) -> dict:
    '''
    Create a folder tree from directory.
    
    Example result:
    ```
    {
        "name": <path>,
        "ext": ".",
        "children": [
            { "name": "file.py",    "ext": ".py"  },
            { "name": "file.png",   "ext": ".png" },
            { "name": "somefolder", "ext": ".", "children": [] }
        ]
    }
    ```
    '''

    name = os.path.basename(path)
    if os.path.isdir(path):
        return {
            "name": name,
            "ext": ".",
            "children": [
                _get_folder_tree(os.path.join(path, child))
                for child in os.listdir(path)
            ]
        }
    else:
        if "." not in name:
            ext = ""
        elif "." not in name[1:]:
            ext = name
        else:
            _, ext = os.path.splitext(name)
        return {
            "name": name,
            "ext": ext,
            "children": []
        }


def _construct_pyfile_children(package: str, file: str) -> dict:
    '''
    Get all functions with their respective offset (first, last).
    
    Example result:
    ```
    {
        "func_1": {
            "id": "123",
            "type": "function",
            "first": 1,
            "last": 6,
            "children": {},
        },
        "class_2": {
            "id": "456",
            "type": "class",
            "first": 7,
            "last": 10,
            "children": {
                "__init__": {
                    "id": "789",
                    "type": "class:method",
                    "first": 8,
                    "last": 10,
                    "children": {}
                }
            }
        }
    }
    ```
    '''

    cg_generator = CallGraphGenerator([file], package)
    cg_generator.analyze()

    # exclude package from file name
    name = file[len(package) + 1:]

    # exclude extension
    name, _ = os.path.splitext(name)
    name = name.replace('/', '.')

    # extract offset dict
    data = cg_generator.output_internal_mods()
    data = data[name]['methods']

    # file structure and id->obj mapping
    structure, hashmap = {}, {}

    def _build(structure, cfg, name, parent_type=''):
        class_cfgs = cfg.class_cfgs.values()
        function_cfgs = cfg.functioncfgs.values()

        for cfg in class_cfgs:
            full_name = name + '.' + cfg.name
            id = hashlib.sha256(full_name.encode()).hexdigest()
            structure[cfg.name] = {
                'id': hashlib.sha256(full_name.encode()).hexdigest(),
                'type': parent_type + ':class',
                'first': data[full_name]['first'],
                'last': data[full_name]['last'],
                'children': {}
            }
            hashmap[id] = full_name
            _build(
                structure[cfg.name]['children'],
                cfg,
                full_name,
                structure[cfg.name]['type']
            )

        for cfg in function_cfgs:
            full_name = name + '.' + cfg.name
            id = hashlib.sha256(full_name.encode()).hexdigest()
            tpe = 'method' if parent_type.split(':')[-1] == 'class' else 'function'
            structure[cfg.name] = {
                'id': hashlib.sha256(full_name.encode()).hexdigest(),
                'type': parent_type + ':' + tpe,
                'first': data[full_name]['first'],
                'last': data[full_name]['last'],
                'children': {}
            }
            hashmap[id] = full_name
            _build(
                structure[cfg.name]['children'],
                cfg,
                full_name,
                structure[cfg.name]['type']
            )

    _build(structure, CFGBuilder().build_from_file("", file), name)

    return structure, hashmap


def _include_pyfile_children(package: str, node: dict, path: str) -> None:
    if node['ext'] == ".":
        for child in node['children']:
            _include_pyfile_children(package, child, os.path.join(path, child['name']))
    elif node['ext'] == ".py" and node['name'] != '__init__.py':
        node['children'], _ = _construct_pyfile_children(package, path)


def get_full_structure(path: str):
    '''
    Same as _get_folder_tree, but now Python files
    have their own children (functions, classes, methods, ...)
    '''
    res = _get_folder_tree(path)
    _include_pyfile_children(path, res, path)
    return res


def dependency_analysis(file_paths: list[str], package: str):
    # Get call edges
    cg_generator = CallGraphGenerator(file_paths, package)
    cg_generator.analyze()
    call_edges: list[list[str, str]] = cg_generator.output_edges()

    # Get import edges
    import_graph = ImportGraph(package)
    import_graph.build_dir_tree()
    import_edges: list[list[str, str]] = []
    for node in import_graph.get_leaf_nodes():
        this_module = node.prefix
        if this_module.endswith('__init__.py'): continue
        module_dict = import_graph.parse_import(node.ast)
        for imported_module, imported_nodes in module_dict.items():
            import_edges.extend([
                [this_module, f"{imported_module}.{imported_node}"]
                for imported_node in imported_nodes
            ])

    return call_edges, import_edges


def get_type_inference(file_name: str, entry_point: str) -> list[dict]:
    inferer = TypeInference(
        name=file_name, entry_point=entry_point
    )
    inferer.infer_types()
    inferred = inferer.get_types()

    return inferred


import json


def find_function_by_id(json_file_path: str, function_id: str) -> tuple[str, str]:
    """
    Search for a function ID in the project's parsed JSON structure.

    Args:
        json_file_path (str): The path to the JSON file containing the project structure.
        function_id (str): The ID of the function to search for.

    Returns:
        tuple: (path_to_file, function_name) if found, else None.
    """
    # Load the JSON file
    with open(json_file_path, 'r') as file:
        project = json.load(file)

    def traverse(project, current_path=""):
        """
        Recursively search for a function ID in the JSON hierarchy.
        """
        if "children" in project:
            # Update the current path if it's a file or directory
            if project.get("ext") == ".py":
                current_path = f"{current_path}/{project['name']}".lstrip("/")
            elif project.get("ext") == ".":
                current_path = f"{current_path}/{project['name']}".rstrip("/")

            # Traverse the children
            if isinstance(project["children"], dict):  # Class or function children
                for name, child in project["children"].items():
                    # If the ID matches, return the path and function/class name
                    if child.get("id") == function_id:
                        return current_path, name
                    # Recursively search within the child
                    result = traverse(child, current_path)
                    if result:
                        return result
            elif isinstance(project["children"], list):  # Directory or file children
                for child in project["children"]:
                    result = traverse(child, current_path)
                    if result:
                        return result

        # If no match is found
        return None

    # Start traversal from the root
    return traverse(project)
