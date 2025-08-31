from flask import Flask
from routes.api_routes import api
from routes.static_routes import static
from routes.proxy_routes import proxy
from routes.priveleged_routes import priv_api
from extensions import csrf
from config import set_csp, FLASK_ENV

def create_app():
    print("Preparing to start App")

    app = Flask(__name__)
    
    if FLASK_ENV == "production":
        app.config.from_object("config.ProdConfig")
    else:
        app.config.from_object("config.DevConfig")
    
    csrf.init_app(app)
    app.register_blueprint(api)
    app.register_blueprint(priv_api)
    app.register_blueprint(static)
    app.register_blueprint(proxy)

    app.after_request(set_csp)
    print("Starting App")
    
    return app

# entry for gunicorn:
#    python_path -u -m gunicorn -b 127.0.0.1:9000 "app:create_app()"

if __name__ == "__main__":
    app = create_app()
    app.run(debug=True, port=9000, use_reloader=False)
