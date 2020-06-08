// Branch depending on the response from a task
import(coin, :python pysrc.main)

fn test(x) {
  if parse_float(x) > 0.5 {
    print("yes")
  }
  else {
    print("no")
  }
}


fn main() {
  result = coin()
  if result {
    print("yes")
  }
  else {
    print("nope")
  }
  result
}


// If-expressions return values too:

fn if_expr(x) {
  x = parse_float(x)
  if (x > 0.5) {"yep"} else { "nah"}
}
