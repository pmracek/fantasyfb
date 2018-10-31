
# coding: utf-8

# In[59]:


import matplotlib
matplotlib.use('Agg')

import matplotlib.pyplot as plt
import matplotlib.dates as md
import pandas as pd
import numpy as np
from pandas.io.json import json_normalize
from datetime import datetime,date,timedelta
import boto3
import pytz 
from bs4 import BeautifulSoup
import requests
import io

params = {
'token' : 'jgyuNE4NXwPdjzmQS568me3TyXLAL9ZCU9NkVlKj'
#,'bot_id' : 'da0beb9ba4b78d5a57a2ed6dd4' #EC
,'bot_id' :'4e93908dd6e03b66cbd07fc458' #Test
}

dynamodb = boto3.resource('dynamodb')
table = dynamodb.Table('MatchupGameFlow')

leagueId = '111414'
season = datetime.now().astimezone(pytz.timezone('US/Eastern')).year

r = requests.get('http://www.nfl.com/liveupdate/scorestrip/ss.xml')
schedxml = BeautifulSoup(r.text, "html.parser")
week = schedxml.find('gms')['w']

def _is_nfl_game_active():
    r = requests.get('http://www.nfl.com/liveupdate/scorestrip/ss.xml')
    schedxml = BeautifulSoup(r.text, "html.parser")
    active = False
    for info in schedxml.findAll('g'):        
        gamestatus = info['q']
        if(gamestatus != 'F'  and gamestatus != 'FO' and gamestatus != 'P'):
            active = True  
            break
        
    return active # return active


# In[60]:


def _last_game_ended_recently():
    r = requests.get('http://www.nfl.com/liveupdate/scorestrip/ss.xml')
    schedxml = BeautifulSoup(r.text, "html.parser")

    last_game_end_utc_ts = pytz.utc.localize(datetime(2000, 1, 1, 0, 0))

    for info in schedxml.findAll('g'):
        hour, minute = info['t'].strip().split(':')
        d = datetime(int(info['eid'][:4]), int(info['eid'][4:6]), int(info['eid'][6:8]),
                              (int(hour) + 12) % 24, int(minute)).astimezone(pytz.timezone('US/Eastern'))
        if(d.hour == 21 and d.minute == 30): #Saturday 9:30am games need to be adjusted from PM to AM
            d = d - timedelta(hours=12)
        
        d = d.astimezone(pytz.timezone('UTC')) #convert to UTC for AWS Lambda environment
        
        current_utc_ts = pytz.utc.localize(datetime.utcnow())

        if(current_utc_ts.date()==d.date()): 
            last_game_end_utc_ts = d + timedelta(hours=4.5)

    return current_utc_ts<=last_game_end_utc_ts


# In[61]:


def generate_charts():
    data = table.scan()

    df = json_normalize(data, 'Items')[['COLLECTTIMESTAMP','TEAM1','TEAM1NAME','TEAM1PTS','TEAM1PROJ','TEAM2NAME','TEAM2PTS','TEAM2PROJ','SCORINGPERIOD']]
    df = df[df['SCORINGPERIOD']==week].sort_values('COLLECTTIMESTAMP', ascending=True)
    #df[['COLLECTTIMESTAMP']] = df[['COLLECTTIMESTAMP']].apply(pd.to_datetime)
    df[['TEAM1PTS','TEAM1PROJ','TEAM2PTS','TEAM2PROJ']] = df[['TEAM1PTS','TEAM1PROJ','TEAM2PTS','TEAM2PROJ']].apply(pd.to_numeric)


    imgs = []
    for home_team in df['TEAM1NAME'].unique():
        matchup = df[df['TEAM1NAME']==home_team]
        team1 = matchup['TEAM1NAME'].unique()[0]
        team2 = matchup['TEAM2NAME'].unique()[0]

        fig, ax = plt.subplots(1,1)

        plt.title(team1+' vs. '+team2+'\nWeek '+week)
        #ax.xaxis.set_minor_locator(md.HourLocator(interval=4))   # every 4 hours
        #ax.xaxis.set_minor_formatter(md.DateFormatter('%H:%M'))  # hours and minutes
        #ax.xaxis.set_major_locator(md.HourLocator(interval=12))    # every day
        #ax.xaxis.set_major_formatter(md.DateFormatter('\n%a'))
        #ax.set_xlim(datetime(2018, 10, 1, 20), datetime(2018, 10, 2 , 0))
        ax.xaxis.set_major_locator(plt.NullLocator())
        
        line_t1pts, = ax.plot(matchup['COLLECTTIMESTAMP'], matchup['TEAM1PTS'], 'r', label=matchup['TEAM1NAME'].unique()[0]+' PTS')
        line_t1proj, = ax.plot(matchup['COLLECTTIMESTAMP'], matchup['TEAM1PROJ'], 'r',linestyle='--', dashes=(2, 2), label=matchup['TEAM1NAME'].unique()[0]+' PROJ')
        line_t2pts, = ax.plot(matchup['COLLECTTIMESTAMP'], matchup['TEAM2PTS'], 'b', label=matchup['TEAM2NAME'].unique()[0]+' PTS')
        line_t2proj, = ax.plot(matchup['COLLECTTIMESTAMP'], matchup['TEAM2PROJ'], 'b',linestyle='--', dashes=(2, 2), label=matchup['TEAM2NAME'].unique()[0]+' PROJ')
        ax.legend(loc='best')

        buf = io.BytesIO()
        plt.savefig(buf, format='png')
        buf.seek(0)
        imgs.append(buf)
        #plt.show()
        plt.close()
    return imgs



# In[62]:


def post_to_groupme(input, imgs):
    headers_img = {
        'X-Access-Token': input['token'],
        'Content-Type': 'image/jpeg',
    }

    headers_post = {
        'Content-Type': 'application/json',
    }

    for img in imgs:
        img.seek(0)
        img = requests.post('https://image.groupme.com/pictures', headers=headers_img, data=img)
        imgurl = img.json()['payload']['picture_url']
        data = '{"bot_id":"'+input['bot_id']+'","text":"","attachments":[{"type":"image","url":"'+imgurl+'"}]}'
        response = requests.post('https://api.groupme.com/v3/bots/post', headers=headers_post, data=data)



# In[63]:


def lambda_handler(input,context):
    if not _is_nfl_game_active() and not _last_game_ended_recently():
        return False
    
    post_to_groupme(input, generate_charts())
    return True

lambda_handler(params,None)


# In[ ]:








# In[ ]:


fig, ax = plt.subplots(1,1)

plt.title(team1+' vs. '+team2+'\nWeek '+week)
#ax.xaxis.set_minor_locator(md.HourLocator(interval=4))   # every 4 hours
#ax.xaxis.set_minor_formatter(md.DateFormatter('%H:%M'))  # hours and minutes
#ax.xaxis.set_major_locator(md.HourLocator(interval=12))    # every day
#ax.xaxis.set_major_formatter(md.DateFormatter('\n%a'))

#ax.set_xticks(matchup['COLLECTTIMESTAMP'])

#ax.set_xticklabels(matchup['COLLECTTIMESTAMP'], rotation=45, horizontalalignment='right')
#x = np.arange(4)
#ax.set_xticks(x, ('Bill', 'Fred', 'Mary', 'Sue'))

#ax.set_xlim(datetime(2018, 9, 30, 12), datetime(2018, 10, 2 , 0))

#ax.set_xticks(matchup['COLLECTTIMESTAMP'].values)
#ax.set_xticklabels(matchup['COLLECTTIMESTAMP'].values, rotation=45, horizontalalignment='right')

line_t1pts, = ax.plot(matchup['COLLECTTIMESTAMP'], matchup['TEAM1PTS'], 'r', label=matchup['TEAM1NAME'].unique()[0]+' PTS')
line_t1proj, = ax.plot(matchup['COLLECTTIMESTAMP'], matchup['TEAM1PROJ'], 'r',linestyle='--', dashes=(2, 2), label=matchup['TEAM1NAME'].unique()[0]+' PROJ')
line_t2pts, = ax.plot(matchup['COLLECTTIMESTAMP'], matchup['TEAM2PTS'], 'b', label=matchup['TEAM2NAME'].unique()[0]+' PTS')
line_t2proj, = ax.plot(matchup['COLLECTTIMESTAMP'], matchup['TEAM2PROJ'], 'b',linestyle='--', dashes=(2, 2), label=matchup['TEAM2NAME'].unique()[0]+' PROJ')
ax.legend(loc='best')
ax.xaxis.set_major_locator(plt.NullLocator())
#ax.xaxis.set_major_formatter(plt.NullFormatter())

#plt.savefig(buf, format='png')
plt.show()
plt.close()


# In[ ]:




every_nth = 4
for label in enumerate(ax.get_xticks(minor=True)):
    print(label)
    #if n % every_nth != 0:
    #    label.set_visible(False)


# In[ ]:


fig, ax = plt.subplots(1,1)

plt.title(team1+' vs. '+team2+'\nWeek '+week)
#ax.xaxis.set_minor_locator(md.HourLocator(interval=4))   # every 4 hours
#ax.xaxis.set_minor_formatter(md.DateFormatter('%H:%M'))  # hours and minutes
#ax.xaxis.set_major_locator(md.HourLocator(interval=12))    # every day
#ax.xaxis.set_major_formatter(md.DateFormatter('\n%a'))

#ax.set_xticks(matchup['COLLECTTIMESTAMP'])

#ax.set_xticklabels(matchup['COLLECTTIMESTAMP'], rotation=45, horizontalalignment='right')
#x = np.arange(4)
#ax.set_xticks(x, ('Bill', 'Fred', 'Mary', 'Sue'))

#ax.set_xlim(datetime(2018, 9, 30, 12), datetime(2018, 10, 2 , 0))

#ax.set_xticks(matchup['COLLECTTIMESTAMP'].values)
#ax.set_xticklabels(matchup['COLLECTTIMESTAMP'].values, rotation=45, horizontalalignment='right')

line_t1pts, = ax.plot(matchup['COLLECTTIMESTAMP'], matchup['TEAM1PTS'], 'r', label=matchup['TEAM1NAME'].unique()[0]+' PTS')
line_t1proj, = ax.plot(matchup['COLLECTTIMESTAMP'], matchup['TEAM1PROJ'], 'r',linestyle='--', dashes=(2, 2), label=matchup['TEAM1NAME'].unique()[0]+' PROJ')
line_t2pts, = ax.plot(matchup['COLLECTTIMESTAMP'], matchup['TEAM2PTS'], 'b', label=matchup['TEAM2NAME'].unique()[0]+' PTS')
line_t2proj, = ax.plot(matchup['COLLECTTIMESTAMP'], matchup['TEAM2PROJ'], 'b',linestyle='--', dashes=(2, 2), label=matchup['TEAM2NAME'].unique()[0]+' PROJ')
ax.legend(loc='best')
ax.xaxis.set_major_locator(plt.NullLocator())
#ax.xaxis.set_major_formatter(plt.NullFormatter())

#plt.savefig(buf, format='png')
plt.show()
plt.close()


# In[ ]:


#this example from here
#https://stackoverflow.com/questions/5656798/python-matplotlib-is-there-a-way-to-make-a-discontinuous-axis/5669301#5669301

#another interesting example using index formatter
#https://matplotlib.org/examples/api/date_index_formatter.html

#check out Jackarow function formatter
#https://www.reddit.com/r/learnpython/comments/4lh841/matplotlib_how_to_avoid_displaying_xaxis_entries/

import matplotlib.pyplot as plt
import numpy as np

# If you're not familiar with np.r_, don't worry too much about this. It's just 
# a series with points from 0 to 1 spaced at 0.1, and 9 to 10 with the same spacing.
x = np.r_[0:1:0.1, 9:10:0.1]
y = np.sin(x)

fig,(ax,ax2) = plt.subplots(1, 2, sharey=True)

# plot the same data on both axes
ax.plot(x, y, 'bo')
ax2.plot(x, y, 'bo')

# zoom-in / limit the view to different portions of the data
ax.set_xlim(0,1) # most of the data
ax2.set_xlim(9,10) # outliers only

# hide the spines between ax and ax2
ax.spines['right'].set_visible(False)
ax2.spines['left'].set_visible(False)
ax.yaxis.tick_left()
ax.tick_params(labeltop='off') # don't put tick labels at the top
ax2.yaxis.tick_right()

# Make the spacing between the two axes a bit smaller
plt.subplots_adjust(wspace=.1)

# This looks pretty good, and was fairly painless, but you can get that
# cut-out diagonal lines look with just a bit more work. The important
# thing to know here is that in axes coordinates, which are always
# between 0-1, spine endpoints are at these locations (0,0), (0,1),
# (1,0), and (1,1). Thus, we just need to put the diagonals in the
# appropriate corners of each of our axes, and so long as we use the
# right transform and disable clipping.

d = .01 # how big to make the diagonal lines in axes coordinates
# arguments to pass plot, just so we don't keep repeating them
#kwargs = dict(transform=ax.transAxes, color='k', clip_on=False)
#ax.plot((1-d,1+d),(-d,+d), **kwargs) # top-left diagonal
#ax.plot((1-d,1+d),(1-d,1+d), **kwargs) # bottom-left diagonal

kwargs.update(transform=ax2.transAxes) # switch to the bottom axes
ax2.plot((-d,d),(-d,+d), **kwargs) # top-right diagonal
ax2.plot((-d,d),(1-d,1+d), **kwargs) # bottom-right diagonal

# What's cool about this is that now if we vary the distance between
# ax and ax2 via f.subplots_adjust(hspace=...) or plt.subplot_tool(),
# the diagonal lines will move accordingly, and stay right at the tips
# of the spines they are 'breaking'

plt.show()

