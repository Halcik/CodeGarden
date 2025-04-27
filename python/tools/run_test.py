import sys
from pathlib import Path
import json
from io import StringIO
from contextlib import redirect_stdout

input_data_list = []
input_index = 0

def fake_input(prompt=""):
  '''Zastępuje zwykłego inputa na czas testów ze względu na wyświetlane komunikaty'''
  global input_index
  if input_index< len(input_data_list):
    value = input_data_list[input_index]
    input_index+=1
    return value
  else:
    return ""

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

  example_file = Path(task_path, "example.py")

  with open(example_file, 'r', encoding='utf-8') as example:
    example_data = example.read()

  print("~~ Basic Tests ~~ ")
  original_input = input
  globals()["input"] = fake_input
  for basic_test in test_data['basic_tests']:
    output_data = basic_test['expected_output']
    input_index = 0
    if basic_test['input']:
      input_data_list = basic_test['input'].splitlines()
    else:
      input_data_list = []

    output_test = StringIO()
    with redirect_stdout(output_test):
      exec(example_data)
    output = output_test.getvalue().strip()
    
    print("Oczekiwane:", output_data)
    print("Uzyskane:", output)
    if output==output_data:
      print("✅ Test przebiegł pomyślnie")
    else:
      print("❌ Test NIE przebiegł pomyślnie")  

  globals()["input"] = original_input

    
  