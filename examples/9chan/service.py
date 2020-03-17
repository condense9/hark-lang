"""Imageboard yay"""

import c9c.events as e
from c9c.lang import Func, If
from c9c.handlers.http import to_object_store, R200, R400


@e.http.GET("/")
def index(_):
    images = db_qry("select * from images limit 10 order by date_created")
    return R200(render("index.html", images=images))


BUCKET = c9c.ObjectStore(name="images")


@e.http.POST("/upload")
@to_object_store(BUCKET, "uploads", field_name="image")  # :: Func
@Func
def on_upload(request, obj):
    # handle both events at the same time (hence two arguments)
    validation = validate_upload(obj)
    response = If(
        validation.success,
        R200(save_image_in_db(obj, run_async=True)),
        R400(validation.errors),
    )
    return response


# def validate_upload(obj): check extension, etc

# def save_image_in_db(obj): move to different folder, put metadata in DB, etc
@e.http.GET("/image/<id>")
def view_image(_, image_id):
    image = db_qry("select * from images where image_id=%d", image_id)
    comments = db_qry("select * from comments where image_id=%d", image_id)
    return R200(render("image.html", image=image, comments=comments))


@e.http.POST("/image/<id>/comments")
def post_comment(request, image_id):
    comment = request.comment
    db_qry(
        "insert into comments (image_id, comment_text) values (?, ?)", image_id, comment
    )
    comments = db_qry("select * from comments where image_id=%d", image_id)
    return view_image(None, image_id)


if __name__ == "__main__":
    import c9c

    c9.compiler_cli()
