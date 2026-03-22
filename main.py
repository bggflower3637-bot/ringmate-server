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
    user_input = req.message.lower().strip()

    booking_keywords = ["예약", "변경", "취소", "가능", "잡아", "접수"]
    scaling_keywords = ["스케일링", "검진", "체크업", "정기검진"]
    pain_keywords = ["아파", "통증", "시려", "붓", "사랑니", "잇몸", "깨졌", "피", "출혈"]

    if any(keyword in user_input for keyword in booking_keywords):
        response = "원하시는 날짜나 시간대 있으실까요?"

    elif any(keyword in user_input for keyword in scaling_keywords):
        response = "마지막 스케일링은 언제 받으셨나요?"

    elif any(keyword in user_input for keyword in pain_keywords):
        response = "현재 붓거나 열이 나시나요?"

    else:
        response = "치과 진료, 예약, 스케일링 관련 문의를 도와드릴 수 있습니다."

    return {"message": response}
