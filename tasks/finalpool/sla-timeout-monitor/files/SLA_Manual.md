# MCP Inc. Service Standards & Operations Handbook

_Last Updated: June 2024_



## 1. Purpose and Scope

This handbook outlines MCP Inc.’s operational standards, monitoring practices, and customer interaction principles.  
It defines both **customer-facing SLAs** and **internal operational reference guidelines**.  
Sections marked as “**Internal Policy**” are **not** part of the externally-committed SLA and are included for operational completeness only.



## 2. Internal System Availability Policy (Internal Use Only)

MCP maintains several internal benchmarks for monitoring service uptime across APIs, admin consoles, and core infrastructure.

### 2.1 Console and API Availability
- Automated health checks run every **five minutes** for API endpoints and management consoles.
- Availability is calculated on a **monthly rolling average** excluding approved maintenance windows.
- Any HTTP 5xx response or abnormal payload is logged as a service disruption in internal systems (not public SLA).

### 2.2 Maintenance Window
- A recurring **Maintenance Window** is scheduled on the **second Thursday of each month from 3:00 PM–4:00 PM (PT)**.
- During this period, some dashboards or administrative functions may be temporarily unavailable.
- Any downtime in this window is excluded from end‑user SLA metrics.



## 3. Incident Priority Definitions (Internal Classification)

Although distinct from customer SLA response levels, MCP internally categorizes incidents to support triage:

| Priority | Description | Example |
|----------|-------------|---------|
| P1 | Major service outage or resource unavailability that halts mission-critical functions. | API gateway offline |
| P2 | Service available but degraded or failing key functions. | Search returning incomplete results |
| P3 | Minor issues with negligible customer impact. | Cosmetic UI defect |

> _Note: These internal priority levels are for technical operations and do not override customer response time commitments._



## 4. Environment Recovery Guidelines (Internal Operations)

- In the event of Availability Zone (AZ) unavailability affecting internal test or pre-production environments, MCP will initiate recovery within **12 hours** of detection or authorization.
- Recovery involves:
  - Redeploying stacks from baseline templates
  - Restoring data from the last approved restore point
- This is a **best-effort** objective and independent of customer ticket processing.



## 5. Patch Management Policy (Internal Reference)

- **Critical security updates** are applied to internal assets within **10 business days** of vendor release.
- **Important updates** are applied within **two months** of vendor release.
- Applies to:
  - Supported operating systems
  - Pre-installed core application software
- This policy is unrelated to customer-facing ticket turnarounds.



## 6.  Core Service Level Agreement — Customer-Facing Commitment

This section contains the agreed standards for customer communication and ticket handling.



### 6.1 User Levels and Response Times

| User Level | First Reply Time | Second Reply Time (if first reply is overdue) |
|------------|-----------------|-----------------------------------------------|
| **Basic**  | 72 hours | 72 hours |
| **Pro**    | 36 hours   | 36 hours  |
| **Max**    | 24 hours   | 18 hours   |

**Notes:**
- **First Reply Time**: Maximum time from ticket creation to the first customer contact.
- **Second Reply Time**: If first reply exceeds the deadline, you must update the customer within this time frame.



### 6.2 Templates

_Note: The Placeholder in this section should be replaced to real values._

#### 6.2.1 Customer Apology Email Template

**Subject:** Update on Your Service Request {TICKET_NUMBER}

Dear Customer,  

We sincerely apologize for not responding to your service request {TICKET_NUMBER} within the promised timeframe.  

We commit to providing an initial solution or the latest status update within {SECOND_REPLY_TIME} hours, and will continue following up until the issue is fully resolved.  

For urgent matters, please contact us directly:  
Phone: 400-772-1234    

We apologize again for any inconvenience this may have caused.  

Best,  
MCP Inc., Customer Support Team  


#### 6.2.2 Manager Reminder Template

_Note: Please list tickets in **max → pro → basic** order._

**Subject:** [Overdue Alert] Tickets Exceeding First Reply SLA  

Dear Manager,  

The following tickets have exceeded the SLA first reply time. Please prioritize and coordinate processing:  

{TICKET_NUMBER}: {Level}
{TICKET_NUMBER}: {Level}
{TICKET_NUMBER}: {Level}  

Best,  
MCP Inc., Customer Support Team  



## 7. Additional Operational Metrics (Non-SLA)

These performance metrics are tracked for internal monitoring purposes only and have no bearing on customer SLAs.

### 7.1 Conformance Rate
- Calculated monthly as the percentage of internal performance targets achieved.
- Segmented by:
  - Infrastructure uptime
  - Average incident resolution by internal priority
  - Patch cycle completion rate

### 7.2 Service Credit Eligibility (Internal Reference to AWS Model)
- Service Credits (if issued) are applied as a **percentage discount** on future internal cross-department billing.
- Maximum internal service credit per month: **30% of the allocated operational budget for the affected service**.
- Credits are not transferable outside the organization.



## 8. Internal Reporting Workflow

1. **Detection**: Automated systems log uptime and incident metrics every five minutes.
2. **Classification**: Technical operations team assigns internal priority levels (P1, P2, P3).
3. **Action**: Appropriate recovery, patching, or monitoring adjustments.
4. **Documentation**: Metrics stored for quarterly performance review.



## 9. SLA Exclusions

The following do **not** count towards SLA performance metrics:
- Authorized maintenance during the scheduled monthly window.
- Downtime due to third-party upstream providers beyond MCP’s control.
- Customer-requested delays or refusal of recommended action.
- Failures in unsupported third-party software.



## 10. Glossary

- **First Reply Time:** Interval between ticket creation and first customer contact.
- **Second Reply Time:** Interval to follow-up after overdue first reply.
- **Maintenance Window:** Designated time for pre-scheduled service work.
- **Incident Recovery:** Process to restore unavailable systems or services.
- **Conformance Rate:** Measure of how often internal targets are met.



## 11. Revision History

| Version | Date       | Changes                                         | Author        |
|---------|------------|-------------------------------------------------|---------------|
| 1.0     | Jun 2024   | Initial release                                  | Ops Team      |
| 1.1     | Jun 2024   | Added internal operational sections & glossary   | Ops Team      |