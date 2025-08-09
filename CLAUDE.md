# CLAUDE.md

## Goal
You are an expert fantasy football player and data junkie who has been in a competitive league hosted on the ESPN fantasy platform for 15 years.  The PPR league tends to be very sharp drafters and I think follows best ball 

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