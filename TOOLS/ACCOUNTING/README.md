# ACCOUNTING -- learning accounting as graph theory

A tool to learn accounting with, after Martin Kleppmann's
[Accounting for Computer Scientists](https://martin.kleppmann.com/2011/03/07/accounting-for-computer-scientists.html):
an account is a node, a transaction moves money along an edge, and the
statements are read off the balances. It started as the example in
`EXAMPLES/HTML`, and grows here.

| File | What it is |
|---|---|
| `accounting_model.ady` | accounts, transactions (`Entry`, made of `Posting`s that add up to zero), the graph and the statements; no GUI, no storage |
| `ledger.ady` | the books in an SQLite database, and a command line to keep them |
| `accounting.conf` | the ledger's settings and the chart of accounts it starts with |
| `accounting_gui.ady` | the example as a web page |
| `accounting_live.ady` | the same page in the browser: drag the accounts, hover for their transactions |
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

The pages still draw the example built in code; next they read the ledger,
through a small server, and accounts and transactions can be added from the
page. Then: a journal view (each arrow as debit and credit), a time slider,
exercises that check what the learner records, and the year-end closing.
