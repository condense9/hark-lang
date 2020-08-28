// In this case, the future will resolve before it is returned, so it will not
// be chained.

fn other() {
  1
}

fn call_it() {
  y = async other();
  sleep(0.4);  // let it resolve
  y
}

fn foo() {
  async call_it();
}

fn main() {
  await foo() + 1  // = 2
}
