# Creating a new project

Hark does not enforce a particular project structure on you. For a good starting
point, you can clone `https://github.com/condense9/starter-project`. In
this tutorial, we will start from scratch to take away some of the mystery.

## The plan

Implement a pipeline that counts the number of words occuring in a randomly generated essay from `https://metaphorpsum.com`.

Returns the run-length encoded (rle) contents of the essay along with the word frequency count.

### Project skeleton

Create a new python project, we will use `poetry` in this case.

```bash
poetry new --src hark-rle
cd hark-rle
poetry add hark-lang
poetry install
hark init
```

We want our Hark code to parallelise the processing of a (potentially) large
essay. To start, we can implement the word counter and rle encoding code in
python. Here is an implementation you can copy. Alternatively feel free to write
(and unit test) your own.

```python
# hark-rle/src/hark_rle/__init__.py

from functools import reduce
from typing import Dict, List, Tuple
from collections import Counter


def _make_encoding(encoding: List[Tuple[int, str]], c: str) -> List[Tuple[int, str]]:
    if not encoding:
        return [(1, c)]

    *init, (count, character) = encoding
    if character == c:
        return [*init , (count + 1, c)]
    else:
        return encoding + [(1, c)]


def cleanup(paragraph: str, *, remove_spaces: bool = False):
    clean = paragraph.lower().strip()
    if remove_spaces:
        return clean.replace(' ', '')
    else:
        return clean


def rle_encode(paragraph: str) -> str:
    characters = cleanup(paragraph, remove_spaces=True)
    encoding = reduce(_make_encoding, characters, [])
    return ''.join(f'{count}{character}' for count, character in encoding)


def word_counts(paragraph: str) -> Dict[str, int]:
    words = cleanup(paragraph).split()
    return dict(Counter(words))


__version__ = '0.1.0'
```

Next we can modify the hark file to do our processing. Here is an example of what we might want:

```javascript
// service.hk

import(rle_encode, hark_rle, 1);
import(word_counts, hark_rle, 1);


fn main(contents) {
    encoding = async rle_encode(contents);
    frequencies = async word_counts(contents);
    {
        "encoding": await encoding,
        "frequencies": await frequencies
    }
}
```

We can now run the hark code locally for example:

```bash
poetry run hark service.hk "the quick brown fox jumps over the lazy dog"
```

If we are happy with that, we can get our essay from `metaphorpsum.com` instead of passing command line arguments. Lets add a nice library to make these requests with.

``` bash
poetry add httpx
```

We can add the following to our `hark_rle` python code to grab a paragraph to be processed. Add the following function to the python code:

```python
# hark-rle/src/hark_rle/__init__.py
...
import httpx
...

def paragraph() -> str:
    url = "http://metaphorpsum.com/sentences/50"
    resp = httpx.get(url)
    resp.raise_for_status()
    return resp.text


__version__ = '0.1.0'
```

And update `service.hk`:

```javascript
// service.hk

import(rle_encode, hark_rle, 1);
import(word_counts, hark_rle, 1);
import(paragraph, hark_rle, 0);


fn main() {
    contents = paragraph();
    encoding = async rle_encode(contents);
    frequencies = async word_counts(contents);
    {
        "encoding": await encoding,
        "frequencies": await frequencies
    }
}
```

And test:

```bash
poetry run hark service.hk
```
