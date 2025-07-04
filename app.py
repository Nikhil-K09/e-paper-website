from flask import Flask, render_template, request, redirect, url_for, session, send_file
from flask_pymongo import PyMongo
from bson.objectid import ObjectId
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from PyPDF2 import PdfReader, PdfWriter
from io import BytesIO
import gridfs
import os
from dotenv import load_dotenv

load_dotenv()

app = Flask(__name__)
app.config["MONGO_URI"] = os.getenv("MONGO_URI")
app.secret_key = os.getenv("SECRET_KEY")
mongo = PyMongo(app)
fs = gridfs.GridFS(mongo.db)

def current_user():
    if 'user_id' in session:
        return mongo.db.users.find_one({'_id': ObjectId(session['user_id'])})
    if 'admin_id' in session:
        return mongo.db.admins.find_one({'_id': ObjectId(session['admin_id'])})
    return None

@app.route('/')
def index():
    date = request.args.get('date') or datetime.now().strftime('%Y-%m-%d')
    district = request.args.get('district') or ''
    pdf_file = mongo.db.articles.find_one({
        'date': date,
        'district': district
    })
    total_pages = 0
    if pdf_file:
        file = fs.get(pdf_file['file_id'])
        reader = PdfReader(BytesIO(file.read()))
        total_pages = len(reader.pages)
    return render_template('index.html', pdf_file=pdf_file, date=date, district=district, user=current_user(), total_pages=total_pages)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        action = request.form.get('action')
        if action == 'login':
            identifier = request.form['identifier']
            password = request.form['password']

            # First try admin
            admin = mongo.db.admins.find_one({'$or': [{'username': identifier}, {'email': identifier}]})
            if admin and check_password_hash(admin['password'], password):
                session.clear()
                session['admin'] = True
                session['admin_name'] = admin['username']
                session['admin_id'] = str(admin['_id'])
                return redirect(url_for('index'))

            # Then try user
            user = mongo.db.users.find_one({'$or': [{'username': identifier}, {'email': identifier}]})
            if user and check_password_hash(user['password'], password):
                session.clear()
                session['user_id'] = str(user['_id'])
                session['username'] = user['username']
                return redirect(url_for('index'))

        elif action == 'register':
            # Your existing user registration logic (check admins+users for duplicate)
            pass

    return render_template('login.html')


@app.route('/logout')
def logout():
    session.clear()
    return redirect(url_for('index'))

@app.route('/manage', methods=['GET', 'POST'])
def manage():
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    if request.method == 'POST':
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
            return redirect(url_for('manage'))
    articles = list(mongo.db.articles.find())
    return render_template('manage.html', articles=articles)

@app.route('/delete/<article_id>')
def delete(article_id):
    if 'admin_id' not in session:
        return redirect(url_for('login'))
    article = mongo.db.articles.find_one({'_id': ObjectId(article_id)})
    if article:
        fs.delete(article['file_id'])
        mongo.db.articles.delete_one({'_id': ObjectId(article_id)})
    return redirect(url_for('manage'))

@app.route('/get_pdf/<file_id>/<int:page>')
def get_pdf(file_id, page):
    file = fs.get(ObjectId(file_id))
    pdf = PdfReader(BytesIO(file.read()))
    if 0 <= page < len(pdf.pages):
        output = BytesIO()
        writer = PdfWriter()
        writer.add_page(pdf.pages[page])
        writer.write(output)
        output.seek(0)
        return send_file(output, download_name=f'page_{page + 1}.pdf', mimetype='application/pdf')
    return "Page not found", 404

if __name__ == '__main__':
    app.run(debug=True)
