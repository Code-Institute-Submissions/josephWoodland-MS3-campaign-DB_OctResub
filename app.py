import os

from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for, g)
from flask_pymongo import PyMongo, pymongo
from bson.objectid import ObjectId
from werkzeug.security import (
    generate_password_hash, check_password_hash)
from datetime import datetime
from operator import itemgetter


if os.path.exists("env.py"):
    import env


app = Flask(__name__)

app.config['MONGO_DBNAME'] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024


mongo  = PyMongo(app)


def create_transaction(user_from_id, user_to_id,
 campaign_id, amount):

    campaign = mongo.db.campaigns.find_one(
        { "_id": ObjectId(campaign_id) })
    user_to = mongo.db.users.find_one(
        { "_id": ObjectId(user_to_id) })
    user_from = mongo.db.users.find_one(
        { "_id": ObjectId(user_from_id) })
    time = datetime.now().isoformat(' ', 'seconds')

    new_transaction = {
        "user_to": user_to['first_name'] + ' ' + user_to['last_name'],
        "user_from": user_from['first_name'] + ' ' + user_from['last_name'],
        "campaign": campaign['name'],
        "amount": amount,
        "transaction_time": time,
        "user_to_id": str(user_to_id),
        "user_from_id": str(user_from_id)
    }
    mongo.db.transactions.insert_one(new_transaction)


@app.errorhandler(413)
def file_to_large(err):

    flash('File is too large! Max size 5MB')
    return redirect(request.referrer)


#Function to assing the user when a request is made
@app.before_request
def before_request_func():

    try:
        if session['user']:
            user = mongo.db.users.find_one_or_404(
            { "email": session.get('user') })
    
            g.user = user

            return 
        
    except KeyError:
        return


# Route for images
@app.route("/images/<filename>")
def file(filename):

    return mongo.send_file(filename)


@app.route("/")
@app.route("/home")
def home():

    campaign = mongo.db.campaigns

    campaigns = list(campaign.find().sort('time_created', pymongo.ASCENDING).limit(4))
    overfunded = list(campaign.find({ "percentage_complete":{ '$gt': 100}} ).limit(4))

    try:
        if session['user']:
            user = mongo.db.users.find_one_or_404({ "email": session['user'] })
        
        return render_template("home.html", campaigns=campaigns, user=user, overfunded=overfunded)
    except KeyError:

        return render_template("home.html", campaigns=campaigns, overfunded=overfunded)


@app.route("/signin", methods=["GET","POST"])
def signin():

    if request.method == "POST":
        user = mongo.db.users.find_one(
            {"email": request.form.get("email".lower())}
        )

        if user:

            if check_password_hash(
                user["password"], request.form.get(
                    "password")):
                    session['user'] = request.form.get(
                        'email').lower()
                    name = user["first_name"].capitalize()
                    
                    flash(f"Welcome, {name}")
                    return redirect( url_for(
                        "profile", user=session["user"]))
                 
            flash("Incorrect password")
            return render_template("signin.html")
        
        flash("Incorrect email, please try again or sign up")
    return render_template("signin.html")


@app.route("/register", methods=["GET","POST"])
def register():

    if request.method == "POST":
        email_check = mongo.db.users.find_one(
            {"email": request.form.get("email").lower()})
        email = request.form.get("email")
        password = request.form.get("password")
        confirm_password = request.form.get("confirm_password")

        if 'profile_image' in request.files:
            profile_image = request.files["profile_image"]
            mongo.save_file(profile_image.filename, profile_image)
            
        if email_check:
            flash("Email already in use, please log in.")
            return redirect(url_for("register"))

        if password != confirm_password:
            flash("Passwords do not match!")
            return redirect(url_for("register"))
        
        register = {
            "first_name": request.form.get(
                'first_name').lower().capitalize(),
            "last_name": request.form.get(
                'last_name').lower().capitalize(),
            "password": generate_password_hash(password),
            "profile_image_name": profile_image.filename,
            "email": email.lower(),
            "credits": 0,
        }
        mongo.db.users.insert_one(register)

        session["user"] = email

        flash('Registered Welcome to the app!!')
        return redirect( url_for("profile", user=session["user"]))
    
    return render_template("register.html")
    

@app.route("/campaigns/<campaign_id>", methods=["GET","POST"])
def campaign_view(campaign_id):
    
    campaign = mongo.db.campaigns.find_one({ "_id": ObjectId(campaign_id) })
    user_id = campaign.get("creator_id")
    user = mongo.db.users.find_one({ "_id": ObjectId(user_id) })
    
    return render_template(
        'campaign_view.html', campaign=campaign, user=user)


@app.route("/user_campaign/<campaign_id>", methods=["GET","POST"])
def user_campaign(campaign_id):

    campaign = mongo.db.campaigns.find_one(
        {"_id": ObjectId(campaign_id)})
    user_id = campaign.get("creator_id")
    user = mongo.db.users.find_one({"_id": ObjectId(user_id)})
    
    return render_template('user_campaign.html',
     campaign=campaign, user=user) 


@app.route("/campaigns")
def campaigns():
        
    campaigns = list(mongo.db.campaigns.find())

    return render_template('campaigns.html', campaigns=campaigns, user=g.user)


@app.route('/search', methods=["GET", "POST"])
def search():

    search = request.form.get("search")

    campaigns = list(mongo.db.campaigns.find({"$text": {"$search": search }}))

    return render_template('campaigns.html', campaigns=campaigns, user=g.user)


@app.route("/profile")
def profile():

    if session['user']:
        return render_template("profile.html", user=g.user)
    
    return redirect(url_for("signin", user=g.user))


@app.route('/logout')
def logout():

    flash("Your have been logged out")
    session.pop("user")

    return redirect( url_for("home"))


@app.route("/update_credits", methods=["GET","POST"])
def add_credits():
    
    if request.method == "POST":
        
        amount = int(request.form.get("add_credits"))
        credits = g.user["credits"]
        new_total = credits + amount
        mongo.db.users.update_one(
            { "email": session['user'] }, {"$set":{"credits": new_total}})
        flash(f"You added {amount}, credits")

        return redirect(url_for("profile", user=g.user))

    return redirect(url_for("profile", user=g.user))


@app.route("/user_campaigns")
def user_campaigns():

    user = g.user
    user_id = str(user["_id"])
    campaigns = list(mongo.db.campaigns.find(
         { "creator_id" : user_id } ))

    return render_template('user_campaigns.html',
     user=user, campaigns=campaigns)


@app.route("/create_campaign", methods=["GET","POST"])
def create_campaign():

    if request.method == "POST":
        user = mongo.db.users.find_one(
            { "email": session['user'] })
        user_id = str(user["_id"])
        time = datetime.now().isoformat(' ', 'seconds')

        if 'image' in request.files:
            image = request.files["image"]
            mongo.save_file(image.filename, image)

        new_campaign = {
            "name": request.form.get("name"),
            "description":request.form.get("description"),
            "target_amount":request.form.get("target"),
            "current_amount": 0,
            "campaign_image_name": image.filename,
            "percentage_complete": 0,
            "time_created": time,
            "creator_id": user_id,
        }

        mongo.db.campaigns.insert_one(new_campaign)
        flash('You have added a new campaign')
        campaigns = list(mongo.db.campaigns.find(
             { "creator_id" : user_id } ))
        return render_template('user_campaigns.html',
         user=user, campaigns=campaigns)

    return render_template("create_campaign.html", user=g.user)


@app.route("/edit_campaign/<campaign_id>", methods=["GET", "POST"])
def edit_campaign(campaign_id):

    campaign = mongo.db.campaigns.find_one(
        { "_id": ObjectId(campaign_id) })

    if request.method == "POST":
        user = mongo.db.users.find_one(
            { "email": session['user'] })
        user_id = str(user["_id"])
        update_campaign = {
            "name": request.form.get("name"),
            "description":request.form.get("description"),
            "target_amount":request.form.get("target"),
            "current_amount": request.form.get("current_amount"),
            "percentage_complete": request.form.get("percentage_complete"),
            "creator_id": user_id,
        }

        mongo.db.campaigns.update(
            { "_id": ObjectId(campaign_id) },update_campaign)
        flash("You have edited the campaign")
        campaigns = list(mongo.db.campaigns.find(
             { "creator_id" : user_id } ))
        return render_template(
            'user_campaigns.html', user=user,
             campaigns=campaigns)

    return render_template("edit_campaign.html",
     campaign=campaign, user=g.user)


@app.route("/collect_campaign/<campaign_id>")
def collect_campaign(campaign_id):

    user = mongo.db.users.find_one(
        { "email": session['user'] })
    campaign = mongo.db.campaigns.find_one(
        { "_id": ObjectId(campaign_id) })
    current_user_credits = user["credits"]
    campaign_credits = campaign['current_amount']

    if campaign_credits == int:
        new_total = int(current_user_credits) + int(campaign_credits)
        mongo.db.users.update_one(
            { "email": session['user'] },
            { "$set":{"credits": new_total } })
        campaign = mongo.db.campaigns.update_one(
            { "_id": ObjectId(campaign_id) },
            { "$set":{"current_amount": 0 } })

        flash("You have debited the campign amount into your account")

        return redirect(url_for("profile", user=user)) 
    else:

        flash("You did not take any credits from this campaign")

        return redirect(url_for("profile", user=user)) 


@app.route("/delete_campaign/<campaign_id>")
def delete_campaign(campaign_id):

    user = mongo.db.users.find_one(
        { "email": session['user'] })
    campaign = mongo.db.campaigns.find_one(
        { "_id": ObjectId(campaign_id) })
    current_user_credits = user["credits"]
    campaign_credits = campaign['current_amount']

    if campaign_credits == int:
        new_total = int(current_user_credits) + int(campaign_credits)
        mongo.db.users.update_one(
            { "email": session['user'] },
            { "$set":{"credits": new_total } })
        mongo.db.campaigns.remove(
            {"_id": ObjectId(campaign_id)})
        flash(
            "Campaign Deleted Credits have been added to your account")
        
        return redirect(url_for("profile", user=user))
    
    else:
    
        flash("You did not take any credits from this campaign")

        return redirect(url_for("profile", user=user)) 


@app.route("/delete_user")
def delete_user():

    mongo.db.campaigns.remove(g.user)
    flash("User Deleted")

    return redirect( url_for("logout"))


@app.route("/transactions")
def transactions():

    user = g.user
    user_id = str(user["_id"])
    transactions_list = list(mongo.db.transactions.find(
        { '$or':[ {"user_to_id": user_id},
        { "user_from_id": user_id} ]} ))
    
    transactions = sorted(transactions_list, key=itemgetter('transaction_time'), reverse=True)

    return render_template(
        "transactions.html",
         transactions=transactions,
          user_id=user_id, user=user)


@app.route("/donate_campaign/<campaign_id>", methods=["GET","POST"])
def donate_campaign(campaign_id):
    
    if not session.get('user'):
        flash('You need to log in to be able to donate!')
        return render_template("signin.html")
    
    campaign = mongo.db.campaigns.find_one(
        { "_id": ObjectId(campaign_id) })
    creator_id = campaign["creator_id"]
    campaign_creator = mongo.db.users.find_one(
        { "_id": ObjectId(creator_id) })
    campaign_name = campaign['name']
    current_user = mongo.db.users.find_one(
        { "email": session['user'] })
    current_user_id = str(current_user['_id'])
    donation_amount = int(request.form.get("donate"))
    user_credits = current_user['credits']

    if donation_amount > user_credits:
        flash(
            "You do not have enough credits to make this donation")
        return render_template(
            'campaign_view.html',
             campaign=campaign, user=campaign_creator)
    
    user_credits_left = user_credits - donation_amount
    target_amount = int(campaign['target_amount'])
    current_amount_raised = campaign['current_amount']
    new_amount = current_amount_raised + donation_amount
    new_percentage = round(
        ( new_amount / target_amount) * 100)

    mongo.db.campaigns.update_one(
        { "_id": ObjectId(campaign_id) },
        { "$set":{"current_amount": new_amount} })
    mongo.db.campaigns.update_one(
        { "_id": ObjectId(campaign_id) },
        { "$set":{"percentage_complete": new_percentage} })
    mongo.db.users.update_one(
        { "email": session['user'] },
        { "$set":{"credits": user_credits_left} })
    
    flash(
        f"You have added to the {campaign_name} campaign they are now {new_percentage} percent towards their target")
    create_transaction(
        current_user_id, creator_id , campaign_id, donation_amount)

    return redirect( url_for('home', user=g.user))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
        port=int(os.environ.get("PORT")),
        debug=True) # Don't forget to change this to False!!!