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


@app.route("signin")
def signin():
    return render_template("signin.html")

@app.route("/register", methods=["GET","POST"])
def register():
    if request.method == "POST":
        email_check = mongo.db.users.find_one(
            {"email": request.form.get("email").lower()})
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        # check if email is already in use
        if email_check:
            flash("Email already in use, please log in.")
            return redirect(url_for("register"))

        # check if the passwords match
        if password != confirm_password:
            flash("Passwords do not match!")
            return redirect(url_for("register"))
        # add the form details to a dictionary
        register = {
            "first_name": request.form.get('first_name'),
            "last_name": request.form.get('last_name'),
            "password": generate_password_hash(password),
            "email": email.lower(),
        }
        mongo.db.users.insert_one(register)

        # add user to a session
        session["user"] = email
        flash('Registered Welcome to the app!!')
        
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