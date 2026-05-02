"""
Place real credentials in secrets/.env (copy from secrets/.env.example).
"""
import os
import sys
from pathlib import Path

from dotenv import load_dotenv
from twilio.rest import Client

_ROOT = Path(__file__).resolve().parent
load_dotenv(_ROOT / "secrets" / ".env")
load_dotenv(_ROOT / ".env")

required = ("TWILIO_ACCOUNT_SID", "TWILIO_AUTH_TOKEN", "TWILIO_FROM_NUMBER", "TWILIO_TO_NUMBER")
missing = [k for k in required if not os.environ.get(k)]
if missing:
    print(
        "Missing environment variables: " + ", ".join(missing),
        file=sys.stderr,
    )
    print(
        f"Copy {_ROOT / 'secrets' / '.env.example'} to {_ROOT / 'secrets' / '.env'} and edit.",
        file=sys.stderr,
    )
    sys.exit(1)

client = Client(os.environ["TWILIO_ACCOUNT_SID"], os.environ["TWILIO_AUTH_TOKEN"])

call = client.calls.create(
    twiml="<Response><Say>Ahoy, World</Say></Response>",
    to=os.environ["TWILIO_TO_NUMBER"],
    from_=os.environ["TWILIO_FROM_NUMBER"],
)

print(call.sid)
