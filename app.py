import os

from flask import (
    Flask, flash, render_template,
    redirect, request, session, url_for)
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import (
    generate_password_hash, check_password_hash)
from datetime import datetime
from werkzeug.utils import secure_filename


if os.path.exists("env.py"):
    import env


app = Flask(__name__)

app.config['MONGO_DBNAME'] = os.environ.get("MONGO_DBNAME")
app.config["MONGO_URI"] = os.environ.get("MONGO_URI")
app.secret_key = os.environ.get("SECRET_KEY")
app.config['MAX_CONTENT_LENGTH'] = 5 * 1024 * 1024

ALLOWED_EXTENSIONS = set(['png', 'jpg', 'jpeg'])

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

# Check what the type of file
def allowed_file(filename):
    	return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route("/campaigns/<filename>")
def file(filename):
    return mongo.send_file(filename)
    

@app.route("/")
@app.route("/home")
def home():
    campaigns = list(mongo.db.campaigns.find())
    return render_template("home.html", campaigns=campaigns)


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


@app.route("/profile/<user>", methods=["GET","POST"])
def profile(user):
    user = mongo.db.users.find_one({ "email": session['user'] })
    if session['user']:
        return render_template("profile.html", user=user)
    
    return redirect(url_for("signin"))


@app.route('/logout')
def logout():
    flash("Your have been logged out")
    session.pop("user")
    return redirect( url_for("signin"))


@app.route("/update_credits/<user>", methods=["GET","POST"])
def add_credits(user):
    
    if request.method == "POST":
        user = mongo.db.users.find_one(
            { "email": session['user'] })
        amount = int(request.form.get("add_credits"))
        credits = user["credits"]
        new_total = credits + amount
        mongo.db.users.update_one(
            { "email": session['user'] }, {"$set":{"credits": new_total}})
        flash(f"You added {amount}, credits")

        return redirect(url_for("profile", user=user))

    return redirect(url_for("profile", user=user))


@app.route("/user_campaigns/<user>")
def user_campaigns(user):
    user = mongo.db.users.find_one(
        { "email": session['user'] })
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
            "creator_id": user_id,
        }

        mongo.db.campaigns.insert_one(new_campaign)
        flash('You have added a new campaign')
        campaigns = list(mongo.db.campaigns.find(
             { "creator_id" : user_id } ))
        return render_template('user_campaigns.html',
         user=user, campaigns=campaigns)

    return render_template("create_campaign.html")


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
     campaign=campaign)


@app.route("/collect_campaign/<campaign_id>")
def collect_campaign(campaign_id):
    user = mongo.db.users.find_one(
        { "email": session['user'] })
    campaign = mongo.db.campaigns.find_one(
        { "_id": ObjectId(campaign_id) })
    current_user_credits = user["credits"]
    campaign_credits = campaign['current_amount']
    new_total = int(current_user_credits) + int(campaign_credits)
    mongo.db.users.update_one(
        { "email": session['user'] },
        { "$set":{"credits": new_total } })
    campaign = mongo.db.campaigns.update_one(
        { "_id": ObjectId(campaign_id) },
        { "$set":{"current_amount": 0 } })

    flash("You have debited the campign amount into your account")

    return redirect(url_for("profile", user=user)) 


@app.route("/delete_campaign/<campaign_id>")
def delete_campaign(campaign_id):
    user = mongo.db.users.find_one(
        { "email": session['user'] })
    campaign = mongo.db.campaigns.find_one(
        { "_id": ObjectId(campaign_id) })
    current_user_credits = user["credits"]
    campaign_credits = campaign['current_amount']
    new_total = int(current_user_credits) + int(campaign_credits)
    mongo.db.users.update_one(
        { "email": session['user'] },
        { "$set":{"credits": new_total } })
    mongo.db.campaigns.remove({"_id": ObjectId(campaign_id)})
    flash("Campaign Deleted Credits have been added to your account")
    
    return redirect(url_for("profile", user=user))


@app.route("/delete_user/<user>")
def delete_user(user):
    mongo.db.campaigns.remove(user)
    flash("User Deleted")
    return render_template("home.html")


@app.route("/transactions/<user>")
def transactions(user):
    user = mongo.db.users.find_one(
        { "email": session['user'] })
    user_id = str(user["_id"])
    transactions = list(mongo.db.transactions.find(
        { '$or':[ {"user_to_id":user_id},
        { "user_from_id":user_id} ]} ))

    return render_template(
        "transactions.html",
         transactions=transactions,
          user_id=user_id)


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
        flash("You do not have enough credits to make this donation")
        return render_template(
            'campaign_view.html', campaign=campaign, user=campaign_creator)
    
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

    return redirect( url_for('home'))


if __name__ == "__main__":
    app.run(host=os.environ.get("IP"),
        port=int(os.environ.get("PORT")),
        debug=True) # Don't forget to change this to False!!!