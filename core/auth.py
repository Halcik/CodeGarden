from passlib.context import CryptContext
from orm import User, Role, UserRole, db, utc_now
from dotenv import load_dotenv
import re
import os
import getpass
from peewee import IntegrityError
from datetime import datetime, timezone, timedelta

load_dotenv()
PASSWORD_PEPPER = os.getenv("PASSWORD_PEPPER")
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")
EMAIL_RE = re.compile(r"^[^@\s]+@[^@\s]+\.[^@\s]+$")
PASSWORD_RE = re.compile(r"^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$#%])[A-Za-z\d@$#%]{8,64}$")

pwd_ctx = CryptContext(
    schemes=["argon2"],
    deprecated="auto",
    argon2__type="ID",
    argon2__memory_cost=65536,
    argon2__time_cost=2,
    argon2__parallelism=2,
)


def hash_password(password: str) -> str:
  '''Hashuje hasło'''
  return pwd_ctx.hash(PASSWORD_PEPPER+password)

def verify_password(password: str, hashed: str) -> bool:
  '''Weryfikuje hasło względem bazy'''
  return pwd_ctx.verify(PASSWORD_PEPPER+password, hashed)


def create_user(login, password, email, role_name) -> User:
  '''Tworzy użytkownika w bazie wraz z rolą'''
  login = login.strip().lower()
  if not USERNAME_RE.fullmatch(login):
    raise ValueError("Login musi mieć 3–20 znaków: a-z, 0-9, _")
  
  if email:
    email = email.strip().lower()
    if not EMAIL_RE.fullmatch(email):
      raise ValueError("Niepoprawny adres e-mail")
    
  role = Role.get(Role.name == role_name)  
  with db.atomic(): # transakcja
    try:
      user = User.create(
        login = login,
        display_name = login,
        password_hash = hash_password(password),
        email = email
      )
      UserRole.create(user=user, role=role)
      return user
    except IntegrityError:
      print("[!] Login niepoprawny")
    


def create_user_body(login: str, password: str, email: str, role_name: str = "student"):
  '''Tworzy zawartość użytkownika'''
  body = {
    "login" : login.lower().strip(),
    "password" : password,
    "role_name" : role_name,
    "email" : email if email else None
  }
  return body  


def create_script_user():
  '''Skrypt do konsolowego tworzenia użytkownika z rolą ucznia'''
  print("~~Tworzenie użytkownika~~")
  login = input("Podaj login: ")
  password = getpass.getpass("Podaj hasło: ")
  password2 = getpass.getpass("Powtórz hasło: ")
  if password != password2 or not PASSWORD_RE.fullmatch(password):
    print("Hasła różne lub niespełniające wymagań (8 znaków, małe i duże litery, znak specjalny, liczba)")
    return
  email = input("Podaj e-mail (opcjonalnie): ")
  user_body = create_user_body(login, password, email)
  create_user(**user_body)
  

def log_in():
  '''Funkcja do logowania użytkownika'''
  login = input("Podaj login: ").strip().lower()
  password = getpass.getpass("Podaj hasło: ")
  user = User.get_or_none(login=login)
  if not user:
    print("Podano niepoprawne dane")
    return
  
  if isinstance(user.locked_until, str):
    locked_until = datetime.fromisoformat(user.locked_until).replace(tzinfo=timezone.utc)
  else:
    locked_until = user.locked_until

  if locked_until and locked_until > utc_now():
    print("Konto zablokowane. Spróbuj ponownie później")
    return

  if verify_password(password, user.password_hash):
    user.last_login_at = utc_now()
    user.failed_login_count = 0
    user.locked_until = None
    user.save()
    print("Zalogowano")
    return user
  
  user.failed_login_count += 1
  if user.failed_login_count >=3:
    user.locked_until = utc_now() + timedelta(minutes=15)
    user.failed_login_count = 0
    print("Za dużo prób logowania. Konto zablokowane na 15 min")
  else:
    print("Podano niepoprawne dane") 
  user.save() 
  return



if __name__ == "__main__": # python -m core.auth
  #create_script_user()
  log_in()
