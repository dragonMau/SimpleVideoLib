# routes/api_routes.py
from flask import Blueprint, abort, request, session
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