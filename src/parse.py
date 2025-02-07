import os
import hashlib
from http.client import responses
from tkinter.font import names

from networkx import goldberg_radzik
from scalpel.cfg import CFGBuilder, CFG
from scalpel.call_graph.pycg import CallGraphGenerator
from scalpel.import_graph.import_graph import ImportGraph, Tree
from scalpel.typeinfer.typeinfer import TypeInference
# from uvloop.includes.system import ntohl


def _get_folder_tree(path: str) -> dict:
    """
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
    """

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

def _get_folder_tree(path: str, cur_full_path: str) -> dict:
    """
    Create a folder tree from directory.
    The different between this and the above function is this adds ids to everything.

    Example result:
    ```
    {
        "id": 'abc123',
        "name": <path>,
        "ext": ".",
        "children": [
            { "name": "file.py",    "ext": ".py"  },
            { "name": "file.png",   "ext": ".png" },
            { "name": "somefolder", "ext": ".", "children": [] }
        ]
    }
    ```
    """

    name = os.path.basename(path)
    cur_full_path = os.path.join(cur_full_path, name)
    id = hashlib.sha256(cur_full_path.encode()).hexdigest()
    if os.path.isdir(path):
        return {
            "id": id,
            "name": name,
            "type": "folder",
            "full_path": cur_full_path,
            "ext": ".",
            "children": [
                _get_folder_tree(os.path.join(path, child), cur_full_path)
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
            "id": id,
            "name": name,
            "type": "file",
            "full_path": cur_full_path,
            "ext": ext,
            "children": []
        }


def _construct_pyfile_children(package: str, file: str) -> dict:
    """
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
    """

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

def _construct_pyfile_children_list(package: str, file: str) -> list:
    """
    Get all functions with their respective offset (first, last).
    The difference between this and the above function is:
        - This one returns list
        - It adds `name` field inside each of the list element

    Example result:
    ```
    [
       {
            "id": "123",
            "name": "func_1",
            "type": "function",
            "first": 1,
            "last": 6,
            "children": {},
        },
        {
            "id": "456",
            "name": "class_2",
            "type": "class",
            "first": 7,
            "last": 10,
            "children": [
                {
                    "id": "789",
                    "name": "__init__",
                    "type": "class:method",
                    "first": 8,
                    "last": 10,
                    "children": {}
                }
            ]
        }
    ]
    ```
    """

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
    structure, hashmap = [], {}

    def _build(structure, cfg, name, parent_type=''):
        class_cfgs = cfg.class_cfgs.values()
        function_cfgs = cfg.functioncfgs.values()

        for cfg in class_cfgs:
            full_name = name + '.' + cfg.name
            id = hashlib.sha256(full_name.encode()).hexdigest()
            structure.append( {
                'id': id,
                'name': cfg.name,
                'absolute_path_to_file': file,
                'type': parent_type + ':class',
                'first': data[full_name]['first'],
                'last': data[full_name]['last'],
                'children': {}
            })

        for cfg in function_cfgs:
            full_name = name + '.' + cfg.name
            id = hashlib.sha256(full_name.encode()).hexdigest()
            tpe = 'method' if parent_type.split(':')[-1] == 'class' else 'function'
            structure.append({
                'id': id,
                'name': cfg.name,
                'absolute_path_to_file': file,
                'type': parent_type + ':' + tpe,
                'first': data[full_name]['first'],
                'last': data[full_name]['last'],
                'children': {}
            })

    _build(structure, CFGBuilder().build_from_file("", file), name)

    return structure


def _include_pyfile_children(package: str, node: dict, path: str) -> None:
    if node['ext'] == ".":
        for child in node['children']:
            _include_pyfile_children(package, child, os.path.join(path, child['name']))
    elif node['ext'] == ".py" and node['name'] != '__init__.py':
        node['children'] = _construct_pyfile_children_list(package, path)


def get_full_structure(path: str):
    '''
    Same as _get_folder_tree, but now Python files
    have their own children (functions, classes, methods, ...)
    '''
    res = _get_folder_tree(path, '')
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

def find_element_by_id(json_data, id, current_path=""):
    """
    Recursively searches for a JSON element by its ID in the given JSON structure.

    :param json_data: The structure in JSON.
    :param id: The ID of the element to search for.
    :param current_path: The current file/directory path being traversed.
    :return: A dictionary containing the element's metadata, file path, and function path, or None if not found.
    """

    if isinstance(json_data, dict):
        # Check if the current node has the desired ID
        if json_data.get("id") == id:
            return {
                "metadata": json_data,
                "file_path": current_path,
            }

        # Update the current path and namespace
        if json_data.get("ext") is not None:
            current_path = f"{current_path}/{json_data['name']}".lstrip("/")

        # Recursively search children
        for key, value in json_data.items():
            if isinstance(value, (dict, list)):
                result = find_element_by_id(value, id, current_path)
                if result:
                    return result

    elif isinstance(json_data, list):
        for item in json_data:
            result = find_element_by_id(item, id, current_path)
            if result:
                return result

    return None

def get_file_info_from_id(json_data, id):
    result = find_element_by_id(json_data, id)
    if result.get('metadata').get('type') == 'file':
        return result.get('metadata')
    else:
        return None

def extract_function_code(file_path, start_line, end_line):
    """
    Extracts the code of a function from a file based on start and end line numbers.

    :param file_path: Path to the file containing the function.
    :param start_line: The line where the function starts.
    :param end_line: The line where the function ends.
    :return: Extracted function code as a string.
    """
    try:
        with open(file_path, 'r') as file:
            lines = file.readlines()
        # Extract the lines corresponding to the function
        function_code = lines[start_line - 1:end_line]
        return ''.join(function_code)
    except Exception as e:
        return f"Error reading file: {e}"

def get_function_dependencies(function_name, dependency_data):
    """
    Retrieves all functions called by the given function based on dependency analysis.

    :param function_name: Fully qualified name of the function (e.g., "my_project.utils.add").
    :param dependency_data: Dependency analysis JSON data.
    :return: List of called functions.
    """
    call_edges = dependency_data.get("call_edges", [])
    called_functions = []

    for edge in call_edges:
        caller, callee = edge
        if caller == function_name:
            called_functions.append(callee)

    return called_functions

def find_id_by_path(json_data, target_namespace, current_namespace=""):
    """
    Recursively searches for a function by its fully qualified path in the given JSON structure.

    :param json_data: The JSON structure representing the project.
    :param target_namespace: The target namespace we want to trace.
    :param current_namespace: The current namespace (used for tracking the path during recursion).
    :return: Function id.
    """

    if isinstance(json_data, dict):
        name = json_data.get("name")
        # Check if the current node has the desired ID
        if f"{current_namespace}.{name}".strip(".") == target_namespace:
            # function_namespace = f"{current_namespace}.{name}".strip(".")
            return json_data.get('id')

        # Update the current path and namespace
        if json_data.get("name") is not None:
            namespace_part = json_data["name"].replace(".py", "")
            current_namespace = f"{current_namespace}.{namespace_part}".strip('.')

        # Recursively search children
        for key, value in json_data.items():
            if isinstance(value, (dict, list)):
                result = find_id_by_path(value, target_namespace, current_namespace)
                if result:
                    return result

    elif isinstance(json_data, list):
        for item in json_data:
            result = find_id_by_path(item, target_namespace, current_namespace)
            if result:
                return result

    return None


def save_test_files(ai_response, base_dir="tests"):
    lines = ai_response.splitlines()
    current_file_path = None
    file_content = []

    for line in lines:
        print(line)
        if line.startswith("File:"):
            # Save the previous file (if any)
            if current_file_path and file_content:
                full_path = os.path.join(base_dir, current_file_path)
                os.makedirs(os.path.dirname(full_path), exist_ok=True)
                with open(full_path, "w", encoding="utf-8") as file:
                    file.write("\n".join(file_content))
                file_content = []

            # Start a new file
            current_file_path = line.replace("File:", "").strip()
        elif line.startswith("Content:"):
            continue  # Skip "Content:" line
        elif line.startswith("```"): # Skip ``` :)))
            continue
        elif current_file_path:
            file_content.append(line)

    # Save the last file
    if current_file_path and file_content:
        full_path = os.path.join(base_dir, current_file_path)
        # print(full_path)
        os.makedirs(os.path.dirname(full_path), exist_ok=True)
        with open(full_path, "w", encoding="utf-8") as file:
            file.write("\n".join(file_content))

    # print(f"Test files saved in '{base_dir}' directory.")
