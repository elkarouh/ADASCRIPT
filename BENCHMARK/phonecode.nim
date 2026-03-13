# phonecode.hpy -- HPython version of the Phone Code benchmark
# ============================================================
#
# Solves the "Phone Code" challenge from:
#   Prechelt, Lutz. "An Empirical Comparison of Seven Programming Languages."
#   IEEE Computer, Vol. 33, No. 10, October 2000, pp. 23-29.
#
# Transpile to Python:  python3 TO_PYTHON/py2py.py BENCHMARK/phonecode.hpy
# Transpile to Nim:     python3 TO_NIM/py2nim.py BENCHMARK/phonecode.hpy

import os

# ---------------------------------------------------------------------------
# Character-to-digit mapping
# ---------------------------------------------------------------------------

proc _build_char_to_digit(): Table[string, int] =
    var mapping: Table[string, int] = newTable()

    proc m(chars: string, digit: int) =
        for c in chars:
            mapping[c.toLowerAscii()] = digit
            mapping[c.toUpperAscii()] = digit

    m("e", 0)
    m("jnq", 1)
    m("rwx", 2)
    m("dsy", 3)
    m("ft", 4)
    m("am", 5)
    m("civ", 6)
    m("bku", 7)
    m("lop", 8)
    m("ghz", 9)

    for d in "0123456789":
        mapping[d] = int(d)

    return mapping

var CHAR_TO_DIGIT: Table[string, int] = _build_char_to_digit()

# ---------------------------------------------------------------------------
# Trie
# ---------------------------------------------------------------------------

type TrieNode = object of RootObj
    children: seq[Option[TrieNode]]
    words: seq[string]

proc initTrieNode(self: var TrieNode) =
    self.children = @[nil, nil, nil, nil, nil, nil, nil, nil, nil, nil]
    self.words = @[]

proc newTrieNode*(): TrieNode =
    initTrieNode(result)
proc add_word(self: TrieNode, word: string, digits: seq[int]): void =
    var node: TrieNode = self
    for idx in digits:
        if node.children[idx] is nil:
            node.children[idx] = newTrieNode()
        node = node.children[idx]
    node.words.add(word)

proc find_exact_word(self: TrieNode, digits: seq[int]): Option[string] =
    var node: TrieNode = self
    for idx in digits:
        if node.children[idx] is nil:
            return nil
        node = node.children[idx]
    if node.words:
        return node.words[0]
    return nil

proc words_at(self: TrieNode, digits: seq[int]): seq[string] =
    var node: TrieNode = self
    for idx in digits:
        if node.children[idx] is nil:
            return @[]
        node = node.children[idx]
    return node.words

proc load_dictionary(self: TrieNode, filename: string, verbose: bool): void =
    var word_count: int = 0

    proc word_to_digits(word: string): seq[int] =
        var result: seq[int] = @[]
        for c in word.toLowerAscii():
            if c notin CHAR_TO_DIGIT:
                return @[]
            result.add(CHAR_TO_DIGIT[c])
        return result

    block:
        let f = open(filename, fmRead)
        defer: f.close()
        for line in f:
            let word: string = line.strip()
            if not word:
                continue
            let digits: seq[int] = word_to_digits(word)
            if digits and len(digits) == len(word):
                self.add_word(word, digits)
                word_count += 1

    if verbose:
        echo(fmt"Loaded {word_count} words from {filename}")

proc find_encodings(self: TrieNode, digits: seq[int], pos: int, current: seq[string], results: seq[seq[string]]): void =
    if pos == len(digits):
        results.add(@current)
        return

        # Option 1: use the bare digit at this position
    self.find_encodings(digits, pos + 1, current + @[$digits[pos]], results)

    var node: TrieNode = self
    for i in range(pos, len(digits)):
        let idx: int = digits[i]
        if node.children[idx] is nil:
            break
        node = node.children[idx]
        for word in node.words:
            self.find_encodings(digits, i + 1, current + @[word], results)

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

proc clean_number(num: string): seq[int] =
    return collect(for c in num if c in CHAR_TO_DIGIT: CHAR_TO_DIGIT[c])

proc format_solution(original_num: string, solution: seq[string]): string =
    return fmt"{original_num}: {' '.join(solution)}"

# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

proc main() =
    if paramCount() < 3:
        echo("Usage: phonecode <dictionary_file> <phone_numbers_file>")
        echo("Example: phonecode words.txt phones.txt")
        quit(1)

    let dict_file: string = paramStr(1)
    let phone_file: string = paramStr(2)

    if not fileExists(dict_file):
        echo(fmt"Error: Dictionary file not found: {dict_file}")
        quit(1)
    if not fileExists(phone_file):
        echo(fmt"Error: Phone numbers file not found: {phone_file}")
        quit(1)

    var trie: TrieNode = newTrieNode()
    trie.load_dictionary(dict_file, true)

    # Quick sanity-check
    let test_digits: seq[int] = @[3, 5]
    let exact_match: Option[string] = trie.find_exact_word(test_digits)
    if exact_match isnot nil:
        echo(fmt"Exact match for digits 3,5: {exact_match}")
    else:
        echo("No exact match for digits 3,5")

    let words_at_35: seq[string] = trie.words_at(test_digits)
    echo(fmt"Words at [3,5]: {words_at_35}")

    # Process phone numbers
    block:
        let f = open(phone_file, fmRead)
        defer: f.close()
        var all_lines: seq[string] = f.readAll().splitLines()

    for line in all_lines:
        let original: string = line.strip()
        if not original:
            continue
        let digits: seq[int] = clean_number(original)
        if not digits:
            continue
        var results: seq[seq[string]] = @[]
        trie.find_encodings(digits, 0, @[], results)
        for sol in results:
            echo(format_solution(original, sol))

when isMainModule:
    main()
