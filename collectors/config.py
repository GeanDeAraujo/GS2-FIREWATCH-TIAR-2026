import os

NASA_FIRMS_API_KEY = os.environ.get("NASA_FIRMS_API_KEY", "")
NASA_FIRMS_BASE_URL = os.environ.get(
    "NASA_FIRMS_BASE_URL",
    "https://firms.modaps.eosdis.nasa.gov/api/area/csv",
)

SENTINEL_CLIENT_ID = os.environ.get("SENTINEL_CLIENT_ID", "")
SENTINEL_CLIENT_SECRET = os.environ.get("SENTINEL_CLIENT_SECRET", "")
SENTINEL_API_URL = os.environ.get(
    "SENTINEL_API_URL",
    "https://catalogue.dataspace.copernicus.eu/odata/v1",
)

INPE_API_URL = os.environ.get("INPE_API_URL", "https://queimadas.dgi.inpe.br/api/")

AWS_BUCKET_NAME = os.environ.get("AWS_BUCKET_NAME", "")
AWS_REGION = os.environ.get("AWS_REGION", "sa-east-1")

# Bounding box for Brazil
BRAZIL_BBOX = (-33.75, -73.98, 5.27, -28.84)  # (min_lat, min_lon, max_lat, max_lon)
