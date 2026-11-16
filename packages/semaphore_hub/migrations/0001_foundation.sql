CREATE TABLE accounts (
    account_id TEXT PRIMARY KEY NOT NULL,
    login_name TEXT UNIQUE,
    display_name TEXT,
    password_hash TEXT,
    is_operator INTEGER NOT NULL DEFAULT 0 CHECK (is_operator IN (0, 1)),
    created_at INTEGER NOT NULL CHECK (created_at >= 0),
    deleted_at INTEGER,
    CHECK ((deleted_at IS NULL AND login_name IS NOT NULL AND display_name IS NOT NULL
            AND password_hash IS NOT NULL)
        OR (deleted_at IS NOT NULL AND login_name IS NULL AND display_name IS NULL
            AND password_hash IS NULL AND is_operator = 0)),
    CHECK (login_name IS NULL OR (length(login_name) BETWEEN 3 AND 32
        AND login_name NOT GLOB '*[^a-z0-9_]*'))
);
CREATE TABLE sessions (
    session_id TEXT PRIMARY KEY NOT NULL,
    account_id TEXT NOT NULL REFERENCES accounts(account_id),
    token_digest TEXT NOT NULL UNIQUE,
    csrf_digest TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    last_seen_at INTEGER NOT NULL,
    absolute_expires_at INTEGER NOT NULL,
    CHECK (created_at <= last_seen_at AND last_seen_at <= absolute_expires_at)
);
CREATE INDEX sessions_account ON sessions(account_id);
CREATE TABLE packs (
    pack_id TEXT PRIMARY KEY NOT NULL,
    owner_id TEXT NOT NULL REFERENCES accounts(account_id),
    created_at INTEGER NOT NULL,
    retired_at INTEGER
);
CREATE TABLE pack_versions (
    version_id TEXT PRIMARY KEY NOT NULL,
    pack_id TEXT NOT NULL REFERENCES packs(pack_id),
    version TEXT NOT NULL,
    manifest_bytes BLOB NOT NULL,
    manifest_digest TEXT NOT NULL,
    semantic_hash TEXT NOT NULL,
    vector_hash TEXT NOT NULL,
    created_at INTEGER NOT NULL,
    UNIQUE (pack_id, version)
);
CREATE TRIGGER immutable_version BEFORE UPDATE ON pack_versions BEGIN
    SELECT RAISE(ABORT, 'immutable pack version');
END;
CREATE TABLE games (
    game_id TEXT PRIMARY KEY NOT NULL,
    player_id TEXT REFERENCES accounts(account_id),
    version_id TEXT NOT NULL REFERENCES pack_versions(version_id),
    mode TEXT NOT NULL CHECK (mode IN ('casual', 'event')),
    fingerprint_hash TEXT NOT NULL,
    model_identity_json TEXT NOT NULL CHECK (json_valid(model_identity_json)),
    ruleset_id TEXT NOT NULL,
    config_digest TEXT NOT NULL,
    config_json TEXT NOT NULL CHECK (json_valid(config_json)),
    artifact_id TEXT NOT NULL,
    challenge_digest TEXT,
    revision INTEGER NOT NULL CHECK (revision >= 0),
    status TEXT NOT NULL CHECK (status IN ('active', 'over')),
    started_at INTEGER NOT NULL,
    finished_at INTEGER,
    end_reason TEXT,
    snapshot_json TEXT NOT NULL CHECK (json_valid(snapshot_json)),
    CHECK ((status = 'active' AND finished_at IS NULL AND end_reason IS NULL)
        OR (status = 'over' AND finished_at >= started_at AND finished_at IS NOT NULL
            AND end_reason IS NOT NULL AND end_reason IN
            ('overflow', 'pack_cleared', 'pack_exhausted', 'event_complete', 'interrupted'))),
    CHECK (end_reason IS NULL OR end_reason IN ('overflow', 'interrupted')
        OR (mode = 'casual' AND end_reason IN ('pack_cleared', 'pack_exhausted'))
        OR (mode = 'event' AND end_reason = 'event_complete')),
    CHECK ((mode = 'casual' AND challenge_digest IS NULL)
        OR (mode = 'event' AND challenge_digest IS NOT NULL))
);
CREATE INDEX games_player ON games(player_id, started_at, game_id);
CREATE TRIGGER immutable_game_pins BEFORE UPDATE OF version_id, mode, fingerprint_hash,
    model_identity_json, ruleset_id, config_digest, config_json, artifact_id,
    challenge_digest, started_at ON games BEGIN
    SELECT RAISE(ABORT, 'immutable game pins');
END;
CREATE TRIGGER terminal_game_frozen BEFORE UPDATE OF revision, status, finished_at,
    end_reason, snapshot_json ON games WHEN OLD.status = 'over' BEGIN
    SELECT RAISE(ABORT, 'terminal game is immutable');
END;
CREATE TABLE commands (
    game_id TEXT NOT NULL REFERENCES games(game_id),
    command_id TEXT NOT NULL,
    payload_hmac TEXT NOT NULL,
    hmac_key_version TEXT NOT NULL,
    received_at INTEGER NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('pending', 'final')),
    receipt_json TEXT NOT NULL CHECK (json_valid(receipt_json)),
    expires_at INTEGER,
    PRIMARY KEY (game_id, command_id)
);
CREATE TRIGGER immutable_command_identity BEFORE UPDATE OF game_id, command_id,
    payload_hmac, hmac_key_version, received_at ON commands BEGIN
    SELECT RAISE(ABORT, 'immutable command identity');
END;
CREATE TRIGGER immutable_final_receipt BEFORE UPDATE OF state, receipt_json ON commands
    WHEN OLD.state = 'final' BEGIN
    SELECT RAISE(ABORT, 'immutable final receipt');
END;
CREATE TABLE clue_attempts (
    game_id TEXT NOT NULL,
    command_id TEXT NOT NULL,
    raw_clue TEXT,
    target_id TEXT,
    received_at INTEGER NOT NULL,
    resolved_at INTEGER,
    outcome TEXT,
    target_rank INTEGER,
    PRIMARY KEY (game_id, command_id),
    FOREIGN KEY (game_id, command_id) REFERENCES commands(game_id, command_id) ON DELETE CASCADE
);
CREATE INDEX attempts_expiry ON clue_attempts(received_at);
CREATE INDEX commands_expiry ON commands(expires_at);
CREATE TABLE scores (
    game_id TEXT PRIMARY KEY NOT NULL REFERENCES games(game_id),
    player_id TEXT REFERENCES accounts(account_id),
    display_name TEXT,
    score INTEGER NOT NULL CHECK (score >= 0),
    completed_at INTEGER NOT NULL
);
CREATE TRIGGER natural_score_only BEFORE INSERT ON scores WHEN NOT EXISTS (
    SELECT 1 FROM games WHERE game_id = NEW.game_id AND status = 'over'
        AND end_reason != 'interrupted' AND finished_at = NEW.completed_at
        AND player_id IS NEW.player_id
) BEGIN
    SELECT RAISE(ABORT, 'score requires matching natural terminal game');
END;
CREATE TRIGGER immutable_score BEFORE UPDATE OF game_id, score, completed_at ON scores BEGIN
    SELECT RAISE(ABORT, 'immutable score');
END;
CREATE TABLE deletion_ledger (
    deletion_id TEXT PRIMARY KEY NOT NULL,
    account_id TEXT NOT NULL,
    scope TEXT NOT NULL CHECK (scope IN ('clues', 'account')),
    requested_at INTEGER NOT NULL,
    retain_until INTEGER NOT NULL CHECK (retain_until >= requested_at)
);
