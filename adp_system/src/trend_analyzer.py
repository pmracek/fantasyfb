"""
ADP trend analysis and calculation
"""
import logging
from datetime import datetime, date, timedelta
from typing import Optional
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, avg, stddev, lag, rank, desc, asc
from pyspark.sql.window import Window

logger = logging.getLogger(__name__)

class TrendAnalyzer:
    """Analyze ADP trends and calculate metrics"""
    
    def __init__(self, spark: SparkSession):
        self.spark = spark
    
    async def calculate_trends(self, target_date: Optional[date] = None) -> None:
        """Calculate trend metrics and update trends table"""
        
        if target_date is None:
            target_date = date.today()
        
        logger.info(f"Calculating trends for {target_date}")
        
        # Execute trend calculation SQL
        self.spark.sql(f"""
        INSERT INTO adp_trends
        WITH current_data AS (
          SELECT 
            pc.canonical_player_id,
            pc.canonical_name as player_name,
            ad.position,
            ad.team as nfl_team,
            ad.scoring_format,
            '{target_date}' as trend_date,
            AVG(ad.overall_adp) as current_adp,
            COUNT(*) as source_count
          FROM adp_data ad
          JOIN player_crosswalk pc ON ad.player_name = pc.source_name 
            AND ad.source = pc.source
            AND pc.is_active = true
          WHERE ad.collection_date = '{target_date}'
            AND ad.overall_adp > 0
          GROUP BY 1,2,3,4,5,6
          HAVING source_count >= 2  -- At least 2 sources for reliability
        ),
        historical_data AS (
          SELECT 
            pc.canonical_player_id,
            ad.scoring_format,
            ad.collection_date,
            AVG(ad.overall_adp) as daily_adp
          FROM adp_data ad
          JOIN player_crosswalk pc ON ad.player_name = pc.source_name 
            AND ad.source = pc.source
            AND pc.is_active = true
          WHERE ad.collection_date >= '{target_date - timedelta(days=30)}'
            AND ad.collection_date < '{target_date}'
            AND ad.overall_adp > 0
          GROUP BY 1,2,3
        ),
        trend_calcs AS (
          SELECT 
            hd.canonical_player_id,
            hd.scoring_format,
            AVG(CASE WHEN hd.collection_date >= '{target_date - timedelta(days=7)}' 
                THEN hd.daily_adp END) as adp_7d_avg,
            AVG(CASE WHEN hd.collection_date >= '{target_date - timedelta(days=14)}' 
                THEN hd.daily_adp END) as adp_14d_avg,
            AVG(CASE WHEN hd.collection_date >= '{target_date - timedelta(days=30)}' 
                THEN hd.daily_adp END) as adp_30d_avg,
            STDDEV(hd.daily_adp) as volatility_score,
            COUNT(*) as data_points
          FROM historical_data hd
          GROUP BY 1,2
          HAVING data_points >= 3  -- Need sufficient history
        )
        SELECT 
          cd.canonical_player_id,
          cd.player_name,
          cd.position,
          cd.nfl_team,
          cd.scoring_format,
          cd.trend_date,
          cd.current_adp,
          COALESCE(cd.current_adp - tc.adp_7d_avg, 0.0) as adp_7d_change,
          COALESCE(cd.current_adp - tc.adp_14d_avg, 0.0) as adp_14d_change,
          COALESCE(cd.current_adp - tc.adp_30d_avg, 0.0) as adp_30d_change,
          COALESCE(tc.volatility_score, 0.0) as volatility_score,
          -- Momentum score: weighted recent change
          COALESCE(
            (cd.current_adp - tc.adp_7d_avg) * 0.5 + 
            (cd.current_adp - tc.adp_14d_avg) * 0.3 +
            (cd.current_adp - tc.adp_30d_avg) * 0.2, 
            0.0
          ) as momentum_score,
          RANK() OVER (
            PARTITION BY cd.scoring_format, cd.position 
            ORDER BY ABS(COALESCE(cd.current_adp - tc.adp_7d_avg, 0)) DESC
          ) as opportunity_rank,
          current_timestamp() as created_at
        FROM current_data cd
        LEFT JOIN trend_calcs tc ON cd.canonical_player_id = tc.canonical_player_id 
          AND cd.scoring_format = tc.scoring_format
        """)
        
        logger.info(f"Trend calculations completed for {target_date}")
    
    def get_latest_trends(self, scoring_format: str = 'ppr', limit: int = 50) -> pd.DataFrame:
        """Get the most recent trend data"""
        
        return self.spark.sql(f"""
        SELECT 
          player_name,
          position,
          nfl_team,
          current_adp,
          adp_7d_change,
          adp_14d_change,
          adp_30d_change,
          volatility_score,
          momentum_score,
          opportunity_rank
        FROM adp_trends
        WHERE scoring_format = '{scoring_format}'
          AND trend_date = (SELECT MAX(trend_date) FROM adp_trends WHERE scoring_format = '{scoring_format}')
        ORDER BY ABS(adp_7d_change) DESC
        LIMIT {limit}
        """).toPandas()
    
    def get_biggest_risers(self, scoring_format: str = 'ppr', days: int = 7, limit: int = 20) -> pd.DataFrame:
        """Get players with biggest ADP improvements (lower numbers = better)"""
        
        change_col = f"adp_{days}d_change"
        
        return self.spark.sql(f"""
        SELECT 
          player_name,
          position,
          nfl_team,
          current_adp,
          {change_col} as adp_change,
          volatility_score,
          opportunity_rank
        FROM adp_trends
        WHERE scoring_format = '{scoring_format}'
          AND trend_date = (SELECT MAX(trend_date) FROM adp_trends WHERE scoring_format = '{scoring_format}')
          AND {change_col} < -1.0  -- Moved up at least 1 draft position
        ORDER BY {change_col} ASC
        LIMIT {limit}
        """).toPandas()
    
    def get_biggest_fallers(self, scoring_format: str = 'ppr', days: int = 7, limit: int = 20) -> pd.DataFrame:
        """Get players with biggest ADP drops (higher numbers = worse)"""
        
        change_col = f"adp_{days}d_change"
        
        return self.spark.sql(f"""
        SELECT 
          player_name,
          position,
          nfl_team,
          current_adp,
          {change_col} as adp_change,
          volatility_score,
          opportunity_rank
        FROM adp_trends
        WHERE scoring_format = '{scoring_format}'
          AND trend_date = (SELECT MAX(trend_date) FROM adp_trends WHERE scoring_format = '{scoring_format}')
          AND {change_col} > 1.0  -- Moved down at least 1 draft position
        ORDER BY {change_col} DESC
        LIMIT {limit}
        """).toPandas()
    
    def get_player_history(self, player_name: str, days: int = 30) -> pd.DataFrame:
        """Get ADP history for a specific player"""
        
        return self.spark.sql(f"""
        SELECT 
          trend_date,
          scoring_format,
          current_adp,
          adp_7d_change,
          volatility_score,
          opportunity_rank
        FROM adp_trends
        WHERE player_name = '{player_name}'
          AND trend_date >= current_date() - {days}
        ORDER BY trend_date DESC, scoring_format
        """).toPandas()
    
    def get_position_trends(self, position: str, scoring_format: str = 'ppr') -> pd.DataFrame:
        """Get trend summary for a specific position"""
        
        return self.spark.sql(f"""
        SELECT 
          player_name,
          nfl_team,
          current_adp,
          adp_7d_change,
          adp_14d_change,
          adp_30d_change,
          momentum_score,
          RANK() OVER (ORDER BY current_adp) as position_adp_rank
        FROM adp_trends
        WHERE position = '{position.upper()}'
          AND scoring_format = '{scoring_format}'
          AND trend_date = (SELECT MAX(trend_date) FROM adp_trends WHERE scoring_format = '{scoring_format}')
        ORDER BY current_adp
        """).toPandas()
    
    def get_volatile_players(self, scoring_format: str = 'ppr', min_volatility: float = 5.0, limit: int = 25) -> pd.DataFrame:
        """Get players with high ADP volatility"""
        
        return self.spark.sql(f"""
        SELECT 
          player_name,
          position,
          nfl_team,
          current_adp,
          volatility_score,
          adp_7d_change,
          adp_14d_change,
          momentum_score
        FROM adp_trends
        WHERE scoring_format = '{scoring_format}'
          AND trend_date = (SELECT MAX(trend_date) FROM adp_trends WHERE scoring_format = '{scoring_format}')
          AND volatility_score >= {min_volatility}
        ORDER BY volatility_score DESC
        LIMIT {limit}
        """).toPandas()
    
    async def close(self):
        """Cleanup resources"""
        pass