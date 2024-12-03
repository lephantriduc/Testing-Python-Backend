# Testing Python Backend

## Getting Started

### Python version

Currently testing on Python 3.12.7.

### Dependencies

```
pip install -r requirements.txt
```

### Run command

Development mode:
```
fastapi dev src/main.py
```

Production mode:
```
fastapi run src/main.py
```

## API descriptions

### /upload_zip/
Upload a zip file to server.

Input: the `.zip` file itself.

Raise an `HTTPException(400)` if:
- File extension isn't `.zip`
- Cannot extract with `zipfile` library. Probably corrupted content or the file is encrypted with password.

Example JSON response:
```
{
    "message": f"File extracted to {extract_path}",
    "folder_tree": {
        "name": <root_folder>,
        "ext": ".",
        "children": [
            { "name": "file_1.png", "ext": ".png", "children": [] },
            { "name": "another_folder", "ext": ".", "children": [...] },
            {
                "name": "file_2.png",
                "ext": ".py",
                "children": {
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
            }
        ]
    }
}
```

> **NOTE** that a `.py` file has its own structure (dictionary) to reach all of its internal classes, methods and functions!

### /get_structure/
Get folder_tree from a repo (required to be uploaded as zip in advance).

Input: `repo_name` as a string.

Raise an `HTTPException(404)` if not found.

JSON Response: the same as `folder_tree` in `/upload_zip/` response.

### /get_file/
Get a file from a repo (required to be uploaded as zip before).

Input: `repo_name` and `file_name` as strings.

Raise an `HTTPException(404)` if not found.

Return value is the file itself (`FileResponse`).

### /generate_unit_tests/
Automatically generate unit tests for a repo.

> **NOTE** that this is just a temporary test generation method and will be deprecated soon. 

Input: `repo_name` as a string.

Raise an:
- `HTTPException(404)` if repo cannot be found.
- `HTTPException(400)` if Pynguin failed to generate tests (usually because of syntax error).

Return value is the zip file containing the generated tests.

### /dependency_analysis/
Generate dependencies edges that files from a repo emit.

Input: `repo_name` as a string.

Raise an `HTTPException(404)` if repo cannot be found.

JSON response:
```
{
    "call_edges": [
        [ node_1, node_2 ],
        [ node_3, node_4 ]
    ],
    "import_edges": [
        [ node_5, node_6 ]
    ]
}
```