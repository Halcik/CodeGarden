import shutil
import json
from unidecode import unidecode
from pathlib import Path
import re

BASE = Path(__file__).resolve().parent.parent
TEMPLATE_DIR = BASE / "tasks" / "00_template"
TASKS_DIR = BASE / "tasks"

def next_free_id() -> str:
    ids = []
    for path in TASKS_DIR.iterdir():
        if path.is_dir and re.match(r"^\d{2,}_", path.name):
            try:
                ids.append(int(path.name.split("_")[0]))
            except Exception as e:
                pass
    return str((max(ids)+1)) if ids else "1"        

def create_new_task():
    task_id = input("Podaj ID zadania (Enter = następne wolne): ").strip()
    if not task_id:
        task_id = next_free_id()

    task_id = int(task_id)    
    title = unidecode(input("Podaj nazwę folderu zadania: ")).strip().replace(" ", "_").lower()

    folder_name = f"{task_id:02d}_{title}" #02d to dwucyfrowy format
    new_task_path = TASKS_DIR / folder_name

    if new_task_path.exists():
        print("Folder już istnieje!")
        return

    # Kopiowanie folderu z szablonu
    shutil.copytree(TEMPLATE_DIR, new_task_path)

    # Aktualizacja plików JSON
    for file_name in ["task.json", "test.json"]:
        path = new_task_path / file_name
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) # ładuje jsona jako dict

        # Zmiana ID
        if file_name == "task.json":
            data["id"] = task_id
        elif file_name == "test.json":
            data["task_id"] = task_id

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2) # zapiuje dane z data (czyli dicta) do file
            # ensure_asci=False by nie zapisywało ą jako kod ascii
            # indent - formatowanie jsona

    print(f"Dodano zadanie w ścieżce: {new_task_path}")

if __name__ == "__main__":
    create_new_task()