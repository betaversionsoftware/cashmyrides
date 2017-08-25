import os
import json
import requests
import datetime
import calendar
import pycountry

import tornado.ioloop
import tornado.web

from strava import Strava
import utils

from pymongo import MongoClient

class BaseHandler(tornado.web.RequestHandler):

    def get_current_user(self):
        return self.get_secure_cookie("user")

    def get_current_token(self):
        user = self.get_secure_cookie("user")
        mongo = MongoClient('mongo')
        return mongo.strava.settings.find_one({"_id": self.get_secure_cookie("user")})["access_token"]


class MainHandler(BaseHandler):
    
    @tornado.web.authenticated
    def get(self):
        strava = Strava()
        strava.access_token(self.get_current_token())

        athlete = strava.get_athlete()
        if athlete['profile'].startswith("avatar"):
            athlete['profile'] = "/static/images/commuter_avatar.png"

        year = datetime.date.today().year
        month = datetime.date.today().month

        mongo = MongoClient('mongo')
        user_settings = mongo.strava.settings.find_one({"_id": self.get_current_user()})
        
        context = dict()        
        context['year'] = year
        context['month'] = calendar.month_name[month]
        context['days_left'] = utils.days_left()
        context['currencies'] = sorted(list(pycountry.currencies), key=lambda currency: currency.name)

        self.render("index.html", context=context, athlete=athlete, settings=user_settings)

    @tornado.web.authenticated
    def post(self):
        cost_per_commute = self.get_argument("cost-per-commute")
        currency = self.get_argument("currency")
        
        mongo = MongoClient('mongo')
        user_settings = mongo.strava.settings.find_one({"_id": self.get_current_user()})
        user_settings['cost_per_commute'] = cost_per_commute
        user_settings['currency'] = currency
        user_settings['settings_ok'] = True
        
        mongo.strava.settings.save(user_settings)
        
        self.redirect("/")

            
class StatsHandler(BaseHandler):

    def get(self):
        if not self.get_current_user():
            raise tornado.web.HTTPError(401, "Access denied")
    
        year = datetime.date.today().year
        month = datetime.date.today().month
        after = datetime.datetime(year, month, 01, 0, 0).strftime("%s")
        
        mongo = MongoClient("mongo")
        user_settings = mongo.strava.settings.find_one({"_id": self.get_current_user()})

        strava = Strava()
        strava.access_token(self.get_current_token())

        athlete = strava.get_athlete()
        activities = strava.get_activities(per_page=200, after=after)

        results = dict()
        results["count"] = 0
        results["count_total"] = len(activities)
        results["kudos"] = 0
        results["achievement"] = 0
        for r in activities:
            if r['type'] == 'Ride' and r['commute']:
                results["count"] = results.get("count", 0) + 1
                results["distance"] = results.get("distance", 0) + r["distance"]
                results["kudos"] = results.get("kudos", 0) + r['kudos_count']
                results["achievement"] = results.get("achievement", 0) + r['achievement_count']
                results["moving_time"] = results.get("moving_time", 0) + r['moving_time']
                results["elevation"] = results.get("elevation", 0) + r['total_elevation_gain']
                
        results['money_saved'] = "%s %.2f" % (user_settings.get("currency", "USD"), (results.get("count", 0) * float(user_settings["cost_per_commute"])))
        results["distance"] = "%.2f" % round(utils.distance(athlete['measurement_preference'], results.get("distance", 0)) / 1000, 2)
        results["elevation"] = utils.elevation(athlete['measurement_preference'], results.get("elevation", 0))
        results["moving_time"] = utils.moving_time(results.get("moving_time", 0))
        results["commutes_percentage"] = utils.commutes_percentage(results["count"], results["count_total"])
        
        self.write(json.dumps(results))


class DoneHandler(tornado.web.RequestHandler):
    def get(self):
        strava = Strava()
        mongo = MongoClient('mongo')
        
        strava_client_secret = os.environ.get('STRAVA_CLIENT_SECRET')
        strava_client_id= os.environ.get('STRAVA_CLIENT_ID')
        
        code = self.get_argument("code")
        access_token, athlete = strava.exchange_token(client_id=strava_client_id, client_secret=strava_client_secret, code=code)
        
        user = mongo.strava.settings.find_one({"_id": athlete['email']})
        if user:
            mongo.strava.settings.update({"_id": athlete['email']}, {"$set": { "access_token": access_token} })
        else:
            mongo.strava.settings.save({
                "_id": athlete['email'],
                "access_token": access_token,
                "settings_ok": False,
                "cost_per_commute": 0,
                "currency": "USD"
            })

        self.set_secure_cookie("user", athlete['email'])
        self.redirect("/")


class LogoutHandler(BaseHandler):
    def get(self):
        if self.get_current_user():
            self.clear_cookie("user")
            self.redirect("/")


class LoginHandler(BaseHandler):
    def get(self):
        strava_client_id= os.environ.get('STRAVA_CLIENT_ID')
        strava = Strava()
        authorize_url = strava.authorization_url(client_id=strava_client_id, redirect_uri='https://www.cashmyrides.com/done')
        self.render("index.html", authorize_url=authorize_url)


def make_app():
    
    settings = {
        "cookie_secret": "wet$%C@#$tr235@#$TV%23",
        "debug": True,
        "template_path": "templates",
        "static_path": os.path.join(os.path.dirname(__file__), "static"),
        "login_url": "/login"
    }
    
    return tornado.web.Application([
        (r"/", MainHandler),
        (r"/api/v1/stats", StatsHandler),
        (r"/done", DoneHandler),
        (r"/login", LoginHandler),
        (r"/logout", LogoutHandler)
    ], **settings)

if __name__ == "__main__":
    app = make_app()
    app.listen(8082)
    tornado.ioloop.IOLoop.current().start()
