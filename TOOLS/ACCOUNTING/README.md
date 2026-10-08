# ACCOUNTING -- learning accounting as graph theory

A tool to learn accounting with, after Martin Kleppmann's
[Accounting for Computer Scientists](https://martin.kleppmann.com/2011/03/07/accounting-for-computer-scientists.html):
an account is a node, a transaction moves money along an edge, and the
statements are read off the balances. It started as the example in
`EXAMPLES/HTML`, and grows here.

## The tool

```
make app            # builds everything, starts ledger_server, opens http://127.0.0.1:8802/
```

The page draws the books of the database: the accounts as nodes (drag them
about), the money that moved between them as arrows, the transactions, the
balances and the statements below. To record a transaction, click the
account the money leaves (red), then the one it reaches (green), and give a
date, what happened and the amount. With VAT, the amount is before VAT, and
the VAT goes to the account numbered 411... (a purchase: VAT to recover) or,
when the money leaves a revenue account, 451... (a sale: VAT to pay). An
account is opened with a number, a kind and a name. The page checks what it
sends as the ledger does, and the ledger refuses what does not fit the
books, saying why. Hover over an account or an arrow to see its
transactions; "Graph only" gives the drawing the whole window.

The first `make app` makes accounting.db with the example company's year;
`make example` starts it over.

| File | What it is |
|---|---|
| `accounting_model.ady` | accounts, transactions (`Entry`, made of `Posting`s that add up to zero), the graph and the statements; no GUI, no storage |
| `ledger.ady` | the books in an SQLite database, and a command line to keep them |
| `ledger_server.ady` | serves the page, and the books to it; records what the page sends |
| `books_text.ady` | the books as text, as the server and the page pass them |
| `accounting_app.ady` | the page: the books drawn, and recorded by clicking |
| `accounting.conf` | the ledger's settings and the chart of accounts it starts with |
| `accounting_gui.ady` | the example as a static web page (`make gui`) |
| `test_accounting_model.ady`, `test_ledger.ady` | the tests (`make test`) |

## The ledger

```
make ledger
./ledger example                 # accounting.db, with the example company's year
./ledger show                    # balances, profit and loss, balance sheet
./ledger journal                 # every transaction, and what it did to each account
./ledger account 613100 expense Fuel
./ledger add 2012-01-02 "Printer paper" "Bank account=-12.10" Food=10.00 "VAT to recover=2.10"
```

A transaction is a date, a description, and postings `ACCOUNT=AMOUNT`: the
account by number or name, the amount added to it (negative: taken out).
The ledger refuses a transaction whose postings do not add up to zero, that
names an account it does not have, or that has several accounts on both
sides (the graph could not tell which pays which); nothing is written then.

### accounting.conf

```
database  accounting.db     # beside the config file, unless absolute
currency  USD

# number  kind        name
100000    equity      Capital
550000    asset       Bank account
700000    revenue     Sales
```

The numbers follow the Belgian chart of accounts (the first digit is the
class: 1 equity and long-term debts, 2 fixed assets, 3 stock, 4 receivables
and payables, 5 cash, 6 costs, 7 revenue); the kind is one of asset,
liability, equity, revenue, expense, and decides the account's colour.
`ledger init` opens the accounts of the config file that the database does
not have yet. `--config FILE` and `--db FILE` choose others.

### The database

| Table | Columns |
|---|---|
| `accounts` | `number` (key), `name` (unique), `kind` |
| `transactions` | `id`, `date` (ISO, 2011-03-07), `what` |
| `postings` | `tx`, `account` (a number), `amount` (in cents) |

## Next

A journal view (each arrow as debit and credit), a time slider, exercises
that check what the learner records, and the year-end closing.
