import sys,os
my_path = os.path.dirname(os.path.abspath(__file__))
sys.path.append(os.path.join(my_path, ".."))

from bs4 import BeautifulSoup
from datetime import date

from pizza import *

import pytest

def test_avg():
  assert 4 == avg([2, 4, 6])

# monolithic test for several layers of soup
def test_review_extraction():
  with open('test/fixtures/fbc.htm', 'r') as fbc:
    canned_soup = BeautifulSoup(fbc.read(), 'html.parser')
    reviews = get_reviews(canned_soup)
    assert len(reviews) == 20
    review = reviews[0]
    assert date(2017, 6, 13) == review['date']
    assert 2.0 == review['rating']
    assert review['content'].startswith('No wifi. Too cavernous and noisy.')
    # AND NOW: do it again with a limiter
    five_reviews = get_n_reviews_with_avg(canned_soup, 5)
    assert 4.0 == five_reviews['average_rating']
    assert 5 == len(five_reviews['reviews'])
    last_review = five_reviews['reviews'][4]
    assert date(2017, 5, 22) == last_review['date']
    assert 5.0 == last_review['rating']
    assert last_review['content'].startswith('GET THE AFFOGATO IT IS AMAZING.')

def test_pretty_date():
  assert '2017-06-22' == pretty_date(date(2017, 6, 22))

# the rest of these are integration tests, could mock stuff but it seems out of scope.
