from flask import Blueprint, Response
import requests
from datetime import datetime, timedelta

proxy = Blueprint("proxy", __name__)

# Not used with nginx, nginx proxies it /thumb/*
@proxy.route("/thumb/<archive_id>")
def thumb_proxy(archive_id):
    print("Flask Thumb Fallback")
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