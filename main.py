from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any

app = FastAPI()

# Temporary in-memory conversation store
# Good for testing. Data resets when server restarts.
conversation_store: Dict[str, Dict[str, Any]] = {}


def normalize_text(text: str) -> str:
    return (text or "").strip().lower()


def classify_intent(user_input: str) -> str:
    text = normalize_text(user_input)

    pain_keywords = [
        "pain", "tooth hurts", "tooth hurt", "toothache", "hurts", "hurt",
        "swelling", "swollen", "fever", "infection", "gum pain",
        "broken tooth", "cracked tooth", "chipped tooth", "sensitive"
    ]

    scaling_keywords = [
        "cleaning", "dental cleaning", "teeth cleaning", "scaling",
        "checkup", "exam", "routine cleaning", "routine exam"
    ]

    booking_keywords = [
        "appointment", "book", "schedule", "make an appointment",
        "set up an appointment"
    ]

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

    yes_words = ["yes", "yeah", "yep", "correct", "right"]
    no_words = ["no", "nope", "not really"]

    for word in yes_words:
        if word in text:
            return "yes"

    for word in no_words:
        if word in text:
            return "no"

    return "unknown"


def extract_patient_type(user_input: str) -> str:
    text = normalize_text(user_input)

    new_markers = [
        "new patient", "first time", "first visit", "never been there"
    ]
    existing_markers = [
        "existing patient", "returning patient", "i have been there before",
        "been there before"
    ]

    for marker in new_markers:
        if marker in text:
            return "new"

    for marker in existing_markers:
        if marker in text:
            return "existing"

    return "unknown"


def get_call_id(body: Dict[str, Any]) -> str:
    """
    Try multiple possible locations for a stable conversation identifier.
    Falls back safely if not found.
    """
    try:
        if isinstance(body.get("call"), dict) and body["call"].get("id"):
            return str(body["call"]["id"])

        if isinstance(body.get("chat"), dict) and body["chat"].get("id"):
            return str(body["chat"]["id"])

        if body.get("call_id"):
            return str(body["call_id"])

        if body.get("chat_id"):
            return str(body["chat_id"])

    except Exception:
        pass

    return "default_test_call"


def get_user_input(body: Dict[str, Any]) -> str:
    """
    Safely extract the user's latest message from a few possible shapes.
    """
    try:
        if isinstance(body.get("message"), str):
            return body.get("message", "")

        if isinstance(body.get("input"), str):
            return body.get("input", "")

        if isinstance(body.get("user_input"), str):
            return body.get("user_input", "")

    except Exception:
        pass

    return ""


def next_response(user_input: str, saved_state: Dict[str, Any]) -> tuple[str, Dict[str, Any]]:
    flow = saved_state.get("flow")
    step = saved_state.get("step")

    # Continue existing flow first
    if flow == "pain" and step == "ask_swelling_fever":
        yn = extract_yes_no(user_input)

        if yn == "yes":
            return (
                "That may be urgent. Are you a new patient or an existing patient?",
                {"flow": "pain", "step": "ask_patient_type_urgent"}
            )

        if yn == "no":
            return (
                "Is the pain severe or keeping you from sleeping?",
                {"flow": "pain", "step": "ask_severe_pain"}
            )

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

        if yn == "no":
            return (
                "Are you a new patient or an existing patient?",
                {"flow": "pain", "step": "ask_patient_type_nonurgent"}
            )

        return (
            "Is the pain severe or keeping you from sleeping?",
            {"flow": "pain", "step": "ask_severe_pain"}
        )

    if flow == "pain" and step in ["ask_patient_type_urgent", "ask_patient_type_nonurgent"]:
        patient_type = extract_patient_type(user_input)

        if patient_type in ["new", "existing"]:
            return (
                "What day and time work best for you?",
                {"flow": "booking", "step": "ask_datetime", "patient_type": patient_type}
            )

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
        patient_type = extract_patient_type(user_input)

        if patient_type in ["new", "existing"]:
            return (
                "What day and time work best for your cleaning appointment?",
                {"flow": "booking", "step": "ask_datetime", "patient_type": patient_type}
            )

        return (
            "Are you a new patient or an existing patient?",
            {"flow": "scaling", "step": "ask_patient_type"}
        )

    if flow == "booking" and step == "ask_patient_type":
        patient_type = extract_patient_type(user_input)

        if patient_type == "new":
            return (
                "What kind of appointment do you need? For example, cleaning, exam, or pain?",
                {"flow": "booking", "step": "ask_appointment_type", "patient_type": "new"}
            )

        if patient_type == "existing":
            return (
                "What kind of appointment do you need? For example, cleaning, exam, pain, or follow-up?",
                {"flow": "booking", "step": "ask_appointment_type", "patient_type": "existing"}
            )

        return (
            "Are you a new patient or an existing patient?",
            {"flow": "booking", "step": "ask_patient_type"}
        )

    if flow == "booking" and step == "ask_appointment_type":
        detected_intent = classify_intent(user_input)

        if detected_intent == "pain":
            return (
                "Do you currently have swelling or a fever?",
                {"flow": "pain", "step": "ask_swelling_fever"}
            )

        if detected_intent == "scaling":
            return (
                "When was your last dental cleaning?",
                {"flow": "scaling", "step": "ask_last_cleaning"}
            )

        return (
            "What day and time work best for you?",
            {"flow": "booking", "step": "ask_datetime"}
        )

    if flow == "booking" and step == "ask_datetime":
        return (
            "Thank you. A team member will help confirm the appointment time.",
            {"flow": "complete", "step": "done"}
        )

    # Start a new flow if no active step
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
    return {
        "status": "ok",
        "message": "Ringmate server is running."
    }


@app.post("/vapi-tool")
async def vapi_tool(request: Request):
    try:
        body = await request.json()
        print("FULL BODY:", body)

        if not isinstance(body, dict):
            return JSONResponse(
                status_code=400,
                content={"message": "Invalid request body."}
            )

        call_id = get_call_id(body)
        user_input = get_user_input(body)

        if not user_input:
            return JSONResponse(
                status_code=200,
                content={
                    "message": "How can I help you today? Are you calling for pain, a cleaning, or an appointment?"
                }
            )

        saved_state = conversation_store.get(call_id, {})
        response_message, new_state = next_response(user_input, saved_state)

        conversation_store[call_id] = new_state

        print("call_id:", call_id)
        print("user_input:", user_input)
        print("saved_state:", saved_state)
        print("new_state:", new_state)

        return JSONResponse(
            status_code=200,
            content={
                "message": response_message
            }
        )

    except Exception as e:
        print("ERROR in /vapi-tool:", str(e))
        return JSONResponse(
            status_code=500,
            content={
                "message": "Sorry, there was an error processing the request.",
                "error": str(e)
            }
        )
