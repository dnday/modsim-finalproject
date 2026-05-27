-- ============================================================
-- SPKLU (EV Charging Station) database schema
-- Requires PostGIS extension for spatial queries.
-- ============================================================

CREATE EXTENSION IF NOT EXISTS postgis;

-- ----------------------------------------------------------
-- Stations table
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS stations (
    id              SERIAL PRIMARY KEY,
    station_id      VARCHAR(255) UNIQUE NOT NULL,
    station_name    VARCHAR(500) NOT NULL,
    location        GEOGRAPHY(POINT, 4326) NOT NULL,
    latitude        DOUBLE PRECISION NOT NULL,
    longitude       DOUBLE PRECISION NOT NULL,
    operator        VARCHAR(255) DEFAULT 'PLN',
    address         TEXT,
    regency         VARCHAR(100),
    province        VARCHAR(100),
    charger_category VARCHAR(50),
    max_power_kw    DOUBLE PRECISION,
    photo_url       TEXT,
    operational_hours VARCHAR(255) DEFAULT '24 jam',
    source          VARCHAR(50) NOT NULL,
    source_id       VARCHAR(255),
    raw_data        JSONB,
    created_at      TIMESTAMPTZ DEFAULT NOW(),
    updated_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------
-- Connectors table
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS connectors (
    id              SERIAL PRIMARY KEY,
    station_id      INTEGER REFERENCES stations(id) ON DELETE CASCADE,
    connector_type  VARCHAR(50),
    charger_category VARCHAR(50),
    power_kw        DOUBLE PRECISION,
    quantity         INTEGER DEFAULT 1,
    chargerbox_name VARCHAR(255),
    status          VARCHAR(50) DEFAULT 'unknown',
    created_at      TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------
-- Collection run logs
-- ----------------------------------------------------------
CREATE TABLE IF NOT EXISTS collection_logs (
    id              SERIAL PRIMARY KEY,
    source          VARCHAR(50) NOT NULL,
    region          VARCHAR(100),
    total_found     INTEGER,
    region_found    INTEGER,
    new_stations    INTEGER DEFAULT 0,
    updated_stations INTEGER DEFAULT 0,
    errors          INTEGER DEFAULT 0,
    duration_seconds DOUBLE PRECISION,
    collected_at    TIMESTAMPTZ DEFAULT NOW()
);

-- ----------------------------------------------------------
-- Indexes
-- ----------------------------------------------------------
CREATE INDEX IF NOT EXISTS idx_stations_location  ON stations USING GIST(location);
CREATE INDEX IF NOT EXISTS idx_stations_regency   ON stations(regency);
CREATE INDEX IF NOT EXISTS idx_stations_province  ON stations(province);
CREATE INDEX IF NOT EXISTS idx_stations_category  ON stations(charger_category);
CREATE INDEX IF NOT EXISTS idx_connectors_station ON connectors(station_id);
