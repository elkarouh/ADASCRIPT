# Test cases

Each `cases/NNN.in.adb` is re-indented by `bin/ada_indent` and must come out as `cases/NNN.out.adb`.

## 001

1. Subprogram with if/elsif/else, loop, and case.

## 002

2. Package spec with a record type and a private part.

## 003

3. Declare block with an exception handler, plus blank-line preservation.

## 004

4. Continuation inside an unclosed parenthesis (aggregate / call) aligns
under the first item after the '('.

## 005

5. Statement/declaration continuation: a line that does not end the
statement (no ';' and not a structural keyword line) indents its
continuation one level; the terminating ';' clears it. (Operator-led
continuations get no extra level outside parentheses — only within.)

## 006

6. Multi-line if/elsif conditions: continuation lines ('and then …') must
indent one level relative to the 'if'/'elsif'; 'then' aligns with the
opener; body and end-if are at the normal depths.

## 007

7. Expression function: 'function ... is' followed by a parenthesised
expression pushes NO block frame, and the declarations after it must
return to the outer level (regression: the spec frame used to linger).

## 008

8. If-expression inside parentheses: 'then'/'else'/'elsif' align under the
'if' itself, condition continuations align under the condition, and the
statement returns to the normal level once the parenthesis closes.

## 009

9. Subunit with a multi-line parameter list. The 'separate (Parent)'
clause is a complete line (must NOT make the body indent), the
parameter continuations align under the first parameter, and the
closing ') is' still opens the body frame so the declarations indent.

## 010

10. Case-expression as an expression-function body. 'when' clauses are
indented one level in from the 'case', and a clause body on its own
line ('=> ...') one level deeper still.

## 011

11. Operator-led continuations take an extra level ONLY within parentheses:
the '=> ...' arms inside the else-aggregate sit one level past the
items, while the bare ':=' continuation gets the plain +1 (no extra).

## 012

12. Operator-led extra indent applies ONLY inside parentheses. The 'and'
continuation outside the paren takes a plain single level (aligned with
where a comment would sit), while the 'or else' inside the paren takes
the extra level past the aligned items.

## 013

13. Parentheses opened inside a multi-line if-statement condition: the
lines within them are aligned to the paren (with the operator extra),
not flattened to the condition level; 'then' still snaps to the 'if'.

## 014

14. Comment lines are transparent to the parser: comments interrupting a
statement continuation must not clear it. The 'return' line is unfinished
(in_cont), so the line that would follow each comment is a continuation:
the comments take the continuation indent, aligned with the 'and (...'
they precede (one level past where the value began), not the shallower
block level. The comment INSIDE the paren follows the unfinished item
there, aligning with the 'or else' continuation it precedes.

## 015

15. A declaration whose initializer is a parenthesised '(case X is …' (or
'(if … )') expression ends in the keyword 'is'/'then', but that keyword
is INSIDE the open '(' — it must NOT push a block frame. Otherwise the
declarations that follow (here a nested expression function and another
constant) would be shifted one level too deep for the rest of the unit.

## 016

16. Multi-line case-expression arm body. The arm body is an expression:
its first line sits at the arm-body level (one in from 'when'), and a
continuation that starts with an operator ('or else') takes one extra
level. A leading '=>' (the result arrow for choices spilled onto an
earlier line) stays at the arm-body level, not the operator level.

## 017

17. A continuation line that opens with '(' is the argument list of the
expression it continues, so it nests one level deeper than the bare
continuation above it (here the '(' under a continued ':= F'); the
arguments then align to that '('.

## 018

17b. A '(' continuation nests only one level past the line it continues.
When the call name is the statement's FIRST line (not itself a
continuation), its argument list takes the plain +1 — not the extra
second level that test 17's ':= Get' chain gets.

## 019

18. Block/loop labels end in ':' and are complete prefixes, not statement
continuations: the labelled 'declare' / 'for … loop' stays at the
label's level (a trailing comment on the label is ignored). Without
this the label would push the following line one level too deep.

## 020

19. Multi-line if condition: 'and then' connectives sit at the base
continuation level, but a line starting with another operator ('>=')
continues the previous term across the break and nests one level
deeper. A comment between the lines stays transparent and aligns with
the current condition-term line — the 'and then' connective clause it
documents — not the deeper '>=' term continuation.

## 021

20. An if-EXPRESSION's 'else …)' line closes the expression and continues
the surrounding statement (it is not a complete statement-level
'else'), so the following '& …;' stays at the continuation level
rather than dropping back to the declaration's base level.

## 022

21. A 'when' choice list split before its '=>': the '|' continuation
goes one level past the arm body, so it cannot be read as the
alternative's first statement.

## 023

22. General term-continuation nesting (not just in conditions): when the
':=' initializer is on its own continuation line, an operator that
continues the value ('- …') nests one level past the ':=' line.

## 024

23. A '(' argument list opening a continuation inside a multi-line if
condition nests one level past the 'and then' term it belongs to; its
arguments then align to that '('.

## 025

23b. The mirror of test 23: when the call name is on the 'elsif'/'if'
opener line itself (not a separate 'and then' continuation), its
split '(' argument list nests one level past the opener — not two.
The 'then' still snaps back to the opener level.

## 026

24. A ')' (or '(') written as a character literal must not be counted in
the running parenthesis depth, otherwise the enclosing '(if …)'
expression looks closed and its 'else' loses the alignment under 'if'.

## 027

25. 'and not' / 'or not' are value operators (bit-clear / boolean negate),
not connectives like 'and then' / 'or else'. When ':=' is on its own
continuation line they nest one extra level past ':='; bare 'and' / 'or'
stay at the plain continuation level.

## 028

27. Inside a plain paren, a '(' that continues the preceding expression
(previous line ended without ',') is the argument list of that
expression, not a new list element: it nests one extra level past the
item column. Here the else-branch of an if-expression calls Convert
whose argument list is split to the next line.

## 029

28. 'or else' / 'and then' continuations in a value expression must NOT
trigger the structural 'or'/'else' de-indent (which only applies when
they stand alone as statement-level keywords). With ':=' on its own
continuation line the value expression begins one level past it, so the
'or else' connective nests there (6 spaces), one level past the ':='.

## 030

29. 'and (' combines the preceding result with a parenthesised subexpression
and is a term continuation: when ':=' is on its own continuation line,
'and (' nests one extra level past ':=' (value_base + 1), just like
'and not' / 'or not'.

## 031

30. A multi-line boolean value expression after a ':='-on-its-own-line:
each 'or else' connective joins a parenthesised operand group and sits
one level past the ':='. The comments interleaved between the groups are
OUTSIDE any paren (the groups have closed) but the statement is still
unfinished, so the line that would follow each comment is a continuation:
the comments take the 'or else' continuation level they precede. Inside
each group the 'and then' lines align to the group's open paren.

## 032

31. A quantified expression '(for some/all … => predicate)': the predicate
after '=>' nests one level past the 'for' keyword (like an '(if'/'(case'
body), not flush with it as a plain-paren first item would. The iterator
spec's own nested call parens close on the same line and don't affect it.

## 033

32. A '(' arg list that continues an expression which is itself the first
item of an outer '(' opened on the SAME statement line. The outer call's
argument (G.Image) is unfinished (the line ends without a comma), so its
own argument list '(' on the next line nests one level past the outer
paren's item column — not flush with it as a new list element would.

## 034

33. A named association whose value spills past a trailing '=>' into the
next line: the value nests one level past the item column; operators
that continue it take one more level; interleaved comments align with
the operator lines they document; the following association starts a
new item at the outer column once its comma closes the current one.

## 035

34. A line that closes a parenthesised if-expression with a lone ')' (often
after a trailing comment) aligns the ')' under the opening '(' — one
column left of the 'if'/'then'/'else' keywords — rather than taking the
condition-continuation indent that would push it right of them.

## 036

35. A standalone comment is indented like the hypothetical instruction that
would occupy its place — the current block level. A comment right before
'begin' (empty declarative part) sits at the declaration level it could
have held (one in from the subprogram header), and a comment after a
deferred 'function ... is' header sits at the body level the following
declaration takes — one level past the header, not at the header itself.

## 037

37. A comment between the branches of a parenthesised if-expression, sitting
right after the 'then (...)' aggregate closed back to the '(if' level,
aligns with the then/else/elsif keywords (the '(if' column) — the level
of the 'else' that follows — not one level deeper. The fallback derives
this from the paren kind when no peer line was recorded at this level.

## 038

38. A comment block after a complete connective clause in a multi-line
elsif condition, sitting just before 'then': it aligns with the 'or else'
clause it documents (the current condition-term level, one in from the
elsif), not one level deeper. 'then' still snaps back to the elsif level.

## 039

39. A comment inside a paren opened on a cond_state (if/elsif condition)
line: the opening line sets paren_cont so the comment fallback correctly
adds one indent level, aligning with the operator continuation (or else)
that follows rather than with the shallower item column.

## 040

40. A comment in a paren must not inherit a stale alignment from a sibling
paren that already closed. Here a first '(...)' group at the connective
level closes, then a second '(...)' group opens at the same depth with a
comment right after its opening line. The comment must align with the
'and then' operator continuation inside the SECOND group (its item column
plus one), not with the deeper lead left over from the first group.

## 041

41. A comment after the HEAD line of a multi-line case-expression arm body:
the head sits at the arm-body level, but the arm body continues with an
operator ('or else') one level deeper. The comment must anticipate that
operator continuation and align with it, not stay at the head level. A
later comment, sitting after an 'or else' line, stays at that same
operator level (operators chain without escalating).

## 042

42. A trailing comment after the LAST argument of a call (a complete named
association 'X => Y' with no comma, so paren_cont is set) stays at the
argument column — the association is a finished list element, not an
unfinished expression, so the comment must NOT anticipate an operator
continuation. The lone ')' that closes the list sits one column left.

## 043

43. A comment between two arguments, sitting after an argument whose value
spilled onto an operator-continuation line that ENDED WITH A COMMA: the
comma closes that argument, so the comment belongs with the next
argument at the item column, not at the deeper operator-continuation
level of the line just above it.

## 044

Regression: an identifier that merely starts with a keyword
('Case_Sensitive', 'For_Each', 'If_Valid') must NOT be treated as the
opener of a (case .. / (for .. / (if .. expression. Such plain-paren
continuations align as a normal operator continuation, one level past
the item — not at the deeper case/for/if body level.

## 045

45. Regression: 'type T is' on its own line (not 'type T is record') pushes
a PKG frame that must be popped together with the RECORD frame when
'end record' is processed, otherwise every line after the type definition
is indented one level too deep.  Covers simple and variant-record forms.

## 046

46. Regression: a standalone 'is' that terminates an aspect-clause
continuation (task type / protected type / subprogram with an aspect
clause) must align with the declaration opener, not be indented one
extra level as a value continuation.

## 047

47. Regression: 'or' / 'else' inside a guarded select statement must align
with 'select', not be indented under the 'when' guard.  When a select
alternative body closes ('end Foo;' or just the last statement), the
WHEN frame pushed by 'when Guard =>' is not popped automatically —
'or'/'else' must pop it before computing disp.

## 048

48. Regression: a standalone 'loop' that terminates a multi-line for/while
header (range continuation '..') must align with the 'for'/'while',
not be indented one extra level as a value continuation.

## 049

49. Regression: 'is new' on a continuation line is a generic instantiation,
not a block opener — it must NOT snap back to the declaration level but
stay indented as a continuation.  Standalone 'is' (no following token)
still snaps back as before.

## 050

50. Regression: when the opening '(' of a named-argument list appears on
its own line with 'Name =>' and the value on the NEXT line, that line
must get the arrow-spill indent (acol + INDENT_WIDTH), not plain acol.
The paren was opened while the regular path was active (paren_depth=0
at entry) so arrow_level must be set there, not only in the paren path.

## 051

51. 'package X is\nnew Y;' inside a subprogram declarative region — the PKG
pushed for 'package X is' must not survive to misalign the 'begin'.

## 052

52. Regression: an expression function whose parameter list spans several
physical lines. The 'is' ending the header lands on the line that closes
the parameter list, so the header's leading word is no longer visible
there; that path used to push a PKG frame unconditionally. An expression
function has no 'end', so the frame never popped and every declaration
after it drifted one level deeper.

## 053

53. The same multi-line header, but with a real body: the deferred push must
still happen, so 'begin'/'end' pair with the function as before.

## 054

54. Resynchronisation: a frame that is opened but never closed by an 'end'
of its own (here 'procedure Leaked', whose body is missing) used to
shift every following line for the rest of the file. The enclosing
'end Outer;' names a construct further down the stack, which says the
frames above it were never real: they are dropped, and 'procedure
After' lands back at the correct level.

## 055

55. The anchors must not fire on well-formed code. Labelled blocks and
loops ('end loop Outer;', 'end Log;'), the keyword ends ('end case;',
'end if;') and a dotted child unit ('end Parent.Child;') all name
exactly the frame they close, so nothing is dropped and the whole
thing is a fixpoint.

## 056

56. '[not] overriding' is an indicator, not the construct: the keyword
that says what is being declared is the one after it. Read literally,
'overriding function F ... is' begins with 'overriding', missed the
expression-function deferral, and opened a block nothing ever closed.

## 057

57. The indicator must not swallow a real body: an 'overriding' subprogram
with a begin/end still pushes its frame, and its 'end' still names it.

## 058

58. The 'is' closing a function header may sit on a line of its own, with
the expression body beside it or below it. The word to go by then
belongs to the line that opened the declaration, not to the 'is' line:
read literally, a standalone 'is' pushed a block frame, and an
expression function has no 'end' to close it.

## 059

59. The same standalone 'is' on a real body must still push its frame, and
a task type's standalone 'is' must be untouched by the function rule.

## 060

60. A complete one-line 'if C then X; end if;'. It starts with 'if' and
does not end with 'then', which is how an unterminated condition is
recognised -- but it is a whole statement, and reading it as a
condition latched the condition tracker on for the rest of the file:
every later line indented as a condition continuation, 'exception'
and 'end' stopped snapping back, and on a real 2192-line source that
ran the display depth down until a bare 'exception' hit depth 0 and
crashed with a RangeDefect.

## 061

61. A multi-line condition must still open the tracker -- the guard above
keys on the line continuing, not on the absence of 'then'.

## 062

62. An expression function whose parameter list closes on one line and
whose 'is' lands on the NEXT line, after the return type. That line
opens with 'return', so a deferral keyed on the line's own first word
missed it and pushed a block frame; an expression function has no
'end', so every following declaration sat one level too deep.

## 063

63. The same shape with a real body: the deferred push must still happen,
so 'begin'/'end' pair with the function as before.

## 064

64. A block opener written hard against the punctuation before it. Ada's
free format allows ')is' with no space, but the final token was cut on
whitespace alone, so it came back as 'Text_IO.File_Type)is' and opened
no frame: the declarative part then indented as a continuation of the
parameter list, which put the first declaration at the continuation
column and dropped every later one to the enclosing level.

## 065

65. The cut must not invent keywords out of trailing identifiers. A token
ending in '_is' or carrying a tick is one word, not a keyword, and a
token that does not end in an identifier character is left whole.

## 066

66. '[not] overriding' again, in the cascade shape the report showed:
consecutive expression functions each a level deeper than the last.
that says what is being declared is the one after it. Read literally,
'overriding function F ... is' begins with 'overriding', missed the
expression-function deferral, and opened a block nothing ever closes.
Consecutive ones then cascade, each a level deeper than the last.

## 067

67. The indicator must not swallow a real body: an 'overriding' subprogram
with a begin/end still pushes its frame.

## 068

68. Complete one-liners whose final token is a block keyword. last_word()
drops the trailing ';', so 'type T is null record;' ended in 'record'
and 'for I in 1 .. 3 loop Put (I); end loop;' ended in 'loop' -- each
opened a frame no 'end' would ever close, and everything after it
drifted. The last two close their parentheses on the way out, which is
a second dispatch with the same hole.

## 069

69. The guard keys on the trailing ';', not on stmt_incomplete(), which
asks a different question and is False for every block opener. The
openers carry no ';' and must still push.

## 070

70. A case alternative whose body starts on the same line as its '=>' and
opens a block there: 'when X => if C then'. The WHEN frame is the
alternative, not that block, and no frame was pushed for the block --
so its own 'end if;' closed the alternative instead, and every 'end'
after it came out one frame short, unwinding the case, the outer if
and the subprogram each a level too shallow.

## 071

71. The same guards as the statement-level dispatch apply to an arm body:
an arm complete on its line opens nothing, and a loop arm opens a LOOP
that its own 'end loop;' closes.

## 072

72. A discriminated record whose header spans lines, so the 'is' lands on
the line that closes the discriminant list. That dispatch knew only
'function' and defaulted everything else to a PKG frame, so the type
opened a PKG instead of a TYPE_HEADER; 'end record;' pops the RECORD
and pairs away a TYPE_HEADER, not a PKG, so the frame stayed open and
every later declaration sat one level too deep.

## 073

73. The other three answers must survive the same split header: a subtype
opens nothing, a case opens a CASE, and a function still defers.

## 074

74. 'procedure X (...) is begin' -- header and the start of the statement
part on one line. Ugly, but legal, and the stack must not care: the
dispatch had no arm for a trailing 'begin', so neither the 'is' nor
the 'begin' opened anything and the subprogram's 'end' closed its
parent instead. stmt_incomplete() also read the line as unfinished,
which put the first body line at the continuation column.

## 075

75. The same for a trailing 'declare': a line ending in one is a complete
opener, so the block's first declaration is a statement rather than a
continuation of the label line.

## 076

76. A condition broken after 'and then'. That line's last word is 'then',
so the tracker took it for the 'then' that ends the condition: it
closed the condition early and pushed the IF there, and the real
'then' further down pushed a second one. Everything inside the block
sat a level too deep and each 'end if;' unwound one frame late.

## 077

77. A 'then' with anything else before it still ends the condition, on the
opener line and on a continuation, and 'and then' mid-line is not the
final token so it never had a say.

## 078

78. The glued-punctuation family, for every opener that has a dedicated
reader. last_word() cuts ')then' back to 'then', but a reader that
splits on blanks of its own gets '(X)then' and sees no keyword -- which
is how ends_with_condition_then() reintroduced the ')is' bug for
')then' after that cut had already fixed it. Anything asking 'does this
line end in <keyword>' has to ask it through last_word().

## 079

79. ...and the cut must not lose the 'and then' distinction it was taught
alongside. Here the glued 'then' is a real terminator -- the word
before it is '(B)', not 'and' -- so the line ends the condition and
snaps back to the opener, as a terminating 'then' always does.

## 080

80. A 'record' that opens its component list part-way along the line, with
the first component already beside it. The dispatches key on a line's
last word, which here belongs to that component, so nothing saw the
opener: the components stayed at the type's level and the 'end record;'
below popped a frame belonging to something else -- taking the package
with it, so every declaration after the type collapsed too.

## 081

81. Counting 'record' words must not disturb the three that open nothing:
a null record, a whole record on one line, and the word inside a string
literal. Each leaves the following declaration at the type's level.

## 082

82. A derived type whose definition sits on the next line:

type Ref_Count_T is
new Integer range -1 .. 9;

The TYPE_HEADER for 'type ... is' is discarded on the 'new' line, as
a type that never reaches 'record' should be -- but the 'new' then
armed the generic-instantiation cleanup, which pops a PKG when the
statement ends. The PKG left on top is the enclosing package's, so
that was the frame taken, and every declaration after it fell out of
the package.

## 083

83. The real generic instantiation must still clean up after itself: there
the PKG on top IS the one 'X is' pushed, and nothing popped a
TYPE_HEADER on the way.

## 084

84. An if statement whose branches are each complete on their own line.
The opener's 'then' is mid-line and its ';' closes the branch, not the
statement, so nothing pushed the IF: every 'elsif', the 'else' and the
'end if;' then aligned one level out, and the 'end if;' popped the
enclosing block instead.

## 085

85. Counting 'if' words must leave the three that open nothing alone: a
whole if statement on one line, an if-EXPRESSION inside parentheses,
and a condition that does not finish on its opening line -- that last
one belongs to the multi-line tracker, which pushes at its own 'then'.

## 086

86. 'private' has two jobs, and the dispatch knew only one. As the section
splitter of a package spec it stands alone on its line and aligns with
the 'package'. As the privacy indicator of a library unit it qualifies
a declaration -- 'private package P is' -- which still has to open its
own frame; taking it for the splitter opened nothing, so the whole
package body stayed at the file's level.

## 087

87. The indicator must not hide what is being declared either, exactly as
'overriding' must not: a private expression function still defers, so
it opens no frame and the declaration after it keeps its level.

## 088

88. An 'end if' reached part-way along a line whose first word the
dispatch has already claimed: 'else return Deactivated; end if;' is an
'else' line, so nothing popped the frame its 'end if' closes. Inside a
case alternative that leaves the IF standing under the WHEN, and every
later arm, the 'end case;' and the subprogram's own 'end' came out a
level in.

## 089

89. The count must close nothing it should not: a whole if statement on
one line is balanced, an 'end if;' of its own has already been popped
by its dispatch, and neither a literal nor an if-expression counts.
Here the outer if must still be open at Next_Statement.

## 090

90. A comment placed deliberately deeper than the indenter would put it
(more than one level) keeps its offset from the code line above it
at its paren depth, and moves with that line: here the whole call
arrives two columns too deep and the note under 'Make (...)' follows
it. A comment at the default column is re-indented as ever.

## 091

91. The same when the only line before the comment at its depth is the
one that opens the parenthesis with its first item ('(V => Make
(...),'): that line is the comment's reference too.
