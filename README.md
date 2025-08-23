# 🌱 Code Garden 

Platforma edukacyjna do nauki programowania, stworzona z myślą o dzieciach i młodzieży. Uczniowie mogą samodzielnie rozwiązywać zadania z Pythona, korzystając z podpowiedzi i automatycznego sprawdzania wyników.

## ✨ Funkcje

- Zadania z języka Python w różnych poziomach trudności
- Podpowiedzi i przykłady wyjścia
- System testów - podstawowe i brzegowe przypadki
- Szablon zadań i automatyczny ich generator (`create_task.py`)
- W pełni rozszerzalna struktura folderów otwarta na rozbudowę o kolejne środowiska

## 📌 Status projektu

Projekt jest w fazie **prototypu** – działa już podstawowa infrastruktura do tworzenia i uruchamiania zadań:

- Struktura katalogów (`tasks/`) z szablonem nowego zadania  
- Skrypt `create_task.py` do generowania zadań na podstawie szablonu  
- Obsługa plików `task.json` i `test.json` z opisem oraz testami  
- Skrypt `run_test.py` do lokalnego uruchamiania testów w osobnych procesach 
- Podgląd przykładowego rozwiązania (`example.py`)  

## 📁 Struktura katalogów

```
CODEGARDEN/
│
│── logs/                 # Zawiera logi działania programu
│   └── cg_YYYY-MM-DD.log
│
├── tasks/                # Wszystkie zadania
│   ├── 00_template/      # Szablon nowego zadania
│   │   ├── task.json     # Opis zadania (tytuł, opis, podpowiedź, limit czasu)
│   │   ├── test.json     # Testy (wejście, oczekiwane wyjście)
│   │   └── example.py    # Przykładowe (puste) rozwiązanie
│   │
│   ├── 01_hello_world/   # Przykład zadania
│   └── 02_sum_of_two_numbers/
│
├── tools/                # Skrypty narzędziowe
│   ├── create_task.py    # Tworzy nowe zadanie z szablonu
│   ├── logger.py         # Ustawia format logowania działania programu
│   └── run_test.py       # Uruchamia testy dla wybranego zadania
│
├── README.md             # Dokumentacja projektu
└── requirements.txt      # Lista wymaganych bibliotek

```

## 🧪 Format zadania (`task.json`)

```json
{
  "id": 1,
  "title": "Witaj Świecie",
  "description": "Napisz program, który wyświetli 'Witaj Świecie'.",
  "difficulty": "łatwe",
  "hint": "Użyj funkcji print().",
  "example_input": null,
  "example_output": "Witaj Świecie",
  "tags": ["print", "podstawy"],
  "function_name": null,
  "time_limit": 2
}
```

## 🔬 Format testów (`test.json`)

```json
{
  "task_id": 1,
  "basic_tests": [
    {
      "input": null,
      "expected_output": "Witaj Świecie",
      "checker": "contains"
    }
  ],
  "extra_tests": []
}
```

## 🛠️ Tworzenie nowego zadania

1. Uruchom skrypt:
   ```bash
   python tools/create_task.py
   ```
2. Podaj ID 
   - Wpisz ręcznie (musi być unikalne), lub kliknij `Enter`, aby skrypt automatycznie dobrał kolejne wolne ID.
3. Podaj nazwę - zostanie użyta w nazwie folderu. Skrypt utworzy nowy folder w `tasks/` na podstawie `tasks/00_template/`, np. 
    ```bash
    tasks/06_nazwa_zadania/
    ```
4. Uzupełnij treść zadania, testy i przykładowe rozwiązanie w plikach json.
   - `task.json` - Tutaj wpisz tytuł, opis, trudność, podpowiedź - informacje będą widoczne dla uczniów
   - `test.json` - dodaj przypadki testowe `basic_tests` oraz brzegowe `extra_tests`. To one będą testować napisany przez uczniów kod
   - `example.py` - przygotuj przykładowe rozwiązanie - będzie ono widoczne dla ucznia po "poddaniu się" lub porównaniu jego rozwiązania z Twoim.
5. Przetestuj zadanie, by upewnić się, że testy przechodzą zgodnie z Twoimi założeniami.   
    ```bash
    python tools/run_test.py 06_nazwa_zadania
    ```
## 👌Uruchomienie testów lokalnie
1. Uruchom skrypt i podaj pełną nazwę zadania (ze spacjami lub bez)
   ```b
   python tools/run_test.py 02_sum_of_two_numbers
   ```
   lub
      ```
   python tools/run_test.py 2 sum of two numbers
   ```
 2. Skrypt wczyta wybrane zadanie (jeśli istnieje) i wykona przypisane do niego testy. Po zakończeniu wyświetli ich wyniki oraz podsumowanie zaliczonych testów.
 ![alt text](https://jpcdn.it/img/0c8973d616c4c18f5a2a96dc114408a8.png)

## 🧾 Rodzaje `checker` w testach

Pole `checker` określa sposób porównania wyniku programu ucznia z oczekiwanym wynikiem (`expected_output`).

| checker     | Opis działania | Przykład `expected_output` | Kiedy używać |
|-------------|----------------|----------------------------|--------------|
| **exact**   | Wynik musi być identyczny (znak w znak) z `expected_output`. | `"TAK"` | Gdy wymagany jest dokładny format i treść, bez odstępstw. |
| **contains**| Wynik musi zawierać w sobie podany fragment. | `"Hello"` | Gdy dopuszczasz dodatkowy tekst, komentarze lub inne elementy obok właściwej odpowiedzi. |
| **regex**   | Wynik musi pasować do wzorca wyrażenia regularnego (Python `re.search`). | `^\\+48\\s\\d{3}\\s\\d{3}\\s\\d{3}$` | Gdy dopuszczasz wiele poprawnych wariantów formatu lub chcesz testować wzorce. |

### Uwagi
- Dla `regex` pamiętaj, aby **escape’ować backslashe** w JSON-ie (`\\d` zamiast `\d`).
- Jeśli oczekujesz **dokładnego tekstu** (np. `INVALID`), możesz w regexie użyć `^INVALID$`.

## 🔮 Plany rozwoju

W przyszłości **Code Garden** ma również wspierać rozwój dzieci w innych narzędziach:

- 🧱 **Scratch**
- 🪓 **Minecraft Education**
- 📱 **App Inventor**
