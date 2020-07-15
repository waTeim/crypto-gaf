FROM python:3.6
WORKDIR /app
ADD . /app
RUN pip install --upgrade pip
RUN pip install -r requirements.txt

CMD if [ -e /run/secrets/pg_pw ]; then python -u app.py --pg_pw `cat /run/secrets/pg_pw`; else python -u app.py; fi