import os
import asyncio
import shutil
import zipfile
import secrets
import shutil
from pathlib import Path, PurePath

from typing import Annotated
from fastapi import HTTPException
from fastapi.responses import FileResponse
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from src.parse import parse
from src.parse2 import get_full_structure

app = FastAPI()

UPLOAD_FOLDER = "./uploads"

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


@app.post("/get_structure/")
async def get_structure(repo_name: str):
    target_path = os.path.join(UPLOAD_FOLDER, repo_name)
    if not os.path.exists(target_path):
        raise HTTPException(status_code=404, detail="Repo not found")
    return get_full_structure(target_path)
#

@app.get("/get_file/")
async def get_file(repo_name: str, file_name: str):
    folder_path = os.path.join(UPLOAD_FOLDER, repo_name)
    file_path = os.path.join(folder_path, file_name)

    if not os.path.exists(folder_path) or not os.path.isfile(file_path):
        raise HTTPException(status_code=404, detail="Folder not found")

    return FileResponse(file_path, media_type="application/octet-stream", filename=file_name)


@app.post("/files/")
async def create_file(file: Annotated[bytes, File()]):
    return {"file_size": len(file)}


@app.post("/uploadfiles/")
async def create_upload_files(files: list[UploadFile]):
    res = []
    for file in files:
        res.append({"file_name": file.filename, "file_size": file.size})

    return {"files": res}
    # return {"filenames": [file.filename for file in files]}


@app.post("/parse/")
async def parse_file(file: UploadFile):
    code = await file.read()
    parsed_data = parse(code)
    return {"parsed_data": parsed_data}


@app.post("/parsefiles/")
async def parse_files(files: list[UploadFile]):
    result = []
    for file in files:
        code = await file.read()
        parsed_data = parse(code)
        result.append({"filename": file.filename, "parsed_data": parsed_data})

    return {"parsed_files": result}


@app.post("/generate-unit-tests/")
async def generate_unit_tests():
    p = Path("uploads/")

    # The full path
    file_paths = list(p.glob("**/*.py"))

    # Pair the project paths and the files' names
    paths_and_names = [(path.parent, path.relative_to('uploads/').parent, path.stem) for path in file_paths]

    # Iterate through each .py file and call (")> pynguin for help generating tests
    for project_path, output_path, filename in paths_and_names:
        pynguin_cmd = f"pynguin --project-path {project_path} --output-path ./test-results/{output_path} --module-name {filename}"
        process = await asyncio.create_subprocess_shell(
            pynguin_cmd,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )

        stdout, stderr = await process.communicate()
        print(f'[{pynguin_cmd!r} exited with {process.returncode}]')
        if stdout:
            print(f'[stdout]\n{stdout.decode()}')
        if stderr:
            print(f'[stderr]\n{stderr.decode()}')

    archived_file = shutil.make_archive('zipped_file', 'zip', 'test-results')

    headers = {"Content-Disposition": "attachment; filename=unit_tests.zip"}
    return FileResponse(archived_file, headers=headers, media_type="application/zip")
