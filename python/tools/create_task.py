import os
import shutil
import json
from unidecode import unidecode

TEMPLATE_DIR = "python/tasks/00_template"
TASKS_DIR = "python/tasks"

def create_new_task():
    task_id = input("Podaj ID zadania: ").strip()
    title = unidecode(input("Podaj nazwę folderu zadania: ")).strip().replace(" ", "_").lower()

    folder_name = f"{int(task_id):02d}_{title}" #02d to dwucyfrowy format
    new_task_path = os.path.join(TASKS_DIR, folder_name)

    if os.path.exists(new_task_path):
        print("Folder już istnieje!")
        return

    # Kopiowanie folderu z szablonu
    shutil.copytree(TEMPLATE_DIR, new_task_path)

    # Aktualizacja plików JSON
    for file_name in ["task.json", "test.json"]:
        path = os.path.join(new_task_path, file_name)
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f) # ładuje jsona jako dict

        # Zmiana ID
        if file_name == "task.json":
            data["id"] = int(task_id)
        elif file_name == "test.json":
            data["task_id"] = int(task_id)

        with open(path, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2) # zapiuje dane z data (czyli dicta) do file
            # ensure_asci=False by nie zapisywało ą jako kod ascii
            # indent - formatowanie jsona

    print("Dodano zadanie")

if __name__ == "__main__":
    create_new_task()