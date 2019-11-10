FROM python:3.7

COPY . .
RUN pip install -r requirements.txt
EXPOSE 8081
CMD ["python3", "main.py"]
