# Chat Service

Authoritative store for user-scoped chat. Channel adapters for app, web, and SMS share one place to record and read conversation history while it still contains identifiable content, before deidentification, analysis, or downstream review happen elsewhere.

Clients call this service when someone sends a message, opens a thread, or needs the AI assistant to draft a reply. SMS and other channel adapters use the same API so every channel sees one timeline. Authorized callers read stored transcripts during escalation and human takeover. Upstream services own episode or domain context; this service only holds the conversations linked to that context. When a conversation ends, the deidentification pipeline is told to fetch the full thread. Authentication establishes identity for callers; channel delivery, push, risk scoring beyond the inline assistant, and long-term clean analytics live in their own services.

## Resources

### Operations

For testers, developers, and system administrators, [OPERATIONS.md](OPERATIONS.md) covers local setup, migrations, ports, and smoke checks. Per-release operator steps and verification are in [INSTALLATION_PLAN.md](INSTALLATION_PLAN.md).

### Changelog

For product owners and release readers, [CHANGELOG.md](CHANGELOG.md) records user-visible chat changes per release ([Keep a Changelog](https://keepachangelog.com/)).

### API Contract

For API consumers, integration testers, and frontend developers, [openapi.json](openapi.json) is the authoritative machine-readable contract for this service. It is maintained in-repo for CI and codegen; it is **not** served over HTTP in any environment.

### Security Policy

For security reviewers, on-call engineers, and contributors, [SECURITY.md](SECURITY.md) documents the threat model, authz boundaries, and logging rules for this service.

### License

AGPL-3.0 — see [LICENSE](LICENSE) and [NOTICE](NOTICE). Deploy-time AI assistant prompts are treated as operator configuration; see NOTICE.

### Feature Specification

For product owners, architects, and new contributors, the [feature spec](https://github.com/Neosofia/cdp/blob/main/specs/001-chat-service.md) describes goals, functional requirements, and acceptance criteria. It is the binding record of what the component must do.

### Governance and architecture

For architects and senior engineers, [ADR-0003](https://github.com/Neosofia/cdp/blob/main/architecture/adrs/0003-store-categorical-columns-as-integer-enums.md) records integer enum storage for categorical columns such as `channel`; [ADR-0008](https://github.com/Neosofia/cdp/blob/main/architecture/adrs/0008-published-json-schema-contracts-for-api-testing.md) establishes the published OpenAPI contract approach used here.
