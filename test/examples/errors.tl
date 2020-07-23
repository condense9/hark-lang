import(bad_fn, :python pysrc.main, 0);

fn main() {
  print("main starting...");
  x = async bad();
  y = async py_bad()
}


fn bad() {
  print("About to fail");
  signal("error", "badness")
}

fn py_bad() {
  bad_fn()
}
