CREATE TABLE IF NOT EXISTS experiments (
    name        VARCHAR(50) PRIMARY KEY,
    variants    JSONB NOT NULL,
    is_active   BOOLEAN NOT NULL DEFAULT true,
    created_at  TIMESTAMPTZ DEFAULT now()
);
