import sys
from pathlib import Path
import json


if __name__ == '__main__':
  task_path = Path(Path(sys.argv[0]).parent.parent, 'tasks')

  if not len(sys.argv) >= 2:
    print("Nie podano folderu przy starcie programu")
    exit()

  sys.argv[1] = '0'+sys.argv[1] if sys.argv[1].isdigit() and len(sys.argv[1])<2 else sys.argv[1]
  folder_name = '_'.join(sys.argv[1:]).lower()  
  task_path = Path(task_path, folder_name)

  if not task_path.exists():
    print("Zadanie nie istnieje, sprawdź jego nazwę jeszcze raz")
    exit()
  print(f"Wybrano folder {folder_name}")

  task_file = Path(task_path, "task.json")
  test_file = Path(task_path, "test.json")

  with open(task_file, 'r', encoding="utf-8") as task:
    task_data = json.load(task)

  with open(test_file, 'r', encoding='utf-8') as test:
    test_data = json.load(test)

  print(task_data)
  print(test_data)
