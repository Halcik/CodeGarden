import sys
from pathlib import Path
import json
from io import StringIO
from contextlib import redirect_stdout
import colorama

colorama.init()
input_data_list = []
input_index = 0

def fake_input(prompt=""):
  '''Zastępuje zwykłego inputa na czas testów ze względu na wyświetlane komunikaty'''
  global input_index
  if input_index < len(input_data_list):
    value = input_data_list[input_index]
    input_index+=1
    return value
  else:
    return ""

def test_code(task_path, type):
  "Funkcja służąca do uruchamiania testów na napisanym kodzie - obecnie na przykładach"
  global input_index
  global input_data_list

  original_input = input
  globals()["input"] = fake_input
  passed = 0
  total = 0

  task_file = Path(task_path, "task.json")
  test_file = Path(task_path, "test.json")
  example_file = Path(task_path, "example.py")

  with open(task_file, 'r', encoding="utf-8") as task:
    task_data = json.load(task)
  with open(test_file, 'r', encoding='utf-8') as test:
    test_data = json.load(test)
  with open(example_file, 'r', encoding='utf-8') as example:
    example_data = example.read()

  print(colorama.Style.BRIGHT+colorama.Fore.BLUE+f"\n~~ {type.replace('_', ' ').title()} ~~ ")
  for test in test_data[type]:
    print(colorama.Style.RESET_ALL, end="")
    total+=1
    output_data = test['expected_output'].strip()
    input_index = 0

    if test['input']:
      input_data_list = test['input'].splitlines()
    else:
      input_data_list = []

    output_test = StringIO()
    try:
      with redirect_stdout(output_test):
        exec(example_data)
    except Exception as e:
      output = f"Wystąpił błąd: {e}"
    else:
      output = output_test.getvalue().strip()
    
    print("Oczekiwane:", output_data)
    print("Uzyskane:", output)
    if output==output_data:
      passed+=1
      print(colorama.Fore.GREEN+"Test przebiegł pomyślnie")
    else:
      print(colorama.Fore.RED+"Test NIE przebiegł pomyślnie")
    print(colorama.Style.RESET_ALL, end="")   

  print(colorama.Style.BRIGHT+colorama.Fore.BLUE+f"\n{passed}/{total} testów przeszło ({round(passed/total*100)}%)")
  globals()["input"] = original_input

if __name__ == '__main__':
  task_path = Path(__file__).resolve().parent.parent / 'tasks'

  if len(sys.argv) < 2:
    print("Nie podano folderu przy starcie programu")
    exit()

  sys.argv[1] = '0'+sys.argv[1] if sys.argv[1].isdigit() and len(sys.argv[1])<2 else sys.argv[1] # dokleja 0 jeśli nie ma

  folder_name = '_'.join(sys.argv[1:]).lower()

  task_path = Path(task_path, folder_name)

  if not task_path.exists():
    print("Zadanie nie istnieje, sprawdź jego nazwę jeszcze raz")
    exit()
  print(f"Wybrano folder {folder_name}")

  test_code(task_path, 'basic_tests')
  test_code(task_path, 'extra_tests')



    
  