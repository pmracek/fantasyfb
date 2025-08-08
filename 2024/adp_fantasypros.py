# Databricks notebook source
import requests
from io import StringIO
import pandas as pd
import json
from pyspark.sql.functions import col, lit


# COMMAND ----------

sites = {
  "fantasypros":    
      [{
          "scoring":"standard"
          ,"url":"https://www.fantasypros.com/nfl/adp/overall.php"
          ,"start_year":2012
      }
      ,{
          "scoring":"half-ppr"
          ,"url":"https://www.fantasypros.com/nfl/adp/half-point-ppr-overall.php"
          ,"start_year":2018
      }
      ,{
          "scoring":"ppr"
          ,"url":"https://www.fantasypros.com/nfl/adp/ppr-overall.php"
          ,"start_year":2012
      }
      ]
}


# COMMAND ----------

url = "https://nfc.shgn.com/adp.data.php"
params = {
    "team_id": "0",
    "from_date": "2024-08-07",
    "to_date": "2024-08-14",
    "num_teams": "12",
    "draft_type": "-1", # All Drafts ("Non Super-flex")
    "sport": "football",
    "league_teams": "0",
    "download":""
}

# COMMAND ----------


r = requests.post(url,data=params)
tsv_string = r.content.decode('utf-8') 
tsv_file = StringIO(tsv_string) # Use StringIO to simulate a file object
pdf = pd.read_csv(tsv_file, sep='\t')
df = spark.createDataFrame(pdf)
df = (df.withColumn("num_teams",lit(params['num_teams']))
       .withColumn("draft_type",lit(params['draft_type']))
       .withColumn("from_date",lit(params['from_date']))
       .withColumn("to_date",lit(params['to_date'])))
        

# Display the Spark DataFrame
display(df)

# COMMAND ----------

import requests
import pandas as pd
from urllib.parse import urlparse

def fetch_adp_data(site, scoring, year, url,  params):
    base_domain = urlparse(url).netloc

    # Fetch the webpage content
    response = requests.get(url, params)
    response.raise_for_status()  # Check if the request was successful

    # Parse the HTML content using pandas
    dfs = pd.read_html(response.text)

    # Assuming the first table is the one we need
    adp_df = dfs[0]
    
    adp_df[['playerName', 'Team', 'Bye']] = adp_df['Player Team (Bye)'].str.extract(
        r'(.+?)(?:\s+([A-Z]+)\s+\((\d*)\))?\s*O?$'
    )

    # Rename the "Rank" column to "overall_pick_num"
    adp_df.rename(columns={'Player Team (Bye)':'PlayerTeamBye','Rank': 'overall_pick_num', 'AVG': 'Consensus'}, inplace=True)

    # Split the "Player Team (Bye)" column into three separate columns


    # Parse the number out of the POS column
    adp_df['position_pick_num'] = adp_df['POS'].str.extract(r'(\d+)')
    adp_df['position'] = adp_df['POS'].str.extract(r'([A-Z]+)')

    # Add the year as a column
    adp_df['Year'] = year
    adp_df['Site'] = base_domain
    adp_df['Scoring'] = scoring

    return adp_df

# COMMAND ----------

all_dfs = []

for site, formats in sites.items():
  for format in formats:
    # Loop through the years from 2015 to 2023 and concatenate the DataFrames
    for year in range(format["start_year"], 2024 + 1):
      df = fetch_adp_data(site=site, scoring=format["scoring"], year=year, url=format["url"], params={'year': year})
      all_dfs.append(df)

# Concatenate all DataFrames
all_years_df = pd.concat(all_dfs, ignore_index=True)

# Convert to Spark DataFrame and save as a table
all_years_df_spark = spark.createDataFrame(all_years_df)
all_years_df_spark.write.mode("overwrite").saveAsTable("pmracek.sports.adp_fantasypros_history")

# Display the concatenated DataFrame
display(all_years_df)
print(format)

# COMMAND ----------



# COMMAND ----------

