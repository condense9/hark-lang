// Branch depending on the response from a task
import(coin, :python pysrc.main, 0);

fn test(x) {
  if parse_float(x) > 0.5 {
    print("yes")
  }
  else {
    print("no")
  }
}


fn main() {
  result = coin();
  if result {
    print("yes")
  }
  else {
    print("nope")
  }
  result
}


fn multi(x) {
  x = parse_float(x);
  if x < 2 {
    x
  }
  else if x < 5 {
    x * 2
  }
  else if x < 10 {
    x * 3
  }
  else {
    x * 4
  }
}


// If-expressions return values too:

fn if_expr(x) {
  x = parse_float(x);
  if (x > 0.5) {"yep"} else { "nah"}
}
