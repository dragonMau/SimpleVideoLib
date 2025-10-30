# routes/api_routes.py
from io import BytesIO
from flask import Blueprint, abort, redirect, request, session, url_for
from config import TEST, trusted_subs
from time import time


priv_api = Blueprint("priv_api", __name__)

@priv_api.before_request
def is_trusted():
    user: dict[str] = session.get("user")
    if user and \
      user.get("exp", 0) >= time() and \
      user.get("sub") in trusted_subs:
        return
    else:
        return {"error": "Unauthorized"}, 401

@priv_api.route("/logout", methods=["POST"])
def logout():
    session.pop("user")
    return {"status": "success"}

@priv_api.route("/get_picture")
def get_picture():
    return {
        "picture": session["user"].get("picture", "")
    }, 200

@priv_api.route("/configure", methods=["POST"])
def configue():
    print("test configure success")
    data = request.form.to_dict(flat=False)
    print("data:", data)
    print("files:", request.files)
    for file in request.files.values():
        for byte in iter(lambda: file.stream.read(8192), b''):
            pass
    # for _ in range(2**26): pass # to test what happens on slow time
    return redirect("/")
    return {"status": "success", "recieved": data}