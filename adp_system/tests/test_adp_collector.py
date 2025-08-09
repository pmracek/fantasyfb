"""
Test cases for ADP collection system
"""
import pytest
import asyncio
from unittest.mock import Mock, patch
from datetime import datetime

import sys
from pathlib import Path
sys.path.append(str(Path(__file__).parent.parent / "src"))

from src.adp_collector import ADPCollector
from src.models import ADPSource, PlayerADP, CollectionResult

class TestADPCollector:
    
    @pytest.fixture
    def mock_spark(self):
        """Mock Spark session"""
        spark = Mock()
        spark.createDataFrame.return_value = Mock()
        spark.sql.return_value = Mock()
        return spark
    
    @pytest.fixture
    def sample_source(self):
        """Sample ADP source for testing"""
        return ADPSource(
            name="TestSource",
            base_url="https://test.com",
            endpoints={"ppr": "/adp/ppr"},
            parser_class="TestParser",
            rate_limit_delay=0.1
        )
    
    @pytest.fixture
    def sample_players(self):
        """Sample player data"""
        return [
            PlayerADP(
                player_name="Christian McCaffrey",
                position="RB",
                team="CAR",
                overall_adp=1.5,
                position_rank=1
            ),
            PlayerADP(
                player_name="Austin Ekeler",
                position="RB", 
                team="LAC",
                overall_adp=3.2,
                position_rank=2
            )
        ]
    
    @pytest.mark.asyncio
    async def test_collection_success(self, mock_spark, sample_source, sample_players):
        """Test successful data collection"""
        
        collector = ADPCollector(mock_spark)
        
        # Mock the parser
        mock_parser = Mock()
        mock_parser.parse_adp_data.return_value = sample_players
        collector.parsers["TestSource"] = mock_parser
        
        # Mock HTTP response
        with patch.object(collector, '_fetch_url') as mock_fetch:
            mock_fetch.return_value = "<html>test data</html>"
            
            result = await collector.collect_source_data(
                source=sample_source,
                scoring_format="ppr",
                collection_id="test-123",
                collection_timestamp=datetime.utcnow(),
                season=2024
            )
        
        assert result.success is True
        assert len(result.players) == 2
        assert result.source == "TestSource"
        assert result.scoring_format == "ppr"
    
    @pytest.mark.asyncio
    async def test_collection_failure(self, mock_spark, sample_source):
        """Test collection failure handling"""
        
        collector = ADPCollector(mock_spark)
        
        # Mock HTTP failure
        with patch.object(collector, '_fetch_url') as mock_fetch:
            mock_fetch.side_effect = Exception("HTTP Error")
            
            result = await collector.collect_source_data(
                source=sample_source,
                scoring_format="ppr", 
                collection_id="test-123",
                collection_timestamp=datetime.utcnow(),
                season=2024
            )
        
        assert result.success is False
        assert result.error_message == "HTTP Error"
        assert len(result.players) == 0
    
    @pytest.mark.asyncio
    async def test_rate_limiting(self, mock_spark, sample_source, sample_players):
        """Test that rate limiting is applied"""
        
        collector = ADPCollector(mock_spark)
        
        mock_parser = Mock()
        mock_parser.parse_adp_data.return_value = sample_players
        collector.parsers["TestSource"] = mock_parser
        
        with patch.object(collector, '_fetch_url') as mock_fetch:
            mock_fetch.return_value = "<html>test</html>"
            
            with patch('asyncio.sleep') as mock_sleep:
                await collector.collect_source_data(
                    source=sample_source,
                    scoring_format="ppr",
                    collection_id="test-123", 
                    collection_timestamp=datetime.utcnow()
                )
                
                # Verify sleep was called with rate limit delay
                mock_sleep.assert_called_once_with(0.1)

class TestPlayerMatching:
    
    def test_name_normalization(self):
        """Test player name normalization"""
        from src.player_matcher import PlayerMatcher
        
        mock_spark = Mock()
        matcher = PlayerMatcher(mock_spark)
        
        # Test basic normalization
        assert matcher._normalize_name("christian mccaffrey") == "Christian Mccaffrey"
        assert matcher._normalize_name("  D.J. Moore  ") == "D.J. Moore"
        
        # Test apostrophe standardization
        assert matcher._normalize_name("D'Andre Swift") == "D'Andre Swift"
    
    def test_confidence_calculation(self):
        """Test name matching confidence scoring"""
        from src.player_matcher import PlayerMatcher
        
        mock_spark = Mock()
        matcher = PlayerMatcher(mock_spark)
        
        # Perfect match
        assert matcher._calculate_name_confidence("Josh Allen", "Josh Allen") == 1.0
        
        # Partial match
        confidence = matcher._calculate_name_confidence("J. Allen", "Josh Allen")
        assert 0 < confidence < 1

class TestTrendAnalysis:
    
    def test_trend_calculation_sql(self):
        """Test that trend calculation SQL is valid"""
        from src.trend_analyzer import TrendAnalyzer
        
        mock_spark = Mock()
        analyzer = TrendAnalyzer(mock_spark)
        
        # Mock the SQL execution
        mock_spark.sql.return_value = None
        
        # This should not raise an exception
        asyncio.run(analyzer.calculate_trends())
        
        # Verify SQL was called
        mock_spark.sql.assert_called()

if __name__ == "__main__":
    # Run tests
    pytest.main([__file__])