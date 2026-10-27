"""Derive each company's own careers page from its job links.

A job link points at one posting on the company's applicant-tracking system (Workday, Greenhouse,
Ashby, ...). Each system has a predictable "all jobs at this company" page, so the careers page is
the posting URL cut back to that root. Links that go to job boards (Adzuna, WhatJobs, ...) say
nothing about the company's own site and are ignored; a company seen only through boards gets no
careers page (the dashboard offers a search link instead).
"""
import re
import urllib.parse as U
from collections import Counter

# hosts that relist other companies' jobs: not the employer's own site
AGGREGATORS = re.compile(
    r"(^|\.)(adzuna|energyjobline|whatjobs|careers-page|4dayweek|himalayas|linkedin|indeed|glassdoor|ziprecruiter|"
    r"lensa|jooble|dice|simplify|builtin|wellfound|jobgether|monster|careerbuilder|snagajob|jobright|"
    r"remoteok|remotive|weworkremotely|freehire|joblist|jobleads|learn4good|recruit\.net|tealhq|seek)\.", re.I)


def root_of(url):
    """Careers-page root for one posting URL, or None when it can't be told / isn't the employer's."""
    try:
        p = U.urlsplit(url)
    except ValueError:
        return None
    host, parts = p.netloc.lower(), [x for x in p.path.split("/") if x]
    if not host or AGGREGATORS.search(host):
        return None
    base = f"https://{host}"
    seg = lambda i: parts[i] if len(parts) > i else ""
    if host.endswith("myworkdayjobs.com"):
        # /[en-US/]<site>/job/<location>/<title>_<id>
        site = next((x for x in parts if not re.fullmatch(r"[a-z]{2}-[A-Z]{2}", x)), "")
        return f"{base}/{site}" if site and site not in ("job", "details") else base
    if host.endswith("myworkdaysite.com"):
        # /recruiting/<tenant>/<site>/job/...
        return f"{base}/recruiting/{seg(1)}/{seg(2)}" if seg(0) == "recruiting" and seg(2) else None
    if host in ("boards.greenhouse.io", "job-boards.greenhouse.io"):
        return f"https://job-boards.greenhouse.io/{seg(0)}" if seg(0) and seg(0) != "embed" else None
    if host in ("jobs.ashbyhq.com", "jobs.lever.co", "jobs.gem.com"):
        return f"{base}/{seg(0)}" if seg(0) else None
    if host == "jobs.smartrecruiters.com":
        return f"{base}/{seg(0)}" if seg(0) else None
    if host == "apply.workable.com":
        return f"{base}/{seg(0)}" if seg(0) and seg(0) != "j" else None   # /j/<id> short links carry no company
    if host == "ats.rippling.com":
        return f"{base}/{seg(0)}/jobs" if seg(0) else None
    if host.endswith("oraclecloud.com"):
        m = re.search(r"(/hcmUI/CandidateExperience/[^/]+/sites/[^/]+)", p.path)
        return base + m.group(1) if m else None
    if re.fullmatch(r"recruiting\d*\.ultipro\.(com|ca)", host) or host.endswith(".rec.pro.ukg.net"):
        # /<tenant>/JobBoard/<board id>/OpportunityDetail?...
        return f"{base}/{seg(0)}/JobBoard/{seg(2)}" if seg(1).lower() == "jobboard" and seg(2) else None
    if host.endswith(".icims.com"):
        return f"{base}/jobs/search"
    if host == "jobs.dayforcehcm.com":
        # /<locale>/<company>/<portal>/jobs/<id>
        i = parts.index("jobs") if "jobs" in parts else len(parts)
        return base + "/" + "/".join(parts[:i]) if i else None
    if host.endswith("ycombinator.com") and seg(0) == "companies" and seg(1):
        return f"https://www.ycombinator.com/companies/{seg(1)}/jobs"
    if host in ("recruiting.paylocity.com", "www.paycomonline.net", "myjobs.adp.com", "workforcenow.adp.com",
                "www.google.com"):
        return None  # shared portals whose company root isn't in the posting link
    # the company's own domain (careers.roblox.com/jobs/123?gh_jid=...): its home is the careers site
    return base


def careers_pages(jobs):
    """{company: careers root} using the root seen most often across that company's postings."""
    seen = {}
    for j in jobs:
        r = root_of(j.get("url") or "")
        if r:
            seen.setdefault(j["company"], Counter())[r] += 1
    return {co: c.most_common(1)[0][0] for co, c in seen.items()}
