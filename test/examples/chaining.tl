### Future Chaining
##
## When an async call returns a future from *another* async call, the original
## caller only needs to wait once.
##
## In the example below, `chain' knows that `chain1' returns a future, and so
## uses `wait' to return the resolved wait. However, `chain1' calls `chain2',
## which *also* returns a future, and `chain1' does not `wait' on its result.


def chain3(x):
  sleep(0.5)
  x + 1

def chain2(x):
    async chain3(x + 1)

def chain1(x):
    async chain2(x + 1)

def main():
    await chain1(1)
