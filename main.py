from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get("/")
def root():
    return {"status": "ok", "message": "Ringmate server is running."}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.api_route("/vapi-tool", methods=["GET", "POST"])
async def vapi_tool(request: Request):
    try:
        # JSON 안전 파싱 (절대 안 죽게)
        try:
            body = await request.json()
        except Exception:
            body = {}

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
                "message": f"You said: {user_input}",
                "received": body
            }
        )

    except Exception as e:
        print("ERROR:", str(e))
        return JSONResponse(
            status_code=200,
            content={
                "message": "Server handled an error.",
                "error": str(e)
            }
        )
