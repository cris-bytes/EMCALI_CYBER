from __future__ import annotations
import re
import pandas as pd

CVE_RE = re.compile(r"^CVE-\d{4}-\d{4,}$", re.I)


def _cve(value):
    if pd.isna(value):
        return ''
    text = str(value).strip().upper()
    return text if CVE_RE.fullmatch(text) else ''


def _numeric(value, low, high):
    try:
        number = float(value)
        return number if pd.notna(number) and low <= number <= high else None
    except (TypeError, ValueError):
        return None


def summarize_provenance(data):
    data = data.copy()
    cvss = pd.to_numeric(data.get('cvss', pd.Series(dtype=float)), errors='coerce')
    epss = pd.to_numeric(data.get('epss', pd.Series(dtype=float)), errors='coerce')
    status = data.get('nvd_status', pd.Series(index=data.index, dtype='object')).astype('string').str.lower()
    source = data.get('cvss_source', pd.Series(index=data.index, dtype='object'))
    date = data.get('epss_date', pd.Series(index=data.index, dtype='object'))
    return {'rows': len(data), 'nvd_analyzed': int(status.eq('analyzed').sum()),
            'cvss_with_source': int((cvss.between(0,10) & source.notna()).sum()),
            'epss_with_date': int((epss.between(0,1) & date.notna()).sum())}


def integrate_enriched_file(base, enriched):
    if 'cve' not in base.columns or 'cve' not in enriched.columns:
        raise ValueError('Ambos conjuntos deben tener columna cve.')
    if 'nvd_status' not in enriched.columns or 'epss_date' not in enriched.columns:
        raise ValueError('Faltan metadatos de NVD/EPSS. Importe el archivo enriquecido, no el benchmark original.')
    lookup = enriched.copy()
    lookup['_cve_key'] = lookup['cve'].map(_cve)
    lookup = lookup[lookup['_cve_key'] != '']
    if lookup['_cve_key'].duplicated().any():
        duplicate = lookup.loc[lookup['_cve_key'].duplicated(), '_cve_key'].iloc[0]
        raise ValueError(f'CVE duplicado en archivo enriquecido: {duplicate}. Resolver antes de importar.')
    lookup = lookup.set_index('_cve_key')
    result = base.copy()
    for field in ['cvss', 'epss', 'epss_percentile']:
        if field not in result.columns:
            result[field] = float('nan')
        result[field] = pd.to_numeric(result[field], errors='coerce').astype(float)
    metadata = ['cvss_version','cvss_vector','cvss_source','cvss_severity',
                'epss_date','nvd_status','nvd_url','nvd_published','nvd_modified',
                'enriched_at','nvd_error','epss_error']
    for field in metadata:
        if field not in result.columns:
            result[field] = pd.Series(index=result.index, dtype='object')
        else:
            result[field] = result[field].astype('object')
    matched = cvss_verified = epss_verified = 0
    for idx, row in result.iterrows():
        key = _cve(row['cve'])
        if not key or key not in lookup.index:
            continue
        matched += 1
        rec = lookup.loc[key]
        nvd_status = str(rec.get('nvd_status', '')).lower()
        cvss = _numeric(rec.get('cvss'), 0, 10)
        epss = _numeric(rec.get('epss'), 0, 1)
        cvss_source = rec.get('cvss_source')
        epss_date = rec.get('epss_date')
        nvd_ok = nvd_status not in ('', 'nan', 'none', 'query_error', 'not_found') and pd.notna(cvss_source)
        epss_ok = pd.notna(epss_date) and str(epss_date).lower() not in ('', 'nan', 'none') and pd.isna(rec.get('epss_error'))
        if cvss is not None and nvd_ok:
            result.at[idx, 'cvss'] = cvss
            cvss_verified += 1
            if 'severity' in result.columns:
                result.at[idx, 'severity'] = ('Critical' if cvss >= 9 else 'High' if cvss >= 7 else 'Medium' if cvss >= 4 else 'Low')
        if epss is not None and epss_ok:
            result.at[idx, 'epss'] = epss
            epss_verified += 1
            percentile = _numeric(rec.get('epss_percentile'), 0, 1)
            if percentile is not None:
                result.at[idx, 'epss_percentile'] = percentile
        for field in metadata:
            value = rec.get(field)
            if pd.notna(value):
                result.at[idx, field] = str(value)
        if 'exploitability' in result.columns:
            kev = str(row.get('cisa_kev', '')).lower() in ('true','1','yes','sí','si')
            if kev or (epss is not None and epss_ok and epss >= .7) or (cvss is not None and nvd_ok and cvss >= 9):
                result.at[idx, 'exploitability'] = 'High'
            elif (epss is not None and epss_ok and epss >= .2) or (cvss is not None and nvd_ok and cvss >= 6):
                result.at[idx, 'exploitability'] = 'Medium'
            elif epss_ok or nvd_ok:
                result.at[idx, 'exploitability'] = 'Low'
        if 'data_quality_flags' in result.columns:
            flags = str(row.get('data_quality_flags') or '')
            parts = [f.strip() for f in flags.split(';') if f.strip() and f.strip().lower() not in ('nan','none')]
            if cvss is not None and nvd_ok:
                parts = [f for f in parts if f != 'CVSS no disponible']
            if epss is not None and epss_ok:
                parts = [f for f in parts if f != 'EPSS no disponible']
            result.at[idx, 'data_quality_flags'] = '; '.join(parts)
    summary = {'matched': matched, 'unmatched': len(base)-matched,
               'cvss_verified': cvss_verified, 'epss_verified': epss_verified,
               'source_file_rows': len(enriched), 'source_audit': summarize_provenance(enriched),
               'note': 'Metadatos del archivo importado; no constituyen verificación independiente en línea.'}
    return result, summary
