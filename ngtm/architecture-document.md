# Architecture Document
## Component Architecture — arc42 Framework
### Angular + Spring Boot + REST API System

> **Document Status:** Draft — Brainstorming / Reference Skeleton  
> **Framework:** arc42 | **Diagrams:** C4 Model | **Decisions:** ADR  
> **Legend:**  
> `[UI-LAYER]` — Frontend architecture topics (to be detailed by UI specialist)  
> `[SUGGESTION]` — Recommended additions identified during architecture review  
> `[ADR-XXX]` — Cross-reference to Architecture Decision Record  
> `[TODO]` — Section requires input from the team

---

## Table of Contents

1. [Introduction & Goals](#1-introduction--goals)
2. [Constraints](#2-constraints)
3. [Context & Scope](#3-context--scope)
4. [Solution Strategy](#4-solution-strategy)
5. [Building Block View](#5-building-block-view)
6. [Runtime View](#6-runtime-view)
7. [Deployment View](#7-deployment-view)
8. [Cross-Cutting Concepts](#8-cross-cutting-concepts)
9. [Architecture Decision Records](#9-architecture-decision-records)
10. [Quality Requirements](#10-quality-requirements)
11. [Risks & Technical Debt](#11-risks--technical-debt)
12. [Glossary](#12-glossary)

**Referenced Separate Documents:**
- [API Design Guide](#api-design-guide)
- [Security Runbook](#security-runbook)
- [Observability Guide](#observability-guide)
- [Database Design Standards](#database-design-standards)
- [Coding Standards & Governance Guide](#coding-standards--governance-guide)
- [Dependency Governance Process](#dependency-governance-process)

---

---

# PART I — ARCHITECTURE DOCUMENT (arc42)

---

## 1. Introduction & Goals

### 1.1 Component Purpose

> **[TODO]** Describe in 2–3 paragraphs what this component does, the business problem it solves, and why it is being built now.

### 1.2 Top Quality Goals

| Priority | Quality Goal | Motivation |
|---|---|---|
| 1 | [TODO] | [TODO] |
| 2 | [TODO] | [TODO] |
| 3 | Statelessness | No server-side session — all state carried in tokens per [ADR-003] |
| 4 | Zero Downtime | Every deployment must be non-disruptive per [ADR-007] |
| 5 | Security | Layered defence-in-depth per Security Runbook |

### 1.3 Stakeholders

| Stakeholder | Role | Expectation |
|---|---|---|
| [TODO] | Product Owner | [TODO] |
| [TODO] | Tech Lead | [TODO] |
| [TODO] | Frontend Team | Angular UI integration |
| [TODO] | Backend Team | Spring Boot service development |
| [TODO] | Third-party Clients | Stable, versioned REST API |
| [TODO] | Platform / Infra Team | Deployability, observability |
| [TODO] | Security Team | Compliance with security policy |
| `[SUGGESTION]` | Operations / SRE | Runbook, alerting, on-call support |
| `[SUGGESTION]` | Compliance / Audit | Audit trail, data retention policy |

---

## 2. Constraints

### 2.1 Technical Constraints

| Constraint | Details |
|---|---|
| Backend Language | Java — Spring Boot [ADR-001] |
| Frontend Framework | Angular [ADR-002] |
| No Stored Procedures | All business logic in service layer [ADR-011] |
| No HTTP Session | Fully stateless [ADR-003] |
| No GPL Libraries | Only Apache / MIT / BSD licensed dependencies |
| DB Connection Pool | Max connections per [ADR-010] |
| `[SUGGESTION]` | JDK version — pin and document |
| `[SUGGESTION]` | Node.js / npm version for Angular build |
| `[SUGGESTION]` | Supported browser matrix [UI-LAYER] |

### 2.2 Organisational Constraints

| Constraint | Details |
|---|---|
| [TODO] | Team size and structure |
| [TODO] | Release cadence |
| [TODO] | External dependency SLA (other platform modules) |
| `[SUGGESTION]` | Compliance requirements (GDPR, PCI, SOC2, etc.) |
| `[SUGGESTION]` | Data residency / regional deployment restrictions |

### 2.3 Infrastructure Constraints

| Constraint | Details |
|---|---|
| [TODO] | Cloud provider / on-prem |
| [TODO] | Max memory per instance |
| [TODO] | Shared DB cluster — max connection pool size |
| [TODO] | Third-party API rate limits |
| `[SUGGESTION]` | CI/CD pipeline tooling |
| `[SUGGESTION]` | Container runtime (Docker, Kubernetes version) |

---

## 3. Context & Scope

### 3.1 Business Context

> **[TODO]** Describe the domain context — what business process does this component support?

### 3.2 C4 Level 1 — System Context Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        [TODO: Draw C4 Level 1]              │
│                                                             │
│  Actors:                                                    │
│  - End User (Browser / Angular SPA)                        │
│  - Third-party Client (REST API consumer)                  │
│  - Platform Modules (Auth, Notification, Audit, etc.)      │
│  - External Systems ([TODO])                               │
│                                                             │
│  This System:                                               │
│  - [Component Name] — black box boundary                   │
└─────────────────────────────────────────────────────────────┘
```

> **[TODO]** Replace with actual C4 Level 1 diagram (PlantUML / Mermaid / Structurizr).

### 3.3 Platform Boundary — What This Component Owns vs Consumes

#### Consume From Platform (Do NOT Rebuild Here)

| Platform Module | Capability | How to Consume |
|---|---|---|
| Auth Module | Authentication, JWT issuance | JWT validation filter — do not re-implement |
| Notification Service | Email / SMS alerts | Via internal REST API call |
| Audit Module | Audit trail infrastructure | Via async event / message queue |
| User Profile Service | User data lookup | Via internal REST API call |
| Document Management | File storage | Via internal REST API — no local file storage |
| `[SUGGESTION]` | Feature Flag Service | Toggle features without redeployment |
| `[SUGGESTION]` | Config Service | Externalised configuration |

#### Must NOT Build Here (Prohibited Capabilities)

| Prohibited | Reason |
|---|---|
| Authentication logic | Owned by Auth Module |
| User registration / profile management | Owned by User Module |
| Notification sending logic | Owned by Notification Service |
| Audit logging infrastructure | Owned by Audit Module |
| File storage | Owned by Document Management |
| `[SUGGESTION]` | Report generation — if needed, delegate to Reporting Service |

> **See [ADR-014] for the platform boundary decision.**

---

## 4. Solution Strategy

### 4.1 Key Strategic Decisions Summary

| Decision | Choice | ADR |
|---|---|---|
| Backend framework | Spring Boot | ADR-001 |
| Frontend framework | Angular | ADR-002 |
| Session strategy | Fully stateless (JWT) | ADR-003 |
| API exposure strategy | Dual API — internal + public REST | ADR-004 |
| Package structure | [TODO — module-first or layer-first] | ADR-005, ADR-006 |
| Deployment strategy | Zero downtime (rolling / blue-green) | ADR-007 |
| Caching | In-memory with defined TTL | ADR-008 |
| Async processing | Only for approved non-critical flows | ADR-009 |
| DB connection pool | [TODO — library and sizing] | ADR-010 |
| No stored procedures | Service layer owns all logic | ADR-011 |
| VO design | One VO per API — no shared objects | ADR-012 |
| Audit strategy | Hibernate Envers + append-only tables | ADR-015 |
| Dependency governance | OWASP scan + approval process | ADR-016 |
| `[SUGGESTION]` | API Gateway strategy | ADR-TBD |
| `[SUGGESTION]` | Service discovery strategy | ADR-TBD |

### 4.2 Architecture Style

> **[TODO]** State the overall architecture style — modular monolith, microservice, layered monolith — and justify it briefly here. Point to the relevant ADR.

---

## 5. Building Block View

### 5.1 C4 Level 2 — Container Diagram

```
┌─────────────────────────────────────────────────────────────┐
│                        [TODO: Draw C4 Level 2]              │
│                                                             │
│  Containers:                                                │
│  - Angular SPA (Browser)                                   │
│  - Spring Boot Application (Backend)                       │
│  - Relational Database                                      │
│  - [TODO: API Gateway?]                                    │
│  - [TODO: Cache layer?]                                    │
│  - [TODO: Message queue for async?]                        │
└─────────────────────────────────────────────────────────────┘
```

### 5.2 C4 Level 3 — Component Diagram (Spring Boot)

```
┌─────────────────────────────────────────────────────────────┐
│                        [TODO: Draw C4 Level 3]              │
│                                                             │
│  Inside Spring Boot:                                        │
│  - Filter Chain (Auth, Correlation, Security headers)      │
│  - Internal API Controllers (web app facing)               │
│  - Public REST API Controllers (third-party facing)        │
│  - Service Layer                                           │
│  - Repository Layer (Spring Data JPA)                      │
│  - Domain Model                                            │
│  - Integration Clients (outbound to platform modules)      │
│  - Global Exception Handler                                │
│  - Async Service (approved cases only)                     │
└─────────────────────────────────────────────────────────────┘
```

### 5.3 Package Structure

> **See [ADR-005] and [ADR-006] for the package structure decision.**

#### Root Package

```
com.<organisation>.<product>.<component>
```

#### Module Structure (Decision Pending — see ADR-006)

**Option A — Module-first (Recommended)**
```
com.org.product.component
├── order/
│   ├── controller/
│   ├── service/
│   ├── repository/
│   ├── domain/
│   └── dto/
├── payment/
│   ├── controller/
│   └── ...
└── shared/
    ├── exception/
    ├── filter/
    ├── audit/
    └── config/
```

**Option B — Layer-first**
```
com.org.product.component
├── controller/
│   ├── order/
│   └── payment/
├── service/
│   ├── order/
│   └── payment/
└── ...
```

> **[TODO]** Finalise decision in ADR-006 and remove the unchosen option from this section.

### 5.4 Component Integration Contracts

> How this component handshakes with other platform components.

| Target Component | Direction | Protocol | Contract Owner | Versioning |
|---|---|---|---|---|
| Auth Module | Inbound JWT | HTTP Header | Auth Team | [TODO] |
| Notification Service | Outbound | REST | Notification Team | [TODO] |
| Audit Module | Outbound | Async Event | Audit Team | [TODO] |
| User Profile Service | Outbound | REST | User Team | [TODO] |
| `[SUGGESTION]` | Define circuit breaker behaviour for each outbound call | | | |

#### Integration Rules

```
✓ All outbound HTTP calls must have explicit timeout configured
✓ All outbound calls must use Resilience4j circuit breaker [ADR-conditional]
✓ Version-pin all integration contracts — no floating versions
✓ If downstream is unavailable — define fallback behaviour per integration
✗ Never call another module's database directly — only via its API
✗ Never share domain model classes across module boundaries
```

### 5.5 `[UI-LAYER]` Angular Application Structure

```
[UI-LAYER] Topics to define:
  - Angular project structure (feature modules vs standalone components)
  - Lazy loading strategy — mandatory for all feature modules
  - State management approach (NgRx / Services / Signals)
  - HTTP interceptor chain (auth token, correlation ID, error handling)
  - Routing strategy and guards
  - Shared module / design system approach
  - Environment configuration strategy (environment.ts)
  - Angular module boundary rules — what can import what
  - API client layer — how services call backend (abstraction layer)
  - [SUGGESTION] Micro-frontend strategy if applicable
```

---

## 6. Runtime View

### 6.1 Key Flows

> For each critical user journey, draw a sequence diagram annotated with expected latency at each hop.

#### 6.1.1 Authentication Flow
```
[TODO: Sequence diagram]
Annotate with latency budget per hop.
Total budget: [TODO]ms
```

#### 6.1.2 Core Business Flow — [TODO: Name]
```
[TODO: Sequence diagram]
```

#### 6.1.3 File Upload Flow
```
[TODO: Sequence diagram]
Total budget: [TODO]s for up to [TODO]MB
```

#### 6.1.4 Public REST API Flow (Third-party client)
```
[TODO: Sequence diagram]
Show: rate limiting, auth validation, response envelope
```

#### 6.1.5 `[SUGGESTION]` Async / Background Job Flow
```
[SUGGESTION] [TODO: Sequence diagram if async jobs exist]
```

### 6.2 `[SUGGESTION]` Error Flow Runtime View
```
[SUGGESTION] Show what happens end-to-end when:
  - BusinessException is thrown
  - SystemException is thrown
  - Downstream service is unavailable
```

---

## 7. Deployment View

### 7.1 Deployment Architecture

```
[TODO: Deployment diagram]
Show:
  - Where Angular SPA is served (CDN / static hosting / backend-served)
  - Where Spring Boot runs (container, VM, K8s pod)
  - Database placement
  - Load balancer / API gateway
  - Any cache tier
```

### 7.2 Environment Strategy

| Environment | Purpose | Notes |
|---|---|---|
| Development | Local dev | [TODO] |
| Integration | Integration testing | [TODO] |
| Staging | Pre-prod validation | [TODO] |
| Production | Live | Zero downtime deployment only |

### 7.3 Zero Downtime Deployment — Per Layer Rules

> **See [ADR-007] for the deployment strategy decision.**

| Layer | Principle | Rule |
|---|---|---|
| **Database** | Backward-compatible migrations | Never drop or rename columns in same release as code. Use expand-contract pattern. |
| **API** | Non-breaking changes only | Additive changes only within same version. New fields optional. Deprecate, do not delete. |
| **Backend** | Graceful shutdown | `server.shutdown=graceful` in Spring Boot. Drain in-flight requests before stopping. |
| **Frontend** | Independent deployability | Angular app must tolerate old and new API responses simultaneously. [UI-LAYER] |
| **Deployment** | Rolling or Blue-Green | No big-bang deploys. Feature flags for risky changes. |
| **State** | Stateless [ADR-003] | No session affinity required — instances are interchangeable. |

### 7.4 `[UI-LAYER]` Frontend Deployment

```
[UI-LAYER] Topics to define:
  - Build pipeline — Angular CLI build flags for production
  - Bundle size budget enforcement (angular.json budgets)
  - CDN strategy and cache-busting (content hash filenames)
  - Environment variable injection strategy
  - Source map handling in production
  - [SUGGESTION] Feature flag integration at UI layer
```

### 7.5 `[SUGGESTION]` Infrastructure as Code
```
[SUGGESTION] Define:
  - IaC tooling (Terraform / Helm / CloudFormation)
  - Who owns infrastructure definitions
  - DR / failover strategy
  - Backup and restore policy
```

---

## 8. Cross-Cutting Concepts

> This is the **engineering rulebook** for the system. Every rule here is mandatory unless explicitly stated as conditional.

---

### 8.1 API Design Standards

> **Full detail in [API Design Guide](#api-design-guide).** Summary principles below.

```
Principles:
  ✓ Resource-based URLs — nouns, plural, lowercase, hyphen-separated
  ✓ HTTP verbs used semantically (GET / POST / PUT / PATCH / DELETE)
  ✓ Versioning via URL path prefix: /api/v1/...
  ✓ Standard error response envelope on all errors (see §8.11)
  ✓ Pagination mandatory on all collection endpoints
  ✓ One Request VO + One Response VO per endpoint (see §8.5) [ADR-012]
  ✗ No RPC-style URLs (/getOrder, /createUser)
  ✗ No business logic in URL design
  ✗ No 200 OK with error in body
```

---

### 8.2 Request Processing Pipeline — Spring Boot Filter Chain

> Each filter must have a **single, documented purpose**. No filter may have more than one responsibility.

| Filter | Order | Purpose | Notes |
|---|---|---|---|
| CorrelationIdFilter | 1 | Extract or generate X-Correlation-ID, add to MDC | Mandatory on all requests |
| SecurityHeaderFilter | 2 | Inject mandatory response security headers | See §8.10 |
| AuthenticationFilter | 3 | Validate JWT / Bearer token | Delegates to Auth Module |
| RateLimitFilter | 4 | Enforce per-client rate limits | [SUGGESTION] |
| RequestLoggingFilter | 5 | Log inbound request metadata (not body) | See §8.7 |
| ContentSizeLimitFilter | 6 | Reject requests above size threshold | See §8.9 |
| `[SUGGESTION]` | 7 | IdempotencyFilter — check X-Request-ID for duplicate detection | For POST/PUT |

```
Rules:
  ✓ Filter order is explicit and documented here
  ✓ Each filter has a single responsibility
  ✓ Filters must not contain business logic
  ✓ Filter exceptions are handled by GlobalExceptionHandler
  ✗ No business logic in filters
  ✗ No DB calls in filters (except token validation cache lookup)
```

---

### 8.3 Session & State Management

> **See [ADR-003] — Stateless Architecture.**

```
Decision: This system is completely stateless. No server-side HTTP session.

Rules:
  ✗ No HttpSession usage anywhere in the codebase
  ✗ No @SessionScope beans
  ✗ No Spring Session dependency
  ✓ All user context carried in JWT token claims
  ✓ Token validated on every request by AuthenticationFilter
  ✓ Any data needed across requests must be re-fetched or re-sent by client
  ✓ No sticky sessions in load balancer configuration

[SUGGESTION] Token refresh strategy:
  - Access token TTL: [TODO]
  - Refresh token strategy: [TODO]
  - Token revocation strategy: [TODO]
```

---

### 8.4 Data Access Principles

> **Full detail in [Database Design Standards](#database-design-standards).**

```
PROHIBITED:
  ✗ No stored procedures
  ✗ No database functions
  ✗ No database triggers
  ✗ No views that encapsulate business logic
  ✗ No SELECT * queries — always project required columns only
  ✗ No unbounded queries — always paginate
  ✗ No string-concatenated queries (SQL injection — also a security rule)
  ✗ No N+1 query patterns — use JOIN or batch fetch
  ✗ findAll() on any entity is banned — use findAll(Pageable) minimum
  ✗ No IN clause with unbounded list — chunk to max 1000 items
  ✗ No cross-module repository access — repositories are module-scoped
  ✗ No repository calls directly from Controllers — always via Service

REQUIRED:
  ✓ Spring Data JPA repositories as the only data access mechanism
  ✓ @Query with JPQL for custom queries
  ✓ Native queries only when JPQL is provably insufficient (Tech Lead review required)
  ✓ All queries on tables above 10K rows must have execution plan reviewed
  ✓ Max rows for non-paginated query: 500 rows (internal jobs only)
  ✓ Batch jobs must use cursor / chunk-based processing
  ✓ Custom Repository base class overrides findAll() to enforce pagination
```

---

### 8.5 Request & Response Object Design

> **See [ADR-012]. Full VO naming rules in [API Design Guide](#api-design-guide).**

```
Core Principle:
  One API endpoint = One Request VO + One Response VO.
  No shared VOs across multiple APIs under any circumstance.

Request VOs:
  ✓ Name: <Action><Resource>Request (e.g., CreateOrderRequest)
  ✓ Only fields required for that specific API
  ✓ Annotated with @Valid and field-level constraints
  ✗ No domain/entity objects used as request objects
  ✗ No Optional<> fields — use nullable with @Nullable annotation

Response VOs:
  ✓ Name: <Resource>Response or <Action><Resource>Response
  ✓ Only fields the consumer needs — nothing more
  ✓ All fields must always be populated — no null fields ever
  ✓ Boolean fields must have explicit true/false — never null
  ✗ No entity objects exposed directly as response
  ✗ No internal DB IDs, sequences, or implementation details

Mapping:
  ✓ Use MapStruct for VO ↔ Domain object mapping
  ✗ No manual mapping code in Service or Controller
  ✗ BeanUtils.copyProperties is banned

Nested Objects:
  ✓ Nest only when relationship is strong and always present
  ✗ No optional nested objects returning {} or null — flatten or omit
```

---

### 8.6 Security Architecture

> **Full layer-by-layer rules in [Security Runbook](#security-runbook).** Summary below.

```
Principle: Defence in depth — every layer validates independently.

Layer                 Security Responsibility
────────────────────────────────────────────────────────
API Gateway           TLS enforcement, rate limiting
Filter Chain          Token validation, security response headers
Controller Layer      Form input validation (@Valid, constraints)
                      File upload validation (MIME, size, filename, AV scan)
Service Layer         Business rule authorisation (who can do what)
                      Input re-validation for sensitive operations
Data Layer            Parameterised queries only — no string concat
                      No sensitive data in query logs

[UI-LAYER] Security Topics:
  - Content Security Policy configuration [UI-LAYER]
  - CSRF token handling in Angular [UI-LAYER]
  - Sensitive data never stored in localStorage / sessionStorage [UI-LAYER]
  - XSS prevention — Angular's built-in sanitisation rules [UI-LAYER]
  - [SUGGESTION] Subresource Integrity (SRI) for third-party scripts [UI-LAYER]
```

---

### 8.7 Observability Standards

> **Full detail in [Observability Guide](#observability-guide).** Principles below.

```
Four Pillars:

1. LOGGING
   ✓ Structured JSON logging (Logback + SLF4J)
   ✓ Log levels: ERROR (system faults), WARN (business exceptions),
     INFO (key business events), DEBUG (dev only — never in prod)
   ✓ Every log line includes: correlationId, requestId, userId, timestamp
   ✗ No PII in logs
   ✗ No auth tokens / credentials in logs
   ✗ No request/response body logging in production

2. TRACING
   ✓ X-Correlation-ID generated at entry, propagated through all layers
   ✓ Correlation ID added to MDC at CorrelationIdFilter
   ✓ Correlation ID echoed in every response header
   ✓ Outbound calls to platform modules must forward correlation ID
   [UI-LAYER] ✓ Angular HTTP interceptor must attach X-Correlation-ID [UI-LAYER]

3. METRICS / INSTRUMENTATION
   ✓ Expose /actuator/metrics via Spring Boot Actuator
   ✓ Key metrics: API latency (p50/p95/p99), error rates, DB call times,
     thread pool utilisation, cache hit/miss ratio
   [SUGGESTION] Custom business metrics (e.g., orders-per-minute)

4. OBSERVABILITY
   ✓ /actuator/health — liveness probe
   ✓ /actuator/health/readiness — readiness probe
   ✓ Readiness probe includes DB and downstream service checks
   [SUGGESTION] Distributed tracing (OpenTelemetry / Zipkin / Jaeger)
   [SUGGESTION] Alerting rules and SLO definitions
```

---

### 8.8 Availability & Zero Downtime Principles

> **See [ADR-007].** Per-layer rules documented in §7.3.

```
[SUGGESTION] Additional availability principles to define:
  - Circuit breaker thresholds per downstream service
  - Retry policy — max retries, backoff strategy, which errors to retry
  - Bulkhead pattern — isolate thread pools per downstream
  - Graceful degradation — what functionality degrades vs what fails hard
  - Health check SLA — how quickly must readiness probe recover
```

---

### 8.9 Performance Engineering Principles

> **Targets defined in §10. Rules for developers below.**

#### Query & Data Access
```
  ✗ No SELECT * — project only required columns
  ✗ No stored procedures or DB functions [ADR-011]
  ✗ N+1 query pattern is prohibited
  ✗ No unbounded result sets
  ✓ Pagination mandatory — max page size 100 for API responses
  ✓ Queries on large tables must use indexed columns in WHERE
  ✓ Query execution plans reviewed before merging new queries
  ✓ Slow query log enabled — queries >100ms flagged
```

#### Response Size Policy
```
  ✓ Single resource response:   Max 50KB
  ✓ Collection response:        Max 100KB
  ✓ File downloads:             Streamed — not buffered in memory
  ✗ No response above 1MB — must be redesigned or streamed

  Enforcement:
  ✓ ContentSizeLimitFilter intercepts oversized responses
  ✓ spring.data.web.pageable.max-page-size=100
  ✓ Monitoring alert at 80% of limit
```

#### DB Query Return Size Policy
```
  ✓ Max rows per non-paginated query: 500 (internal jobs only)
  ✓ API responses: max 100 rows per page
  ✓ Batch jobs: cursor/chunk-based — never full dataset in memory
  ✗ findAll() without Pageable is banned in production code
  ✗ IN clause with unbounded list is prohibited — chunk to 1000 max

  Enforcement:
  ✓ Custom Repository base class overrides findAll()
  ✓ Code review checklist: "Does this query have a result size limit?"
  ✓ Integration tests assert pagination behaviour
```

#### API Layer
```
  ✗ No synchronous calls to external systems in user-facing request path
  ✓ Async or pre-fetch pattern for external data
  ✓ Gzip compression enabled on all REST responses above 1KB
  ✓ Explicit timeouts on all outbound HTTP calls
```

#### `[UI-LAYER]` Frontend Performance
```
[UI-LAYER] Topics to define:
  - Lazy loading mandatory for all Angular feature modules
  - Bundle size budget in angular.json
  - Debounce on search / autocomplete — no API call on every keystroke
  - Image optimisation strategy
  - [SUGGESTION] Core Web Vitals targets (LCP, FID, CLS)
  - [SUGGESTION] Server-side rendering / pre-rendering strategy
```

---

### 8.10 Cookie, Request & Response Header Policy

#### Cookie Policy
```
Allowed Use:
  ✓ CSRF token (HttpOnly=false so Angular JS can read it)
  ✓ Non-sensitive user preference cookies only
  ✗ No auth tokens in non-HttpOnly cookies
  ✗ No PII in cookies
  ✗ No sensitive business data in cookies

Mandatory Attributes on ALL cookies:
  HttpOnly=true         (except CSRF token)
  Secure=true           (HTTPS only — no exceptions)
  SameSite=Strict       (or Lax — never None without ADR justification)
  Max-Age=<explicit>    (no session-only cookies for persistent data)
  Domain=<scoped>       (never wildcard)
  Path=<scoped>         (never /)
```

#### Request Header Policy
```
Mandatory Headers on All Inbound Requests:
  Header              Purpose
  ─────────────────────────────────────────────────────────
  Authorization       Bearer token for auth
  X-Correlation-ID    Trace ID — propagated through all layers
  X-Request-ID        Unique ID per request (idempotency)
  Content-Type        Explicit — never assumed
  Accept              Explicit — default application/json

Rules:
  ✓ X-Correlation-ID: validate format — reject if malformed
  ✓ If X-Correlation-ID absent: generate at filter layer
  ✗ No business data in custom headers
  ✗ No sensitive data in headers (they appear in access logs)
  ✗ Authorization header must never be logged
```

#### Response Header Policy
```
Mandatory Headers on ALL Outbound Responses:
  Header                        Value
  ──────────────────────────────────────────────────────────────
  X-Correlation-ID              Echo inbound correlation ID
  X-Request-ID                  Echo inbound request ID
  Content-Type                  Always explicit
  Cache-Control                 Explicit on every response
  X-Content-Type-Options        nosniff
  X-Frame-Options               DENY
  Strict-Transport-Security     max-age=31536000; includeSubDomains
  Content-Security-Policy       [TODO — define per environment]
  Referrer-Policy               [SUGGESTION] strict-origin-when-cross-origin

Rules:
  ✗ No Server or X-Powered-By headers — strip in filter
  ✗ No stack trace or internal path in any response header
  ✗ No internal system or module names in headers
```

> **See [ADR-013] for the cookie and header standards decision.**

---

### 8.11 Exception Handling Policy

#### Classification

```
Two classes of exceptions only:

BUSINESS EXCEPTION
  Definition:  A business rule violation the caller can act upon.
  Examples:    Duplicate order, insufficient balance, account locked,
               resource not found for this user, invalid promo code.
  HTTP Status: 4xx (see status code table below)
  Logging:     WARN level with correlationId
  Handling:    Caught at Service layer → wrapped in BusinessException
               → propagated to GlobalExceptionHandler

SYSTEM EXCEPTION
  Definition:  Infrastructure or unexpected failure caller cannot act on.
  Examples:    DB connection failure, downstream timeout, NPE, IO error.
  HTTP Status: 5xx
  Logging:     ERROR level with full stack trace
  Handling:    Never catch and swallow. Propagate to GlobalExceptionHandler.
               Full stack trace logged internally.
               Sanitised generic message returned to caller — no internals.
```

#### Exception Hierarchy

```
RuntimeException
├── BusinessException (base — your class)
│   ├── ValidationException          → 400
│   ├── ResourceNotFoundException     → 404
│   ├── DuplicateResourceException    → 409
│   ├── AuthorizationException        → 403
│   └── BusinessRuleException         → 422
└── SystemException (base — your class)
    ├── IntegrationException          → 502
    ├── DataAccessException           → 500
    └── ServiceUnavailableException   → 503
```

#### Error Code Design

```
Format:  <DOMAIN>-<TYPE>-<NUMBER>

DOMAIN:  3-letter domain prefix
TYPE:    B = Business | S = System
NUMBER:  4-digit zero-padded

Examples:
  ORD-B-1001  Order already exists
  ORD-B-1002  Order cannot be modified in current state
  PAY-B-2001  Insufficient balance
  PAY-S-2001  Payment gateway unreachable
  USR-B-3001  User account is locked
  USR-B-3002  User not found
  DOC-B-4001  File type not allowed
  DOC-S-4001  File storage service unavailable

Rules:
  ✓ Error codes defined in central enum/constants per domain package
  ✓ Error codes never change once published — they are a contract
  ✓ New scenarios always get new codes — codes never repurposed
  ✗ No hardcoded error strings in code — always reference enum
  [SUGGESTION] Maintain error code registry as a separate published document
```

#### Error Response Envelope

```json
{
  "status": 422,
  "errorCode": "ORD-B-1002",
  "message": "Order cannot be modified because it is already dispatched.",
  "timestamp": "2026-04-26T10:30:00Z",
  "correlationId": "abc-123-xyz",
  "path": "/api/v1/orders/9987",
  "details": [
    {
      "field": "quantity",
      "message": "Quantity must be between 1 and 100"
    }
  ]
}
```

```
Rules:
  ✓ message — always human-readable, actionable for 4xx
  ✓ message — always generic and safe for 5xx:
    "An unexpected error occurred. Please try again or contact support."
  ✓ correlationId — always echoed so caller can reference in support
  ✓ details array — only for 400 validation errors; omit for all others
  ✗ Never expose stack traces in response
  ✗ Never expose internal class names, DB errors, or query text
  ✗ Never expose server paths or infrastructure details
```

#### HTTP Status Code Rules

```
Status   When to Use
──────────────────────────────────────────────────────────────
400      Input validation failed (form fields, types, formats)
401      Not authenticated — token missing or invalid
403      Authenticated but not authorised for this action
404      Resource does not exist (only when existence is not sensitive)
409      Conflict — duplicate resource, optimistic lock failure
422      Business rule violation — valid input, business says no
429      Rate limit exceeded
500      Unexpected system error — catch-all for SystemException
502      Upstream service returned invalid response
503      Upstream service unavailable or timeout
504      Gateway timeout on outbound call

BANNED:
  ✗ Never return 200 with an error body
  ✗ Never use 400 for business rule violations — use 422
  ✗ Never use 500 for something the client caused
  ✗ Never use 404 to hide existence of sensitive resources — use 403
```

#### Global Exception Handler Rules

```
Implementation: @RestControllerAdvice (one class only)

Rules:
  ✓ One GlobalExceptionHandler class in the application
  ✓ All @ExceptionHandler methods must log before returning
  ✓ BusinessException → log at WARN with correlationId
  ✓ SystemException   → log at ERROR with full stack trace
  ✗ No try-catch blocks in Controller layer — ever
  ✗ No try-catch in Service layer for SystemExceptions
  ✓ try-catch in Service layer ONLY when explicitly converting
    a SystemException to a BusinessException with full context

[UI-LAYER] Frontend Error Handling:
  - HTTP interceptor for global error interception [UI-LAYER]
  - User-facing message strategy per error type [UI-LAYER]
  - Error boundary components [UI-LAYER]
  - [SUGGESTION] Client-side error logging service [UI-LAYER]
```

---

### 8.12 Audit Policy

> **See [ADR-015].**

```
Audit Principle:
  Every state-changing operation on core business entities must produce
  an immutable audit record: what changed, who changed it, when, and
  from what previous state.

What Must Be Audited:
  ✓ All CREATE, UPDATE, DELETE on business entities
  ✓ All security events — login, logout, failed auth, permission change
  ✓ All data export or bulk read operations
  ✗ Regular read operations (SELECT) — do not audit
  ✗ Health checks, metrics polling — do not audit

Audit Table Rules:
  ✓ Table name: aud_<source_table_name>
  ✓ Append-only — no UPDATE or DELETE on audit tables
  ✓ Audit record written in same transaction as the change
  ✓ Use Hibernate Envers — no manual audit code
  ✓ old_value and new_value stored as JSON snapshots
  ✗ No PII in audit records unless compliance mandates it
  ✗ No foreign key constraints from audit tables to source tables
  ✗ Audit tables must never be queried by application business logic

[SUGGESTION] Additional audit topics:
  - Audit data retention policy (how long to keep)
  - Audit data archival strategy
  - Compliance reporting from audit data
  - GDPR right-to-erasure — how to handle audit records with PII
```

---

### 8.13 Coding Guidelines

> **Full detail in [Coding Standards & Governance Guide](#coding-standards--governance-guide).** Principles below.

```
Summary Principles:
  ✓ Constructor injection only — @Autowired on fields is banned
  ✓ One GlobalExceptionHandler — no exception handling in controllers
  ✓ Service layer owns @Transactional — not controllers, not repositories
  ✓ No business logic in filters, interceptors, or listeners
  ✓ @Async only in designated AsyncService classes with approved use cases
  ✓ All new third-party libraries must go through Dependency Governance Process
  ✓ OWASP Dependency Check runs on every CI build
  ✗ No Lombok @Data on JPA entities
  ✗ No BeanUtils.copyProperties — use MapStruct
  ✗ No version ranges in pom.xml — always pin exact versions

[UI-LAYER] Angular Coding Guidelines:
  - Naming conventions for components, services, pipes [UI-LAYER]
  - OnPush change detection strategy preference [UI-LAYER]
  - Unsubscribe strategy (takeUntilDestroyed / async pipe) [UI-LAYER]
  - [SUGGESTION] ESLint ruleset definition [UI-LAYER]
  - [SUGGESTION] Prettier configuration [UI-LAYER]
```

---

### 8.14 `[SUGGESTION]` Internationalisation & Localisation

```
[SUGGESTION] Topics to define:
  - Date/time: always store in UTC, convert at presentation layer
  - Currency: store as minor units (integer), format at presentation
  - Locale-aware formatting rules
  - [UI-LAYER] i18n strategy in Angular (ngx-translate / Angular i18n)
  - API responses: locale header support
```

### 8.15 `[SUGGESTION]` Feature Flags

```
[SUGGESTION] Topics to define:
  - Feature flag library/service choice
  - Flag naming convention
  - Flag lifecycle (creation → rollout → removal)
  - Who can enable flags in which environment
  - [UI-LAYER] Angular integration with feature flag service
```

### 8.16 `[SUGGESTION]` Background Jobs & Scheduling

```
[SUGGESTION] Topics to define:
  - Job framework (@Scheduled vs dedicated job runner)
  - Distributed lock for multi-instance deployments
  - Job failure handling and alerting
  - Job execution audit trail
  - Max execution time SLA per job category
```

### 8.17 `[SUGGESTION]` API Rate Limiting & Throttling

```
[SUGGESTION] Topics to define:
  - Rate limit tiers (internal app vs public REST API clients)
  - Rate limit headers in response (X-RateLimit-Limit, X-RateLimit-Remaining)
  - Behaviour on limit exceeded (429 + Retry-After header)
  - Rate limit storage (in-memory vs distributed)
```

---

## 9. Architecture Decision Records

> All decisions follow the standard ADR format:  
> **Title | Status | Context | Decision | Consequences | Alternatives Considered**

---

### ADR-001: Spring Boot Version Selection

**Status:** `[TODO — Accepted/Proposed]`  
**Context:** [TODO]  
**Decision:** [TODO — pin exact version]  
**Consequences:** [TODO]  
**Alternatives Considered:** [TODO]

---

### ADR-002: Angular Version Selection

**Status:** `[TODO — Accepted/Proposed]`  
**Context:** [TODO]  
**Decision:** [TODO — pin exact version]  
**Consequences:** [TODO]

---

### ADR-003: Stateless Architecture (No HTTP Session)

**Status:** Accepted  
**Context:** Traditional HTTP session creates server affinity, prevents horizontal scaling, and complicates zero-downtime deployment.  
**Decision:** This system is completely stateless. No HttpSession, no @SessionScope, no Spring Session. All user context is carried in JWT token claims and validated on every request.  
**Consequences:**  
+ Horizontal scaling without sticky sessions  
+ Zero-downtime deployments simplified (no session drain)  
+ Instances are fully interchangeable  
- Token size grows if many claims are embedded  
- Token revocation requires additional strategy (blocklist or short TTL)  
**Alternatives Considered:** Spring Session with Redis — rejected due to added infrastructure dependency and operational complexity.

---

### ADR-004: Dual API Strategy — Internal Web App API vs Public REST API

**Status:** `[TODO — Accepted/Proposed]`  
**Context:** The system serves two distinct consumer types: the Angular web application (internal, trusted, may have richer contracts) and third-party clients (external, public, must be stable and versioned strictly).  
**Decision:** Two distinct controller packages — `api/internal/` for the web app, `api/public/` for third-party consumers. Separate versioning, separate VOs, separate documentation.  
**Consequences:**  
+ Internal API can evolve faster without breaking external consumers  
+ External API contract is stable and independently versioned  
- More code to maintain  
- Risk of duplication — must be managed via shared service layer  
**Rules:**  
- Internal API is not documented in public API docs  
- Internal API may be protected by network policy (not just auth)  
- External API must go through full deprecation cycle before removal

---

### ADR-005: Package Structure Convention

**Status:** `[TODO — Decision Pending]`  
**Context:** [TODO]  
**Decision:** [TODO — Module-first or Layer-first — see §5.3]  
**Consequences:** [TODO]

---

### ADR-006: Intra-Module Package Layout

**Status:** `[TODO — Decision Pending]`  
**Context:** [TODO]  
**Decision:** [TODO]

---

### ADR-007: Zero Downtime Deployment Strategy

**Status:** `[TODO — Accepted/Proposed]`  
**Context:** Current system experiences downtime on every patch change. This is unacceptable.  
**Decision:** [TODO — Rolling deployment / Blue-Green / Canary — choose one]  
**Rules:** See §7.3 for per-layer implementation rules.  
**Consequences:** [TODO]

---

### ADR-008: In-Memory Caching Strategy

**Status:** `[TODO]`  
**Context:** [TODO]  
**Decision:** [TODO — Caffeine / Spring Cache]  
**Consequences:** [TODO]

---

### ADR-009: Async Processing for Non-Blocking Flows

**Status:** `[TODO]`  
**Context:** Certain flows (e.g., sending notifications, audit events) should not block the user-facing request thread.  
**Decision:** @Async permitted only in designated AsyncService classes with a named, configured ThreadPoolExecutor. Each async use case must be documented and approved.  
**Consequences:** [TODO]

---

### ADR-010: DB Connection Pool Configuration

**Status:** `[TODO]`  
**Context:** [TODO]  
**Decision:** [TODO — HikariCP, pool sizing]  
**Consequences:** [TODO]

---

### ADR-011: Prohibition of Stored Procedures and Database Functions

**Status:** Accepted  
**Context:** Business logic in stored procedures creates tight coupling between application and DB engine. It is hard to version, test, and migrate.  
**Decision:** No stored procedures, DB functions, triggers, or views containing business logic. Database is a dumb persistence store only. All business logic resides in the Spring Boot service layer.  
**Consequences:**  
+ Business logic is unit-testable without DB dependency  
+ DB-engine agnostic — easier to migrate  
- Complex aggregations must be done in code or structured JPQL  
- Developers must be disciplined about query performance  
**Alternatives Considered:** Stored procedures for reporting — rejected in favour of a dedicated reporting service if needed.

---

### ADR-012: One VO Per API — No Shared Value Objects

**Status:** Accepted  
**Context:** Teams reuse a single VO across multiple APIs for convenience. Over time this leads to bloated null-filled responses, unclear contracts, and cascading breaking changes.  
**Decision:** Every API endpoint has its own dedicated Request VO and Response VO. Sharing VOs between endpoints is prohibited.  
**Consequences:**  
+ API contracts are explicit and minimal  
+ No null fields in responses  
+ Changes to one API cannot break another  
- More classes to maintain  
- Requires MapStruct mappings between VOs and domain objects

---

### ADR-013: Cookie and Header Standards

**Status:** Accepted  
**Context:** Without explicit standards, security headers are inconsistently applied, correlation IDs are not propagated, and server identification headers leak implementation details.  
**Decision:** All cookies use HttpOnly + Secure + SameSite=Strict. X-Correlation-ID is propagated through all layers. Security headers applied globally via SecurityHeaderFilter. Server identification headers stripped.  
**Consequences:** [TODO]

---

### ADR-014: Platform Boundary — Owned vs Consumed Capabilities

**Status:** Accepted  
**Context:** Without explicit boundary definition, teams rebuild capabilities that already exist in the platform, leading to duplication and inconsistency.  
**Decision:** Capabilities listed in §3.3 as "Consume From Platform" will never be re-implemented here. Integration is always via the owning module's published API contract.  
**Consequences:**  
+ No capability duplication  
+ Clear ownership  
- Dependent on other teams' availability and SLAs  
- Must version-pin integration contracts

---

### ADR-015: Audit Strategy — Hibernate Envers + Append-Only Tables

**Status:** Accepted  
**Context:** Manual audit code is error-prone and inconsistent.  
**Decision:** Hibernate Envers for entity-level audit. Audit tables are append-only and written in the same transaction as the change. No manual audit code permitted.  
**Consequences:** [TODO]

---

### ADR-016: Dependency Governance — OWASP Scan + Approval Process

**Status:** Accepted  
**Context:** Third-party libraries are a primary source of security vulnerabilities. Without governance, risky libraries are introduced without review.  
**Decision:** No third-party library added without completing the Dependency Governance Process (see [Dependency Governance Process](#dependency-governance-process)). OWASP Dependency Check runs on every CI build. Any CRITICAL CVE causes a build failure.  
**Consequences:** [TODO]

---

### `[SUGGESTION]` ADR-017: API Gateway Strategy
**Status:** Proposed  
**Context:** [TODO]  
**Decision:** [TODO]

### `[SUGGESTION]` ADR-018: Message Queue / Event Bus Strategy
**Status:** Proposed  
**Context:** Async flows (audit events, notifications) need a reliable delivery mechanism.  
**Decision:** [TODO]

### `[SUGGESTION]` ADR-019: Distributed Tracing Tool Selection
**Status:** Proposed  
**Context:** [TODO]  
**Decision:** [TODO — OpenTelemetry / Zipkin / Jaeger]

### `[SUGGESTION]` ADR-020: Database Migration Tool
**Status:** Proposed  
**Context:** Schema changes must be versioned, repeatable, and support the expand-contract pattern for zero-downtime.  
**Decision:** [TODO — Flyway / Liquibase]

### `[SUGGESTION]` ADR-021: Containerisation & Orchestration Strategy
**Status:** Proposed  
**Context:** [TODO]  
**Decision:** [TODO — Docker + Kubernetes / ECS / etc.]

---

## 10. Quality Requirements

### 10.1 Performance Targets

| Metric | Target | Notes |
|---|---|---|
| API response time (p95) | ≤ 300ms | At [X] concurrent users, user-facing APIs |
| API response time (p99) | ≤ 1000ms | Degraded scenario |
| Route transition time (cached) | ≤ 2s | Click → full UI painted, JS cached, 4G Fast profile |
| Hard reload time (cold) | ≤ [TODO]s | Uncached — separate budget needed |
| DB query time — simple | ≤ 50ms | PK lookups, indexed single-table |
| DB query time — complex | ≤ 300ms | Joins, aggregates, reporting queries |
| File upload (10MB) | ≤ 5s | 4G Fast profile — clarify upper file size limit |
| Error rate | ≤ 0.1% | Across all user-facing API calls |
| TTFB | ≤ 600ms | Server response before browser starts rendering |
| Core Web Vitals — LCP | ≤ 1.8s | Must fit within route transition budget |
| Core Web Vitals — CLS | ≤ 0.1 | Layout stability |
| Core Web Vitals — INP | ≤ 200ms | Interaction to Next Paint (replaced FID in 2024) |
| JS bundle — initial chunk | ≤ 200KB | Gzipped; blocks first render |
| JS bundle — per lazy route | ≤ 100KB | Gzipped; per Angular lazy-loaded module |
| JS bundle — total budget | ≤ 2MB | Gzipped; all chunks combined |

### 10.2 Availability Targets

| Metric | Target |
|---|---|
| Uptime SLA | [TODO] % |
| RTO (Recovery Time Objective) | [TODO] |
| RPO (Recovery Point Objective) | [TODO] |
| Planned downtime window | Zero — rolling deployment |

### 10.3 Security Quality Goals

| Goal | Measure |
|---|---|
| No CRITICAL / HIGH CVE in dependencies | OWASP scan on every build |
| All inputs validated | Security Runbook layer-by-layer rules |
| No sensitive data in logs | Log review in code review checklist |
| `[SUGGESTION]` | OWASP Top 10 compliance review |
| `[SUGGESTION]` | Penetration testing schedule |

### 10.4 Scalability Goals

| Goal | Target |
|---|---|
| Horizontal scaling | Stateless — any number of instances |
| DB connection efficiency | Connection pool [ADR-010] |
| `[SUGGESTION]` | Auto-scaling triggers and thresholds |

### 10.5 Maintainability Goals

| Goal | Measure |
|---|---|
| Code coverage | [TODO] % minimum |
| `[SUGGESTION]` | Static analysis gate (SonarQube / Checkstyle) |
| `[SUGGESTION]` | Technical debt ratio target |
| `[SUGGESTION]` | API documentation coverage (OpenAPI 100%) |

---

## 11. Risks & Technical Debt

| # | Risk / Debt | Impact | Mitigation |
|---|---|---|---|
| 1 | Team unfamiliar with arc42 + C4 | Medium | Architecture review sessions, this document |
| 2 | Platform module SLA dependency | High | Circuit breakers, fallback strategy [ADR-TBD] |
| 3 | Zero-downtime deployment new to team | High | ADR-007, expand-contract DB pattern training |
| 4 | [TODO] | | |
| `[SUGGESTION]` | Third-party API rate limits under load | Medium | Caching + async queue strategy |
| `[SUGGESTION]` | Audit table growth over time | Medium | Archival and retention policy |
| `[SUGGESTION]` | Token revocation for stateless system | Medium | Short TTL + blocklist strategy |

---

## 12. Glossary

| Term | Definition |
|---|---|
| ADR | Architecture Decision Record — a document capturing a significant architectural decision |
| arc42 | Architecture documentation framework with 12 standardised sections |
| C4 Model | Context, Container, Component, Code — four levels of architecture diagram |
| VO | Value Object — a data transfer object used in API request/response |
| JWT | JSON Web Token — self-contained token carrying user claims |
| Correlation ID | A unique ID propagated across all system layers for request tracing |
| Soft Delete | Marking a record as deleted (is_deleted=true) rather than physically removing it |
| Expand-Contract | DB migration pattern — add new structure before removing old to allow zero-downtime |
| OWASP | Open Web Application Security Project |
| MDC | Mapped Diagnostic Context — thread-local log context in SLF4J/Logback |
| `[SUGGESTION]` | SLO | Service Level Objective — measurable reliability target |
| `[SUGGESTION]` | SLA | Service Level Agreement — contractual commitment |
| [TODO] | Add domain-specific terms here | |

---
---

# PART II — REFERENCED DOCUMENTS

---

# API Design Guide

> **Owner:** [TODO] | **Status:** Draft | **Referenced from:** arc42 §8.1, §8.5

## 1. URL Design

```
Format:     /api/{version}/{resource}/{id}/{sub-resource}
Version:    /api/v1/ — mandatory prefix on all public APIs
Resources:  Plural nouns, lowercase, hyphen-separated
            ✓ /api/v1/orders
            ✓ /api/v1/order-items
            ✗ /api/v1/getOrder
            ✗ /api/v1/OrderItem

Dual API Paths [ADR-004]:
  Internal:  /internal/v1/{resource}   (web app facing)
  Public:    /api/v1/{resource}         (third-party facing)
```

## 2. HTTP Verb Semantics

| Verb | Use | Body | Idempotent |
|---|---|---|---|
| GET | Retrieve resource | None | Yes |
| POST | Create resource | Required | No |
| PUT | Full replace | Required | Yes |
| PATCH | Partial update | Required | No |
| DELETE | Soft delete | None | Yes |

## 3. VO Naming & Design Rules

```
Request VOs:
  Pattern:  <Action><Resource>Request
  Examples: CreateOrderRequest, UpdateShippingAddressRequest

Response VOs:
  Pattern:  <Resource>Response or <Action><Resource>Response
  Examples: OrderResponse, OrderSummaryResponse

Rules:
  ✓ One VO per API endpoint — no sharing [ADR-012]
  ✓ No null fields in responses
  ✓ Use MapStruct for all VO ↔ Domain mappings
  ✗ BeanUtils.copyProperties is banned
  ✗ No entity classes exposed as API response
  ✗ No Optional<> in request VOs
```

## 4. Pagination Standard

```json
Request:  GET /api/v1/orders?page=0&size=20&sort=createdAt,desc

Response envelope for collections:
{
  "data": [...],
  "pagination": {
    "page": 0,
    "size": 20,
    "totalElements": 150,
    "totalPages": 8,
    "hasNext": true,
    "hasPrevious": false
  }
}
```

## 5. Error Response Envelope

> See arc42 §8.11 for full error handling policy.

## 6. API Versioning Policy

```
✓ Version in URL path: /api/v1/, /api/v2/
✓ New version only for breaking changes
✓ Old version supported for minimum [TODO] months after new version release
✓ Deprecation communicated via Deprecation and Sunset headers
✗ No header-based versioning for public APIs
✗ Never remove a field without a new version
✗ New optional fields may be added without version bump
```

## 7. `[SUGGESTION]` OpenAPI / Swagger Specification

```
[SUGGESTION] Rules to define:
  - OpenAPI 3.x specification mandatory for all public APIs
  - Spec-first or code-first approach decision
  - API documentation hosting (Swagger UI / Redoc)
  - Consumer-facing changelog
  - Mock server from spec for third-party consumers
```

## 8. `[UI-LAYER]` Angular API Client Layer

```
[UI-LAYER] Topics to define:
  - Generated API client from OpenAPI spec vs hand-written services
  - Base URL configuration per environment
  - Request/response typing strategy
  - HTTP interceptor integration
```

---

# Security Runbook

> **Owner:** [TODO] | **Status:** Draft | **Referenced from:** arc42 §8.6

## Layer-by-Layer Security Rules

### API Gateway / Entry Layer
```
✓ TLS 1.2 minimum — TLS 1.3 preferred
✓ Rate limiting per client [ADR-TBD]
✓ DDoS basic protection
✗ No plain HTTP — redirect to HTTPS or reject
[SUGGESTION] WAF (Web Application Firewall) rules
```

### Filter Layer
```
✓ Auth token validation on every request (except whitelisted public endpoints)
✓ Token claims extracted and placed in SecurityContext
✓ Security response headers injected (see §8.10)
✓ X-Correlation-ID extracted or generated
✗ No caching of failed auth decisions
```

### Controller Layer — Form Input Validation
```
All form inputs MUST be validated using @Valid + Jakarta Validation annotations.

Validation rules for form fields:
  ✓ Type validation — correct data type
  ✓ Not-null / not-blank where required
  ✓ Length constraints — min and max
  ✓ Format validation — regex patterns for emails, phone numbers, codes
  ✓ Range validation — numeric min/max
  ✓ Allowed values — @Pattern or @Enum validation
  ✓ No HTML/script injection — strip or reject
  ✗ Do not trust client-side validation alone — all validation server-side
  ✗ No raw string concatenation with user input
```

### Controller Layer — File Upload Validation
```
All file uploads MUST pass ALL of the following checks before processing:

  1. MIME Type Check
     ✓ Validate Content-Type header
     ✓ Validate actual file magic bytes (not just extension)
     ✓ Allowlist of permitted MIME types: [TODO — define per use case]
     ✗ Reject anything not on the allowlist

  2. File Size Limit
     ✓ Max file size: [TODO]MB
     ✓ Enforce at multipart config level (spring.servlet.multipart.max-file-size)
     ✓ Reject before processing — not after reading the entire stream

  3. Filename Sanitisation
     ✓ Strip path separators (/ \ ..)
     ✓ Strip special characters
     ✓ Generate a server-side UUID filename — never use client-supplied name

  4. Antivirus / Malware Scan
     ✓ All uploaded files scanned before storage
     ✓ Quarantine on detection — do not store
     [SUGGESTION] Define AV tool and integration pattern

  5. Content Validation
     ✓ Validate file content matches declared type (parse, don't trust header)
     [TODO] Define content validation rules per permitted file type
```

### Service Layer
```
✓ Authorisation checks — who is allowed to perform this action on this resource
✓ Re-validate sensitive inputs (defence in depth)
✓ No direct construction of queries from user input
✗ No business secrets / credentials hardcoded — use config / secrets manager
[SUGGESTION] Field-level encryption for sensitive data at rest
```

### Data Layer
```
✓ Parameterised queries only — JPQL @Query or Spring Data method names
✗ No string-concatenated queries
✗ No sensitive data (passwords, tokens, PII) in query logs
✗ No entity classes with @Formula using unvalidated user input
```

## `[SUGGESTION]` Additional Security Topics
```
[SUGGESTION] Define:
  - Secrets management strategy (Vault / AWS Secrets Manager / K8s secrets)
  - Password hashing standard (BCrypt with work factor)
  - PII data classification and handling
  - Data encryption at rest policy
  - Security incident response runbook
  - Penetration testing schedule and scope
  - OWASP Top 10 mitigation per item
```

---

# Observability Guide

> **Owner:** [TODO] | **Status:** Draft | **Referenced from:** arc42 §8.7

## 1. Logging Standards

```
Format:     Structured JSON (Logback)
Log Levels per Environment:
  Production:    ERROR, WARN, INFO
  Staging:       ERROR, WARN, INFO, DEBUG (gated by config)
  Development:   All levels

Mandatory Fields in Every Log Line:
  timestamp       ISO-8601 UTC
  level           ERROR / WARN / INFO / DEBUG
  correlationId   From MDC
  requestId       From MDC
  userId          From SecurityContext (anonymised if PII concern)
  service         Application name
  message         Human-readable description

What to Log:
  ✓ Service method entry/exit for key business operations (INFO)
  ✓ Business exceptions with context (WARN)
  ✓ System exceptions with full stack trace (ERROR)
  ✓ Outbound call start/end with duration (INFO)
  ✓ Authentication events — success and failure (INFO/WARN)

What NOT to Log:
  ✗ Request or response body (contains PII / sensitive data)
  ✗ Authorization header or any token value
  ✗ Passwords or credentials
  ✗ PII — names, emails, ID numbers (unless explicitly required)
  ✗ DB query parameters for sensitive queries
```

## 2. Distributed Tracing

```
✓ X-Correlation-ID generated at system entry (CorrelationIdFilter)
✓ Added to SLF4J MDC — automatically in all log lines
✓ Propagated in all outbound REST calls as X-Correlation-ID header
✓ Echoed in all response headers
[UI-LAYER] ✓ Angular HTTP interceptor attaches X-Correlation-ID to all requests

[SUGGESTION] Upgrade to OpenTelemetry trace context propagation (traceid + spanid)
[SUGGESTION] Zipkin / Jaeger integration for visual trace exploration
```

## 3. Metrics & Instrumentation

```
Spring Boot Actuator + Micrometer mandatory.

Standard Metrics to Expose:
  API Metrics:
    - http.server.requests (count, sum, max) — tagged by status, uri, method
    - API error rate per endpoint
  DB Metrics:
    - jdbc.connections.active / idle / max
    - Query execution time histogram
  JVM Metrics:
    - jvm.memory.used / jvm.memory.max
    - jvm.gc.pause
    - jvm.threads.live
  Cache Metrics (if Caffeine):
    - cache.gets (hit / miss)
    - cache.evictions

[SUGGESTION] Custom Business Metrics:
  - orders.created.count
  - payments.failed.count
  - [TODO] Add domain-specific metrics

Alerting Thresholds [SUGGESTION]:
  - Error rate > 1% for 5 minutes → alert
  - p95 latency > 500ms for 5 minutes → alert
  - DB connection pool > 80% → alert
```

## 4. Health Checks

```
Endpoints:
  /actuator/health         — Liveness probe (is the app running?)
  /actuator/health/readiness — Readiness probe (can it serve traffic?)

Readiness checks must include:
  ✓ Database connectivity
  ✓ Critical downstream service reachability
  [SUGGESTION] Cache connectivity
  [SUGGESTION] Message queue connectivity

Rules:
  ✓ Readiness probe used by load balancer / K8s — liveness is separate
  ✗ Never expose /actuator endpoints publicly — internal network only
  ✗ Health endpoint must not expose sensitive infrastructure details
```

---

# Database Design Standards

> **Owner:** [TODO] | **Status:** Draft | **Referenced from:** arc42 §8.4

## 1. Table Naming Convention

```
Format:       <domain>_<entity>
Case:         All lowercase
Separator:    Underscore only — no camelCase, no hyphens
Max Length:   30 characters
Prefix:       Domain prefix mandatory

Examples:
  ✓ ord_order
  ✓ ord_order_item
  ✓ usr_user_profile
  ✓ pay_payment_transaction
  ✗ Order, OrderItem, tbl_order, ORDER_MASTER

Junction Tables:   <domain>_<entity1>_<entity2>
Views (read-only): vw_<domain>_<entity>
Audit Tables:      aud_<source_table>

Index Names:       idx_<tablename>_<column>
Constraint Names:
  PK:  pk_<tablename>
  FK:  fk_<tablename>_<referenced_table>
  UQ:  uq_<tablename>_<column>
  CK:  ck_<tablename>_<column>

Column Names:
  ✓ lowercase, underscore-separated
  ✓ Descriptive — no abbreviations except standard ones
  ✗ No reserved words (type, value, order, user — use prefixed form)
  [SUGGESTION] Column naming convention document with reserved-word list
```

## 2. Mandatory Audit Fields — Every Table

| Column | Type | Nullable | Default | Purpose |
|---|---|---|---|---|
| id | BIGINT / UUID | NOT NULL | Sequence / UUID | Primary Key |
| created_by | VARCHAR(100) | NOT NULL | | Who created |
| created_at | TIMESTAMP WITH TZ | NOT NULL | NOW() | When created (UTC) |
| updated_by | VARCHAR(100) | NOT NULL | | Who last modified |
| updated_at | TIMESTAMP WITH TZ | NOT NULL | NOW() | When modified (UTC) |
| is_deleted | BOOLEAN | NOT NULL | FALSE | Soft delete flag |
| deleted_by | VARCHAR(100) | NULL | | Who soft-deleted |
| deleted_at | TIMESTAMP WITH TZ | NULL | | When soft-deleted |
| version | BIGINT | NOT NULL | 0 | Optimistic locking |

```
Rules:
  ✓ All timestamps in UTC — no local timezone
  ✓ version used by JPA @Version — mandatory for all entities
  ✓ is_deleted=true means invisible to all application queries
  ✓ No hard deletes from application code
  ✗ No table exempt from audit fields
  ✗ created_at must never be updated after insert
  ✗ Application never manually sets created_at / updated_at
    — handled by @CreatedDate / @LastModifiedDate (Spring Data Auditing)
```

## 3. Primary Key & Unique Key Policy

```
Primary Key:
  ✓ Surrogate PK on every table
  ✓ BIGINT (sequence) for internal-only tables
  ✓ UUID for tables whose records are exposed via public REST API
    (prevents enumeration attacks)
  ✗ No composite PKs — use surrogate PK + unique constraint
  ✗ No business key as PK (email, order_number etc.)

Business Unique Key:
  ✓ Business uniqueness via UNIQUE CONSTRAINT — not via PK
  ✓ Named index (uq_ prefix) for every unique constraint
  ✓ Validate uniqueness at Service layer before insert
  ✗ Never catch DataIntegrityViolationException to return user message
    — validate before insert, not after failure
```

## 4. Audit Table Structure

```
Table Name: aud_<source_table>
Example:    aud_ord_order

Column          Type              Purpose
──────────────────────────────────────────────────
id              BIGINT            PK of audit record
entity_id       BIGINT / UUID     Identifier of source entity
operation       VARCHAR(10)       CREATE / UPDATE / DELETE
changed_by      VARCHAR(100)      User who made the change
changed_at      TIMESTAMP WITH TZ When the change happened (UTC)
old_value       JSONB / TEXT      Previous state (null for CREATE)
new_value       JSONB / TEXT      New state (null for DELETE)
correlation_id  VARCHAR(100)      Trace ID from the request
```

## 5. Migration Policy

```
Tool: [TODO — Flyway / Liquibase] [SUGGESTION: ADR-020]

Rules:
  ✓ All schema changes via migration scripts — no manual DDL
  ✓ Migration scripts are versioned and immutable once committed
  ✓ Expand-contract pattern for zero-downtime migrations:
      Step 1: Add new column (nullable) — deploy
      Step 2: Migrate data — deploy
      Step 3: Add NOT NULL constraint — deploy
      Step 4: Remove old column — deploy (separate release)
  ✗ Never drop or rename columns in same release as code change
  ✗ No destructive migration without data backup verification
  [SUGGESTION] Migration tested in staging before production
  [SUGGESTION] Rollback script for every migration
```

## 6. `[SUGGESTION]` Additional Database Topics

```
[SUGGESTION] Define:
  - Indexing strategy — when to index, composite index rules
  - Partitioning strategy for large tables
  - Archive / purge policy for old data
  - Read replica usage rules
  - Database backup and restore procedure
  - Connection pool sizing formula
```

---

# Coding Standards & Governance Guide

> **Owner:** [TODO] | **Status:** Draft | **Referenced from:** arc42 §8.13

## 1. Spring Annotation Governance Policy

### Category 1: Freely Usable

| Annotation | Allowed Context |
|---|---|
| @RestController | Controller classes only |
| @Service | Service classes only |
| @Repository | Repository interfaces only |
| @Component | Utility / helper classes only |
| @Autowired | Constructor injection **only** — field injection banned |
| @Value | Configuration properties injection |
| @Valid / @Validated | Request VO parameters in Controllers |
| @Transactional | Service layer methods only (see rules) |
| @Query | Repository interfaces only |
| @Slf4j | Any class needing logging |
| @CreatedDate / @LastModifiedDate | JPA entity audit fields only |
| @Version | JPA entity optimistic locking field only |

### Category 2: Conditionally Usable — Tech Lead Approval Required

| Annotation | Restriction |
|---|---|
| @Async | Only in designated AsyncService classes. Must use named, configured ThreadPoolExecutor. Never on @Transactional methods. All exceptions handled in Future/CompletableFuture. Requires ADR for each new async flow. |
| @Scheduled | Only in designated ScheduledJobService. Must have distributed lock in multi-instance deployment. All executions logged with duration. |
| @Cacheable / @CacheEvict | Only on Service layer methods. Cache key reviewed. TTL explicitly configured. Eviction strategy defined. |
| @EventListener / @TransactionalEventListener | Only for internal decoupling — not for business-critical flows. Must be documented in §6. |
| @Profile | Only for environment-specific beans. Must not switch business logic. |

### Category 3: Banned — Never Use

| Annotation | Reason |
|---|---|
| @Autowired on fields | Breaks testability, hides dependencies |
| @SuppressWarnings | Masks real problems — fix the root cause |
| @Data (Lombok) on JPA Entity | Generates problematic equals/hashCode — use @Getter @Setter only |
| @Transactional on Controller | Transaction scope too broad — service layer only |
| @SpringBootTest on every test | Slows CI — use slice tests (@WebMvcTest, @DataJpaTest) |

## 2. @Transactional Rules

```
✓ Only on Service layer methods
✓ Explicitly set readOnly=true for read-only service methods
✓ Transaction boundaries should be as small as possible
✗ No @Transactional on Controller
✗ No @Transactional on Repository (Spring Data manages this)
✗ No long-running operations (HTTP calls, file I/O) inside a transaction
✗ No catching exceptions inside @Transactional that would prevent rollback
[SUGGESTION] Document transaction isolation level decisions per use case
```

## 3. Approved Java Libraries

| Category | Library | Version |
|---|---|---|
| Web | Spring Boot Starter Web | [ADR-001] |
| Security | Spring Security | [ADR-001] |
| Data | Spring Data JPA | [ADR-001] |
| Audit | Hibernate Envers | [pinned] |
| Mapping | MapStruct | [pinned] |
| Logging | Logback + SLF4J | [pinned] |
| Testing | JUnit 5, Mockito, AssertJ, Testcontainers | [pinned] |
| Validation | Jakarta Validation API | [pinned] |
| JSON | Jackson | [pinned] |
| Utilities | Apache Commons Lang | [pinned] |
| Connection Pool | HikariCP | [ADR-010] |
| Resilience | Resilience4j | Conditional [ADR-TBD] |
| Cache | Caffeine | Conditional [ADR-008] |

### Banned Libraries

| Library | Reason |
|---|---|
| Guava | Use Java standard library equivalents |
| Apache Commons BeanUtils | Use MapStruct instead |
| Any JSON lib other than Jackson | Standardise on one — Gson, Fastjson banned |
| Lombok @Data on entities | See annotation policy |

## 4. Testing Standards

```
Test Pyramid:
  ✓ Unit tests — 70%+ coverage target
  ✓ Integration tests — @DataJpaTest, @WebMvcTest slice tests
  ✓ End-to-end tests — limited, for critical paths only
  ✗ No @SpringBootTest for unit testing

Rules:
  ✓ Every public service method has a unit test
  ✓ Every API endpoint has a @WebMvcTest integration test
  ✓ Every repository query has a @DataJpaTest test
  ✓ Testcontainers for DB integration tests — no H2 in-memory
  ✓ Test method name: given_<state>_when_<action>_then_<expectation>
  [SUGGESTION] Mutation testing to validate test quality
  [SUGGESTION] Contract testing for public REST API (Pact)
  [SUGGESTION] Performance / load testing in CI pipeline
```

## 5. Code Review Checklist

```
Before approving any PR, verify:
  API:
  □ Does every endpoint have its own Request and Response VO?
  □ Are all response fields always populated (no nulls)?
  □ Is the correct HTTP status code used?

  Data Access:
  □ Does every multi-row query have a LIMIT or Pageable?
  □ Are there any N+1 patterns?
  □ Is SELECT * used anywhere?

  Exception Handling:
  □ Is there any try-catch in a Controller?
  □ Is any SystemException being swallowed?
  □ Does every error use a defined error code from the enum?

  Security:
  □ Is @Valid used on all request VOs?
  □ Are file uploads validated (MIME, size, filename, AV)?
  □ Is the Authorization header logged anywhere?

  Performance:
  □ Is there any unbounded query?
  □ Is there any synchronous external call in the request path?

  New Dependencies:
  □ Did the dependency go through the Dependency Governance Process?
  □ Has OWASP scan passed with no CRITICAL/HIGH CVE?

  [SUGGESTION] Automate this checklist as a PR template
```

## 6. `[UI-LAYER]` Angular Coding Standards

```
[UI-LAYER] Topics to define:
  - Component naming convention (PascalCase, -component suffix)
  - Service naming convention (-service suffix)
  - File naming convention (kebab-case)
  - OnPush change detection as default
  - Unsubscribe strategy (takeUntilDestroyed preferred)
  - No logic in templates beyond simple binding
  - Form validation approach (Reactive Forms preferred)
  - [SUGGESTION] Standalone components vs NgModule decision
  - [SUGGESTION] Signal-based reactivity adoption strategy
  - [SUGGESTION] Unit test framework (Jest vs Karma/Jasmine)
```

---

# Dependency Governance Process

> **Owner:** [TODO] | **Status:** Draft | **Referenced from:** arc42 §8.13, ADR-016

## Process Steps

```
Step 1: Need Identification
  Developer raises a Dependency Request documenting:
    - What problem it solves
    - Why existing approved libraries are insufficient
    - License type (GPL libraries are banned — Apache/MIT/BSD only)
    - Transitive dependency count and assessment

Step 2: Security Scan
  Library scanned using OWASP Dependency Check
  CRITICAL or HIGH CVE → automatic rejection
  MEDIUM CVE → Tech Lead decision with documented justification

Step 3: Tech Lead Approval
  Reviews: necessity, license, CVE report, transitive deps, maintenance status
  Documents approval as an ADR

Step 4: Version Pinning
  Approved library added to approved list with exact version pinned
  No version ranges permitted (1.2.+ banned — use 1.2.3)

Step 5: Ongoing Monitoring
  OWASP Dependency Check on every CI build
  Monthly CVE status report
  New CRITICAL CVE on existing library → emergency upgrade process
```

## Rules

```
✗ No library added to pom.xml without completing this process
✗ No SNAPSHOT versions in production
✗ No version ranges — always pin exact version
✓ All approved libraries tracked in Approved Library Register (§3 of this doc)
✓ License compatibility reviewed for each new library
[SUGGESTION] Automated PR check for new dependencies not in approved list
[SUGGESTION] Renovate / Dependabot for automated dependency update PRs
```

---

*Document generated from brainstorming session — [TODO] items require team input.*  
*All `[SUGGESTION]` items are recommended additions not yet accepted.*  
*All `[UI-LAYER]` items require input from the frontend architecture specialist.*  
*ADR status: Accepted = decided, Proposed = pending decision, TODO = not yet discussed.*
