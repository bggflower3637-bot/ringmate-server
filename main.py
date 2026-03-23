from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get("/")
def root():
    return {"status": "ok"}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/vapi-tool")
async def vapi_tool(request: Request):
    try:
        try:
            body = await request.json()
        except Exception:
            body = {}

        user_input = ""
        if isinstance(body, dict):
            if isinstance(body.get("message"), str):
                user_input = body.get("message", "")
            elif isinstance(body.get("input"), str):
                user_input = body.get("input", "")
            elif isinstance(body.get("user_input"), str):
                user_input = body.get("user_input", "")

        return JSONResponse(
            status_code=200,
            content={
                "message": f"echo: {user_input or 'no input received'}",
                "received": body
            }
        )

    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={
                "message": "handler error",
                "error": str(e)
            }
        )
