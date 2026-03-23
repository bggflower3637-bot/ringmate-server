from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import re

app = FastAPI()

conversation_store = {}


def normalize_text(text: str) -> str:
    return (text or "").lower().strip()


def classify_intent(user_input: str) -> str:
    text = normalize_text(user_input)

    if any(k in text for k in ["pain", "tooth", "hurt", "swelling", "fever"]):
        return "pain"

    if any(k in text for k in ["cleaning", "scaling", "checkup"]):
        return "cleaning"

    if any(k in text for k in ["appointment", "book", "schedule"]):
        return "booking"

    return "other"


def extract_yes_no(user_input: str) -> str:
    text = normalize_text(user_input)

    if any(w in text for w in ["yes", "yeah", "yep"]):
        return "yes"

    if any(w in text for w in ["no", "nope"]):
        return "no"

    return "unknown"


def extract_patient_type(user_input: str) -> str:
    text = normalize_text(user_input)

    if "new" in text:
        return "new"

    if "existing" in text or "returning" in text:
        return "existing"

    return "unknown"


def extract_datetime(text: str) -> str:
    text = text.lower()

    days = ["monday", "tuesday", "wednesday", "thursday", "friday"]
    found_day = None

    for d in days:
        if d in text:
            found_day = d.capitalize()

    time_match = re.search(r"(\d{1,2})(am|pm)", text)

    if found_day and time_match:
        return f"{found_day} at {time_match.group(1)}{time_match.group(2)}"

    return ""


def next_response(user_input: str, state: dict):
    flow = state.get("flow")
    step = state.get("step")

    # 예약 시간 받는 단계
    if flow == "booking" and step == "ask_datetime":
        dt = extract_datetime(user_input)

        if dt:
            return (
                f"Great. You're scheduled for {dt}. We look forward to seeing you!",
                {"flow": "done", "step": "complete", "appointment": dt},
            )
        else:
            return (
                "Please tell me a day and time, for example Tuesday at 3pm.",
                {"flow": "booking", "step": "ask_datetime"},
            )

    # pain 흐름
    if flow == "pain" and step == "ask_swelling_fever":
        yn = extract_yes_no(user_input)

        if yn == "yes":
            return (
                "That may be urgent. Are you a new patient or an existing patient?",
                {"flow": "pain", "step": "ask_patient_type_urgent"},
            )

        if yn == "no":
            return (
                "Is the pain severe or keeping you from sleeping?",
                {"flow": "pain", "step": "ask_severe_pain"},
            )

        return (
            "Do you currently have swelling or a fever?",
            {"flow": "pain", "step": "ask_swelling_fever"},
        )

    if flow == "pain" and step == "ask_severe_pain":
        yn = extract_yes_no(user_input)

        if yn == "yes":
            return (
                "That sounds urgent. Are you a new patient or an existing patient?",
                {"flow": "pain", "step": "ask_patient_type_urgent"},
            )

        if yn == "no":
            return (
                "Are you a new patient or an existing patient?",
                {"flow": "pain", "step": "ask_patient_type_nonurgent"},
            )

        return (
            "Is the pain severe or keeping you from sleeping?",
            {"flow": "pain", "step": "ask_severe_pain"},
        )

    if flow == "pain" and "ask_patient_type" in str(step):
        pt = extract_patient_type(user_input)

        if pt in ["new", "existing"]:
            return (
                "What day and time work best for you?",
                {"flow": "booking", "step": "ask_datetime", "patient_type": pt},
            )

        return (
            "Are you a new patient or an existing patient?",
            {"flow": flow, "step": step},
        )

    # cleaning
    if flow == "cleaning":
        return (
            "Are you a new patient or an existing patient?",
            {"flow": "cleaning", "step": "ask_patient_type"},
        )

    # booking
    if flow == "booking" and step == "ask_patient_type":
        pt = extract_patient_type(user_input)

        if pt in ["new", "existing"]:
            return (
                "What kind of appointment do you need?",
                {"flow": "booking", "step": "ask_type"},
            )

        return (
            "Are you a new patient or an existing patient?",
            {"flow": "booking", "step": "ask_patient_type"},
        )

    # 초기 intent
    intent = classify_intent(user_input)

    if intent == "pain":
        return (
            "Do you currently have swelling or a fever?",
            {"flow": "pain", "step": "ask_swelling_fever"},
        )

    if intent == "cleaning":
        return (
            "When was your last dental cleaning?",
            {"flow": "cleaning", "step": "ask_last_cleaning"},
        )

    if intent == "booking":
        return (
            "Are you a new patient or an existing patient?",
            {"flow": "booking", "step": "ask_patient_type"},
        )

    return (
        "How can I help you today? Pain, cleaning, or appointment?",
        {"flow": "general", "step": "clarify"},
    )


@app.get("/")
def root():
    return {"status": "ok"}


@app.api_route("/vapi-tool", methods=["GET", "POST", "OPTIONS"])
async def vapi_tool(request: Request):
    try:
        body = {}
        try:
            body = await request.json()
        except:
            pass

        user_input = body.get("message", "")

        call_id = body.get("call_id", "default")

        state = conversation_store.get(call_id, {})

        response, new_state = next_response(user_input, state)

        conversation_store[call_id] = new_state

        return JSONResponse(
            status_code=200,
            content={"message": response}
        )

    except Exception as e:
        return JSONResponse(
            status_code=200,
            content={"message": "Error", "error": str(e)}
        )
