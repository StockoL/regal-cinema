# 6. Development log and engineering phases

The phases below are the planned build order, worked out from the dependencies between apps in [section 4](architecture.md). They aren't a commit history yet, because the build hasn't started. Each phase's `<details>` block will be filled in with the real narrative, decisions and problems as development happens, and the planned scope is what those entries get checked against. The Must steps in [section 1](user_stories.md) are the spine of the build. Should and Could steps are added once the spine works.

## Phase 1: Foundations, auth and screenings catalogue

<details>
<summary>Phase 1</summary>

Planned scope: project scaffolding; the `accounts` app and the auth and registration flow (4.16); the `screenings` catalogue (`Film`, `Screen`, `Seat`, `TicketClass`, `TicketType`, `Screening`, `ScreeningPrice`) including the TMDb integration (4.15); and the deployment skeleton, so there's a live site from the start. Public browsing only, with no booking yet. This comes first because almost every other app depends on a logged-in user and a real catalogue to book against.

### 24 October 2026: local PostgreSQL

I develop against PostgreSQL, not Django's default SQLite, because production on Render is PostgreSQL and the riskiest part of the design depends on how the database handles concurrent writes. The seat hold transaction (4.8) locks rows with `select_for_update()`. SQLite ignores that and locks the whole database on every write instead, so a double-booking test that passes on SQLite would tell me nothing about the live site.

I considered three ways to run it: a native install, Docker, or a hosted development database. I chose the native install. It runs as a Windows service, works offline, and has no network delay, which matters for a concurrency test that fires requests at nearly the same moment. Docker Desktop would have meant setting up WSL2 for a single service. A hosted database stops working whenever I'm offline, and Render's free databases expire.

I installed PostgreSQL 17 with `winget install PostgreSQL.PostgreSQL.17`, and I'll pick the same major version for the Render database so the two environments behave the same. I then created a `regal` role and a `regal_cinema` database owned by it. The role has `CREATEDB` because Django's test runner creates and drops its own test database. The connection string lives in an uncommitted `.env` file. The steps are in the README under Local deployment.

</details>

## Phase 2: Core booking skeleton, seats and holds

<details>
<summary>Phase 2</summary>

Planned scope: the transactional core of `bookings`: `SeatHold`, `Booking`, `SeatBooking`, the interactive seat map, ticket types and infants, going back to amend, immediate release of seats, and the database-level double-booking protection (4.8). Payment is stubbed at this stage, with bookings marked paid manually, so the seat concurrency logic, the highest-risk part of the project, can be built and tested before Stripe is added.

### To be completed during development

</details>

## Phase 3: Payment integration

<details>
<summary>Phase 3</summary>

Planned scope: Stripe on top of the working booking skeleton: PaymentIntent creation, webhook handling and signature verification, idempotency, and the retry and hold-extension behaviour for failed payments (4.13). Building this after Phase 2 means payment problems and seat concurrency problems get debugged one at a time.

### To be completed during development

</details>

## Phase 4: Concessions, membership and discounts

<details>
<summary>Phase 4</summary>

Planned scope: the `concessions` app (`Product`, `OrderItem`) in checkout; the `membership` app (`MembershipTier`, `Voucher`); and the discount and voucher order (4.10). This comes after payment works because there's no sensible way to test whether a discount applies correctly until a charge can already succeed without one.

### To be completed during development

</details>

## Phase 5: Priority booking and venue features

<details>
<summary>Phase 5</summary>

Planned scope: priority booking logic and the greyed-out listing state (4.18); the `venue` app (`EnquiryRequest`, `VenueSettings`, private hire and screening visibility per 4.19, 4.23); and the static pages (About, Accessibility policy, Membership terms).

### To be completed during development

</details>

## Phase 6: In-venue and staff tooling

<details>
<summary>Phase 6</summary>

Planned scope: staff-assisted card-in-person bookings (4.14); the `staff` app (audit log, refunds, customer cancellation requests, sales dashboard per 4.9 and 4.22); the permission groups and the separate `/staff/` login (4.9, 4.12). This is last among the functional work because it depends on bookings, payments and discounts already existing.

### To be completed during development

</details>

## Phase 7: Accessibility, cross-browser and testing pass

<details>
<summary>Phase 7</summary>

Planned scope: the accessibility implementation (4.17) checked properly instead of assumed; cross-browser and responsiveness checks; and the structured testing pass in [section 7](testing.md), covering validators, Lighthouse and the manual and automated test matrix.

### To be completed during development

</details>

---

[← 5. Core features](features.md) · [README](../README.md) · [7. Testing and quality assurance →](testing.md)
