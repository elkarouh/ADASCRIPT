// The VS Code grammar, run through the engine VS Code uses (vscode-textmate
// on Oniguruma), over each file given. Prints FILE:LINE: TEXT for every span
// it scopes as a regex, and FILE:LINE: STRING LEAK for every line whose first
// non-blank character is inside a quoted string it did not open -- a quote
// that opened one and never closed.
//
// Needs vscode-textmate and vscode-oniguruma: `npm install` in this directory.
const fs = require('fs'), path = require('path');
const vsctm = require('vscode-textmate'), oniguruma = require('vscode-oniguruma');
const wasm = fs.readFileSync(require.resolve('vscode-oniguruma/release/onig.wasm')).buffer;
const onigLib = oniguruma.loadWASM(wasm).then(() => ({
  createOnigScanner: (p) => new oniguruma.OnigScanner(p),
  createOnigString: (s) => new oniguruma.OnigString(s),
}));
const grammarPath = path.join(__dirname, '..', 'vscode-adascript', 'syntaxes', 'adascript.tmLanguage.json');
const registry = new vsctm.Registry({ onigLib,
  loadGrammar: async () => vsctm.parseRawGrammar(fs.readFileSync(grammarPath, 'utf8'), grammarPath) });

registry.loadGrammar('source.adascript').then((g) => {
  for (const f of process.argv.slice(2)) {
    let rule = vsctm.INITIAL, n = 0;
    for (const line of fs.readFileSync(f, 'utf8').split('\n')) {
      n++;
      const r = g.tokenizeLine(line, rule);
      rule = r.ruleStack;
      let span = '';
      for (const t of r.tokens) {
        if (t.scopes.some(s => s.startsWith('string.regexp'))) {
          span += line.slice(t.startIndex, t.endIndex);
        } else if (span) {
          console.log(`${f}:${n}: ${span}`);
          span = '';
        }
      }
      if (span) console.log(`${f}:${n}: ${span}`);
      const first = r.tokens.find(t => line.slice(t.startIndex, t.endIndex).trim() !== '');
      if (first && first.scopes.some(s => s.startsWith('string.quoted'))
          && !/^\s*[rbfu]*["']/i.test(line)) {
        console.log(`${f}:${n}: STRING LEAK`);
      }
    }
  }
});
