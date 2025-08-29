# routes/api_routes.py
from flask import Blueprint, abort, request, session
import services.database as db
from config import TEST, trusted_subs
from google.oauth2 import id_token
from google.auth.transport import requests
import json
from time import time


api = Blueprint("api", __name__)

@api.record_once
def init(state):
    if TEST == "true":
        print("test db mode (not updating)")
        db.init_db()
    else:
        print("release db mode (updating)")
        db.do_all()


@api.route("/groups", methods=["GET"])
def get_groups():
    return {
        "type": "groups list",
        "items": db.get_groups()
    }

@api.route("/groups/<id_>/playlists", methods=["GET"])
def get_playlists(id_):
    group_data = {
        "type": "playlists list",
        "items": db.get_playlists(id_)
    }
    if group_data:
        return group_data
    else:
        abort(404, description=f"Group '{id_}' not found")

@api.route("/playlists/<id_>/videos")
def get_videos(id_):
    playlist_data = {
        "type": "videos list",
        "items": db.get_videos(id_)
    }
    if playlist_data:
        return playlist_data
    else:
        abort(404, description=f"Playlist '{id_}' not found")


# Example POST route to test CSRF (you can remove this if not needed)
@api.route("/test-post", methods=["POST"])
def test_post():
    print("test post success")
    data = request.get_json()
    print('data:', data)
    return {"status": "success", "received": data}

@api.route("/login", methods=['POST'])
def login():
    data: dict[str] = json.loads(request.get_json())
    credential = data.get("credential")
    idinfo: dict[str] = id_token.verify_oauth2_token(credential, requests.Request())

    session['user'] = {
        'sub': idinfo.get("sub"),
        'exp': int(idinfo.get("exp"))
    }
    return {
        "status": "success",
        "trusted": idinfo.get('sub') in trusted_subs,
        "picture": idinfo.get('picture')
    }

def is_trusted():
    user: dict[str] = session.get("user")
    if not user: return False

    # Check expiration
    if user.get("exp", 0) < time():
        session.pop("user")  # remove expired session
        return False
    
    if user.get("sub") in trusted_subs:
        return True
    else:
        return False
