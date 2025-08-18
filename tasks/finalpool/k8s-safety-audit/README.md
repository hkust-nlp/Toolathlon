## Project Overview

This project performs a comprehensive Kubernetes security audit across all namespaces and pods in a cluster. The goal is to assess container security configurations and write the audit results to a Google Sheet under the "Week3" worksheet, following established risk scoring guidelines.

---

## 1. Data Sources

* **Kubernetes Cluster**: Target cluster configuration specified by `cluster241-config.yaml`. The audit examines all running pods across all namespaces for security-related configurations.

* **Risk Scoring Guidelines**: Defined in `guidelines.md`, which provides a comprehensive scoring system for container security risks based on privileged mode, capabilities, host mounts, and other security contexts.

* **Google Sheets Integration**: Results are appended to the "Kubernetes Security Audit" spreadsheet under the "Week3" worksheet, maintaining consistency with existing "Week1" and "Week2" data.

---

## 2. Security Audit Structure

### Container-Level Risk Assessment

* **Scope**: All containers in all pods across all namespaces
* **Risk Factors Evaluated**:
  * Privileged mode (10 points - immediate high risk)
  * Sensitive capabilities (CAP_SYS_ADMIN, CAP_SYS_MODULE, etc.)
  * Host path mounts (especially /var/run/docker.sock)
  * Host network/PID/IPC namespace usage
  * Privilege escalation settings
  * Root user execution
  * Writable root filesystem

### Risk Level Classification

* **High Risk** (e8 points): Containers with significant security vulnerabilities
* **Medium Risk** (4-7 points): Containers with multiple concerning settings
* **Low Risk** (0-3 points): Containers following security best practices

### Output Format

Each container generates one row with the following columns:

| Namespace | Pod Name | Container Name | Privileged Mode | Image | Creation Time | Node | Risk Score | Risk Level |

---

## 3. GT Solution Acquisition

The ground truth (GT) solution is generated through a combination of:

1. **Benchmark Data**: A predefined set of expected container configurations with their security assessments stored in the evaluation script (`check_google_sheet.py:106-117`).

2. **Live Cluster Data**: Real-time information retrieved from the Kubernetes cluster including:
   * Actual pod names (resolved from prefixes in benchmark)
   * Pod creation timestamps 
   * Node assignments

3. **GT Generation Process**:
   ```python
   # The evaluation system:
   # 1. Loads benchmark rows with expected security configurations
   benchmark_rows = load_benchmark_rows()
   
   # 2. Resolves actual pod names and retrieves live cluster data
   gt_rows = build_gt_from_live(benchmark_rows, kubeconfig_path)
   
   # 3. Compares agent results against the generated GT
   diffs = compare_week3_with_gt(week3_rows, gt_rows)
   ```

4. **Expected Containers**: The benchmark includes 10 containers across different namespaces:
   * **production**: monitoring-agent (High Risk), payment-gateway (Low Risk), time-sync (Medium Risk)
   * **dev**: build-runner (High Risk), inventory-api (Low Risk)  
   * **staging**: diag-tools (Medium Risk), auth-service (Low Risk)
   * **test**: net-tapper (Medium Risk), cache-service (Low Risk), search-engine (Low Risk)

The GT solution validates that the agent correctly identifies all containers, applies the risk scoring methodology accurately, and formats the results properly in the Google Sheet.