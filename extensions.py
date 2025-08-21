from flask_wtf.csrf import CSRFProtect

csrf = CSRFProtect()
# then call csrf.init_app(app)
