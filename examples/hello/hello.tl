// -*- mode: javascript -*- (sort-of... close enough for now)

import(hi, src.example);
import(format, src.example);

fn main() {
  print("Some output");
  hi();
  print({1: 2, 3: 4});
  print([1,
         2,
         3]);
  "Hello world!"
}

fn more() {
  print("MORE")
}
