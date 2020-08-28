/* Concurrency
 *
 * Functions `conc-b' and `conc-d' are called asynchronously from `concurrent'.
 * Functions `ser-a' and `ser-c' are called normally.
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

import(random_sleep, :python pysrc.main, 2);


fn ser_a (x) {
  print("a starting to sleep");
  random_sleep(50, 500);
  print("a finished sleeping");
  x + 1
}

fn conc_b(x) {
  ser_a(x) * 1000
}

fn ser_c(x) {
  print ("c starting to sleep");
  random_sleep(50, 500);
  print("c finished sleeping");
  x + -1
}

fn conc_d(x){
  ser_c(x) * 10
}

fn final(p, q) {
  await p + await q * -1
}

fn concurrent(x) {
  // (1000 * (x + 1)) - (10 * (x - 1)) = 5960 if x is 5
  final(async conc_b(x), async conc_d(x))
}


fn main() {
  x = 5;
  concurrent(x)
}
