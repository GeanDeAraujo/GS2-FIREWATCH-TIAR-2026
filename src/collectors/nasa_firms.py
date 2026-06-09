"""NASA FIRMS API collector — MODIS and VIIRS fire hotspot data."""
from __future__ import annotations

import csv
import io
import logging
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List

import boto3
import requests

from config import AWS_BUCKET_NAME, AWS_REGION, BRAZIL_BBOX, NASA_FIRMS_API_KEY, NASA_FIRMS_BASE_URL

logger = logging.getLogger(__name__)

# ── TODO: set NASA_FIRMS_API_KEY in .env ──────────────────────────────────────
# Get your free key at: https://firms.modaps.eosdis.nasa.gov/api/area/
# ─────────────────────────────────────────────────────────────────────────────


@dataclass
class Hotspot:
    latitude: float
    longitude: float
    brightness: float
    acquisition_date: str
    acquisition_time: str
    satellite: str
    confidence: str
    frp: float  # Fire Radiative Power (MW)


class NASAFirmsCollector:
    """Collect active fire hotspots from the NASA FIRMS area API."""

    SOURCES = ["MODIS_NRT", "VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT"]

    def __init__(self, api_key: str = NASA_FIRMS_API_KEY):
        if not api_key:
            raise ValueError("NASA_FIRMS_API_KEY is not set. Configure it in .env")
        self.api_key = api_key
        self.session = requests.Session()

    def fetch_hotspots(
        self,
        source: str = "VIIRS_SNPP_NRT",
        days: int = 1,
        bbox: tuple = BRAZIL_BBOX,
    ) -> List[Hotspot]:
        """
        Fetch hotspots for a bounding box from the FIRMS area API.

        :param source: Data source (MODIS_NRT, VIIRS_SNPP_NRT, VIIRS_NOAA20_NRT)
        :param days: Number of days to look back (1–10)
        :param bbox: (min_lat, min_lon, max_lat, max_lon)
        """
        min_lat, min_lon, max_lat, max_lon = bbox
        area = f"{min_lon},{min_lat},{max_lon},{max_lat}"
        url = f"{NASA_FIRMS_BASE_URL}/{self.api_key}/{source}/{area}/{days}"

        logger.info("Fetching FIRMS hotspots from %s", url)
        response = self.session.get(url, timeout=30)
        response.raise_for_status()

        reader = csv.DictReader(io.StringIO(response.text))
        hotspots: List[Hotspot] = []

        for row in reader:
            try:
                hotspots.append(Hotspot(
                    latitude=float(row["latitude"]),
                    longitude=float(row["longitude"]),
                    brightness=float(row.get("bright_ti4", row.get("brightness", 0))),
                    acquisition_date=row.get("acq_date", ""),
                    acquisition_time=row.get("acq_time", ""),
                    satellite=row.get("satellite", source),
                    confidence=row.get("confidence", ""),
                    frp=float(row.get("frp", 0)),
                ))
            except (KeyError, ValueError) as exc:
                logger.warning("Skipping malformed row: %s — %s", row, exc)

        logger.info("Collected %d hotspots from %s", len(hotspots), source)
        return hotspots

    def upload_to_s3(self, hotspots: List[Hotspot], source: str, s3_client=None) -> str:
        """Upload hotspot CSV to S3 raw bucket. Returns the S3 key."""
        if s3_client is None:
            s3_client = boto3.client("s3", region_name=AWS_REGION)

        today = date.today().isoformat()
        s3_key = f"raw/nasa_firms/{source}/{today}/hotspots.csv"

        lines = ["latitude,longitude,brightness,acq_date,acq_time,satellite,confidence,frp"]
        for h in hotspots:
            lines.append(
                f"{h.latitude},{h.longitude},{h.brightness},{h.acquisition_date},"
                f"{h.acquisition_time},{h.satellite},{h.confidence},{h.frp}"
            )

        s3_client.put_object(
            Bucket=AWS_BUCKET_NAME,
            Key=s3_key,
            Body="\n".join(lines).encode("utf-8"),
            ContentType="text/csv",
        )
        logger.info("Uploaded %d hotspots → s3://%s/%s", len(hotspots), AWS_BUCKET_NAME, s3_key)
        return s3_key


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = NASAFirmsCollector()
    spots = collector.fetch_hotspots(source="VIIRS_SNPP_NRT", days=1)
    print(f"Found {len(spots)} hotspots")
    if spots:
        print(f"Sample: {spots[0]}")
