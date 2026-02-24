# routes/api_routes.py
from io import BytesIO
from typing import Any
from flask import Blueprint, abort, redirect, request, session, url_for, render_template
from config import TEST, trusted_subs, GOOGLE_CLIENT_ID
from time import time


priv_api = Blueprint("priv_api", __name__)

@priv_api.before_request
def is_trusted():
    user: dict[str, Any] = session.get("user")
    if user and \
      user.get("exp", 0) >= time() and \
      user.get("sub") in trusted_subs:
        return
    else:
        return {"error": "Unauthorized"}, 401


@priv_api.route("/panel")
def login():
    return render_template("panel.html", google_cid=GOOGLE_CLIENT_ID)

@priv_api.route("/logout", methods=["POST"])
def logout():
    session.pop("user")
    return {"status": "success"}

@priv_api.route("/get_picture")
def get_picture():
    return {
        "picture": session["user"].get("picture", "")
    }, 200
