import(format, :python pysrc.main, 2);
import(cos, :python math, 1);


fn show_format(name) {
  format("Hello {}!", name)
}


fn show_trig(val) {
  cos(parse_float(val))
}


fn main() {
  print(show_format("World!"));
  print("Cos(0.0):");
  print(show_trig(0))
}
