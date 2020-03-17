"""Imageboard yay"""

import c9c.events as e
import c9c.services as s
from c9c.lang import Func, If
from c9c.handlers.http import to_object_store, R200, R400

BUCKET = s.ObjectStore(name="images")
DB = s.KVStore()  # default pk is id(str), no GSIs
ImageId = str  # type alias


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


@e.http.GET("/")
def index(_):
    images = db_list_images(10)
    return R200(render("index.html", dict(images=images)))


@e.http.GET("/image/<id>")
def view_image(_, image_id):
    image = db_find_image(image_id)
    comments = db_find_comments(image_id)
    return R200(render("image.html", dict(image=image, comments=comments)))


@e.http.POST("/image/<id>/comments")
def post_comment(request, image_id):
    comment = request.comment
    db_insert(image_id, comment)
    return view_image(None, image_id)


@e.http.POST("/upload")
@to_object_store(BUCKET, "uploads", field_name="image")  # :: Func
def on_upload(request, obj):
    # handle both events at the same time (hence two arguments)
    validation = validate_upload(obj)
    response = If(
        First(validation),
        view_image(None, save_image_in_db(obj)),
        R400(Second(validation)),
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


if __name__ == "__main__":
    import c9c

    c9.compiler_cli()
