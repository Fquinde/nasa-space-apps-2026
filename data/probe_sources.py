"""
TERRAIN-X Source Verification Script
Probes official NASA, PDS, ODE, Trek, and POWER endpoints.
Generates an audit report for docs/SOURCES_STATUS.md.
"""
import json
import time
import urllib.parse
from datetime import datetime, timezone
import requests

PROBES = [
    {
        "source": "NASA CMR Collections API",
        "url": "https://cmr.earthdata.nasa.gov/search/collections.json?keyword=NASADEM&page_size=1",
        "method": "GET",
        "auth": False,
        "notes": "Queries NASA Common Metadata Repository for NASADEM collections dynamically."
    },
    {
        "source": "NASA CMR-STAC Catalog",
        "url": "https://cmr.earthdata.nasa.gov/stac",
        "method": "GET",
        "auth": False,
        "notes": "SpatioTemporal Asset Catalog endpoint for CMR datasets."
    },
    {
        "source": "NASA CMR ASTER GDEM Search",
        "url": "https://cmr.earthdata.nasa.gov/search/collections.json?short_name=ASTGTM&version=003&page_size=1",
        "method": "GET",
        "auth": False,
        "notes": "ASTER Global Digital Elevation Model V003 collection search in CMR."
    },
    {
        "source": "NASA POWER Daily API",
        "url": "https://power.larc.nasa.gov/api/temporal/daily/point?parameters=T2M,PRECTOTCORR&community=RE&longitude=-13.5&latitude=29.0&start=20230101&end=20230105&format=JSON",
        "method": "GET",
        "auth": False,
        "notes": "Daily meteorological and solar climatology from NASA POWER for Lanzarote candidate site."
    },
    {
        "source": "NASA PDS API",
        "url": "https://pds.nasa.gov/api/search/1/products?q=lroc&limit=1",
        "method": "GET",
        "auth": False,
        "notes": "NASA Planetary Data System Search API for metadata discovery."
    },
    {
        "source": "Washington University ODE REST API (Moon)",
        "url": "https://oderest.rsl.wustl.edu/live2/?target=moon&query=product&pt=LOLA_EDR&output=JSON&limit=1",
        "method": "GET",
        "auth": False,
        "notes": "Orbital Data Explorer REST service for Moon LOLA data products."
    },
    {
        "source": "Washington University ODE REST API (Mars)",
        "url": "https://oderest.rsl.wustl.edu/live2/?target=mars&query=product&pt=MOLA_MEGDR&output=JSON&limit=1",
        "method": "GET",
        "auth": False,
        "notes": "Orbital Data Explorer REST service for Mars MOLA topography datasets."
    },
    {
        "source": "NASA Moon Trek WMTS Capabilities",
        "url": "https://trek.nasa.gov/tiles/Moon/EQ/LRO_LOLA_ClrShade_Global_128ppd_v04/1.0.0/WMTSCapabilities.xml",
        "method": "GET",
        "auth": False,
        "notes": "NASA Moon Trek WMTS visual mosaic capabilities for LOLA Color Shaded relief."
    },
    {
        "source": "NASA Mars Trek WMTS Capabilities",
        "url": "https://trek.nasa.gov/tiles/Mars/EQ/Mars_MGS_MOLA_ClrShade_merge_global_463m/1.0.0/WMTSCapabilities.xml",
        "method": "GET",
        "auth": False,
        "notes": "NASA Mars Trek WMTS visual mosaic capabilities for MOLA shaded relief."
    },
    {
        "source": "NASA HLS LP DAAC Endpoint",
        "url": "https://cmr.earthdata.nasa.gov/search/collections.json?short_name=HLSL30&page_size=1",
        "method": "GET",
        "auth": False,
        "notes": "Harmonized Landsat Sentinel-2 (HLS L30) collection catalog search."
    },
    {
        "source": "NASA EMIT Mineral Identification (EMITL2BMIN)",
        "url": "https://cmr.earthdata.nasa.gov/search/collections.json?short_name=EMITL2BMIN&page_size=1",
        "method": "GET",
        "auth": False,
        "notes": "Earth Surface Mineral Dust Source Investigation L2B mineral identification collection."
    },
    {
        "source": "USGS Astrogeology Unified Geologic Map of the Moon",
        "url": "https://astrogeology.usgs.gov/search/map/Moon/Geology/Unified_Geologic_Map_of_the_Moon_GIS_v2/",
        "method": "GET",
        "auth": False,
        "notes": "USGS landing page / publication reference for Unified Geologic Map of the Moon."
    }
]

def run_probes():
    results = []
    print("Testing official NASA, PDS, ODE, and Planetary APIs...")
    for probe in PROBES:
        name = probe["source"]
        url = probe["url"]
        print(f"-> Probing: {name} ...", end=" ", flush=True)
        t0 = time.time()
        try:
            resp = requests.get(url, timeout=12, headers={"User-Agent": "TERRAIN-X-ScienceProbe/1.0"})
            elapsed = time.time() - t0
            content_type = resp.headers.get("Content-Type", "unknown")
            status_code = resp.status_code
            status_desc = "OK" if status_code < 400 else f"HTTP {status_code}"
            print(f"[{status_code}] ({elapsed:.2f}s)")
            results.append({
                "source": name,
                "url": url,
                "status_code": status_code,
                "status_desc": status_desc,
                "latency_s": round(elapsed, 2),
                "auth_required": probe["auth"],
                "content_type": content_type,
                "notes": probe["notes"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
        except Exception as e:
            elapsed = time.time() - t0
            print(f"[FAIL: {type(e).__name__}]")
            results.append({
                "source": name,
                "url": url,
                "status_code": None,
                "status_desc": f"Connection Error: {str(e)}",
                "latency_s": round(elapsed, 2),
                "auth_required": probe["auth"],
                "content_type": "none",
                "notes": probe["notes"],
                "timestamp": datetime.now(timezone.utc).isoformat()
            })
    return results

if __name__ == "__main__":
    res = run_probes()
    with open("probe_results.json", "w", encoding="utf-8") as f:
        json.dump(res, f, indent=2)
    print("Probe completed. Saved to probe_results.json")

