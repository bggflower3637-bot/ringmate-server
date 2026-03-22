from pydantic import BaseModel

class Request(BaseModel):
    message: str

@app.post("/vapi-tool")
async def vapi_tool(req: Request):
    
    user_input = req.message

    # 🔥 여기서 필터링 시작
    processed = f"받은 메시지: {user_input}"

    return {
        "message": processed
    }
