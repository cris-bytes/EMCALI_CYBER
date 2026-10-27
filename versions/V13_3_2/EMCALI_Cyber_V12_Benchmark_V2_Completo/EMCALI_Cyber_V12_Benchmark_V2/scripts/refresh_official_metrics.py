#!/usr/bin/env python3
"""
Refresh official CVSS from NIST NVD and EPSS from FIRST for EMCALI Cyber V12 Benchmark V2.
Input/output are CSV to keep dependencies minimal. For XLSX, export Benchmark_Master to CSV first
or adapt with your preferred local spreadsheet library.
"""
import csv, json, time, urllib.parse, urllib.request, argparse, datetime

NVD="https://services.nvd.nist.gov/rest/json/cves/2.0?cveId={}"
EPSS="https://api.first.org/data/v1/epss?cve={}"

def get_json(url, timeout=30):
    req=urllib.request.Request(url,headers={"User-Agent":"EMCALI-Cyber-V12-Benchmark/2.0"})
    with urllib.request.urlopen(req,timeout=timeout) as r:
        return json.load(r)

def nvd_metric(cve):
    d=get_json(NVD.format(urllib.parse.quote(cve)))
    vs=d.get("vulnerabilities",[])
    if not vs: return {}
    c=vs[0].get("cve",{})
    m=c.get("metrics",{})
    for key,ver in [("cvssMetricV40","4.0"),("cvssMetricV31","3.1"),("cvssMetricV30","3.0"),("cvssMetricV2","2.0")]:
        if m.get(key):
            item=m[key][0]
            data=item.get("cvssData",{})
            return {"cvss_official":data.get("baseScore"),"cvss_version":ver,"cvss_vector":data.get("vectorString")}
    return {}

def epss_metric(cve):
    d=get_json(EPSS.format(urllib.parse.quote(cve)))
    arr=d.get("data",[])
    if not arr: return {}
    x=arr[0]
    return {"epss_official":x.get("epss"),"epss_percentile":x.get("percentile"),"epss_date":x.get("date")}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("input_csv")
    ap.add_argument("output_csv")
    ap.add_argument("--nvd-delay",type=float,default=6.0,help="Delay between NVD calls without API key")
    args=ap.parse_args()
    with open(args.input_csv,encoding="utf-8-sig",newline="") as f:
        rows=list(csv.DictReader(f))
    for i,row in enumerate(rows,1):
        cve=row["cve"].strip()
        print(f"[{i}/{len(rows)}] {cve}")
        try:
            row.update(nvd_metric(cve))
        except Exception as e:
            row["nvd_error"]=str(e)
        time.sleep(args.nvd_delay)
        try:
            row.update(epss_metric(cve))
        except Exception as e:
            row["epss_error"]=str(e)
        row["official_metrics_retrieved_at_utc"]=datetime.datetime.now(datetime.timezone.utc).isoformat()
    fields=[]
    for r in rows:
        for k in r:
            if k not in fields: fields.append(k)
    with open(args.output_csv,"w",encoding="utf-8-sig",newline="") as f:
        w=csv.DictWriter(f,fieldnames=fields); w.writeheader(); w.writerows(rows)
    print("Saved",args.output_csv)

if __name__=="__main__":
    main()
