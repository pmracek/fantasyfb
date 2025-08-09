-- Example queries for ADP analysis

-- 1. Find biggest ADP risers in the last 7 days (lower ADP = better draft position)
SELECT 
  player_name,
  position,
  nfl_team,
  current_adp,
  adp_7d_change,
  volatility_score,
  opportunity_rank
FROM adp_trends
WHERE scoring_format = 'ppr'
  AND trend_date = current_date()
  AND adp_7d_change < -2.0  -- Moved up at least 2 draft positions
ORDER BY adp_7d_change ASC
LIMIT 20;

-- 2. Find biggest ADP fallers in the last 7 days
SELECT 
  player_name,
  position,
  nfl_team,
  current_adp,
  adp_7d_change,
  volatility_score
FROM adp_trends
WHERE scoring_format = 'ppr'
  AND trend_date = current_date()
  AND adp_7d_change > 2.0  -- Moved down at least 2 draft positions
ORDER BY adp_7d_change DESC
LIMIT 20;

-- 3. Most volatile players (high ADP variance)
SELECT 
  player_name,
  position,
  current_adp,
  volatility_score,
  adp_7d_change,
  adp_30d_change
FROM adp_trends
WHERE scoring_format = 'ppr'
  AND trend_date = current_date()
  AND volatility_score > 5.0
ORDER BY volatility_score DESC
LIMIT 25;

-- 4. Position-based trend analysis
SELECT 
  position,
  COUNT(*) as player_count,
  AVG(current_adp) as avg_adp,
  AVG(adp_7d_change) as avg_7d_change,
  AVG(ABS(adp_7d_change)) as avg_abs_change,
  MAX(volatility_score) as max_volatility
FROM adp_trends
WHERE scoring_format = 'ppr'
  AND trend_date = current_date()
GROUP BY position
ORDER BY avg_adp;

-- 5. Top opportunities by position (biggest movers in each position)
WITH position_ranks AS (
  SELECT 
    *,
    ROW_NUMBER() OVER (
      PARTITION BY position 
      ORDER BY ABS(adp_7d_change) DESC
    ) as position_movement_rank
  FROM adp_trends
  WHERE scoring_format = 'ppr'
    AND trend_date = current_date()
)
SELECT 
  position,
  player_name,
  nfl_team,
  current_adp,
  adp_7d_change,
  CASE WHEN adp_7d_change < 0 THEN 'RISER' ELSE 'FALLER' END as trend_direction
FROM position_ranks
WHERE position_movement_rank <= 3
ORDER BY position, ABS(adp_7d_change) DESC;

-- 6. Player ADP history over time
SELECT 
  trend_date,
  player_name,
  scoring_format,
  current_adp,
  adp_7d_change,
  volatility_score
FROM adp_trends
WHERE player_name = 'Christian McCaffrey'
  AND trend_date >= current_date() - 30
ORDER BY trend_date DESC, scoring_format;

-- 7. Early round vs late round volatility comparison
SELECT 
  CASE 
    WHEN current_adp <= 36 THEN 'Early (Rounds 1-3)'
    WHEN current_adp <= 84 THEN 'Middle (Rounds 4-7)'  
    ELSE 'Late (Rounds 8+)'
  END as draft_tier,
  COUNT(*) as player_count,
  AVG(volatility_score) as avg_volatility,
  AVG(ABS(adp_7d_change)) as avg_movement,
  MAX(ABS(adp_7d_change)) as max_movement
FROM adp_trends
WHERE scoring_format = 'ppr'
  AND trend_date = current_date()
  AND current_adp <= 200  -- First ~17 rounds in 12-team
GROUP BY 1
ORDER BY 1;

-- 8. Cross-format ADP comparison (PPR vs Standard)
SELECT 
  pc.canonical_name as player_name,
  ppr.current_adp as ppr_adp,
  std.current_adp as standard_adp,
  ppr.current_adp - std.current_adp as format_difference,
  ppr.position
FROM adp_trends ppr
JOIN adp_trends std ON ppr.canonical_player_id = std.canonical_player_id
  AND ppr.trend_date = std.trend_date
JOIN player_crosswalk pc ON ppr.canonical_player_id = pc.canonical_player_id
WHERE ppr.scoring_format = 'ppr'
  AND std.scoring_format = 'standard'  
  AND ppr.trend_date = current_date()
  AND pc.is_active = true
ORDER BY ABS(format_difference) DESC
LIMIT 30;

-- 9. Data quality check - collection success rates
SELECT 
  collection_date,
  COUNT(*) as total_collections,
  SUM(CASE WHEN status = 'COMPLETED' THEN 1 ELSE 0 END) as successful_collections,
  AVG(sources_successful::FLOAT / sources_attempted) as success_rate,
  AVG(total_players_collected) as avg_players_collected
FROM collection_runs
WHERE collection_date >= current_date() - 7
GROUP BY collection_date
ORDER BY collection_date DESC;

-- 10. Identify potential sleepers (low ADP, rising trend)
SELECT 
  player_name,
  position,
  nfl_team,
  current_adp,
  adp_7d_change,
  adp_14d_change,
  momentum_score
FROM adp_trends
WHERE scoring_format = 'ppr'
  AND trend_date = current_date()
  AND current_adp > 100  -- Later round picks
  AND adp_7d_change < -3  -- Rising significantly
  AND momentum_score < -2  -- Strong upward momentum
ORDER BY momentum_score ASC
LIMIT 15;