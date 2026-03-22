from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get("/")
async def root():
    return {"status": "ok", "message": "Ringmate server is running."}


@app.post("/vapi-tool")
async def vapi_tool(request: Request):
    try:
        body = await request.json()
        print("FULL BODY:", body)

        user_input = ""
        if isinstance(body, dict):
            if isinstance(body.get("message"), str):
                user_input = body.get("message", "")
            elif isinstance(body.get("input"), str):
                user_input = body.get("input", "")
            elif isinstance(body.get("user_input"), str):
                user_input = body.get("user_input", "")

        if not user_input:
            user_input = "No user message received."

        return JSONResponse(
            status_code=200,
            content={
                "message": f"You said: {user_input}"
            }
        )

    except Exception as e:
        print("ERROR:", str(e))
        return JSONResponse(
            status_code=500,
            content={
                "message": "Server error",
                "error": str(e)
            }
        )
