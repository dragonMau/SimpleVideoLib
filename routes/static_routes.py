from flask import Blueprint, render_template, send_from_directory, abort, make_response
from config import STATIC_DIR, STATIC_FILES, CACHED_FILES
from datetime import datetime, timedelta

static = Blueprint("static", __name__)

@static.route("/")
def serve_index():
    return render_template("index.html")

@static.route("/<file_name>")
def serve_allowed_static(file_name):
    if file_name in STATIC_FILES:
        response = make_response(send_from_directory(STATIC_DIR, file_name))
        
        if file_name in CACHED_FILES:
            response.headers["Cache-Control"] = "public, max-age=604800"  # 7 days
            response.headers["Expires"] = (datetime.now() + timedelta(days=7))\
                                          .strftime("%a, %d %b %Y %H:%M:%S GMT")
        return response
    abort(404)
