# Databricks notebook source
%pip install fuzzywuzzy[speedup]

# COMMAND ----------

from fuzzywuzzy import fuzz
from pyspark.sql.functions import udf
from pyspark.sql.types import IntegerType

def similarity_score(name1, name2):
    return fuzz.token_sort_ratio(name1, name2)

similarity_score_udf = udf(similarity_score, IntegerType())

# COMMAND ----------

from pyspark.sql import functions as F

# Assume df1 and df2 are your two DataFrames with player name columns 'playerName1' and 'playerName2'
df1 = spark.table("pmracek.sports.adp_fantasypros_history").alias("adp")
df2 = spark.table("pmracek.sports.drafts_ec").alias("ec")

# Rename the player name columns
df1 = df1.withColumnRenamed("playerName", "fantasypros_playerName")
df2 = df2.withColumnRenamed("playerName", "ec_playerName")

# Cross join the DataFrames and compute the similarity score
cross_joined_df = df1.crossJoin(df2)
cross_joined_df = cross_joined_df.withColumn("similarity", similarity_score_udf(F.col("fantasypros_playerName"), F.col("ec_playerName")))

# Filter the rows with a similarity score above a certain threshold (e.g., 80)
threshold = 87
fuzzy_joined_df = cross_joined_df.filter(
    (F.col("similarity") >= threshold) 
    & (F.col("ec.season") == F.col("adp.year"))
)

# Select the relevant columns and rename them
result_df = fuzzy_joined_df.select("fantasypros_playerName", "ec_playerName", "adp.year", "similarity", "adp.site","adp.scoring")

result_df.write.mode("overwrite").saveAsTable("pmracek.sports.fantasypros_ec_xref")
# Display the result
display(result_df)

# COMMAND ----------

display(df2)

# COMMAND ----------

# MAGIC %sql
# MAGIC select year, count(*) from pmracek.sports.fantasypros_ec_xref group by all 

# COMMAND ----------

