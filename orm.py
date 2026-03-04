import os
from dotenv import load_dotenv
from peewee import *
from playhouse.db_url import connect
import uuid
from datetime import datetime, timezone

load_dotenv()
db = DatabaseProxy()

DATABASE_URL = os.getenv("DATABASE_URL")
db.initialize(connect(DATABASE_URL))


def utc_now():
  '''Funkcja pomocniczna do updatowania czasu'''
  return datetime.now(timezone.utc)


class BaseModel(Model):
  created_at = DateTimeField(default=utc_now)
  updated_at = DateTimeField(default=utc_now)

  class Meta:
    database = db

  def save(self, *args, **kwargs): # każde zmiany dają nową wartość updated_at
    self.updated_at = utc_now()
    return super().save(*args, **kwargs)


# ---- MODELE ----
class User(BaseModel):
  id = UUIDField(primary_key=True, default=uuid.uuid4)
  login = CharField(unique=True)
  display_name = CharField()
  password_hash = CharField()
  hash_version = IntegerField(default=1)
  email = CharField(null=True)
  is_active = BooleanField(default=True)
  failed_login_count = IntegerField(default=0)
  locked_until = DateTimeField(null=True)
  last_login_at = DateTimeField(null=True)


class Role(BaseModel):
  id = IntegerField(primary_key=True)
  name = CharField(unique=True)
  description = CharField()


class UserRole(BaseModel):
  user = ForeignKeyField(User, backref="user_roles", on_delete="CASCADE")
  role = ForeignKeyField(Role, backref="role_users", on_delete="NO ACTION")

  class Meta:
    indexes = ((("user", "role"), True),) # para unikalna


class Group(BaseModel):
  name = CharField(unique=True)
  teacher = ForeignKeyField(User, backref="teacher_groups", on_delete="CASCADE")


class GroupMember(BaseModel):
  group = ForeignKeyField(Group, backref="memberships", on_delete="CASCADE")
  student = ForeignKeyField(User, backref="group_memberships", on_delete="CASCADE")

  class Meta:
    indexes = ((("group", "student"), True),)


class TaskProgress(BaseModel):
  student = ForeignKeyField(User, backref="task_progress", on_delete="CASCADE")
  task_folder = CharField()
  best_percent = IntegerField(default=0)
  last_percent = IntegerField(default=0)
  attempts = IntegerField(default=0)
  points = IntegerField(default=0)
  bonus_awarded = BooleanField(default=False)

  class Meta:
    indexes = ((("student", "task_folder"), True),)


class TaskTestProgress(BaseModel):
  student = ForeignKeyField(User, backref="test_progress", on_delete="CASCADE")
  task_folder = CharField()
  test_type = CharField()
  test_index = IntegerField()
  passed = BooleanField(default=False)
  first_pass_attempt = IntegerField(null=True)

  class Meta:
    indexes = ((("student", "task_folder", "test_type", "test_index"), True),)


def create_all_tables():
  '''Tworzy tabele w bazie danych'''
  with db:
    db.create_tables([User, Role, UserRole, Group, GroupMember, TaskProgress, TaskTestProgress])


def seed_roles():
  '''Tworzy domyślne role w bazie'''
  default_roles = [
    ("student", "Uczeń"),
    ("teacher", "Nauczyciel"),
    ("admin", "Administrator"),
]

  for name, desc in default_roles:
      Role.get_or_create(name=name, defaults={"description": desc})


if __name__ == "__main__":
  create_all_tables()
  seed_roles()

