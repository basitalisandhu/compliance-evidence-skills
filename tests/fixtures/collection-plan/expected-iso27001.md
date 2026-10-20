## Evidence collection plan: Example Pty Ltd

Framework iso27001-2022, audit period 2026-07-01 to 2026-12-31, evaluated as of 2026-11-15. Evidence statuses come from the manifest.

8 controls in scope: 1 met, 4 missing, 1 stale, 1 overdue, 1 without an applicable request.
17 requests selected, 19 request rows: 8 met, 9 missing, 1 stale, 1 overdue. 3 requests are not applicable unless their system is added.

### Controls

| Control | Topic (paraphrase) | Status | Requests |
|---|---|---|---|
| A.5.1 | Security policies exist, are approved and reach the people they apply to | missing | HR-03, POL-01 |
| A.5.18 | Access is granted, reviewed and removed on purpose | overdue | ACC-01, ACC-02, IAM-01, IDP-03 |
| A.6.3 | People receive security awareness training | stale | HR-02 |
| A.7.4 |  | gap: no request in the catalogue | none |
| A.8.5 | Sign-in uses strong methods such as multi-factor authentication | missing | IAM-01, IAM-02, IDP-01, IDP-02 |
| A.8.13 | Copies of data and systems exist and restoring them is tried | missing | BKP-01 |
| A.8.15 | Systems keep a tamper-resistant record of who did what | met | LOG-01 |
| A.8.32 | Changes go through a reviewed, recorded process | missing | CHG-01, CHG-02 |

A control takes the worst status of its rows (met, then missing, stale, overdue). A status says whether a file was collected in time, not whether the control works.

### PBC request list

| Request | Slot | Due | Item | Controls | System | Owner | Status | Evidence file | Collected |
|---|---|---|---|---|---|---|---|---|---|
| ACC-01 | Q1 | 2026-09-30 | Access review sign-off for in-scope systems | A.5.18 | entra | Identity administrator | overdue |  |  |
| CHG-01 | Q1 | 2026-09-30 | GitHub branch protection or rulesets on the release branch | A.8.32 | github | Engineering lead | met | github/branch-protection.json | 2026-07-14 |
| IAM-01 | Q1 | 2026-09-30 | AWS IAM credential report | A.5.18 A.8.5 | aws | Cloud platform lead | met | aws/credential-report.csv | 2026-07-20 |
| IDP-01 | Q1 | 2026-09-30 | Entra Conditional Access policies export | A.8.5 | entra | Identity administrator | met | m365/conditional-access-policies.json | 2026-09-12 |
| IDP-03 | Q1 | 2026-09-30 | Entra privileged role assignments | A.5.18 | entra | Identity administrator | met | m365/privileged-roles-2026-07.json | 2026-07-08 |
| ACC-01 | Q2 | 2026-12-31 | Access review sign-off for in-scope systems | A.5.18 | entra | Identity administrator | missing |  |  |
| ACC-02 | population | 2026-12-31 | Leavers list with account disablement dates | A.5.18 | hr-system | People operations lead | met | hr/leavers-2026-h2.csv | 2026-11-02 |
| BKP-01 | period | 2026-12-31 | AWS Backup plans and protected resources | A.8.13 | aws | Cloud platform lead | missing |  |  |
| CHG-01 | Q2 | 2026-12-31 | GitHub branch protection or rulesets on the release branch | A.8.32 | github | Engineering lead | missing |  |  |
| CHG-02 | population | 2026-12-31 | Merged pull requests with approvals for the period | A.8.32 | github | Engineering lead | missing |  |  |
| HR-02 | period | 2026-12-31 | Security awareness training completion report | A.6.3 | hr-system | People operations lead | stale | hr/training-completion.csv | 2026-07-05 |
| HR-03 | period | 2026-12-31 | Policy acknowledgement records | A.5.1 | hr-system | People operations lead | missing |  |  |
| IAM-01 | Q2 | 2026-12-31 | AWS IAM credential report | A.5.18 A.8.5 | aws | Cloud platform lead | missing |  |  |
| IAM-02 | period | 2026-12-31 | AWS account password policy and account summary | A.8.5 | aws | Cloud platform lead | met | aws/password-policy.json | 2026-10-30 |
| IDP-01 | Q2 | 2026-12-31 | Entra Conditional Access policies export | A.8.5 | entra | Identity administrator | missing |  |  |
| IDP-02 | period | 2026-12-31 | Entra security defaults and authentication methods policy | A.8.5 | entra | Identity administrator | missing |  |  |
| IDP-03 | Q2 | 2026-12-31 | Entra privileged role assignments | A.5.18 | entra | Identity administrator | missing |  |  |
| LOG-01 | period | 2026-12-31 | AWS CloudTrail trails and logging status | A.8.15 | aws | Cloud platform lead | met | aws/cloudtrail-trails.json | 2026-09-10 |
| POL-01 | period | 2026-12-31 | Approved information security policy set with approval dates | A.5.1 | document | Security lead | met | documents/policies/information-security-policy.pdf | 2026-08-01 |

Notes:

- CHG-01 Q2: latest matching file github/branch-protection.json is from 2026-07-14 (124 days ago), before this slot; collect a new one by 2026-12-31
- HR-02 period: collected 133 days before 2026-11-15; the freshness window is 120 days
- IAM-01 Q2: latest matching file aws/credential-report.csv is from 2026-07-20 (118 days ago), before this slot; collect a new one by 2026-12-31
- IDP-01 Q2: latest matching file m365/conditional-access-policies.json is from 2026-09-12 (64 days ago), before this slot; collect a new one by 2026-12-31
- IDP-03 Q2: latest matching file m365/privileged-roles-2026-07.json is from 2026-07-08 (130 days ago), before this slot; collect a new one by 2026-12-31

### How to obtain each item

- ACC-01 (quarterly, fresh within 100 days, owner Identity administrator): Entra access review results or the access review pack output, with the reviewer's sign-off and date. Used by: access-review-pack, evidence-pack-builder.
- CHG-01 (quarterly, fresh within 100 days, owner Engineering lead): gh api repos/<owner>/<repo>/branches/<branch>/protection; gh api repos/<owner>/<repo>/rules/branches/<branch>. Used by: github-change-control-evidence, control-map-from-exports.
- IAM-01 (quarterly, fresh within 100 days, owner Cloud platform lead): aws iam generate-credential-report, then aws iam get-credential-report --query Content --output text, decoded from base64 and saved as CSV. Used by: aws-identity-and-logging-evidence, control-map-from-exports, evidence-pack-builder.
- IDP-01 (quarterly, fresh within 100 days, owner Identity administrator): Microsoft Graph GET /identity/conditionalAccess/policies (Policy.Read.All), saved unchanged as JSON. Used by: control-map-from-exports, evidence-pack-builder.
- IDP-03 (quarterly, fresh within 100 days, owner Identity administrator): Microsoft Graph GET /roleManagement/directory/roleAssignments with $expand=principal (RoleManagement.Read.Directory), saved as JSON. Used by: access-review-pack, evidence-pack-builder.
- ACC-02 (population-sample, fresh within 120 days, owner People operations lead): HR system report of leavers in the period, joined to the date each account was disabled, saved as CSV. Used by: evidence-pack-builder.
- BKP-01 (once-per-period, fresh within 180 days, owner Cloud platform lead): aws backup list-backup-plans --region <region> --output json. Used by: aws-identity-and-logging-evidence, control-map-from-exports.
- CHG-02 (population-sample, fresh within 120 days, owner Engineering lead): gh pr list --repo <owner>/<repo> --state merged --limit 1000 --json number,mergedAt,author,reviews. Used by: github-change-control-evidence, evidence-pack-builder.
- HR-02 (once-per-period, fresh within 120 days, owner People operations lead): Training platform or HR system completion report for all staff, with completion dates, saved as CSV. Used by: evidence-pack-builder.
- HR-03 (once-per-period, fresh within 180 days, owner People operations lead): HR system or policy tool report of staff acknowledgements of the current policies, with dates. Used by: evidence-pack-builder.
- IAM-02 (once-per-period, fresh within 180 days, owner Cloud platform lead): aws iam get-account-password-policy --output json; aws iam get-account-summary --output json. Used by: aws-identity-and-logging-evidence, control-map-from-exports.
- IDP-02 (once-per-period, fresh within 180 days, owner Identity administrator): Microsoft Graph GET /policies/identitySecurityDefaultsEnforcementPolicy and GET /policies/authenticationMethodsPolicy, saved as JSON. Used by: control-map-from-exports.
- LOG-01 (once-per-period, fresh within 180 days, owner Cloud platform lead): aws cloudtrail describe-trails --output json; aws cloudtrail get-trail-status --name <trail> --output json. Used by: aws-identity-and-logging-evidence, control-map-from-exports.
- POL-01 (once-per-period, fresh within 365 days, owner Security lead): The current policy documents with version, approver and approval date; export the version history from the document store. Used by: evidence-pack-builder.

### Not applicable unless the system is added

- CHG-03 Emergency and out-of-process change tickets (system ticketing, controls A.8.32): applies if ticketing is added to the inventory, otherwise evidence these controls another way.
- GWS-01 Google Workspace 2-step verification enforcement (system google-workspace, controls A.8.5): applies if google-workspace is added to the inventory, otherwise evidence these controls another way.
- GWS-02 Google Workspace admin roles and audit log settings (system google-workspace, controls A.8.15): applies if google-workspace is added to the inventory, otherwise evidence these controls another way.

### Gaps

- A.7.4: no request in the catalogue.

Manifest files matching no selected request (1): notes/readme.txt.

Preparation for a human assessor: this is a collection plan, not an audit opinion, an attestation or a statement that any control works. The catalogue is a starting set; the assessor decides what evidence is sufficient.
