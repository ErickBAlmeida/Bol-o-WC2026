from datetime import date, datetime, timedelta, timezone

_WEEKDAYS_PT = ['Seg', 'Ter', 'Qua', 'Qui', 'Sex', 'Sáb', 'Dom']
_MONTHS_PT = ['jan', 'fev', 'mar', 'abr', 'mai', 'jun',
              'jul', 'ago', 'set', 'out', 'nov', 'dez']


def _fmt_day_pt(d: date) -> str:
    return f"{_WEEKDAYS_PT[d.weekday()]}, {d.day} de {_MONTHS_PT[d.month - 1]}"

import psycopg2.extras
from flask import Blueprint, redirect, render_template, request, session, url_for, flash

from app.db import get_db
from app.football_api import get_current_matchday, get_matches_for_matchday, parse_kickoff
from app.scoring import calculate_points

main_bp = Blueprint("main", __name__)


def _refresh_matches_in_db(force: bool = False) -> int | None:
    matches, matchday = get_matches_for_matchday(force_refresh=force)
    if not matches:
        return None

    conn = get_db()
    try:
        with conn.cursor() as cur:
            for m in matches:
                score = m.get("score", {})
                full_time = score.get("fullTime", {})
                kickoff = parse_kickoff(m["utcDate"])
                raw_winner = score.get("winner")
                winner = (
                    "home" if raw_winner == "HOME_TEAM"
                    else "away" if raw_winner == "AWAY_TEAM"
                    else None
                )
                cur.execute(
                    """
                    INSERT INTO matches (id, home_team, away_team, kickoff_utc, status, home_score, away_score, matchday, stage, winner)
                    VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
                    ON CONFLICT (id) DO UPDATE SET
                        status = EXCLUDED.status,
                        home_score = EXCLUDED.home_score,
                        away_score = EXCLUDED.away_score,
                        matchday = EXCLUDED.matchday,
                        stage = EXCLUDED.stage,
                        winner = EXCLUDED.winner,
                        last_updated = NOW()
                    """,
                    (
                        m["id"],
                        m["homeTeam"]["name"],
                        m["awayTeam"]["name"],
                        kickoff,
                        m["status"],
                        full_time.get("home"),
                        full_time.get("away"),
                        m.get("matchday"),
                        m.get("stage"),
                        winner,
                    ),
                )
        conn.commit()
    finally:
        conn.close()
    return matchday


def _score_finished_matches() -> int:
    conn = get_db()
    updated = 0
    try:
        with conn.cursor() as cur:
            cur.execute(
                """
                SELECT p.id, p.pred_home, p.pred_away, p.tiebreaker,
                       m.home_score, m.away_score, m.winner
                FROM predictions p
                JOIN matches m ON m.id = p.match_id
                WHERE m.status = 'FINISHED'
                  AND m.home_score IS NOT NULL
                  AND p.points IS NULL
                """
            )
            rows = cur.fetchall()
            for pred_id, ph, pa, tb, rh, ra, winner in rows:
                pts = calculate_points(ph, pa, rh, ra, tb, winner)
                cur.execute("UPDATE predictions SET points = %s WHERE id = %s", (pts, pred_id))
                updated += 1
        conn.commit()
    finally:
        conn.close()
    return updated


@main_bp.route("/")
def index():
    if not session.get("nickname"):
        return redirect(url_for("main.nickname"))

    matchday = None
    try:
        matchday = _refresh_matches_in_db()
        _score_finished_matches()
    except Exception:
        pass

    if matchday is None:
        try:
            matchday = get_current_matchday()
        except Exception:
            pass

    player_id = session.get("player_id")
    now = datetime.now(timezone.utc)

    conn = get_db()
    try:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            if matchday is not None:
                cur.execute(
                    """
                    SELECT m.id, m.home_team, m.away_team, m.kickoff_utc, m.status,
                           m.home_score, m.away_score, m.stage, m.winner,
                           p.pred_home, p.pred_away, p.tiebreaker, p.points
                    FROM matches m
                    LEFT JOIN predictions p ON p.match_id = m.id AND p.player_id = %s
                    WHERE m.matchday = %s
                    ORDER BY m.kickoff_utc
                    """,
                    (player_id, matchday),
                )
            else:
                # No matchday (knockout rounds) — show a rolling window around today
                cur.execute(
                    """
                    SELECT m.id, m.home_team, m.away_team, m.kickoff_utc, m.status,
                           m.home_score, m.away_score, m.stage, m.winner,
                           p.pred_home, p.pred_away, p.tiebreaker, p.points
                    FROM matches m
                    LEFT JOIN predictions p ON p.match_id = m.id AND p.player_id = %s
                    WHERE DATE(m.kickoff_utc) BETWEEN %s AND %s
                    ORDER BY m.kickoff_utc
                    """,
                    (player_id, date.today() - timedelta(days=1), date.today() + timedelta(days=10)),
                )
            matches = cur.fetchall()
    finally:
        conn.close()

    # Group matches by calendar day, preserving kickoff order from the query
    matches_by_day: dict[date, list] = {}
    for m in matches:
        day = m['kickoff_utc'].date()
        matches_by_day.setdefault(day, []).append(m)

    days_with_matches = [(_fmt_day_pt(day), day_matches)
                         for day, day_matches in matches_by_day.items()]

    return render_template("index.html", days_with_matches=days_with_matches,
                           now=now, matchday=matchday)


@main_bp.route("/nickname", methods=["GET", "POST"])
def nickname():
    if request.method == "POST":
        nick = request.form.get("nickname", "").strip()
        if not nick or len(nick) > 50:
            return render_template("nickname.html", error="Apelido inválido (máx 50 caracteres)")

        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    """
                    INSERT INTO players (nickname) VALUES (%s)
                    ON CONFLICT (nickname) DO UPDATE SET nickname = EXCLUDED.nickname
                    RETURNING id
                    """,
                    (nick,),
                )
                player_id = cur.fetchone()[0]
            conn.commit()
        finally:
            conn.close()

        session["nickname"] = nick
        session["player_id"] = player_id
        return redirect(url_for("main.index"))

    return render_template("nickname.html")


@main_bp.route("/logout", methods=["POST"])
def logout():
    session.clear()
    return redirect(url_for("main.nickname"))


@main_bp.route("/admin/sync", methods=["POST"])
def admin_sync():
    try:
        _refresh_matches_in_db(force=True)
        scored = _score_finished_matches()
        session["sync_msg"] = f"Sincronizado. {scored} palpite(s) pontuado(s)."
    except Exception as e:
        session["sync_msg"] = f"Erro: {e}"
    return redirect(url_for("main.index"))
