from pathlib import Path
from datetime import timedelta, datetime, timezone
import os, json, secrets, hmac, hashlib, base64
from orm import utc_now, User
from dotenv import load_dotenv

load_dotenv()
SESSION_FILE = Path(__file__).resolve().parent.parent / 'data' / "session.json"
SECRET_KEY = os.getenv("SECRET_KEY").encode() # for hmac need to be bytes


def create_signature(data: str) -> str:
  '''Tworzenie podpisu przez hmac'''
  return base64.urlsafe_b64encode(
      hmac.new(SECRET_KEY, data.encode(), hashlib.sha256).digest()
  ).decode()

def verify_signature(data: str, signature: str) -> bool:
  '''Weryfikuje podpis z danymi'''
  expected = create_signature(data)
  return hmac.compare_digest(expected, signature)


def save_session(user: User):
  '''Zapisuje dane o sesji'''
  SESSION_FILE.parent.mkdir(exist_ok=True)

  expires_at = (utc_now() + timedelta(hours=24)).isoformat() #special format as 2025-09-09T18:20:00+00:00
  user_id = str(user.id)
  raw = user_id + expires_at
  signature = create_signature(raw)

  data = {
    "user_id": user_id,
    "expires_at": expires_at,
    "signature": signature,
    "token": secrets.token_hex(16)  # losowy identyfikator dla wielu sesji jednego usera
  }

  with SESSION_FILE.open("w", encoding="utf-8") as f:
    json.dump(data, f, indent=2, ensure_ascii=False)



def load_session():
  '''Ładuje istniejącą sesję'''
  if not SESSION_FILE.exists():
    return
  try:
    with SESSION_FILE.open(encoding="utf-8") as f:
      data = json.load(f)

    raw = data.get("user_id", "") + data.get("expires_at", "")
    if not verify_signature(raw, data.get("signature", "")):
      print("Sesja została podmieniona!")
      return
    
    exp = datetime.fromisoformat(data["expires_at"]).astimezone(timezone.utc)
    if exp <= utc_now():
      print("Sesja wygasła.")
      return
    return data
  except Exception:
    return

def clear_session():
  '''Czyści plik sesji'''
  if SESSION_FILE.exists():
    try:
      os.remove(SESSION_FILE)
    except OSError as e:
      print(f"Nie udało się usunąć pliku sesji: {e}")
