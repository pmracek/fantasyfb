# Databricks notebook source
import requests
import json
import pandas as pd

def get_pff_http_headers():
  return {
  'accept': 'application/json, text/plain, */*',
  'accept-language': 'en-US,en;q=0.9',
  'cookie': '_gcl_au=1.1.793003037.1726106497; _ga=GA1.1.1713050416.1726106497; prism_651055355=f02757d5-7d32-479a-b43c-063145c60219; FPID=FPID2.2.uoIuSrpck3K65K9oQOvm3SwPeEQMt1YCGiXLzHd367s%3D.1726106497; FPAU=1.1.793003037.1726106497; _gtmeec=e30%3D; _fbp=fb.1.1726106497426.1067781360; FPLC=ovluuFNWF27B0766pTwX18WCr2b9vzAribWE2tGz%2BdamTW8jG0jne3g0Y3XAlPQk0GOWPw4meYdjhQzRvyhUyIZsqNxmcnnaMuhaHYbRFO6B41DrJt%2FwoJ5nPNLZeQ%3D%3D; _hp2_ses_props.2100373990=%7B%22r%22%3A%22https%3A%2F%2Fwww.pff.com%2F%22%2C%22ts%22%3A1727872573709%2C%22d%22%3A%22premium.pff.com%22%2C%22h%22%3A%22%2Fnfl%2Fpositions%2F2024%2FREGPO%2Freceiving%22%2C%22q%22%3A%22%3Fposition%3DWR%26minimum%3D50p%22%7D; _premium_key=SFMyNTY.g3QAAAABbQAAABZndWFyZGlhbl9kZWZhdWx0X3Rva2VubQAAAlhleUpoYkdjaU9pSklVelV4TWlJc0luUjVjQ0k2SWtwWFZDSjkuZXlKaGRXUWlPaUpRY21WdGFYVnRJaXdpWlhod0lqb3hOekkzT0RjMk1UYzFMQ0pwWVhRaU9qRTNNamM0TnpJMU56VXNJbWx6Y3lJNklsQnlaVzFwZFcwaUxDSnFkR2tpT2lKbU1qSmhPRGN3WXkxbE1tUm1MVFEyT1RrdFlqRTVNQzB5WWpRNFlqYzRNakJrWVdNaUxDSnVZbVlpT2pFM01qYzROekkxTnpRc0luQmxiU0k2ZXlKaFlXWWlPakVzSW01allXRWlPakVzSW01bWJDSTZNU3dpZFdac0lqb3hmU3dpYzNWaUlqb2llMXdpWlcxaGFXeGNJanBjSW5CdGNtRmpaV3RBWjIxaGFXd3VZMjl0WENJc1hDSm1aV0YwZFhKbGMxd2lPbHRkTEZ3aVptbHljM1JmYm1GdFpWd2lPbTUxYkd3c1hDSnNZWE4wWDI1aGJXVmNJanB1ZFd4c0xGd2lkV2xrWENJNlhDSTRPVGN3TmpZeU9DMHdNRGMxTFRSbU1tWXRZak5qTnkwMFpqVTJaRFExTldKa05UZGNJaXhjSW5abGNuUnBZMkZzWENJNlhDSkRiMjV6ZFcxbGNsd2lmU0lzSW5SNWNDSTZJbUZqWTJWemN5SjkuSGE2U3EyWkFrVHJYb21JWUVjWl9ZZVpxZ0h4RERqY0xQR1BndHFFSGQwWXg4WkMxVlltZW1aYkFxOF9tZ2J0dmJyMndQUm1yZEhHeWZSWlZkMlo5ZXc._6ZZkcPAhwPCiiH4iPJ9GU2o2GUX9ZAozfDu5yjIjl8; c_groot_access_token=GwZCQ5a0AIlHDsV1d0U_y2yfCY51KjFRxsDqpeCrSOMnoSzTTgKHpZWwRGumaBpO; c_groot_access_ts=2024-10-02T12:36:15Z; c_groot_refresh_token=80dY_xc6kwBkN9kW2qpe3OAL0jp0cjGOGYud1mCxmCIeYSFMqlUJ_J-lO0NT2IUU; _ga_123456789=GS1.1.1727872575.5.1.1727872777.0.0.1272969869; _hp2_id.2100373990=%7B%22userId%22%3A%226038982445977620%22%2C%22pageviewId%22%3A%222547683139655758%22%2C%22sessionId%22%3A%223841027956150538%22%2C%22identity%22%3A%2289706628-0075-4f2f-b3c7-4f56d455bd57%22%2C%22trackerVersion%22%3A%224.0%22%2C%22identityField%22%3Anull%2C%22isIdentified%22%3A1%7D',
  'priority': 'u=1, i',
  'referer': 'https://premium.pff.com/nfl/positions/2024/REGPO/receiving?position=WR',
  'sec-ch-ua': '"Chromium";v="128", "Not;A=Brand";v="24", "Google Chrome";v="128"',
  'sec-ch-ua-mobile': '?0',
  'sec-ch-ua-platform': '"macOS"',
  'sec-fetch-dest': 'empty',
  'sec-fetch-mode': 'cors',
  'sec-fetch-site': 'same-origin',
  'user-agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/128.0.0.0 Safari/537.36'
}




# COMMAND ----------

def scrape_pff_data(url, headers, years=None, weeks=None):
    # Initialize an empty DataFrame
    all_data = pd.DataFrame()

    # if years and weeks are not provided, download all seasons and weeks
    if years is None:
        years = range(2006, 2025)
    
    # Loop through each season and week
    for season in years:
        print(f"Starting to download {season} from {url}")
        if weeks is None:
            max_week = 18 if season >= 2021 else 17
            weeks = range(1, max_week + 1)

        for week in weeks:
            data = []
            params = {
                'league': 'nfl',
                'season': str(season),
                'week': str(week)
            }
            response = requests.get(url, headers=headers, params=params)
            
            if response.status_code == 200:
                response_json = json.loads(response.text)
                for key, value in response_json.items():
                    if key == 'restricted':
                        pass
                    else:
                        dataset_name = key
                        data = value
                if data:
                    df = pd.DataFrame(data)
                    df['league'] = params['league']
                    df['season'] = params['season']
                    df['week'] = params['week']
                    all_data = pd.concat([all_data, df], ignore_index=True)
            else:
                print(f"Failed to retrieve data for season {season}, week {week}, url {url}")
    return dataset_name, all_data

# COMMAND ----------

def save_pff_data(category, subcategory, years=None, weeks=None, mode="overwrite"):
  headers = get_pff_http_headers()
  url = f"https://premium.pff.com/api/v1/facet/{category}/{subcategory}"
  dataset_name, df = scrape_pff_data(url, headers, years, weeks)
  spark.createDataFrame(df).write.option("mergeSchema", "true").mode(mode).saveAsTable(f"pmracek.sports.bronze_pff_{dataset_name}_weekly")


stat_categories = {
  "passing":["summary","depth","pressure","concept","allowed_pressure"] # time_in_pocket
  ,"receiving":["summary","depth","concept","scheme"]
  # I stopped at 2023 Concept.  Need to pick up backfilling schemes + below.
  ,"rushing":["summary"]
  ,"offense":["blocking","pass_blocking","run_blocking"]
  ,"defense":["summary","pass_rush","run","coverage"]
  # ,"special teams"
}

stat_categories = {
 "defense":["pass_rush","run","coverage"]
  # ,"special teams"
}

years = range(2006, 2024)
weeks = None

for category, subcategories in stat_categories.items():
  for subcategory in subcategories:
    save_pff_data(category, subcategory, years, weeks, mode="append")


# COMMAND ----------

headers = get_pff_http_headers()
url = f"https://premium.pff.com/api/v1/facet/receiving/summary"
dataset_name, df = scrape_pff_data(url, headers, [2023], )

# COMMAND ----------

df

# COMMAND ----------

