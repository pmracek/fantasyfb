# Databricks notebook source
# MAGIC %md
# MAGIC # Questions to answer
# MAGIC - Compare PosN across EC and FP ECR -- especially first 6-8 rounds
# MAGIC - Can we predict EC draft position by [FP] ECR round by round, every 2 rounds, and in the first 10 rounds for year and across years
# MAGIC - Expand to other ADP sources

# COMMAND ----------

from pyspark.sql.functions import col,lit

# COMMAND ----------

adp_df = spark.table("pmracek.sports.adp_fantasypros_history").alias("adp").withColumnRenamed("overall_pick_num","fantasypros_overall_pick_num")
xref_df = spark.table("pmracek.sports.fantasypros_ec_xref").alias("xref")
ec_df = spark.table("pmracek.sports.drafts_ec").alias("ec").withColumnRenamed("overall_pick_num","ec_overall_pick_num")

# COMMAND ----------

# Join ec and xref on playerName and season
ec_xref_joined = ec_df.join(
    xref_df,
    (ec_df.playerName == xref_df.ec_playerName) & (ec_df.season == xref_df.year),
    "inner"
)


# Join the result with adp on adp_playerName and season
draft_data = ec_xref_joined.join(
    adp_df,
    (ec_xref_joined.fantasypros_playerName == adp_df.playerName) & 
    (ec_xref_joined.year == col("adp.Year")) & 
    (ec_xref_joined.scoring == col("adp.scoring")),
    "inner"
).select("teamid","teamName", "ec_playerName","adp.year","adp.scoring","ec.position","fantasypros_overall_pick_num","ec_overall_pick_num")

# Display the final DataFrame
draft_data.createOrReplaceTempView("draft_data")
display(draft_data)

# COMMAND ----------


corr_df = (final_df.select("teamid","teamName",
                           "ec_playerName","adp.year","adp.scoring","ec.position","fantasypros_overall_pick_num","ec_overall_pick_num")
          .filter((col("year")==2024) & (col("adp.scoring") == 'ppr'))
         )
corr_df.createOrReplaceTempView("corr_df")
display(corr_df)

# COMMAND ----------

# MAGIC %sql
# MAGIC create or replace table pmracek.sports.draft_gold
# MAGIC as
# MAGIC select 
# MAGIC floor((fantasypros_overall_pick_num-1) / 12)+1 as fp_round
# MAGIC ,fantasypros_overall_pick_num as fp_overall_pick_num
# MAGIC ,ec_overall_pick_num
# MAGIC ,ec_playername
# MAGIC ,position
# MAGIC ,rank() over (partition by year, scoring, position order by fantasypros_overall_pick_num) as fp_pos_rank
# MAGIC ,rank() over (partition by year, scoring, position order by ec_overall_pick_num) as ec_pos_rank
# MAGIC ,floor((ec_overall_pick_num-1) / 12)+1 as ec_round
# MAGIC ,year
# MAGIC ,scoring
# MAGIC
# MAGIC from draft_data 
# MAGIC where (scoring = 'ppr' and year = 2024) or (scoring = 'half-ppr' and year < 2024)

# COMMAND ----------

corr_df = spark.table("pmracek.sports.draft_gold")
corr_df.createOrReplaceTempView("corr_df")

# COMMAND ----------

from pyspark.sql.functions import col, corr

# Calculate correlation by position
positions = ["QB", "RB", "WR", "TE"]
correlations = {}

for position in positions:
    pos_corr = (corr_df.filter(col("position") == position)
                .select(corr("fp_overall_pick_num", "ec_overall_pick_num").alias("correlation"))
                .collect()[0]["correlation"])
    correlations[position] = pos_corr

# Calculate overall correlation
overall_corr = (corr_df.select(corr("fp_overall_pick_num", "ec_overall_pick_num").alias("correlation"))
                .collect()[0]["correlation"])

# Display results
correlations["Overall"] = overall_corr
correlations

# COMMAND ----------

from pyspark.sql.functions import col, corr

# Filter for fantasypros rounds 1-15
filtered_corr_df = corr_df.filter(col("fp_round").between(1, 15))

# Calculate correlation by position and round
positions = ["QB", "RB", "WR", "TE"]
rounds = range(1, 16)
correlations = {}

for position in positions:
    for round_num in rounds:
        key = f"{position}-round{round_num}"
        pos_round_corr = (filtered_corr_df.filter((col("position") == position) & (col("fp_round") == round_num))
                          .select(corr("fp_overall_pick_num", "ec_overall_pick_num").alias("correlation"))
                          .collect()[0]["correlation"])
        correlations[key] = pos_round_corr

# Calculate overall correlation
overall_corr = (filtered_corr_df.select(corr("fp_overall_pick_num", "ec_overall_pick_num").alias("correlation"))
                .collect()[0]["correlation"])

# Display results
correlations["Overall"] = overall_corr
correlations

# COMMAND ----------

# MAGIC %sql
# MAGIC with fp as (select 
# MAGIC fp_overall_pick_num
# MAGIC ,max(if(position=='QB', fp_pos_rank,0)) over (partition by year,scoring order by fp_overall_pick_num rows between unbounded preceding and current row) as fp_qbs_taken
# MAGIC ,max(if(position=='RB', fp_pos_rank,0)) over (partition by year,scoring order by fp_overall_pick_num rows between unbounded preceding and current row) as fp_rbs_taken
# MAGIC ,max(if(position=='WR', fp_pos_rank,0)) over (partition by year,scoring order by fp_overall_pick_num rows between unbounded preceding and current row) as fp_wrs_taken
# MAGIC ,max(if(position=='TE', fp_pos_rank,0)) over (partition by year,scoring order by fp_overall_pick_num rows between unbounded preceding and current row) as fp_tes_taken
# MAGIC ,year
# MAGIC ,scoring
# MAGIC from pmracek.sports.draft_gold
# MAGIC )
# MAGIC , ec as (select
# MAGIC ec_overall_pick_num
# MAGIC ,max(if(position=='QB', ec_pos_rank,0)) over (partition by year,scoring order by ec_overall_pick_num rows between unbounded preceding and current row) as ec_qbs_taken
# MAGIC ,max(if(position=='RB', ec_pos_rank,0)) over (partition by year,scoring order by ec_overall_pick_num rows between unbounded preceding and current row) as ec_rbs_taken
# MAGIC ,max(if(position=='WR', ec_pos_rank,0)) over (partition by year,scoring order by ec_overall_pick_num rows between unbounded preceding and current row) as ec_wrs_taken
# MAGIC ,max(if(position=='TE', ec_pos_rank,0)) over (partition by year,scoring order by ec_overall_pick_num rows between unbounded preceding and current row) as ec_tes_taken
# MAGIC ,year 
# MAGIC ,scoring
# MAGIC from pmracek.sports.draft_gold
# MAGIC )
# MAGIC select * 
# MAGIC from ec 
# MAGIC join fp 
# MAGIC on ec.ec_overall_pick_num = fp.fp_overall_pick_num 
# MAGIC and ec.year = fp.year 
# MAGIC and ec.scoring = fp.scoring

# COMMAND ----------

pos_taken_df2 = _sqldf 

# COMMAND ----------

import matplotlib.pyplot as plt

# Define positions
positions = ["qb", "rb", "wr", "te"]

# Convert Spark DataFrame to Pandas DataFrame and sort by ec_overall_pick_num
pos_taken_pd = pos_taken_df2.orderBy("ec.year", "ec_overall_pick_num").drop("fp.year","fp.scoring").toPandas()

# Get unique years
years = pos_taken_pd["year"].unique()

# Create line charts for each position and each year
for position in positions:
    for year in years:
        plt.figure(figsize=(10, 6))
        
        # Filter data for the current year
        year_data = pos_taken_pd[pos_taken_pd["year"] == year]
        
        # Limit WR and RB to the first 36 players drafted
        if position in ["wr", "rb"]:
            year_data = year_data[year_data["ec_overall_pick_num"] <= 36]
        
        # Check if the column exists in the DataFrame
        if f"ec_{position}s_taken" in year_data.columns:
            # Plot ec_{position}s_taken
            plt.plot(year_data["ec_overall_pick_num"],
                     year_data[f"ec_{position}s_taken"],
                     label=f"EC {position.upper()}s Taken", marker='o')
        
        if f"fp_{position}s_taken" in year_data.columns:
            # Plot fp_{position}s_taken
            plt.plot(year_data["ec_overall_pick_num"],
                     year_data[f"fp_{position}s_taken"],
                     label=f"FP {position.upper()}s Taken", marker='x')
        
        # Set chart title and labels
        plt.title(f"{position.upper()} Taken Over Picks in {year}")
        plt.xlabel("EC Overall Pick Number")
        plt.ylabel(f"{position.upper()}s Taken")
        plt.legend()
        
        # Set x-axis major ticks every 12 units
        plt.xticks(range(0, year_data["ec_overall_pick_num"].max() + 1, 12))
        
        # Enable grid lines
        plt.grid(True, which='both', linestyle='--', linewidth=0.5)
        
        # Show the plot
        plt.show()

# COMMAND ----------

# MAGIC %sql
# MAGIC create or replace table pmracek.sports.draft_gold_pos_rank as 
# MAGIC with fp as (
# MAGIC select 
# MAGIC fp_pos_rank as pos_rank
# MAGIC ,fp_overall_pick_num
# MAGIC ,position
# MAGIC ,year
# MAGIC ,scoring
# MAGIC from pmracek.sports.draft_gold 
# MAGIC )
# MAGIC , ec as (
# MAGIC select 
# MAGIC ec_pos_rank as pos_rank
# MAGIC ,ec_overall_pick_num
# MAGIC ,position
# MAGIC ,year
# MAGIC ,scoring
# MAGIC from pmracek.sports.draft_gold
# MAGIC )
# MAGIC select 
# MAGIC fp.position
# MAGIC ,fp.pos_rank
# MAGIC ,ec.ec_overall_pick_num
# MAGIC ,fp.fp_overall_pick_num
# MAGIC ,fp.year
# MAGIC ,fp.scoring
# MAGIC from fp 
# MAGIC join ec 
# MAGIC on fp.pos_rank = ec.pos_rank 
# MAGIC and fp.position = ec.position 
# MAGIC and fp.year = ec.year 
# MAGIC and fp.scoring = ec.scoring

# COMMAND ----------

# MAGIC %sql 
# MAGIC select 
# MAGIC year, count(*)
# MAGIC from pmracek.sports.draft_gold_pos_rank
# MAGIC group by all 

# COMMAND ----------

# MAGIC %sql
# MAGIC select * from pmracek.sports.draft_gold where year = 2024 and fp_pos_rank between 20 and 75 and position = 'WR'

# COMMAND ----------

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator

# Load the draft_gold_pos_rank DataFrame
draft_gold_pos_rank = spark.table("pmracek.sports.draft_gold_pos_rank").filter(
    ((col("pos_rank") <= 60) & (col("position").isin("WR", "RB"))) |
    ((col("pos_rank") <= 18) & (col("position").isin("TE", "QB")))
).filter((col("year")>= 2021))

# Convert Spark DataFrame to Pandas DataFrame
draft_gold_pos_rank_pd = draft_gold_pos_rank.toPandas()

# Get unique years and positions
years = draft_gold_pos_rank_pd["year"].unique()
positions = ["RB", "WR", "TE", "QB"]

# Create line charts for each position and year combination
for position in positions:
    for year in years:
        plt.figure(figsize=(10, 6))
        
        # Filter data for the current year and position
        year_position_data = draft_gold_pos_rank_pd[
            (draft_gold_pos_rank_pd["year"] == year) & 
            (draft_gold_pos_rank_pd["position"] == position)
        ]
        
        # Sort data by overall draft position
        year_position_data = year_position_data.sort_values(by=["ec_overall_pick_num", "fp_overall_pick_num"])
        
        # Plot ec_overall_pick_num
        plt.plot(year_position_data["ec_overall_pick_num"], 
                 year_position_data["pos_rank"], 
                 label="EC Overall Pick Number", marker='o')
        
        # Plot fp_overall_pick_num
        plt.plot(year_position_data["fp_overall_pick_num"], 
                 year_position_data["pos_rank"], 
                 label="FP Overall Pick Number", marker='x')
        
        # Set chart title and labels
        plt.title(f"{position} Draft Position Over Ranks in {year}")
        plt.ylabel("Position Rank")
        plt.xlabel("Overall Pick Number")
        plt.legend()
        
        # Enable grid lines
        plt.grid(True, which='both', linestyle='--', linewidth=0.5)
        
        # Set major grid lines
        plt.gca().xaxis.set_major_locator(MultipleLocator(12))
        plt.gca().yaxis.set_major_locator(MultipleLocator(6))
        
        # Show the plot
        plt.show()

# COMMAND ----------

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from pyspark.sql.functions import col

# Load the draft_gold_pos_rank DataFrame
draft_gold_pos_rank = spark.table("pmracek.sports.draft_gold_pos_rank").filter(
    ((col("pos_rank") <= 60) & (col("position").isin("WR", "RB"))) |
    ((col("pos_rank") <= 18) & (col("position").isin("TE", "QB")))
).filter((col("year") >= 2021))

# Convert Spark DataFrame to Pandas DataFrame
draft_gold_pos_rank_pd = draft_gold_pos_rank.toPandas()

# Calculate the difference between ec_overall_pick_num and fp_overall_pick_num
draft_gold_pos_rank_pd['pick_num_difference'] = draft_gold_pos_rank_pd['ec_overall_pick_num'] - draft_gold_pos_rank_pd['fp_overall_pick_num']

# Get unique years and positions
years = draft_gold_pos_rank_pd["year"].unique()
positions = ["RB", "WR", "TE", "QB"]

# Create line charts for each position and year combination
for position in positions:
    for year in years:
        plt.figure(figsize=(10, 6))
        
        # Filter data for the current year and position
        year_position_data = draft_gold_pos_rank_pd[
            (draft_gold_pos_rank_pd["year"] == year) & 
            (draft_gold_pos_rank_pd["position"] == position)
        ]
        
        # Sort data by overall draft position
        year_position_data = year_position_data.sort_values(by=["ec_overall_pick_num", "fp_overall_pick_num"])
        
        # Plot the difference between ec_overall_pick_num and fp_overall_pick_num
        plt.plot(year_position_data["ec_overall_pick_num"], 
                 year_position_data["pick_num_difference"], 
                 label="Pick Number Difference", marker='o')
        
        # Set chart title and labels
        plt.title(f"{position} Draft Position Difference Over Ranks in {year}")
        plt.ylabel("Position Rank")
        plt.xlabel("Overall Pick Number")
        plt.legend()
        
        # Enable grid lines
        plt.grid(True, which='both', linestyle='--', linewidth=0.5)
        
        # Set major grid lines
        plt.gca().xaxis.set_major_locator(MultipleLocator(12))
        plt.gca().yaxis.set_major_locator(MultipleLocator(6))
        
        # Show the plot
        plt.show()

# COMMAND ----------

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from pyspark.sql.functions import col

# Load the draft_gold_pos_rank DataFrame
draft_gold_pos_rank = spark.table("pmracek.sports.draft_gold_pos_rank").filter(
    ((col("pos_rank") <= 60) & (col("position").isin("WR", "RB"))) |
    ((col("pos_rank") <= 18) & (col("position").isin("TE", "QB")))
).filter((col("year") >= 2021))

# Convert Spark DataFrame to Pandas DataFrame
draft_gold_pos_rank_pd = draft_gold_pos_rank.toPandas()

# Calculate the difference between ec_overall_pick_num and fp_overall_pick_num
draft_gold_pos_rank_pd['pick_num_difference'] = draft_gold_pos_rank_pd['ec_overall_pick_num'] - draft_gold_pos_rank_pd['fp_overall_pick_num']

# Get unique years and positions
years = draft_gold_pos_rank_pd["year"].unique()
positions = ["RB", "WR", "TE", "QB"]

# Create line charts for each position and year combination

for position in positions:
    for year in years:
        plt.figure(figsize=(10, 6))
        
        # Filter data for the current year and position
        year_position_data = draft_gold_pos_rank_pd[
            (draft_gold_pos_rank_pd["year"] == year) & 
            (draft_gold_pos_rank_pd["position"] == position)
        ]
        
        # Sort data by position rank
        year_position_data = year_position_data.sort_values(by=["pos_rank"])
        
        # Plot the difference between ec_overall_pick_num and fp_overall_pick_num
        plt.plot(year_position_data["pos_rank"], 
                 year_position_data["pick_num_difference"], 
                 label="Pick Number Difference", marker='o')
        
        # Set chart title and labels
        plt.title(f"{position} Draft Position Difference Over Ranks in {year}")
        plt.xlabel("Position Rank")
        plt.ylabel("Pick Number Difference")
        plt.legend()
        
        # Enable grid lines
        plt.grid(True, which='both', linestyle='--', linewidth=0.5)
        
        # Set major grid lines
        plt.gca().xaxis.set_major_locator(MultipleLocator(12))
        plt.gca().yaxis.set_major_locator(MultipleLocator(6))
        
        # Show the plot
        plt.show()

# COMMAND ----------

import matplotlib.pyplot as plt
from matplotlib.ticker import MultipleLocator
from pyspark.sql.functions import col

# Load the draft_gold_pos_rank DataFrame
draft_gold_pos_rank = spark.table("pmracek.sports.draft_gold_pos_rank").filter(
    ((col("pos_rank") <= 60) & (col("position").isin("WR", "RB"))) |
    ((col("pos_rank") <= 18) & (col("position").isin("TE", "QB")))
).filter((col("year") >= 2021))

# Convert Spark DataFrame to Pandas DataFrame
draft_gold_pos_rank_pd = draft_gold_pos_rank.toPandas()

# Calculate the difference between ec_overall_pick_num and fp_overall_pick_num
draft_gold_pos_rank_pd['pick_num_difference'] = draft_gold_pos_rank_pd['ec_overall_pick_num'] - draft_gold_pos_rank_pd['fp_overall_pick_num']

# Get unique years and positions
years = draft_gold_pos_rank_pd["year"].unique()
positions = ["RB", "WR", "TE", "QB"]

# Create a color map for years
colors = plt.cm.get_cmap('tab10', len(years))

# Create line charts for each position with each year as a different series
for position in positions:
    plt.figure(figsize=(10, 6))
    
    for i, year in enumerate(years):
        # Filter data for the current year and position
        year_position_data = draft_gold_pos_rank_pd[
            (draft_gold_pos_rank_pd["year"] == year) & 
            (draft_gold_pos_rank_pd["position"] == position)
        ]
        
        # Sort data by position rank
        year_position_data = year_position_data.sort_values(by=["pos_rank"])
        
        # Plot the difference between ec_overall_pick_num and fp_overall_pick_num
        plt.plot(year_position_data["pos_rank"], 
                 year_position_data["pick_num_difference"], 
                 label=f"{year}", marker='o', color=colors(i))
    
    # Set chart title and labels
    plt.title(f"{position} Draft Position Difference Over Ranks")
    plt.xlabel("Position Rank")
    plt.ylabel("Pick Number Difference")
    plt.legend(title="Year")
    
    # Enable grid lines
    plt.grid(True, which='both', linestyle='--', linewidth=0.5)
    
    # Set major grid lines
    plt.gca().xaxis.set_major_locator(MultipleLocator(12))
    plt.gca().yaxis.set_major_locator(MultipleLocator(6))
    
    # Show the plot
    plt.show()

# COMMAND ----------

# MAGIC %sql 
# MAGIC select
# MAGIC position
# MAGIC ,pos_rank
# MAGIC ,avg(ec_overall_pick_num) as avg_ec_overall_pick_num
# MAGIC ,avg(fp_overall_pick_num) as avg_fp_overall_pick_num
# MAGIC ,avg(ec_overall_pick_num) - avg(fp_overall_pick_num) as dif
# MAGIC from pmracek.sports.draft_gold_pos_rank
# MAGIC where position in ('QB','RB','WR','TE') and year >= 2021 and pos_rank <= 60
# MAGIC group by all
# MAGIC order by position, pos_rank 

# COMMAND ----------

df = _sqldf

# COMMAND ----------

import matplotlib.pyplot as plt
import pandas as pd

# Ensure df is defined and contains the necessary columns
# df should have columns: 'position', 'pos_rank', 'dif'

# Define the positions to plot
positions = ['RB', 'QB', 'TE', 'WR']

# Convert Spark DataFrame to Pandas DataFrame
df_pandas = df.toPandas()

# Create a new figure
plt.figure(figsize=(12, 8))

# Plot each position
for position in positions:
    subset = df_pandas[df_pandas['position'] == position]
    plt.plot(subset['pos_rank'], subset['dif'], label=position, marker='o')

# Set chart title and labels
plt.title('Difference by Position Rank for Each Position')
plt.xlabel('Position Rank')
plt.ylabel('Difference (avg_ec_overall_pick_num - avg_fp_overall_pick_num)')

# Set x-axis major ticks to intervals of 6 units
plt.xticks(range(6, int(df_pandas['pos_rank'].max()) + 6, 6))

# Set y-axis major ticks to intervals of 12 units
plt.yticks(range(int(df_pandas['dif'].min()), int(df_pandas['dif'].max()) + 12, 12))

# Add legend
plt.legend()

# Enable grid lines
plt.grid(True, which='both', linestyle='--', linewidth=0.5)

# Show the plot
plt.show()

# COMMAND ----------

