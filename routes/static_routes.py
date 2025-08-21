from flask import Blueprint, render_template, send_from_directory, abort
from config import STATIC_DIR, STATIC_FILES

static = Blueprint("static", __name__)

@static.route("/")
def serve_index():
    return render_template("index.html")

@static.route("/<file_name>")
def serve_allowed_static(file_name):
    if file_name in STATIC_FILES:
        return send_from_directory(STATIC_DIR, file_name)
    abort(404)