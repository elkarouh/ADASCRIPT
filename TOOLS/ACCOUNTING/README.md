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

The graph and its controls (scenario picker, replay, date slider, Exercise,
Close the year) stay at the top; below them four tabs hold the detail views:
Transactions (the journal, with the Debit and credit toggle), T-accounts,
Accounts (the table, and opening an account) and Statements (profit and loss,
balance sheet, ratios). The chosen tab is kept when you switch scenario, and
the explanations (introduction, section captions, the how-to hint) stay hidden until you press Help.

The page shows one scenario at a time, picked at its top: a small
company's books that show one idea, with a few lines saying which.

| Scenario | What it shows |
|---|---|
| 1. The basics | money moving between accounts; revenue, costs and profit |
| 2. VAT | VAT paid is recovered, VAT charged is owed, the VAT return settles both |
| 3a. Stock, the Belgian way | purchases go to 604 Purchases (achats, aankopen); at the year end the goods still in stock go back to Goods for resale through 609 Change in stock |
| 3b. Stock, the international way | the same transactions: goods bought for resale are Goods for resale, an asset, until sold, then Cost of sales |
| 4. Intellectual work | salaries for billed work are a cost; for lasting work (software) they are capitalised and depreciated |
| 5. A loan | borrowing is no income and repaying no cost; interest is |
| 6. Salaries | an employee costs the gross salary plus the employer's social security; what is withheld is owed to the ONSS and the tax office |
| 7. A customer's deposit | money received before delivery is a liability, not revenue, until the goods are invoiced |
| 8. A credit note and a bad debt | a credit note cancels part of a sale; an unpaid debt is written off as a cost |
| 9. The year end | prepaid and accrued expenses put each cost in the year it belongs to |
| 10. A small company's year | the whole of one year, each kind of transaction once, down to the stock count, the depreciation and the income tax |
| 11. A bakery-cafe's year | a made-up small business in about sixty entries: monthly takings, quarterly bills, VAT returns, the year-end depreciation and tax |
| 12. An IT consultancy's year | a made-up business without stock, in about seventy entries: monthly invoices, an advance from a client, a freelancer, salaries, VAT returns and the year-end tax |
| 11. Start from scratch | the whole chart of accounts, no transaction yet |

Change a scenario as you like: Start over brings it back as it was, and
Save as keeps your version as a scenario of its own; Delete scenario removes the one shown (after asking), with its database.

The page draws the scenario's books: the accounts as nodes (drag them
about), the money that moved between them as arrows, the transactions below
the graph, then the accounts, the profit and loss and the balance sheet.
The drawing is laid out like a balance sheet: a dashed line down the middle
puts the assets (activa) on the left and the liabilities and equity
(passiva) on the right; below a dashed line across, the costs sit on the
left and the revenue on the right, as in a profit and loss account. An
account can be dragged anywhere inside its own quarter, not out of it.
Each arrow is a spline through two waypoints, pushed aside just enough to
weave around the other accounts and stay inside the drawing, and each
amount is written beside its arrow where it covers no account, title or
other amount; both are worked out again whenever an account moves.
If the accounts have been dragged into a mess, Tidy up (beside Save as) lays them out again:
each in its quarter, and within it placed so that the arrows are short and
run over as few other accounts as possible.
With more than a dozen accounts, "Group by" (beside Play) draws the accounts whose numbers
start with the same digits as one node: 2 digits turns 143 accounts of an ERP into about forty,
a node's amount is the sum of its accounts and an arrow between two nodes is the sum of the
transactions between them (those inside a group vanish). Hover over a group to see its accounts;
click it to open it: its accounts are drawn on their own, the other groups stay closed, and
Close groups folds them again. A big chart starts grouped by as many digits as leave about thirty
nodes. The page counts in whole numbers below 2,147,483,648 cents, so a grouping whose sums
would pass that is refused: group by more digits. "fold" draws the accounts that fewer than 2, 5, 10, ... transactions touch as one node a kind
("8 quiet expense"); on the ERP data, fewer than 50 leaves 29 nodes with no grouping at all.
To make your own groups, hold Shift and click two or more accounts of one kind (a blue dashed
outline marks them), press "Merge the N picked..." and name the group; click it to take it apart.
A group cannot be frozen or be the end of
a new arrow, and the Exercise waits until no account is grouped.
The small circle where the two dashed lines cross resizes the quarters:
drag it, and when you let go the accounts are tidied into their new
quarters.
The accounts are drawn as boxes holding their name and balance, stacked
one column a quarter like the lines of a balance sheet; an arrow leaves
the side of one box and enters the side of the other, across the middle,
or round the outside of a column between two boxes in it. A box is as
high as its arrows need: the more of those coming in or going out it has,
the taller it is, and its column restacks as it grows.

To record a transaction, click the account the money leaves: it freezes
(a dashed red ring) and no longer moves. Drag an arrow from it to the
account the money reaches, holding the button down, and let go there: a
popup asks for the date, what happened, the amount and the VAT. Enter
records it, Escape or Cancel closes it; a click on the frozen account, or
Escape, lets it go. With VAT, the amount is before VAT, and the VAT goes to
the account numbered 411... (a purchase: VAT receivable) or, when the money
leaves a revenue account, 451... (a sale: VAT payable). The page checks what
it sends as the ledger does, and the ledger refuses what does not fit the
books, saying why.

Rarer things happen in the tables: each transaction and each account has a
Delete button (an account only goes once no transaction touches it), and
the last row of the accounts opens a new one. Hover over an account (its number, name and balance, then its
transactions) or an
arrow to see its transactions.

"Play the transactions" replays the books one transaction at a time: the
graph, the balances and the statements as they stood after it, its arrows
and accounts in orange and its row in the table highlighted. Pause, Previous
and Next step through by hand; Show all ends the replay. The transaction's
own words ("The founders put in 20,000") stand large above the graph, its
number and date small above them, and each quarter's title carries its
total as it stood then: Activa (20,000.00), Passiva (20,000.00).

To follow one account's story, click it so that it freezes: the Play button
becomes "Play Bank's transactions", and Play, Previous and Next go
through only the transactions touching it, in order, the balances of every
account as they stood after each ("Bank: transaction 4 of 10
(number 5 of 16)"). A student sees how the bank account fills and empties,
where a customer's debt comes from and how it is settled, or what a VAT
account collects before it is paid; Show all lets the account go.

Under the replay buttons, the date slider goes from one day the
transactions are dated to the next: the graph, the quarter totals, the
accounts, the profit and loss account and the balance sheet are those of the
books as they stood at the end of that day ("Books as at 2011-07-31"),
whatever the replay was doing before. It is the quickest way to ask what
the balance sheet looked like at the end of March. Activa and Passiva differ
by the costs less the revenue so far, until the year is closed.

Under the balance sheet, five ratios are read off it, as a banker would:
working capital (the current assets less the debts due within the year),
the current ratio (the same two, divided), the quick ratio (without the
stock), solvency (equity over total assets) and net margin (profit over
revenue), each with a line saying what it tells. They are those of the books
as shown, so they move with the replay and the date slider: the current
ratio of scenario 10 is 8.80 at the year's end and 2.76 after the first
purchase on credit. The chart's numbers say which accounts are fixed assets
(2...), stock (3...), long-term debt (1... liabilities) or current.

"Debit and credit", at the top of the Transactions tab, writes the books the way an accountant does. The
transactions list becomes a journal: each transaction has a line for every
account it touches, the debits first and the credits, indented, after them
(Furniture and equipment 5,000.00 and VAT receivable 1,050.00 in debit,
Bank 6,050.00 in credit), and the accounts table shows each balance as a
debit or a credit. Under the transactions, each account touched is drawn as a T:
its debits on the left, its credits on the right, and the balance, the
bigger side less the smaller, under it. An arrow in the graph goes from the
account that is credited to the account that is debited; assets and
expenses grow on the debit side, liabilities, equity and revenue on the
credit side. The T-accounts follow the replay and the exercise, counting only the
transactions shown so far. "Plus and minus" brings the first view back.

"Exercise" turns the scenario into a quiz. The graph shows the books as
they stood before a transaction, the transaction is told in words in the
card ("Goods for resale bought on credit: 8,000 plus 21% VAT"), and the
student draws the arrow: click the account the money leaves, then drag to
the account it reaches. A right arrow is confirmed with what the
transaction did to each account (here Bank -6,050.00, VAT receivable
+1,050.00, Furniture and equipment +5,000.00), and the next transaction is
asked; a wrong one says whether it goes the other way round, or just not
that one, and "Show the answer" gives up on it. Only the transactions
solved so far are listed, the score counts the ones right at the first
try, and "Stop the exercise" goes back to the books. Nothing is recorded:
the books are not changed.

"Close the year" (shown while there is a cost or revenue balance to close)
does what an accountant does on 31 December: it posts two entries dated the
end of the last transaction's year, one moving each cost into retained
earnings (opened as 140000 if the books have no such account) and one
moving each revenue, so the costs and the revenue end at zero and the
profit sits in equity. Activa and Passiva, which differed by the profit
until then, are now equal. The two entries are ordinary transactions: they
are replayed with the others, and Delete takes them back.

### Scenarios

A scenario is `scenarios/NAME.books`, the books as text (`books_text.ady`:
a title, about lines, the accounts, the transactions), and `NAME.db`, the
database the page changes. ledger_server makes NAME.db from NAME.books the
first time NAME is shown, again on Start over, and again when NAME.books
is newer than NAME.db (a new version of the scenario came in, with git pull); Save as writes the books
shown to a new NAME.books. A new scenario is a new .books file: write it by
hand, record it in the page and Save as, or start one with `./backend/ledger new
NAME`. `ledger_server --scenario NAME` starts on NAME, else on the first.

| File | What it is |
|---|---|
| `backend/` (native, compiled to C) | |
| `backend/ledger.ady` | the books in an SQLite database, the scenarios' files, and a command line to keep them |
| `backend/ledger_server.ady` | HTTP only: hands each request to `accounting_events.ady` and serves the scripts |
| `backend/accounting_events.ady` | what each event the page sends does to the books (record, delete, open an account, close the year, the scenarios); holds the books shown. No HTTP |
| `backend/accounting_gui.ady` | `to_html` for the model's objects (boxes, arrows, tables, statements), the page's texts, and the static example (`make gui`) |
| `backend/accounting_page.ady` | the page, drawn by the server for htmx, and which event each part of it sends (`hx-*` attributes) |
| `backend/books_text.ady` | the books as text, as the server and the page pass them |
| `backend/accounting_model.ady` | accounts, transactions (`Entry`, made of `Posting`s that add up to zero), the graph and the statements; no GUI, no storage |
| `importers/` (native; used by `ledger` to make a scenario from another program's file) | |
| `importers/gnucash.ady`, `beancount.ady`, `journal.ady`, `erp_csv.ady`, `plain_books.ady` | reading GnuCash, Beancount, ledger-style journal and ERP CSV files into `Books`; `plain_books` is what the text formats share |
| `frontend/` (compiled to JavaScript) | |
| `frontend/accounting_js_events.ady` | the events that stay in the browser: dragging accounts and drawing arrows; everything else is declared in the page and handled on the server |
| `frontend/htmx.min.js` | htmx, vendored, copied to `build/` |
| `shared/` (compiled both ways) | |
| `shared/routes.ady` | where accounts are drawn and how the arrows run between them (`routes_of`, on plain names, points and texts, so the model stays in `backend/`): the server draws the page with it, and `accounting_js_events.js` runs the same code to route the arrows again while you drag |
| `tests/` | the tests, one `test_*.ady` for each part (`make test`) |
| `generators/` | `make_bakery.py` and `make_consultancy.py`, which write scenarios 11 and 12 (run from here: `python3 generators/make_bakery.py`) |
| `accounting.conf`, `scenarios/*.books` | the currency and chart a new scenario starts with, and the scenarios the page offers |

**Why `shared/` exists.** Everything in `backend/` runs on the server, everything in `frontend/` in the browser,
and `shared/` is the one thing both need: the arrow routing. The server uses it to draw the page; `accounting_js_events.js` uses
it to route the arrows again, live, while you drag an account (a round trip to the server per mouse move would be
too slow). Two implementations would make the arrows jump when you drop the account and every routing fix would
have to be made twice, so it is one source (`routes.ady`), compiled natively and to JavaScript. It works on plain
names, points and texts so that nothing else, the accounting model above all, has to come along into the browser.

## The ledger

The page's scenarios, on the command line: the same files, the same books.

```
make ledger
./backend/ledger list                          # the scenarios, with their titles
./backend/ledger 2_vat show                    # balances, profit and loss, balance sheet
./backend/ledger 2_vat journal                 # every transaction, numbered, and what it did to each account
./backend/ledger 2_vat add 2011-05-02 "Printer paper" "Bank=-12.10" "Furniture and equipment=10.00" "VAT receivable=2.10"
./backend/ledger 2_vat delete 6                # transaction 6, as journal numbers it
./backend/ledger 2_vat account 613100 expense Fuel
./backend/ledger 2_vat delete-account Fuel     # an account no transaction touches
./backend/ledger 2_vat start-over              # back as 2_vat.books has it
./backend/ledger delete-scenario NAME           # a scenario's .books file and database gone
./backend/ledger 2_vat save-as vat_mine        # a new scenario, from these books
./backend/ledger 2_vat export                  # the books as a .books file holds them
./backend/ledger new mine                      # a new scenario: the config's chart, no transaction
```

A transaction is a date, a description, and postings `ACCOUNT=AMOUNT`: the
account by number or name, the amount added to it (negative: taken out).
The ledger refuses a transaction whose postings do not add up to zero, that
names an account it does not have, or that has several accounts on both
sides (the graph could not tell which pays which); nothing is written then.

### Reading a GnuCash file

```
ledger import-gnucash NAME FILE.gnucash     # a new scenario NAME, in scenarios/NAME.books
```

GnuCash must have saved FILE as sqlite3 (File > Save As > Data Format; its
default, gzipped XML, is not read). Each account that a transaction touches
becomes an account, each transaction an entry, so the page shows, replays and
closes real books like any scenario.

- An account keeps its GnuCash account code when it has a unique one;
  otherwise it is numbered by kind (assets 550000..., liabilities 480000...,
  equity 100000..., costs 600000..., revenue 700000...).
- It is named by its own name, or by the last two parts of its path (Brokerage:VEUR) when
  two accounts would share a name (the whole path if that is still alike).
- GnuCash's trading accounts (it adds them to balance currencies) are
  ignored; amounts are the splits' values in the transaction's currency.
- A transaction with several debits *and* several credits cannot be an entry
  (one side of an entry is a single account); it is left out, and the
  scenario's description says how many.

Real files to try are in the piecash project: `simple_sample.gnucash`,
`investment.gnucash` and `book_schtx.gnucash`, under `gnucash_books/` at
https://github.com/sdementen/piecash.

### Reading a Beancount file

```
ledger import-beancount NAME FILE.beancount
```

Beancount is a plain-text double-entry format (Ledger and hledger journals
look much alike). The `ledger` command reads its transactions the same way:

- Assets, Liabilities, Equity, Income and Expenses give the five kinds, and
  an account is named by as many last parts of its path as tell it from the
  others (`Y2013:US:Federal`).
- Amounts are counted in the file's operating currency; a commodity bought at
  a cost (`8 ITOT {101.25 USD}`) counts at its cost, one with only a price
  at that price, and one with neither (vacation hours) is left out.
- A transaction with several debits against several credits (a pay slip)
  cannot be one entry, whose one side is a single account: it becomes two
  entries through a `Clearing` account. The scenario's description counts
  them.

A realistic file to try is Beancount's own example, 1,226 transactions of
three years of a household's life (pay slips, taxes, rent, cards, shares):
https://raw.githubusercontent.com/beancount/beancount/v2/examples/example.beancount

### Reading a Ledger or hledger journal

```
ledger import-journal NAME FILE.journal
```

Ledger and hledger keep books as plain text, a date, a description and
indented postings (`Expenses:Rent  $2,400.00`, the last amount left out).
Dates may be 2013/01/06, 2013-01-06 or 2013.01.06, or 1/6 after a `Y 2013`
line. Amounts count in the first currency the file uses; another commodity
counts at its cost (`{$50}`) or price (`@ $5`, `@@ $50`), and one with
neither is left out. Accounts must start with Assets, Liabilities, Equity,
Income or Expenses (any case; Revenue and Capital too), as plain-text
accountants write them. Virtual postings in parentheses, automated and
periodic transactions, prices, declarations, comments and balance
assertions are ignored.

Beancount and journal files make entries the same way (`importers/plain_books.ady`):
a transaction with several debits against several credits becomes two
entries through a `Clearing` account.

Real files to try: hledger's `examples/bcexample.hledger` (Beancount's
example, 1,111 transactions; at tag 1.40, in
https://github.com/simonmichael/hledger) and Ledger's `test/input/demo.ledger`
and `drewr3.dat` (https://github.com/ledger/ledger).

### Reading an ERP's journal lines (CSV)

```
ledger import-erp NAME JOURNAL.csv [CHART.json]
```

An ERP exports its general ledger as one line per posting. This reads the
columns `document_id`, `posting_date`, `header_text`, `gl_account`,
`debit_amount` and `credit_amount` (and `currency`), as the synthetic
datasets of https://github.com/meghahonna/erp_data_sample write them: the
lines of a document are together and make one entry, or two through a
`Clearing` account when it has several debits against several credits.
The accounts keep their GL numbers. Names and kinds come from the chart of
accounts (`chart_of_accounts.json` beside it: `account_number`,
`short_description`, `account_type`); an account it does not know is
"Account 1530", its kind from the first digit (1 assets, 2 liabilities,
3 equity, 4 revenue, 5 to 8 costs). Two accounts of one name get their
numbers added.

That repository's `complete-output/journal_entries.csv` is a year-in-eight-months
of a company: 1,068 documents (purchases, sales, payroll, depreciation)
over 143 accounts, 1,324 entries here. Its chart of accounts is stored with
Git LFS, so fetch it from
https://media.githubusercontent.com/media/meghahonna/erp_data_sample/main/complete-output/chart_of_accounts.json

A scenario's database is made from its `.books` file in a single pass, so
even this one opens in well under a second.

### accounting.conf

```
currency  USD

# number  kind        name
100000    equity      Share capital
550000    asset       Bank
700000    revenue     Sales
```

The numbers follow the Belgian chart of accounts (the first digit is the
class: 1 equity and long-term debts, 2 fixed assets, 3 stock, 4 receivables
and payables, 5 cash, 6 costs, 7 revenue), and the names are the usual
English ones for them: Share capital, Trade receivables, Trade payables,
VAT receivable and VAT payable, Wages and salaries, Change in stock; the kind is one of asset,
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

## How the page is made (HTMX)

`ledger_server` draws the page itself: http://127.0.0.1:8802/. It is
htmx (`frontend/htmx.min.js`, 14 KB gzipped, copied to `build/`) swapping in the HTML
that `backend/accounting_page.ady` makes, with the same `backend/accounting_gui.ady`, `backend/books_text.ady`, `shared/routes.ady` and
`backend/accounting_model.ady` the static example (`make gui`) uses, compiled natively. The server keeps no
state: the scenario, the grouping, the folding, the opened groups and the tab are the fields
of a form in the page, and a change to one, or a click on a group or a tab, asks `/h/all`
for the whole page again. Amounts are 64-bit here, so no grouping is refused for being
too big for the browser. The page has: the scenario picker, Group by, fold, click a group to open
it, the graph (laid out by the server; drag an account and it is drawn again where you let go, Tidy up forgets that), and the Transactions, Accounts and
Statements tabs. Dragging is the page's one script of our own, `frontend/accounting_js_events.ady` (Nim to JavaScript): it moves the account (every arrow is routed again in the browser by the same `routes_of` the server uses, so they keep their curves) and tells the server where it was dropped. To record a transaction, click an account (it freezes, a red dashed outline), drag an arrow from it to another and answer the popup (when, what, how much, VAT), the server checks and records it. The replay works too: Previous, Next, Play (the server ticks every 1.8 seconds), Pause, a date slider and Show all; with an account frozen, Play steps through that account's transactions alone. The T-accounts tab (debits left, credits right, up to the replay step) and the ratios (under Statements) are there too. Also: Help, Debit and credit, the Exercise (draw each transaction's arrow, with Show the answer), shift-click to pick accounts and Merge the picked into a group of one's own (Close groups takes them apart), Close the year, opening and deleting accounts and transactions, Start over, Save as and Delete scenario. What changes the books is POSTed to `/h/do` (or `/h/record`); the page asks first (`hx-confirm`) before deleting or starting over. This page replaced an earlier one written in Adascript for the browser (`accounting_app.ady`, 2,100 lines, with its own copy of the model); it is in git history.
