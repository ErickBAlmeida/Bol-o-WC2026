import os

from dotenv import load_dotenv
from flask import Flask

load_dotenv()


def create_app() -> Flask:
    app = Flask(__name__)
    app.secret_key = os.environ.get("SECRET_KEY", "troque-em-producao")

    from app.routes.leaderboard import leaderboard_bp
    from app.routes.main import main_bp
    from app.routes.predictions import predictions_bp

    app.register_blueprint(main_bp)
    app.register_blueprint(predictions_bp)
    app.register_blueprint(leaderboard_bp)

    return app
