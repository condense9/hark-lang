import(format, :python pysrc.main)
import(cos, :python math)


show_format = fn(name) {
  format("Hello {}!", name)
}


show_trig = fn(val) {
  cos(val)
}


main = fn() {
  print(show_format("World!"))
  print("Cos(0.0):")
  print(show_trig(0))
}
