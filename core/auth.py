from passlib.context import CryptContext
from orm import User, Role, UserRole, db
from dotenv import load_dotenv
import re
import os

load_dotenv()
PASSWORD_PEPPER = os.getenv("PASSWORD_PEPPER")
USERNAME_RE = re.compile(r"^[a-z0-9_]{3,20}$")

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
  '''Porównanie hashy specjalnie z sol - hashed z bazy'''
  return pwd_ctx.verify(PASSWORD_PEPPER+password, hashed)


def create_user(login, password, email, role_name) -> User:
  '''Tworzy użytkownika w bazie wraz z rolą'''
  login = login.strip().lower()
  if not USERNAME_RE.fullmatch(login):
    raise ValueError("Login musi mieć 3–20 znaków: a-z, 0-9, _")

  with db.atomic(): # transakcja
    user = User.create(
      login = login,
      display_name = login,
      password_hash = password,
      email = email
    )
    role = Role.get(Role.name == role_name)
    UserRole.create(user=user, role=role)
    return user


def create_user_body(login: str, password: str, email: str, role_name: str = "student"):
  '''Tworzy zawartość użytkownika'''
  body = {
    "login" : login.lower().strip(),
    "password" : hash_password(password),
    "role_name" : role_name,
    "email" : email if email else None
  }
  return body  


def create_script_user():
  '''Skrypt do konsolowego tworzenia użytkownika z rolą ucznia'''
  print("~~Tworzenie użytkownika~~")
  login = input("Podaj login: ")
  password = input("Podaj hasło: ")
  email = input("Podaj e-mail (opcjonalnie): ")
  user_body = create_user_body(login, password, email)
  create_user(**user_body)
  

if __name__ == "__main__": # python -m core.auth
  create_script_user()
