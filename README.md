# 🌱 Code Garden 

Platforma edukacyjna do nauki programowania, stworzona z myślą o dzieciach i młodzieży. Uczniowie mogą samodzielnie rozwiązywać zadania z Pythona, korzystając z podpowiedzi i automatycznego sprawdzania wyników.

## ✨ Funkcje

- Zadania z języka Python w różnych poziomach trudności
- Podpowiedzi i przykłady wyjścia
- System testów - podstawowe i brzegowe przypadki
- Szablon zadań i automatyczny ich generator (`create_task.py`)
- W pełni rozszerzalna struktura folderów otwarta na rozbudowę o kolejne środowiska

## 📁 Struktura katalogów

```
python/
├── tasks/
│   ├── 01_hello_world/
│   │   ├── task.json        # treść zadania
│   │   ├── test.json        # dane testowe
│   │   └── example.py       # przykładowe rozwiązanie
│   └── 00_template/         # szablon nowego zadania
└── tools/
    └── create_task.py       # skrypt do tworzenia nowych zadań
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
  "public_tests": [
    {
      "input": null,
      "expected_output": "Witaj Świecie"
    }
  ],
  "hidden_tests": []
}
```

## 🛠️ Tworzenie nowego zadania

1. Uruchom skrypt:
   ```bash
   python tools/create_task.py
   ```
2. Podaj ID i nazwę – skrypt utworzy nowy folder na podstawie szablonu.
3. Uzupełnij treść zadania, testy i przykładowe rozwiązanie w plikach json.

## 🔮 Plany rozwoju

W przyszłości **Code Garden** ma również wspierać rozwój dzieci w innych narzędziach:

- 🧱 **Scratch**
- 🪓 **Minecraft Education**
- 📱 **App Inventor**
