from datetime import datetime, timezone

from flask import Blueprint, jsonify, redirect, render_template, request, session, url_for

from app.db import get_db

predictions_bp = Blueprint("predictions", __name__)


@predictions_bp.route("/predict/<int:match_id>", methods=["POST"])
def predict(match_id):
    if not session.get("nickname"):
        return redirect(url_for("main.nickname"))

    player_id = session.get("player_id")
    pred_home = request.form.get("pred_home", type=int)
    pred_away = request.form.get("pred_away", type=int)
    tiebreaker = request.form.get("tiebreaker") or None

    if pred_home is None or pred_away is None or pred_home < 0 or pred_away < 0:
        return render_template("error.html", message="Palpite inválido."), 400

    if tiebreaker not in (None, "home", "away"):
        return render_template("error.html", message="Palpite inválido."), 400

    conn = get_db()
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT kickoff_utc, status, stage FROM matches WHERE id = %s", (match_id,))
            row = cur.fetchone()
            if not row:
                return render_template("error.html", message="Partida não encontrada."), 404

            kickoff, status, stage = row
            if kickoff <= datetime.now(timezone.utc):
                return render_template("error.html", message="Palpites encerrados para essa partida."), 403

            is_knockout = stage is not None and stage != "GROUP_STAGE"
            if is_knockout and pred_home == pred_away and tiebreaker is None:
                return render_template("error.html", message="Escolha qual time avança."), 400

            # tiebreaker only applies to knockout draws; clear it otherwise
            if not (is_knockout and pred_home == pred_away):
                tiebreaker = None

            cur.execute(
                """
                INSERT INTO predictions (player_id, match_id, pred_home, pred_away, tiebreaker)
                VALUES (%s, %s, %s, %s, %s)
                ON CONFLICT (player_id, match_id) DO UPDATE SET
                    pred_home = EXCLUDED.pred_home,
                    pred_away = EXCLUDED.pred_away,
                    tiebreaker = EXCLUDED.tiebreaker,
                    submitted_at = NOW(),
                    points = NULL
                """,
                (player_id, match_id, pred_home, pred_away, tiebreaker),
            )
        conn.commit()
    finally:
        conn.close()

    if request.headers.get("X-Requested-With") == "XMLHttpRequest":
        return jsonify({"ok": True})
    return redirect(url_for("main.index"))
