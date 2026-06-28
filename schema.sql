CREATE TABLE IF NOT EXISTS players (
    id SERIAL PRIMARY KEY,
    nickname VARCHAR(50) UNIQUE NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS matches (
    id INTEGER PRIMARY KEY,
    home_team VARCHAR(100) NOT NULL,
    away_team VARCHAR(100) NOT NULL,
    kickoff_utc TIMESTAMPTZ NOT NULL,
    status VARCHAR(20) NOT NULL,
    home_score INTEGER,
    away_score INTEGER,
    matchday INTEGER,
    stage VARCHAR(50),
    winner VARCHAR(10),
    last_updated TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    player_id INTEGER REFERENCES players(id),
    match_id INTEGER REFERENCES matches(id),
    pred_home INTEGER NOT NULL,
    pred_away INTEGER NOT NULL,
    tiebreaker VARCHAR(10),
    points INTEGER,
    submitted_at TIMESTAMPTZ DEFAULT NOW(),
    UNIQUE(player_id, match_id)
);
