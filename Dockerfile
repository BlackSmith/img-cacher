FROM python:3.11-slim AS worker
WORKDIR /app
ADD requirements_worker.txt /root
RUN apt update && \
    apt install --no-install-recommends -y libgl1 libglib2.0-0 &&\
    apt clean &&\
    pip install --upgrade pip &&\
    pip install -r /root/requirements_worker.txt
ADD app/ /app/
CMD ["python3", "worker.py"]

FROM node:lts-slim AS ui
WORKDIR /img-proxy
ADD img-proxy/ /img-proxy/
RUN npm ci &&\
    npm run build --

FROM python:3.11-slim AS main
WORKDIR /app
ADD requirements.txt /root
RUN pip install --upgrade pip && \
    pip install -r /root/requirements.txt
ADD app/ /app/
COPY --from=ui /app/static /app/static/
CMD ["python3", "main.py"]
