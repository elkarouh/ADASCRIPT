int main() {
    int a[4];
    int *p;
    int *q;
    int n;
    char *s;
    p = a + 1;
    p = 2 + a;
    q = p - 1;
    n = q - p;
    n = n + 3;
    n = n - 1;
    s = "ab\x41\101\7\n";
    s = s + 1;
    return n;
}
