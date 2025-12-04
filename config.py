import os
from dotenv import load_dotenv

load_dotenv()


HOME_DIR = os.path.abspath(os.path.dirname(__file__))

STATIC_DIR = os.path.join(HOME_DIR, "static")
STATIC_FILES = [
    "script.js",
    "styles.css",
    "config.json"
]
NPM_DIR = os.path.join(HOME_DIR, "npm")
CACHED_FILES = [
    #"styles.css",
    #"script.js"
]
DB_PATH = os.path.join(HOME_DIR, "temp/archive.db")


FLASK_ENV = os.environ.get("FLASK_ENV")
GOOGLE_CLIENT_ID = os.environ.get("GoogleClientID")
GOOGLE_CLIENT_SECRET = os.environ.get("GoogleClientSecret")
TEST = os.environ.get('TEST', 'false').strip()

trusted_uploaders = [ # for archive.org filtering
    "m.seligey321@gmail.com",
    "chasidustv.com@gmail.com"
]
trusted_subs = [ # for accessing site (google sub) 
    "117092394708269010937", # m.seligey321@gmail.com
    "105244470467228453598" # chasidustv.com@gmail.com
]

def set_csp(response):
    response.headers['Content-Security-Policy-Report-Only'] = (
        "default-src 'self' archive.org *.archive.org google.com *.google.com;"
    )
    return response


class BaseConfig:
    SECRET_KEY = os.environ.get("SiteSecretKey", "fallback-secret")
    WTF_CSRF_ENABLED = True

class DevConfig(BaseConfig):
    DEBUG = True
    TESTING = True

class ProdConfig(BaseConfig):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE=True     # only send cookie over HTTPS
    SESSION_COOKIE_HTTPONLY=True   # not accessible via JS
    SESSION_COOKIE_SAMESITE="Lax"  # CSRF protection
