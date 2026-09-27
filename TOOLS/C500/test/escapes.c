int main() {
    char c;
    char *s;
    c = 'a'; c = '\n'; c = '\\'; c = '\''; c = '\x41'; c = '\101'; c = '\0'; c = '\?';
    s = "plain\ttab\nnl \x41\x4 \101\7 \"q\" \\ \? \a\b\f\v end";
    s = "joined " "strings";
    return c;
}
