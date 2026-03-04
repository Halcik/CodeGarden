from __future__ import annotations

import json
import os
import re
import shutil
import multiprocessing
import difflib
import secrets
import string
from contextlib import redirect_stdout
from io import StringIO
from pathlib import Path

from flask import Flask, abort, g, redirect, render_template, request, url_for
from peewee import fn
from unidecode import unidecode
from core.auth import create_user, create_user_body, verify_password, hash_password
from core.session import load_session, save_session, clear_session
from orm import Group, GroupMember, Role, TaskProgress, TaskTestProgress, User, UserRole, utc_now
from datetime import datetime, timezone, timedelta


BASE_DIR = Path(__file__).resolve().parent
TASKS_DIR = BASE_DIR / "tasks"
TEMPLATE_DIR = TASKS_DIR / "00_template"


app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET_KEY", "dev")
DEFAULT_BASIC_COUNT = 1
DEFAULT_EXTRA_COUNT = 0
ALLOWED_CHECKERS = {"exact", "contains", "regex"}


def slugify(value: str) -> str:
    cleaned = unidecode(value).strip().lower()
    cleaned = re.sub(r"\s+", "_", cleaned)
    cleaned = re.sub(r"[^a-z0-9_]+", "", cleaned)
    cleaned = re.sub(r"_+", "_", cleaned).strip("_")
    return cleaned


def generate_temp_password(length: int = 12) -> str:
    lower = string.ascii_lowercase
    upper = string.ascii_uppercase
    digits = string.digits
    specials = "@$#%"
    rng = secrets.SystemRandom()
    required = [
        rng.choice(lower),
        rng.choice(upper),
        rng.choice(digits),
        rng.choice(specials),
    ]
    pool = lower + upper + digits + specials
    required.extend(rng.choice(pool) for _ in range(max(0, length - len(required))))
    rng.shuffle(required)
    return "".join(required)


def task_dirs() -> list[Path]:
    if not TASKS_DIR.exists():
        return []
    return [
        path
        for path in TASKS_DIR.iterdir()
        if path.is_dir() and re.match(r"^\d{2}_", path.name)
    ]


def next_free_id() -> int:
    ids: list[int] = []
    for path in task_dirs():
        try:
            ids.append(int(path.name.split("_")[0]))
        except ValueError:
            continue
    return max(ids) + 1 if ids else 1


def load_template_json(name: str) -> dict:
    path = TEMPLATE_DIR / name
    if not path.exists():
        return {}
    with path.open(encoding="utf-8") as f:
        return json.load(f)


def parse_task_id_from_folder(folder_name: str) -> int | None:
    match = re.match(r"^(\d{2})_", folder_name)
    if not match:
        return None
    return int(match.group(1))


def load_task_bundle(folder_name: str) -> tuple[dict, dict, str]:
    task_path = TASKS_DIR / folder_name
    task_json = task_path / "task.json"
    test_json = task_path / "test.json"
    example_file = task_path / "example.py"
    task_data = {}
    test_data = {}
    example_code = ""
    if task_json.exists():
        with task_json.open(encoding="utf-8") as f:
            task_data = json.load(f)
    if test_json.exists():
        with test_json.open(encoding="utf-8") as f:
            test_data = json.load(f)
    if example_file.exists():
        example_code = example_file.read_text(encoding="utf-8")
    return task_data, test_data, example_code


def list_tasks(user: User | None = None) -> list[dict]:
    tasks: list[dict] = []
    for path in sorted(task_dirs(), key=lambda p: p.name):
        if path.name == "00_template":
            continue
        task_data, _, _ = load_task_bundle(path.name)
        status = "not_started"
        points = 0
        if user:
            progress = TaskProgress.get_or_none(
                TaskProgress.student == user, TaskProgress.task_folder == path.name
            )
            if progress:
                status = "completed" if progress.best_percent == 100 else "started"
                points = progress.points
            else:
                saved_code = load_solution(user, path.name)
                if saved_code.strip():
                    status = "started"
        tasks.append(
            {
                "folder": path.name,
                "title": task_data.get("title", path.name),
                "difficulty": task_data.get("difficulty", ""),
                "description": task_data.get("description", ""),
                "status": status,
                "points": points,
            }
        )
    return tasks


def authenticate_user(login: str, password: str) -> tuple[User | None, str | None]:
    login = login.strip().lower()
    user = User.get_or_none(login=login)
    if not user:
        return None, "Podano niepoprawne dane logowania."

    if isinstance(user.locked_until, str):
        locked_until = datetime.fromisoformat(user.locked_until).replace(
            tzinfo=timezone.utc
        )
    else:
        locked_until = user.locked_until

    if locked_until and locked_until > utc_now():
        return None, "Konto zablokowane. Spróbuj ponownie później."

    if verify_password(password, user.password_hash):
        user.last_login_at = utc_now()
        user.failed_login_count = 0
        user.locked_until = None
        user.save()
        return user, None

    user.failed_login_count += 1
    if user.failed_login_count >= 3:
        user.locked_until = utc_now() + timedelta(minutes=15)
        user.failed_login_count = 0
        user.save()
        return None, "Za dużo prób logowania. Konto zablokowane na 15 minut."

    user.save()
    return None, "Podano niepoprawne dane logowania."


def get_solution_path(user_id: str, folder: str) -> Path:
    base = BASE_DIR / "data" / "solutions" / user_id / folder
    base.mkdir(parents=True, exist_ok=True)
    return base / "solution.py"


def load_solution(user: User, folder: str) -> str:
    path = get_solution_path(str(user.id), folder)
    if not path.exists():
        return ""
    return path.read_text(encoding="utf-8")


def save_solution(user: User, folder: str, code: str) -> Path:
    path = get_solution_path(str(user.id), folder)
    path.write_text(code, encoding="utf-8")
    return path


def script_worker(code: str, input_lines: list[str], q: multiprocessing.Queue):
    output = StringIO()
    iterator = iter(input_lines)

    def fake_input(prompt: str = "") -> str:
        return next(iterator, "")

    try:
        with redirect_stdout(output):
            env = {"__name__": "__main__", "input": fake_input}
            exec(code, env, env)
    except Exception as exc:
        q.put({"status": "error", "output": f"Wystąpił błąd: {exc}"})
        return
    q.put({"status": "ok", "output": output.getvalue().strip()})


def function_worker(
    code_path: str,
    function_name: str,
    input_lines: list[str],
    q: multiprocessing.Queue,
):
    try:
        import importlib.util
        import sys

        spec = importlib.util.spec_from_file_location("student_solution", code_path)
        module = importlib.util.module_from_spec(spec)
        sys.modules["student_solution"] = module
        spec.loader.exec_module(module)
        func = getattr(module, function_name)
        output = func(*input_lines)
        q.put({"status": "ok", "output": output})
    except Exception as exc:
        q.put({"status": "error", "output": f"Wystąpił błąd: {exc}"})


def run_with_timeout(target, args: tuple, timeout: int) -> dict:
    q: multiprocessing.Queue = multiprocessing.Queue()
    p = multiprocessing.Process(target=target, args=(*args, q))
    p.start()
    p.join(timeout)
    if p.is_alive():
        p.terminate()
        p.join()
        return {"status": "timeout", "output": "TIMEOUT"}
    if q.empty():
        return {"status": "error", "output": "BRAK WYNIKU"}
    return q.get()


def check_output(expected: str, output: str, checker: str) -> bool:
    if checker == "exact":
        return expected == output
    if checker == "contains":
        return expected in output
    if checker == "regex":
        return bool(re.search(expected, output))
    return False


def run_tests_for_code(code: str, task_data: dict, test_data: dict, solution_path: Path) -> dict:
    function_name = task_data.get("function_name")
    timeout = int(task_data.get("time_limit", 2))

    results: dict = {"basic_tests": [], "extra_tests": [], "summary": {}}

    def run_group(group_key: str) -> list[dict]:
        group_results = []
        for test in test_data.get(group_key, []):
            expected = str(test.get("expected_output", "")).strip()
            input_value = test.get("input")
            input_lines = input_value.splitlines() if input_value else []
            checker = test.get("checker", "exact")

            if function_name:
                result = run_with_timeout(
                    function_worker,
                    (str(solution_path), function_name, input_lines),
                    timeout,
                )
                output = str(result.get("output", "")).strip()
            else:
                result = run_with_timeout(
                    script_worker,
                    (code, input_lines),
                    timeout,
                )
                output = str(result.get("output", "")).strip()

            passed = result.get("status") == "ok" and check_output(
                expected, output, checker
            )
            diff = None
            error_message = None
            if result.get("status") != "ok":
                error_message = output
            elif not passed:
                diff_lines = list(
                    difflib.unified_diff(
                        expected.splitlines(),
                        output.splitlines(),
                        fromfile="expected",
                        tofile="got",
                        lineterm="",
                        n=1,
                    )
                )
                diff = "\n".join(diff_lines[:8]) if diff_lines else None
            group_results.append(
                {
                    "input": input_value,
                    "expected": expected,
                    "output": output,
                    "checker": checker,
                    "status": result.get("status"),
                    "passed": passed,
                    "diff": diff,
                    "error": error_message,
                }
            )
        return group_results

    if function_name:
        solution_path.write_text(code, encoding="utf-8")

    results["basic_tests"] = run_group("basic_tests")
    results["extra_tests"] = run_group("extra_tests")

    total = len(results["basic_tests"]) + len(results["extra_tests"])
    passed = sum(1 for item in results["basic_tests"] + results["extra_tests"] if item["passed"])
    results["summary"] = {
        "passed": passed,
        "total": total,
        "percent": round((passed / total) * 100) if total else 100,
    }
    return results


def get_current_user() -> User | None:
    data = load_session()
    if not data:
        return None
    user_id = data.get("user_id")
    if not user_id:
        return None
    return User.get_or_none(User.id == user_id)


def get_user_roles(user: User) -> set[str]:
    roles = UserRole.select(UserRole.role).where(UserRole.user == user)
    return {user_role.role.name for user_role in roles}


def render_admin_users(reset_notice: dict | None = None):
    users = list(User.select().order_by(User.login))
    user_roles = {user.id: get_user_roles(user) for user in users}
    return render_template(
        "admin/users.html",
        users=users,
        user_roles=user_roles,
        reset_notice=reset_notice,
    )


@app.before_request
def attach_user():
    user = get_current_user()
    if not user:
        g.current_user = None
        g.roles = set()
        g.can_edit = False
        g.is_teacher = False
        return
    roles = get_user_roles(user)
    g.current_user = user
    g.roles = roles
    g.can_edit = bool(roles.intersection({"teacher", "admin"}))
    g.is_teacher = "teacher" in roles


@app.context_processor
def inject_user():
    return {
        "current_user": getattr(g, "current_user", None),
        "can_edit": getattr(g, "can_edit", False),
        "is_admin": "admin" in getattr(g, "roles", set()),
        "is_teacher": getattr(g, "is_teacher", False),
    }


def list_users_with_role(role_name: str) -> list[User]:
    return (
        User.select()
        .join(UserRole)
        .join(Role)
        .where(Role.name == role_name)
        .order_by(User.login)
    )


def list_group_members(group: Group) -> list[User]:
    return (
        User.select()
        .join(GroupMember, on=(GroupMember.student == User.id))
        .where(GroupMember.group == group)
        .order_by(User.login)
    )


def get_group_progress_for_student(student: User) -> dict:
    progress = TaskProgress.select().where(TaskProgress.student == student)
    completed = sum(1 for item in progress if item.best_percent == 100)
    started = sum(1 for item in progress if 0 < item.best_percent < 100)
    total = len(list_tasks())
    percent = round((completed / total) * 100) if total else 100
    points = sum(item.points for item in progress)
    return {
        "completed": completed,
        "started": started,
        "total": total,
        "percent": percent,
        "points": points,
    }


def get_total_points(student: User) -> int:
    return TaskProgress.select(fn.SUM(TaskProgress.points)).where(
        TaskProgress.student == student
    ).scalar() or 0


def get_group_ranking(group: Group) -> list[dict]:
    members = list_group_members(group)
    ranking = []
    for student in members:
        ranking.append(
            {
                "student": student,
                "points": get_total_points(student),
            }
        )
    ranking.sort(key=lambda item: (-item["points"], item["student"].login))
    for idx, entry in enumerate(ranking, start=1):
        entry["rank"] = idx
    return ranking


def normalize_dt(value) -> datetime | None:
    if not value:
        return None
    if isinstance(value, str):
        try:
            parsed = datetime.fromisoformat(value)
        except ValueError:
            return None
        return parsed if parsed.tzinfo else parsed.replace(tzinfo=timezone.utc)
    return value


def is_active_user(user: User) -> bool:
    last_login = normalize_dt(user.last_login_at)
    if not last_login:
        return False
    return last_login >= utc_now() - timedelta(days=7)


def get_group_stats(group: Group) -> dict:
    members = list_group_members(group)
    count = len(members)
    total_points = sum(get_total_points(student) for student in members)
    avg_points = round(total_points / count) if count else 0
    return {"count": count, "avg_points": avg_points}


def difficulty_multiplier(value: str) -> int:
    mapping = {
        "bardzo łatwe": 1,
        "łatwe": 2,
        "średnie": 3,
        "trudne": 4,
        "bardzo trudne": 5,
    }
    return mapping.get((value or "").strip().lower(), 1)


def update_task_progress(
    student: User,
    task_folder: str,
    task_data: dict,
    test_results: dict,
) -> TaskProgress:
    progress, _ = TaskProgress.get_or_create(
        student=student, task_folder=task_folder
    )
    progress.attempts += 1
    progress.last_percent = test_results["summary"]["percent"]
    if progress.last_percent > progress.best_percent:
        progress.best_percent = progress.last_percent

    multiplier = difficulty_multiplier(task_data.get("difficulty"))

    newly_passed = 0
    for test_type in ("basic_tests", "extra_tests"):
        for index, result in enumerate(test_results.get(test_type, [])):
            if not result.get("passed"):
                continue
            record, _ = TaskTestProgress.get_or_create(
                student=student,
                task_folder=task_folder,
                test_type=test_type,
                test_index=index,
            )
            if record.passed:
                continue
            record.passed = True
            record.first_pass_attempt = progress.attempts
            record.save()
            newly_passed += 1

    if newly_passed:
        if progress.attempts == 1:
            base = 4
        elif progress.attempts == 2:
            base = 3
        elif progress.attempts == 3:
            base = 2
        else:
            base = 1
        progress.points += base * newly_passed * multiplier

    if progress.last_percent == 100 and not progress.bonus_awarded:
        progress.points += 10 * multiplier
        progress.bonus_awarded = True

    progress.save()
    return progress


def build_rows_from_template(tests: list[dict], count: int) -> list[dict]:
    rows: list[dict] = []
    for idx in range(count):
        row = tests[idx] if idx < len(tests) and isinstance(tests[idx], dict) else {}
        checker = row.get("checker", "exact")
        if checker not in ALLOWED_CHECKERS:
            checker = "exact"
        value = "" if row.get("input") is None else str(row.get("input", ""))
        rows.append(
            {
                "input": value,
                "expected_output": str(row.get("expected_output", "")),
                "checker": checker,
            }
        )
    return rows


def build_rows_from_form(form, prefix: str, count: int) -> list[dict]:
    rows: list[dict] = []
    for idx in range(1, count + 1):
        checker = form.get(f"{prefix}_checker_{idx}", "") or "exact"
        if checker not in ALLOWED_CHECKERS:
            checker = "exact"
        rows.append(
            {
                "input": form.get(f"{prefix}_input_{idx}", ""),
                "expected_output": form.get(f"{prefix}_expected_{idx}", ""),
                "checker": checker,
            }
        )
    return rows


def collect_tests(form, prefix: str, count: int) -> list[dict]:
    tests: list[dict] = []
    for idx in range(1, count + 1):
        raw_input = form.get(f"{prefix}_input_{idx}", "").strip()
        expected = form.get(f"{prefix}_expected_{idx}", "").strip()
        checker = form.get(f"{prefix}_checker_{idx}", "").strip() or "exact"
        if checker not in ALLOWED_CHECKERS:
            checker = "exact"
        if not raw_input and not expected:
            continue
        tests.append(
            {
                "input": raw_input or None,
                "expected_output": expected,
                "checker": checker,
            }
        )
    return tests


@app.get("/")
def index():
    return render_template("index.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "GET":
        return render_template("login.html", error=None)

    login_value = request.form.get("login", "").strip()
    password = request.form.get("password", "")
    user, error = authenticate_user(login_value, password)
    if error:
        return render_template("login.html", error=error, login=login_value)

    save_session(user)
    return redirect(url_for("index"))


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "GET":
        return render_template("register.html", error=None)

    login_value = request.form.get("login", "").strip()
    password = request.form.get("password", "")
    email = request.form.get("email", "").strip() or None
    try:
        body = create_user_body(login_value, password, email, role_name="student")
        create_user(**body)
    except ValueError as exc:
        return render_template("register.html", error=str(exc), login=login_value, email=email)
    except Exception:
        return render_template(
            "register.html",
            error="Nie udało się utworzyć konta.",
            login=login_value,
            email=email,
        )
    return redirect(url_for("login"))


@app.post("/logout")
def logout():
    clear_session()
    return redirect(url_for("login"))


@app.get("/tasks")
def tasks_list():
    if not g.current_user:
        return redirect(url_for("login"))
    total_points = get_total_points(g.current_user)
    return render_template(
        "tasks/tasks_list.html",
        tasks=list_tasks(g.current_user),
        total_points=total_points,
    )


@app.get("/student")
def student_panel():
    if not g.current_user:
        return redirect(url_for("login"))
    if g.can_edit:
        return redirect(url_for("teacher_panel"))
    return render_template("panels/student_panel.html")


@app.get("/teacher")
def teacher_panel():
    if not g.current_user:
        return redirect(url_for("login"))
    if not g.can_edit:
        abort(403)
    groups = Group.select().where(Group.teacher == g.current_user).order_by(Group.name)
    group_stats = {group.id: get_group_stats(group) for group in groups}
    return render_template(
        "panels/teacher_panel.html",
        groups=groups,
        group_stats=group_stats,
    )


@app.get("/admin")
def admin_panel():
    if not g.current_user:
        return redirect(url_for("login"))
    if "admin" not in g.roles:
        abort(403)
    return render_template(
        "panels/admin_panel.html",
    )


@app.get("/admin/users")
def admin_users():
    if not g.current_user:
        return redirect(url_for("login"))
    if "admin" not in g.roles:
        abort(403)
    return render_admin_users()


@app.post("/admin/users/<user_id>/role")
def set_user_role(user_id: str):
    if not g.current_user:
        return redirect(url_for("login"))
    if "admin" not in g.roles:
        abort(403)
    target = User.get_or_none(User.id == user_id)
    if not target:
        abort(404)
    role_name = request.form.get("role_name", "").strip()
    if role_name not in {"student", "teacher"}:
        abort(400)
    if "admin" in get_user_roles(target):
        return redirect(url_for("admin_users"))
    UserRole.delete().where(UserRole.user == target).execute()
    role = Role.get(Role.name == role_name)
    UserRole.create(user=target, role=role)
    return redirect(url_for("admin_users"))


@app.post("/admin/users/<user_id>/reset-password")
def admin_reset_password(user_id: str):
    if not g.current_user:
        return redirect(url_for("login"))
    if "admin" not in g.roles:
        abort(403)
    target = User.get_or_none(User.id == user_id)
    if not target:
        abort(404)
    if target.id == g.current_user.id:
        abort(400)
    if "admin" in get_user_roles(target):
        abort(403)
    temp_password = generate_temp_password()
    target.password_hash = hash_password(temp_password)
    target.hash_version += 1
    target.failed_login_count = 0
    target.locked_until = None
    target.save()
    return render_admin_users(
        reset_notice={"login": target.login, "temp_password": temp_password}
    )


@app.post("/admin/users/<user_id>/delete")
def admin_delete_user(user_id: str):
    if not g.current_user:
        return redirect(url_for("login"))
    if "admin" not in g.roles:
        abort(403)
    target = User.get_or_none(User.id == user_id)
    if not target:
        abort(404)
    if target.id == g.current_user.id:
        abort(400)
    if "admin" in get_user_roles(target):
        abort(403)
    UserRole.delete().where(UserRole.user == target).execute()
    GroupMember.delete().where(GroupMember.student == target).execute()
    TaskProgress.delete().where(TaskProgress.student == target).execute()
    TaskTestProgress.delete().where(TaskTestProgress.student == target).execute()
    target.delete_instance()
    return redirect(url_for("admin_users"))


@app.get("/ranking")
def ranking():
    if not g.current_user:
        return redirect(url_for("login"))
    if g.can_edit:
        return redirect(url_for("groups_list"))
    membership = (
        GroupMember.select(GroupMember, Group)
        .join(Group)
        .where(GroupMember.student == g.current_user)
        .first()
    )
    group = membership.group if membership else None
    ranking_list = get_group_ranking(group) if group else []
    rank_position = None
    if group:
        for entry in ranking_list:
            if entry["student"].id == g.current_user.id:
                rank_position = entry["rank"]
                break
    return render_template(
        "ranking.html",
        group=group,
        ranking=ranking_list,
        rank_position=rank_position,
    )


@app.get("/profile")
def profile():
    if not g.current_user:
        return redirect(url_for("login"))
    tasks = list_tasks(g.current_user)
    total_points = get_total_points(g.current_user)
    membership = (
        GroupMember.select(GroupMember, Group)
        .join(Group)
        .where(GroupMember.student == g.current_user)
        .first()
    )
    group = membership.group if membership else None
    return render_template(
        "profile.html",
        tasks=tasks,
        total_points=total_points,
        group=group,
    )


@app.get("/groups")
def groups_list():
    if not g.current_user:
        return redirect(url_for("login"))
    if not g.can_edit:
        abort(403)
    if "admin" in g.roles:
        groups = Group.select().order_by(Group.name)
    else:
        groups = Group.select().where(Group.teacher == g.current_user).order_by(Group.name)
    teachers = list_users_with_role("teacher")
    group_stats = {group.id: get_group_stats(group) for group in groups}
    selected_group = None
    members = []
    student_progress = {}
    selected_id = request.args.get("group_id", "").strip()
    if selected_id.isdigit():
        selected_group = Group.get_or_none(Group.id == int(selected_id))
        if selected_group:
            if "admin" not in g.roles and selected_group.teacher != g.current_user:
                abort(403)
            members = list_group_members(selected_group)
            student_progress = {
                student.id: get_group_progress_for_student(student) for student in members
            }
    return render_template(
        "groups/groups_list.html",
        groups=groups,
        teachers=teachers,
        group_stats=group_stats,
        selected_group=selected_group,
        members=members,
        student_progress=student_progress,
    )


@app.post("/groups/create")
def create_group():
    if not g.current_user:
        return redirect(url_for("login"))
    if "admin" not in g.roles:
        abort(403)
    name = request.form.get("name", "").strip()
    teacher_id = request.form.get("teacher_id", "").strip()
    if not name or not teacher_id:
        return redirect(url_for("groups_list"))
    teacher = User.get_or_none(User.id == teacher_id)
    if not teacher:
        return redirect(url_for("groups_list"))
    Group.get_or_create(name=name, defaults={"teacher": teacher})
    return redirect(url_for("groups_list"))


@app.get("/groups/<int:group_id>")
def group_detail(group_id: int):
    if not g.current_user:
        return redirect(url_for("login"))
    if not g.can_edit:
        abort(403)
    group = Group.get_or_none(Group.id == group_id)
    if not group:
        abort(404)
    if "admin" not in g.roles and group.teacher != g.current_user:
        abort(403)
    members = list_group_members(group)
    students = list_users_with_role("student")
    student_progress = {
        student.id: get_group_progress_for_student(student) for student in members
    }
    student_activity = {student.id: is_active_user(student) for student in members}
    ranking = get_group_ranking(group)
    return render_template(
        "groups/group_detail.html",
        group=group,
        members=members,
        students=students,
        student_progress=student_progress,
        student_activity=student_activity,
        ranking=ranking,
    )


@app.post("/groups/<int:group_id>/edit")
def edit_group(group_id: int):
    if not g.current_user:
        return redirect(url_for("login"))
    if not g.can_edit:
        abort(403)
    group = Group.get_or_none(Group.id == group_id)
    if not group:
        abort(404)
    if "admin" not in g.roles and group.teacher != g.current_user:
        abort(403)
    name = request.form.get("name", "").strip()
    teacher_id = request.form.get("teacher_id", "").strip()
    if name:
        group.name = name
    if "admin" in g.roles and teacher_id:
        teacher = User.get_or_none(User.id == teacher_id)
        if teacher:
            group.teacher = teacher
    group.save()
    return redirect(url_for("group_detail", group_id=group_id))


@app.post("/groups/<int:group_id>/delete")
def delete_group(group_id: int):
    if not g.current_user:
        return redirect(url_for("login"))
    if "admin" not in g.roles:
        abort(403)
    group = Group.get_or_none(Group.id == group_id)
    if not group:
        abort(404)
    GroupMember.delete().where(GroupMember.group == group).execute()
    group.delete_instance()
    return redirect(url_for("groups_list"))


@app.post("/groups/<int:group_id>/add-student")
def add_group_student(group_id: int):
    if not g.current_user:
        return redirect(url_for("login"))
    if not g.can_edit:
        abort(403)
    group = Group.get_or_none(Group.id == group_id)
    if not group:
        abort(404)
    if "admin" not in g.roles and group.teacher != g.current_user:
        abort(403)
    student_id = request.form.get("student_id", "").strip()
    if not student_id:
        return redirect(url_for("group_detail", group_id=group_id))
    student = User.get_or_none(User.id == student_id)
    if not student:
        return redirect(url_for("group_detail", group_id=group_id))
    GroupMember.get_or_create(group=group, student=student)
    return redirect(url_for("group_detail", group_id=group_id))


@app.post("/groups/<int:group_id>/remove-student")
def remove_group_student(group_id: int):
    if not g.current_user:
        return redirect(url_for("login"))
    if not g.can_edit:
        abort(403)
    group = Group.get_or_none(Group.id == group_id)
    if not group:
        abort(404)
    if "admin" not in g.roles and group.teacher != g.current_user:
        abort(403)
    student_id = request.form.get("student_id", "").strip()
    if not student_id:
        return redirect(url_for("group_detail", group_id=group_id))
    GroupMember.delete().where(
        GroupMember.group == group, GroupMember.student == student_id
    ).execute()
    return redirect(url_for("group_detail", group_id=group_id))


@app.route("/tasks/<folder>", methods=["GET", "POST"])
def task_detail(folder: str):
    if not g.current_user:
        return redirect(url_for("login"))
    task_path = TASKS_DIR / folder
    if not task_path.exists() or not task_path.is_dir():
        abort(404)
    if folder == "00_template":
        abort(404)
    task_data, test_data, _ = load_task_bundle(folder)
    saved_code = load_solution(g.current_user, folder)
    solution_path = get_solution_path(str(g.current_user.id), folder)
    test_results = None
    points_awarded = None
    task_points = 0
    total_points = 0
    group = None
    rank_position = None
    group_points = None
    progress = TaskProgress.get_or_none(
        TaskProgress.student == g.current_user, TaskProgress.task_folder == folder
    )
    if progress:
        task_points = progress.points
    total_points = get_total_points(g.current_user)
    membership = (
        GroupMember.select(GroupMember, Group)
        .join(Group)
        .where(GroupMember.student == g.current_user)
        .first()
    )
    group = membership.group if membership else None
    if group:
        ranking = get_group_ranking(group)
        for entry in ranking:
            if entry["student"].id == g.current_user.id:
                rank_position = entry["rank"]
                group_points = entry["points"]
                break
    if request.method == "POST":
        code = request.form.get("solution_code", "")
        save_solution(g.current_user, folder, code)
        saved_code = code
        if request.form.get("action") == "test":
            before_points = task_points
            test_results = run_tests_for_code(code, task_data, test_data, solution_path)
            progress = update_task_progress(g.current_user, folder, task_data, test_results)
            task_points = progress.points
            points_awarded = task_points - before_points
            total_points = get_total_points(g.current_user)
            if group:
                group_points = total_points
    return render_template(
        "tasks/task_detail.html",
        folder=folder,
        task=task_data,
        saved_code=saved_code,
        test_results=test_results,
        task_points=task_points,
        total_points=total_points,
        points_awarded=points_awarded,
        group=group,
        rank_position=rank_position,
        group_points=group_points,
    )


@app.route("/tasks/new", methods=["GET", "POST"])
def new_task():
    if not g.current_user:
        return redirect(url_for("login"))
    if not g.can_edit:
        abort(403)
    task_template = load_template_json("task.json")
    test_template = load_template_json("test.json")
    example_template = (TEMPLATE_DIR / "example.py").read_text(
        encoding="utf-8"
    ) if (TEMPLATE_DIR / "example.py").exists() else ""

    default_basic_rows = build_rows_from_template(
        test_template.get("basic_tests", []), DEFAULT_BASIC_COUNT
    )
    default_extra_rows = build_rows_from_template(
        test_template.get("extra_tests", []), DEFAULT_EXTRA_COUNT
    )

    created = request.args.get("created")
    if request.method == "GET":
        return render_template(
            "tasks/add_task.html",
            next_id=next_free_id(),
            defaults=task_template,
            basic_rows=default_basic_rows,
            extra_rows=default_extra_rows,
            basic_count=DEFAULT_BASIC_COUNT,
            extra_count=DEFAULT_EXTRA_COUNT,
            example_code=example_template,
            errors=[],
            created=created,
            form={},
        )

    errors: list[str] = []

    title = request.form.get("title", "").strip()
    folder_title = title
    description = request.form.get("description", "").strip()
    difficulty = request.form.get("difficulty", "").strip()
    hint = request.form.get("hint", "").strip()
    example_input = request.form.get("example_input", "").strip()
    example_output = request.form.get("example_output", "").strip()
    tags_raw = request.form.get("tags", "").strip()
    function_name = request.form.get("function_name", "").strip()
    time_limit_raw = request.form.get("time_limit", "").strip()
    example_code = request.form.get("example_code", "")
    if not title:
        errors.append("Tytuł zadania jest wymagany.")

    slug = slugify(folder_title)
    if not slug:
        errors.append("Nazwa folderu jest wymagana.")

    try:
        time_limit = int(time_limit_raw) if time_limit_raw else int(
            task_template.get("time_limit", 2)
        )
    except ValueError:
        errors.append("Limit czasu musi być liczbą.")
        time_limit = int(task_template.get("time_limit", 2))

    try:
        basic_count = int(request.form.get("basic_count", DEFAULT_BASIC_COUNT))
        extra_count = int(request.form.get("extra_count", DEFAULT_EXTRA_COUNT))
    except ValueError:
        basic_count = DEFAULT_BASIC_COUNT
        extra_count = DEFAULT_EXTRA_COUNT

    basic_tests = collect_tests(request.form, "basic", basic_count)
    extra_tests = collect_tests(request.form, "extra", extra_count)

    if errors:
        return render_template(
            "tasks/add_task.html",
            next_id=next_free_id(),
            defaults=task_template,
            basic_rows=build_rows_from_form(
                request.form, "basic", basic_count
            ),
            extra_rows=build_rows_from_form(
                request.form, "extra", extra_count
            ),
            basic_count=basic_count,
            extra_count=extra_count,
            example_code=example_template,
            errors=errors,
            created=None,
            form=request.form,
        )

    task_id = next_free_id()
    folder_name = f"{task_id:02d}_{slug}"
    new_task_path = TASKS_DIR / folder_name
    if new_task_path.exists():
        errors.append("Folder zadania już istnieje. Spróbuj ponownie.")
        return render_template(
            "tasks/add_task.html",
            next_id=next_free_id(),
            defaults=task_template,
            basic_rows=build_rows_from_form(
                request.form, "basic", basic_count
            ),
            extra_rows=build_rows_from_form(
                request.form, "extra", extra_count
            ),
            basic_count=basic_count,
            extra_count=extra_count,
            example_code=example_template,
            errors=errors,
            created=None,
            form=request.form,
        )

    shutil.copytree(TEMPLATE_DIR, new_task_path)

    tags = [tag.strip() for tag in tags_raw.split(",") if tag.strip()]

    task_data = {
        "id": task_id,
        "title": title,
        "description": description,
        "difficulty": difficulty,
        "hint": hint,
        "example_input": example_input or None,
        "example_output": example_output,
        "tags": tags,
        "function_name": function_name or None,
        "time_limit": time_limit,
    }

    test_data = {
        "task_id": task_id,
        "basic_tests": basic_tests,
        "extra_tests": extra_tests,
    }

    with (new_task_path / "task.json").open("w", encoding="utf-8") as f:
        json.dump(task_data, f, ensure_ascii=False, indent=2)

    with (new_task_path / "test.json").open("w", encoding="utf-8") as f:
        json.dump(test_data, f, ensure_ascii=False, indent=2)

    (new_task_path / "example.py").write_text(example_code, encoding="utf-8")

    return redirect(url_for("new_task", created=folder_name))


@app.route("/tasks/<folder>/edit", methods=["GET", "POST"])
def edit_task(folder: str):
    if not g.current_user:
        return redirect(url_for("login"))
    if not g.can_edit:
        abort(403)
    task_path = TASKS_DIR / folder
    if not task_path.exists() or not task_path.is_dir():
        abort(404)

    task_data, test_data, example_code = load_task_bundle(folder)
    basic_tests = test_data.get("basic_tests", [])
    extra_tests = test_data.get("extra_tests", [])

    basic_count = max(DEFAULT_BASIC_COUNT, len(basic_tests))
    extra_count = max(DEFAULT_EXTRA_COUNT, len(extra_tests))

    if request.method == "GET":
        return render_template(
            "tasks/edit_task.html",
            folder=folder,
            task=task_data,
            example_code=example_code,
            basic_rows=build_rows_from_template(basic_tests, basic_count),
            extra_rows=build_rows_from_template(extra_tests, extra_count),
            basic_count=basic_count,
            extra_count=extra_count,
            tags_value=", ".join(task_data.get("tags", [])),
            errors=[],
        )

    errors: list[str] = []

    title = request.form.get("title", "").strip()
    description = request.form.get("description", "").strip()
    difficulty = request.form.get("difficulty", "").strip()
    hint = request.form.get("hint", "").strip()
    example_input = request.form.get("example_input", "").strip()
    example_output = request.form.get("example_output", "").strip()
    tags_raw = request.form.get("tags", "").strip()
    function_name = request.form.get("function_name", "").strip()
    time_limit_raw = request.form.get("time_limit", "").strip()
    example_code = request.form.get("example_code", "")

    if not title:
        errors.append("Tytuł zadania jest wymagany.")

    try:
        time_limit = int(time_limit_raw) if time_limit_raw else int(
            task_data.get("time_limit", 2)
        )
    except ValueError:
        errors.append("Limit czasu musi być liczbą.")
        time_limit = int(task_data.get("time_limit", 2))

    try:
        basic_count = int(request.form.get("basic_count", basic_count))
        extra_count = int(request.form.get("extra_count", extra_count))
    except ValueError:
        basic_count = max(DEFAULT_BASIC_COUNT, len(basic_tests))
        extra_count = max(DEFAULT_EXTRA_COUNT, len(extra_tests))

    basic_tests = collect_tests(request.form, "basic", basic_count)
    extra_tests = collect_tests(request.form, "extra", extra_count)

    if errors:
        return render_template(
            "tasks/edit_task.html",
            folder=folder,
            task={
                **task_data,
                "title": title,
                "description": description,
                "difficulty": difficulty,
                "hint": hint,
                "example_input": example_input or None,
                "example_output": example_output,
                "function_name": function_name or None,
                "time_limit": time_limit,
            },
            example_code=example_code,
            basic_rows=build_rows_from_form(request.form, "basic", basic_count),
            extra_rows=build_rows_from_form(request.form, "extra", extra_count),
            basic_count=basic_count,
            extra_count=extra_count,
            tags_value=tags_raw,
            errors=errors,
        )

    tags = [tag.strip() for tag in tags_raw.split(",") if tag.strip()]
    task_id = task_data.get("id") or parse_task_id_from_folder(folder) or 0

    updated_task = {
        "id": task_id,
        "title": title,
        "description": description,
        "difficulty": difficulty,
        "hint": hint,
        "example_input": example_input or None,
        "example_output": example_output,
        "tags": tags,
        "function_name": function_name or None,
        "time_limit": time_limit,
    }

    updated_test = {
        "task_id": task_id,
        "basic_tests": basic_tests,
        "extra_tests": extra_tests,
    }

    with (task_path / "task.json").open("w", encoding="utf-8") as f:
        json.dump(updated_task, f, ensure_ascii=False, indent=2)

    with (task_path / "test.json").open("w", encoding="utf-8") as f:
        json.dump(updated_test, f, ensure_ascii=False, indent=2)

    (task_path / "example.py").write_text(example_code, encoding="utf-8")

    return redirect(url_for("tasks_list"))


@app.post("/tasks/<folder>/delete")
def delete_task(folder: str):
    if not g.current_user:
        return redirect(url_for("login"))
    if "admin" not in g.roles:
        abort(403)
    if folder == "00_template":
        abort(400)
    task_path = (TASKS_DIR / folder).resolve()
    if not task_path.exists() or not task_path.is_dir():
        abort(404)
    if TASKS_DIR.resolve() not in task_path.parents:
        abort(400)
    shutil.rmtree(task_path)
    return redirect(url_for("tasks_list"))


if __name__ == "__main__":
    app.run(debug=True)
