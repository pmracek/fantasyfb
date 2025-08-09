"""
Fantasy Football Calculator ADP parser
"""
import re
import json
from typing import List
from bs4 import BeautifulSoup

from ..collectors.base import BaseParser
from ..models import PlayerADP

class FFCParser(BaseParser):
    """Parser for Fantasy Football Calculator ADP data"""
    
    async def parse_adp_data(self, html_content: str, scoring_format: str, **kwargs) -> List[PlayerADP]:
        """Parse FFC HTML or JSON data"""
        
        players = []
        
        # Try JSON first (FFC sometimes provides JSON endpoints)
        if self._is_json(html_content):
            return await self._parse_json_data(html_content)
        
        # Parse HTML table
        soup = BeautifulSoup(html_content, 'html.parser')
        
        # Look for the ADP table
        table = soup.find('table', class_='adp-table') or soup.find('table', {'id': 'adp-data'})
        if not table:
            # Try generic table search
            tables = soup.find_all('table')
            for t in tables:
                if 'ADP' in str(t) or 'adp' in str(t):
                    table = t
                    break
        
        if not table:
            raise Exception("Could not find ADP data table")
        
        tbody = table.find('tbody') or table
        rows = tbody.find_all('tr')
        
        for row in rows:
            try:
                cells = row.find_all(['td', 'th'])
                if len(cells) < 4:
                    continue
                
                # Skip header row
                if cells[0].name == 'th':
                    continue
                
                # Extract data (FFC format varies)
                rank_cell = cells[0].get_text(strip=True)
                if not rank_cell.isdigit():
                    continue
                
                player_cell = cells[1]
                player_text = player_cell.get_text(strip=True)
                
                # Parse player info
                player_info = self._parse_player_info(player_text)
                if not player_info:
                    continue
                
                # Extract ADP
                adp_text = cells[2].get_text(strip=True)
                overall_adp = self._extract_float(adp_text)
                
                # Extract additional data if available
                times_drafted = self._extract_int(cells[3].get_text(strip=True)) if len(cells) > 3 else None
                
                player = PlayerADP(
                    player_name=self.clean_player_name(player_info['name']),
                    position=self.clean_position(player_info['position']),
                    team=player_info.get('team'),
                    overall_adp=overall_adp,
                    total_drafts=times_drafted
                )
                
                players.append(player)
                
            except Exception as e:
                print(f"Error parsing FFC row: {str(e)}")
                continue
        
        return players
    
    async def _parse_json_data(self, json_content: str) -> List[PlayerADP]:
        """Parse JSON format ADP data"""
        try:
            data = json.loads(json_content)
            players = []
            
            # Handle different JSON structures
            if isinstance(data, list):
                player_list = data
            elif 'players' in data:
                player_list = data['players']
            elif 'data' in data:
                player_list = data['data']
            else:
                return players
            
            for item in player_list:
                try:
                    player = PlayerADP(
                        player_name=self.clean_player_name(item.get('name', '')),
                        position=self.clean_position(item.get('position', '')),
                        team=item.get('team'),
                        overall_adp=float(item.get('adp', 0)),
                        position_rank=int(item.get('position_rank', 0)) if item.get('position_rank') else None,
                        total_drafts=int(item.get('times_drafted', 0)) if item.get('times_drafted') else None
                    )
                    players.append(player)
                except Exception as e:
                    print(f"Error parsing JSON player: {str(e)}")
                    continue
            
            return players
            
        except json.JSONDecodeError:
            raise Exception("Invalid JSON data")
    
    def _is_json(self, content: str) -> bool:
        """Check if content is JSON"""
        try:
            json.loads(content)
            return True
        except:
            return False
    
    def _parse_player_info(self, text: str) -> dict:
        """Parse player name, team, and position from FFC format"""
        
        # FFC formats vary:
        # "Josh Allen (QB - BUF)"
        # "Christian McCaffrey RB, CAR"
        # "Tyreek Hill, WR, MIA"
        
        # Pattern 1: Name (Position - Team)
        pattern1 = r'^(.+?)\s*\(([A-Z/]+)\s*-\s*([A-Z]{2,4})\)$'
        match1 = re.match(pattern1, text.strip())
        
        if match1:
            return {
                'name': match1.group(1).strip(),
                'position': match1.group(2).strip(),
                'team': match1.group(3).strip()
            }
        
        # Pattern 2: Name Position, Team
        pattern2 = r'^(.+?)\s+([A-Z/]+),\s*([A-Z]{2,4})$'
        match2 = re.match(pattern2, text.strip())
        
        if match2:
            return {
                'name': match2.group(1).strip(),
                'position': match2.group(2).strip(),
                'team': match2.group(3).strip()
            }
        
        # Pattern 3: Name, Position, Team
        parts = [p.strip() for p in text.split(',')]
        if len(parts) >= 3:
            return {
                'name': parts[0],
                'position': parts[1],
                'team': parts[2]
            }
        
        return None
    
    def _extract_float(self, text: str) -> float:
        """Extract float value from text"""
        try:
            clean_text = re.sub(r'[^\d.]', '', text)
            return float(clean_text) if clean_text else 0.0
        except:
            return 0.0
    
    def _extract_int(self, text: str) -> int:
        """Extract integer value from text"""
        try:
            clean_text = re.sub(r'[^\d]', '', text)
            return int(clean_text) if clean_text else 0
        except:
            return 0