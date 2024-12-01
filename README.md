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
            { "name": "file_2.png", "ext": ".py", "children": {...} }
        ]
    }
}
```

Note that children of a `.py` file is a **dictionary** (different from one of a folder).

Example of a `.py` file children:
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

### /get_structure/
Get folder_tree from a repo (required to be uploaded as zip before).

Raise an `HTTPException(404)` if not found.

JSON Response: the same as `folder_tree` in `/upload_zip/` response.

### /get_file/
Get a file from a repo (required to be uploaded as zip before).

Raise an `HTTPException(404)` if not found.

Return value is the file itself (`FileResponse`).
