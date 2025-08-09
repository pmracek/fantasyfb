# ADP Data Collection System

A comprehensive system for collecting, analyzing, and tracking Average Draft Position (ADP) data from multiple fantasy football sources.

## Features

- **Multi-Source Data Collection**: Collects ADP data from FantasyPros, Fantasy Football Calculator, and other major sites
- **Async Data Processing**: Concurrent collection from multiple sources for efficiency
- **Player Name Standardization**: Handles name variations across different sources
- **Trend Analysis**: Tracks ADP changes over time with 7, 14, and 30-day comparisons
- **Volatility Scoring**: Identifies players with high ADP variance
- **Delta Lake Storage**: Scalable data storage with ACID transactions

## Quick Start

### 1. Setup
```bash
cd adp_system
pip install -r requirements.txt
```

### 2. Initialize Database Tables
```bash
# Run the SQL scripts in your Spark environment
spark-sql -f sql/create_tables.sql
```

### 3. Run Data Collection
```bash
# Full collection from all sources
python main.py collect

# Run trend analysis only
python main.py trends

# View player history
python main.py player "Christian McCaffrey"
```

## Configuration

Edit `config/sources.yaml` to:
- Add/remove ADP sources
- Adjust rate limiting
- Configure endpoints for different scoring formats

## Usage Examples

### Collect Data Programmatically
```python
from src.adp_collector import ADPCollector
from pyspark.sql import SparkSession

spark = SparkSession.builder.appName("ADP").getOrCreate()
collector = ADPCollector(spark)

# Run collection
collection_id = await collector.collect_all_sources(
    season=2024,
    league_size=12,
    draft_type='redraft'
)
```

### Analyze Trends
```python
from src.trend_analyzer import TrendAnalyzer

analyzer = TrendAnalyzer(spark)

# Get biggest risers
risers = analyzer.get_biggest_risers(scoring_format='ppr', days=7)
print(risers)

# Get volatile players
volatile = analyzer.get_volatile_players(min_volatility=5.0)
print(volatile)
```

### Query Data with SQL
```sql
-- Find biggest ADP changes in last 7 days
SELECT player_name, position, current_adp, adp_7d_change
FROM adp_trends 
WHERE scoring_format = 'ppr' 
  AND trend_date = current_date()
ORDER BY ABS(adp_7d_change) DESC
LIMIT 20;

-- Compare position trends
SELECT 
  position,
  AVG(current_adp) as avg_adp,
  AVG(adp_7d_change) as avg_change,
  COUNT(*) as player_count
FROM adp_trends
WHERE scoring_format = 'ppr'
  AND trend_date = current_date()
GROUP BY position
ORDER BY avg_adp;
```

## Data Schema

### Core Tables

**adp_data**: Raw ADP collection data
- Partitioned by collection_date, source, scoring_format
- Contains player ADP, position ranks, volatility metrics

**player_crosswalk**: Player name standardization
- Maps source-specific names to canonical player IDs
- Handles name variations (T.J. vs TJ, etc.)

**adp_trends**: Calculated trend metrics
- Daily trend calculations with 7/14/30-day changes
- Momentum scores and opportunity rankings

**collection_runs**: Collection metadata
- Tracks collection success/failure
- Error logging and performance metrics

## Architecture

```
┌─────────────────┐    ┌──────────────────┐    ┌─────────────────┐
│   Data Sources  │───▶│  ADP Collector   │───▶│  Delta Tables   │
│                 │    │                  │    │                 │
│ • FantasyPros   │    │ • Async fetching │    │ • adp_data      │
│ • FFC           │    │ • Rate limiting  │    │ • crosswalk     │
│ • Underdog      │    │ • Error handling │    │ • trends        │
└─────────────────┘    └──────────────────┘    └─────────────────┘
                                 │
                       ┌──────────────────┐
                       │ Trend Analyzer   │
                       │                  │
                       │ • Daily calcs    │
                       │ • Momentum       │
                       │ • Volatility     │
                       └──────────────────┘
```

## Extending the System

### Adding New Sources
1. Create a new parser class inheriting from `BaseParser`
2. Add source configuration to `config/sources.yaml`
3. Register parser in `ADPCollector.__init__()`

### Custom Analysis
Use the `TrendAnalyzer` class methods or write custom Spark SQL queries against the Delta tables.

## Scheduling

For automated collection, set up a cron job or use Apache Airflow:

```bash
# Collect 3x daily
0 8,14,20 * * * cd /path/to/adp_system && python main.py collect
```

## Monitoring

Check collection success in the `collection_runs` table:

```sql
SELECT 
  collection_date,
  sources_successful,
  sources_attempted,
  total_players_collected,
  status
FROM collection_runs
ORDER BY start_timestamp DESC
LIMIT 10;
```