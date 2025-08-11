# Przykładowe rozwiązanie zadania
text = input().lower()
vowels = 'aąeęiouy'
count = 0
for c in text:
  if c in vowels:
    count+=1
print(count)