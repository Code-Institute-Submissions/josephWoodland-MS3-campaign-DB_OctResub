from crypt import methods
import os
import profile
from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash

if os.path.exists("env.py"):
    import env

app = Flask(__name__)

app.config['MONGO_DBNAME'] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")

mongo  = PyMongo(app)


@app.route("/")
@app.route("/home")
def home():
    campaigns = list(mongo.db.campaigns.find())
    return render_template("home.html", campaigns=campaigns)


@app.route("/register", methods=["GET","POST"])
def register():
    return render_template("/register.html")
    

@app.route("/campaigns/<campaign_id>", methods=["GET","POST"])
def campaign_view(campaign_id):
    campaign = mongo.db.campaigns.find_one({"_id": ObjectId(campaign_id)})
    user_id = campaign.get("creator_id")
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    return render_template('campaign_view.html', campaign=campaign, user=user)


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
        port=int(os.environ.get("PORT")),
        debug=True) # Don't forget to change this to False!!!