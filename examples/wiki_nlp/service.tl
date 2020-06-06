// import(extract_pages, :python src.extract_pages)
// import(process_page, :python src.process_page)
// import(aggregate, :python src.aggregate)
import(test_pillow, :python src.fractal)


fn _map(list, func, acc) {
  if nullp(list) {
    acc
  }
  else {
    _map(rest(list), func, append(acc, func(first(list))))
  }
}

fn map(list, func) {
  _map(list, func, null)
}


// fn main(archive_key) {
//   page_names = extract_pages(archive_key)
//   results = map(page_names, process_page)
//   aggregate(results)
// }


fn main() {
  test_pillow()
}
