#!/usr/bin/env python

from bs4 import BeautifulSoup 
import requests
import re
import os
import json
from datetime import datetime
from urllib import urlencode
from flask import Flask, render_template, request

DEFAULT_REVIEW_COUNT = 5
CHROME_UA = ('Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) '
  +'AppleWebKit/537.36 (KHTML, like Gecko) '
  +'Chrome/58.0.3029.110 Safari/537.36')

# easy averages
def avg(values):
  return sum(values)/len(values)

# act like a human! beep boop. take a url and turn it into soup.
def soup_url(url):
    # pretend we're chrome to be less obvious robots
    headers = {'User-Agent': CHROME_UA}
    response = requests.get(url, headers=headers)
    return BeautifulSoup(response.content, 'html.parser')

# page has a json block containing all the reviews! This is kind of a cheat
# See earlier rev for a more tag-based approach
def get_review_dict(soup):
  for script in soup.findAll('script'):
    if script.attrs.get('type') == 'application/ld+json':
      return json.loads(script.text)
  return {}

# take a souped review page and grab ALL the reviews.
def get_reviews(soup):
  review_dict = get_review_dict(soup)
  # trim down the information passed
  reviews = map(lambda x: {'date': datetime.strptime(x['datePublished'], 
                                                      '%Y-%m-%d').date(),
                          'rating': float(x['reviewRating']['ratingValue']),
                          'content': x['description'],
                          'author': x['author']}, 
                review_dict['review'])
  # return them sorted by date desc
  return sorted(reviews,
                key=lambda x: x['date'],
                reverse=True)

# from a souped review page, get ONLY num_reviews reviews + their average.
def get_n_reviews_with_avg(soup, num_reviews):
  reviews = get_reviews(soup)[0:num_reviews]
  avg_rating = avg(filter(lambda x: x is not None,
                          map(lambda x: x['rating'],
                            reviews)))
  return {"average_rating": avg_rating,
          "reviews": reviews}

# just do this manually, it's simple and we don't need a lib.
def refresh_token(secret_id, secret):
  url = 'https://api.yelp.com/oauth2/token'
  args = {'grant_type': 'client_credentials',
          'client_id': secret_id,
          'client_secret': secret }
  response = requests.post(url, args)
  os.environ['PIZZA_ACCESS_TOKEN'] = response.json()['access_token']

# returns raw HTTP response. 
# this is what we refresh/retry if the token is expired.
def do_pizza_search(name):
  url = 'https://api.yelp.com/v3/businesses/search'
  params = {'term': name,
    "location": 'New York, NY, US',
    'categories': 'pizza',
    'limit': 1
    }
  # authorize
  headers = {'Authorization': 
              "Bearer %s" % os.environ.get('PIZZA_ACCESS_TOKEN')}
  return requests.get(url, params=params, headers=headers)

# get the first NY pizza place returned by the API for this name
def find_pizza(name):
  # go grab the api key id/secret
  key_id = os.environ.get('YELP_API_KEY_ID')
  secret_key = os.environ.get('YELP_API_SECRET_KEY')
  # make sure the token's in the cache
  if os.environ.get('PIZZA_ACCESS_TOKEN') is None:
    refresh_token(key_id, secret_key)
  pizza_response = do_pizza_search(name)
  if pizza_response.status_code / 100 == 4:
    # auth probs, refresh and try again
    refresh_token(key_id, secret_key)
    pizza_response = do_pizza_search(name)
  if pizza_response.status_code != 200:
    raise IOError("Can't get pizza! %d: %s" \
      % (pizza_response.status_code, pizza_response.content))
  print pizza_response.json()
  results = pizza_response.json().get('businesses', [])
  return results[0] if len(results) > 0 else None

### Flask stuff (webapp)

app = Flask(__name__)

# turn date objects into human-readable dates
@app.template_filter('pretty_date')
def pretty_date(d):
    return d.isoformat()

# simple route for just displaying pizza form
@app.route('/')
def pizza_finder():
    return render_template('search.html')

# route for finding pizza
@app.route('/find', methods=['POST', 'GET'])
def pizza_display():
    arg_dict = None
    if request.method == 'POST':
      arg_dict = request.form
    else:
      arg_dict = request.args
    pizza_term = arg_dict.get('name')
    review_count = arg_dict.get('count', DEFAULT_REVIEW_COUNT)
    # coercion for the count since we will get a string
    # also make sure it's no more than 10
    try:
      review_count = min(10, int(review_count))
    except ValueError:
      review_count = DEFAULT_REVIEW_COUNT
    if pizza_term is None:
      print "Request:" + request.__repr__()
      print "Form:" + str(request.form)
      return render_template('search.html')
    else:
      result = find_pizza(pizza_term)
      pizza_url = result['url'].split('?')[0] # dump trailing junk
      pizza_name = result['name']
      pizza_soup = soup_url(pizza_url)
      pizza_reviews = get_n_reviews_with_avg(pizza_soup, review_count)
      return render_template('search.html', results=pizza_reviews, 
                              pizza_name=pizza_name, search_term=pizza_term)
