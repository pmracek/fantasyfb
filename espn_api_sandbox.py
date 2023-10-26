# Databricks notebook source
# MAGIC %pip install espn_api

# COMMAND ----------

dbutils.widgets.text("leagueId","111414")
dbutils.widgets.text("season","2023")

# COMMAND ----------

from espn_api.football import League
league_id = dbutils.widgets.get("leagueId")
season = int(dbutils.widgets.get("season"))

league = League(league_id=league_id, year=season)

# COMMAND ----------




# COMMAND ----------

box = league.box_scores()

# COMMAND ----------


