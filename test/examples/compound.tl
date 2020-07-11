/* Lists and Hashes! -*- mode: javascript -*- */

fn lists() {
  lst = [1, 2, 3];
  // Multi-line is ok:
  lst2 = [
    4,
    5
  ];
  length(lst) + length(lst2)
}

fn hashes(key) {
  h = {"hello": "world", "foo": "bar"};
  get(h, key)
}

fn modify() {
  // again, multi-line works, BUT the k:v pairs must be on the same line!
  h = {
    "hello": "world",
    "foo": "bar"
  };
  h = set(h, "monkey", "tree");
  get(h, "monkey")
}

fn main() {
  print(lists());
  print(hashes("hello"));
  print(modify());
  print({1: 2, 3: 4});
  {"Done?": {"hmm...": true}}
}
