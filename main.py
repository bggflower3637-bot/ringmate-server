from fastapi import FastAPI
from pydantic import BaseModel

app = FastAPI()


class Request(BaseModel):
    message: str


@app.get("/")
def root():
    return {"status": "ok"}


@app.post("/vapi-tool")
async def vapi_tool(req: Request):
    user_input = req.message
    processed = f"받은 메시지: {user_input}"
    return {"message": processed}
