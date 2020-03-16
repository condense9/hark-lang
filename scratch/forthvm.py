"""Go Forth."""

import collections


def f_add(m):
    m.stack.append(stack.pop() + stack.pop())


def f_words(m):
    print(" ".join(m.dictionary.keys()))


# def f_def(m):
#     m.add_word(m.stack.pop(), m.)


class M:
    def __init__(self):
        self.stack = collections.deque()
        self.dictionary = {}
        self.add_word("+", f_add)
        self.add_word("words", f_words)
        self.add_word(":", f_def)

    def add_word(self, word, definition):
        self._dictionary[word] = definition

    # def read(self, stream):


def repl():
    m = M()
    while not m.stopped():
        inp = read()
        result = m.interpret(inp)
        print(f"{result}")


if __name__ == "__main__":
    repl()
