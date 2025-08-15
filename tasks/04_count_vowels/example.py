# Przykładowe rozwiązanie zadania
text = input("Podaj tekst: ").lower()
vowels = 'aąeęiouy'
count = 0
for c in text:
  if c in vowels:
    count+=1
print(f"W tekście jest {count} samogłosek")