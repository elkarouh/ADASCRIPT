#!/usr/bin/env python3
"""make_consultancy -- writes scenarios/12_consultancy.books: a year of a small IT consultancy.

Made up, not real: about seventy entries. Run: python3 make_consultancy.py [FILE]
"""
import sys
from pathlib import Path

VAT, c = 21, 100
CHART = [
    ("100000", "equity", "Share capital"), ("240000", "asset", "Laptops and furniture"),
    ("400000", "asset", "Trade receivables"), ("411000", "asset", "VAT receivable"),
    ("440000", "liability", "Trade payables"), ("450000", "liability", "Income tax payable"),
    ("451000", "liability", "VAT payable"), ("453000", "liability", "Withholding tax payable"),
    ("460000", "liability", "Advances received"), ("489000", "liability", "Credit card"),
    ("550000", "asset", "Bank"), ("610000", "expense", "Rent"), ("611000", "expense", "Software subscriptions"),
    ("614000", "expense", "Travel"), ("617000", "expense", "Subcontractors"),
    ("620000", "expense", "Wages and salaries"), ("621000", "expense", "Social contributions"),
    ("630000", "expense", "Depreciation"), ("670000", "expense", "Income tax"),
    ("700000", "revenue", "Consulting fees"),
]
entries = []

def entry(date, what, *postings):
    assert sum(a for _, a in postings) == 0, (date, what)
    entries.append((date, what, postings))

def vat(net): return net * VAT // 100

def sale(date, what, net, account, debit):
    v = vat(net)
    entry(date, what, (debit, net + v), (account, -net), ("VAT payable", -v))

def bought(date, what, net, account, credit):
    v = vat(net)
    entry(date, what, (account, net), ("VAT receivable", v), (credit, -(net + v)))

entry("2024-01-02", "The two founders put in 25,000", ("Bank", 25000 * c), ("Share capital", -25000 * c))
bought("2024-01-08", "Four laptops and desks, on credit", 9000 * c, "Laptops and furniture", "Trade payables")
entry("2024-02-05", "The laptops are paid", ("Trade payables", 9000 * c + vat(9000 * c)), ("Bank", -(9000 * c + vat(9000 * c))))

fees = [12500, 14000, 15500, 15000, 16500, 16000, 10000, 9500, 17000, 18000, 17500, 13500]
months = range(1, 13)
for m, net in zip(months, fees):
    if m == 9:   # the big project of September: 12,000 was paid in advance in May
        net += 18000
    sale(f"2024-{m:02d}-28", f"Invoices to clients for month {m:02d}", net * c, "Consulting fees", "Trade receivables")
    if m < 12:
        due = net * c + vat(net * c) - (12000 * c if m == 9 else 0)   # the advance was paid in May
        entry(f"2024-{m + 1:02d}-20", f"Clients pay the invoices of month {m:02d}", ("Bank", due), ("Trade receivables", -due))
entry("2024-05-10", "A client pays 12,000 in advance for the September project", ("Bank", 12000 * c), ("Advances received", -12000 * c))
entry("2024-09-30", "The advance is set against the September invoice", ("Advances received", 12000 * c), ("Trade receivables", -12000 * c))

for q, me in enumerate([3, 6, 9, 12], 1):
    bought(f"2024-{me:02d}-01", f"Office rent, Q{q}", 3600 * c, "Rent", "Bank")
    soft = [1500, 1500, 1800, 1800][q - 1] * c
    bought(f"2024-{me:02d}-26", f"Cloud and software subscriptions, Q{q}, on the company card", soft, "Software subscriptions", "Credit card")
    entry(f"2024-{me:02d}-28", f"The card statement of Q{q} is paid", ("Credit card", soft + vat(soft)), ("Bank", -(soft + vat(soft))))
    bought(f"2024-{me:02d}-15", f"A freelance developer's invoices, Q{q}", [6000, 8000, 3000, 7000][q - 1] * c, "Subcontractors", "Trade payables")
    pay = [6000, 8000, 3000, 7000][q - 1] * c
    if q < 4:
        nxt = {1: "04-12", 2: "07-12", 3: "10-12"}[q]
        entry(f"2024-{nxt}", f"The freelancer of Q{q} is paid", ("Trade payables", pay + vat(pay)), ("Bank", -(pay + vat(pay))))
    entry(f"2024-{me:02d}-20", f"Travel to clients, Q{q}: train tickets and mileage, paid (no VAT)", ("Travel", [900, 1100, 600, 1000][q - 1] * c), ("Bank", -[900, 1100, 600, 1000][q - 1] * c))
    gross, held, social = 22000 * c, 6000 * c, 5500 * c
    entry(f"2024-{me:02d}-25", f"Salaries of the two consultants, Q{q}: 22,000 gross, 6,000 withheld",
          ("Wages and salaries", gross), ("Bank", -(gross - held)), ("Withholding tax payable", -held))
    entry(f"2024-{me:02d}-26", f"Employer's social contributions, Q{q}", ("Social contributions", social), ("Bank", -social))
    if q < 4:
        nxt = {1: "04-15", 2: "07-15", 3: "10-15"}[q]
        entry(f"2024-{nxt}", f"Withholding tax of Q{q} paid to the tax office", ("Withholding tax payable", held), ("Bank", -held))

bal = {}
for d, _, ps in entries:
    q = (int(d[5:7]) - 1) // 3
    for a, v in ps:
        if a in ("VAT payable", "VAT receivable"):
            bal[q, a] = bal.get((q, a), 0) + v
for q in range(3):   # the last quarter's return falls in January
    p, r = bal[q, "VAT payable"], bal.get((q, "VAT receivable"), 0)
    entry(["2024-04-20", "2024-07-20", "2024-10-20"][q], f"VAT return Q{q+1}: {(-p - r)//c:,} paid", ("VAT payable", -p), ("VAT receivable", -r), ("Bank", p + r))

entry("2024-12-31", "The laptops and desks lose a third of their value", ("Depreciation", 3000 * c), ("Laptops and furniture", -3000 * c))
costs = ("Rent", "Software subscriptions", "Travel", "Subcontractors", "Wages and salaries", "Social contributions", "Depreciation")
profit = -sum(a for _, _, ps in entries for n, a in ps if n == "Consulting fees" or n in costs)
tax = profit * 25 // 100
entry("2024-12-31", f"Income tax, 25% of the profit of {profit//c:,}, owed", ("Income tax", tax), ("Income tax payable", -tax))

entries.sort(key=lambda e: e[0])
out = [
    "# scenarios/12_consultancy.books: made by make_consultancy.py. Amounts are in cents.",
    "title\t12. An IT consultancy's year: no stock, people are the cost",
    "about\tA made-up consultancy of two consultants and a freelancer. There is no stock: the cost is people. Clients are invoiced every month with 21% VAT and pay a month later; one client pays 12,000 in advance for a September project, which is then set against the invoice.",
    "about\tRent, software on a company card, a freelance developer, travel, salaries with withholding tax and social contributions, and the VAT returns are booked quarterly. At the year end the laptops are depreciated and the income tax on the profit is owed.",
    "currency\tUSD",
]
out += [f"account\t{n}\t{k}\t{name}" for n, k, name in CHART]
for d, what, ps in entries:
    out.append(f"entry\t{d}\t{what}")
    out += [f"posting\t{a}\t{v}" for a, v in ps]
Path(sys.argv[1] if len(sys.argv) > 1 else "scenarios/12_consultancy.books").write_text("\n".join(out) + "\n")
print(f"{len(entries)} entries; profit {profit//c:,}, tax {tax//c:,}")
