from dashie_sampler import DashieSampler

import random
import collections
import os
import sys
import json
from datetime import datetime, timedelta
import html
from os.path import expanduser

import twitter
from config import tide_key, news_key, aws_mqtt_uri as aws_host, slz_twitter_oauth_token, slz_twitter_oauth_token_secret, slz_twitter_CONSUMER_KEY, slz_twitter_CONSUMER_SECRET, intrinio_username, intrinio_password

twit = twitter.Twitter(auth=twitter.OAuth(slz_twitter_oauth_token, slz_twitter_oauth_token_secret, slz_twitter_CONSUMER_KEY, slz_twitter_CONSUMER_SECRET))

home = expanduser('~')
#sys.path =  sys.path + [os.path.join(home,'sqlalchemy','lib')] + [os.path.join(home, 'twitter')] + [os.path.join(home, 'mylistmanager3')]
sys.path =  sys.path + [os.path.join(home, 'twitter')] + [os.path.join(home, 'mylistmanager3')]

from lmdb_p import Task, Context, remote_session, func

# all the imports below are related to accessing google calendar
import httplib2
from dateutil import parser
from apiclient import discovery
from oauth2client import client
from oauth2client import tools
from oauth2client.file import Storage

home_dir = os.path.expanduser('~')
credential_dir = os.path.join(home_dir, '.credentials')
credential_path = os.path.join(credential_dir, 'google-calendar.json')
store = Storage(credential_path)
credentials = store.get()

from config import aws_mqtt_uri as aws_host, exch_name, exch_pw, email
from pytz import timezone
from exchangelib import Account, EWSDateTime, credentials as exchange_credentials, errors as exchange_errors
from calendar import monthrange

cred = exchange_credentials.Credentials(username=exch_name, password=exch_pw)
account = Account(primary_smtp_address=email, credentials=cred, autodiscover=True, access_type=exchange_credentials.DELEGATE)
calendar = account.calendar
eastern = timezone('US/Eastern')

class SynergySampler(DashieSampler):
    def __init__(self, *args, **kwargs):
        DashieSampler.__init__(self, *args, **kwargs)
        self._last = 0

    def name(self):
        return 'synergy'

    def sample(self):
        s = {'value': random.randint(0, 100),
             'current': random.randint(0, 100),
             'last': self._last}
        self._last = s['current']
        return s

class BuzzwordsSampler(DashieSampler):
    def name(self):
        return 'buzzwords'

    def sample(self):
        my_little_pony_names = ['Rainbow Dash',
                                'Blossomforth',
                                'Derpy',
                                'Fluttershy',
                                'Lofty',
                                'Scootaloo',
                                'Skydancer']
        items = [{'label': pony_name, 'value': random.randint(0, 20)} for pony_name in my_little_pony_names]
        random.shuffle(items)
        return {'items':items}

class ConvergenceSampler(DashieSampler):
    def name(self):
        return 'convergence'

    def __init__(self, *args, **kwargs):
        self.seedX = 0
        self.items = collections.deque()
        DashieSampler.__init__(self, *args, **kwargs)

    def sample(self):
        self.items.append({'x': self.seedX,
                           'y': random.randint(0,20)})
        self.seedX += 1
        if len(self.items) > 10:
            self.items.popleft()
        return {'points': list(self.items)}

class CalendarSampler(DashieSampler):
    def name(self):
        return 'calendar'

    #def __init__(self, *args, **kwargs):
    #    DashieSampler.__init__(self, *args, **kwargs)

    def sample(self):
        http = credentials.authorize(httplib2.Http())
        service = discovery.build('calendar', 'v3', http=http)

        now = datetime.utcnow().isoformat() + 'Z' # 'Z' indicates UTC time
        print('Getting the upcoming 10 events')
        eventsResult = service.events().list(
            calendarId='primary', timeMin=now, maxResults=10, singleEvents=True,
            orderBy='startTime').execute()
        events = eventsResult.get('items', [])

        text = []

        if not events:
            text = ['No upcoming events found']
        for event in events:
            print("--------------------------------------------------------")
            start = event['start'].get('dateTime', event['start'].get('date'))
            start_dt = parser.parse(start)
            month = start_dt.strftime("%B")
            end = event['end'].get('dateTime', event['end'].get('date'))
            end_dt = parser.parse(end)
            summary = event.get('summary', "No summary") 
            if start_dt.hour == 0:
                item = '<span style="color:red">{} {} </span> {}'.format(month, str(start_dt.day), summary)
            else:
                item = '<span style="color:red">{} {} </span> <span style="color:green">{} - {}: </span>{}'.format(month, str(start_dt.day),
                                  start_dt.strftime("%-H:%M"), end_dt.strftime("%-H:%M"), summary)
            print(("\nItem =", summary))
            location = event.get('location')
            if location:
                item = "{} ({})".format(item, location)

            text.append({"label":item, "value":""})

        return({"items":text})

class IndustrySampler(DashieSampler):

    def name(self):
        return 'industry'

    def sample(self):

        task = remote_session.query(Task).join(Context).filter(Context.title=='industry', Task.star==True, Task.completed==None, Task.deleted==False).order_by(func.random()).first()
        if not task:
            return
        title = "[{}] {}".format(task.context.title.capitalize(), task.title)
        note = task.note if task.note else '' # would be nice to truncate on a word
        return {"text":note, "title":title}

class TwitterSampler(DashieSampler):

    def name(self):
        return 'twitter'

    def sample(self):
        try:
            z = twit.statuses.home_timeline()[:5]
        except twitter.api.TwitterHTTPError as e:
            print("Twitter exception: ",e)
            return
        #tweets = ["{} - {}".format(x['user']['screen_name'], html.unescape(x['text'].split('https')[0])) for x in z] #could just use ['user']['name']
        
        tweets = []
        for x in z:
            tweet = "{} - {}".format(x['user']['screen_name'], html.unescape(x['text'].split('https')[0]))
            try:
                tweet+=' <a href="{}" target="_blank">link</a>'.format(x['entities']['urls'][0]['url'])
            except:
                pass

            print("{}".format(x['text']))
            tweets.append({"label":tweet, "value":""})

        print(tweets)
        return({"items":tweets})

class OutlookSampler(DashieSampler):
    def name(self):
        return 'outlook'

    def sample(self):

        now = datetime.now()
        highlight_hour = False
        if now.weekday() == 4 and now.hour > 21: # note this include time_zone_offset, ie 17 + 4
            inc_days = 3
        elif now.weekday() > 4:
            inc_days = 7 - now.weekday()
        elif now.hour > 21:
            inc_days = 1
        else:
            inc_days = 0
            highlight_hour = True
      
        dt = now + timedelta(inc_days)
        print("dt =",dt)
        # below a problem at the end of the month
        #items = calendar.view(start=eastern.localize(EWSDateTime(now.year, now.month, now.day+next_)), end=eastern.localize(EWSDateTime(now.year, now.month, now.day+next_+1)))
        #below works
        #items = calendar.view(start=eastern.localize(EWSDateTime(now.year, now.month, now.day+next_)), end=eastern.localize(EWSDateTime(now.year, now.month, now.day+next_, now.hour+10)))

        #items = calendar.view(start=eastern.localize(EWSDateTime(now.year, now.month, now.day+next_), 1), end=eastern.localize(EWSDateTime(now.year, now.month, now.day+next_, 23)))
        items = calendar.view(start=eastern.localize(EWSDateTime(dt.year, dt.month, dt.day, 1)), end=eastern.localize(EWSDateTime(dt.year, dt.month, dt.day, 23)))

        try:
            len(items)
        except (exchange_errors.ErrorInternalServerTransientError, exchange_errors.ErrorMailboxStoreUnavailable) as e:
            print("exchangelib error: ", e)
            return
        except AttributeError as e:
            print("outlook error - would be caused by incorrect pw", e)
            return

        text = []
        try:
            for item in items:
                subject = item.subject
                if "time off" in subject.lower():
                    continue
                # after fall back hours = 5?
                line = (item.start-timedelta(hours=5)).strftime("%I:%M").lstrip('0')+"-"+(item.end-timedelta(hours=5)).strftime("%I:%M").lstrip('0')+" "+subject
                if "12:00-12:00" in line:
                    line = "All Day Event -"+line[11:]

                #if highlight_hour and (now.hour == item.start.hour - 4):
                if highlight_hour and (now.hour == item.start.hour):
                    line = "#{red}"+line
                text.append({"label":line, "value":""})
                print(line)
        except (exchange_errors.ErrorTimeoutExpired, exchange_errors.ErrorInternalServerTransientError) as e:
            print("exchangelib error: ", e)
            return

        if not text:
            text = [{"label":"Nothing Scheduled", "value":""}]



        return({"items":text})
