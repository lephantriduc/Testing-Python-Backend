import json
import os
import asyncio
import shutil
import zipfile
import shutil
import hashlib
from asyncio import start_server
from contextlib import nullcontext

import openai
from json import JSONDecoder

from pathlib import Path

from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi import FastAPI, File, UploadFile
from concurrent.futures import ThreadPoolExecutor
from fastapi.middleware.cors import CORSMiddleware
from hyperlink.hypothesis import paths
from multipart import file_path
from pyexpat.errors import messages
from twisted.python.log import deferr
from twisted.web.http import responses

from src.randomize import randomize_type
from src.parse import *
from src.utils import *
from pydantic import BaseModel


app = FastAPI()
executor = ThreadPoolExecutor(max_workers=10)


UPLOAD_FOLDER = "./uploads"
TEST_RESULT_FOLDER = "./test-results"
STRUCTURES_FOLDER = "./structures"

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
async def root():
    return {"message": "Welcome to Testing-Python-Backend!"}


@app.post("/upload-zip/")
async def upload_zip_file(file: UploadFile):
    if not file.filename.endswith(".zip"):
        raise HTTPException(status_code=400, detail="Uploaded file must be a .zip file")

    # Ensure the upload directory exists
    os.makedirs(UPLOAD_FOLDER, exist_ok=True)

    # Save the uploaded zip file temporarily
    temp_zip_path = os.path.join(UPLOAD_FOLDER, file.filename)
    with open(temp_zip_path, "wb") as f:
        f.write(await file.read())

    try:
        # Extract the zip file to a folder named after the file (without .zip)
        folder_name = os.path.splitext(file.filename)[0]
        extract_path = os.path.join(UPLOAD_FOLDER, folder_name)
        if os.path.exists(extract_path):
            shutil.rmtree(extract_path)
        os.makedirs(extract_path)

        with zipfile.ZipFile(temp_zip_path, "r") as zip_ref:
            zip_ref.extractall(extract_path)
    except (zipfile.BadZipFile, RuntimeError):
        os.remove(temp_zip_path)
        raise HTTPException(status_code=400, detail="Invalid zip file")
    finally:
        # Clean up the temporary zip file
        if os.path.exists(temp_zip_path):
            os.remove(temp_zip_path)

    return {
        "message": f"File extracted to {extract_path}",
        "folder_tree": await get_structure(folder_name),
    }


@app.get("/get-structure/")
async def get_structure(repo_name: str):
    path_to_structure = f'{STRUCTURES_FOLDER}/{repo_name}.json'
    if os.path.exists(path_to_structure):
        with open(path_to_structure, 'r') as file:
            return json.load(file)

    target_path = os.path.join(UPLOAD_FOLDER, repo_name)
    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="Repo not found")
    full_structure = get_full_structure(target_path)

    json_object = json.dumps(full_structure, indent=2)
    with open(f"./structures/{repo_name}.json", "w") as outfile:
        outfile.write(json_object)

    return full_structure


@app.get("/dependency-analysis/")
async def get_dependency_edges(repo_name: str):
    project_path = os.path.join(UPLOAD_FOLDER, repo_name)

    if not os.path.exists(project_path):
        raise HTTPException(status_code=404, detail="Folder not found")

    file_paths = list(map(str, Path(project_path).glob("**/*.py")))

    call_edges, import_edges = dependency_analysis(file_paths, project_path)
    return {'call_edges': call_edges, 'import_edges': import_edges}


@app.get("/get-file/")
async def get_file(repo_name: str, file_name: str):
    folder_path = os.path.join(UPLOAD_FOLDER, repo_name)
    file_path = os.path.join(folder_path, file_name)

    if not os.path.exists(folder_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="File or folder not found")

    return FileResponse(file_path, media_type="application/octet-stream", filename=file_name)

@app.get("/generate-unit-tests/")
async def generate_unit_tests(repo_name: str):
    project_path = os.path.join(UPLOAD_FOLDER, repo_name)
    project_test = os.path.join(TEST_RESULT_FOLDER, repo_name)

    if not os.path.exists(project_path):
        raise HTTPException(status_code=404, detail="Folder not found")

    file_paths = list(map(str, Path(project_path).glob("**/*.py")))

    module_names = [
        os.path.relpath(file, project_path)
        for file in file_paths
        for file, _ in [os.path.splitext(file)]
    ]
    try:
        for module_name in module_names:
            if module_name.endswith('__init__'): continue

            output_path = os.path.join(
                project_test,
                os.path.dirname(module_name)
            )

            module_name = module_name.replace('/', '.')

            pynguin_cmd = f"""pynguin \
                --project-path {project_path} \
                --output-path {output_path} \
                --module-name {module_name} \
                --maximum-search-time 10 \
                --seed 13022004 \
                --assertion-generation SIMPLE
            """
            process = await asyncio.create_subprocess_shell(
                pynguin_cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
            )

            stdout, stderr = await process.communicate()
            print(f'Running `pynguin` on `{module_name}` exited with {process.returncode}')
            if process.returncode != 0:
                raise HTTPException(
                    status_code=400,
                    detail=f"Pynguin failed for module `{module_name}`:\n{stdout.decode().strip()}"
                )

        path = os.path.join(TEST_RESULT_FOLDER, repo_name)
        archived_file = shutil.make_archive(path, 'zip', path)
    finally:
        shutil.rmtree(project_path)

    headers = {"Content-Disposition": "attachment; filename=unit_tests.zip"}
    return FileResponse(archived_file, headers=headers, media_type="application/zip")

@app.get("/get-json-element-info")
async def get_json_element_info(repo_name: str, element_id: str):
    json_file_path = f'{STRUCTURES_FOLDER}/{repo_name}.json'
    if not os.path.exists(json_file_path):
        raise HTTPException(status_code=404, detail="Repo not found")

    with open(json_file_path, 'r') as file:
        project_json = json.load(file)

    function_info = find_element_by_id(project_json, element_id)

    return function_info

@app.get("/get-file-content")
async def get_file_content(repo_name: str, file_id: str):
    json_file_path = f'{STRUCTURES_FOLDER}/{repo_name}.json'
    if not os.path.exists(json_file_path):
        raise HTTPException(status_code=404, detail="Repo not found")

    with open(json_file_path, 'r') as file:
        project_json = json.load(file)

    file_info = get_file_info_from_id(project_json, file_id)

    if file_info is None:
        raise HTTPException(status_code=404, detail="File not found")

    file_full_path = os.path.join(UPLOAD_FOLDER, file_info['full_path'])

    result = {}

    try:
        with open(file_full_path, 'r', encoding='utf-8') as file:
            result['file_content'] = file.read()
    except FileNotFoundError:
        raise FileNotFoundError(f"The file at path '{file_full_path}' does not exist.")
    except PermissionError:
        raise PermissionError(f"Permission denied for file at path '{file_full_path}'.")
    except Exception as e:
        raise IOError(f"An error occurred while reading the file: {e}")

    result['metadata'] = file_info.get('children')

    return result

@app.get("/get-function-info-from-path")
async def get_function_info_from_path(repo_name: str, path_to_file: str):
    json_file_path = f'{STRUCTURES_FOLDER}/{repo_name}.json'
    if not os.path.exists(json_file_path):
        raise HTTPException(status_code=404, detail="Repo not found")

    with open(json_file_path, 'r') as file:
        project_json = json.load(file)

    function_info = find_id_by_path(project_json, path_to_file)

    return function_info

# What am I even doing??? A temporary fix.
def remove_duplicate_prefix(full_path):
    parts = full_path.split('.')
    if len(parts) > 1 and parts[0] == parts[1]:
        parts.pop(0)
    return '.'.join(parts)

def add_duplicate_prefix(repo_name, full_path):
    return f'{repo_name}.' + full_path

@app.get("/get-dependencies")
async def get_dependencies(repo_name: str, function_id: str):
    dependency_data = await get_dependency_edges(repo_name)
    function_info = await get_json_element_info(repo_name, function_id)

    # Parsing file path into the form in /dependency-analysis/
    file_path = function_info.get('file_path')
    file_path = file_path.replace('.py', '').replace('/', '.')
    file_path += '.' + function_info.get('metadata').get('name')
    file_path = remove_duplicate_prefix(file_path)

    return get_function_dependencies(file_path, dependency_data)

@app.get("/get-code")
async def get_code(repo_name: str, function_id: str):
    function_info = await get_json_element_info(repo_name, function_id)

    path_to_file = function_info['metadata']['absolute_path_to_file']
    # path_to_file = os.path.join(f'{UPLOAD_FOLDER}', path_to_file)
    first_line = function_info['metadata']['first']
    last_line = function_info['metadata']['last']

    return extract_function_code(path_to_file, first_line, last_line)

@app.get("/get-dependencies-code")
async def get_dependencies_code(repo_name: str, function_id: str):
    json_file_path = f'{STRUCTURES_FOLDER}/{repo_name}.json'
    if not os.path.exists(json_file_path):
        raise HTTPException(status_code=404, detail="Repo not found")

    with open(json_file_path, 'r') as file:
        project_json = json.load(file)

    dependencies_ids = []
    dependencies = await get_dependencies(repo_name, function_id)

    for dependency in dependencies:
        dependency = add_duplicate_prefix(repo_name, dependency)
        dependency_id = find_id_by_path(project_json, dependency)
        if dependency_id is not None:
            dependencies_ids.append(dependency_id)
    print(dependencies_ids)

    codes: list[str] = []
    for dependency_id in dependencies_ids:
        code = await get_code(repo_name, dependency_id)
        codes.append(code)

    return codes

@app.get("/ai-gen-test")
async def ai_gen_test(repo_name: str, function_id: str):
    main_code = await get_code(repo_name, function_id)
    dependency_code = await get_dependencies_code(repo_name, function_id)

    loop = asyncio.get_running_loop()
    result = await loop.run_in_executor(
        executor, generate_test_with_ai, main_code, dependency_code
    )

    info = await get_json_element_info(repo_name, function_id)

    # Print out test script for coverage analysis?

    return reformat_gpt_response(result, info['file_path'])
