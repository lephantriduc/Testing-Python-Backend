import os
import asyncio
import shutil
import zipfile
import shutil
import hashlib

from pathlib import Path
from typing import Annotated

from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from src.parse import get_full_structure, dependency_analysis, get_type_inference
from src.randomize import randomize_type

app = FastAPI()

UPLOAD_FOLDER = "./uploads"
TEST_RESULT_FOLDER = "./test-results"

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


@app.post("/upload_zip/")
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


@app.get("/get_structure/")
async def get_structure(repo_name: str):
    target_path = os.path.join(UPLOAD_FOLDER, repo_name)
    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="Repo not found")
    return get_full_structure(target_path)


@app.get("/dependency_analysis/")
async def get_dependency_edges(repo_name: str):
    project_path = os.path.join(UPLOAD_FOLDER, repo_name)

    if not os.path.exists(project_path):
        raise HTTPException(status_code=404, detail="Folder not found")

    file_paths = list(map(str, Path(project_path).glob("**/*.py")))

    call_edges, import_edges = dependency_analysis(file_paths, project_path)
    return {'call_edges': call_edges, 'import_edges': import_edges}


@app.get("/get_file/")
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


@app.get("/get-randomized-inputs/")
async def get_randomized_inputs():
    file_name = 'type_infer_ex.py'
    entry_point = f"{UPLOAD_FOLDER}/my_project/type_infer_ex.py"

    infer_list = get_type_inference(file_name, entry_point)

    randomized_inputs = {}
    for item in infer_list:
        para_name = item.get('parameter', '')
        if para_name:
            type_name = item.get('type').pop()
            randomized_inputs[para_name] = randomize_type(type_name)
            print((para_name, type_name))

    return {'file_name': file_name, 'randomized_inputs': randomized_inputs}
