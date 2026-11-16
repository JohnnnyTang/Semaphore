CREATE TABLE install_reservations (
    install_id TEXT PRIMARY KEY NOT NULL,
    pack_id TEXT NOT NULL REFERENCES packs(pack_id),
    version TEXT NOT NULL,
    manifest_digest TEXT NOT NULL,
    state TEXT NOT NULL CHECK (state IN ('pending','published','failed','cancelled')),
    created_at INTEGER NOT NULL,
    finished_at INTEGER,
    CHECK ((state = 'pending' AND finished_at IS NULL)
        OR (state != 'pending' AND finished_at IS NOT NULL))
);
CREATE UNIQUE INDEX one_pending_install ON install_reservations(pack_id, version)
    WHERE state = 'pending';
CREATE TABLE pack_entries (
    version_id TEXT NOT NULL REFERENCES pack_versions(version_id),
    ordinal INTEGER NOT NULL CHECK (ordinal >= 0),
    entry_id TEXT NOT NULL,
    entry_json TEXT NOT NULL CHECK (json_valid(entry_json)),
    PRIMARY KEY (version_id, entry_id),
    UNIQUE (version_id, ordinal)
);
CREATE TRIGGER immutable_entry BEFORE UPDATE ON pack_entries BEGIN
    SELECT RAISE(ABORT, 'immutable pack entry');
END;
CREATE TABLE verification_reports (
    report_id TEXT PRIMARY KEY NOT NULL,
    version_id TEXT NOT NULL REFERENCES pack_versions(version_id),
    manifest_digest TEXT NOT NULL,
    semantic_hash TEXT NOT NULL,
    fingerprint_hash TEXT NOT NULL,
    protocol_hash TEXT NOT NULL,
    ruleset_id TEXT NOT NULL,
    trusted INTEGER NOT NULL CHECK (trusted IN (0,1)),
    passed INTEGER NOT NULL CHECK (passed IN (0,1)),
    report_json TEXT NOT NULL CHECK (json_valid(report_json)),
    created_at INTEGER NOT NULL,
    UNIQUE (report_id, version_id)
);
CREATE TRIGGER report_version_pins BEFORE INSERT ON verification_reports WHEN NOT EXISTS (
    SELECT 1 FROM pack_versions WHERE version_id = NEW.version_id
        AND manifest_digest = NEW.manifest_digest AND semantic_hash = NEW.semantic_hash
) BEGIN
    SELECT RAISE(ABORT, 'report version identity mismatch');
END;
CREATE TRIGGER immutable_report BEFORE UPDATE ON verification_reports BEGIN
    SELECT RAISE(ABORT, 'immutable report');
END;
CREATE TABLE vector_caches (
    vector_hash TEXT NOT NULL,
    fingerprint_hash TEXT NOT NULL,
    ordered_vectors_digest TEXT NOT NULL,
    asset_path TEXT NOT NULL,
    dimensions INTEGER NOT NULL CHECK (dimensions > 0),
    entry_count INTEGER NOT NULL CHECK (entry_count > 0),
    PRIMARY KEY (vector_hash, fingerprint_hash)
);
CREATE TRIGGER immutable_vector_cache BEFORE UPDATE ON vector_caches BEGIN
    SELECT RAISE(ABORT, 'immutable vector cache');
END;
CREATE TABLE published_versions (
    version_id TEXT PRIMARY KEY NOT NULL REFERENCES pack_versions(version_id),
    report_id TEXT NOT NULL,
    accepted_by TEXT NOT NULL REFERENCES accounts(account_id),
    rights_reference TEXT NOT NULL CHECK (length(rights_reference) > 0),
    accepted_at INTEGER NOT NULL,
    FOREIGN KEY (report_id, version_id) REFERENCES verification_reports(report_id, version_id)
);
CREATE TRIGGER trusted_publication BEFORE INSERT ON published_versions WHEN NOT EXISTS (
    SELECT 1 FROM verification_reports WHERE report_id = NEW.report_id
        AND version_id = NEW.version_id AND trusted = 1 AND passed = 1
) BEGIN
    SELECT RAISE(ABORT, 'publication requires trusted passing report');
END;
CREATE TRIGGER immutable_publication BEFORE UPDATE ON published_versions BEGIN
    SELECT RAISE(ABORT, 'immutable publication acceptance');
END;
CREATE TABLE artifacts (
    artifact_id TEXT PRIMARY KEY NOT NULL,
    version_id TEXT NOT NULL REFERENCES published_versions(version_id),
    report_id TEXT NOT NULL,
    mode TEXT NOT NULL CHECK (mode IN ('casual','event')),
    fingerprint_hash TEXT NOT NULL,
    ruleset_id TEXT NOT NULL,
    config_digest TEXT NOT NULL,
    config_json TEXT NOT NULL CHECK (json_valid(config_json)),
    artifact_digest TEXT NOT NULL,
    artifact_json TEXT NOT NULL CHECK (json_valid(artifact_json)),
    challenge_digest TEXT,
    FOREIGN KEY (report_id, version_id) REFERENCES verification_reports(report_id, version_id),
    CHECK ((mode='casual' AND challenge_digest IS NULL)
        OR (mode='event' AND challenge_digest IS NOT NULL))
);
CREATE TRIGGER artifact_report_pins BEFORE INSERT ON artifacts WHEN NOT EXISTS (
    SELECT 1 FROM verification_reports WHERE report_id = NEW.report_id
        AND version_id = NEW.version_id AND fingerprint_hash = NEW.fingerprint_hash
        AND ruleset_id = NEW.ruleset_id AND trusted = 1 AND passed = 1
) BEGIN
    SELECT RAISE(ABORT, 'artifact report identity mismatch');
END;
CREATE TRIGGER immutable_artifact BEFORE UPDATE ON artifacts BEGIN
    SELECT RAISE(ABORT, 'immutable artifact');
END;
CREATE INDEX games_cohort ON games(mode,version_id,fingerprint_hash,ruleset_id,
    config_digest,challenge_digest,game_id);
CREATE INDEX scores_ranking ON scores(score DESC,completed_at,game_id COLLATE BINARY);
CREATE INDEX installs_cleanup ON install_reservations(state,created_at);
CREATE INDEX reports_version ON verification_reports(version_id,created_at);
CREATE UNIQUE INDEX one_active_game_per_player ON games(player_id)
    WHERE status = 'active' AND player_id IS NOT NULL;
