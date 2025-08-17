import sys
from pathlib import Path
import json
from io import StringIO
from contextlib import redirect_stdout
import colorama
import multiprocessing
import importlib.util
import re

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


def script_worker(student_code: str, q: multiprocessing.Queue):
  '''Uruchamia skrypt w osobnym procesie'''
  global input_data_list, input_index # bo fake_input bierze globalne
  input_data_list = q.get()
  input_index = 0
  output_test = StringIO()
  try:
    with redirect_stdout(output_test):
      env = {"__name__":"__main__", "input": fake_input} #podmianka do przekazania
      exec(student_code, env, env) # sorce, globals, locals
  except Exception as e:
    q.put(("err", f"Wystąpił błąd: {e}"))
  else:
    q.put(("ok", output_test.getvalue().strip())) 


def function_worker(student_path_file: str, function_name: str, name_of_file: str, q: multiprocessing.Queue):
  """Worker, który ładuje moduł w osobnym procesie i wywołuje funkcję."""
  try:
    input_data_list = q.get()
    spec = importlib.util.spec_from_file_location(name_of_file, student_path_file)
    modul = importlib.util.module_from_spec(spec)
    sys.modules[name_of_file] = modul
    spec.loader.exec_module(modul)

    func = getattr(modul, function_name) # zwraca obiekt funkcji z modułu.
    output = func(*input_data_list) # normalnie się wywołuje
    q.put(("ok", output))
  except Exception as e:
    q.put(("err", f"Wystąpił błąd: {e}"))


def test_script(example_data, timeout):
  '''Funkcja do testowania skryptu'''
  q = multiprocessing.Queue()
  q.put(input_data_list)
  p = multiprocessing.Process(target=script_worker, args=(example_data, q))
  p.start()

  p.join(timeout)
  if p.is_alive():
    p.terminate()
    p.join() # dla upewnienia
    return "TIMEOUT"
  if q.empty():
    return "BRAK WYNIKU"
  
  status, output = q.get()
  return output


def test_function(example_file, function_name, timeout):
  '''Funkcja do testowania wyjść (return) funkcji'''
  path_to_import = str(example_file)
  name_of_file = example_file.stem

  q = multiprocessing.Queue()
  q.put(input_data_list)
  p = multiprocessing.Process(target=function_worker, args=(path_to_import, function_name, name_of_file, q))
  p.start()

  p.join(timeout)
  if p.is_alive():
    p.terminate()
    p.join() # dla upewnienia
    return "TIMEOUT"
  if q.empty():
    return "BRAK WYNIKU"
  
  status, output = q.get()
  return output


def print_test_result(output_data, output, checker) -> int:
  '''Funkcja wyświetla podsumowanie pojedynczego testu.
  Zwraca 1, gdy przebiegł pomyślnie, 0 gdy się nie powiódł'''

  print(f"Oczekiwane: {output_data}")
  print(f"Uzyskane: {output}")
  print(f"Forma sprawdzania: {checker}")

  if (
    (checker == "exact" and output_data == output) or
    (checker == "contains" and output_data in output) or
    (checker == "regex" and re.search(output_data, output))
    ):
    print(colorama.Fore.GREEN+"Test przebiegł pomyślnie")
    return 1
  
  print(colorama.Fore.RED+"Test NIE przebiegł pomyślnie")
  print(colorama.Style.RESET_ALL, end="")  
  return 0


def test_code(task_path, type_test):
  "Funkcja służąca do uruchamiania testów na napisanym kodzie - obecnie na przykładach"
  global input_index, input_data_list

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

  function_name = task_data['function_name']
  timeout = task_data['time_limit']

  print(colorama.Style.BRIGHT+colorama.Fore.BLUE+f"\n~~ {type_test.replace('_', ' ').title()} ~~ ")
  for test in test_data[type_test]:
    print(colorama.Style.RESET_ALL, end="")
    total+=1
    output_data = test['expected_output'].strip()
    input_index = 0

    if test['input']:
      input_data_list = test['input'].splitlines()
    else:
      input_data_list = []

    if function_name:
      output = test_function(example_file, function_name, timeout)  
    else:
      output = test_script(example_data, timeout)

    passed += print_test_result(output_data, output, test['checker'])  

  print(colorama.Style.BRIGHT+colorama.Fore.BLUE+f"\n{passed}/{total} testów przeszło ({round(passed/total*100) if total else 100}%)")

if __name__ == '__main__':
  task_path = Path(__file__).resolve().parent.parent / 'tasks'

  if len(sys.argv) < 2:
    print("Nie podano folderu przy starcie programu")
    exit()

  sys.argv[1] = '0'+sys.argv[1] if sys.argv[1].isdigit() and len(sys.argv[1])<2 else sys.argv[1] # dokleja 0 jeśli nie ma

  folder_name = '_'.join(sys.argv[1:]).lower()

  task_path = task_path / folder_name

  if not task_path.exists():
    print("Zadanie nie istnieje, sprawdź jego nazwę jeszcze raz")
    exit()
  print(f"Wybrano folder {folder_name}")

  test_code(task_path, 'basic_tests')
  test_code(task_path, 'extra_tests')
