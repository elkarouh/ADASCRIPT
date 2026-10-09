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
| 3a. Stock, the Belgian way | purchases go to 604 Purchases (achats, aankopen); at the year end the goods still in stock go back to Stock through 609 Stock variation |
| 3b. Stock, the international way | the same transactions: goods bought for resale are Stock, an asset, until sold, then Cost of sales |
| 4. Intellectual work | salaries for billed work are a cost; for lasting work (software) they are capitalised and depreciated |
| 5. A loan | borrowing is no income and repaying no cost; interest is |
| 6. Salaries | an employee costs the gross salary plus the employer's social security; what is withheld is owed to the ONSS and the tax office |
| 7. A customer's deposit | money received before delivery is a liability, not revenue, until the goods are invoiced |
| 8. A credit note and a bad debt | a credit note cancels part of a sale; an unpaid debt is written off as a cost |
| 9. The year end | prepaid and accrued expenses put each cost in the year it belongs to |
| 10. A small company's year | the whole of one year, each kind of transaction once, down to the stock count, the depreciation and the income tax |
| 11. Start from scratch | the whole chart of accounts, no transaction yet |

Change a scenario as you like: Start over brings it back as it was, and
Save as keeps your version as a scenario of its own.

The page draws the scenario's books: the accounts as nodes (drag them
about), the money that moved between them as arrows, the transactions below
the graph, then the accounts, the profit and loss and the balance sheet.
The drawing is laid out like a balance sheet: a dashed line down the middle
puts the assets (activa) on the left and the liabilities and equity
(passiva) on the right; below a dashed line across, the costs sit on the
left and the revenue on the right, as in a profit and loss account. An
account can be dragged anywhere inside its own quarter, not out of it.
Each arrow is a cubic spline, bowed just enough to pass around the other
accounts and stay inside the drawing; it finds its way again whenever an
account moves.
If the accounts have been dragged into a mess, Tidy up lays them out again:
each in its quarter, and within it placed so that the arrows are short and
run over as few other accounts as possible.

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

"Play the transactions" replays the books one transaction at a time: the
graph, the balances and the statements as they stood after it, its arrows
and accounts in orange and its row in the table highlighted. Pause, Previous
and Next step through by hand; Show all ends the replay.

### Scenarios

A scenario is `scenarios/NAME.books`, the books as text (`books_text.ady`:
a title, about lines, the accounts, the transactions), and `NAME.db`, the
database the page changes. ledger_server makes NAME.db from NAME.books the
first time NAME is shown, and again on Start over; Save as writes the books
shown to a new NAME.books. A new scenario is a new .books file: write it by
hand, record it in the page and Save as, or start one with `./ledger new
NAME`. `ledger_server --scenario NAME` starts on NAME, else on the first.

| File | What it is |
|---|---|
| `accounting_model.ady` | accounts, transactions (`Entry`, made of `Posting`s that add up to zero), the graph and the statements; no GUI, no storage |
| `ledger.ady` | the books in an SQLite database, the scenarios' files, and a command line to keep them |
| `ledger_server.ady` | serves the page, and the books to it; records what the page sends |
| `books_text.ady` | the books as text, as the server and the page pass them |
| `accounting_app.ady` | the page: the books drawn, and recorded by clicking |
| `accounting.conf` | the currency and the chart of accounts a new scenario starts with |
| `scenarios/*.books` | the scenarios the page offers |
| `accounting_gui.ady` | the example as a static web page (`make gui`) |
| `test_accounting_model.ady`, `test_ledger.ady` | the tests (`make test`) |

## The ledger

The page's scenarios, on the command line: the same files, the same books.

```
make ledger
./ledger list                          # the scenarios, with their titles
./ledger 2_vat show                    # balances, profit and loss, balance sheet
./ledger 2_vat journal                 # every transaction, numbered, and what it did to each account
./ledger 2_vat add 2011-05-02 "Printer paper" "Bank account=-12.10" Furniture=10.00 "VAT to recover=2.10"
./ledger 2_vat delete 6                # transaction 6, as journal numbers it
./ledger 2_vat account 613100 expense Fuel
./ledger 2_vat delete-account Fuel     # an account no transaction touches
./ledger 2_vat start-over              # back as 2_vat.books has it
./ledger 2_vat save-as vat_mine        # a new scenario, from these books
./ledger 2_vat export                  # the books as a .books file holds them
./ledger new mine                      # a new scenario: the config's chart, no transaction
```

A transaction is a date, a description, and postings `ACCOUNT=AMOUNT`: the
account by number or name, the amount added to it (negative: taken out).
The ledger refuses a transaction whose postings do not add up to zero, that
names an account it does not have, or that has several accounts on both
sides (the graph could not tell which pays which); nothing is written then.

### accounting.conf

```
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
`ledger new NAME` starts a scenario with these accounts. `--config FILE`
chooses another config, and with it the scenarios/ beside it.

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
