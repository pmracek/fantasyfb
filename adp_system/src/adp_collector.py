"""
Main ADP data collection orchestrator
"""
import asyncio
import uuid
import yaml
import logging
from datetime import datetime
from typing import List, Dict, Optional
from pathlib import Path
import pandas as pd
from pyspark.sql import SparkSession

from .models import ADPSource, CollectionResult
from .collectors.base import BaseCollector
from .parsers.fantasypros import FantasyProsParser
from .parsers.ffc import FFCParser
from .player_matcher import PlayerMatcher
from .trend_analyzer import TrendAnalyzer

logger = logging.getLogger(__name__)

class ADPCollector(BaseCollector):
    """Main ADP collection orchestrator"""
    
    def __init__(self, spark: SparkSession, config_path: Optional[str] = None):
        super().__init__()
        self.spark = spark
        self.config_path = config_path or "config/sources.yaml"
        self.sources = self._load_sources()
        self.player_matcher = PlayerMatcher(spark)
        self.trend_analyzer = TrendAnalyzer(spark)
        
        # Register parsers
        self.parsers = {
            'FantasyPros': FantasyProsParser(self.sources.get('fantasypros')),
            'Fantasy Football Calculator': FFCParser(self.sources.get('fantasyfootballcalculator')),
        }
    
    def _load_sources(self) -> Dict[str, ADPSource]:
        """Load source configurations from YAML file"""
        config_file = Path(__file__).parent.parent / self.config_path
        
        with open(config_file, 'r') as f:
            config = yaml.safe_load(f)
        
        sources = {}
        for key, source_config in config['sources'].items():
            sources[key] = ADPSource(**source_config)
        
        return sources
    
    async def collect_all_sources(self, **kwargs) -> str:
        """Collect ADP data from all configured sources"""
        
        collection_id = str(uuid.uuid4())
        collection_timestamp = datetime.utcnow()
        
        logger.info(f"Starting collection run {collection_id}")
        
        # Track collection metadata
        await self._log_collection_start(collection_id, collection_timestamp)
        
        # Create collection tasks
        tasks = []
        for source_key, source in self.sources.items():
            for scoring_format in source.endpoints.keys():
                tasks.append(
                    self.collect_source_data(
                        source=source,
                        scoring_format=scoring_format,
                        collection_id=collection_id,
                        collection_timestamp=collection_timestamp,
                        **kwargs
                    )
                )
        
        # Execute all collections concurrently
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Process results
        successful_results = []
        failed_results = []
        
        for result in results:
            if isinstance(result, CollectionResult):
                if result.success:
                    successful_results.append(result)
                else:
                    failed_results.append(result)
            else:
                logger.error(f"Unexpected result type: {type(result)}")
        
        # Save successful data
        if successful_results:
            await self._save_collection_results(successful_results)
            
            # Update player crosswalk
            await self.player_matcher.update_crosswalk(successful_results)
            
            # Calculate trends
            await self.trend_analyzer.calculate_trends()
        
        # Log collection completion
        await self._log_collection_end(
            collection_id, 
            len(tasks), 
            len(successful_results),
            sum(len(r.players) for r in successful_results),
            failed_results
        )
        
        logger.info(f"Collection run {collection_id} completed. "
                   f"Success: {len(successful_results)}/{len(tasks)} sources")
        
        return collection_id
    
    async def _save_collection_results(self, results: List[CollectionResult]):
        """Save collection results to Delta table"""
        
        # Convert results to DataFrame
        records = []
        for result in results:
            for player in result.players:
                record = {
                    'collection_id': result.collection_id,
                    'collection_date': result.collection_timestamp.date(),
                    'collection_timestamp': result.collection_timestamp,
                    'source': result.source,
                    'season': result.season,
                    'scoring_format': result.scoring_format,
                    'league_size': result.league_size,
                    'draft_type': result.draft_type,
                    'player_name': player.player_name,
                    'player_id': player.player_id,
                    'position': player.position,
                    'team': player.team,
                    'overall_adp': player.overall_adp,
                    'position_rank': player.position_rank,
                    'tier': player.tier,
                    'total_drafts': player.total_drafts,
                    'std_deviation': player.std_deviation,
                    'min_pick': player.min_pick,
                    'max_pick': player.max_pick,
                    'trend_direction': None,  # Will be calculated later
                    'trend_magnitude': None,
                    'created_at': datetime.utcnow()
                }
                records.append(record)
        
        if records:
            df = self.spark.createDataFrame(pd.DataFrame(records))
            
            # Write to Delta table with append mode
            df.write \
              .format("delta") \
              .mode("append") \
              .option("mergeSchema", "true") \
              .saveAsTable("adp_data")
            
            logger.info(f"Saved {len(records)} player records to adp_data table")
    
    async def _log_collection_start(self, collection_id: str, timestamp: datetime):
        """Log collection run start"""
        record = {
            'collection_id': collection_id,
            'start_timestamp': timestamp,
            'end_timestamp': None,
            'status': 'RUNNING',
            'sources_attempted': len(self.sources) * 3,  # Assume 3 scoring formats per source
            'sources_successful': None,
            'total_players_collected': None,
            'error_log': None
        }
        
        df = self.spark.createDataFrame(pd.DataFrame([record]))
        df.write.format("delta").mode("append").saveAsTable("collection_runs")
    
    async def _log_collection_end(
        self, 
        collection_id: str, 
        attempted: int, 
        successful: int, 
        total_players: int,
        failures: List[CollectionResult]
    ):
        """Log collection run completion"""
        
        error_messages = [f.error_message for f in failures if f.error_message]
        error_log = "; ".join(error_messages) if error_messages else None
        
        # Update the collection run record
        self.spark.sql(f"""
        MERGE INTO collection_runs cr
        USING (
          SELECT 
            '{collection_id}' as collection_id,
            current_timestamp() as end_timestamp,
            'COMPLETED' as status,
            {successful} as sources_successful,
            {total_players} as total_players_collected,
            '{error_log or ""}' as error_log
        ) updates ON cr.collection_id = updates.collection_id
        WHEN MATCHED THEN UPDATE SET
          end_timestamp = updates.end_timestamp,
          status = updates.status,
          sources_successful = updates.sources_successful,
          total_players_collected = updates.total_players_collected,
          error_log = updates.error_log
        """)
    
    async def get_latest_trends(self, scoring_format: str = 'ppr', limit: int = 50) -> pd.DataFrame:
        """Get latest trend data"""
        return self.trend_analyzer.get_latest_trends(scoring_format, limit)
    
    async def get_player_history(self, player_name: str, days: int = 30) -> pd.DataFrame:
        """Get ADP history for a specific player"""
        return self.trend_analyzer.get_player_history(player_name, days)
    
    async def close(self):
        """Cleanup resources"""
        await super().close()
        if self.player_matcher:
            await self.player_matcher.close()
        if self.trend_analyzer:
            await self.trend_analyzer.close()