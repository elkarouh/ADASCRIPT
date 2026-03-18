import math, strformat
import times

var N = 1000000

proc is_prime(n: int): bool =
    var flag = true
    for k in 2 .. int(pow(float(n), 0.5)):
        if n mod k == 0:
            flag = false
            break
    return flag

proc count_primes(n: int): int =
    var count = 0
    for k in 2 ..< n:
        if is_prime(k):
            count += 1

    return count

var start = cpuTime()
echo(fmt"Number of primes: {count_primes(N)}")
echo(fmt"time elapsed: {cpuTime() - start}/s")
