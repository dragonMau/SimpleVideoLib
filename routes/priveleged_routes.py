# routes/api_routes.py
from io import BytesIO
from typing import Any
from flask import Blueprint, abort, redirect, request, session, url_for, render_template
from config import TEST, trusted_subs, GOOGLE_CLIENT_ID
from time import time
import services.database as db


priv_api = Blueprint("priv_api", __name__)

@priv_api.before_request
def is_trusted():
    user: None| dict[str, Any] = session.get("user")
    if user and \
      user.get("exp", 0) >= time() and \
      user.get("sub") in trusted_subs:
        return
    else:
        if request.endpoint == 'priv_api.panel': 
            return redirect("/login")
        return {"error": "Unauthorized"}, 401


@priv_api.route("/panel")
def panel():
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

@priv_api.route("/admin/all_videos")
def send_all_videos():
    return db.get_all_videos()