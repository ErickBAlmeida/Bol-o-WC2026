def calculate_points(pred_home: int, pred_away: int, real_home: int, real_away: int) -> int:
    if pred_home == real_home and pred_away == real_away:
        return 2
    # sign: +1 home win, -1 away win, 0 draw — two draws of different scores still match
    pred_outcome = (pred_home > pred_away) - (pred_home < pred_away)
    real_outcome = (real_home > real_away) - (real_home < real_away)
    return 1 if pred_outcome == real_outcome else 0
