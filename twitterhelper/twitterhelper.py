from flask import Flask
from flask.ext.mail import Mail
from datetime import datetime
from flask_mail import Message
from crossdomain import crossdomain
from datetime import time
import pytz
import urllib2, base64
import credentials, json
import os.path
import sqlite3
from flask import g, jsonify
from flask.ext.cors import CORS


TWITTER_APIKEY=credentials.twitterapikey
TWITTER_APISECRET=credentials.twitterapisecret
TWITTER_BEARERTOKEN=credentials.twitterbearertoken

TRIMET_APPID=credentials.trimetappid

MAIL_SERVER = credentials.MAIL_SERVER
MAIL_PORT = credentials.MAIL_PORT
MAIL_USE_TLS = credentials.MAIL_USE_TLS
MAIL_USE_SSL =  credentials.MAIL_USE_SSL
MAIL_USERNAME = credentials.MAIL_USERNAME
MAIL_PASSWORD = credentials.MAIL_PASSWORD

app = Flask(__name__)
app.config.from_object(__name__)
mail = Mail(app)
cors = CORS(app, resources={r"/getdashboard": {"origins": "*"}},
            headers="Content-Type")


DATABASE = '/var/www/trimethelper/resources/trimet.db'


@app.route('/')
def hello():
    return "This server is a service. Please use the right path"


# http://developer.trimet.org/ws_docs/arrivals2_ws.shtml
# functions for /getdashboard
@app.route('/getdashboard')
def getdashboard():
    locationids = '1003,1114,9978,10168,9833,9834,8381'
    url = 'http://developer.trimet.org/ws/v2/arrivals?locIDs=' + locationids + '&json=true&appID=' + TRIMET_APPID
    req = urllib2.Request(url)
    response = urllib2.urlopen(req)
    data = response.read()
    p_arrivals = getArrivals(json.loads(data)['resultSet']['arrival'])
    p_detours = getDetours(json.loads(data)['resultSet']['detour'])
    p_locations = getLocations(json.loads(data)['resultSet']['location'])
    return jsonify(arrivals=p_arrivals,detours=p_detours,locations=p_locations)

def getArrivals(arrivals):
    filtered = dict()
    for arrival in arrivals:
        locid = arrival['locid']        
        if(not filtered.has_key(locid)):
            filtered[locid] = list()
        filtered[locid].append(arrival)
    return filtered

def getDetours(detours):
    processedDetours = dict()
    for detour in detours:
	d_id = detour['id']
	desc = detour['desc']
	processedDetours[d_id] = desc
    return processedDetours


def getLocations(locations):
    processedLocs = dict()
    for loc in locations:
        l_id = loc['id']
        desc = loc['desc']
        processedLocs[l_id] = desc
    return processedLocs



# functions for /checktrimetstatus
# https://dev.twitter.com/docs/auth/application-only-auth
@app.route("/checktrimetstatus")
def checktrimetstatus():
    bearerToken = getBearerToken()
    authorization = 'Bearer ' + bearerToken
    headers = {'Authorization':authorization}
    url = 'https://api.twitter.com/1.1/statuses/user_timeline.json?screen_name=trimet'
    req = urllib2.Request(url, None, headers)
    response = urllib2.urlopen(req)
    data = response.read()   
    problems =  checkForProblems(data)
    
    if(len(problems) > 0):
        problemsStr = str('<br/>'.join(problems))
        if(problemsNew(problemsStr)):
            query_db('delete from TRIMET_PROBLEMS', [], one=True)
            query_db("insert into TRIMET_PROBLEMS(PROBLEMS) values(?)" , [problemsStr], one=True)
            sendEmail(problemsStr)
            return problemsStr
        return "No new problems"
    else:
        return "No new problems"
    


def checkForProblems(data):
    tweetsJSON = json.loads(data)
    problems = []
    delayFound = False;
    # https://docs.python.org/2/library/datetime.html#strftime-and-strptime-behavior
    datefmt = '%I:%M %p'
    for tweet in tweetsJSON:
        text = tweet['text']
        created_at_utc  = pytz.utc.localize(datetime.strptime(tweet['created_at'].replace('+0000 ',''), '%a %b %d %H:%M:%S %Y'))
        created_at = created_at_utc.replace(tzinfo=pytz.utc).astimezone(pytz.timezone('US/Pacific'))
        now = datetime.now(pytz.timezone('US/Pacific'))
        diff_seconds = (now - created_at).total_seconds()
        # difference is less than 2 hours
        if(diff_seconds < 7200):
            if(text.find('closed') != -1 or text.find('delayed') != -1 or text.find('disrupted') != -1):
                problems.append('At '  + created_at.strftime(datefmt) +  ', ' + text)
    return problems;


def problemsNew(problemsStr):
    problemsFromDB = query_db('select PROBLEMS from TRIMET_PROBLEMS where ID = ?', [1], one=True)
    if problemsFromDB is None:
        return True
    return problemsStr != problemsFromDB[0]


def sendEmail(problemsStr):
    msg = Message("Trimet problems", sender=MAIL_USERNAME, recipients=["athreya86@gmail.com"])
    msg.html = problemsStr
    mail.send(msg)


def getBearerToken():
    return TWITTER_BEARERTOKEN


# bearer tokens don't change for now - but they may change in the future
def getBearerTokenFromTwitter():
    # construct header first
    basic = base64.b64encode(urllib.quote_plus(TWITTER_APIKEY) + ':' + urllib.quote_plus(TWITTER_APISECRET))
    authorization = 'Basic ' + basic
    contentType = 'application/x-www-form-urlencoded;charset=UTF-8'
    headers = {'Authorization':authorization, 'Content-Type':contentType}
    # body then and make request
    body = 'grant_type=client_credentials'
    url = 'https://api.twitter.com/oauth2/token'
    req = urllib2.Request(url, body, headers)
    response = urllib2.urlopen(req)
    tokenJSON = json.loads(response.read())
    return tokenJSON['access_token']

### database stuff
def query_db(query, args=(), one=False):
    cur = get_db().execute(query, args)
    rv = cur.fetchall()
    get_db().commit()
    cur.close()
    return (rv[0] if rv else None) if one else rv

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(DATABASE)
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()


if __name__ == "__main__":
    app.run()
