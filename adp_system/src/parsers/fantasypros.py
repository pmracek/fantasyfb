"""
FantasyPros ADP parser
"""
import re
from typing import List
from bs4 import BeautifulSoup
import pandas as pd

from ..collectors.base import BaseParser
from ..models import PlayerADP

class FantasyProsParser(BaseParser):
    """Parser for FantasyPros ADP data"""
    
    async def parse_adp_data(self, html_content: str, scoring_format: str, **kwargs) -> List[PlayerADP]:
        """Parse FantasyPros HTML table"""
        
        soup = BeautifulSoup(html_content, 'html.parser')
        players = []
        
        # Find the main ADP table
        table = soup.find('table', {'id': 'data'})
        if not table:
            raise Exception("Could not find ADP data table")
        
        tbody = table.find('tbody')
        if not tbody:
            raise Exception("Could not find table body")
        
        rows = tbody.find_all('tr')
        
        for row in rows:
            try:
                cells = row.find_all('td')
                if len(cells) < 6:
                    continue
                
                # Extract player info (usually in format "Player Name Team - Position")
                player_cell = cells[1]  # Usually second column
                player_text = player_cell.get_text(strip=True)
                
                # Parse player name, team, and position
                player_info = self._parse_player_info(player_text)
                if not player_info:
                    continue
                
                # Extract ADP data
                overall_adp = self._extract_float(cells[2].get_text(strip=True))
                position_rank = self._extract_int(cells[3].get_text(strip=True))
                
                # Additional stats if available
                total_drafts = self._extract_int(cells[4].get_text(strip=True)) if len(cells) > 4 else None
                std_dev = self._extract_float(cells[5].get_text(strip=True)) if len(cells) > 5 else None
                
                player = PlayerADP(
                    player_name=self.clean_player_name(player_info['name']),
                    position=self.clean_position(player_info['position']),
                    team=player_info.get('team'),
                    overall_adp=overall_adp,
                    position_rank=position_rank,
                    total_drafts=total_drafts,
                    std_deviation=std_dev
                )
                
                players.append(player)
                
            except Exception as e:
                print(f"Error parsing row: {str(e)}")
                continue
        
        return players
    
    def _parse_player_info(self, text: str) -> dict:
        """Parse player name, team, and position from text"""
        
        # Common patterns:
        # "Josh Allen BUF - QB"
        # "Christian McCaffrey CAR - RB" 
        # "Tyreek Hill MIA - WR"
        
        # Pattern to match: Name [Team] - [Position]
        pattern = r'^(.+?)\s+([A-Z]{2,4})\s*-\s*([A-Z/]+)$'
        match = re.match(pattern, text.strip())
        
        if match:
            return {
                'name': match.group(1).strip(),
                'team': match.group(2).strip(),
                'position': match.group(3).strip()
            }
        
        # Fallback pattern without team
        pattern2 = r'^(.+?)\s*-\s*([A-Z/]+)$'
        match2 = re.match(pattern2, text.strip())
        
        if match2:
            return {
                'name': match2.group(1).strip(),
                'team': None,
                'position': match2.group(2).strip()
            }
        
        return None
    
    def _extract_float(self, text: str) -> float:
        """Extract float value from text"""
        try:
            # Remove non-numeric characters except decimal point
            clean_text = re.sub(r'[^\d.]', '', text)
            return float(clean_text) if clean_text else 0.0
        except:
            return 0.0
    
    def _extract_int(self, text: str) -> int:
        """Extract integer value from text"""
        try:
            # Remove non-numeric characters
            clean_text = re.sub(r'[^\d]', '', text)
            return int(clean_text) if clean_text else 0
        except:
            return 0