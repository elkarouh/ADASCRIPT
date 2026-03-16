import math
import times

var N = 1000000

proc is_prime(n: int): bool =
    var flag = true
    for k in 2 ..< int(pow(float(n), 0.5)) + 1:
        if n mod k == 0:
            flag = false
            break
    return flag
