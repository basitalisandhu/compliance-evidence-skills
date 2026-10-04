# Evidence pack manifest

> Preparation for a human assessor: this is not an audit opinion, an attestation or a certification, and not legal advice. Every result comes from exported files and needs review by the assessor.

- Built: 2026-10-05T00:00:00Z by evidence_pack.py 0.1.0
- Mode: copy (files copied under evidence/)
- Scope: GitHub repository example-org/payments-api (branch main), AWS account 123456789012, Microsoft 365 tenant example.com
- Period: 2026-07-01 to 2026-09-30
- Collector: jane.doe@example.com
- Files: 17

## Files

| Path | Source system | Command | Collected (basis) | Collector | SHA-256 | Bytes |
|---|---|---|---|---|---|---|
| aws/account-summary.json | aws | aws iam get-account-summary --output json | 2026-10-01T09:30:00Z (sidecar) | jane.doe@example.com | `58495fedbb5143b8bb4ece8e03215e60807fe959dbd4cf02d40a64c4ac2ba4a7` | 125 |
| aws/cloudtrail-status-org-trail.json | aws | aws cloudtrail get-trail-status --name arn:aws:cloudtrail:us-east-1:123456789012:trail/org-trail --output json | 2026-10-01T09:30:00Z (sidecar) | jane.doe@example.com | `b6ee96e68c72ea6451c11b7370f1730dc8ad5533ef09e00ebafaedd3b8c9c400` | 135 |
| aws/cloudtrail-trails.json | aws | aws cloudtrail describe-trails --output json | 2026-10-01T09:30:00Z (sidecar) | jane.doe@example.com | `bf111d58e83a079092c3e63947270411adc8db31c6f5ca6b62a0fd9e3111392d` | 416 |
| aws/credential-report.csv | aws | aws iam get-credential-report --query Content --output text \| base64 --decode | 2026-10-01T09:30:00Z (sidecar) | jane.doe@example.com | `315e7d770a737dd105a2656ef5e066275a1ef3b23bba48874b924fe35e7c4729` | 1049 |
| aws/password-policy.json | aws | aws iam get-account-password-policy --output json | 2026-10-01T09:30:00Z (sidecar) | jane.doe@example.com | `116ee87e7052f714009cae8cc5615e19fe7285d1166a1f1fae259b7800e71f5f` | 90 |
| aws/regions/us-east-1/backup-plans.json | aws | aws backup list-backup-plans --region us-east-1 --output json | 2026-10-01T09:30:00Z (sidecar) | jane.doe@example.com | `4155a9b0d35d21a261ce2b44317b5bb727036e684657ad4f9a440d920944c16c` | 28 |
| aws/regions/us-east-1/config-recorder-status.json | aws | aws configservice describe-configuration-recorder-status --region us-east-1 --output json | 2026-10-01T09:30:00Z (sidecar) | jane.doe@example.com | `1da19d6b50486d2bf0add71155e7d8c42d33f0cf0ebd3420689a8d30989451f9` | 136 |
| aws/s3control-public-access-block.json | aws | aws s3control get-public-access-block --account-id 123456789012 --output json | 2026-10-01T09:30:00Z (sidecar) | jane.doe@example.com | `a01009f8abee2f4e461987b8451484525ebd391f45cfa0ff344950a32a15c764` | 170 |
| github/branch-protection.json | github | gh api repos/example-org/payments-api/branches/main/protection | 2026-10-01T09:30:00Z (sidecar) | jane.doe@example.com | `5cbae6b1369452e404e715ef61b189ceace1f31306e7f2a316a23a05399aa5a9` | 834 |
| github/codeowners.json | github | gh api repos/example-org/payments-api/contents/.github/CODEOWNERS | 2026-10-01T09:30:00Z (sidecar) | jane.doe@example.com | `0246287857e674884da408d22663050f0d4ccee18ddd0f2a81f9d0bc48b37c2e` | 269 |
| github/dependabot-alerts.json | github | gh api --paginate "repos/example-org/payments-api/dependabot/alerts?state=open&per_page=100" | 2026-10-01T09:30:00Z (sidecar) | jane.doe@example.com | `d6a243bea9c2e0f036bb5f30a7abf44424cc2e85b6a1305331ac00a4e2033075` | 754 |
| github/pulls-merged.json | github | gh pr list --repo example-org/payments-api --state merged --base main --limit 1000 --json number,author,mergedAt,mergedBy,reviewDecision,reviews | 2026-10-01T09:35:00Z (sidecar) | jane.doe@example.com | `99a1fdcd43f527006f0c38520e3eb132180b4540791240436bd291787f3e5bf3` | 1508 |
| github/repo.json | github | gh api repos/example-org/payments-api | 2026-10-01T09:30:00Z (sidecar) | jane.doe@example.com | `64bb76d1773b8acb5d71d05b3f309aca8eb15e65479d28f61ac665ee5c270be7` | 462 |
| github/vulnerability-alerts.http | github | gh api -i repos/example-org/payments-api/vulnerability-alerts | 2026-10-01T09:30:00Z (sidecar) | jane.doe@example.com | `2e7ea52d98a61748079ef883f605452b12b6991e1d2e3c637df6839dc7a78146` | 98 |
| m365/conditional-access-policies.json | m365 | mgc identity conditional-access policies list --output json | 2026-10-01T09:30:00Z (sidecar) | jane.doe@example.com | `a3cc5d9fd24d6220eaa20012b242594e9a9c83933c7e2c10448073f9d9ddea5e` | 1267 |
| m365/intune-compliance-policies.json | m365 | not recorded | 2026-10-01T09:30:00Z (sidecar) | jane.doe@example.com | `34c5e11f37534eee64bdf75f2e58c2fd498d04e4d04f2999cf37bb78bee8cf3e` | 358 |
| m365/security-defaults.json | m365 | mgc policies identity-security-defaults-enforcement-policy get --output json | 2026-10-01T09:30:00Z (sidecar) | jane.doe@example.com | `84d7d0a191faeca078ab3441677344191a18970557e3b8d9ca9c1d1a4faa9615` | 236 |

## Gaps

- m365/intune-compliance-policies.json: no export command recorded; the assessor cannot repeat this export

## How to verify

Recompute every hash and compare it with this manifest:

```bash
python3 evidence_pack.py verify <pack> --manifest-sha256 <value given to you separately>
```
