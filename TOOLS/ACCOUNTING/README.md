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

The page shows one scenario at a time, picked at its top: a small
company's books that show one idea, with a few lines saying which.

| Scenario | What it shows |
|---|---|
| 1. The basics | money moving between accounts; revenue, costs and profit |
| 2. VAT | VAT paid is recovered, VAT charged is owed, the VAT return settles both |
| 3. Stock | goods bought for resale are an asset until sold, then Cost of sales |
| 4. Intellectual work | salaries for billed work are a cost; for lasting work (software) they are capitalised and depreciated |
| 5. A loan | borrowing is no income and repaying no cost; interest is |
| 6. Start from scratch | the whole chart of accounts, no transaction yet |

Change a scenario as you like: Start over brings it back as it was, and
Save as keeps your version as a scenario of its own.

The page draws the scenario's books: the accounts as nodes (drag them
about), the money that moved between them as arrows, the transactions below
the graph, then the accounts, the profit and loss and the balance sheet.

To record a transaction, click the account the money leaves: it freezes
(a dashed red ring) and no longer moves. Drag an arrow from it to the
account the money reaches, holding the button down, and let go there: a
popup asks for the date, what happened, the amount and the VAT. Enter
records it, Escape or Cancel closes it; a click on the frozen account, or
Escape, lets it go. With VAT, the amount is before VAT, and the VAT goes to
the account numbered 411... (a purchase: VAT to recover) or, when the money
leaves a revenue account, 451... (a sale: VAT to pay). The page checks what
it sends as the ledger does, and the ledger refuses what does not fit the
books, saying why.

Rarer things happen in the tables: each transaction and each account has a
Delete button (an account only goes once no transaction touches it), and
the last row of the accounts opens a new one. Hover over an account or an
arrow to see its transactions; "Graph only" gives the drawing the whole
window, with the transactions table under it.

### Scenarios

A scenario is `scenarios/NAME.books`, the books as text (`books_text.ady`:
a title, about lines, the accounts, the transactions), and `NAME.db`, the
database the page changes. ledger_server makes NAME.db from NAME.books the
first time NAME is shown, and again on Start over; Save as writes the books
shown to a new NAME.books. A new scenario is a new .books file: write it by
hand, or record it in the page and Save as. `./ledger --db X.db load
scenarios/NAME.books` and `./ledger --db X.db export` do the same on the
command line. `ledger_server --scenario NAME` starts on NAME, else on the
first.

| File | What it is |
|---|---|
| `accounting_model.ady` | accounts, transactions (`Entry`, made of `Posting`s that add up to zero), the graph and the statements; no GUI, no storage |
| `ledger.ady` | the books in an SQLite database, and a command line to keep them |
| `ledger_server.ady` | serves the page, and the books to it; records what the page sends |
| `books_text.ady` | the books as text, as the server and the page pass them |
| `accounting_app.ady` | the page: the books drawn, and recorded by clicking |
| `accounting.conf` | the ledger's settings and the chart of accounts it starts with |
| `scenarios/*.books` | the scenarios the page offers |
| `accounting_gui.ady` | the example as a static web page (`make gui`) |
| `test_accounting_model.ady`, `test_ledger.ady` | the tests (`make test`) |

## The ledger

```
make ledger
./ledger example                 # accounting.db, with Kleppmann's example company's whole year
./ledger show                    # balances, profit and loss, balance sheet
./ledger journal                 # every transaction, numbered, and what it did to each account
./ledger delete 3                # transaction 3, as journal numbers it
./ledger delete-account Fuel     # an account no transaction touches
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
| `settings` | `key` (title, about, currency), `value` |

## Next

A journal view (each arrow as debit and credit), a time slider, exercises
that check what the learner records, and the year-end closing.
