import psycopg2.extras
from flask import Blueprint, render_template, session

from app.db import get_db

leaderboard_bp = Blueprint("leaderboard", __name__)


@leaderboard_bp.route("/leaderboard")
def leaderboard():
    current_nick = session.get("nickname")

    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute(
                """
                SELECT
                    p.nickname,
                    COALESCE(SUM(pr.points), 0)                                    AS total_points,
                    COUNT(pr.id) FILTER (WHERE pr.points = 2)                      AS exact_scores,
                    COUNT(pr.id) FILTER (WHERE pr.points = 1)                      AS correct_outcomes,
                    COUNT(pr.id) FILTER (WHERE pr.points = 0)                      AS wrong,
                    COUNT(pr.id)                                                    AS total_predictions
                FROM players p
                LEFT JOIN predictions pr ON pr.player_id = p.id
                GROUP BY p.id, p.nickname
                ORDER BY total_points DESC, exact_scores DESC, p.nickname ASC
                """
            )
            ranking = cur.fetchall()
    finally:
        conn.close()

    return render_template("leaderboard.html", ranking=ranking, current_nick=current_nick)
