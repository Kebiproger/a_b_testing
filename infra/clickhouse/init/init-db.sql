CREATE TABLE IF NOT EXISTS tracking_events (
    timestamp DateTime64(3, 'UTC'),
    user_id String,
    event_name String,
    experiment_name Nullable(String),
    variant Nullable(String),
    event_data String
) ENGINE = MergeTree()
ORDER BY (event_name, toDate(timestamp), user_id);
