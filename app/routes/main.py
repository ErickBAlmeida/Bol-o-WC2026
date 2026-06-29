from datetime import date, datetime, timezone

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


def _refresh_matches_in_db(force: bool = False) -> tuple[int | None, str | None]:
    matches, matchday, stage = get_matches_for_matchday(force_refresh=force)
    if not matches:
        return None, None

    conn = get_db()
    try:
        with conn.cursor() as cur:
            for m in matches:
                # Skip matches where teams haven't been determined yet
                if not m.get("homeTeam", {}).get("name") or not m.get("awayTeam", {}).get("name"):
                    continue

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
    return matchday, stage


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
    stage = None
    try:
        matchday, stage = _refresh_matches_in_db()
        _score_finished_matches()
    except Exception:
        pass

    if matchday is None and stage is None:
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
            elif stage is not None:
                cur.execute(
                    """
                    SELECT m.id, m.home_team, m.away_team, m.kickoff_utc, m.status,
                           m.home_score, m.away_score, m.stage, m.winner,
                           p.pred_home, p.pred_away, p.tiebreaker, p.points
                    FROM matches m
                    LEFT JOIN predictions p ON p.match_id = m.id AND p.player_id = %s
                    WHERE m.stage = %s
                    ORDER BY m.kickoff_utc
                    """,
                    (player_id, stage),
                )
            else:
                cur.execute(
                    """
                    SELECT m.id, m.home_team, m.away_team, m.kickoff_utc, m.status,
                           m.home_score, m.away_score, m.stage, m.winner,
                           p.pred_home, p.pred_away, p.tiebreaker, p.points
                    FROM matches m
                    LEFT JOIN predictions p ON p.match_id = m.id AND p.player_id = %s
                    WHERE DATE(m.kickoff_utc) = %s
                    ORDER BY m.kickoff_utc
                    """,
                    (player_id, date.today()),
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

    _STAGE_LABELS = {
        "LAST_32": "Rodada de 32",
        "LAST_16": "Oitavas de Final",
        "QUARTER_FINALS": "Quartas de Final",
        "SEMI_FINALS": "Semifinais",
        "THIRD_PLACE": "Disputa do 3º Lugar",
        "FINAL": "Final",
    }
    stage_label = _STAGE_LABELS.get(stage) if stage else None

    return render_template("index.html", days_with_matches=days_with_matches,
                           now=now, matchday=matchday, stage_label=stage_label)


@main_bp.route("/nickname", methods=["GET", "POST"])
def nickname():
    if request.method == "POST":
        nick = request.form.get("nickname", "").strip()
        pin = request.form.get("pin", "").strip()

        if not nick or len(nick) > 50:
            return render_template("nickname.html", error="Apelido inválido (máx 50 caracteres)")
        if not pin.isdigit() or len(pin) != 4:
            return render_template("nickname.html", error="PIN deve ter exatamente 4 números", nickname=nick)

        conn = get_db()
        try:
            with conn.cursor() as cur:
                cur.execute(
                    "SELECT id, nickname, pin FROM players WHERE LOWER(nickname) = LOWER(%s)",
                    (nick,),
                )
                row = cur.fetchone()

                if row is None:
                    # Novo usuário — cria com o PIN fornecido
                    cur.execute(
                        "INSERT INTO players (nickname, pin) VALUES (%s, %s) RETURNING id",
                        (nick, pin),
                    )
                    player_id = cur.fetchone()[0]
                    display_nick = nick
                else:
                    player_id, display_nick, stored_pin = row
                    if stored_pin is None:
                        # Usuário antigo sem PIN — define agora
                        cur.execute("UPDATE players SET pin = %s WHERE id = %s", (pin, player_id))
                    elif stored_pin != pin:
                        return render_template("nickname.html", error="PIN incorreto", nickname=nick)

            conn.commit()
        finally:
            conn.close()

        session["nickname"] = display_nick
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
