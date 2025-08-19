# Databricks notebook source
"""
Analysis to identify which fantasy industry source most closely resembles your ESPN league's 2024 draft
"""
import pandas as pd
from pyspark.sql import SparkSession
from pyspark.sql.functions import col, corr, when, avg, stddev
import matplotlib.pyplot as plt
import seaborn as sns
from espn_api.football import League
import requests
from io import StringIO
import numpy as np
from scipy.stats import spearmanr, pearsonr

# COMMAND ----------

# Initialize Spark session and get league data
spark = SparkSession.getActiveSession()

# Your league configuration from CLAUDE.md
league_id = "111414"  # Update with your actual league ID
season = 2024

# Initialize ESPN league
league = League(league_id=league_id, year=season)

# COMMAND ----------

def get_espn_draft_data(league):
    """Extract draft data from ESPN league"""
    draft_dict = {}
    for i, pick in enumerate(league.draft):
        draft_dict[i+1] = {            
            "overall_pick_num": i+1,
            "round_num": pick.round_num,
            "round_pick_num": pick.round_pick,
            "teamId": pick.team.team_id,
            "teamName": pick.team.team_name,            
            "playerId": pick.playerId,
            "playerName": pick.playerName,
            "position": league.player_info(playerId=pick.playerId).position
        }
    df = pd.DataFrame.from_dict(draft_dict, orient="index")
    df["position_pick_num"] = df.groupby("position")["overall_pick_num"].rank(method="dense").astype(int)
    df["season"] = season
    df["leagueId"] = league_id
    return df

# Get your league's 2024 draft results
espn_draft_df = get_espn_draft_data(league)
print(f"ESPN Draft Data: {len(espn_draft_df)} picks")
print(espn_draft_df[['playerName', 'position', 'overall_pick_num', 'position_pick_num']].head(10))

# COMMAND ----------

# Define industry sources based on adp_system config
industry_sources = {
    'fantasypros': {
        'name': 'FantasyPros',
        'ppr_url': 'https://www.fantasypros.com/nfl/adp/ppr-overall.php',
        'params': {'year': 2024}
    },
    'fantasyfootballcalculator': {
        'name': 'Fantasy Football Calculator', 
        'ppr_url': 'https://fantasyfootballcalculator.com/adp/ppr/12-team/all',
        'params': {'year': 2024}
    },
    'nfc_shgn': {
        'name': 'NFC (SHGN)',
        'ppr_url': 'https://nfc.shgn.com/adp.data.php',
        'params': {
            "team_id": "0",
            "from_date": "2024-08-01", 
            "to_date": "2024-08-31",
            "num_teams": "12",
            "draft_type": "-1",
            "sport": "football",
            "league_teams": "0",
            "download": ""
        },
        'method': 'POST'
    }
}

# COMMAND ----------

def fetch_fantasypros_adp(url, params):
    """Fetch ADP data from FantasyPros"""
    response = requests.get(url, params)
    response.raise_for_status()
    
    dfs = pd.read_html(response.text)
    adp_df = dfs[0]
    
    # Parse player info
    adp_df[['playerName', 'Team', 'Bye']] = adp_df['Player Team (Bye)'].str.extract(
        r'(.+?)(?:\s+([A-Z]+)\s+\((\d*)\))?\s*O?$'
    )
    
    # Clean up columns
    adp_df.rename(columns={'Rank': 'overall_adp', 'AVG': 'consensus_adp'}, inplace=True)
    adp_df['position_rank'] = adp_df['POS'].str.extract(r'(\d+)').astype(float)
    adp_df['position'] = adp_df['POS'].str.extract(r'([A-Z]+)')
    
    return adp_df[['playerName', 'position', 'overall_adp', 'position_rank', 'consensus_adp']]

def fetch_ffc_adp(url, params):
    """Fetch ADP data from Fantasy Football Calculator"""
    response = requests.get(url, params)
    response.raise_for_status()
    
    dfs = pd.read_html(response.text)
    adp_df = dfs[0]
    
    # FFC typically has columns: Rank, Player, Pos, Team, Avg, Std Dev, etc.
    if 'Player' in adp_df.columns:
        adp_df['playerName'] = adp_df['Player']
        adp_df['position'] = adp_df['Pos'] if 'Pos' in adp_df.columns else adp_df['Position']
        adp_df['overall_adp'] = adp_df['Rank'] if 'Rank' in adp_df.columns else adp_df.index + 1
        adp_df['consensus_adp'] = adp_df['Avg'] if 'Avg' in adp_df.columns else adp_df['ADP']
        
        # Calculate position rank
        adp_df['position_rank'] = adp_df.groupby('position')['overall_adp'].rank(method='dense')
        
        return adp_df[['playerName', 'position', 'overall_adp', 'position_rank', 'consensus_adp']]
    
    return pd.DataFrame()

def fetch_nfc_adp(url, params):
    """Fetch ADP data from NFC/SHGN"""
    response = requests.post(url, data=params)
    response.raise_for_status()
    
    tsv_string = response.content.decode('utf-8')
    tsv_file = StringIO(tsv_string)
    adp_df = pd.read_csv(tsv_file, sep='\t')
    
    # NFC columns typically: Player, Pos, Team, ADP, etc.
    if 'Player' in adp_df.columns:
        adp_df['playerName'] = adp_df['Player']
        adp_df['position'] = adp_df['Pos'] if 'Pos' in adp_df.columns else adp_df['Position']
        adp_df['consensus_adp'] = adp_df['ADP'] if 'ADP' in adp_df.columns else adp_df['Avg']
        adp_df['overall_adp'] = adp_df.index + 1
        
        # Calculate position rank
        adp_df['position_rank'] = adp_df.groupby('position')['overall_adp'].rank(method='dense')
        
        return adp_df[['playerName', 'position', 'overall_adp', 'position_rank', 'consensus_adp']]
    
    return pd.DataFrame()

# COMMAND ----------

# Collect ADP data from all sources
adp_data = {}

for source_key, source_config in industry_sources.items():
    print(f"Fetching data from {source_config['name']}...")
    try:
        if source_key == 'fantasypros':
            df = fetch_fantasypros_adp(source_config['ppr_url'], source_config['params'])
        elif source_key == 'fantasyfootballcalculator':
            df = fetch_ffc_adp(source_config['ppr_url'], source_config['params'])
        elif source_key == 'nfc_shgn':
            df = fetch_nfc_adp(source_config['ppr_url'], source_config['params'])
        
        if not df.empty:
            df['source'] = source_config['name']
            adp_data[source_key] = df
            print(f"✓ {source_config['name']}: {len(df)} players")
        else:
            print(f"✗ {source_config['name']}: No data retrieved")
            
    except Exception as e:
        print(f"✗ {source_config['name']}: Error - {str(e)}")

print(f"\nSuccessfully collected data from {len(adp_data)} sources")

# COMMAND ----------

def standardize_player_names(name):
    """Standardize player names for matching"""
    if pd.isna(name):
        return ""
    
    # Remove common suffixes
    name = str(name).strip()
    suffixes = [' Jr.', ' Sr.', ' III', ' II', ' IV']
    for suffix in suffixes:
        name = name.replace(suffix, '')
    
    # Handle common name variations
    name_replacements = {
        'Kenneth Walker': 'Ken Walker',
        'Gabriel Davis': 'Gabe Davis',
        'DJ Moore': 'D.J. Moore',
        'AJ Brown': 'A.J. Brown',
        'CJ Stroud': 'C.J. Stroud',
        'DK Metcalf': 'D.K. Metcalf'
    }
    
    return name_replacements.get(name, name)

# Standardize player names in all datasets
espn_draft_df['playerName_std'] = espn_draft_df['playerName'].apply(standardize_player_names)

for source_key in adp_data:
    adp_data[source_key]['playerName_std'] = adp_data[source_key]['playerName'].apply(standardize_player_names)

# COMMAND ----------

# Calculate correlations between your league and each industry source
correlation_results = {}

for source_key, source_df in adp_data.items():
    source_name = source_df['source'].iloc[0]
    
    # Merge ESPN draft with industry ADP data
    merged_df = espn_draft_df.merge(
        source_df, 
        on=['playerName_std', 'position'], 
        how='inner',
        suffixes=('_espn', '_industry')
    )
    
    if len(merged_df) > 10:  # Need minimum matches for meaningful correlation
        # Calculate various correlation metrics
        pearson_overall = pearsonr(merged_df['overall_pick_num'], merged_df['consensus_adp'])[0]
        spearman_overall = spearmanr(merged_df['overall_pick_num'], merged_df['consensus_adp'])[0]
        
        # Calculate by position
        position_corrs = {}
        for pos in ['QB', 'RB', 'WR', 'TE']:
            pos_data = merged_df[merged_df['position'] == pos]
            if len(pos_data) >= 3:
                position_corrs[pos] = {
                    'pearson': pearsonr(pos_data['overall_pick_num'], pos_data['consensus_adp'])[0],
                    'spearman': spearmanr(pos_data['overall_pick_num'], pos_data['consensus_adp'])[0],
                    'matches': len(pos_data)
                }
        
        correlation_results[source_key] = {
            'source_name': source_name,
            'total_matches': len(merged_df),
            'pearson_overall': pearson_overall,
            'spearman_overall': spearman_overall,
            'position_correlations': position_corrs,
            'merged_data': merged_df
        }
        
        print(f"{source_name}: {len(merged_df)} matches, "
              f"Pearson: {pearson_overall:.3f}, Spearman: {spearman_overall:.3f}")

# COMMAND ----------

# Create comprehensive results summary
results_summary = []

for source_key, results in correlation_results.items():
    row = {
        'Source': results['source_name'],
        'Total_Matches': results['total_matches'],
        'Pearson_Overall': results['pearson_overall'],
        'Spearman_Overall': results['spearman_overall']
    }
    
    # Add position-specific correlations
    for pos in ['QB', 'RB', 'WR', 'TE']:
        if pos in results['position_correlations']:
            row[f'{pos}_Pearson'] = results['position_correlations'][pos]['pearson']
            row[f'{pos}_Matches'] = results['position_correlations'][pos]['matches']
        else:
            row[f'{pos}_Pearson'] = None
            row[f'{pos}_Matches'] = 0
    
    results_summary.append(row)

summary_df = pd.DataFrame(results_summary)
summary_df = summary_df.sort_values('Spearman_Overall', ascending=False)

print("CORRELATION ANALYSIS RESULTS")
print("=" * 60)
print(summary_df.round(3))

# COMMAND ----------

# Identify the best matching source
if correlation_results:
    best_source_key = max(correlation_results.keys(), 
                         key=lambda x: correlation_results[x]['spearman_overall'])
    best_source = correlation_results[best_source_key]
    
    print(f"\n🏆 BEST MATCHING SOURCE: {best_source['source_name']}")
    print(f"   Overall Spearman Correlation: {best_source['spearman_overall']:.3f}")
    print(f"   Total Player Matches: {best_source['total_matches']}")
    print(f"   Position Breakdown:")
    
    for pos, stats in best_source['position_correlations'].items():
        print(f"     {pos}: {stats['spearman']:.3f} correlation ({stats['matches']} matches)")

# COMMAND ----------

# Create visualization comparing your league to the best matching source
if correlation_results:
    fig, axes = plt.subplots(2, 2, figsize=(15, 12))
    fig.suptitle(f'2024 Draft Comparison: Your League vs {best_source["source_name"]}', fontsize=16)
    
    merged_data = best_source['merged_data']
    
    # Overall comparison
    axes[0,0].scatter(merged_data['consensus_adp'], merged_data['overall_pick_num'], alpha=0.7)
    axes[0,0].plot([0, 200], [0, 200], 'r--', alpha=0.5)  # Perfect correlation line
    axes[0,0].set_xlabel(f'{best_source["source_name"]} ADP')
    axes[0,0].set_ylabel('Your League Pick Number')
    axes[0,0].set_title(f'Overall Correlation: {best_source["spearman_overall"]:.3f}')
    
    # Position-specific plots
    positions = ['RB', 'WR', 'TE']
    colors = ['blue', 'green', 'orange']
    
    for i, (pos, color) in enumerate(zip(positions, colors)):
        if pos in best_source['position_correlations']:
            pos_data = merged_data[merged_data['position'] == pos]
            row, col = (0,1) if i == 0 else (1, i-1)
            
            axes[row,col].scatter(pos_data['consensus_adp'], pos_data['overall_pick_num'], 
                                alpha=0.7, color=color)
            axes[row,col].set_xlabel(f'{best_source["source_name"]} ADP')
            axes[row,col].set_ylabel('Your League Pick Number')
            
            corr = best_source['position_correlations'][pos]['spearman']
            matches = best_source['position_correlations'][pos]['matches']
            axes[row,col].set_title(f'{pos} Correlation: {corr:.3f} ({matches} players)')
    
    plt.tight_layout()
    plt.show()

# COMMAND ----------

# Save results for future reference
results_df = spark.createDataFrame(summary_df)
results_df.write.mode("overwrite").saveAsTable("pmracek.sports.league_adp_correlation_2024")

print(f"\n✅ Analysis complete! Results saved to pmracek.sports.league_adp_correlation_2024")
print(f"Your league most closely resembles: {best_source['source_name']}")

# COMMAND ----------

# Additional insights: Where does your league differ most?
if correlation_results:
    merged_data = best_source['merged_data']
    merged_data['pick_difference'] = merged_data['overall_pick_num'] - merged_data['consensus_adp']
    
    print("\n📊 BIGGEST DIFFERENCES FROM INDUSTRY CONSENSUS:")
    print("Players drafted earlier than expected:")
    early_picks = merged_data.nlargest(10, 'pick_difference')[['playerName', 'position', 'overall_pick_num', 'consensus_adp', 'pick_difference']]
    print(early_picks.round(1))
    
    print("\nPlayers drafted later than expected:")
    late_picks = merged_data.nsmallest(10, 'pick_difference')[['playerName', 'position', 'overall_pick_num', 'consensus_adp', 'pick_difference']]
    print(late_picks.round(1))

# COMMAND ----------