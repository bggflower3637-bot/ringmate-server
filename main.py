from fastapi import FastAPI
from fastapi.responses import JSONResponse

app = FastAPI()

@app.get("/")
def root():
    return {"status": "ok"}

@app.post("/vapi-tool")
async def vapi_tool():
    return JSONResponse(
        content={
            "message": "안녕하세요. 테스트 성공입니다."
        },
        media_type="application/json; charset=utf-8"
    )
