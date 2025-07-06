from flask import Flask, render_template, request, redirect, url_for, session, send_file, Response
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from io import BytesIO
import gridfs
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
app.secret_key = os.getenv("SECRET_KEY")
print(f"Loaded MONGO_URI: {app.config['MONGO_URI']}")
mongo = PyMongo(app)
fs = gridfs.GridFS(mongo.db)

@app.route('/')
def index():
    date = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    district = request.args.get('district') or ''
    districts = list(mongo.db.districts.find())

    if not district and districts:
        district = districts[0]['name']

    pdf_file = mongo.db.articles.find_one({'date': date, 'district': district})

    return render_template('index.html',
                           pdf_file=pdf_file,
                           date=date,
                           district=district,
                           districts=districts)

@app.route('/get_full_pdf/<file_id>')
def get_full_pdf(file_id):
    file = fs.get(ObjectId(file_id))
    return send_file(BytesIO(file.read()), mimetype='application/pdf')


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')

        if action == 'login':
            identifier = request.form['identifier']
            password = request.form['password']

            # Check admin
            admin = mongo.db.admins.find_one({'$or': [{'username': identifier}, {'email': identifier}]})
            if admin and check_password_hash(admin['password'], password):
                session.clear()
                session['admin'] = True
                session['admin_name'] = admin['username']
                session['admin_id'] = str(admin['_id'])
                return redirect(url_for('index'))

            # Check user
            user = mongo.db.users.find_one({'$or': [{'username': identifier}, {'email': identifier}]})
            if user and check_password_hash(user['password'], password):
                session.clear()
                session['user_id'] = str(user['_id'])
                session['username'] = user['username']
                return redirect(url_for('index'))

            # Invalid login
            return render_template('login.html', error="Invalid credentials")

        elif action == 'register':
            # Redirect to register page if form submitted with register action (optional)
            return redirect(url_for('register'))

    return render_template('login.html')


@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['reg_username']
        email = request.form['reg_email']
        password = request.form['reg_password']
        phone = request.form['reg_phone']

        # Check for existing username/email
        if mongo.db.users.find_one({'$or': [{'username': username}, {'email': email}]}) or \
           mongo.db.admins.find_one({'$or': [{'username': username}, {'email': email}]}):
            return render_template('register.html', error="Username or email already exists.")

        mongo.db.users.insert_one({
            'username': username,
            'email': email,
            'password': generate_password_hash(password),
            'phone': phone
        })
        return redirect(url_for('login'))

    return render_template('register.html')

@app.route('/edit_profile', methods=['GET', 'POST'])
def edit_profile():
    if 'user_id' not in session:
        return redirect(url_for('login'))
    
    user = mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
    
    if not user:
        session.clear()
        return redirect(url_for('login'))
    
    if request.method == 'POST':
        updates = {}
        username = request.form.get('username')
        email = request.form.get('email')
        phone = request.form.get('phone')
        password = request.form.get('password')
        
        if username and username != user['username']:
            # Ensure username is unique
            if mongo.db.users.find_one({'username': username, '_id': {'$ne': user['_id']}}):
                return "Username already taken", 400
            updates['username'] = username
            session['username'] = username
        
        if email and email != user['email']:
            # Ensure email is unique
            if mongo.db.users.find_one({'email': email, '_id': {'$ne': user['_id']}}):
                return "Email already registered", 400
            updates['email'] = email
        
        if phone:
            updates['phone'] = phone
        
        if password:
            updates['password'] = generate_password_hash(password)
        
        if updates:
            mongo.db.users.update_one({'_id': user['_id']}, {'$set': updates})
        
        return redirect(url_for('index'))
    
    return render_template('edit_profile.html', user=user)

@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/manage', methods=['GET', 'POST'])
def manage():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'upload':
            date = request.form['date']
            district = request.form['district']
            file = request.files['pdf_file']
            if file:
                file_id = fs.put(file.read(), filename=file.filename)
                mongo.db.articles.insert_one({
                    'date': date,
                    'district': district,
                    'file_id': file_id,
                    'uploaded_at': datetime.now()
                })
                return redirect(url_for('index', date=date, district=district))
        elif action == 'add_district':
            new_district = request.form['new_district']
            if new_district and not mongo.db.districts.find_one({'name': new_district}):
                mongo.db.districts.insert_one({'name': new_district})
        elif action == 'delete_district':
            mongo.db.districts.delete_one({'name': request.form['del_district']})
        return redirect(url_for('manage'))
    districts = list(mongo.db.districts.find())
    articles = list(mongo.db.articles.find())
    return render_template('manage.html', articles=articles, districts=districts)

@app.route('/delete/<article_id>')
def delete(article_id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    article = mongo.db.articles.find_one({'_id': ObjectId(article_id)})
    if article:
        fs.delete(article['file_id'])
        mongo.db.articles.delete_one({'_id': ObjectId(article_id)})
    return redirect(url_for('manage'))

if __name__ == '__main__':
    import os
    from dotenv import load_dotenv
    load_dotenv()
    port = int(os.environ.get("PORT", 5000))
    app.run(host='0.0.0.0', port=port)