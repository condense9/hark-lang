### Concurrency
##
## Functions `conc-b' and `conc-d' are called asynchronously from `concurrent'
## (using two different syntaxes, just for funs). Functions `ser-a' and `ser-c'
## are called normally.
##
## So the evaluation/data-flow graph looks like:
##
##                        .---[ conc-b ]---[ ser-a ]--.
##                       /                             \
## X --[ concurrent ]---+                               >---[ final ]--->
##                       \                             /
##                        ·---[ conc-d ]---[ ser-c ]--·
##

importpy random_sleep from pysrc.main


def ser_a(x):
    print("a starting to sleep")
    random_sleep(50, 500)
    print("a finished sleeping")
    x + 1

def conc_b(x):
    ser_a(x) * 1000

def ser_c(x):
    print ("c starting to sleep")
    random_sleep(50, 500)
    print("c finished sleeping")
    x + -1

def conc_d(x):
    ser_c(x) * 10

def final(p, q):
    await p + await q * -1

def concurrent(x):
    # (1000 * (x + 1)) - (10 * (x - 1)) = 5960 if x is 5
    final(async conc_b(x), async conc_d(x))


def main():
    x = 5
    concurrent(x)
