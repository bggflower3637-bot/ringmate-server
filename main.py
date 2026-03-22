from fastapi import FastAPI, Request
from fastapi.responses import JSONResponse
from typing import Dict, Any

app = FastAPI()


# -----------------------------
# Helpers
# -----------------------------
def normalize_text(text: str) -> str:
    return (text or "").lower().strip()


def classify_intent(user_input: str) -> str:
    text = normalize_text(user_input)

    pain_keywords = [
        "pain", "toothache", "hurts", "hurt", "aching", "ache",
        "swelling", "swollen", "fever", "gum pain", "bleeding",
        "broken tooth", "cracked tooth", "chip", "chipped",
        "wisdom tooth", "infection", "sensitive", "sensitivity"
    ]

    scaling_keywords = [
        "cleaning", "dental cleaning", "teeth cleaning",
        "scaling", "checkup", "exam", "routine exam", "routine cleaning"
    ]

    reschedule_keywords = [
        "reschedule", "move my appointment", "change my appointment",
        "change appointment", "different time", "different day"
    ]

    cancel_keywords = [
        "cancel", "cancel my appointment", "delete my appointment"
    ]

    booking_keywords = [
        "appointment", "book", "schedule", "make an appointment",
        "set up an appointment", "come in"
    ]

    price_keywords = [
        "price", "cost", "fee", "how much", "insurance", "covered"
    ]

    for kw in pain_keywords:
        if kw in text:
            return "pain"

    for kw in scaling_keywords:
        if kw in text:
            return "scaling"

    for kw in reschedule_keywords:
        if kw in text:
            return "reschedule"

    for kw in cancel_keywords:
        if kw in text:
            return "cancel"

    for kw in booking_keywords:
        if kw in text:
            return "booking"

    for kw in price_keywords:
        if kw in text:
            return "price"

    return "other"


def extract_yes_no(user_input: str) -> str:
    text = normalize_text(user_input)

    yes_words = ["yes", "yeah", "yep", "i do", "correct", "right", "there is", "i am"]
    no_words = ["no", "nope", "not really", "i don't", "none"]

    for w in yes_words:
        if w in text:
            return "yes"

    for w in no_words:
        if w in text:
            return "no"

    return "unknown"


def extract_patient_type(user_input: str) -> str:
    text = normalize_text(user_input)

    new_patient_words = [
        "new patient", "first time", "i have never been there",
        "haven't been there before", "first visit"
    ]
    existing_patient_words = [
        "existing patient", "returning patient", "i have been there before",
        "i'm a patient", "i already go there", "been there before"
    ]

    for w in new_patient_words:
        if w in text:
            return "new"

    for w in existing_patient_words:
        if w in text:
            return "existing"

    return "unknown"


def extract_urgency_signals(user_input: str) -> Dict[str, bool]:
    text = normalize_text(user_input)
    return {
        "swelling_or_fever": any(k in text for k in ["swelling", "swollen", "fever", "infection"]),
        "bleeding": any(k in text for k in ["bleeding", "blood"]),
        "trauma": any(k in text for k in ["broken tooth", "cracked tooth", "chipped", "knocked out", "trauma"]),
        "severe_pain": any(k in text for k in ["severe", "unbearable", "very painful", "extreme pain", "can't sleep"])
    }


# -----------------------------
# Conversation Logic
# -----------------------------
def generate_response(
    user_input: str,
    intent: str,
    state: Dict[str, Any]
) -> Dict[str, Any]:
    """
    state example:
    {
        "flow": "pain_triage",
        "step": "ask_swelling_fever",
        "intent": "pain"
    }
    """

    current_flow = state.get("flow")
    current_step = state.get("step")

    # ---------------------------------
    # Continue existing flow first
    # ---------------------------------
    if current_flow == "pain_triage":
        if current_step == "ask_swelling_fever":
            yn = extract_yes_no(user_input)

            if yn == "yes":
                return {
                    "message": "Because you may have swelling or fever, we recommend calling the office as soon as possible for urgent evaluation. Are you a new patient or an existing patient?",
                    "state": {
                        "flow": "pain_triage",
                        "step": "ask_patient_type_urgent",
                        "intent": "pain",
                        "urgency": "urgent"
                    }
                }
            elif yn == "no":
                return {
                    "message": "Understood. Is the pain severe, constant, or keeping you from sleeping?",
                    "state": {
                        "flow": "pain_triage",
                        "step": "ask_severe_pain",
                        "intent": "pain",
                        "urgency": "unknown"
                    }
                }
            else:
                return {
                    "message": "Just to confirm, do you currently have swelling or a fever?",
                    "state": state
                }

        elif current_step == "ask_severe_pain":
            yn = extract_yes_no(user_input)

            if yn == "yes":
                return {
                    "message": "That sounds urgent. Are you a new patient or an existing patient?",
                    "state": {
                        "flow": "pain_triage",
                        "step": "ask_patient_type_urgent",
                        "intent": "pain",
                        "urgency": "urgent"
                    }
                }
            elif yn == "no":
                return {
                    "message": "Are you a new patient or an existing patient?",
                    "state": {
                        "flow": "pain_triage",
                        "step": "ask_patient_type_nonurgent",
                        "intent": "pain",
                        "urgency": "nonurgent"
                    }
                }
            else:
                return {
                    "message": "Would you say the pain is severe, constant, or keeping you from sleeping?",
                    "state": state
                }

        elif current_step == "ask_patient_type_urgent":
            patient_type = extract_patient_type(user_input)

            if patient_type == "new":
                return {
                    "message": "Thank you. Since this may be urgent, what is the best phone number for a callback, and what time are you available today?",
                    "state": {
                        "flow": "urgent_booking",
                        "step": "collect_contact_new",
                        "intent": "pain",
                        "patient_type": "new",
                        "urgency": "urgent"
                    }
                }
            elif patient_type == "existing":
                return {
                    "message": "Thank you. Since this may be urgent, what time are you available today for an emergency visit?",
                    "state": {
                        "flow": "urgent_booking",
                        "step": "collect_time_existing",
                        "intent": "pain",
                        "patient_type": "existing",
                        "urgency": "urgent"
                    }
                }
            else:
                return {
                    "message": "Are you a new patient or an existing patient?",
                    "state": state
                }

        elif current_step == "ask_patient_type_nonurgent":
            patient_type = extract_patient_type(user_input)

            if patient_type == "new":
                return {
                    "message": "Thank you. What day and time work best for your first visit?",
                    "state": {
                        "flow": "routine_booking",
                        "step": "collect_datetime_new",
                        "intent": "pain",
                        "patient_type": "new",
                        "urgency": "nonurgent"
                    }
                }
            elif patient_type == "existing":
                return {
                    "message": "Thank you. What day and time work best for your visit?",
                    "state": {
                        "flow": "routine_booking",
                        "step": "collect_datetime_existing",
                        "intent": "pain",
                        "patient_type": "existing",
                        "urgency": "nonurgent"
                    }
                }
            else:
                return {
                    "message": "Are you a new patient or an existing patient?",
                    "state": state
                }

    elif current_flow == "scaling_flow":
        if current_step == "ask_last_cleaning":
            return {
                "message": "Thank you. Are you a new patient or an existing patient?",
                "state": {
                    "flow": "scaling_flow",
                    "step": "ask_patient_type",
                    "intent": "scaling"
                }
            }

        elif current_step == "ask_patient_type":
            patient_type = extract_patient_type(user_input)

            if patient_type == "new":
                return {
                    "message": "Great. What day and time work best for your cleaning appointment?",
                    "state": {
                        "flow": "routine_booking",
                        "step": "collect_datetime_new",
                        "intent": "scaling",
                        "patient_type": "new"
                    }
                }
            elif patient_type == "existing":
                return {
                    "message": "Great. What day and time work best for your cleaning appointment?",
                    "state": {
                        "flow": "routine_booking",
                        "step": "collect_datetime_existing",
                        "intent": "scaling",
                        "patient_type": "existing"
                    }
                }
            else:
                return {
                    "message": "Are you a new patient or an existing patient?",
                    "state": state
                }

    elif current_flow == "booking_flow":
        if current_step == "ask_patient_type":
            patient_type = extract_patient_type(user_input)

            if patient_type == "new":
                return {
                    "message": "Thank you. What kind of appointment do you need? For example, cleaning, exam, pain, or something else?",
                    "state": {
                        "flow": "booking_flow",
                        "step": "ask_appointment_type_new",
                        "intent": "booking",
                        "patient_type": "new"
                    }
                }
            elif patient_type == "existing":
                return {
                    "message": "Thank you. What kind of appointment do you need? For example, cleaning, exam, pain, or follow-up?",
                    "state": {
                        "flow": "booking_flow",
                        "step": "ask_appointment_type_existing",
                        "intent": "booking",
                        "patient_type": "existing"
                    }
                }
            else:
                return {
                    "message": "Are you a new patient or an existing patient?",
                    "state": state
                }

        elif current_step in ["ask_appointment_type_new", "ask_appointment_type_existing"]:
            detected_intent = classify_intent(user_input)

            if detected_intent == "pain":
                return {
                    "message": "I understand. Do you currently have swelling or a fever?",
                    "state": {
                        "flow": "pain_triage",
                        "step": "ask_swelling_fever",
                        "intent": "pain"
                    }
                }
            elif detected_intent == "scaling":
                return {
                    "message": "Sure. When was your last dental cleaning?",
                    "state": {
                        "flow": "scaling_flow",
                        "step": "ask_last_cleaning",
                        "intent": "scaling"
                    }
                }
            else:
                return {
                    "message": "What day and time work best for you?",
                    "state": {
                        "flow": "routine_booking",
                        "step": "collect_datetime",
                        "intent": "booking"
                    }
                }

    # ---------------------------------
    # New intent entry
    # ---------------------------------
    if intent == "pain":
        urgency = extract_urgency_signals(user_input)

        if urgency["swelling_or_fever"] or urgency["trauma"] or urgency["severe_pain"]:
            return {
                "message": "That may be urgent. Are you a new patient or an existing patient?",
                "state": {
                    "flow": "pain_triage",
                    "step": "ask_patient_type_urgent",
                    "intent": "pain",
                    "urgency": "urgent"
                }
            }

        return {
            "message": "Do you currently have swelling or a fever?",
            "state": {
                "flow": "pain_triage",
                "step": "ask_swelling_fever",
                "intent": "pain"
            }
        }

    elif intent == "scaling":
        return {
            "message": "Sure. When was your last dental cleaning?",
            "state": {
                "flow": "scaling_flow",
                "step": "ask_last_cleaning",
                "intent": "scaling"
            }
        }

    elif intent == "booking":
        return {
            "message": "Of course. Are you a new patient or an existing patient?",
            "state": {
                "flow": "booking_flow",
                "step": "ask_patient_type",
                "intent": "booking"
            }
        }

    elif intent == "reschedule":
        return {
            "message": "I can help with that. May I have your full name and the current appointment date you want to change?",
            "state": {
                "flow": "reschedule_flow",
                "step": "collect_identity_and_current_appt",
                "intent": "reschedule"
            }
        }

    elif intent == "cancel":
        return {
            "message": "I can help with that. May I have your full name and the appointment date you want to cancel?",
            "state": {
                "flow": "cancel_flow",
                "step": "collect_identity_and_appt",
                "intent": "cancel"
            }
        }

    elif intent == "price":
        return {
            "message": "Which treatment are you asking about? For example, cleaning, filling, crown, root canal, or implant?",
            "state": {
                "flow": "price_flow",
                "step": "ask_treatment_type",
                "intent": "price"
            }
        }

    else:
        return {
            "message": "How can I help you today? Are you calling for pain, a cleaning, an appointment, a change, or a cost question?",
            "state": {
                "flow": "general",
                "step": "clarify_reason",
                "intent": "other"
            }
        }


# -----------------------------
# Routes
# -----------------------------
@app.get("/")
async def root():
    return {
        "status": "ok",
        "message": "Ringmate dental phone AI server is running."
    }


@app.post("/vapi-tool")
async def vapi_tool(request: Request):
    try:
        body = await request.json()

        user_input = ""
        conversation_state = {}

        if isinstance(body, dict):
            user_input = (
                body.get("message")
                or body.get("input")
                or body.get("user_input")
                or ""
            )

            # If VAPI or your middleware sends prior state, read it here
            conversation_state = body.get("state", {}) or {}

        intent = classify_intent(user_input)
        result = generate_response(
            user_input=user_input,
            intent=intent,
            state=conversation_state
        )

        return JSONResponse({
            "message": result["message"],
            "intent": result["state"].get("intent", intent),
            "state": result["state"],
            "received_input": user_input
        })

    except Exception as e:
        return JSONResponse(
            status_code=500,
            content={
                "message": "Sorry, there was an error processing the request.",
                "error": str(e)
            }
        )
