FROM python:3

ENV TZ=America/Chicago
RUN ln -snf /usr/share/zoneinfo/$TZ /etc/localtime && echo $TZ > /etc/timezone

WORKDIR /app
COPY requirements.txt ./
COPY identify.py ./
RUN pip3 install --no-cache-dir -r requirements.txt

ENTRYPOINT [ "python", "./identify.py" ]
CMD [ "-d", "/input", "-o", "/output", "/metadata/metadata.json" ]