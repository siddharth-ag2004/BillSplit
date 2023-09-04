from rich import print


def main() -> None:
    num_people = int(input("Number of people: "))
    L = []
    for i in range(1, num_people + 1):
        L.append(eval(input(f"Person {i}: ")))
    other_charges = eval(input("Other charges: "))

    total = sum(L)
    weights = [x / total for x in L]
    print(f"{total} + {charges} = {total + charges}")
    [
        print(f"Person {i}: {l + other_charges * w}")
        for i, (l, w) in enumerate(zip(L, weights), start=1)
    ]


if __name__ == "__main__":
    main()
