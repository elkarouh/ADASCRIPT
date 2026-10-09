#!/usr/bin/env python3
"""make_bakery -- writes scenarios/11_bakery.books: a year of a small bakery-cafe.

Made up, not real: about sixty entries, so that the whole year can be followed.
Run: python3 make_bakery.py [scenarios/11_bakery.books]
"""
import sys
from pathlib import Path

VAT = 21
CHART = [
    ("100000", "equity", "Share capital"), ("173000", "liability", "Bank loans"),
    ("240000", "asset", "Ovens and equipment"), ("400000", "asset", "Trade receivables"),
    ("411000", "asset", "VAT receivable"), ("440000", "liability", "Trade payables"),
    ("450000", "liability", "Income tax payable"), ("451000", "liability", "VAT payable"),
    ("453000", "liability", "Withholding tax payable"), ("550000", "asset", "Bank"),
    ("604000", "expense", "Ingredients"), ("610000", "expense", "Rent"),
    ("612000", "expense", "Energy"), ("620000", "expense", "Wages and salaries"),
    ("621000", "expense", "Social contributions"), ("630000", "expense", "Depreciation"),
    ("650000", "expense", "Interest expense"), ("670000", "expense", "Income tax"),
    ("700000", "revenue", "Shop sales"), ("701000", "revenue", "Catering"),
]
entries = []

def entry(date, what, *postings):
    assert sum(a for _, a in postings) == 0, (date, what)
    entries.append((date, what, postings))

def vat(net):
    return net * VAT // 100

def sale(date, what, net, account, debit):
    v = vat(net)
    entry(date, what, (debit, net + v), (account, -net), ("VAT payable", -v))

def bought(date, what, net, account, credit):
    v = vat(net)
    entry(date, what, (account, net), ("VAT receivable", v), (credit, -(net + v)))

c = 100  # cents per dollar
entry("2024-01-02", "The owner puts in 30,000", ("Bank", 30000 * c), ("Share capital", -30000 * c))
entry("2024-01-03", "The bank lends 20,000 for the ovens", ("Bank", 20000 * c), ("Bank loans", -20000 * c))
bought("2024-01-05", "Two ovens and a counter, paid", 24000 * c, "Ovens and equipment", "Bank")

shop = [9800, 10400, 12100, 13300, 14600, 15200, 15900, 15100, 13800, 12900, 12400, 16700]
for m, net in enumerate(shop, 1):
    sale(f"2024-{m:02d}-28", f"Shop takings, month {m:02d} (cash and cards)", net * c, "Shop sales", "Bank")

for q, month_end in enumerate([3, 6, 9, 12], 1):
    bought(f"2024-{month_end:02d}-15", f"Flour, butter, coffee and the rest, Q{q}, on credit", [13000, 15500, 17000, 16000][q - 1] * c, "Ingredients", "Trade payables")
    pay_net = [13000, 15500, 17000, 16000][q - 1] * c
    pay = pay_net + vat(pay_net)
    if q < 4:
        nxt = {1: "2024-04-10", 2: "2024-07-10", 3: "2024-10-10"}[q]
        entry(nxt, f"The supplier of Q{q} is paid", ("Trade payables", pay), ("Bank", -pay))
    bought(f"2024-{month_end:02d}-01", f"Rent of the shop, Q{q}", 3000 * c, "Rent", "Bank")
    bought(f"2024-{month_end:02d}-20", f"Gas and electricity, Q{q}", [2100, 1400, 1100, 1900][q - 1] * c, "Energy", "Bank")
    gross, held, social = 14000 * c, 3500 * c, 3500 * c
    entry(f"2024-{month_end:02d}-25", f"Wages of the baker and two shop assistants, Q{q}: {gross//c:,} gross, {held//c:,} withheld",
          ("Wages and salaries", gross), ("Bank", -(gross - held)), ("Withholding tax payable", -held))
    entry(f"2024-{month_end:02d}-26", f"Employer's social contributions, Q{q}", ("Social contributions", social), ("Bank", -social))
    entry(f"2024-{month_end:02d}-27", f"Interest on the loan, Q{q}", ("Interest expense", 250 * c), ("Bank", -250 * c))
    if q < 4:
        nxt = {1: "2024-04-15", 2: "2024-07-15", 3: "2024-10-15"}[q]
        entry(nxt, f"Withholding tax of Q{q} paid to the tax office", ("Withholding tax payable", held), ("Bank", -held))
    cat = [3200, 4100, 3600, 6800][q - 1] * c
    sale(f"2024-{month_end:02d}-20", f"Catering invoices of Q{q} (offices, a wedding), on credit", cat, "Catering", "Trade receivables")
    if q < 4:
        due = cat + vat(cat)
        nxt = {1: "2024-04-25", 2: "2024-07-25", 3: "2024-10-25"}[q]
        entry(nxt, f"The customers of Q{q} pay", ("Bank", due), ("Trade receivables", -due))

# one quarterly VAT return per quarter: payable less receivable, in the month after
class Sums(dict):
    def __missing__(self, k): return 0
bal = Sums()
for d, _, ps in entries:
    q = (int(d[5:7]) - 1) // 3
    for a, v in ps:
        if a in ("VAT payable", "VAT receivable"):
            bal[q, a] += v
for q in range(4):
    owed = -bal[q, "VAT payable"] - bal[q, "VAT receivable"]
    when = ["2024-04-20", "2024-07-20", "2024-10-20", "2025-01-20"][q]
    entry(when, f"VAT return Q{q+1}: {owed//c:,} paid", ("VAT payable", -bal[q, "VAT payable"]), ("VAT receivable", -bal[q, "VAT receivable"]), ("Bank", -owed))

entry("2024-12-31", "The ovens and counter lose a fifth of their value", ("Depreciation", 4800 * c), ("Ovens and equipment", -4800 * c))
profit = -sum(a for d, _, ps in entries for n, a in ps if n in ("Shop sales", "Catering", "Ingredients", "Rent", "Energy", "Wages and salaries", "Social contributions", "Depreciation", "Interest expense"))
tax = profit * 25 // 100
entry("2024-12-31", f"Income tax, 25% of the profit of {profit//c:,}, owed", ("Income tax", tax), ("Income tax payable", -tax))

entries.sort(key=lambda e: e[0])
out = [
    "# scenarios/11_bakery.books: made by make_bakery.py. Amounts are in cents.",
    "title\t11. A bakery-cafe's year: monthly takings, quarterly bills",
    "about\tA made-up small bakery-cafe with a shop and some catering: the owner's money and a bank loan buy the ovens; takings are booked monthly with 21% VAT; ingredients, rent, energy, wages, social contributions and loan interest are booked quarterly, as are the catering invoices and the VAT returns.",
    "about\tAt the year end the ovens are depreciated and the income tax on the profit is owed. About sixty entries in all: few enough to follow a whole year in the graph.",
    "currency\tUSD",
]
out += [f"account\t{n}\t{k}\t{name}" for n, k, name in CHART]
for d, what, ps in entries:
    out.append(f"entry\t{d}\t{what}")
    out += [f"posting\t{a}\t{v}" for a, v in ps]
dest = Path(sys.argv[1] if len(sys.argv) > 1 else "scenarios/11_bakery.books")
dest.write_text("\n".join(out) + "\n")
b = sum(v for _, _, ps in entries for n, v in ps if n == "Bank")
print(f"{len(entries)} entries; profit {profit//c:,}, tax {tax//c:,}, bank {b//c:,}")
