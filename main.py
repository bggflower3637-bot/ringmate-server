from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get("/")
async def root():
    return {"status": "ok"}


@app.post("/vapi-tool")
async def vapi_tool(request: Request):
    try:
        body = {}
        try:
            body = await request.json()
        except:
            body = {}

        user_input = ""
        if isinstance(body, dict):
            user_input = body.get("message", "")

        return JSONResponse({
            "message": f"echo: {user_input}"
        })

    except Exception as e:
        return JSONResponse({
            "message": "error",
            "error": str(e)
        })
