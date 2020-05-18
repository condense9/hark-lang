// Branch depending on the response from a task
import(coin, :python pysrc.main)

fn test(x) {
  if x > 0.5 {
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
  result = if (x > 0.5) {"yep"} else { "nah"}
  result
}
