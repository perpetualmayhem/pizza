FROM python:2

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# load up the env
# had this been an actual security model, we'd have found these in a secret store somewhere
ENV YELP_API_KEY_ID='7gck0xCgh1VbY6n5yLd_YA' YELP_API_SECRET_KEY='yydTTgHU3blJFEvZOSe5UzLn9diqBhMvwiEj8Y50aSwXObZIxq9xldqsRTBklmMy' FLASK_APP=pizza.py

# this is where flask runs
EXPOSE 5000

CMD [ "flask", "run", "--host=0.0.0.0"]