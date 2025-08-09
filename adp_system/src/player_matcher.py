"""
Player name matching and crosswalk management
"""
import uuid
import logging
from typing import List, Dict, Set
from datetime import datetime
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, lower, regexp_replace, trim

from .models import CollectionResult, PlayerCrosswalk

logger = logging.getLogger(__name__)

class PlayerMatcher:
    """Handles player name standardization and crosswalk management"""
    
    def __init__(self, spark: SparkSession):
        self.spark = spark
        self.name_variations = self._load_common_name_variations()
    
    def _load_common_name_variations(self) -> Dict[str, Set[str]]:
        """Load common name variations and nicknames"""
        return {
            # Common name variations - could be loaded from a file
            'T.J. Hockenson': {'TJ Hockenson', 'T.J. Hockenson', 'T J Hockenson'},
            'D.J. Moore': {'DJ Moore', 'D.J. Moore', 'D J Moore'},
            'A.J. Brown': {'AJ Brown', 'A.J. Brown', 'A J Brown'},
            'D.K. Metcalf': {'DK Metcalf', 'D.K. Metcalf', 'D K Metcalf'},
            'J.K. Dobbins': {'JK Dobbins', 'J.K. Dobbins', 'J K Dobbins'},
            # Add more as needed...
        }
    
    async def update_crosswalk(self, results: List[CollectionResult]) -> None:
        """Update player crosswalk table with new collection data"""
        
        logger.info("Updating player crosswalk table")
        
        # Extract all unique players from results
        all_players = []
        for result in results:
            for player in result.players:
                all_players.append({
                    'source': result.source,
                    'source_name': player.player_name,
                    'source_player_id': player.player_id,
                    'position': player.position,
                    'team': player.team
                })
        
        if not all_players:
            return
        
        players_df = pd.DataFrame(all_players)
        
        # Get existing crosswalk data
        existing_crosswalk = self._get_existing_crosswalk()
        
        # Find new players not in crosswalk
        new_players = self._find_new_players(players_df, existing_crosswalk)
        
        if not new_players.empty:
            # Generate canonical IDs and names for new players
            crosswalk_records = self._create_crosswalk_records(new_players)
            
            # Save new crosswalk records
            await self._save_crosswalk_records(crosswalk_records)
            
            logger.info(f"Added {len(crosswalk_records)} new player crosswalk records")
    
    def _get_existing_crosswalk(self) -> pd.DataFrame:
        """Get existing crosswalk data"""
        try:
            return self.spark.table("player_crosswalk").toPandas()
        except:
            # Table doesn't exist yet
            return pd.DataFrame(columns=['source', 'source_name', 'canonical_player_id'])
    
    def _find_new_players(self, players_df: pd.DataFrame, existing_crosswalk: pd.DataFrame) -> pd.DataFrame:
        """Find players not in existing crosswalk"""
        if existing_crosswalk.empty:
            return players_df.drop_duplicates(['source', 'source_name'])
        
        # Merge to find new combinations
        merged = players_df.merge(
            existing_crosswalk[['source', 'source_name']], 
            on=['source', 'source_name'], 
            how='left', 
            indicator=True
        )
        
        new_players = merged[merged['_merge'] == 'left_only'].drop('_merge', axis=1)
        return new_players.drop_duplicates(['source', 'source_name'])
    
    def _create_crosswalk_records(self, new_players: pd.DataFrame) -> List[PlayerCrosswalk]:
        """Create crosswalk records for new players"""
        records = []
        canonical_map = {}  # Track canonical names to avoid duplicates
        
        for _, player in new_players.iterrows():
            source_name = player['source_name']
            normalized_name = self._normalize_name(source_name)
            
            # Check if we already have a canonical ID for this normalized name
            canonical_id = canonical_map.get(normalized_name)
            if canonical_id is None:
                canonical_id = str(uuid.uuid4())
                canonical_map[normalized_name] = canonical_id
            
            # Calculate confidence score
            confidence = self._calculate_name_confidence(source_name, normalized_name)
            
            record = PlayerCrosswalk(
                canonical_player_id=canonical_id,
                canonical_name=normalized_name,
                position=player['position'],
                nfl_team=player.get('team'),
                source=player['source'],
                source_player_id=player.get('source_player_id'),
                source_name=source_name,
                confidence_score=confidence,
                is_active=True
            )
            records.append(record)
        
        return records
    
    def _normalize_name(self, name: str) -> str:
        """Normalize player name to canonical format"""
        if not name:
            return ""
        
        # Basic normalization
        normalized = name.strip().title()
        
        # Handle common patterns
        normalized = normalized.replace("'", "'")  # Standardize apostrophes
        
        # Check for known variations
        for canonical, variations in self.name_variations.items():
            if normalized in variations:
                return canonical
        
        # Remove extra spaces
        normalized = " ".join(normalized.split())
        
        return normalized
    
    def _calculate_name_confidence(self, source_name: str, canonical_name: str) -> float:
        """Calculate confidence score for name matching"""
        if source_name == canonical_name:
            return 1.0
        
        # Simple similarity based on character overlap
        source_chars = set(source_name.lower().replace(" ", ""))
        canonical_chars = set(canonical_name.lower().replace(" ", ""))
        
        if not source_chars or not canonical_chars:
            return 0.0
        
        overlap = len(source_chars.intersection(canonical_chars))
        union = len(source_chars.union(canonical_chars))
        
        return overlap / union if union > 0 else 0.0
    
    async def _save_crosswalk_records(self, records: List[PlayerCrosswalk]) -> None:
        """Save crosswalk records to database"""
        
        # Convert to DataFrame
        data = []
        for record in records:
            data.append({
                'canonical_player_id': record.canonical_player_id,
                'canonical_name': record.canonical_name,
                'position': record.position,
                'nfl_team': record.nfl_team,
                'source': record.source,
                'source_player_id': record.source_player_id,
                'source_name': record.source_name,
                'confidence_score': record.confidence_score,
                'is_active': record.is_active,
                'created_at': datetime.utcnow(),
                'updated_at': datetime.utcnow()
            })
        
        if data:
            df = self.spark.createDataFrame(pd.DataFrame(data))
            
            # Write to Delta table
            df.write \
              .format("delta") \
              .mode("append") \
              .option("mergeSchema", "true") \
              .saveAsTable("player_crosswalk")
    
    def get_canonical_name(self, source_name: str, source: str) -> str:
        """Get canonical name for a source-specific player name"""
        try:
            result = self.spark.sql(f"""
            SELECT canonical_name 
            FROM player_crosswalk 
            WHERE source_name = '{source_name}' 
              AND source = '{source}' 
              AND is_active = true
            LIMIT 1
            """).collect()
            
            if result:
                return result[0]['canonical_name']
            else:
                return self._normalize_name(source_name)
        except:
            return self._normalize_name(source_name)
    
    def find_similar_players(self, player_name: str, threshold: float = 0.8) -> pd.DataFrame:
        """Find similar player names in crosswalk"""
        # This would use more sophisticated matching in production
        # For now, just return exact matches
        return self.spark.sql(f"""
        SELECT canonical_name, source_name, source, confidence_score
        FROM player_crosswalk
        WHERE canonical_name LIKE '%{player_name}%' 
           OR source_name LIKE '%{player_name}%'
        ORDER BY confidence_score DESC
        """).toPandas()
    
    async def close(self):
        """Cleanup resources"""
        pass