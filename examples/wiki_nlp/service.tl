import(random_fractals, :python src.draw)
import(save_fractal_to_file, :python src.draw)
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


// FFI must be wrapped in a Teal func to be called async
fn do_save(args) {
  print(args)
  result = save_fractal_to_file(nth(args, 0), nth(args, 1), nth(args, 2), "/tmp")
  upload_to_bucket(result)
}

fn build_fractal(args) {
  async do_save(args)
}


fn main() {
  fractals = random_fractals(3)
  results = map_wait(fractals, build_fractal)
  results
}
