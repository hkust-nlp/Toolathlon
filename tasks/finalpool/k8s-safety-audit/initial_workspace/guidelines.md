# Requirements

- **Cluster Scope:** Audit running pods in 4 namespaces(production, staging, dev, test).
- **Scoring:** Follow the detailed risk scoring rules below.
- **Result Format:** For each container, output one row with the following columns:

| Namespace | Pod Name | Container Name | Privileged Mode | Image | Creation Time | Node | Risk Score | Risk Level |

## Column Details
1. **Namespace** — The Kubernetes namespace of the Pod.
2. **Pod Name** — Full Pod name.
3. **Container Name** — Name of the container inside the Pod.
4. **Privileged Mode** — True/False.
5. **Image** — Full image name with tag.
6. **Creation Time** — Pod creation timestamp in UTC (ISO 8601 format).
7. **Node** — Node name where the Pod is scheduled.
8. **Risk Score** — Calculated according to `guidelines.md`.
9. **Risk Level** — High / Medium / Low based on the Risk Score thresholds.

# Kubernetes Security Audit — Risk Scoring Guidelines

This document defines the **container-level risk scoring rules** for Kubernetes security review, along with risk level classification and reporting recommendations.

---

## 1. Scoring Overview

- **Unit of scoring:** Each container is scored individually.
- **Maximum score:** 10 points.
- **Privileged containers:** If `privileged: true`, score = 10 points and marked **High Risk** immediately (no further additions).
- **Non-privileged containers:** Sum points from the table below; cap the total score at **10**.

---

## 2. Risk Factor Table

| Factor | Points | Rule |
|--------|-------:|------|
| **Privileged Mode** | **10** | `securityContext.privileged: true`. Immediate high risk, skip other checks. |
| **Sensitive Capabilities** | +4 each, **max +6** | Count only from the high-risk set: `CAP_SYS_ADMIN`, `CAP_SYS_MODULE`, `CAP_SYS_PTRACE`, `CAP_NET_ADMIN`, `CAP_SYS_TIME`, `CAP_SYS_BOOT`. Ignore other capabilities. |
| **Host Path Mount** | +5 or +3 | `+5` if `/var/run/docker.sock` is mounted. Otherwise `+3` if mounting any sensitive path: `/etc`, `/root`, `/proc`, `/sys`, `/var/lib/kubelet`, `/var/run/containerd`. Do not stack with `+5`. |
| **Host Network** | +2 | `spec.hostNetwork: true`. |
| **Host PID Namespace** | +2 | `spec.hostPID: true`. |
| **Host IPC Namespace** | +2 | `spec.hostIPC: true`. |
| **Allow Privilege Escalation** | +2 | `allowPrivilegeEscalation: true`. |
| **Running as Root** | +2 | Any of: `runAsUser: 0`, `runAsNonRoot: false`, or default UID=0 without override. |
| **Writable Root Filesystem** | +1 | `readOnlyRootFilesystem: false`. |

**Calculation order:**
1. If privileged, set score to 10.
2. Else, sum factors from the table and cap at 10.

---

## 3. Risk Level Classification

| Risk Level | Score Range | Description |
|------------|-------------|-------------|
| **High** | ≥ 8 | Likely full or near-full host compromise capability. |
| **Medium** | 4–7 | Multiple sensitive settings combined, but not full host control. |
| **Low** | 0–3 | Minimal privileges, follows least privilege principle. |

---

## 4. Examples

**Example 1**  
```yaml
securityContext:
  privileged: true
```
→ Score = 10 → **High Risk**

**Example 2**

* Non-privileged
* `CAP_SYS_ADMIN` (+4)
* `/var/run/docker.sock` mounted (+5)
  → Score = 9 → **High Risk**

**Example 3**

* Read-only root filesystem
* No sensitive capabilities
* No host namespaces
  → Score = 0 → **Low Risk**

**Example 4**

* Non-privileged
* `CAP_NET_ADMIN` (+4)
* `hostNetwork: true` (+2)
* `allowPrivilegeEscalation: true` (+2)
  → Score = 8 → **High Risk**

---

## 5. Reporting to Google Sheets

When appending audit results to the Google Sheet, use the following columns:

\| Namespace | Pod Name | Container Name | Privileged Mode | Image | Creation Time | Node | Risk Score | Risk Level | 

Example row:

```
default | web-app-1-5c7d9f4f8c-xtj9p | nginx | True | nginx:1.19 | 2024-01-15 | node-1 | 10 | High 
```


