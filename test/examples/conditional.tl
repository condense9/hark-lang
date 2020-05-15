
fn main(x):
    if x > 0.5:
        print("yes")
    else:
        false

    fn bla(x): x +1

    return bla


# Functions all get stored in
#
# In this, the value of the local symbol "add" is a /closure/ of that function.
# The closure is a tuple: (ptr to function body, ptr to stack frame).
#
# "adder" is a symbol in the global bindings, and its value is a /function/,
# which is just a ptr to the function body
#
# if there was an import, its symbol would be bound to a /pyimport/.
#
# at link time, all of the function bodies get concatenated, and their pointers
# are added to the table.


def adder(x, do_sub):
    w = x * 2

    def add(y): w + y
    def sub(y): w - y

    if do_sub
        print("subtracting")
        sub

    else add


# maybe just make the : after else optional. Guido says: no optional syntax. Do
# it my way. Consistency is king.

# ruby:
# if @item.rigged then 'Yes' else 'No' end
# if @item.rigged; 'Yes' else 'No' end
# if @item.rigged
#   'Yes' else 'No' end
