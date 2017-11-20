# fantasyfb


#### Data Files follow this naming convention: **season**\_**week**\_**filetype**.txt

  * **matchup_recap** One line per team per week with team score, opponents score, and outcome
    + SEASON
    + SCORINGPERIOD
    + WEEK_NM
    + TEAM
    + TEAMNAME
    + SCORE
    + OPPONENT
    + OPPONENTNAME
    + OPPONENTSCORE
    + OUTCOME
  
  * **quickbox**  Only 2017 data has details on individual bench scores.  PlayerID for 2012-2015 quickbox is not populated as ESPN did not keep this data around.  2016  
    + SEASON
    + SCORINGPERIOD
    + WEEK_NM
    + TEAM
    + TEAMNAME
    + SLOT
    + PLAYERID
    + PLAYERNAME
    + PLAYEROPP
    + GAMEOUTCOME
    + PLAYERPOINTS
    + STARTERPOINTS
    + BENCHPOINTS
    
  * **faab_report** One line per bid.  Multiple auction days rolled into 1 file per week.
    + SEASON
    + SCORINGPERIOD
    + WEEK_NM
    + AUCTIONDATE
    + TEAM
    + TEAMNAME
    + PLAYERID
    + PLAYERNAME
    + BID
    + BIDRESULT
  
