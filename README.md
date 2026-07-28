# Regal Cinema — Booking Platform

## A Full-Stack Django Application

## Introduction

Regal Cinema is a fictional boutique cinema, and this project is a full-stack Django booking platform built for it as my Milestone 4 submission. It's inspired by independent, hospitality-led cinemas — venues with table seating, a bar, and a broader events calendar, rather than a standard multiplex.

The project exists to address a real gap: many small independent cinemas run on generic, off-the-shelf ticketing systems that treat every seat as identical inventory and don't reflect what actually makes these venues distinctive — premium seating tiers, food and drink service, membership schemes, and private event hire. This application builds those things in as core features rather than bolting them on afterwards.

```text
Django (data model, business logic)
  └─ Server-rendered templates
       └─ CSS design system + a small amount of hand-written JavaScript
```

### Technical approach

- **Backend:** Django with a relational (PostgreSQL) database. The schema is built directly around the venue's real domain — screenings, seat tiers, bookings, concessions, membership — with relationships and constraints designed to prevent issues like double-booking.
- **Frontend:** Server-rendered Django templates, plain CSS, and a small amount of purpose-written JavaScript, rather than a frontend framework. This was a deliberate choice given the project's assessment criteria — see the [UX Design Strategy](#ux-strategy) section for the reasoning.
- **Design system:** A dark, cinema-inspired visual style built from a small set of reusable layout and colour patterns, rather than one-off page styles — based on the _Every Layout_ approach (Heydon Pickering and Andy Bell) and Alla Kholmatova's _Design Systems_.

---

## <a name="top"></a>Table of Contents

1. [Project Purpose & User Stories](#purpose)
2. [Strategic Research](#research)
3. [UX Design Strategy (The 5 Planes)](#ux-strategy)
4. [System Architecture & Logic Maps](#architecture)
5. [Core Features](#features)
6. [Deployment Guide](#deployment)
7. [Credits & Acknowledgements](#credits)
8. [Development Log & Engineering Phases](#dev-log)
9. [Testing & Quality Assurance Portfolio](#testing)
10. [Marketing Development Thoughts (Future Business Ideas)](#marketing-development)

---

## 1. <a name="purpose"></a> Project Purpose & User Stories

Regal Cinema exists to give a boutique independent cinema a booking experience that actually matches its offering — premium seating, food and drink service, and a membership scheme — rather than a generic multiplex ticketing template.

### The Cinema-Goer

_Focus: booking seats, adding food/drink, and being recognised as a returning customer_

- **User story:** As a customer, I want to see what's on and browse showtimes clearly, so I can decide what to watch and when.
- **User story:** As a customer, I want to choose specific seats on a seating plan, so I can pick my preferred view and seat type (standard, sofa, or box).
  - _Acceptance criteria:_ seat availability reflects the current state accurately; the same seat can never be booked twice for the same screening; the seating plan is usable on a phone-sized screen.
- **User story:** As a customer needing a captioned or audio-described screening, I want that information shown clearly on the listing, so I can choose an appropriate showing without having to ask.
- **User story:** As a customer, I want to add drinks or snacks to my order at checkout, so they're ready for me on arrival instead of queuing at the bar.
- **User story:** As a returning customer, I want my membership discount applied automatically, so being a Friend member feels worthwhile.

### The Venue Manager

_Focus: managing schedules and enquiries without needing developer help_

- **User story:** As a manager, I want to add and edit screenings (film, screen, time, price) through an admin interface, so I can update what's showing myself.
  - _Acceptance criteria:_ the system prevents two screenings being scheduled on the same screen at overlapping times.
- **User story:** As a manager, I want to see private hire and event enquiries in one place, so I can follow them up.

## <p align="right">(<a href="#top">Back to top</a>)</p>

## 2. <a name="research"></a> Research

### Everyman & Tivoli Cinema Group

- **What works well:** A dark, premium visual style that makes the site feel consistent with the in-person venue experience. Food and drink pre-ordering is built into the booking flow as a core step, not added on as an afterthought.
- **What doesn't translate to this project:** As large chains, they run on enterprise ticketing platforms (e.g. Vista) built to serve many venues at once. That's more infrastructure than a single independent site needs, and makes it harder to support small-venue specifics — a local membership scheme, or one-off private hire.
- **What this project takes from them:** the dark, premium visual language, and the idea of treating food/drink pre-ordering as a first-class part of checkout — built on a much simpler, single-venue Django backend rather than enterprise ticketing software.

## <p align="right">(<a href="#top">Back to top</a>)</p>

## 3. <a name="ux-strategy"></a> UX Design Strategy (The Five Planes)

This section follows Jesse James Garrett's "five planes" model — Strategy, Scope, Structure, Skeleton, Surface — moving from the most abstract design decisions to the most concrete.

### Wireframes

![Description](./docs/wireframes/….png)

### I. Strategy

- **User goals:** customers want an easy way to check what's on, book the seats they want, and optionally add food and drink to their order. Staff want a simple way to manage screenings and see bookings without needing developer help.
- **Site goals:** encourage premium seat bookings and food/drink add-ons, and build repeat custom through the membership scheme.
- **Target audience:** local film-goers looking for a more comfortable, hospitality-led experience than a standard multiplex — including families and older customers (served by discounted showings like Family Super Saver and Silver Screen), students, and people booking the venue privately for events.

### II. Scope

#### Feature summary

| Area         | In scope                                                                                | Out of scope (for now)                                |
| :----------- | :-------------------------------------------------------------------------------------- | :---------------------------------------------------- |
| Booking      | Seat selection on an interactive seating plan, by tier (standard / sofa / box)          | Split payments between multiple people on one booking |
| Food & drink | Pre-ordering linked to a booking                                                        | Live in-seat ordering during a screening              |
| Membership   | Paid, tiered Friend membership (priority booking, ticket/food discounts); gift vouchers | Automatic recurring renewal/billing                   |
| Admin        | CRUD for films, screens, and screenings; visibility of bookings and enquiries           | Automated pricing based on historical sales data      |

#### Design principles

- **No frontend framework, organised with CUBE CSS.** The interface is built with plain, semantic HTML and CSS — no React/Vue, no build step — using Andy Bell's **CUBE CSS** methodology to organise the CSS itself: **C**omposition, **U**tility, **B**lock, **E**xception. This isn't a separate decision from the "no framework" choice — CUBE CSS is specifically designed with _Every Layout_ as its Composition layer, so adopting it extends a decision already made rather than adding a competing one.
  - **Composition** — the _Every Layout_ patterns already decided: a "stack" for consistent vertical spacing, a "switcher" for elements that sit side-by-side on desktop and stack on mobile without manual breakpoints, and similar layout-level primitives. These control arrangement, not appearance.
  - **Utility** — small, single-purpose classes for common needs that don't deserve their own component: a `.visually-hidden` class for text that's read by a screen reader but not shown visually (used directly for the seat map's accessible seat names in [4.17](#architecture)), spacing utilities built on the same CSS custom properties already used for the design tokens (e.g. `var(--space-m)`).
  - **Block** — the actual reusable components, each with its own scoped, sensibly-named styles: `.seat-map`, `.film-card`, `.nav`. This is where the "cards for film posters" idea from Surface (below) is actually implemented, as a named, self-contained block rather than a one-off set of styles.
  - **Exception** — scoped, deliberate overrides for a component in an unusual state, applied via data attributes rather than piling on more classes. **This maps directly onto the seat map's states from [4.8](#architecture):** rather than four separate modifier classes for available/selected/held/booked, each seat carries a single `data-seat-status` attribute, and the exception layer defines what changes for each value. One attribute reflects the seat's actual state; the styling for every state lives in one predictable place rather than being scattered across conditional classes.

  Beyond keeping the CSS itself organised, this gives the project a consistent, explainable naming convention throughout — directly relevant to the assessment's own emphasis on consistent naming and readable, well-organised code, since "why is this class named the way it is" now has a one-word answer (which of the four layers it belongs to) rather than being ad hoc.

- **Dark, cinema-inspired palette:** dark background, light text, a warm accent colour for interactive states — meant to evoke a cinema auditorium rather than a typical light-mode web app.
- **Consistent media framing:** posters and trailers are shown at fixed aspect ratios so the page layout doesn't jump as images load.

#### Data & security principles

- Seat double-booking is prevented at the database level (a unique constraint), not just in the interface, so it holds even if two requests arrive at almost the same time.
- No card details or passwords are stored directly. Payments go through Stripe, and only a payment reference is kept in the local database.

### III. Structure

#### Interaction model

Actions that need a live check against the database — most importantly, reserving a seat — are handled with a JavaScript fetch request to the server rather than a full page reload. This means the page can show an inline error (e.g. "that seat was just taken") without losing the user's other selections, rather than reloading the whole page.

```text
User selects seats, clicks "Continue"
   │
   ▼
JS sends a fetch request with the chosen seat IDs
   │
   ▼
Server checks seat availability
   ├── available → holds are created, checkout proceeds
   └── conflict  → affected seats are returned and marked unavailable in the UI
```

#### Site map

```text
Home (what's on)
  └─ Film detail (synopsis, trailer, showtimes)
        └─ Screening (seat selection)
              └─ Checkout (add food/drink → pay)
  Membership / account (profile, vouchers)
  About / private hire (static content, enquiry form)
```

### IV. Skeleton

- **Booking page layout:** the seating plan and the order summary sit side by side on wide screens, and stack vertically on narrow ones, using the "switcher" layout pattern rather than a manual breakpoint for each screen size.
- **Navigation:** a simple top nav bar (the "cluster" pattern), which wraps naturally onto a second line on small screens rather than switching to a separate mobile menu component.
- **Content spacing:** long text sections (film synopses, policies) use consistent vertical spacing via CSS custom properties, so spacing stays uniform without repeated one-off margin values.

### V. Surface

- **Palette:** dark background (`#0b0b0d`), light text (`#f5f5f7`), and a warm gold accent colour for active/selected states.
- **Cards:** film posters and information sit in a simple bordered card with consistent internal padding.
- **Media:** trailers and posters are constrained to fixed aspect ratios (16:9 for video, 2:3 for posters) so they scale without distortion or causing the layout to shift as they load.

## <p align="right">(<a href="#top">Back to top</a>)</p>

## 4. <a name="architecture"></a> System Architecture & Data Model

The project is split into seven Django apps, each covering one distinct area of the domain. Splitting it this way keeps each app's models and logic focused on a single responsibility, and means several of the apps (`concessions`, `membership`) could realistically be reused on a different project with minimal change.

| App           | Responsibility                                                                 |
| :------------ | :----------------------------------------------------------------------------- |
| `accounts`    | User profile data: membership tier and expiry                                  |
| `screenings`  | The venue's fixed catalogue: films, screens, seats, and scheduled screenings   |
| `bookings`    | The transactional core: bookings and the seats attached to them                |
| `concessions` | Bar/snack products and the items attached to a booking                         |
| `membership`  | Membership tiers and gift vouchers                                             |
| `venue`       | Static site content and private hire / event enquiries                         |
| `staff`       | Staff-only tooling that cuts across the other apps: audit log, sales reporting |

### 4.1 `screenings`

- **Film** — `tmdb_id` (nullable — see 4.15), `title`, `synopsis`, `poster_path`, `trailer_key`, `age_rating`, `duration_minutes`. Populated from the TMDb API and cached locally rather than queried live on every page load — see [4.15](#architecture) for the full mechanics.
- **Screen** — `name`, `total_capacity`.
- **Seat** — `screen` (FK), `row_label`, `seat_number`, `tier` (standard / sofa / box). The fixed physical seating plan for a screen; does not change per booking.
- **TicketClass** — `name` (e.g. Standard, Silver Screen, Summer Saver, Family Super Saver, Subtitled, Live Event), `description`, `default_price_pence` (nullable — a convenience suggestion, not an enforced price). Modelled directly on how the real Regal Cinema actually prices things: a discounted showing (like a senior-focused "Silver Screen" screening) is a _property of that specific showing_, not a discount computed from who's booking it. See [4.18](#architecture).
- **Screening** — `film` (FK), `screen` (FK), `ticket_class` (FK to `TicketClass`), `date_time`, `base_price`, `public_onsale_at` (nullable — see 4.18 for priority booking), `is_private` (boolean, default `False` — see [4.19](#architecture) for private hire), `has_captions`, `has_audio_description`.

### 4.2 `bookings`

- **Booking** — `user` (nullable FK — see design note below), `screening` (FK), `status` (pending / paid / cancelled / refunded), `channel` (online / in_venue), `payment_method` (`card_online` / `card_in_person`), `stripe_payment_intent_id` (nullable — only set for `card_online`), `created_by` (nullable FK to `User`, the staff member who took an in-venue booking), `voucher_used` (nullable FK to `Voucher`), `discount_applied_percent` (snapshot, see note below), `created_at`.
- **SeatBooking** — `booking` (FK), `seat` (FK), `screening` (FK, duplicated from `booking.screening` specifically so the database can enforce a `unique_together` constraint on `(screening, seat)`). This is what stops two people booking the same seat for the same screening.

A booking can have several `SeatBooking` rows (a party booking four seats together is four rows against one `Booking`), which is why seats live on their own linking table rather than as a single field on `Booking`.

**Design note — snapshotting the discount:** `Booking.discount_applied_percent` stores the membership tier discount rate that actually applied at the moment of purchase, rather than the app always looking up the user's _current_ membership tier. This means if someone's membership lapses or changes later, their historical bookings and receipts don't silently change with it.

**Design note — `user` is nullable.** A walk-up customer paying by card at the venue doesn't need an account, in the same way buying a ticket at a real box office doesn't. If they want their membership discount, staff look their account up (e.g. by email) and link the booking to it; otherwise it proceeds as a guest sale with no discount. See 4.14 for the full in-venue flow.

### 4.3 `concessions`

- **Product** — `name`, `price`, `category` (drink / snack).
- **OrderItem** — `booking` (FK), `product` (FK), `quantity`. Food and drink pre-orders ride along with the ticket purchase through the same checkout and the same `Booking` record, rather than being a separate transaction.

### 4.4 `membership`

- **MembershipTier** — `name` (e.g. Friend, Premium Friend), `annual_fee_pence`, `priority_booking_hours` (how far ahead of general on-sale a member of this tier can book), `ticket_discount_percent`, `food_drink_discount_percent` (nullable — a higher-tier-only perk), `description`. Modelled on real theatre "Friends" schemes (e.g. Chelmsford Theatre's two-tier structure of priority booking plus escalating discounts) rather than the demographic self-select approach originally drafted here — see [4.18](#architecture) for the full reasoning and how priority booking actually works.
- **Voucher** — `code`, `initial_value_pence`, `remaining_value_pence`, `expires_at`, `source` (purchased / screening_cancelled), `is_active`. Not tied to a specific user, in the same way a physical gift card isn't — whoever has the code can redeem it. A voucher's balance is drawn down at checkout and can be spread across more than one booking until it reaches zero.

### 4.5 `accounts`

- **Profile** — `user` (1:1 with Django's built-in `User`), `membership_tier` (nullable FK to `MembershipTier`), `membership_expires_at` (nullable — see 4.18).

**Design note — `date_of_birth` and `membership_verified` are dropped.** Both existed in an earlier draft of this design to support demographic discount verification (e.g. confirming someone was actually a senior or a student), which is no longer needed now that discounted showings are priced per-screening via `TicketClass` rather than computed from who's booking. Neither field would have a purpose left, so rather than leave dead columns in the schema, they're removed — a paid membership's validity is simply whether `membership_expires_at` is in the future, a database check rather than a staff judgement call.

### 4.6 `venue`

- **EnquiryRequest** — `name`, `email`, `event_type`, `preferred_date`, `party_size`, `message`, `status`, `resulting_screening` (nullable FK to `Screening` — see [4.19](#architecture)). Handles private hire and event enquiries without needing a full booking/payment flow.
- Static content (About, Accessibility policy, Membership terms) — plain templates rather than models, unless there's a reason later to make them admin-editable.

### 4.7 Relationship overview

```text
User ──1:1── Profile ──FK── MembershipTier
  │
  └──FK── Booking ──FK── Screening ──FK── Film
              │              │              └──FK── TicketClass
              │              └──FK── Screen ──1:N── Seat
              ├──1:N── SeatBooking ──FK── Seat
              ├──1:N── OrderItem ──FK── Product
              └──FK (nullable)── Voucher

EnquiryRequest ──FK (nullable)── Screening
```

### 4.8 Core Flow: Seat Selection & Holds

A gap exists between a user selecting seats and completing payment — without handling this deliberately, a user could pick seats, spend time in checkout, and then be told at the payment step that someone else got there first. To avoid that, seat selection uses a short-lived **hold**, separate from a confirmed booking.

- **SeatHold** — `screening` (FK), `seat` (FK), `session_key`, `user` (nullable FK — see 4.16 for why), `expires_at`, `extension_count` (default 0). `unique_together = ('screening', 'seat')`.

`SeatHold` is deliberately a separate model from `SeatBooking` (4.2): a hold is provisional and expires if unused, whereas a `SeatBooking` means the seat has actually been paid for. Keeping them apart means an abandoned checkout can never permanently block a seat.

**Sequence:**

1. **Page load** — the seat grid is rendered server-side with each seat's live status (available / held / booked), so the user is never looking at stale information. Each seat's status is expressed as a single `data-seat-status` attribute, styled via the CSS Exception layer (see [section 3](#ux-strategy)) rather than a pile of state-specific classes.
2. **Selecting seats** — pure client-side toggling while browsing the grid; no server call yet.
3. **Proceeding to checkout** — a single request sends the chosen seat IDs. The server, in one transaction, clears any expired holds for that screening, checks the requested seats are still free against both live holds and confirmed bookings, and if clear, creates fresh `SeatHold` rows with a short TTL (e.g. 10 minutes).
4. **Conflict** — if a seat was taken in the gap between page load and this request, the server returns exactly which seat(s) failed. The page updates only those seats to "taken," deselects them, and shows an inline message — the user's other selections are preserved rather than the whole flow restarting.
5. **A failed payment attempt** (declined card, insufficient funds, wrong details) does **not** release the hold. The customer sees the specific reason and can try again — a different card, or corrected details — as many times as they like within the hold window. Each failed attempt extends `expires_at` by a short amount (e.g. 5 minutes) and increments `extension_count`, up to a hard cap on total hold time (e.g. 30 minutes from the first hold), so a genuine retry isn't punished but a hold can't be kept alive indefinitely.
6. **Explicit cancellation** — a "Cancel" button lets the customer release their hold immediately rather than waiting out the timer, freeing the seats for someone else sooner.
7. **Successful payment** — the hold converts into a permanent `Booking` and its `SeatBooking` rows (see 4.13 for exactly when this happens relative to Stripe's confirmation).
8. **True abandonment** (tab closed, no cancel, no retry) — nothing needs to actively release the seat; the hold simply expires once its TTL (as extended by any retries) runs out, and is swept up by the next hold-attempt's cleanup step (step 3).
9. **Hold expires mid-checkout** — payment confirmation re-validates the hold still exists before accepting the charge. If it's expired, the user is sent back to the seat map with a plain explanation rather than a confusing card decline for seats they no longer hold.
10. **Back/forward navigation** — the seat grid re-fetches live state on page show rather than trusting a cached view, so the browser's back button can never display an out-of-date "your seats" state.

### 4.9 `staff`

This app has no customer-facing models of its own. It owns the one genuinely new cross-cutting concern — accountability for staff actions — and otherwise only _reads_ data that already lives in the other apps, for reporting. Keeping it separate avoids scattering staff-only concerns across every domain app, and avoids duplicating booking/sales data into a second model just to report on it.

- **AuditLogEntry** — `actor` (FK to `User`), `action_type` (choices: `refund`, `screening_cancelled`), `related_booking` (nullable FK), `related_voucher` (nullable FK), `reason` (text, required), `created_at`.

**Design note — logging is automatic, not a separate step.** An `AuditLogEntry` is created by the same server-side action that performs the sensitive operation itself (applying a discount, issuing a refund, etc.) — not filled in by staff afterwards as an extra form. This means it can't be forgotten or skipped, and the "who and why" is guaranteed to exist for anything sensitive that happened.

**Permission tiers.** Two Django Groups: `FrontOfHouse` and `Manager`. `FrontOfHouse` handles day-to-day booking and enquiry tasks. `Manager` additionally processes refunds, cancels a screening, and views the sales dashboard.

**Business overview (Manager only).** Rather than a separate reporting model, this is a set of read-only views built on Django's aggregate queries over existing data — revenue by day/week/month, revenue and seat occupancy by screening, top-selling concessions, and total value of discounts/vouchers redeemed. Because it's computed live from `Booking`/`SeatBooking`/`OrderItem` rather than stored separately, the numbers can never drift out of sync with the underlying bookings.

**Access.** The `staff` app's views (and the staff-only views in other apps) sit under their own `/staff/` URL path with their own login page, distinct from the customer-facing site. No customer-facing template links to it. This keeps everything reachable within a single deployment — important for assessment — while still giving staff tooling a separate identity from the public site. See [4.12](#architecture) for how this would evolve for a real venue.

### 4.10 Business Rule: Discount & Voucher Order of Operations

With ticket-class pricing, membership discounts, and vouchers all potentially touching the same booking, the order they're applied in has to be fixed and documented — otherwise it's easy for the same logic to be implemented two different ways in two different places.

**Ticket-class pricing isn't part of this stack at all.** A screening's `base_price` already reflects its `TicketClass` (4.1) before any of the following runs — a Silver Screen showing is simply priced lower from the start, the same way a standard evening showing is priced higher. There's nothing to "apply"; it's just the starting number.

The order is:

1. Start from the sum of the base ticket price(s) (as already set by the screening's ticket class) and any concessions.
2. Apply the customer's membership tier discount, if any — snapshotted onto `discount_applied_percent` (4.2).
3. Deduct whatever's left from the customer's voucher balance, if a voucher code was entered, up to the voucher's remaining balance.
4. Charge the remainder to Stripe. If the voucher fully covers the total, no Stripe charge is needed, but the `Booking` is still marked paid.

A voucher can never take a booking below £0 — any unused voucher balance stays on the voucher for a future booking, it isn't paid out as cash or credit.

_(An earlier version of this design also included a staff discretionary discount and a promo-code layer, each with its own stacking rule. Those have been moved to [Marketing Development Thoughts](#marketing-development) as future business ideas rather than part of the initial build — see that section for the reasoning that was worked out for them.)_

### 4.11 Business Rule: Screening Cancellation

If a screening has to be cancelled (e.g. a technical fault), a manager cancelling it triggers, for every existing `Booking` against that screening: the booking is marked `cancelled`, its seats are released, and the customer is automatically issued a `Voucher` (`source='screening_cancelled'`) for the full amount they paid, rather than requiring an individual refund to be processed by hand for each customer. Each of these is logged as an `AuditLogEntry` with the manager as actor and "screening cancelled" as the reason, so there's a single, reviewable batch of entries rather than the cancellation being invisible.

### 4.12 Note: Staff System Separation Beyond This Submission

**This section describes a possible future direction and is explicitly out of scope for the submitted project.** For assessment purposes, the `staff` app runs in the same Django deployment as the public site, reachable at its own `/staff/` URL with its own login page and no link to it anywhere in the customer-facing templates. That's sufficient to demonstrate the intended separation of concerns and keeps the whole project reachable and testable through a single deployment, which matters for assessment.

If this project were ever taken further — for a real, operating venue — the same logical separation (customer-facing vs staff-only) would be worth turning into an actual infrastructure boundary, not just a routing one:

- **Network isolation:** the staff area restricted to the venue's own network or a VPN, rather than being reachable from the open internet at all — the public booking site stays internet-facing, the staff tooling doesn't need to be.
- **Separate staff authentication:** rather than staff being Django `User` rows created ad hoc by a superuser, a proper provisioning and offboarding process (so a leaving staff member's access is reliably revoked), and additional protection — e.g. two-factor authentication — specifically for the `Manager` tier, given it can process refunds and issue vouchers.
- **Device-level controls:** the venue's tablets/terminals running in a locked-down "kiosk mode" browser profile pointed only at the staff URL, with device-level passcodes and remote-wipe capability, since they're physical devices sitting in a publicly accessible venue.
- **Shift-appropriate session handling:** a short auto-logout tuned to real usage patterns (so one staff member's session isn't still active for the next person on a shared tablet), which matters directly for the audit log's attribution to stay meaningful.
- **Reporting load separation:** if real transaction volume made the sales dashboard's queries noticeably heavy, running those reports against a read replica of the database rather than the primary one, so staff pulling up a sales report can never slow down a customer mid-checkout.
- **Dual authorisation for large refunds:** a common real-world control where a refund above a set threshold needs a second manager's sign-off — the audit log already captures who did what, so this would extend naturally on top of it rather than requiring new infrastructure.

None of the above is needed to meet this project's assessment criteria, and building it now would add infrastructure complexity with no corresponding credit — but it's recorded here because the reasoning is worth keeping if this ever becomes more than a coursework submission.

### 4.13 Business Rule: Payment Lifecycle (Online)

The core principle: **a Stripe webhook, not the customer's browser, is the source of truth for whether payment succeeded.** If the customer's connection drops, or they close the tab mid-payment, the app can't rely on them ever returning to a "success" page — the booking only becomes real when Stripe independently tells the server it's been paid.

**Sequence:**

1. Checkout is initiated (a `SeatHold` already exists — see 4.8). The server calculates the final total using the discount/voucher order from 4.10, and creates a Stripe PaymentIntent for that amount.
2. **If the total is £0** (a voucher fully covers it), there's no Stripe interaction at all — the booking is marked paid immediately, server-side.
3. Otherwise, the customer completes payment through Stripe's client-side card element; card details never touch this application's own server.
4. The server's only immediate response to the browser is "payment submitted," not "payment succeeded."
5. Stripe sends a `payment_intent.succeeded` webhook. **This** is what finalises everything: the seat hold converts to confirmed `SeatBooking` rows, the voucher balance is decremented (not before — see below), and a confirmation is sent.
6. A genuinely declined/failed attempt (`payment_intent.payment_failed`) does not release the seat hold — see the retry behaviour in 4.8, step 5.
7. **Uncertain outcomes** (e.g. the connection dropped after submission but before the browser heard back) are resolved by checking the PaymentIntent's actual status with Stripe before allowing a new attempt — never by assuming failure just because the client didn't get a response. This avoids ever double-charging a card that actually went through.

Two implementation details worth being explicit about, since they're easy to get subtly wrong:

- **Webhook signature verification.** Stripe signs every webhook payload; the endpoint must verify that signature before trusting it, or anyone could POST a fake "payment succeeded" event.
- **Idempotency.** Stripe can and does redeliver the same webhook event more than once. Finalisation logic checks "is this booking already marked paid?" before acting, so a redelivered webhook can't double-decrement a voucher.

**Consequence for 4.10:** a voucher's balance is only decremented once payment is _confirmed_ by the webhook, not at checkout time — otherwise an abandoned or failed payment would have permanently spent someone's voucher for nothing. It's the same "provisional, not committed" pattern as the seat hold, applied a second time.

**Refunds** (manager-initiated, from 4.9) call Stripe's refund API directly and get an immediate response, unlike the original payment — this doesn't need to wait on a webhook.

**Known limitation, deliberately not solved:** a voucher's balance isn't "held" the way a seat is. If the same code were entered in two simultaneous checkouts, there's a narrow window where both could succeed against the same balance before either payment confirms. Given a voucher requires manually typing a code, this is a low-probability, low-severity edge case — solving it properly would mean a second holding mechanism mirroring `SeatHold`, which is disproportionate complexity for the risk involved. This is recorded as a known issue (see [Testing](#testing)) rather than engineered around.

### 4.14 In-Venue Bookings (Staff-Assisted, Card Only)

A walk-up customer at the venue should be able to book largely the same way an online customer does — same seat map, same concessions, same discounts — with a member of staff completing it on their behalf. Matching the real Regal Cinema's own policy, this project is **cashless — card payments only**, in venue as well as online.

Channel (online vs in-venue) is a separate decision from payment method — a customer at the venue pays by card without that meaning "online," and specifically without needing to give an email address or create an account. This matters for privacy-minded customers who'd rather not hand over an email just to pay at the counter.

This deliberately reuses the existing booking flow rather than being a separate code path: the same `SeatHold` → `SeatBooking` mechanics and the same discount stacking order (4.10) apply unchanged. The only real differences are in who initiates it and how payment is recorded:

- `Booking.channel = 'in_venue'`, `Booking.payment_method = 'card_in_person'`, `Booking.created_by` set to the staff member completing the sale.
- `card_in_person` means the customer paid by card on the venue's own separate card machine, not through Stripe. That card terminal sits entirely outside this application, the same as a physical till would; staff simply mark the booking as paid once payment is confirmed. No Stripe PaymentIntent is created — `stripe_payment_intent_id` stays null.
- `Booking.user` is left blank by default for a walk-up sale — **no account or email is required**, mirroring a real box office and respecting a customer who'd rather not provide one. If the customer wants their membership discount, staff look their account up (e.g. by email) and attach it to the booking; otherwise it proceeds as a fully anonymous guest sale.
- The customer doesn't need an email confirmation for a same-day in-person purchase, though staff can send one if the customer chooses to provide an address — the till/booking screen itself serves as the receipt.

**Available to:** Front of House, as a routine day-to-day action — this is the standard box-office sale, not a discretionary override.

### 4.15 TMDb Integration Mechanics

Building on the `Film` model (4.1) and the hybrid approach decided earlier — real film data from TMDb, bespoke scheduling of our own — this section pins down exactly how and when TMDb is actually called, and what happens if it isn't available.

**Where the live API is called, and where it deliberately isn't.** The only place this application ever calls TMDb live is the staff-only "add a film" flow. The public, customer-facing site never calls TMDb directly — customers only ever see the cached `Film` rows already saved locally. This matters for reliability: if TMDb is slow or briefly down, it only affects a staff member trying to add a brand-new film that day. It has zero effect on customers browsing listings or booking a seat, since that data comes entirely from the local database, not a live external call.

**Adding a film (staff flow):**

1. Staff search by title, hitting TMDb's search endpoint. Because titles aren't unique (sequels, remakes, foreign-language titles), results are shown as a short list — poster thumbnail, title, release year — so staff pick the correct match rather than the system guessing.
2. On selecting a result, the app fetches the film's full detail (synopsis, runtime, genres), its available trailer videos, and its UK age certification (TMDb's release-dates data, filtered to the GB entry).
3. **The API's results are pre-filled, not auto-committed.** Staff see the fetched synopsis, poster, a suggested trailer, and a suggested age rating on a review screen before anything is saved — the age rating specifically, since TMDb's certification coverage is inconsistent and getting this wrong has real consequences (age-restricted content shown with the wrong certificate). A human confirms before it goes live; the API just does the typing.
4. Once confirmed, it's saved as a local `Film` row and isn't queried from TMDb again unless staff explicitly choose to refresh it.

**Films with no TMDb entry.** Not everything a venue screens is a commercially released film with a TMDb page — event cinema (e.g. a National Theatre Live broadcast), a Q&A screening, or a private hire's own content wouldn't have one. Staff can add a `Film` manually instead of searching TMDb, leaving `tmdb_id` null and filling in the same fields by hand. `Screening` doesn't need to know or care which path a given `Film` came from.

**Images.** Rather than downloading and re-hosting poster images, `Film.poster_path` stores TMDb's own relative image path, and the actual display URL is built by prefixing TMDb's image CDN address at render time. TMDb's images are explicitly served for this kind of use, so there's no reason to duplicate storage of something TMDb already hosts reliably.

**Trailers.** A film can have several videos on TMDb (teasers, clips, trailers in different languages). The system suggests the most likely candidate (an official YouTube trailer, where that's identifiable) but — consistent with the age-rating decision above — staff confirm or choose a different one from the list rather than it being silently auto-selected. If no suitable video exists, the trailer embed is simply omitted rather than showing a broken player.

**Failure handling.** If TMDb is unreachable or returns an error during the staff add-film flow, the failure surfaces as a plain, specific message ("Couldn't reach the film database — try again in a moment") with a retry option, rather than a generic crash. This is the one place in the project a genuine third-party API failure needs handling gracefully, and it's scoped narrowly enough — staff-only, not time-critical — that a clear error and a retry button is a proportionate response, rather than needing a queued background retry system.

**Rate limits and the API key.** TMDb's rate limits are generous, and since calls only happen when staff actively add a film — not on every customer page view — this is never a practical concern here. The TMDb API key is a server-side environment variable, the same as the Stripe keys: the browser never sees it, since every TMDb call happens from the server during the staff flow, never from the customer's browser.

**Optional refresh.** Because film data is cached rather than fetched live, a poster or synopsis TMDb later corrects won't automatically update locally. A "Refresh from TMDb" action on a `Film`'s staff edit page re-runs steps 2–3 above and overwrites the local record (again with staff review before saving), which covers this without needing a background sync job.

### 4.16 Authentication & Registration Flow

**Signup is deliberately minimal:** email and password only. `Profile` (4.5) is created automatically via a signal the moment a `User` is created, rather than being a second form the customer has to fill in — a membership tier is only added afterwards, on the profile page, if and when the customer chooses to become a Friend (see 4.18).

**Simplification, stated explicitly:** rather than building a fully custom Django user model with email as the username field (the more "correct" long-term approach), this project keeps Django's default `User` model and derives a username automatically from the email address behind the scenes. A custom user model has to be decided before the very first migration ever runs — a real risk for a project at this stage — so the registration _form_ only ever shows email and password, while the underlying model stays the simpler, lower-risk default.

**Username derivation and collisions.** The username is built from the email's local part (the text before `@`), sanitised to characters Django's username field actually permits. Since two different email addresses can share the same local part (`j.smith@gmail.com` and `j.smith@yahoo.com` would both derive to `j.smith`), the derivation checks for an existing match and appends an incrementing number until it finds one that's free (`j.smith`, then `j.smith2`, `j.smith3`, and so on). This is purely internal — the customer logs in with their email, never sees or needs to know their generated username, so a collision here is invisible plumbing, not a real UX problem.

**The uniqueness rule that actually matters is on email, not username.** Django's default `User` model does _not_ enforce email addresses to be unique out of the box — easy to assume it does, since it feels like it should. Because email is the real login identifier here, that constraint has to be added deliberately (a unique constraint on the field, or an equivalent check in the registration view); without it, nothing would stop the same email being used to create two separate accounts.

**Login/registration pages are restricted to anonymous users only** (an already-logged-in user is redirected away from them rather than being shown a login form) — this is a pass-level requirement, not just a nice-to-have.

**Email verification is sent, but non-blocking.** A verification email goes out on registration, but the account is usable immediately — someone registering specifically to book a seat in the next five minutes shouldn't be stuck waiting on an email that might take a few minutes to arrive. Verification is a gentle reminder (e.g. a banner), not a gate on using the site. Password reset reuses the same signed-token approach Django already provides for this, rather than needing a second, separate token-storage model for verification.

**Registration is required to complete an online checkout, but not to browse or select seats, and not for an in-venue card sale.** This is deliberately two different rules for two different real-world contexts, not an inconsistency: browsing and picking seats works anonymously, but finishing an _online_ purchase requires an account — which is exactly the "clear reason to register" the assessment criteria ask for, since booking history and the membership discount both depend on having one. In-venue sales stay guest-friendly, as already decided in 4.14, because a walk-up customer at a real box office was never going to be asked to create an account first.

**Design note — seat holds surviving a mid-checkout login.** Django deliberately rotates a user's session ID at the moment they log in, as a defence against session-fixation attacks. Since `SeatHold` (4.8) is tied to `session_key`, a customer who selects seats anonymously and then registers or logs in _mid-checkout_ — exactly the moment "continue to checkout" prompts them to, per the rule above — would otherwise silently lose their hold the instant login succeeds. To prevent that: `SeatHold` carries a nullable `user` FK alongside `session_key`, and on a successful login, any holds under the current session are reassigned to that user. A small addition, but it closes a gap that would otherwise cause a confusing, hard-to-reproduce failure at exactly the point a customer is trying to convert.

**Staff logins are entirely separate** from all of the above — a different URL, a different login template (4.9/4.12), and unrelated to whether a given staff member also happens to hold their own personal customer account.

### 4.17 Accessibility Implementation

The captioned/audio-described flags on `Screening` (4.1) are about the film experience itself. This section is about the _website_ — making sure the interface is genuinely usable by someone using a keyboard alone, a screen reader, or with low vision — which is a separate concern the project hasn't pinned down yet.

**Target:** WCAG 2.1 AA — the practical, widely used baseline, and a concrete way to make the "meets accessibility guidelines" pass criterion (1.2) checkable rather than aspirational.

**Structure and semantics.** One `<h1>` per page, a logical heading order, and semantic landmarks (`<nav>`, `<main>`, `<footer>`) so a screen reader user can jump straight to a section rather than reading the whole page linearly. Anything clickable is a real `<button>` or `<a>`, never a `<div>` with a click handler bolted on — that's what gives keyboard and screen-reader support "for free" rather than needing to be rebuilt by hand.

**Colour and contrast.** The dark palette chosen in [section 3 (Surface)](#ux-strategy) gets checked against WCAG's actual contrast ratios before being finalised, not just judged by eye — text needs a 4.5:1 ratio against its background, and the gold accent specifically needs checking wherever it's used for anything beyond large or purely decorative text, since a colour chosen for mood ("premium," "cinematic") isn't automatically legible. **Nothing is conveyed by colour alone**: the seat map's states (available / selected / held by someone else / booked) each get a second signal beyond colour — an icon or pattern, and a text label available to screen readers — so the map works for a colourblind customer, not only a sighted one.

**The seat map specifically**, since it's the most complex interactive component in the project:

- Every seat is a real, focusable `<button>` — reachable by Tab, activatable with Enter or Space — not a hover-only or click-only interaction.
- Each seat's accessible name states what a screen reader user actually needs ("Row C, seat 4, sofa, available"), not just a grid coordinate.
- When a seat-hold conflict happens (4.8) and the page updates inline rather than reloading, the change is announced through an ARIA live region. A sighted user sees the seat turn red; a screen reader user needs to be _told_ it just became unavailable, or the whole inline-update design from 4.8 quietly fails for them.

**Forms** (registration, checkout, enquiries, staff tools): every input has a real, associated `<label>`; validation errors are stated in text, not colour alone, and tied to their field so a screen reader announces _which_ field the error belongs to, not just that something's wrong.

**Focus and motion.** A visible, high-contrast focus style is defined explicitly for the dark theme, rather than relying on the browser default (which can be hard to see against a very dark background) or — a common and avoidable failure — removed outright for looking "cleaner." Transitions and layout shifts respect `prefers-reduced-motion`, and — as already decided in the UX strategy — trailers never autoplay, which is as much an accessibility decision as a stylistic one.

**A design choice from earlier that helps here for free.** The fluid, no-fixed-breakpoint layout approach ([Every Layout](#ux-strategy)) chosen for its own reasons also happens to make the site more resilient to text zoom and browser large-text settings than a pixel-fixed layout would be — worth naming explicitly as a place two separate design decisions reinforce each other rather than being unrelated.

**Verification.** Rather than assuming accessible markup is accessible in practice, this gets checked concretely: an automated pass (e.g. Lighthouse or axe) catches the mechanical issues — contrast, missing labels, landmark structure — and a manual keyboard-only pass through the booking flow, the highest-risk journey in the project, catches what automated tools can't, such as whether the live region actually announces a lost seat sensibly. See [Testing](#testing).

### 4.18 Ticket Classes, Membership Tiers & Priority Booking

This section replaces an earlier draft of the membership design, after checking it against how the real Regal Cinema, Evesham actually structures things. Two changes fall out of that: discounted showings are a property of the _screening_, not the _customer_, and "membership" is a paid Friends/Patron scheme rather than a free, self-selected discount category.

**Ticket Classes.** The real venue's own site lists named categories — Silver Screen, Summer Saver, Family Super Saver, Subtitled, Live Event, and others — and a customer review confirms what one of these actually is: a specifically discounted showing (Silver Screen, priced around £8 against a higher standard price), not a discount computed from who's booking it. This project models that directly: `TicketClass` (4.1) is a label with an optional default price, assigned to a `Screening` when it's created. Staff pick the class, the system suggests a price, staff can override it — no age or identity check involved, because there isn't meant to be one. Anyone can book a Silver Screen showing; it's simply priced for that audience.

**Membership as a paid Friends scheme.** `MembershipTier` (4.4) replaces the free, self-selected OAP/Family/Student category from the earlier draft with a paid, tiered scheme in the pattern real UK theatres commonly use — e.g. Chelmsford Theatre's structure of an entry tier with priority booking and a higher tier adding further discounts. A customer purchases a tier via a one-off Stripe charge (the same `card_online` payment pattern as a booking, not a new payment mechanism), which sets `Profile.membership_tier` and `membership_expires_at` to one year from purchase.

**No auto-renewal.** Membership doesn't automatically renew or re-charge a saved card when it lapses — that would mean building recurring billing (a materially bigger feature, involving Stripe subscriptions and their own webhook events), which is disproportionate for this project's scope. Instead, a lapsed member simply sees a "renew your membership" prompt and repeats the same one-off purchase. Worth recording as a deliberate scope boundary, in the same spirit as 4.12's other "beyond this submission" notes, rather than an oversight.

**Priority booking.** `Screening.public_onsale_at` (4.1) is when a screening opens to the general public. Before that point, only a member whose tier's `priority_booking_hours` covers the gap can book it — i.e. `now >= public_onsale_at − tier.priority_booking_hours`. If `public_onsale_at` is left blank entirely, the screening is members-only permanently rather than on a countdown — this is the same mechanism used for something like the real venue's members' Q&A events, just with no eventual public on-sale date rather than a future one. One field, two related purposes, rather than two separate booleans that could contradict each other.

**Ticket and food/drink discounts** from a member's tier apply through the discount stacking order already defined in 4.10 — nothing new needed there beyond what's already specified.

**What this removes from the earlier design.** The old `MembershipType`'s self-declared category and the staff "verify a member's ID" action (previously in 4.9) are no longer needed: a paid membership's validity is a straightforward `membership_expires_at` check, not a subjective judgement call staff have to make in person. This is a genuine simplification, not just a change — one less thing for Front of House to manage, and one less field (`membership_verified`) sitting in the schema without a clear purpose.

### 4.19 Private Hire & Screening Visibility

`EnquiryRequest` (4.6) handles the initial private hire or event conversation, but nothing so far connects it to an actual bookable — or _unbookable_ — `Screening`. Two things needed pinning down: how an agreed hire becomes a real screening, and whether the public should ever see or book it.

**No automatic conversion.** Once terms are agreed with a hirer, staff manually create a `Screening` the same way they'd create any other one — picking a film (or, for a non-film event, a manually-added `Film` entry per 4.15), a screen, and a date/time — and tick `is_private`. Building an automated enquiry-to-screening pipeline would mean also handling quoting and invoicing, which is a genuinely different, larger feature area than this project's booking system; a manual step here is a deliberate scope boundary, not an oversight. For traceability, `EnquiryRequest.resulting_screening` links back to whichever `Screening` came out of that conversation, so staff can see the connection later without needing to remember it.

**What `is_private = True` actually changes:**

- The screening doesn't appear in public "what's on" listings.
- Anonymous/customer online booking is blocked for it entirely — there's no public seat map to book against.
- It still participates fully in the existing screen/time overlap check (4.1's "system prevents two screenings overlapping on the same screen") — a private hire still physically occupies the screen for that slot, so it has to block public screenings from clashing with it exactly like any other screening would.
- If the hirer wants named individual seats tracked (rather than a single flat-fee block booking), staff create those bookings through the existing in-venue flow (4.14) — no new booking mechanism needed, since a private hire's seats are conceptually no different from a staff-assisted walk-up sale, just arranged in advance.

**Payment for the hire itself stays outside this system.** The actual private-hire fee is negotiated and settled through the `EnquiryRequest` conversation (an invoice, a bank transfer, whatever the venue's existing process is) rather than through Stripe — building a quoting/invoicing flow is out of scope here, and real private hire agreements are usually bespoke enough (catering add-ons, differing durations, negotiated rates) that forcing them through a fixed per-seat checkout wouldn't actually fit. `is_private` exists to reserve the slot and control visibility, not to process the hire's payment.

## <p align="right">(<a href="#top">Back to top</a>)</p>

## 5. <a name="features"></a> Core Features

Each app's user-facing and staff-facing features, building directly on the [data model](#architecture) and [user stories](#purpose) above.

### Permission model

Two kinds of user: registered customers, and staff. Staff status (`is_staff`) is granted by a superuser — there's no public "become staff" path. Staff are further split into two Django Groups: **Front of House** (bounded, day-to-day discretion) and **Manager** (everything Front of House can do, plus financial and administrative actions). See [4.9](#architecture) for the reasoning and the full permission breakdown.

Deliberately, staff do not use Django's built-in `/admin` for day-to-day work. `/admin` exposes every field on every model, which is more power — and more room for accidental mistakes — than day-to-day duties call for, and it isn't designed to match the rest of the site or guide someone unfamiliar with Django through their actual tasks. Instead, staff get a small set of custom views, built with the same templates and design system as the public site, that expose exactly the actions listed below, gated by group-based permission checks rather than open `/admin` access. `/admin` still exists behind the scenes for genuine one-off data fixes, but it isn't part of the day-to-day handover.

Anything financial (a refund, a screening cancellation) is automatically recorded in the audit log with who did it and why — see [4.9](#architecture).

### 5.1 `screenings`

**Customer-facing**

- Browse current/upcoming screenings, filterable by date, showing each one's ticket class (e.g. Silver Screen, Family Super Saver) and price
- Film detail page (synopsis, trailer, age rating, captioned/audio-described indicator)
- Seat selection on an interactive seating plan, by tier

**Staff-facing**

- _(Front of House)_ View a screening's current seat occupancy at a glance
- _(Manager)_ Search TMDb and add a film to the local catalogue, reviewing and confirming the fetched details (including age rating) before saving — see [4.15](#architecture)
- _(Manager)_ Add a film manually for anything without a TMDb entry (event cinema, private hire content), or refresh an existing film's cached details from TMDb
- _(Manager)_ Create, edit, or cancel a screening (film, screen, date/time, price, ticket class, priority booking window, private/public visibility) — the system prevents two screenings overlapping on the same screen; cancelling one triggers the [screening cancellation flow](#architecture)
- _(Manager)_ Mark a screening private for a confirmed private hire or exclusive event — hides it from public listings and blocks public online booking (see [4.19](#architecture))
- _(Manager)_ Manage the list of ticket classes and their default prices (see [4.18](#architecture))

### 5.2 `bookings`

**Customer-facing**

- Seat selection with a short-lived hold (see [Core Flow](#architecture) above)
- Checkout: seats + concessions + voucher/discount → Stripe payment
- Order confirmation and booking history on their profile

**Staff-facing**

- _(Front of House)_ Create a booking on behalf of a walk-up customer, by card, without requiring an email or account — same seat map, concessions, and discount rules as the online flow (see [4.14](#architecture))
- _(Front of House)_ View bookings for a given screening, for door/headcount purposes
- _(Front of House)_ View a single booking's full detail (seats, concessions ordered, payment status) — useful for resolving a customer query at the door or by phone
- _(Manager)_ Process a full refund/cancellation — releases the booking's seats and is logged

### 5.3 `concessions`

**Customer-facing**

- Add drinks or snacks to a booking during checkout

**Staff-facing**

- _(Manager)_ Manage the product catalogue (add, edit, or retire items and prices)
- _(Front of House)_ A simple prep list per screening — what's been ordered and needs to be ready

### 5.4 `membership`

**Customer-facing**

- Purchase or renew a Friend membership tier, with the discount and priority booking window applying immediately (see [4.18](#architecture))
- Book a screening during its priority window before general on-sale, if their tier covers it
- Enter a gift voucher code at checkout

**Staff-facing**

- _(Front of House)_ View a member's tier and expiry status if a query comes up

### 5.5 `venue`

**Customer-facing**

- Static pages: About, Accessibility policy, Membership terms
- Private hire / event enquiry form

**Staff-facing**

- _(Front of House)_ View and update the status of enquiries (new / contacted / booked / declined), and see which `Screening` an enquiry turned into once one exists (see [4.19](#architecture))

### 5.6 `staff`

**Staff-facing**

- _(Manager)_ Sales/business overview: revenue by day/week/month, revenue and occupancy by screening, top-selling concessions, total vouchers redeemed
- _(Manager)_ Audit log: a searchable/filterable list of refund and screening-cancellation actions, with who did it and why
- _(Front of House and Manager)_ Nothing customer-facing — this app exists purely to support the other apps

## <p align="right">(<a href="#top">Back to top</a>)</p>

## 6. <a name="deployment"></a> Deployment Guide

This project needs a hosting platform that can run a Python/Django application with a PostgreSQL database — a static host such as GitHub Pages isn't sufficient, since the app relies on server-side logic, a live database, and Stripe integration. Suitable platforms include **Render**, **Railway**, or **Heroku**.

_(This section will be filled in with the exact steps once the project is actually deployed. Planned approach below.)_

### Planned Deployment Steps

1. Push the project to GitHub, including a `requirements.txt` and a `Procfile`.
2. Create a new web service on the chosen platform, connected to the GitHub repository.
3. Add a managed PostgreSQL database and connect it via an environment variable (e.g. `DATABASE_URL`).
4. Set environment variables for `SECRET_KEY`, the Stripe API keys, and the TMDb API key — none of these are committed to the repository.
5. Set `DEBUG = False` for the production environment.
6. Deploy, then run database migrations against the production database.
7. Verify the live site matches the development version, and that static files (CSS, images) are served correctly.

### Local Deployment (Cloning)

_(To be completed with the actual local setup steps once the project is underway.)_

### Quick Local Spin-Up Alternatives

## <p align="right">(<a href="#top">Back to top</a>)</p>

## 7. <a name="credits"></a> Credits & Acknowledgements

### AI Pair Programming & Academic Integrity

Artificial Intelligence (LLMs) was utilised strictly as a "Pair Programmer" and strict linter throughout the development lifecycle to accelerate cross-browser debugging, reflow profiling, and formatting, ensuring absolute human ownership and comprehension of the overarching engine code.

### Technologies Used

### Repository Structural Layout

## <p align="right">(<a href="#top">Back to top</a>)</p>

## 8. <a name="dev-log"></a> Development Log & Engineering Phases

### Phase 1:

<details>
<summary><b>Expand Engineering Case Study: Phase 1</b></summary>

####

</details>

### Phase 2:

<details>
<summary><b>Expand Engineering Case Study: Phase 2</b></summary>

####

####

</details>

### Phase 3:

<details>
<summary><b>Expand Engineering Case Study: Phase 3</b></summary>

####

####

</details>

###

<details>
<summary><b>Expand Engineering Case Study: Phase 4</b></summary>

####

####

</details>

###

<details>
<summary><b>Expand Engineering Case Study: Phase 5</b></summary>

####

####

###

</details>

###

###

<details>
<summary><b>Expand Engineering Case Study: Phase 7</b></summary>

####

####

####

####

</details>

###

## <p align="right">(<a href="#top">Back to top</a>)</p>

## 9. <a name="testing"></a> Testing & Quality Assurance Portfolio

This section outlines the holistic verification suite executed to guarantee the engineering integrity, mathematical precision, and cross-platform accessibility of…

### 1. Manual Testing Matrix (Boundary Explorations)

### 2. User Story Testing (Behavior-Driven Verification)

Verification of core target audience features mapped back to the primary user requirements.

### 3. Validator Testing

### 4. Lighthouse Testing

### 5. Browser Compatibility

Cross-origin audio context rendering pipelines were explicitly verified across major rendering engines:

### 6. Responsiveness Testing

### 7. Automated End-to-End Testing

### 8. Bugs Fixed (Sprint Log)

### 9. Known Issues

<p align="right">(<a href="#top">Back to top</a>)</p>

## 10. <a name="marketing-development"></a> Marketing Development Thoughts (Future Business Ideas)

**Everything in this section is explicitly out of scope for the initial build.** The project's core is now modelled as closely as possible on the real Regal Cinema, Evesham — ticket classes, paid Friend membership tiers, gift cards, cashless payments — rather than on features invented without a real-world equivalent to check them against. The ideas below were worked out in earlier design sessions and are preserved here in full, not because they're being built now, but because the reasoning behind them took real effort and could become a genuine business development pitch later — extending what the real venue currently offers, once the core platform exists and (potentially) once there's a real conversation with the venue about it.

### 10.1 Loyalty Points Scheme

A free, automatic points scheme, separate from the paid Friend tiers — anyone with an account earns points per booking, redeemable toward a free ticket once a threshold is reached.

- **LoyaltyTransaction** — `user` (FK), `points_change`, `reason`, `related_booking` (nullable FK), `created_at`. A ledger of individual earn/spend events rather than a single mutable counter on the user's profile — this gives an auditable history and avoids two simultaneous transactions corrupting a shared counter. A user's current balance is the sum of their transactions.

**Design logic — reusing the voucher system.** Rather than inventing a second redemption mechanism, when a member's points balance crosses the reward threshold, the system would issue them a `Voucher` (valued at one standard ticket, `source='loyalty_reward'`), which then goes through the exact same checkout logic as a purchased gift card. One mechanism, two ways of earning it — the same principle used elsewhere in this project (e.g. screening-cancellation refunds also reusing `Voucher`).

**Proposed rate (illustrative, not fact-checked against anything real).** Unlike the ticket classes and membership tiers, there's no evidence the real Regal Cinema runs a loyalty scheme at all — this idea has no confirmed real-world counterpart to model against, so any numbers here are a starting proposal rather than a researched fact. A simple, easily-explained rate: **1 point per £1 spent** (tickets and concessions both), with **100 points** earning a free standard ticket — roughly equivalent to a traditional "buy nine, get the tenth free" loyalty card, a pattern most customers already recognise instinctively. Both the rate and the threshold would be stored as single configurable values (the same "keep configuration in one place" principle used elsewhere in this project) rather than hard-coded, so they could be tuned once real spending data existed to judge whether that's actually sustainable for the venue's margins — a genuine business decision that shouldn't be guessed at permanently, only enough to make the idea concrete rather than hand-wavy.

### 10.2 Newsletter & Promotional Emails

- **NewsletterSubscriber** — `email` (unique), `user` (nullable FK — linked automatically if the email matches a registered account), `opt_in_deals`, `opt_in_digest` (both boolean, default `False`), `subscribed_at`, `is_active`. Deliberately not folded into `Profile`: anyone could subscribe from the site footer without an account.
- **NewsletterCampaign** — `subject`, `body`, `campaign_type` (`one_off_deal` / `monthly_digest`), `status` (`draft` / `sent`), `created_by` (FK staff), `sent_at`.
- **PromoCode** — `code`, `discount_percent`, `valid_from`, `valid_until`, `max_total_redemptions` (nullable — unlimited if blank), `times_redeemed`, `is_active`. A shared, rule-based marketing code, deliberately modelled separately from `Voucher`: `Voucher` is a personal balance (a gift card), spent down by one holder over time, while a promo code is redeemed by potentially hundreds of subscribers, each once, within a date window — forcing that into `Voucher`'s balance semantics would mean the first handful of customers could drain a "balance" meant to serve everyone.

**Consent, done properly.** Two separate opt-in checkboxes at subscribe time — deals and the monthly digest — both unticked by default. Having an account would never imply consent to marketing email; the two would be deliberately kept apart, in line with UK PECR rules on marketing communications.

**Two campaign types, with "Book Now" CTAs (the ODEON-style prompt that motivated this in the first place):**

- **Monthly digest** — auto-drafted rather than written from scratch: the system would pull newly added films and upcoming screenings since the last digest (reusing data that already exists in `screenings`, not duplicating it) and compose a draft with a "Book Now" button under each item, linking straight to that film or screening's page. As with the TMDb integration (4.15), the principle would be **the system drafts, a human confirms before it sends** — never auto-sent.
- **One-off deal** — fully staff-authored, since "£5 tickets this weekend" isn't something a system could sensibly invent. Optionally linked to a `PromoCode`, with the code pre-filled at checkout via a URL parameter on the "Book Now" button.

**The membership upsell.** Subscription confirmation and every digest email would include a short block — "Members get priority booking and ticket discounts — create an account" — but only for subscribers without a linked account. An existing member obviously doesn't need selling on joining.

**Unsubscribe** would reuse the same signed-token pattern as email verification and password reset (4.16) — one mechanism, several uses, rather than a separate implementation.

**Beyond even this.** At real scale, bulk marketing email and transactional email (booking confirmations, password resets) are usually best sent through separate infrastructure, since a spam-flagged newsletter can drag down deliverability for the transactional email that actually matters. Worth knowing, not worth solving at this stage.

### 10.3 Staff Discretionary "Goodwill" Discounts

The original motivating scenario: a disgruntled patron, or someone whose membership hasn't quite synced — front-of-house staff having the flexibility to make it right on the spot.

- `Booking.staff_discount_pence` (nullable) — a flat discretionary discount, applied on top of whatever else the booking already qualifies for.
- A configurable discount cap for the `FrontOfHouse` tier (stored as a single changeable value, not hard-coded), with `Manager` able to exceed it.
- Every use logged automatically to `AuditLogEntry` (`action_type='manual_discount'`) with a required reason — accountability without adding friction to using the discretion in the first place.
- The same pattern extended to manually issuing a `Voucher` as a goodwill gesture (`source='manual_goodwill'`) — reusing the existing voucher redemption logic rather than inventing a second one.

**Why this moved out rather than staying core:** there's no evidence the real Regal Cinema actually operates this way — their site shows fixed ticket classes and a structured membership scheme, not visible discretionary pricing. Keeping the initial build close to what's verifiably real took priority over a plausible-sounding feature with no confirmed real-world counterpart. The reasoning is sound and the mechanism (bounded discretion, mandatory logging) would be a legitimate real-world addition if a venue ever wanted it — it just isn't part of what's being built now.
