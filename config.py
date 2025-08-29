import os

HOME_DIR = os.path.abspath(os.path.dirname(__file__))

STATIC_DIR = os.path.join(HOME_DIR, "static")
STATIC_FILES = [
    "script.js",
    "styles.css",
    "config.json"
]
CACHED_FILES = [
    #"styles.css",
    #"script.js"
]
DB_PATH = os.path.join(HOME_DIR, "temp/archive.db")

trusted_uploaders = [
    "m.seligey321@gmail.com"
]

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


class BaseConfig:
    SECRET_KEY = os.environ.get("SiteSecretKey", "fallback-secret")
    WTF_CSRF_ENABLED = True

class DevConfig(BaseConfig):
    DEBUG = True
    TESTING = True

class ProdConfig(BaseConfig):
    DEBUG = False
    TESTING = False
    SESSION_COOKIE_SECURE = True
