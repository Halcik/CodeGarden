# Przykładowe rozwiązanie zadania
text = input().lower()
vowels = 'aąeęiouy'
count = 0
for c in text:
  if c in vowels:
    count+=1
print(count)    

# Wersja z forem w jednej linii
text = input().lower()
vowels = 'aąeęiouy'
count = sum(1 for c in text if c in vowels)
print(count)