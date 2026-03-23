from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
import re

app = FastAPI()

conversation_store = {}


def normalize_text(text: str) -> str:
    return (text or "").lower().strip()


def classify_intent(user_input: str) -> str:
    text = normalize_text(user_input)

    pain_keywords = ["pain", "tooth pain", "toothache", "hurt", "hurts", "swelling", "fever"]
    cleaning_keywords = ["cleaning", "scaling", "checkup", "exam"]
    booking_keywords = ["appointment", "book", "schedule"]

    for kw in pain_keywords:
        if kw in text:
            return "pain"

    for kw in cleaning_keywords:
        if kw in text:
            return "cleaning"

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

    if "new patient" in text or "first time" in text or text == "new":
        return "new"

    if "existing patient" in text or "returning patient" in text or "existing" in text or "returning" in text:
        return "existing"

    return "unknown"


def extract_datetime(text: str) -> str:
    text = text.lower()

    days = [
        "monday", "tuesday", "wednesday",
        "thursday", "friday", "saturday"
    ]
    found_day = None

    for d in days:
        if d in text:
            found_day = d.capitalize()
            break

    time_match = re.search(r"(\d{1,2})(?::(\d{2}))?\s*(am|pm)", text)

    if found_day and time_match:
        hour = time_match.group(1)
        minute = time_match.group(2)
        ampm = time_match.group(3)

        if minute:
            return f"{found_day} at {hour}:{minute}{ampm}"
        return f"{found_day} at {hour}{ampm}"

    return ""


def extract_phone_number(text: str) -> str:
    digits = re.sub(r"\D", "", text or "")
    if len(digits) >= 10:
        digits = digits[-10:]
        return f"({digits[0:3]}) {digits[3:6]}-{digits[6:10]}"
    return ""


def extract_name(text: str) -> str:
    raw = (text or "").strip()

    patterns = [
        r"my name is\s+([A-Za-z][A-Za-z\s'-]{0,40})",
        r"this is\s+([A-Za-z][A-Za-z\s'-]{0,40})",
        r"i am\s+([A-Za-z][A-Za-z\s'-]{0,40})",
        r"i'm\s+([A-Za-z][A-Za-z\s'-]{0,40})",
    ]

    lowered = raw.lower()
    for p in patterns:
        m = re.search(p, lowered, re.IGNORECASE)
        if m:
            name = m.group(1).strip(" .,!?:;")
            return " ".join(part.capitalize() for part in name.split())

    if re.fullmatch(r"[A-Za-z][A-Za-z\s'-]{1,40}", raw):
        return " ".join(part.capitalize() for part in raw.split())

    return ""


def next_response(user_input: str, state: dict):
    flow = state.get("flow")
    step = state.get("step")

    if flow == "booking" and step == "ask_datetime":
        dt = extract_datetime(user_input)
        if dt:
            updated = dict(state)
            updated["appointment"] = dt
            updated["flow"] = "booking"
            updated["step"] = "ask_name"
            return (
                "May I have your full name for the appointment?",
                updated,
            )
        return (
            "Please tell me a day and time, for example Tuesday at 3pm.",
            {"flow": "booking", "step": "ask_datetime", "patient_type": state.get("patient_type")},
        )

    if flow == "booking" and step == "ask_name":
        name = extract_name(user_input)
        if name:
            updated = dict(state)
            updated["name"] = name
            updated["flow"] = "booking"
            updated["step"] = "ask_phone"
            return (
                "Thank you. What is the best phone number for the appointment?",
                updated,
            )
        return (
            "May I have your full name for the appointment?",
            dict(state),
        )

    if flow == "booking" and step == "ask_phone":
        phone = extract_phone_number(user_input)
        if phone:
            updated = dict(state)
            updated["phone"] = phone
            updated["flow"] = "done"
            updated["step"] = "complete"

            appointment = updated.get("appointment", "your requested time")
            name = updated.get("name", "the patient")

            return (
                f"Great, {name}. I have you scheduled for {appointment}. "
                f"We will contact you at {phone} if anything changes. We look forward to seeing you.",
                updated,
            )
        return (
            "Please provide the best phone number for the appointment, including area code.",
            dict(state),
        )

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

    if flow == "pain" and step in ["ask_patient_type_urgent", "ask_patient_type_nonurgent"]:
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

    if flow == "cleaning" and step == "ask_last_cleaning":
        return (
            "Are you a new patient or an existing patient?",
            {"flow": "cleaning", "step": "ask_patient_type"},
        )

    if flow == "cleaning" and step == "ask_patient_type":
        pt = extract_patient_type(user_input)
        if pt in ["new", "existing"]:
            return (
                "What day and time work best for your cleaning appointment?",
                {"flow": "booking", "step": "ask_datetime", "patient_type": pt},
            )
        return (
            "Are you a new patient or an existing patient?",
            {"flow": "cleaning", "step": "ask_patient_type"},
        )

    if flow == "booking" and step == "ask_patient_type":
        pt = extract_patient_type(user_input)
        if pt == "new":
            return (
                "What kind of appointment do you need? For example, cleaning, exam, or pain?",
                {"flow": "booking", "step": "ask_appointment_type", "patient_type": "new"},
            )
        if pt == "existing":
            return (
                "What kind of appointment do you need? For example, cleaning, exam, pain, or follow-up?",
                {"flow": "booking", "step": "ask_appointment_type", "patient_type": "existing"},
            )
        return (
            "Are you a new patient or an existing patient?",
            {"flow": "booking", "step": "ask_patient_type"},
        )

    if flow == "booking" and step == "ask_appointment_type":
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
        return (
            "What day and time work best for you?",
            {"flow": "booking", "step": "ask_datetime", "patient_type": state.get("patient_type")},
        )

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
        "How can I help you today? Are you calling about tooth pain, a cleaning, or an appointment?",
        {"flow": "general", "step": "clarify"},
    )


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

        call_id = "default_test_call"
        if isinstance(body, dict):
            if isinstance(body.get("call"), dict):
                call_id = body["call"].get("id", "default_test_call")
            elif isinstance(body.get("call_id"), str):
                call_id = body.get("call_id", "default_test_call")

        saved_state = conversation_store.get(call_id, {})
        response_message, new_state = next_response(user_input, saved_state)
        conversation_store[call_id] = new_state

        print("CALL_ID:", call_id)
        print("SAVED_STATE:", saved_state)
        print("NEW_STATE:", new_state)

        return JSONResponse(
            status_code=200,
            content={"message": response_message},
        )

    except Exception as e:
        print("ERROR:", str(e))
        return JSONResponse(
            status_code=200,
            content={
                "message": "Sorry, there was an error.",
                "error": str(e),
            },
        )
