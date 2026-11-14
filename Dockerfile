FROM python:3.11-slim
WORKDIR /app
COPY requirements.txt /app/
RUN pip install --no-cache-dir -r requirements.txt && pip install --no-cache-dir 'google-cloud-storage>=2.18,<4' 'ecmwf-opendata>=0.3,<1' 'xarray>=2024.1' 'cfgrib>=0.9.10' 'eccodes>=2.35'
COPY src /app/src
COPY data /app/data
ENV PYTHONUNBUFFERED=1
CMD ["python", "src/cloud_cycle.py"]
