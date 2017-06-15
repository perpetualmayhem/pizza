#!/usr/bin/env python

from bs4 import BeautifulSoup 
import requests
import re
import os
import json
from datetime import date
from urllib import urlencode
from collections import OrderedDict

BASE_URL='https://www.yelp.com/'
TITLE_TO_RATING = r'(\d\.\d) star rating'
YELP_DATE_MATCHER = r'(\d{1,2})/(\d{1,2})/(\d{4})'

def has_class(tag, class_str):
  return 'class' in tag.attrs and class_str in tag.attrs.get('class')

def parse_rating_from_title(title):
  # guaranteed to be valid and numeric
  # unless re match failed
  try:
    return float(re.sub(TITLE_TO_RATING, '\\1', title))
  except ValueError:
    # if it matched, it was numeric, so musta not matched.
    return None

def get_review_text(review_div):
  return review_div.find('p').text

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

def get_review_rating(review_div):
  rating_div = filter(lambda x: has_class(x, 'i-stars'),
                      review_div.find_all('div'))[0]
  return parse_rating_from_title(rating_div.attrs.get('title'))

# this gets the raw ratings
def get_raw_ratings(reviews_divs):
  filter(is_star_div, map(lambda x: x.find_all('div'), reviews_divs))

def soup_url(url):
  response = request.get(url)
  return BeautifulSoup(response.content, 'html.parser')

# ratings must be scraped after we have the biz's url
def get_ratings(soup):
  review_divs = filter(lambda x: has_class(x, 'review'), soup.find_all('div'))
  # pop off the first one of these, it's just us and our non-existent review
  review_divs.pop(0)
  # do some quick extraction here to reduce what's passed around
  reviews = map(lambda x: {'date': get_review_date(x),
                            'content': get_review_text(x),
                            'rating': get_review_rating(x)}, review_divs)
  # order what's left by date, desc
  return sorted(reviews, 
                          key=lambda x: x['date'],
                          reverse=True)

def avg(values):
  return sum(values)/len(values)

def get_n_ratings_with_avg(soup, num_ratings):
  ratings = get_ratings(soup)[0:num_ratings]
  avg_rating = avg(filter(lambda x: x is not None, map(lambda x: x['rating'], ratings)))
  return (avg_rating, ratings)

def refresh_token(secret_id, secret):
  url = 'https://api.yelp.com/oauth2/token'
  args = {'grant_type': 'client_credentials',
          'client_id': secret_id,
          'client_secret': secret }
  response = requests.post(url, args)
  os.environ['PIZZA_ACCESS_TOKEN'] = response.json()['access_token']
  print os.environ['PIZZA_ACCESS_TOKEN']

# returns raw request. this is what we refresh/retry if the token is expired.
def do_pizza_search(name):
  url = 'https://api.yelp.com/v3/businesses/search'
  params = {'keyword': name,
    "location": 'New York, NY, US',
    'categories': 'pizza',
    'limit': 1
    }
  headers = {'Authorization': "Bearer %s" % os.environ.get('PIZZA_ACCESS_TOKEN')}
  return requests.get(url, params=params, headers=headers)

def find_pizza(name):
  pizza_response = do_pizza_search(name)
  if pizza_response.status_code / 100 == 4:
    # auth probs, refresh and try again
    refresh_token
    pizza_response = do_pizza_search(name)
  if pizza_response.status_code != 200:
    raise IOError("Can't get pizza! %d: %s" \
      % (pizza_response.status_code, pizza_response.content))
  print pizza_response.json()
  results = pizza_response.json().get('businesses', [])
  url = results[0]['url'] if len(results) > 0 else None
  return url

if __name__=='__main__':
  # cache this in the env.
  if os.environ.get('PIZZA_ACCESS_TOKEN') is None:
    refresh_token('7gck0xCgh1VbY6n5yLd_YA', 'yydTTgHU3blJFEvZOSe5UzLn9diqBhMvwiEj8Y50aSwXObZIxq9xldqsRTBklmMy')
  url = find_pizza('italy')
  print url
  with open('fbc.htm', 'r') as myfile:
    canned_soup = BeautifulSoup(myfile.read(), 'html.parser')
    print get_n_ratings_with_avg(canned_soup, 5)
