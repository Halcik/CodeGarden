# Przykładowe rozwiązanie zadania
n = int(input("Podaj liczbę końca zakresu: "))
for i in range(2, n+1, 2):
    print(i)

# Wersja z modulo
n = int(input("Podaj liczbę końca zakresu: "))
for i in range(n+1):
    if i%2==0:
        print(i)