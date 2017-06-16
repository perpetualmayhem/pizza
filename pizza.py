#!/usr/bin/env python

from bs4 import BeautifulSoup 
import requests
import re
import os
import json
from datetime import date
from urllib import urlencode
from flask import Flask, render_template, request

TITLE_TO_RATING = r'(\d\.\d) star rating'
YELP_DATE_MATCHER = r'(\d{1,2})/(\d{1,2})/(\d{4})'
DEFAULT_REVIEW_COUNT = 5

API_SECRET_ID = None
API_SECRET = None

# easy average
def avg(values):
  return sum(values)/len(values)

### Specific parsing of some tags and content

# does the given tag have the requested class? used to filter everywhere.
def has_class(tag, class_str):
  return 'class' in tag.attrs and class_str in tag.attrs.get('class')

# turn "5.0 star rating" into 5.0f, or returns None if it didn't find something good.
def parse_rating_from_title(title):
  # guaranteed to be valid and numeric
  # unless re match failed
  try:
    return float(re.sub(TITLE_TO_RATING, '\\1', title))
  except ValueError:
    # if it matched, it was numeric, so musta not matched.
    return None

# from a review div, get the content
def get_review_text(review_div):
  return review_div.find('p').text

# from a review div, get the date
def get_review_date(review_div):
  # dates are found in spans of class rating-qualifier
  for span in review_div.find_all('span'):
    if has_class(span, 'rating-qualifier'):
      # see if there's a date
      m = re.search(YELP_DATE_MATCHER, span.text)
      if m is not None:
        (month, day, year) = map(int, m.groups())
        return date(year, month, day)
  # fell out
  return None

# from a review div, get the rating
def get_review_rating(review_div):
  rating_div = filter(lambda x: has_class(x, 'i-stars'),
                      review_div.find_all('div'))[0]
  return parse_rating_from_title(rating_div.attrs.get('title'))

# act like a human! beep boop. take a url and turn it into soup.
def soup_url(url):
    # pretend we're chrome to be less obvious robots
    headers = {'User-Agent': 'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_10_5) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/58.0.3029.110 Safari/537.36'}
    response = requests.get(url, headers=headers)
    return BeautifulSoup(response.content, 'html.parser')

def get_review_divs(soup):
  review_divs = filter(lambda x: has_class(x, 'review'), soup.find_all('div'))
  # pop off the first one of these, it's just us and our non-existent review
  if review_divs is not None and len(review_divs) > 0:
    review_divs.pop(0)
  return review_divs

# take a souped review page and grab ALL the reviews.
def get_reviews(soup):
  review_divs = get_review_divs(soup)
  # do some quick extraction here to reduce what's passed around
  reviews = map(lambda x: {'date': get_review_date(x),
                            'content': get_review_text(x),
                            'rating': get_review_rating(x)}, review_divs)
  # order what's left by date, desc
  return sorted(reviews, 
                          key=lambda x: x['date'],
                          reverse=True)

# from a souped review page, get ONLY num_reviews reviews + their average.
def get_n_reviews_with_avg(soup, num_reviews):
  reviews = get_reviews(soup)[0:num_reviews]
  avg_rating = avg(filter(lambda x: x is not None, map(lambda x: x['rating'], reviews)))
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

# returns raw HTTP response. this is what we refresh/retry if the token is expired.
def do_pizza_search(name):
  url = 'https://api.yelp.com/v3/businesses/search'
  params = {'term': name,
    "location": 'New York, NY, US',
    'categories': 'pizza',
    'limit': 1
    }
  # authorize
  headers = {'Authorization': "Bearer %s" % os.environ.get('PIZZA_ACCESS_TOKEN')}
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
