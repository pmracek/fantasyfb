# Databricks notebook source
# MAGIC %pip install espn_api

# COMMAND ----------

# MAGIC %pip show espn_api

# COMMAND ----------

from databricks.connect import DatabricksSession
from databricks.sdk import WorkspaceClient
import pandas as pd

spark = DatabricksSession.builder.getOrCreate()
w = WorkspaceClient()
w.dbutils.widgets.text("leagueId","111414")
w.dbutils.widgets.text("season","2024")

# COMMAND ----------

from espn_api.football import *
from espn_api.base_pick import BasePick
league_id = w.dbutils.widgets.get("leagueId")
season = int(w.dbutils.widgets.get("season"))

league = League(league_id=league_id, year=season)

# COMMAND ----------

league = League(league_id=league_id, year=2018)
league.draft

# COMMAND ----------

def parse_draft(draft=[BasePick]):
    """Take a list of espn_api.football.Pick objects and returns a spark dataframe with the following columns: overall pick number, round number, round pick number, teamId, teamName,playerName, playerId"""

    draft_dict = {}
    for i,pick in enumerate(draft):
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
    df = pd.DataFrame.from_dict(draft_dict,orient="index")
    # use a window function on the df to calculate the pick number per position.  The equivalent SQL syntax is RANK() OVER (PARTITION BY position ORDER BY overall_pick_num)
    df["position_pick_num"] =   df.groupby("position")["overall_pick_num"].rank(method="dense").astype(int)
    return df

draft_dfs = []
for year in range(2024,2025,1):
    print(f"Getting draft for league {league_id} in year {year}")
    league = League(league_id=league_id, year=year)
    try:
        df = parse_draft(league.draft)
        df["season"]            =   year
        df["leagueId"]          =   league_id
        draft_dfs.append(df)
    except:
        continue
draft_df = pd.concat(draft_dfs)

#convert draft_df to a spark dataframe and save as a table named pmracek.pm_fantasyfb.drafts
draft_df_spark = spark.createDataFrame(draft_df)
display(draft_df_spark)


# COMMAND ----------

# draft_df_spark.write.mode("overwrite").saveAsTable("pmracek.sports.drafts_ec")
draft_df_spark.write.mode("append").saveAsTable("pmracek.sports.drafts_ec")


# COMMAND ----------

# MAGIC %sql
# MAGIC select season, count(*) from pmracek.sports.drafts_ec group by all

# COMMAND ----------

