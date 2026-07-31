# Staging2 security-header verification checklist

**Status:** plan-only, review-required, explicit HOLD on external changes.

**Evidence limitation:** Kiro could not read the WordPress repository in its
review session because filesystem access was denied. The checklist below is a
first-principles safety draft, not site-specific verification. Confirm every
site fact against authorized monitor/config evidence before acting.

The deployed convmem checkout remains at
`76126e07a97187f68d925dd8b431d2d03967084f` through 2026-08-07 00:00 UTC.

## Scope and observations

This concerns only the external staging site
`staging2.willowyhollow.com` and these paired monitor observations:

- CSP: `obs_staging2_monitor_csp-missing`, `ver_staging2_mon_csp`
- HSTS: `obs_staging2_monitor_header-hsts`, `ver_staging2_mon_hsts`
- Referrer-Policy: `obs_staging2_monitor_referrer-policy`,
  `ver_staging2_mon_referrer-policy`

The practice repository is an audit/documentation source only. No database,
WordPress content, plugin, server, cache, service, or external configuration
may be changed by this plan.

## Evidence to collect before remediation

For each header independently, record:

1. The exact monitor URL, HTTP method, expected status codes, assertion rule,
   retry behavior, and last known passing timestamp.
2. Whether the monitor checks presence, exact value, duplicates, or only one
   response path; also confirm HTTPS versus HTTP for HSTS.
3. The version-controlled server/application configuration locations that
   could set or strip the header: vhost, `.htaccess`, WordPress hook/plugin,
   reverse proxy, CDN, or cache layer.
4. Last deployment, plugin, proxy, or cache change before the first failure.
5. Whether a prior approved decision specifies the intended final value.

Do not infer a live header from a practice file. Do not issue an external
request, alter a monitor, or inspect a database as part of this plan.

## Root-cause classification

Classify each header separately:

- **A — monitor failure:** wrong URL/path, HTTP instead of HTTPS for HSTS,
  TLS failure, transient timeout, or assertion mismatch.
- **B — deployment drift:** the header previously passed and a deploy, plugin,
  proxy, or cache change removed or overrode it.
- **C — never deployed:** no passing evidence exists and the intended setting
  was never applied to staging2.

Do not choose remediation until the class and evidence timestamp are recorded.

## Header semantics to verify

These are review criteria, not authorized final values:

| Header | Verification criteria | Hard caution |
|---|---|---|
| CSP | Enforced `Content-Security-Policy` response header, not only `Report-Only` or a meta tag; policy must be compatible with the actual staging app and reviewed for unsafe broad sources. | Do not invent a policy or add a reporting endpoint without knowing its recipient. |
| HSTS | Present on HTTPS responses; monitor must probe HTTPS; confirm an appropriate `max-age`. | Never add `preload` or submit staging2 to a preload list without explicit authorization. |
| Referrer-Policy | Present on intended HTML responses; confirm the chosen privacy behavior and absence of conflicting duplicates. | Changing from permissive to restrictive behavior may affect analytics and is an external behavioral change. |

The exact final header string is a Ryan authorization field, not an inference
from this checklist.

## Acceptance criteria for a future authorized change

Close a header observation only when:

1. The staging2 monitor passes on the intended HTTPS/HTTP path.
2. The value meets the approved semantics and no duplicate header conflicts.
3. The root cause A/B/C and evidence window are documented.
4. The version-controlled deployment source contains the change.
5. A post-change monitor result confirms persistence after relevant cache or
   deployment boundaries.
6. Ryan authorizes any observation closure or ledger write separately.

## Authorization boundary

Before any external operation, Ryan must name all three:

- **Resource:** exact config file, plugin setting, monitor, or service;
- **Operation:** add, replace, remove, or verify the header/probe;
- **Final value:** exact header string or configuration line.

No approval is implied by a failed monitor, this plan, or a passing practice
audit. Rollback must be identified before execution; HSTS preload is treated as
high-risk and prohibited for staging by default.

**Verdict: HOLD.** This checklist supports future read-only evidence review and
authorization preparation only. It does not authorize WordPress, staging2,
monitor, service, or external configuration changes.
