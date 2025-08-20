import sys
import database_man
from database_man import Video, Playlist, Group
from flask import Flask, Response, jsonify, make_response, request, \
    send_from_directory, abort, render_template, session
import os
from dotenv import load_dotenv
import requests
from flask_wtf.csrf import CSRFProtect
from datetime import datetime, timedelta

app = Flask(__name__)
HOME_DIR = "./"
load_dotenv()
app.secret_key = os.environ.get('SiteSecretKey')
csrf = CSRFProtect(app)

def create_template():
    with open('index.html', 'r') as in_file:
        content = in_file.read()
    
    os.makedirs(HOME_DIR + 'templates/', exist_ok=True)
    
    with open(HOME_DIR + 'templates/index.html', 'w') as out_file:
        out_file.write(content.replace(r'%csrf_token%', '{{ csrf_token() }}'))

@app.route("/")
def serve_index():
    is_admin = session.get('admin', False)
    return render_template("index.html",  is_admin=is_admin)

@app.route("/script.js")
def serve_script():
    return send_from_directory(HOME_DIR, "script.js")

@app.route("/styles.css")
def serve_styles():
    return send_from_directory(HOME_DIR, "styles.css")


@app.route("/groups", methods=["GET"])
def get_groups():
    return {
        "type": "groups list",
        "items": database_man.get_groups()
    }

@app.route("/groups/<id_>/playlists", methods=["GET"])
def get_playlists(id_):
    group_data = {
        "type": "playlists list",
        "items": database_man.get_playlists(id_)
    }
    if group_data:
        return group_data
    else:
        abort(404, description=f"Group '{id_}' not found")

@app.route("/playlists/<id_>/videos")
def get_videos(id_):
    playlist_data = {
        "type": "videos list",
        "items": database_man.get_videos(id_)
    }
    if playlist_data:
        return playlist_data
    else:
        abort(404, description=f"Playlist '{id_}' not found")

@app.route("/config")
def get_config():
    return send_from_directory(HOME_DIR, "config.json")


@app.route("/thumb/<archive_id>")
def thumb_proxy(archive_id):
    url = f"https://archive.org/download/{archive_id}/__ia_thumb.jpg"
    r = requests.get(url, stream=True)
    if r.status_code != 200:
        return "Not found", 404
    
    response = Response(r.content, mimetype="image/jpeg")

     # Cache for 1 week
    cache_duration = 7 * 24 * 60 * 60  # seconds
    response.headers["Cache-Control"] = f"public, max-age={cache_duration}"
    
    # Optional: set Expires header
    expires = datetime.now() + timedelta(seconds=cache_duration)
    response.headers["Expires"] = expires.strftime("%a, %d %b %Y %H:%M:%S GMT")

    return response

@app.after_request
def set_csp(response):
    response.headers['Content-Security-Policy'] = (
        "default-src 'self';"
        "style-src 'self' 'unsafe-inline';"
        "frame-src 'self' archive.org *.archive.org;"
        "img-src 'self' archive.org *.archive.org;"
        "connect-src 'self' archive.org *.archive.org;"
        "script-src 'self' 'unsafe-inline' archive.org *.archive.org;"
    )
    return response
# Example POST route to test CSRF (you can remove this if not needed)

@app.route("/test-post", methods=["POST"])
def test_post():
    print("test post success")
    data = request.get_json()
    print('data:', data)
    return {"status": "success", "received": data}

def init():
    print("Preparing to start App")
    create_template()
    if os.environ.get('TEST', 'false').strip() == "true":
        print("test mode")
        database_man.init_db()
    else:
        print("release mode")
        database_man.do_all()
    print("Starting App")

init()

if __name__ == "__main__":
    app.run(debug=True, port=5000)