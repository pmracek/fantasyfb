-- Create ADP data collection database and tables

-- Core ADP data table
CREATE TABLE IF NOT EXISTS adp_data (
  collection_id STRING,
  collection_date DATE,
  collection_timestamp TIMESTAMP,
  source STRING,
  season INTEGER,
  scoring_format STRING,
  league_size INTEGER,
  draft_type STRING,
  player_name STRING,
  player_id STRING,
  position STRING,
  team STRING,
  overall_adp DOUBLE,
  position_rank INTEGER,
  tier INTEGER,
  total_drafts INTEGER,
  std_deviation DOUBLE,
  min_pick INTEGER,
  max_pick INTEGER,
  trend_direction STRING,
  trend_magnitude DOUBLE,
  created_at TIMESTAMP
) 
USING DELTA
PARTITIONED BY (collection_date, source, scoring_format)
LOCATION 's3://your-bucket/adp_data/';

-- Player name standardization crosswalk table
CREATE TABLE IF NOT EXISTS player_crosswalk (
  canonical_player_id STRING,
  canonical_name STRING,
  position STRING,
  nfl_team STRING,
  source STRING,
  source_player_id STRING,
  source_name STRING,
  confidence_score DOUBLE,
  is_active BOOLEAN,
  created_at TIMESTAMP,
  updated_at TIMESTAMP,
  PRIMARY KEY (canonical_player_id, source)
)
USING DELTA
LOCATION 's3://your-bucket/player_crosswalk/';

-- ADP trends and analytics table  
CREATE TABLE IF NOT EXISTS adp_trends (
  canonical_player_id STRING,
  player_name STRING,
  position STRING,
  nfl_team STRING,
  scoring_format STRING,
  trend_date DATE,
  current_adp DOUBLE,
  adp_7d_change DOUBLE,
  adp_14d_change DOUBLE,
  adp_30d_change DOUBLE,
  volatility_score DOUBLE,
  momentum_score DOUBLE,
  opportunity_rank INTEGER,
  created_at TIMESTAMP
)
USING DELTA
PARTITIONED BY (trend_date, scoring_format)
LOCATION 's3://your-bucket/adp_trends/';

-- Collection run metadata
CREATE TABLE IF NOT EXISTS collection_runs (
  collection_id STRING,
  start_timestamp TIMESTAMP,
  end_timestamp TIMESTAMP,
  status STRING,
  sources_attempted INTEGER,
  sources_successful INTEGER,
  total_players_collected INTEGER,
  error_log STRING,
  PRIMARY KEY (collection_id)
)
USING DELTA
LOCATION 's3://your-bucket/collection_runs/';

-- Create indexes for better query performance
CREATE INDEX IF NOT EXISTS idx_adp_data_player_date 
ON adp_data (player_name, collection_date);

CREATE INDEX IF NOT EXISTS idx_crosswalk_canonical 
ON player_crosswalk (canonical_player_id);

CREATE INDEX IF NOT EXISTS idx_trends_player_date 
ON adp_trends (canonical_player_id, trend_date);