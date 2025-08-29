# routes/api_routes.py
from flask import Blueprint, abort, request
import services.database as db
import os

api = Blueprint("api", __name__)

@api.record_once
def init(state):
    if os.environ.get('TEST', 'false').strip() == "true":
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