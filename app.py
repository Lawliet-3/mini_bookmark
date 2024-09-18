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
import re

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
        print("Analyzing content...")
        page_type = analyze_page_type(html_content, url)
        
        if page_type == 'article':
            print("Parsing article content...")
            parsed_content = parse_content(html_content, url)
            return {
                'type': 'article',
                'title': parsed_content['title'],
                'summary': parsed_content['main_content'],
                'full_text': parsed_content['main_content']
            }
        else:
            print("Extracting links from list page...")
            soup = BeautifulSoup(html_content, 'lxml')
            links = extract_links_from_list(soup, url)
            return {
                'type': 'list',
                'title': soup.title.string if soup.title else 'Link List',
                'links': links
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

def analyze_page_type(html_content, url):
    soup = BeautifulSoup(html_content, 'lxml')
    
    # Check URL structure
    if re.search(r'/\d{4}/\d{2}/\d{2}/', url) or re.search(r'/article/', url):
        return 'article'
    
    # Analyze content structure
    article_tags = soup.find_all(['article', 'div', 'section'], class_=re.compile(r'article|post|content'))
    if len(article_tags) == 1 and len(article_tags[0].get_text()) > 1000:
        return 'article'
    
    # Check for list-like structures
    list_items = soup.find_all(['ul', 'ol', 'div'], class_=re.compile(r'list|grid'))
    if list_items and len(list_items[0].find_all('a')) > 5:
        return 'list'
    
    # Analyze text-to-link ratio
    text_length = len(soup.get_text())
    link_count = len(soup.find_all('a'))
    if link_count > 0 and text_length / link_count < 100:
        return 'list'
    
    # Default to article if uncertain
    return 'article'

def extract_links_from_list(soup, base_url):
    links = []
    for a in soup.find_all('a', href=True):
        href = a['href']
        full_url = requests.compat.urljoin(base_url, href)
        title = a.get_text().strip() or a.get('title', '')
        
        # Extract image if available
        img = a.find('img')
        img_src = img['src'] if img and 'src' in img.attrs else None
        if img_src:
            img_src = requests.compat.urljoin(base_url, img_src)
        
        if title and full_url not in [link['url'] for link in links]:
            links.append({
                'title': title,
                'url': full_url,
                'image': img_src
            })
    return links[:20]  # Limit to top 20 links

if __name__ == '__main__':
    app.run(use_reloader=True, port=5000, threaded=True)