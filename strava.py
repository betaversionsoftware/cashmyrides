import requests
import datetime

class Strava():

    _ENDPOINT = "https://www.strava.com/api"
    _ATHLETE = "/v3/athlete"
    _ACTIVITIES = "/v3/activities/"
    
    _EXCHANGE_TOKEN = "https://www.strava.com/oauth/token"

    _SECRET = ""

    _ACCESS_TOKEN = None

    def _get_params(self):
        params = {}
        params["access_token"] = self._ACCESS_TOKEN
        return params

    def access_token(self, token):
        self._ACCESS_TOKEN = token

    def authorization_url(self, client_id, redirect_uri):
        url = "https://www.strava.com/oauth/authorize?approval_prompt=auto&redirect_uri=%s&response_type=code&client_id=%s" % (redirect_uri, client_id)
        return url

    def exchange_token(self, client_id, client_secret, code):
        payload = {}
        payload['client_id'] = client_id
        payload['client_secret'] = client_secret
        payload['code'] = code
        
        token = requests.post(self._EXCHANGE_TOKEN, data=payload).json()
        return token['access_token'], token['athlete']

    def get_athlete(self):
        params = self._get_params()
        url = "%s%s" % (self._ENDPOINT, self._ATHLETE)

        result = requests.get(url, params=params)
        if result.status_code == 200:
            return result.json()
        else:
            return None

    def get_activities(self, commutes_only=False, before=None, after=None, page=None, per_page=None):
        url = "%s%s" % (self._ENDPOINT, self._ACTIVITIES)

        params = self._get_params()
    
        if after:
            params["after"] = after
    
        if per_page:
            params["per_page"] = per_page
    
        if page:
            params["page"] = page

        result = requests.get(url, params=params)
        status_code = result.status_code
        if status_code == 200:
            return result.json()
        else:
            return None

if __name__ == "__main__":
    from pymongo import MongoClient

    mongodb = MongoClient("mongo")
    strava = mongodb.strava
    activity = strava.activities
    strava = Strava()
    strava.access_token("9dfbb892eb05ba342a27f77eca90d47c41cabaf5")

    FORMAT = '%Y%m%d%H%M%S'
    f = open("/app/datestamp.txt", "r+")
    line = f.readlines()

    if line and len(line) > 0:
        after_date = datetime.datetime.strptime(line[0].strip(), FORMAT).strftime("%s")
    else:
        after_date = datetime.datetime(2009,01,01,0,0).strftime("%s")

    index = 1
    count = 0
    while True:
        activities = strava.get_activities(after=after_date, page=index)
        for a in activities:
            if not activity.find_one({"id":a['id']}):
                activity.save(a)
        count += len(activities)
        index += 1
        if len(activities) < 30:
            break
    print count

    f.seek(0)
    f.truncate()
    f.write(datetime.datetime.now().strftime(FORMAT))
    f.close()
