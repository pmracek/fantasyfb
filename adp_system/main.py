"""
Main entry point for ADP collection system
"""
import asyncio
import logging
import sys
from pathlib import Path
from pyspark.sql import SparkSession
from datetime import datetime

# Add src to path for imports
sys.path.append(str(Path(__file__).parent / "src"))

from src.adp_collector import ADPCollector

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

def create_spark_session() -> SparkSession:
    """Create Spark session with Delta Lake support"""
    return SparkSession.builder \
        .appName("ADP_Data_Collection") \
        .config("spark.sql.extensions", "io.delta.sql.DeltaSparkSessionExtension") \
        .config("spark.sql.catalog.spark_catalog", "org.apache.spark.sql.delta.catalog.DeltaCatalog") \
        .config("spark.sql.adaptive.enabled", "true") \
        .config("spark.sql.adaptive.coalescePartitions.enabled", "true") \
        .getOrCreate()

async def run_collection():
    """Run a single ADP data collection cycle"""
    
    logger.info("Starting ADP data collection")
    
    # Create Spark session
    spark = create_spark_session()
    
    try:
        # Initialize collector
        collector = ADPCollector(spark)
        
        # Run collection
        collection_id = await collector.collect_all_sources(
            season=2024,
            league_size=12,
            draft_type='redraft'
        )
        
        logger.info(f"Collection completed with ID: {collection_id}")
        
        # Show some trend data
        trends = await collector.get_latest_trends(scoring_format='ppr', limit=10)
        print("\nTop 10 ADP Changes (7-day):")
        print(trends[['player_name', 'position', 'current_adp', 'adp_7d_change']].to_string(index=False))
        
        # Show risers and fallers
        risers = collector.trend_analyzer.get_biggest_risers(scoring_format='ppr', days=7, limit=5)
        fallers = collector.trend_analyzer.get_biggest_fallers(scoring_format='ppr', days=7, limit=5)
        
        print("\nBiggest Risers (7-day):")
        print(risers[['player_name', 'position', 'current_adp', 'adp_change']].to_string(index=False))
        
        print("\nBiggest Fallers (7-day):")
        print(fallers[['player_name', 'position', 'current_adp', 'adp_change']].to_string(index=False))
        
        await collector.close()
        
    except Exception as e:
        logger.error(f"Collection failed: {str(e)}")
        raise
    finally:
        spark.stop()

async def run_trend_analysis_only():
    """Run just the trend analysis on existing data"""
    
    logger.info("Running trend analysis")
    
    spark = create_spark_session()
    
    try:
        from src.trend_analyzer import TrendAnalyzer
        
        analyzer = TrendAnalyzer(spark)
        await analyzer.calculate_trends()
        
        # Show results
        trends = analyzer.get_latest_trends(scoring_format='ppr', limit=20)
        print("\nLatest ADP Trends:")
        print(trends.to_string(index=False))
        
    except Exception as e:
        logger.error(f"Trend analysis failed: {str(e)}")
        raise
    finally:
        spark.stop()

async def show_player_history(player_name: str):
    """Show ADP history for a specific player"""
    
    spark = create_spark_session()
    
    try:
        from src.trend_analyzer import TrendAnalyzer
        
        analyzer = TrendAnalyzer(spark)
        history = analyzer.get_player_history(player_name, days=30)
        
        print(f"\nADP History for {player_name} (Last 30 days):")
        print(history.to_string(index=False))
        
    except Exception as e:
        logger.error(f"Failed to get player history: {str(e)}")
        raise
    finally:
        spark.stop()

def main():
    """Main CLI interface"""
    
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python main.py collect          - Run full data collection")
        print("  python main.py trends           - Run trend analysis only")
        print("  python main.py player <name>    - Show player history")
        return
    
    command = sys.argv[1].lower()
    
    if command == "collect":
        asyncio.run(run_collection())
    elif command == "trends":
        asyncio.run(run_trend_analysis_only())
    elif command == "player" and len(sys.argv) > 2:
        player_name = " ".join(sys.argv[2:])
        asyncio.run(show_player_history(player_name))
    else:
        print("Invalid command. Use 'collect', 'trends', or 'player <name>'")

if __name__ == "__main__":
    main()