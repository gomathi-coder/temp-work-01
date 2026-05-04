# Architecture Requirements
## Captured from Brainstorming Session

> **Purpose:** This document captures all architectural requirements, principles, constraints,
> and governance rules as stated by the product/tech owner during the brainstorming session.
> It serves as the source of truth for what needs to be documented, decided, and enforced.
>
> **Status:** Complete capture — all items from session included.
> **Next Step:** Use this to validate the Architecture Document and Referenced Guides are complete.

---

## Table of Contents

1. [System Overview](#1-system-overview)
2. [API Design Requirements](#2-api-design-requirements)
3. [Technology Stack Requirements](#3-technology-stack-requirements)
4. [Application Architecture Requirements](#4-application-architecture-requirements)
5. [Data & Database Requirements](#5-data--database-requirements)
6. [Security Requirements](#6-security-requirements)
7. [Observability Requirements](#7-observability-requirements)
8. [Performance Requirements](#8-performance-requirements)
9. [Availability & Zero Downtime Requirements](#9-availability--zero-downtime-requirements)
10. [Exception Handling Requirements](#10-exception-handling-requirements)
11. [Coding Governance Requirements](#11-coding-governance-requirements)
12. [Dependency & Library Governance Requirements](#12-dependency--library-governance-requirements)
13. [Platform Boundary Requirements](#13-platform-boundary-requirements)
14. [Frontend Requirements](#14-frontend-requirements)
15. [Document & Traceability Requirements](#15-document--traceability-requirements)

---

## 1. System Overview

### What We Are Building
- A new **component** that is part of a **larger existing system ecosystem**
- Technology stack: **Angular UI + Spring Boot backend**
- The system will also **expose REST APIs for third-party clients**
- The component sits alongside other components — integration and handshake between them must be explicitly defined

### Architecture Documentation Requirements
- Follow the **arc42 framework** (12 sections)
- Include **C4 Model diagrams** wherever applicable (Context, Container, Component levels)
- Use **Architecture Decision Records (ADRs)** for every significant decision
- This document will serve as the **reference for both HLD and LLD**
- The session approach: **brainstorming first, document outline to fill in later**

---

## 2. API Design Requirements

### Core Problem to Solve
> *"Usually our team mess up with API design as not following the standards"*

### Requirements
- API design standards must be **specific and detailed** — not generic statements like "follow industry practice"
- Create a **separate API Design Guide document** linked from the architecture document
- Standards must cover specific rules that can be enforced in code review

### Specific API Design Rules Required
- URL naming conventions — resource-based, specific format
- HTTP verb semantics — exactly when to use each verb
- HTTP status code rules — explicit mapping (e.g. 400 vs 422, 404 vs 403)
- API versioning strategy
- Pagination standards — format, defaults, enforcement
- Error response envelope — standard structure for all errors
- Request and response naming conventions

### Dual API Strategy
- The system has **two sets of APIs**:
  - One set used by the **Angular web application** (internal)
  - One set as **standard REST API exposed to third parties** (public)
- Decision needed: Is this the right practice? If yes, document it formally
- Both sets must be clearly separated in package structure, documentation, and versioning

### Response Object (VO) Design Policy
> *"We usually create one value object and use that for many APIs — we end up having so many keys and that ends up bloating the response JSON with lots of empty JSON keys"*

- **Core rule: One API = One Request VO + One Response VO** — no shared VOs across multiple APIs
- No null or empty fields in responses
- VO naming convention must be defined
- Mapping strategy must be specified (MapStruct)
- No entity objects exposed directly as API response
- No `BeanUtils.copyProperties` — banned

---

## 3. Technology Stack Requirements

### Version Selection
- **Spring Boot version** — must be explicitly selected and documented with justification
- **Angular version** — must be explicitly selected and documented with justification
- Both decisions must be captured as ADRs

### Package Structure
- **Root package structure** must be decided and documented
- **Individual module package definition** must be defined
- Decision required on approach:
  - Option A (module-first): `<module>/controller`, `<module>/service`
  - Option B (layer-first): `controller/<module>`, `service/<module>`
- This decision must be captured as an ADR

---

## 4. Application Architecture Requirements

### Statelessness
> *"Usually we use HTTP web session to hold data for the user — this time I want the entire system to be completely stateless"*

- **Zero HTTP session usage** — no `HttpSession`, no `@SessionScope`, no Spring Session
- All user context must be carried in JWT token claims
- Token validated on every request
- Decision captured as ADR

### Spring Boot Filters
> *"We write various filters in Spring Boot — we need to clearly articulate the purpose of each"*

- Every filter must have a **single, documented purpose** — no filter with multiple responsibilities
- Filter chain order must be explicitly defined
- No business logic in filters
- Each filter documented: name, order, purpose, what it rejects/accepts

### Inter-Component Handshake
> *"This component lies along with other components — how the handshake between components should be done"*

- Integration contracts between components must be explicitly documented
- For each outbound integration: protocol, contract owner, versioning, timeout, fallback
- Circuit breaker behaviour to be defined
- Cannot call another module's database directly — only via its published API

### Async Usage
> *"@Async — should it be used or only with certain approved cases?"*

- `@Async` must **not be freely used** — only in approved, designated cases
- Each approved async use case must be documented
- Named, configured `ThreadPoolExecutor` mandatory
- Cannot be combined with `@Transactional`
- All exceptions must be handled — not swallowed

---

## 5. Data & Database Requirements

### No Stored Procedures
> *"You cannot use any stored procedure or functions"*

- **Absolute prohibition** on stored procedures, DB functions, triggers, business logic in views
- Database is a **dumb persistence store only**
- All business logic must reside in the Spring Boot service layer
- Captured as ADR

### Table Naming Convention
- Standard naming format must be defined
- Domain prefix mandatory on all tables
- Case convention: lowercase, underscore-separated
- Junction tables, views, audit tables — separate naming rules
- Index naming convention
- Constraint naming convention (PK, FK, UQ, CK)

### Standard Audit Fields
> *"All tables should have standard audit fields and unique key fields"*

- Every table must have mandatory audit columns:
  - `created_by`, `created_at`, `updated_by`, `updated_at`
  - `is_deleted`, `deleted_by`, `deleted_at` (soft delete — no hard deletes)
  - `version` (optimistic locking)
- All timestamps in UTC
- Application must never manually set `created_at` / `updated_at` — handled by Spring Data Auditing

### Primary Key & Unique Key Policy
- Surrogate PK on every table — no business keys as PK
- BIGINT for internal tables, UUID for tables exposed via public API
- No composite PKs
- Business uniqueness via named unique constraints — not via PK
- Validate uniqueness at service layer before insert — do not rely on catching `DataIntegrityViolationException`

### Audit Table & Audit Policy
- Separate audit tables for all state-changing operations on business entities
- Audit tables are **append-only** — no UPDATE or DELETE
- Use Hibernate Envers — no manual audit code
- Table naming: `aud_<source_table>`
- Audit record written in same transaction as the change
- No FK constraints from audit tables to source tables
- Security events must also be audited (login, logout, failed auth, permission change)

### Repository Query Rules
> *"We need to put the rules of repository queries as do's and don'ts"*

- Explicit do's and don'ts for repository queries documented
- No `SELECT *`
- No unbounded queries — always paginate
- No N+1 patterns
- No string-concatenated queries
- `findAll()` without `Pageable` is banned
- `IN` clause with unbounded list is prohibited

### DB Query Return Size Limits
> *"DB query data return size should be within certain limits"*

- Max rows per non-paginated query: 500 (internal jobs only)
- API responses: max 100 rows per page
- Batch jobs: cursor/chunk-based processing — never full dataset in memory
- Enforced via custom Repository base class and code review checklist

---

## 6. Security Requirements

### Layered Security Principle
> *"I just don't want to mention 'all inputs should be validated' — I want to extend it to say the principle is all inputs should be validated, the kind of inputs is form inputs and file uploads, for form inputs what kind of validation, for file uploads what kind of validation — this level of detailing I want to do"*

- Security rules must be defined **layer by layer** — not as a generic statement
- Every layer has its own specific security responsibilities
- Security Runbook to be created as a separate referenced document

### Form Input Validation (Controller Layer)
- Type validation
- Not-null / not-blank where required
- Length constraints (min and max)
- Format validation (regex for emails, phone numbers, codes)
- Range validation (numeric min/max)
- Allowed values validation
- HTML/script injection prevention
- Server-side validation mandatory — client-side alone is not sufficient

### File Upload Validation (Controller Layer)
Five mandatory checks, in order:
1. **MIME type** — validate Content-Type header AND actual file magic bytes
2. **File size** — enforce at multipart config level, reject before reading full stream
3. **Filename sanitisation** — strip path separators, special characters; use server-generated UUID filename
4. **Antivirus / malware scan** — all uploads scanned before storage; quarantine on detection
5. **Content validation** — validate content matches declared type

### Cookie Policy
- All cookies: `HttpOnly=true`, `Secure=true`, `SameSite=Strict`, explicit `Max-Age`, scoped `Domain` and `Path`
- No auth tokens in non-HttpOnly cookies
- No PII in cookies
- No sensitive business data in cookies

### Request Header Policy
- Mandatory headers on all inbound requests defined
- `X-Correlation-ID` — validate format, generate if absent
- `Authorization` header must never be logged
- No business data in custom headers

### Response Header Policy
- Mandatory security headers on all responses:
  - `X-Content-Type-Options: nosniff`
  - `X-Frame-Options: DENY`
  - `Strict-Transport-Security`
  - `Content-Security-Policy`
- `X-Correlation-ID` echoed back in every response
- Server identification headers (`Server`, `X-Powered-By`) stripped

---

## 7. Observability Requirements

> *"Logging, instrumentation, traceability and observability should be implemented"*

### Logging
- Structured JSON logging
- Mandatory fields on every log line: `correlationId`, `requestId`, `userId`, `timestamp`, `level`, `service`
- Log level rules per environment
- Explicit rules on what to log and what NOT to log (no PII, no tokens, no request body in production)

### Tracing
- `X-Correlation-ID` generated at system entry and propagated through all layers
- Added to MDC — appears automatically in all log lines
- Propagated in all outbound calls to platform modules
- Echoed in all responses

### Metrics / Instrumentation
- Spring Boot Actuator + Micrometer mandatory
- Standard metrics defined: API latency, error rates, DB call times, thread pool, cache hit/miss
- Custom business metrics to be identified

### Observability
- Health check endpoints: `/actuator/health` (liveness) and `/actuator/health/readiness`
- Readiness probe checks DB and downstream service connectivity
- Actuator endpoints must not be publicly exposed

---

## 8. Performance Requirements

### Performance Concern Placement
- Performance targets documented in **arc42 §10 Quality Requirements**
- Hard constraints documented in **arc42 §2 Constraints**
- Developer rules documented in **arc42 §8.9 Performance Engineering Principles**
- Critical flow latency annotated in **arc42 §6 Runtime View**

### Performance Targets (Defined)
| Metric | Target |
|---|---|
| API response time p95 | ≤ 300ms (normal load) |
| API response time p99 | ≤ 1000ms (degraded) |
| Angular initial page load | ≤ 2s on 4G |
| DB query time | ≤ 100ms per single query |
| File upload (10MB) | ≤ 5s |

### Response Size Limits
> *"Response size should always be within certain limits"*

- Single resource response: max 50KB
- Collection response: max 100KB
- No response above 1MB — must be redesigned or streamed
- Enforced via `ContentSizeLimitFilter` in Spring Boot
- Monitored — alert at 80% of limit

### Performance Coding Rules
- No `SELECT *`
- No N+1 patterns
- Pagination mandatory — max page size 100
- Gzip compression on all REST responses above 1KB
- Explicit timeouts on all outbound HTTP calls
- No synchronous calls to external systems in user-facing request path

---

## 9. Availability & Zero Downtime Requirements

> *"Major problem: every patch change results in application downtime — what principles to follow in application architecture for no downtime, how each layer should be built for it"*

### Core Requirement
- **Zero application downtime** on any patch, release, or deployment
- This is a cross-layer architectural principle — not just a deployment concern

### Per-Layer Rules Required

| Layer | Principle |
|---|---|
| Database | Backward-compatible migrations — expand-contract pattern |
| API | Non-breaking changes only within a version — additive only |
| Backend | Graceful shutdown — drain in-flight requests |
| Frontend | Must tolerate old and new API responses simultaneously |
| Deployment | Rolling or Blue-Green — no big-bang deploys |
| State | Stateless architecture enables this (ADR-003) |

### Decision Required
- Rolling deployment vs Blue-Green vs Canary — must be chosen and documented as ADR

---

## 10. Exception Handling Requirements

### Classification
- **Exactly two classes of exceptions**: Business Exception and System Exception
- Clear definition, examples, HTTP status mapping, logging level, and handling behaviour for each

### Business Exception
- Represents business rule violations the caller can act upon
- HTTP 4xx responses
- Logged at WARN level
- User-friendly, actionable message in response

### System Exception
- Infrastructure or unexpected failures the caller cannot act upon
- HTTP 5xx responses
- Logged at ERROR level with full stack trace internally
- Generic, sanitised message returned to caller — no internals ever exposed

### Exception Hierarchy
- Custom base classes: `BusinessException` and `SystemException`
- Sub-types mapped to specific HTTP status codes

### Error Code Design
> *"Error codes in exception handling"*

- Standard error code format: `<DOMAIN>-<TYPE>-<NUMBER>`
- Error codes defined in central enum per domain
- Error codes are a **published contract** — never changed, never repurposed
- New scenarios always get new codes

### Error Response Envelope
> *"What messages we need to send for exceptions, how to return the business exception error and system exception error"*

Standard JSON structure with: `status`, `errorCode`, `message`, `timestamp`, `correlationId`, `path`, `details` (validation only)

Rules:
- `message` for 4xx: human-readable, actionable
- `message` for 5xx: always generic — "An unexpected error occurred"
- Stack traces must never appear in response
- Internal class names, DB errors, query text must never appear in response
- `correlationId` always echoed

### HTTP Status Code Rules
- Explicit mapping required for: 400, 401, 403, 404, 409, 422, 429, 500, 502, 503, 504
- 200 with error in body is **banned**
- 400 for business rule violations is **banned** — use 422

### Global Exception Handler
- One `@RestControllerAdvice` class only
- No try-catch in Controller layer — ever
- No try-catch in Service layer for SystemExceptions
- try-catch in Service layer only when explicitly converting a SystemException to BusinessException

---

## 11. Coding Governance Requirements

### Annotation Governance
> *"Should I mention what Spring annotations to use and what Java package to use? Will there be situations where new annotations that the team uses will have an impact — e.g. can we use @Async or should it be used only with certain approved cases?"*

- **Yes** — annotation governance policy is required
- Three categories: Freely Usable / Conditionally Usable (approval required) / Banned
- Specific rules for conditionally approved annotations: `@Async`, `@Scheduled`, `@Cacheable`, `@EventListener`
- Banned annotations explicitly listed with reasons

### Key Annotation Rules
- `@Autowired` — constructor injection only; field injection is banned
- `@Transactional` — Service layer only; banned on Controllers; banned on Repositories
- `@Data` (Lombok) — banned on JPA entities; use `@Getter @Setter` only
- `@SuppressWarnings` — banned
- `@SpringBootTest` — not on every test; use slice tests

### Code Review Checklist
- Formal checklist organised by category: API, Data Access, Exception Handling, Security, Performance, Dependencies
- Must be enforced in every PR review

### Testing Standards
- Test pyramid approach defined
- Testcontainers for DB integration tests — no H2 in-memory
- Every public service method has a unit test
- Every API endpoint has an integration test
- Every repository query has a `@DataJpaTest` test

---

## 12. Dependency & Library Governance Requirements

> *"Which third-party jar to use — because that will have security vulnerabilities — the process for that, where will we define it?"*

### Core Requirement
- No third-party library added without a formal approval process
- Security vulnerabilities in dependencies are a primary attack vector

### Dependency Governance Process
1. Need identification with justification
2. Security scan using OWASP Dependency Check
3. Tech Lead approval — documented as ADR
4. Exact version pinning (no version ranges)
5. Ongoing monitoring — OWASP scan on every CI build

### Rules
- GPL licensed libraries are banned — Apache/MIT/BSD only
- CRITICAL or HIGH CVE → automatic rejection
- No SNAPSHOT versions in production
- No version ranges in `pom.xml` — always pin exact version
- Approved library register maintained

---

## 13. Platform Boundary Requirements

> *"This component lies in the larger system ecosystem — there are certain functionalities that should be used from other platform modules and certain functionality we should not build here"*

### Core Requirement
- Explicit definition of what this component **owns** vs what it **consumes** from the platform
- Must be documented in Context diagram (C4 Level 1) and Component Integration Contracts section

### What Must Be Consumed From Platform (Not Rebuilt)
- Authentication — from Auth Module
- User profile management — from User Module
- Notification sending — from Notification Service
- Audit logging infrastructure — from Audit Module
- File storage — from Document Management Service

### What Must Not Be Built Here
- Any of the above capabilities must not be re-implemented
- If a gap is found in a platform module, escalate to owning team — do not work around locally

### Integration Rules
- Only consume via published API contract of owning module
- Never call another module's database directly
- Version-pin all integration contracts
- Define timeout and fallback for every outbound integration

---

## 14. Frontend Requirements

> *"I am intentionally leaving out frontend design — I am not an expert there"*

### Requirement
- Frontend / Angular topics must be **identified and tagged** as `[UI-LAYER]`
- These sections are **placeholders** to be filled in by a UI architecture specialist
- The architecture document must not leave these as blank gaps — it must list the specific topics that need to be addressed

### UI-Layer Topics Identified (to be defined by specialist)
- Angular project structure and module strategy
- Lazy loading — mandatory for feature modules
- State management approach
- HTTP interceptor chain (auth token, correlation ID, error handling)
- Routing strategy and guards
- Bundle size budget enforcement
- Environment configuration strategy
- Angular coding standards (naming, OnPush, unsubscribe strategy)
- ESLint ruleset
- Angular deployment pipeline (build flags, CDN, cache-busting)
- Error handling at UI layer
- i18n strategy
- CSRF token handling
- XSS prevention rules
- Core Web Vitals targets
- API client layer design

---

## 15. Document & Traceability Requirements

### Architecture Document Structure
- **One master Architecture Document** following arc42 (12 sections)
- **Six referenced separate documents** linked from the master:
  1. API Design Guide
  2. Security Runbook
  3. Observability Guide
  4. Database Design Standards
  5. Coding Standards & Governance Guide
  6. Dependency Governance Process

### ADR Requirements
- Every significant decision must have an ADR
- Standard format: Title, Status, Context, Decision, Consequences, Alternatives Considered
- ADRs are a **published contract** — once accepted, the decision text does not change
- New decisions get new ADRs — existing ones are not overwritten

### ADRs Identified in Session

| ADR | Title |
|---|---|
| ADR-001 | Spring Boot Version Selection |
| ADR-002 | Angular Version Selection |
| ADR-003 | Stateless Architecture (No HTTP Session) |
| ADR-004 | Dual API Strategy — Internal vs Public REST |
| ADR-005 | Package Structure Convention |
| ADR-006 | Intra-Module Package Layout |
| ADR-007 | Zero Downtime Deployment Strategy |
| ADR-008 | In-Memory Caching Strategy |
| ADR-009 | Async Processing for Non-Blocking Flows |
| ADR-010 | DB Connection Pool Configuration |
| ADR-011 | Prohibition of Stored Procedures and DB Functions |
| ADR-012 | One VO Per API — No Shared Value Objects |
| ADR-013 | Cookie and Header Standards |
| ADR-014 | Platform Boundary — Owned vs Consumed Capabilities |
| ADR-015 | Audit Strategy — Hibernate Envers + Append-Only Tables |
| ADR-016 | Dependency Governance — OWASP Scan + Approval Process |

### Where Each Requirement Type Lives

| Requirement Type | Document / Section |
|---|---|
| API standards (specific rules) | API Design Guide → linked from arc42 §8.1 |
| Technology version decisions | ADR-001, ADR-002 |
| Spring filters and their purpose | arc42 §8.2 |
| Statelessness decision | ADR-003 |
| Inter-component handshake | arc42 §5.3 + §3 C4 Level 1 |
| Package structure decision | ADR-005, ADR-006 → rules in arc42 §5.3 |
| Repository query do's and don'ts | arc42 §8.4 + Database Design Standards |
| VO design policy | arc42 §8.5 + API Design Guide + ADR-012 |
| Dual API strategy | ADR-004 + API Design Guide |
| Security principles (layered, specific) | Security Runbook → linked from arc42 §8.6 |
| Logging, tracing, observability | Observability Guide → linked from arc42 §8.7 |
| Zero downtime principles (per layer) | arc42 §8.8, §7.3 + ADR-007 |
| Performance targets | arc42 §10 Quality Requirements |
| Performance coding rules | arc42 §8.9 |
| No stored procedures (decision) | ADR-011 |
| No stored procedures (rules) | arc42 §8.4 + Database Design Standards |
| Table naming convention | Database Design Standards |
| Audit fields | Database Design Standards |
| Audit policy | arc42 §8.12 + ADR-015 |
| Coding guidelines | Coding Standards & Governance Guide → arc42 §8.13 |
| Annotation governance | Coding Standards & Governance Guide |
| Third-party library governance | Dependency Governance Process + ADR-016 |
| Response size limits | arc42 §8.9 + arc42 §10 |
| DB query size limits | arc42 §8.4 |
| Cookie policy | arc42 §8.10 + ADR-013 |
| Request/response header policy | arc42 §8.10 |
| Platform boundary | arc42 §3.3 + arc42 §5.4 + ADR-014 |
| Exception handling policy | arc42 §8.11 |
| Error codes | arc42 §8.11 |
| Error response structure | arc42 §8.11 + API Design Guide |
| Frontend topics | arc42 §5.5, §7.4, §8.6, §8.9, §8.13 [UI-LAYER] |

---

*This document is a complete capture of all requirements stated during the brainstorming session.*
*It does not contain any invented requirements — only what was explicitly discussed.*
