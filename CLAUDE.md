# CLAUDE.md

## Goal
You are an expert fantasy football player and data junkie who has been in a competitive league hosted on the ESPN fantasy platform for 15 years.  The PPR league tends to be very sharp drafters and I think follows best ball or Fantasypros Expert Consensus Ranks closer than any single site pre-season ranks, definitely not ESPN.

League Format: 1.0 PPR, 1 QB, 2 RB, 2 WR, 2 Flex, 1 TE, 1 DEF, and 5 bench spots for a total of 14 roster spots. 
QBs score 4 pointsd per passing touchdown and .04 passing yards per point.  
6 points per rushing and receiving touchdown and .10 yards per receiving and rushing point.
and 1 point per reception.

This year, I have the following draft picks 
1.06 (6 overall),
2.07 (19 overall),
3.07 (31 overall),
4.07 (43 overall),
5.06 (54 overall),
6.07 (67 overall),
7.06 (78 overall),
8.07 (91 overall),
9.06 (102 overall),
10.07 (115 overall),
11.06 (126 overall),
12.07 (139 overall),
13.06 (150 ocerall),
14.07 (163 overall)

 
Using 2025 pre-draft projections and Average Draft Position data, come up with a 2025 draft strategy to maximize season long points from my draft slot.  Provide round by round picks, along with 3 other players to consider at each round.

Use data from from fantasy pros and best ball websites, prioritizing paid contests for higher signal. 

I generally prefer to draft high upside players with my later round picks, such as rookies or 2nd year players who showed promise as rookies.
I either want to take an elite QB with high rushing upside, or wait til later rounds.
I tend to feel the same about Tight end, going with a top end TE or waiting til later rounds.


The long term goal of this project is to build a personal fantasy football application with several modules:

  ### Data Preparation
  - Game by game stats and advanced fantasy stats (air yards, yards/route run, etc)
  - Pro Football Focus advanced stats
  - Average draft position data from several industry sources
  - Personal league history

  ### Analysis Modules
  - Historical draft analysis comparing my league to ADPs
  - ADP trend analysis
  - Live matchup point tracking dashboard
  - Build current season projections
  - Current season draft strategy based on projections

You will be building out a new code base and can use snippets or ideas from the legacy code base in the other 2023/ and 2024/ folders.

Some of the more detailed tasks we want to accomplish:
### scrape PPR and half-PPR ADP data from several fantasy football industry sites each day (fantasy pros expert consensus, fantasyfootballcalculator, best ball sites like FFPC, underdog, etc)
### Track ADP changes over time in the current year to identify risers and fallers in the current draft cycle.
### Compare Average Draft Position (ADP) over time versus historical drafts of my primary ESPN league.  Spot trends that i can exploit in the current year.
### create custom fantasy point projections and rankings, both overall and per position, identifying tier breaks. 
### suggest draft strategies tailored to my league and current ADP data.  

##Tools to use

### python, pandas, and SQL
### use any or none of the legacy code.  You wont offend me if we write it from scratch, but use the intent to guide or inform the type of analyses i want to investigate.





## Legacy Project Overview

This is a fantasy football analytics repository with two main components:
- **2023/**: Legacy ESPN fantasy football analysis tools (2009-2023 seasons)  
- **2024/**: Advanced ADP correlation analysis using Databricks/PySpark

When in doubt, 2024/ supercedes similar files or functions from 2023/.  2023 used Selenium Webdriver to scrape ESPN league data but 2024 uses the espn_api python package.

## Development Setup

### 2023 Legacy Code
```bash
cd 2023/
pip install -r requirements.txt
```

Configuration required in `fantasyfb.ini` (copy from template):
```ini
[main]
username=your_espn_username
password=your_espn_password
leagueId=your_league_id
chromedriverexe=path/to/chromedriver
```

### 2024 Analysis
Requires Databricks environment with access to Unity Catalog tables:
- `pmracek.sports.adp_fantasypros_history`
- `pmracek.sports.fantasypros_ec_xref`
- `pmracek.sports.drafts_ec`

## Architecture

### Data Layer (2023)
Historical data follows naming pattern: `{season}_{week}_{filetype}.txt`

**Core Data Types:**
- `matchup_recap`: Team scores and head-to-head outcomes
- `quickbox`: Individual player performances (starter/bench breakdown)
- `faab_report`: Waiver wire bidding history and results

### Analysis Pipeline (2023)
1. **Data Collection**: `espn.py` uses Selenium for ESPN login/scraping
2. **Real-time Processing**: `MatchupPointFlow_Data.py` collects live scoring during games
3. **Analysis Modules**:
   - `FAAB Analysis.py`: Correlates waiver spending with player performance
   - `Luck aka Pythagorean Expected Wins.py`: Statistical luck analysis using z-scores
   - `MatchupPointFlow_Charts_*.py`: Live scoring visualizations

### Modern Analytics (2024)
Built on PySpark DataFrames with Spark SQL:
- `adp_correlation.py`: Multi-year correlation between expert rankings vs actual drafts
- `adp_fantasypros.py`: Scrapes FantasyPros ADP data across scoring formats
- `pff data collection.py`: Premium PFF data collection with authentication

## Key Development Patterns

### Databricks Notebooks (2024)
- Use `# COMMAND ----------` for cell separation
- Access data via `spark.table()` from Unity Catalog
- Create temp views with `.createOrReplaceTempView()` for SQL analysis
- Convert to Pandas with `.toPandas()` for matplotlib charts

### Team Mapping System
Historical team rosters maintained by year dictionaries:
```python
teams = {2008:pre2010, 2009:pre2010, 2010:t2010, ...}
```

### Real-time Data Collection
`MatchupPointFlow_Data.py` checks NFL game status via ESPN API before collecting live fantasy scores during active games.