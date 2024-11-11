from typing import Annotated

from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

from src.parse import parse

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


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
