from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()


@app.get("/")
def root():
    return {"status": "ok", "message": "Ringmate server is running."}


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.api_route(
    "/vapi-tool",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
@app.api_route(
    "/vapi-tool/",
    methods=["GET", "POST", "PUT", "PATCH", "DELETE", "OPTIONS", "HEAD"],
)
async def vapi_tool(request: Request):
    try:
        method = request.method
        headers = dict(request.headers)

        body = {}
        raw_text = ""

        try:
            body = await request.json()
        except Exception:
            try:
                raw_text = (await request.body()).decode("utf-8", errors="ignore")
            except Exception:
                raw_text = ""

        print("METHOD:", method)
        print("HEADERS:", headers)
        print("BODY_JSON:", body)
        print("BODY_TEXT:", raw_text)

        user_input = ""

        if isinstance(body, dict):
            if isinstance(body.get("message"), str):
                user_input = body.get("message", "")
            elif isinstance(body.get("input"), str):
                user_input = body.get("input", "")
            elif isinstance(body.get("user_input"), str):
                user_input = body.get("user_input", "")

        if not user_input and raw_text:
            user_input = raw_text.strip()

        if not user_input:
            user_input = "No user message received."

        return JSONResponse(
            status_code=200,
            content={
                "ok": True,
                "method": method,
                "message": f"You said: {user_input}",
                "received_json": body,
                "received_text": raw_text,
            },
        )

    except Exception as e:
        print("ERROR:", str(e))
        return JSONResponse(
            status_code=200,
            content={
                "ok": False,
                "message": "Server handled an error.",
                "error": str(e),
            },
        )
