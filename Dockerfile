FROM python:3.8

WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt
# RUN pip install alembic 
# RUN pip install psycopg2-binary

COPY . .

CMD [ "uvicorn", "main:app", "--reload", "--host", "0.0.0.0" ]