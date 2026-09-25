# Threat model

This document defines the security boundaries demonstrated by the blueprint. It
is not a substitute for a system-specific threat assessment.

## Assets

- knowledge records and their tenant or role restrictions;
- user identity, roles and approval authority;
- tool arguments and external systems reachable through tools;
- model prompts, responses, citations and audit events;
- approval records and idempotency keys.

## Trust boundaries

1. User input is untrusted.
2. Retrieved document content is untrusted and may contain prompt injection.
3. Model output is untrusted, including tool names, arguments and citations.
4. Policy and authorization code belongs to the host application, not the model.
5. Tool execution belongs to a separate least-privilege service.
6. Audit and approval storage may contain sensitive operational metadata.

## Threats and controls

| Threat | Example | Demonstrated control | Production follow-up |
| --- | --- | --- | --- |
| Cross-tenant retrieval | Tenant B receives Tenant A's runbook | `MetadataAuthorizer` filters before model context | Enforce authorization inside the retrieval service and database |
| Role bypass | An ordinary user retrieves a security procedure | Record-level `allowed_roles` check | Derive roles from verified identity claims, never request text |
| Fabricated citation | Model cites a record it never received | Reject citation IDs outside supplied context | Evaluate claim-level entailment and quote spans |
| Prompt injection | A record instructs the model to call a tool | Retrieval and tool policy are separate | Treat documents as data, constrain outputs, test adversarial corpora |
| Unknown tool | Model invents `export_database` | Unknown tools are denied by default | Version tool schemas and review every new capability |
| Side-effect escalation | Model sends email without review | Side-effecting tools require approval | Execute only after consuming a valid approval in a separate service |
| Duplicate execution | Retry creates the same ticket twice | Persistent idempotency key and consumed state | Propagate the key to the external tool and enforce it there too |
| Self-approval | Requester approves their own action | Requester and approver must differ | Apply separation-of-duty rules per risk class |
| Stale approval | Old approval is replayed | Expiration and one-way state transitions | Sign execution envelopes and bind approval to exact arguments |
| Audit leakage | Secrets are copied into logs | Agent audit omits prompts, arguments and free-form purpose | Redact at ingestion and apply retention/access policies |
| Database disclosure | Approval database exposes tool arguments | Local SQLite is an explicit sensitive boundary | Encrypt storage and minimize retained arguments |
| Denial of service | Huge prompts or repeated requests | Not implemented | Add size, rate, time and cost limits before deployment |

## Security invariants

- Unauthorized records never enter the language-model context.
- A citation must identify a record supplied to the model.
- Unknown and explicitly denied tools cannot proceed.
- Approval does not execute a tool; it only changes authorization state.
- A pending approval can become approved or expired; an unused approval can also expire.
- An approved request can be consumed once; consumption is idempotent.
- Audit events do not include prompts, record text or tool arguments.

## Known limitations

- Keyword retrieval is illustrative and not resistant to inference attacks.
- Metadata authorization is applied after retrieval in this local example.
- Citation provenance does not prove claim-level factual entailment.
- SQLite does not provide distributed coordination or encrypted storage here.
- No model, identity provider or external tool is connected by default.
- Prompt-injection detection is intentionally not claimed as solved.
