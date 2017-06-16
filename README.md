# PIZZA.PY
##OMG WTF PZA

Cheapie review aggregator. Uses the Yelp API to grab your pizza place, then scrapes reviews and averages the N most recent. NB: Yelp doesn't like being scraped, service cleanly returns 0 reviews if Yelp has noticed you're a robot.

### Without Docker
* Install the required libraries
    ```pip install -r requirements.txt```
* Export needed env and run Flask
    ```source dev.env && flask run```
* Use your web browser to go find a New York slice
    ```http://localhost:5000```
