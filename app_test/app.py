from flask import Flask, request, jsonify, render_template
from selenium import webdriver
from selenium.webdriver.chrome.service import Service
from selenium.webdriver.common.by import By
from bs4 import BeautifulSoup
import time
import os
from datetime import datetime, timedelta
from dateutil import parser

app = Flask(__name__)

def extract_titles(soup, title_tag='h2', title_class='post-title'):
    titles = []
    for title in soup.find_all(title_tag, class_=title_class):
        titles.append(title.get_text().strip())
    return titles

def navigate_to_date_infinite_scroll(page_url, target_date_str, time_tag, time_class):
    options = webdriver.ChromeOptions()
    options.add_argument('--headless')
    options.add_argument('--disable-gpu')
    options.add_argument('--no-sandbox')
    options.add_argument('--disable-dev-shm-usage')
    
    service = Service(executable_path=os.getenv('CHROMEDRIVER_PATH'))
    driver = webdriver.Chrome(service=service, options=options)
    
    driver.get(page_url)

    last_height = driver.execute_script("return document.body.scrollHeight")
    soup = None
    most_recent_date = None

    target_date = parser.parse(target_date_str).date()

    while True:
        driver.execute_script("window.scrollTo(0, document.body.scrollHeight);")
        time.sleep(2)

        page_source = driver.page_source
        soup = BeautifulSoup(page_source, 'html.parser')

        most_recent_date = track_most_recent_date(soup, time_tag, time_class)

        if most_recent_date and most_recent_date < target_date:
            break

        new_height = driver.execute_script("return document.body.scrollHeight")
        if new_height == last_height:
            break

        last_height = new_height

    driver.quit()
    return soup

def track_most_recent_date(soup, time_tag, time_class):
    most_recent_date = None
    current_datetime = datetime.now()
    for date_tag in soup.find_all(time_tag, class_=time_class):
        article_date_str = date_tag.get_text().strip()
        if 'day' in article_date_str or 'hour' in article_date_str or 'minute' in article_date_str:
            if 'day' in article_date_str:
                days_ago = int(article_date_str.split()[0])
                article_date = current_datetime - timedelta(days=days_ago)
            elif 'hour' in article_date_str:
                hours_ago = int(article_date_str.split()[0])
                article_date = current_datetime - timedelta(hours=hours_ago)
            elif 'minute' in article_date_str:
                minutes_ago = int(article_date_str.split()[0])
                article_date = current_datetime - timedelta(minutes=minutes_ago)
            
            article_date = article_date.date()
        else:
            try:
                article_date = parser.parse(article_date_str).date()
            except (ValueError, TypeError) as e:
                print(f"Unable to parse date '{article_date_str}': {e}")
                continue
        if most_recent_date is None or article_date > most_recent_date:
            most_recent_date = article_date
    return most_recent_date
@app.route('/')
def index():
    return render_template('index.html')
@app.route('/scrape', methods=['GET'])
def scrape():
    page_url = request.args.get('url')
    target_date_str = request.args.get('date')
    time_tag = request.args.get('time_tag', 'time')
    time_class = request.args.get('time_class', '')

    soup = navigate_to_date_infinite_scroll(page_url, target_date_str, time_tag, time_class)
    titles = extract_titles(soup, title_tag='h2', title_class='post-title')
    
    return jsonify(titles)

if __name__ == '__main__':
    app.run(host='127.0.0.1', port=5000)
