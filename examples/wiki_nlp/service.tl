import(random_fractals, :python src.fractal)
import(save_fractal_to_file, :python src.fractal)
import(upload_to_bucket, :python src.store)


// Tail-recursive version of map
fn map_tr(items, func, acc) {
  if nullp(items) {
    acc
  }
  else {
    map_tr(rest(items), func, append(acc, func(first(items))))
  }
}

fn map(items, func) {
  map_tr(items, func, null)
}


// Map and wait
fn map_wait(items, func) {
  map(map(items, func), wait)
}


fn build_fractal(args) {
  async save_fractal_to_file(nth(args, 0), nth(args, 1), nth(args, 2))
}


fn main() {
  // map(list(1, 2, 3), print)
  fractals = random_fractals(3)
  results = map_wait(fractals, build_fractal)
  map(results, upload_to_bucket)
}
