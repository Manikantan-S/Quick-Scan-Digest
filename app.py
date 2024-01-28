from flask import Flask, request, render_template, flash, redirect, url_for
import nltk
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
from textblob import TextBlob
from newspaper import Article
from datetime import datetime
from urllib.parse import urlparse
import validators
import requests

nltk.download('punkt')

app = Flask(__name__)



tokenizer = AutoTokenizer.from_pretrained("facebook/bart-large-cnn")
model = AutoModelForSeq2SeqLM.from_pretrained("facebook/bart-large-cnn")

def get_website_name(url):
    # Extract the website name from the URL
    parsed_url = urlparse(url)
    domain = parsed_url.netloc
    if domain.startswith("www."):
        domain = domain[4:]
    return domain

@app.route('/', methods=['GET', 'POST'])
def index():
    if request.method == 'POST':
        url = request.form['url']
        # Check if the input is a valid URL

        if not validators.url(url):
            flash('Please enter a valid URL.')
            return redirect(url_for('index'))
        
        try:
            response = requests.get(url)
            response.raise_for_status()  # Raise an HTTPError if the HTTP request returned an unsuccessful status code
        except requests.RequestException:
            flash('Failed to download the content of the URL.')
            return redirect(url_for('index'))
        
        article = Article(url)
        article.download()
        article.parse()
        article.nlp()  # Perform natural language processing

        title = article.title
        authors = ', '.join(article.authors)
        if not authors:
            authors = get_website_name(url)  # Set the author field to the website name
        publish_date = article.publish_date.strftime('%B %d, %Y') if article.publish_date else "N/A"

        # Use Pegasus for summarization
        article_text = article.text
        inputs = tokenizer.encode("summarize: " + article_text, return_tensors="pt", max_length=1024, truncation=True)
        summary_ids = model.generate(inputs, max_length=150, min_length=50, length_penalty=2.0, num_beams=4, early_stopping=True)
        summary = tokenizer.decode(summary_ids[0], skip_special_tokens=True)

        top_image = article.top_image  # Get the top image URL

        analysis = TextBlob(article.text)
        polarity = analysis.sentiment.polarity  # Get the polarity value

        if summary == "":
            flash('Please enter a valid URL.')
            return redirect(url_for('index'))

        if polarity > 0:
            sentiment = 'happy 😊'
        elif polarity < 0:
            sentiment = ' sad 😟'
        else:
            sentiment = 'neutral 😐'

        return render_template('index.html', title=title, authors=authors, publish_date=publish_date, summary=summary, top_image=top_image, sentiment=sentiment)

    return render_template('index.html')

app.secret_key = 'your_secret_key'

if __name__ == '__main__':
    app.run(debug=True)
