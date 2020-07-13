/// Future Chaining
//
// When an async call returns a future from *another* async call, the original
// caller only needs to wait once.
//
// In the example below, `chain' knows that `chain1' returns a future, and so
// uses `wait' to return the resolved wait. However, `chain1' calls `chain2',
// which *also* returns a future, and `chain1' does not `wait' on its result.


fn chain3(x) {
  // -> 4
  sleep(0.5);
  x + 1
}

fn chain2(x) {
  // -> future
  async chain3(x + 1)
}

fn chain1(x) {
  // -> future -> future
  async chain2(x + 1)
}

fn main() {
  // Wait for both futures, return value will be 4
  print("The answer should be 4...");
  await chain1(1)
}
