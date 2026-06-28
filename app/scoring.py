def calculate_points(
    pred_home: int,
    pred_away: int,
    real_home: int,
    real_away: int,
    pred_tiebreaker: str | None = None,
    real_winner: str | None = None,
) -> int:
    if pred_home == real_home and pred_away == real_away:
        pts = 2
    else:
        pred_out = (pred_home > pred_away) - (pred_home < pred_away)
        real_out = (real_home > real_away) - (real_home < real_away)
        pts = 1 if pred_out == real_out else 0

    # Bonus for correct tiebreaker in knockout draws
    if (pred_tiebreaker and real_winner
            and pred_home == pred_away
            and real_home == real_away
            and pred_tiebreaker == real_winner):
        pts += 1

    return pts
