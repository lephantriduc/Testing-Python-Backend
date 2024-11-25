import os
from scalpel.call_graph.pycg import CallGraphGenerator


def _get_folder_tree(path: str) -> dict:
    '''
    Create a folder tree from directory.
    
    Example result:
    ```
    {
        "name": <path>,
        "ext": ".",
        "children": [
            { "name": "file.py",  "ext": ".py"  },
            { "name": "file.png", "ext": ".png" },
            { "name": "folder",   "ext": ".", "children": [] }
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
        return { "name": name, "ext": ext }


def _get_functions_in_file(package: str, file: str) -> dict:
    '''
    Get all functions with their respective offset (first, last).
    
    Example result:
    ```
    {
        "func_1": { "first": 1, "last": 6 },
        "func_2": { "first": 7, "last": 9 }
    }
    ```
    '''
    
    cg_generator = CallGraphGenerator([file], package)
    cg_generator.analyze()

    name = os.path.basename(file)
    name, _ = os.path.splitext(name)
    data = cg_generator.output_internal_mods()

    return {
        key.split('.')[1]: {
            'first': value['first'],
            'last': value['last']
        }
        for key, value in data[name]['methods'].items()
        if key.count('.') == 1
    }


def _include_functions(package: str, node: dict, path: str):
    if node['ext'] == ".":
        for child in node['children']:
            _include_functions(package, child, os.path.join(path, child['name']))
    elif node['ext'] == ".py" and node['name'] != '__init__.py':
        node['functions'] = _get_functions_in_file(package, path)


def get_full_structure(path: str):
    res = _get_folder_tree(path)
    _include_functions(path, res, path)
    return res