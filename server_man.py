import sys
import database_man
from database_man import Video, Playlist, Group
from flask import Flask, jsonify, make_response, request, \
    send_from_directory, abort, render_template, session
import os
from dotenv import load_dotenv
from flask_wtf.csrf import CSRFProtect

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


@app.after_request
def set_csp(response):
    response.headers['Content-Security-Policy'] = "default-src 'self'; script-src 'self' 'unsafe-inline'; style-src 'self' 'unsafe-inline'; img-src 'self' archive.org; frame-src archive.org"
    return response
# Example POST route to test CSRF (you can remove this if not needed)

@app.route("/test-post", methods=["POST"])
def test_post():
    print("test post success")
    data = request.get_json()
    print('data:', data)
    return {"status": "success", "received": data}

def init_app():
    create_template()
    database_man.do_all()

if __name__ == "__main__":
    init_app()
    app.run(debug=True, port=5000)