# Example :: Imageboard

Let's build a 4chan-ish clone.

This could be trivially implemented with a small Flask app. Like
[this](https://github.com/RealArpanBhattacharya/QuickChan/blob/master/server.py)!

App requirements
- upload image
- put a comment on an image
- view an image + comments
- view N most recent images (no comments)

User (programmer) requirements
- handle file uploads
- serve GET requests
- handle POST requests
- store comments in a 

Views
- List some images
- Show a specific image (and comments, and comment box)

To make the backend slightly more complex we could require that there is a
thumbnail creation step, and thumbnails are displayed in the first view. The
thumbnail creation must be implemented "asynchronously" as if it is a really
expensive computation. DB updated only once it's finished.

### Preface: Imports

A few things are needed.

```python tangle:service.py
"""Imageboard yay"""

import c9c.events as e
import c9c.services as s
from c9c.lang import Func, If
from c9c.handlers.http import to_object_store, R200, R400
```


## Let's do it!

Serverless is all about events.

So what events have we got?
- User browses to the site (`GET /`)
- File uploaded (`POST /upload`)
- Specific image viewed (`GET /image/<id>`)
- Comment posted to image (`POST /image/<id>/comments`)

So let's stub some event handlers.

```python
@e.http.GET("/")
def index(request):
    pass

@e.http.GET("/image/<id>")
def view_image(request, image_id):
    pass

@e.http.POST("/image/<id>/comments")
def post_comment(request, image_id):
    pass

@e.http.POST("/upload")
def on_upload(request):
    pass
```

Now we'll implement each one separately.


### 3rd Party Services

First, we will use a couple of cloud-provider (serverless) services to power the
backend of the application.

```python tangle:service.py
BUCKET = s.ObjectStore(name="images")
DB = s.KVStore()  # default pk is id(str), no GSIs
ImageId = str  # type alias
```

And add some helper functions to access the new key-value store (this may be
implemented, depending on compiler constraints, as a DynamoDB).

```python tangle:service.py
@Func
def db_list_images(n: int) -> list:
    """Return the last N images"""
    # API TBD

@Func
def db_insert_image(new_image: dict) -> ImageId:
    """Put a new image into the database"""
    # API TBD

@Func
def db_find_image(image_id: ImageId) -> dict:
    """Find a specific image"""
    # API TBD

@Func
def db_find_comments(image_id: ImageId) -> list:
    """Find all comments"""
    # API TBD

@Func
def db_insert_comment(image_id: ImageId, new_comment: dict):
    """Add a comment to an image"""
    # API TBD
```

Note that these are all `Func`, **not** normal Python functions, as they will
all interact with the DB, and hence must be "visible" to the compiler. All of
the methods presented by the DB are also `Func`.


### GET /

This is easy.

```python tangle:service.py
@e.http.GET("/")
def index(_):
    images = db_list_images(10)
    return R200(render('index.html', dict(images=images)))
```

Assuming we have the ability to render templates and query a database.

`R200` means return an HTTP 200 response with the given string body.

Note that `index` is a normal Python function. The `request` parameter isn't
used, so it's named `_`.

Technical detail: `index` will actually also be a `Func`, because it's handling
an event, and needs to call other `Func`.


### GET /image/<id>

Also a trivial Python function.

```python tangle:service.py
@e.http.GET("/image/<id>")
def view_image(_, image_id):
    image = db_find_image(image_id)
    comments = db_find_comments(image_id)
    return R200(render('image.html', dict(image=image, comments=comments)))
```

Note that the two DB queries could be done concurrently if they were
long-running. We'd have to change `view_image` to a `Func` though, so it'd be
slightly less pretty. But way more powerful.

Also note that request is unused.


### POST /image/<id>/comments

Also trivial. Just update the DB and show the page again.

```python tangle:service.py
@e.http.POST("/image/<id>/comments")
def post_comment(request, image_id):
    comment = request.comment
    db_insert(image_id, comment)
    return view_image(None, image_id)
```

Note that if anything fails (db down, ...) an unhandled exception will fall
through to the top level, where it would be turned into an `R500`.

Also, we reused the existing `view_image` implementation to respond, but we
don't pass a request, because it's not needed.


### POST /upload

This is the interesting bit. We want uploaded files to end up in S3. We want to
do things with them there. But we also want to respond to the HTTP request.

So we handle the POST request with a special form that says "this takes a file
(with some validation** and puts it into object storage** and then runs some
code with the resulting file. **At the same time**, we want to respond to the
user request saying whether the upload was successful or not.

```python tangle:service.py
@e.http.POST("/upload")
@to_object_store(BUCKET, "uploads", field_name="image")  # :: Func
def on_upload(request, obj):
    # handle both events at the same time (hence two arguments)
    validation = validate_upload(obj)
    response = If(
        First(validation),
        view_image(None, save_image_in_db(obj)),
        R400(Second(validation))
    )
    return

@Foreign
def validate_upload(obj):
    # check extension, etc
    pass

@Func
def save_image_in_db(obj) -> ImageId:
    # move to different folder, put metadata in DB, etc
    # db_insert_image()
    pass

```

Assuming we can "validate" an existing object, and put its metadata into the db.

Of course, common validations (e.g. extension) could be wrapped up in
`to_object_store` with a nice API.

Note that `on_upload` will automatically become a `Func` (as it is handling an
event). `save_image_in_db` runs asynchronously, so the HTTP request returns
immediately, but with a reference to the result of saving the image (this isn't
well defined at the moment).


### Finally, compile the service

The last detail we need to do is compile the service. Since this is all embedded
in Python, creating the compiler CLI in the same file is a nice way to do it. It
also ensures that there is a single "top-level" file for the service.

```python tangle:service.py
if __name__ == '__main__':
    import c9c
    c9.compiler_cli()
```


## Ric's Notes

Ideas and thoughts while writing this example.

Chaining events is interested (on HTTP POST -> on object create object -> handle
both). Returning things to events. The idea that events (eg HTTP req) can handle
something being returned. Not all can (eg object created event). And if it
doesn't, what side-effects are there? Nothing... All side-effects are handled in
the Foreign code.

But actually returning something to an event handler is a neat way of having
side effects but not having to write icky foreign code.

The event handler creates a promise which is fulfilled by the user's function.

There could be multiple `to_object_store` to deal with multiple files being
uploaded. The programmer specifies the form field name.


## How it works in the poet's mind

To build this, we need
- a database
- API gateways
- lambda request handlers
- S3 bucket
- CDN (maybe) for statics (CSS...)

The compiler knows which bits are needed - except the database.

There are too many possible implementations to easily optimise though.

We could reuse serverless components (generate YAML from some arguments in the
python).

We could easily generate a pythonic interface to serverless components. ie
generate YAML from a dict.
