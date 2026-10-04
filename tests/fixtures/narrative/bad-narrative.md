# Draft control narratives (hand-edited, with planted problems)

> Preparation for a human assessor: this is not an audit opinion, an attestation or a certification, and not legal advice.

## A.8.15

Topic (paraphrase): Systems keep a tamper-resistant record of who did what.

CloudTrail logging is enforced across the estate. The export aws/cloudtrail-status-org-trail.json records IsLogging as `true` [evidence: aws/cloudtrail-status-org-trail.json#IsLogging].

## A.8.12

Topic (paraphrase): Leaks of sensitive data, including credentials, are prevented or caught.

Secret scanning output supports this control [evidence: github/repo.json#security_and_analysis.secret_scanning.status].

## A.8.32

Topic (paraphrase): Changes go through a reviewed, recorded process.

The organisation is fully compliant with change management and reviews cover 100% of merges [evidence: github/branch-protection.json#url].
Branch rules are recorded in the export [evidence: github/rulesets.json#rules].

## A.9.9

Topic (paraphrase): A control identifier that is not in the map.

This heading names an identifier the control map does not hold.
