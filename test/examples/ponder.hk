// Call 'ponder' twice in parallel, and wait for the answer

import(format, :python pysrc.main, 2);
import(random_sleep, :python pysrc.main, 2);


fn ponder() {
  random_sleep();
  print("thinking really hard!");
  // The last expression evaluated in a function is its return value:
  21
}

fn main() {
  print("beginning...");
  x = async ponder();
  y = async ponder();
  print("waiting for an answer...");

  answer = await x + await y;
  format("The answer is... {}!", answer)
}
