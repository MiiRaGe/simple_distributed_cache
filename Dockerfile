FROM python:3.6
WORKDIR /usr/src/app

COPY requirements.txt ./
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 5555
CMD [ "python", "./server.py", "127.0.0.1:5555", "172.168.0.1:5555"]