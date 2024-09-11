import json
import os
from flask import Flask, render_template, request, jsonify, session, send_from_directory
from flask_pymongo import PyMongo
from bson import ObjectId
from datetime import datetime
from bs4 import BeautifulSoup
import requests
from trafilatura import extract
import asyncio
from playwright.async_api import async_playwright
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.naive_bayes import MultinomialNB
from sklearn.pipeline import Pipeline
import nltk
from nltk.corpus import stopwords
import time
import robotexclusionrulesparser
from werkzeug.security import generate_password_hash, check_password_hash
from bson.objectid import ObjectId

app = Flask(__name__, static_folder='static')
app.config["MONGO_URI"] = "mongodb://localhost:27017/bookmarkmanager"
app.secret_key = os.environ.get('SECRET_KEY')
mongo = PyMongo(app)

BOOKMARKS_FILE = 'bookmarks.json'

# Download necessary NLTK data
nltk.download('stopwords')
nltk.download('punkt')

# Initialize the robots.txt parser
rp = robotexclusionrulesparser.RobotExclusionRulesParser()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/signup', methods=['POST'])
def signup():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    if mongo.db.users.find_one({"username": username}):
        return jsonify({"error": "Username already exists"}), 400
    
    hashed_password = generate_password_hash(password)
    mongo.db.users.insert_one({"username": username, "password": hashed_password})
    
    session['username'] = username
    return jsonify({"success": True, "username": username})

@app.route('/login', methods=['POST'])
def login():
    data = request.json
    username = data.get('username')
    password = data.get('password')
    
    user = mongo.db.users.find_one({"username": username})
    if user and check_password_hash(user['password'], password):
        session['username'] = username
        return jsonify({"success": True, "username": username})
    else:
        return jsonify({"success": False, "error": "Invalid username or password"}), 401

@app.route('/logout', methods=['POST'])
def logout():
    session.clear()
    return jsonify({"success": True})

@app.route('/fetch', methods=['POST'])
async def fetch_content_route():
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    url = request.json['url']
    content = await fetch_content(url)
    return jsonify(content)

async def fetch_content(url):
    print(f"Received request to fetch URL: {url}")
    try:
        # Check robots.txt
        robots_url = f"{url.split('//', 1)[0]}//{url.split('//', 1)[1].split('/', 1)[0]}/robots.txt"
        print(f"Checking robots.txt at: {robots_url}")
        rp.fetch(robots_url)
        if not rp.is_allowed(url, '*'):
            print(f"Access to {url} is not allowed by robots.txt")
            return {'error': 'Access to this URL is not allowed by robots.txt'}

        print("Fetching content with JavaScript support...")
        html_content = await fetch_url_with_js(url)
        print("Parsing content...")
        parsed_content = parse_content(html_content, url)
        
        print(f"Fetched URL: {url}")
        print(f"Title: {parsed_content['title']}")
        print(f"Summary length: {len(parsed_content['main_content'])}")
        
        return {
            'title': parsed_content['title'],
            'summary': parsed_content['main_content'],
            'full_text': parsed_content['main_content']
        }
    except Exception as e:
        print(f"Error fetching content: {str(e)}")
        import traceback
        traceback.print_exc()
        return {'error': str(e)}

@app.route('/save_bookmark', methods=['POST'])
def save_bookmark():
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    data = request.json
    try:
        mongo.db.bookmarks.insert_one({
            'username': session['username'],
            'url': data['url'],
            'title': data['title'],
            'summary': data['summary']
        })
        return jsonify({'success': True})
    except Exception as e:
        print(f"Error saving bookmark: {str(e)}")
        return jsonify({'success': False})

@app.route('/bookmarks', methods=['GET'])
def get_bookmarks():
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    bookmarks = list(mongo.db.bookmarks.find({'username': session['username']}).sort('_id', -1))
    for bookmark in bookmarks:
        bookmark['_id'] = str(bookmark['_id'])  # Convert ObjectId to string
    return jsonify(bookmarks)

async def fetch_url_with_js(url):
    async with async_playwright() as p:
        browser = await p.chromium.launch()
        page = await browser.new_page()
        await page.goto(url)
        # Wait for any JavaScript to finish executing
        await page.wait_for_load_state('networkidle')
        content = await page.content()
        await browser.close()
        return content

def parse_content(html_content, url):
    soup = BeautifulSoup(html_content, 'lxml')
    
    title = soup.title.string if soup.title else ''
    
    # Use a more sophisticated content extraction method
    main_content = extract_main_content(html_content)
    
    metadata = {
        'author': soup.find('meta', {'name': 'author'})['content'] if soup.find('meta', {'name': 'author'}) else '',
        'description': soup.find('meta', {'name': 'description'})['content'] if soup.find('meta', {'name': 'description'}) else '',
        'keywords': soup.find('meta', {'name': 'keywords'})['content'] if soup.find('meta', {'name': 'keywords'}) else '',
    }
    
    # Try to extract Open Graph metadata
    og_title = soup.find('meta', {'property': 'og:title'})
    og_description = soup.find('meta', {'property': 'og:description'})
    if og_title:
        metadata['og_title'] = og_title['content']
    if og_description:
        metadata['og_description'] = og_description['content']
    
    content_type = classify_content_ml(title, main_content)
    
    links = extract_links(soup, url)
    
    return {
        'title': title,
        'main_content': main_content,
        'metadata': metadata,
        'url': url,
        'content_type': content_type,
        'links': links
    }

def load_bookmarks():
    if os.path.exists(BOOKMARKS_FILE):
        with open(BOOKMARKS_FILE, 'r') as f:
            return json.load(f)
    return []

def save_bookmarks(bookmarks):
    with open(BOOKMARKS_FILE, 'w') as f:
        json.dump(bookmarks, f)

def extract_links(soup, base_url):
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        full_url = requests.compat.urljoin(base_url, href)
        links.append({'text': a.text.strip(), 'url': full_url})
    return links

def classify_content_ml(title, main_content):
    combined_text = f"{title} {main_content}"
    return classifier.predict([combined_text])[0]

def extract_main_content(html_content):
    # Use readability-lxml for better content extraction
    from readability import Document
    doc = Document(html_content)
    return doc.summary()

# Train a simple ML model for content classification
def train_classifier():
    # This is a placeholder. In a real scenario, you'd use a larger, labeled dataset.
    X = ["This is a news article about current events",
         "Check out our new product for sale",
         "Welcome to my personal blog",
         "Here's the documentation for our API"]
    y = ["news", "product", "blog", "documentation"]

    classifier = Pipeline([
        ('tfidf', TfidfVectorizer(stop_words=stopwords.words('english'))),
        ('clf', MultinomialNB()),
    ])
    classifier.fit(X, y)
    return classifier

classifier = train_classifier()

@app.route('/check_login')
def check_login():
    if 'username' in session:
        return jsonify({"logged_in": True})
    else:
        return jsonify({"logged_in": False})

@app.route('/', defaults={'path': ''})
@app.route('/<path:path>')
def serve(path):
    if path != "" and os.path.exists(app.static_folder + '/' + path):
        return send_from_directory(app.static_folder, path)
    else:
        return send_from_directory(app.static_folder, 'index.html')

@app.route('/delete_bookmark/<bookmark_id>', methods=['DELETE'])
def delete_bookmark(bookmark_id):
    if 'username' not in session:
        return jsonify({"error": "Not logged in"}), 401
    
    try:
        result = mongo.db.bookmarks.delete_one({
            '_id': ObjectId(bookmark_id),
            'username': session['username']
        })
        
        if result.deleted_count == 1:
            return jsonify({'success': True})
        else:
            return jsonify({'success': False, 'error': 'Bookmark not found or not authorized'}), 404
    except Exception as e:
        print(f"Error deleting bookmark: {str(e)}")
        return jsonify({'success': False, 'error': 'Server error'}), 500

if __name__ == '__main__':
    app.run(use_reloader=True, port=5000, threaded=True)