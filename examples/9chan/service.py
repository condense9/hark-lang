"""Imageboard yay"""

import c9c.events as e
import c9c.services as s
from c9c.lang import Func, If
from c9c.handlers.http import to_object_store, R200, R400

BUCKET = s.ObjectStore(name="images")
DB = s.KVStore()  # default pk is id(str), no GSIs


def db_list_images(n) -> list:
    """Return the last N images"""
    # db_qry("select * from images limit 10 order by date_created")


def db_insert_image(new_image: dict):
    """Put a new image into the database"""


def db_find_image(image_id: str) -> dict:
    """Find a specific image"""
    # db_qry("select * from images where image_id=%d", image_id)


def db_find_comments(image_id: str) -> list:
    """Find all comments"""
    # db_qry("select * from comments where image_id=%d", image_id)


def db_insert_comment(image_id: str, new_comment: dict):
    """Add a comment to an image"""
    # db_qry(
    #     "insert into comments (image_id, comment_text) values (?, ?)",
    #     image_id,
    #     comment
    # )


@e.http.GET("/")
def index(_):
    images = db_list_images(10)
    return R200(render("index.html", images=images))


@e.http.GET("/image/<id>")
def view_image(_, image_id):
    image = db_find_image(image_id)
    comments = db_find_comments(image_id)
    return R200(render("image.html", image=image, comments=comments))


@e.http.POST("/image/<id>/comments")
def post_comment(request, image_id):
    comment = request.comment
    db_insert(image_id, comment)
    comments = db_qry("select * from comments where image_id=%d", image_id)
    return view_image(None, image_id)


@e.http.POST("/upload")
@to_object_store(BUCKET, "uploads", field_name="image")  # :: Func
@Func
def on_upload(request, obj):
    # handle both events at the same time (hence two arguments)
    validation = validate_upload(obj)
    response = If(
        validation.success,
        R200(save_image_in_db(obj, run_async=True).task_id),
        R400(validation.errors),
    )
    return response


def validate_upload(obj):
    # check extension, etc
    pass


@Func
def save_image_in_db(obj):
    # move to different folder, put metadata in DB, etc
    pass


if __name__ == "__main__":
    import c9c

    c9.compiler_cli()
