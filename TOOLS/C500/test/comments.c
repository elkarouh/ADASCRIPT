// a line comment first
int main() {
    /* a block comment */ int a;
    /* one that
       spans lines */
    int b; // trailing
    a = 1; /**/ b = /* inline */ 2;
    /* with a * and a / inside */
    // a line comment with /* inside it
    return a + b; /* last */
}
// no newline at the end
