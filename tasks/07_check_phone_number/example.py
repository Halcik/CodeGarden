# Przykładowe rozwiązanie zadania

# Wczytaj numer, znormalizuj do +48 XXX XXX XXX lub wypisz INVALID.

import re

raw = input().strip()

# Wyciągnij tylko cyfry i ewentualny wiodący + (do detekcji +48)
plus = raw.startswith("+")
digits = re.sub(r"\D", "", raw)

# Logika:
# - jeśli 9 cyfr -> polski numer lokalny; poprzedź 48
# - jeśli 11 cyfr i zaczyna się od 48 -> użyj ostatnich 9 cyfr
# - jeśli było + i po usunięciu znaków mamy '48' + 9 cyfr -> też OK
normalized_9 = None

if len(digits) == 9:
    normalized_9 = digits
elif len(digits) == 11 and digits.startswith("48"):
    normalized_9 = digits[-9:]

if normalized_9 and len(normalized_9) == 9 and normalized_9.isdigit():
    # Zbuduj +48 XXX XXX XXX
    out = f"+48 {normalized_9[0:3]} {normalized_9[3:6]} {normalized_9[6:9]}"
    print(out)
else:
    print("INVALID")

