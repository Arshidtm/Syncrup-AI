from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
from .parser import TypeScriptParser

app = FastAPI(title="Nexus TypeScript Parser Worker")
parser = TypeScriptParser()

class ParseRequest(BaseModel):
    code: str
    filename: str

@app.post("/parse")
async def parse_code(request: ParseRequest):
    try:
        results = parser.parse_code(request.code)
        return {
            "status": "success",
            "filename": request.filename,
            "data": results
        }
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/health")
async def health():
    return {"status": "ok"}
