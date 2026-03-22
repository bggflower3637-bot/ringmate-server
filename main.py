from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse

app = FastAPI()

# 임시 메모리 저장소
# Render 재시작하면 날아감. 지금은 테스트용으로 충분함.
conversation_store = {}


def normalize_text(text: str) -> str:
    return (text or "").lower().strip()


def classify_intent(user_input: str) -> str:
    text = normalize_text(user_input)

    pain_keywords = ["pain", "toothache", "hurts", "hurt", "swelling", "swollen", "fever", "broken tooth"]
    scaling_keywords = ["cleaning", "scaling", "checkup", "exam"]
    booking_keywords = ["appointment", "book", "schedule"]

    for kw in pain_keywords:
        if kw in text:
            return "pain"

    for kw in scaling_keywords:
        if kw in text:
            return "scaling"

    for kw in booking_keywords:
        if kw in text:
            return "booking"

    return "other"


def extract_yes_no(user_input: str) -> str:
    text = normalize_text(user_input)

    yes_words = ["yes", "yeah", "yep"]
    no_words = ["no", "nope"]

    for w in yes_words:
        if w in text:
            return "yes"

    for w in no_words:
        if w in text:
            return "no"

    return "unknown"


def extract_patient_type(user_input: str) -> str:
    text = normalize_text(user_input)

    if "new patient" in text or "first time" in text:
        return "new"

    if "existing patient" in text or "returning patient" in text:
        return "existing"

    return "unknown"


def next_response(user_input: str, state: dict) -> tuple[str, dict]:
    flow = state.get("flow")
    step = state.get("step")

    # 1) 기존 흐름 먼저 처리
    if flow == "pain" and step == "ask_swelling_fever":
        yn = extract_yes_no(user_input)
        if yn == "yes":
            return (
                "That may be urgent. Are you a new patient or an existing patient?",
                {"flow": "pain", "step": "ask_patient_type_urgent"}
            )
        elif yn == "no":
            return (
                "Is the pain severe or keeping you from sleeping?",
                {"flow": "pain", "step": "ask_severe_pain"}
            )
        else:
            return (
                "Do you currently have swelling or a fever?",
                {"flow": "pain", "step": "ask_swelling_fever"}
            )

    if flow == "pain" and step == "ask_severe_pain":
        yn = extract_yes_no(user_input)
        if yn == "yes":
            return (
                "That sounds urgent. Are you a new patient or an existing patient?",
                {"flow": "pain", "step": "ask_patient_type_urgent"}
            )
        elif yn == "no":
            return (
                "Are you a new patient or an existing patient?",
                {"flow": "pain", "step": "ask_patient_type_nonurgent"}
            )
        else:
            return (
                "Is the pain severe or keeping you from sleeping?",
                {"flow": "pain", "step": "ask_severe_pain"}
            )

    if flow == "pain" and step in ["ask_patient_type_urgent", "ask_patient_type_nonurgent"]:
        pt = extract_patient_type(user_input)
        if pt == "new":
            return (
                "What day and time work best for you?",
                {"flow": "booking", "step": "ask_datetime", "patient_type": "new"}
            )
        elif pt == "existing":
            return (
                "What day and time work best for you?",
                {"flow": "booking", "step": "ask_datetime", "patient_type": "existing"}
            )
        else:
            return (
                "Are you a new patient or an existing patient?",
                {"flow": flow, "step": step}
            )

    if flow == "scaling" and step == "ask_last_cleaning":
        return (
            "Are you a new patient or an existing patient?",
            {"flow": "scaling", "step": "ask_patient_type"}
        )

    if flow == "scaling" and step == "ask_patient_type":
        pt = extract_patient_type(user_input)
        if pt in ["new", "existing"]:
            return (
                "What day and time work best for your cleaning appointment?",
                {"flow": "booking", "step": "ask_datetime", "patient_type": pt}
            )
        else:
            return (
                "Are you a new patient or an existing patient?",
                {"flow": "scaling", "step": "ask_patient_type"}
            )

    if flow == "booking" and step == "ask_patient_type":
        pt = extract_patient_type(user_input)
        if pt == "new":
            return (
                "What kind of appointment do you need? For example, cleaning, exam, or pain?",
                {"flow": "booking", "step": "ask_appointment_type", "patient_type": "new"}
            )
        elif pt == "existing":
            return (
                "What kind of appointment do you need? For example, cleaning, exam, pain, or follow-up?",
                {"flow": "booking", "step": "ask_appointment_type", "patient_type": "existing"}
            )
        else:
            return (
                "Are you a new patient or an existing patient?",
                {"flow": "booking", "step": "ask_patient_type"}
            )

    if flow == "booking" and step == "ask_appointment_type":
        intent = classify_intent(user_input)
        if intent == "pain":
            return (
                "Do you currently have swelling or a fever?",
                {"flow": "pain", "step": "ask_swelling_fever"}
            )
        elif intent == "scaling":
            return (
                "When was your last dental cleaning?",
                {"flow": "scaling", "step": "ask_last_cleaning"}
            )
        else:
            return (
                "What day and time work best for you?",
                {"flow": "booking", "step": "ask_datetime"}
            )

    # 2) state가 없거나 끝난 경우 새 intent 시작
    intent = classify_intent(user_input)

    if intent == "pain":
        return (
            "Do you currently have swelling or a fever?",
            {"flow": "pain", "step": "ask_swelling_fever"}
        )

    if intent == "scaling":
        return (
            "When was your last dental cleaning?",
            {"flow": "scaling", "step": "ask_last_cleaning"}
        )

    if intent == "booking":
        return (
            "Are you a new patient or an existing patient?",
            {"flow": "booking", "step": "ask_patient_type"}
        )

    return (
        "How can I help you today? Are you calling for pain, a cleaning, or an appointment?",
        {"flow": "general", "step": "clarify"}
    )


@app.get("/")
async def root():
    return {"status": "ok", "message": "Ringmate server is running."}


@app.post("/vapi-tool")
async def vapi_tool(request: Request):
    try:
        body = await request.json()

        user_input = body.get("message", "")

        # VAPI payload 안에서 call id 찾기
        call_id = None
        if isinstance(body.get("call"), dict):
            call_id = body["call"].get("id")

        # 없으면 임시 fallback
        if not call_id:
            call_id = "default_test_call"

        saved_state = conversation_store.get(call_id, {})

        response_message, new_state = next_response(user_input, saved_state)

        # 새 state 저장
        conversation_store[call_id] = new_state

        # 디버그 로그
        print("call_id:", call_id)
        print("user_input:", user_input)
        print("saved_state:", saved_state)
        print("new_state:", new_state)

        return JSONResponse({
            "message": response_message
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={"message": "Sorry, there was an error.", "error": str(e)}
        )
