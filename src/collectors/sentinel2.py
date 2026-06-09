"""Sentinel-2 collector — download RGB+NIR images from Copernicus Data Space."""
from __future__ import annotations

import logging
import os
import tempfile
from dataclasses import dataclass
from datetime import date, timedelta
from typing import List, Optional

import boto3
import requests

from config import (
    AWS_BUCKET_NAME,
    AWS_REGION,
    BRAZIL_BBOX,
    SENTINEL_API_URL,
    SENTINEL_CLIENT_ID,
    SENTINEL_CLIENT_SECRET,
)

logger = logging.getLogger(__name__)

# ── TODO: set SENTINEL_CLIENT_ID and SENTINEL_CLIENT_SECRET in .env ──────────
# Register at: https://dataspace.copernicus.eu/
# ─────────────────────────────────────────────────────────────────────────────

TOKEN_URL = "https://identity.dataspace.copernicus.eu/auth/realms/CDSE/protocol/openid-connect/token"


@dataclass
class Sentinel2Scene:
    product_id: str
    sensing_time: str
    cloud_cover: float
    download_url: str
    tile_id: str


class Sentinel2Collector:
    """Download Sentinel-2 L2A multispectral scenes from Copernicus Data Space."""

    def __init__(
        self,
        client_id: str = SENTINEL_CLIENT_ID,
        client_secret: str = SENTINEL_CLIENT_SECRET,
    ):
        if not client_id or not client_secret:
            raise ValueError(
                "SENTINEL_CLIENT_ID and SENTINEL_CLIENT_SECRET are not set. Configure them in .env"
            )
        self.client_id = client_id
        self.client_secret = client_secret
        self._token: Optional[str] = None
        self.session = requests.Session()

    def _get_token(self) -> str:
        """Request an OAuth2 access token from Copernicus Identity Service."""
        response = self.session.post(
            TOKEN_URL,
            data={
                "grant_type": "client_credentials",
                "client_id": self.client_id,
                "client_secret": self.client_secret,
            },
            timeout=30,
        )
        response.raise_for_status()
        self._token = response.json()["access_token"]
        return self._token

    @property
    def auth_headers(self) -> dict:
        if not self._token:
            self._get_token()
        return {"Authorization": f"Bearer {self._token}"}

    def search_scenes(
        self,
        bbox: tuple = BRAZIL_BBOX,
        date_from: Optional[date] = None,
        date_to: Optional[date] = None,
        max_cloud_cover: float = 20.0,
        max_results: int = 10,
    ) -> List[Sentinel2Scene]:
        """
        Query Copernicus OData catalogue for available Sentinel-2 L2A scenes.

        :param bbox: (min_lat, min_lon, max_lat, max_lon)
        :param date_from: Start date (defaults to yesterday)
        :param date_to: End date (defaults to today)
        :param max_cloud_cover: Maximum cloud cover percentage (0–100)
        :param max_results: Maximum number of scenes to return
        """
        if date_from is None:
            date_from = date.today() - timedelta(days=1)
        if date_to is None:
            date_to = date.today()

        min_lat, min_lon, max_lat, max_lon = bbox
        wkt = f"POLYGON(({min_lon} {min_lat},{max_lon} {min_lat},{max_lon} {max_lat},{min_lon} {max_lat},{min_lon} {min_lat}))"

        params = {
            "$filter": (
                f"Collection/Name eq 'SENTINEL-2' "
                f"and Attributes/OData.CSC.DoubleAttribute/any(att:att/Name eq 'cloudCover' and att/OData.CSC.DoubleAttribute/Value le {max_cloud_cover}) "
                f"and ContentDate/Start ge {date_from.isoformat()}T00:00:00.000Z "
                f"and ContentDate/Start le {date_to.isoformat()}T23:59:59.999Z "
                f"and OData.CSC.Intersects(area=geography'SRID=4326;{wkt}')"
            ),
            "$orderby": "ContentDate/Start desc",
            "$top": max_results,
        }

        url = f"{SENTINEL_API_URL}/Products"
        response = self.session.get(url, params=params, headers=self.auth_headers, timeout=60)
        response.raise_for_status()

        scenes: List[Sentinel2Scene] = []
        for item in response.json().get("value", []):
            scenes.append(Sentinel2Scene(
                product_id=item["Id"],
                sensing_time=item.get("ContentDate", {}).get("Start", ""),
                cloud_cover=0.0,  # extracted from attributes if needed
                download_url=f"{SENTINEL_API_URL}/Products({item['Id']})/$value",
                tile_id=item.get("Name", ""),
            ))

        logger.info("Found %d Sentinel-2 scenes", len(scenes))
        return scenes

    def download_scene(self, scene: Sentinel2Scene, local_dir: str | None = None) -> str:
        """Download a scene ZIP file and return the local path."""
        if local_dir is None:
            local_dir = tempfile.mkdtemp()

        local_path = os.path.join(local_dir, f"{scene.tile_id}.zip")
        response = self.session.get(scene.download_url, headers=self.auth_headers, stream=True, timeout=300)
        response.raise_for_status()

        with open(local_path, "wb") as f:
            for chunk in response.iter_content(chunk_size=8192):
                f.write(chunk)

        logger.info("Downloaded Sentinel-2 scene → %s", local_path)
        return local_path

    def upload_to_s3(
        self,
        local_path: str,
        scene: Sentinel2Scene,
        state: str = "BR",
        lat: Optional[float] = None,
        lon: Optional[float] = None,
        s3_client=None,
    ) -> str:
        """Upload downloaded scene to S3 with coordinates in metadata and key."""
        if s3_client is None:
            s3_client = boto3.client("s3", region_name=AWS_REGION)

        filename = os.path.basename(local_path)
        day = scene.sensing_time[:10] if scene.sensing_time else date.today().isoformat()

        coord_prefix = f"lat_{lat:.4f}_lon_{lon:.4f}_" if lat is not None else ""
        s3_key = f"raw/sentinel2/{state}/{day}/{coord_prefix}{filename}"

        extra_args: dict = {}
        if lat is not None and lon is not None:
            extra_args["Metadata"] = {"lat": str(round(lat, 6)), "lon": str(round(lon, 6))}

        s3_client.upload_file(local_path, AWS_BUCKET_NAME, s3_key, ExtraArgs=extra_args or None)
        logger.info("Uploaded %s → s3://%s/%s", local_path, AWS_BUCKET_NAME, s3_key)
        return s3_key


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    collector = Sentinel2Collector()
    scenes = collector.search_scenes(max_cloud_cover=15.0, max_results=5)
    print(f"Found {len(scenes)} scenes")
    for s in scenes:
        print(f"  {s.tile_id}  {s.sensing_time}")
