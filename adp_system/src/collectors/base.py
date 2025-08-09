"""
Base classes for ADP data collection
"""
import asyncio
import aiohttp
import logging
from abc import ABC, abstractmethod
from typing import List, Dict, Optional
from datetime import datetime
import pandas as pd

from ..models import ADPSource, PlayerADP, CollectionResult

logger = logging.getLogger(__name__)

class BaseParser(ABC):
    """Abstract base class for source-specific parsers"""
    
    def __init__(self, source: ADPSource):
        self.source = source
    
    @abstractmethod
    async def parse_adp_data(self, html_content: str, scoring_format: str, **kwargs) -> List[PlayerADP]:
        """Parse HTML content and extract ADP data"""
        pass
    
    def clean_player_name(self, name: str) -> str:
        """Standardize player name format"""
        # Remove common suffixes and normalize spacing
        name = name.strip()
        suffixes = [' Jr.', ' Sr.', ' III', ' II', ' IV']
        for suffix in suffixes:
            name = name.replace(suffix, '')
        return name.title()
    
    def clean_position(self, position: str) -> str:
        """Standardize position format"""
        position = position.strip().upper()
        # Handle combined positions
        if '/' in position:
            position = position.split('/')[0]
        return position

class BaseCollector:
    """Base collector class with common functionality"""
    
    def __init__(self, session: Optional[aiohttp.ClientSession] = None):
        self.session = session
        self.parsers: Dict[str, BaseParser] = {}
    
    async def _get_session(self) -> aiohttp.ClientSession:
        """Get or create aiohttp session"""
        if self.session is None:
            timeout = aiohttp.ClientTimeout(total=30)
            self.session = aiohttp.ClientSession(timeout=timeout)
        return self.session
    
    async def _fetch_url(self, url: str, headers: Optional[Dict[str, str]] = None) -> str:
        """Fetch URL content with error handling"""
        session = await self._get_session()
        
        try:
            async with session.get(url, headers=headers) as response:
                if response.status == 200:
                    return await response.text()
                else:
                    logger.error(f"HTTP {response.status} for {url}")
                    raise Exception(f"HTTP {response.status} for {url}")
        except Exception as e:
            logger.error(f"Error fetching {url}: {str(e)}")
            raise
    
    async def collect_source_data(
        self, 
        source: ADPSource, 
        scoring_format: str,
        collection_id: str,
        collection_timestamp: datetime,
        **kwargs
    ) -> CollectionResult:
        """Collect data from a single source"""
        
        try:
            # Get parser for this source
            parser = self.parsers.get(source.name)
            if not parser:
                raise Exception(f"No parser found for source: {source.name}")
            
            # Build URL
            endpoint = source.endpoints.get(scoring_format)
            if not endpoint:
                raise Exception(f"No endpoint for {scoring_format} in {source.name}")
            
            url = source.base_url + endpoint
            
            # Fetch data
            headers = source.headers or {}
            html_content = await self._fetch_url(url, headers)
            
            # Parse data
            players = await parser.parse_adp_data(
                html_content, scoring_format, **kwargs
            )
            
            # Rate limiting
            if source.rate_limit_delay > 0:
                await asyncio.sleep(source.rate_limit_delay)
            
            result = CollectionResult(
                collection_id=collection_id,
                collection_timestamp=collection_timestamp,
                source=source.name,
                season=kwargs.get('season', 2024),
                scoring_format=scoring_format,
                league_size=kwargs.get('league_size', 12),
                draft_type=kwargs.get('draft_type', 'redraft'),
                players=players,
                success=True
            )
            
            logger.info(f"Successfully collected {len(players)} players from {source.name} ({scoring_format})")
            return result
            
        except Exception as e:
            logger.error(f"Error collecting from {source.name} ({scoring_format}): {str(e)}")
            return CollectionResult(
                collection_id=collection_id,
                collection_timestamp=collection_timestamp,
                source=source.name,
                season=kwargs.get('season', 2024),
                scoring_format=scoring_format,
                league_size=kwargs.get('league_size', 12),
                draft_type=kwargs.get('draft_type', 'redraft'),
                players=[],
                success=False,
                error_message=str(e)
            )
    
    async def close(self):
        """Close aiohttp session"""
        if self.session:
            await self.session.close()