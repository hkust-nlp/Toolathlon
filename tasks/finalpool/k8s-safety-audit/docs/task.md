# Task: Kubernetes Security Audit

## Objective
Perform a security audit on the Kubernetes cluster and append the results to the **`Kubernetes Security Audit`** Google Sheet under the **Week3** worksheet. The data must follow the same column order and formatting style used in **Week1** and **Week2**.

---

## Requirements

- **Cluster Scope:** Audit running pods in 4 namespaces(production, staging, dev, test).
- **Scoring:** Follow the detailed risk scoring rules defined in [`guidelines.md`] in the workspace.
- **Result Format:** For each container, output one row with the following columns:

| Namespace | Pod Name | Container Name | Privileged Mode | Image | Creation Time | Node | Risk Score | Risk Level |

### Column Details
1. **Namespace** — The Kubernetes namespace of the Pod.
2. **Pod Name** — Full Pod name.
3. **Container Name** — Name of the container inside the Pod.
4. **Privileged Mode** — True/False.
5. **Image** — Full image name with tag.
6. **Creation Time** — Pod creation timestamp in UTC (ISO 8601 format).
7. **Node** — Node name where the Pod is scheduled.
8. **Risk Score** — Calculated according to `guidelines.md`.
9. **Risk Level** — High / Medium / Low based on the Risk Score thresholds.

