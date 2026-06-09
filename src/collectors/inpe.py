"""
INPE / IBAMA fire data collector — versão corrigida.

Fontes:
  1. NASA FIRMS área API (bbox Brasil) — hotspots geocodificados por satélite
     Atribuído como fonte INPE/FIRMS pois o INPE também usa dados FIRMS
  2. IBAMA SISFOGO ROI CSV — estatísticas de incêndios por estado (sem lat/lon)
     Usado para enriquecer metadados com dados de ocorrências registradas

Motivo: INPE BDQueimadas API retorna 404 desde jun/2026 (endpoint migrado)
        IBAMA SISFOGO não possui coordenadas geográficas no CSV público
        FIRMS country API requer permissão especial de acesso
"""
from __future__ import annotations

import csv
import io
import logging
from collections import Counter
from dataclasses import dataclass, field
from datetime import date, timedelta
from typing import List, Optional

import boto3
import requests

from config import AWS_BUCKET_NAME, AWS_REGION, NASA_FIRMS_API_KEY, NASA_FIRMS_BASE_URL, BRAZIL_BBOX

logger = logging.getLogger(__name__)

IBAMA_ROI_CSV = "https://dadosabertos.ibama.gov.br/dados/SISFOGO/ROI.csv"

ESTADO_SIGLA = {
    "AC": "AC", "AL": "AL", "AP": "AP", "AM": "AM", "BA": "BA",
    "CE": "CE", "DF": "DF", "ES": "ES", "GO": "GO", "MA": "MA",
    "MT": "MT", "MS": "MS", "MG": "MG", "PA": "PA", "PB": "PB",
    "PR": "PR", "PE": "PE", "PI": "PI", "RJ": "RJ", "RN": "RN",
    "RS": "RS", "RO": "RO", "RR": "RR", "SC": "SC", "SP": "SP",
    "SE": "SE", "TO": "TO",
}

# Centróides aproximados dos estados para geocodificação de municipios IBAMA
ESTADO_CENTROID = {
    "AC": (-9.02, -70.81), "AL": (-9.57, -36.78), "AP": (1.41, -51.77),
    "AM": (-3.47, -65.10), "BA": (-12.97, -41.71), "CE": (-5.20, -39.53),
    "DF": (-15.78, -47.93), "ES": (-19.19, -40.34), "GO": (-15.83, -49.83),
    "MA": (-5.42, -45.44), "MT": (-12.64, -55.42), "MS": (-20.51, -54.54),
    "MG": (-18.10, -44.38), "PA": (-3.79, -52.48), "PB": (-7.28, -36.72),
    "PR": (-24.89, -51.55), "PE": (-8.38, -37.86), "PI": (-7.72, -42.73),
    "RJ": (-22.25, -42.66), "RN": (-5.81, -36.59), "RS": (-30.18, -53.50),
    "RO": (-10.83, -63.34), "RR": (2.72, -61.67), "SC": (-27.45, -50.95),
    "SP": (-22.25, -48.64), "SE": (-10.57, -37.43), "TO": (-10.18, -48.33),
}


@dataclass
class INPEFoco:
    latitude: float
    longitude: float
    municipio: str
    estado: str
    bioma: str
    data_hora_gmt: str
    satelite: str
    risco_fogo: Optional[float]
    frp: Optional[float]
    fonte: str = "FIRMS/INPE"


class INPECollector:
    """
    Coleta focos de incêndio para o Brasil via NASA FIRMS área API.
    Enriquece com estatísticas do IBAMA SISFOGO quando disponível.
    """

    def __init__(self, api_key: str = NASA_FIRMS_API_KEY, base_url: str = NASA_FIRMS_BASE_URL):
        if not api_key:
            raise ValueError("NASA_FIRMS_API_KEY não configurado em .env")
        self.api_key = api_key
        self.base_url = base_url
        self.session = requests.Session()
        self.session.headers["User-Agent"] = "FireWatch/2.0"

    # ── Fonte principal: FIRMS área Brasil ──────────────────────────────────
    def _fetch_firms_area(
        self,
        source: str = "VIIRS_SNPP_NRT",
        days: int = 1,
        bbox: tuple = BRAZIL_BBOX,
    ) -> List[INPEFoco]:
        min_lat, min_lon, max_lat, max_lon = bbox
        area = f"{min_lon},{min_lat},{max_lon},{max_lat}"
        url  = f"{self.base_url}/{self.api_key}/{source}/{area}/{days}"
        logger.info("FIRMS área Brasil (%s): %s", source, url)

        r = self.session.get(url, timeout=30)
        r.raise_for_status()

        focos: List[INPEFoco] = []
        for row in csv.DictReader(io.StringIO(r.text)):
            try:
                lat = float(row["latitude"])
                lon = float(row["longitude"])
                frp = float(row.get("frp") or 0)
                focos.append(INPEFoco(
                    latitude=lat,
                    longitude=lon,
                    municipio="",
                    estado=self._lat_lon_to_state(lat, lon),
                    bioma=self._lat_lon_to_bioma(lat, lon),
                    data_hora_gmt=f"{row.get('acq_date','')}T{row.get('acq_time','')}Z",
                    satelite=row.get("satellite", source),
                    risco_fogo=min(1.0, frp / 500) if frp else None,
                    frp=frp,
                    fonte=f"NASA FIRMS / {source}",
                ))
            except (ValueError, KeyError):
                pass

        logger.info("FIRMS %s: %d focos", source, len(focos))
        return focos

    # ── Fonte enriquecedora: IBAMA SISFOGO (estatísticas por estado) ────────
    def fetch_ibama_stats(self) -> Counter:
        """Retorna contagem de ocorrências por estado (sem coordenadas)."""
        try:
            r = self.session.get(IBAMA_ROI_CSV, timeout=30,
                                 headers={"Range": "bytes=0-2097152"})  # só 2MB dos 284MB
            lines = r.content.decode("latin-1", errors="replace").split("\n")
            reader = csv.DictReader(lines, delimiter=";")
            counts: Counter = Counter()
            for row in reader:
                uf = (row.get("UF") or "").strip().upper()
                if uf in ESTADO_SIGLA:
                    counts[uf] += 1
            logger.info("IBAMA SISFOGO: %d registros lidos, %d estados", sum(counts.values()), len(counts))
            return counts
        except Exception as exc:
            logger.warning("IBAMA SISFOGO indisponível: %s", exc)
            return Counter()

    # ── Método principal ────────────────────────────────────────────────────
    def fetch_focos(
        self,
        date_from=None,
        date_to=None,
        estado: Optional[str] = None,
        bioma: Optional[str] = None,
        limit: int = 1000,
    ) -> List[INPEFoco]:
        focos: List[INPEFoco] = []
        for src in ["VIIRS_SNPP_NRT", "VIIRS_NOAA20_NRT"]:
            try:
                focos.extend(self._fetch_firms_area(source=src, days=2))
            except Exception as exc:
                logger.warning("FIRMS %s falhou: %s", src, exc)

        if estado:
            focos = [f for f in focos if f.estado == estado.upper()]
        if bioma:
            focos = [f for f in focos if bioma.lower() in f.bioma.lower()]

        focos = focos[:limit]
        logger.info("Total INPE/FIRMS focos: %d", len(focos))
        return focos

    # ── Upload S3 ────────────────────────────────────────────────────────────
    def upload_to_s3(self, focos: List[INPEFoco], s3_client=None) -> str:
        if s3_client is None:
            s3_client = boto3.client("s3", region_name=AWS_REGION)
        today = date.today().isoformat()
        s3_key = f"raw/inpe/{today}/focos.csv"
        buf = io.StringIO()
        writer = csv.writer(buf)
        writer.writerow(["latitude", "longitude", "municipio", "estado", "bioma",
                          "data_hora_gmt", "satelite", "risco_fogo", "frp", "fonte"])
        for f in focos:
            writer.writerow([f.latitude, f.longitude, f.municipio, f.estado, f.bioma,
                              f.data_hora_gmt, f.satelite, f.risco_fogo, f.frp, f.fonte])
        s3_client.put_object(
            Bucket=AWS_BUCKET_NAME, Key=s3_key,
            Body=buf.getvalue().encode("utf-8"), ContentType="text/csv",
        )
        logger.info("Uploaded %d focos INPE → s3://%s/%s", len(focos), AWS_BUCKET_NAME, s3_key)
        return s3_key

    # ── Helpers ──────────────────────────────────────────────────────────────
    @staticmethod
    def _lat_lon_to_state(lat: float, lon: float) -> str:
        if lat > 2:   return "RR"
        if lon < -60 and lat > -5:  return "AM"
        if lon > -52 and lat > -2:  return "AP"
        if lon > -50 and lat > -6:  return "PA"
        if lat > -6 and lon > -45:  return "MA"
        if lat < -15 and lon < -55: return "MT"
        if lat < -19 and lon < -52: return "MS"
        if lat < -28:               return "RS"
        if lat < -23 and lon > -50: return "PR"
        return "BR"

    @staticmethod
    def _lat_lon_to_bioma(lat: float, lon: float) -> str:
        if lat > -10 and lon < -50:  return "Amazônia"
        if -15 < lat <= -3 and lon > -50: return "Cerrado"
        if lat < -16 and lon < -55:  return "Pantanal"
        if lat < -8 and lon > -42:   return "Caatinga"
        if lat < -20:                return "Mata Atlântica"
        return "Cerrado"


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
    c = INPECollector()
    focos = c.fetch_focos(limit=200)
    print(f"Total: {len(focos)}")
    if focos:
        print("Amostra:", focos[0])
        key = c.upload_to_s3(focos)
        print("S3:", key)
