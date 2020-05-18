/* Concurrency
 *
 * Functions `conc-b' and `conc-d' are called asynchronously from `concurrent'
 * (using two different syntaxes, just for funs). Functions `ser-a' and `ser-c'
 * are called normally.
 *
 * So the evaluation/data-flow graph looks like:
 *
 *                        .---[ conc-b ]---[ ser-a ]--.
 *                       /                             \
 * X --[ concurrent ]---+                               >---[ final ]--->
 *                       \                             /
 *                        ·---[ conc-d ]---[ ser-c ]--·
 *
 **/

import(random_sleep, :python pysrc.main)


ser_a = fn(x) {
  print("a starting to sleep")
  random_sleep(50, 500)
  print("a finished sleeping")
  x + 1
}

conc_b = fn(x) {
  ser_a(x) * 1000
}

ser_c = fn(x) {
  print ("c starting to sleep")
  random_sleep(50, 500)
  print("c finished sleeping")
  x + -1
}

conc_d = fn(x){
  ser_c(x) * 10
}

final = fn(p, q) {
  await p + await q * -1
}

concurrent = fn(x) {
  // (1000 * (x + 1)) - (10 * (x - 1)) = 5960 if x is 5
  final(async conc_b(x), async conc_d(x))
}


main = fn() {
  x = 5
  concurrent(x)
}
