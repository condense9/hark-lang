import(bad_fn, :python pysrc.main)

fn main() {
  x = async bad()
}


fn bad() {
  print("hi")
  signal("error", "badness")
}

fn py_bad() {
  bad_fn()
}
