from __future__ import annotations
import requests


def query_nvd_cve(cve_id: str, timeout_sec: int = 20) -> dict | None:
    cve_id = (cve_id or '').strip()
    if not cve_id or cve_id == 'N/A' or ',' in cve_id:
        return None
    try:
        resp = requests.get('https://services.nvd.nist.gov/rest/json/cves/2.0', params={'cveId': cve_id}, timeout=timeout_sec)
        resp.raise_for_status()
        payload = resp.json()
        vulns = payload.get('vulnerabilities', [])
        if not vulns:
            return None
        cve = vulns[0].get('cve', {})
        descriptions = cve.get('descriptions', [])
        desc = next((d.get('value') for d in descriptions if d.get('lang') == 'en'), None)
        return {'cve_id': cve_id, 'published': cve.get('published'), 'last_modified': cve.get('lastModified'), 'description': desc, 'source': 'NVD'}
    except Exception:
        return None
