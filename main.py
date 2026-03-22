from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/vapi-tool")
async def vapi_tool():
    return JSONResponse(
        status_code=200,
        content={"message": "server is alive"}
    )
