# 4. System architecture and data model

I've split the project into seven Django apps, each covering one area of the domain. That keeps each app's models and logic focused on one job, and means some of them (`concessions`, `membership`) could be reused on another project with little change.

Within each app, logic goes in one place per kind. Models hold the data rules and validation that must always be true, such as the no-overlap check on a screening or the unique seat constraint. A `services.py` module holds business logic that touches more than one model or app, such as creating holds, pricing a booking in the order from 4.10, or finalising a booking from a Stripe webhook. Views handle the request, call a service and choose a response, and templates only present what they're given. That makes a rule like the discount order something I can test directly, without going through a page.

| App           | Responsibility                                                                                                     |
| :------------ | :----------------------------------------------------------------------------------------------------------------- |
| `accounts`    | The email-login user model, and profile data: membership tier and expiry                                           |
| `screenings`  | The venue's catalogue: films, screens, seats, ticket classes and types, and scheduled screenings with their prices |
| `bookings`    | The transactional core: bookings, the seats attached to them, and seat holds                                       |
| `concessions` | Bar and snack products, and the items attached to a booking                                                        |
| `membership`  | Membership tiers and gift vouchers                                                                                 |
| `venue`       | Static site content, private hire enquiries, and the venue's settings                                              |
| `staff`       | Staff-only tooling that cuts across the other apps: audit log and sales reporting                                  |

## Contents

- [4.1 `screenings`](#41-screenings)
- [4.2 `bookings`](#42-bookings)
- [4.3 `concessions`](#43-concessions)
- [4.4 `membership`](#44-membership)
- [4.5 `accounts`](#45-accounts)
- [4.6 `venue`](#46-venue)
- [4.7 Relationship overview](#47-relationship-overview)
- [4.8 Core flow: seat selection and holds](#48-core-flow-seat-selection-and-holds)
- [4.9 `staff`](#49-staff)
- [4.10 Business rule: discount and voucher order](#410-business-rule-discount-and-voucher-order)
- [4.11 Business rule: screening cancellation](#411-business-rule-screening-cancellation)
- [4.12 Note: staff system separation beyond this submission](#412-note-staff-system-separation-beyond-this-submission)
- [4.13 Business rule: payment lifecycle (online)](#413-business-rule-payment-lifecycle-online)
- [4.14 In-venue bookings (staff-assisted, card only)](#414-in-venue-bookings-staff-assisted-card-only)
- [4.15 TMDb integration](#415-tmdb-integration)
- [4.16 Authentication and registration flow](#416-authentication-and-registration-flow)
- [4.17 Accessibility implementation](#417-accessibility-implementation)
- [4.18 Ticket classes, membership tiers and priority booking](#418-ticket-classes-membership-tiers-and-priority-booking)
- [4.19 Private hire and screening visibility](#419-private-hire-and-screening-visibility)
- [4.20 Live booking summary ("Ledger")](#420-live-booking-summary-ledger)
- [4.21 Data integrity and deletion policy](#421-data-integrity-and-deletion-policy)
- [4.22 Customer cancellations and refunds](#422-customer-cancellations-and-refunds)
- [4.23 Venue settings, and what is law versus policy](#423-venue-settings-and-what-is-law-versus-policy)
- [4.24 Project structure](#424-project-structure)
- [4.25 URL conventions](#425-url-conventions)

## 4.1 `screenings`

- `Film`: `tmdb_id` (nullable, see 4.15), `title`, `slug` (unique, for the film's public URL, see 4.25), `synopsis`, `poster_path`, `trailer_key`, `age_rating`, `duration_minutes`, `is_active`. It's filled from the TMDb API and cached locally instead of being queried on every page load. See [4.15](#415-tmdb-integration).
- `Screen`: `name`, `is_active`. Its capacity is the number of its seats, counted when needed rather than stored, so it can never disagree with the seat plan.
- `Seat`: `screen` (FK), `row_label`, `seat_number`, `area` (stalls or circle). Unique on `(screen, row_label, seat_number)`. This is the fixed physical plan for a screen and doesn't change per booking. Area says where a seat is, for the seat map and for a screen reader's description of it. It doesn't affect price: the real venue charges the same wherever you sit, and so does this project. If a venue did price areas differently, `ScreeningPrice` could take an area column later without disturbing anything else.
- `TicketClass`: `name` (for example Standard, Silver Screen, Summer Saver, Family Super Saver, Subtitled, Live Event), `description`, `default_price_pence` (nullable, a suggestion and not an enforced price), `is_active`. This is modelled on how the real Regal prices things: a discounted showing such as a Silver Screen screening is a property of that showing, not a discount worked out from who is booking. See [4.18](#418-ticket-classes-membership-tiers-and-priority-booking).
- `TicketType`: `name` (Adult, Student, OAP, Child), `is_active`. The kind of person a seated ticket is for. Infants are handled separately, see `Booking.infant_count` in 4.2.
- `Screening`: `film` (FK), `screen` (FK), `ticket_class` (FK), `date_time`, `ends_at` (worked out on save, see below), `cancelled_at` (nullable, see [4.11](#411-business-rule-screening-cancellation)), `public_onsale_at` (nullable, see 4.18), `is_private` (default `False`, see [4.19](#419-private-hire-and-screening-visibility)), `has_captions`, `has_audio_description`.
- `ScreeningPrice`: `screening` (FK), `ticket_type` (FK), `price_pence`. One row per ticket type per screening, unique together on `(screening, ticket_type)`. When staff create a screening, the form pre-fills a price for each ticket type from the chosen class's default, and staff adjust any line. A flat-priced showing such as a Silver Screen screening carries the same price on every row.

There are two layers of pricing. `TicketClass` describes the showing and sets its starting prices. `TicketType` describes the person each seated ticket is for. A family booking two adults and two children has four seats at two different prices, which a single price per screening couldn't represent. The system doesn't verify eligibility for a ticket type. The customer chooses it when buying and it is checked at the door, as at a box office. That is why the `date_of_birth` and `membership_verified` fields from an earlier draft stay removed (see 4.5).

A screening cannot overlap another on the same screen. That is enforced when a screening is saved, not just when it is created, and by the database itself, so two members of staff saving at the same moment can't both get through. A screening occupies its screen from `date_time` until `ends_at`, which is `date_time` plus the trailer time, the film's runtime and the turnaround time for clearing the room. The trailer and turnaround times are the venue's to set (4.23), and either can be zero. A PostgreSQL exclusion constraint on the screen and that time range rejects any overlap, including with a private screening (4.19). A cancelled screening no longer holds its screen, so the constraint ignores it (4.11). A change to the venue's times applies to screenings saved after it.

A film's runtime can change after it's been scheduled, for example when staff correct a figure that came from TMDb. Its upcoming screenings then need a new `ends_at`, and one of them might now run into the next showing on that screen. Saving a new runtime recalculates every upcoming, uncancelled screening of the film in one transaction. If any would overlap, nothing is saved yet. Staff see which screenings clash and what they clash with, each with a link to move it, and the new runtime stays filled in on the form, so they can sort out the listings and save again. They're never just told no for a reason they can't see. Past screenings are left as they were.

## 4.2 `bookings`

- `Booking`: `user` (nullable FK, see the note below), `screening` (FK), `status` (pending, paid, cancellation_requested, cancelled, refunded), `channel` (online or in_venue), `payment_method` (`card_online` or `card_in_person`), `stripe_payment_intent_id` (nullable, only set for `card_online`), `created_by` (nullable FK to `User`, the staff member who took an in-venue booking), `voucher_used` (nullable FK to `Voucher`), `membership_tier_at_booking` (nullable FK to `MembershipTier`, a snapshot), `discount_applied_percent` (snapshot), `amount_charged_pence` (snapshot, set once when payment is confirmed), `infant_count` (free infant tickets with no seat, default 0), `created_at`.
- `SeatBooking`: `booking` (FK), `seat` (FK), `ticket_type` (FK), `price_pence` (a snapshot of what this seat's ticket cost when sold), `released_at` (nullable), and `screening` (FK, copied from `booking.screening` so the database can enforce uniqueness on `(screening, seat)`). That constraint is what stops two people booking the same seat for the same screening.

A booking can have several `SeatBooking` rows. A party booking four seats is four rows against one `Booking`, which is why seats live on their own linking table and not in a single field on `Booking`.

Releasing a seat without deleting the record. When a booking is cancelled or refunded before the screening, its seats go back on sale immediately. The `SeatBooking` rows are not deleted. `released_at` is set instead, and the rule that stops a seat being sold twice becomes a partial unique constraint: `(screening, seat)` must be unique only among rows where `released_at` is empty. The seat can be sold again at once, and the record that it was sold and later released stays. That matters for reporting. A refunded seat was still real demand for that showing, and deleting the row would quietly remove it from any analysis of which screenings and times sell best. Live occupancy counts only unreleased rows.

Snapshots. A booking records what actually happened at the moment of purchase instead of looking things up again later. `discount_applied_percent` stores the discount rate that applied. `membership_tier_at_booking` stores which tier it came from, because a percentage alone can't be matched back to a tier once tier terms change, and a question like "how many Friend-tier members booked in March?" would become unanswerable. `amount_charged_pence` stores the final total, and each `SeatBooking` stores the price of its own ticket. Without these, a booking's total would be recalculated from the screening's current prices, so editing a price next month would silently change last month's receipts. The same reasoning applies to `OrderItem` in 4.3.

Infants. A free infant ticket needs no seat. At the real venue a baby sits on a lap or stays in a pushchair. So infants aren't seated tickets: `infant_count` is a plain headcount with no `SeatBooking` row and no price, and it tells the venue how many infants to expect. The booking form rejects a booking with no seated ticket. I haven't decided whether to cap the number of infants per booking.

`user` is nullable. A walk-up customer paying by card at the venue doesn't need an account, in the same way buying a ticket at a real box office doesn't. If they want their membership discount, staff look their account up (by email, for example) and link the booking to it. Otherwise it is a guest sale with no discount. See 4.14.

## 4.3 `concessions`

- `Product`: `name`, `price_pence`, `category` (drink or snack).
- `OrderItem`: `booking` (FK), `product` (FK), `quantity`, `unit_price_pence` (a snapshot of the product's price when the order was placed).

Food and drink pre-orders ride along with the ticket purchase through the same checkout and the same `Booking` record, instead of being a separate transaction.

## 4.4 `membership`

- `MembershipTier`: `name` (for example Friend, Premium Friend), `annual_fee_pence`, `priority_booking_hours` (how far ahead of general on-sale a member of this tier can book), `ticket_discount_percent`, `food_drink_discount_percent` (nullable, a higher-tier perk), `description`. It's modelled on real theatre Friends schemes, such as Chelmsford Theatre's two tiers of priority booking plus escalating discounts, instead of the demographic self-select approach in my first draft. See [4.18](#418-ticket-classes-membership-tiers-and-priority-booking).
- `Voucher`: `code`, `initial_value_pence`, `remaining_value_pence`, `expires_at`, `source` (purchased, screening_cancelled or booking_cancelled), `is_active`. A voucher isn't tied to a user, in the same way a physical gift card isn't: whoever has the code can redeem it. Its balance is drawn down at checkout and can be spread across more than one booking until it reaches zero.

## 4.5 `accounts`

- `Profile`: `user` (1:1 with the custom `User`, see 4.16), `membership_tier` (nullable FK to `MembershipTier`), `membership_expires_at` (nullable, see 4.18).

An earlier draft had `date_of_birth` and `membership_verified` to support demographic discounts, such as confirming someone really was a senior or a student. Discounted showings are now priced per screening through `TicketClass`, and ticket types are checked at the door, so neither field has a purpose. Instead of leaving dead columns in the schema I removed them. A paid membership is valid if `membership_expires_at` is in the future, which is a database check and not a staff judgement.

## 4.6 `venue`

- `EnquiryRequest`: `name`, `email`, `event_type`, `preferred_date`, `party_size`, `message`, `status`, `resulting_screening` (nullable FK to `Screening`, see [4.19](#419-private-hire-and-screening-visibility)). It handles private hire and event enquiries without a full booking and payment flow.
- `VenueSettings`: a single record holding the values a venue is most likely to want to change. See [4.23](#423-venue-settings-and-what-is-law-versus-policy).
- Static content (About, Accessibility policy, Membership terms) is plain templates, not models, unless there's a reason later to make it editable by staff.

## 4.7 Relationship overview

```text
User ──1:1── Profile ──FK (nullable)── MembershipTier

User ──FK (nullable, as customer)── Booking
User ──FK (nullable, as staff)──── Booking.created_by
User ──FK (nullable)────────────── SeatHold.user
User ──FK──────────────────────── AuditLogEntry.actor

Booking ──FK── Screening ──FK── Film
   │              │          └──FK── TicketClass
   │              └──FK── Screen ──1:N── Seat
   │
   ├──1:N── SeatBooking ──FK── Seat, TicketType, Screening (duplicated, partial unique constraint)
   ├──1:N── OrderItem ──FK── Product
   ├──FK (nullable)── Voucher            [1 Voucher : N Bookings, balance drawn down over time]
   └──FK (nullable)── MembershipTier     [snapshot at time of booking, see 4.2]

Screening ──1:N── ScreeningPrice ──FK── TicketType   (unique on screening + ticket type)

SeatHold ──FK── Screening, Seat (unique_together)

AuditLogEntry ──FK (nullable)── Booking   (related_booking)
              ──FK (nullable)── Voucher   (related_voucher)

EnquiryRequest ──FK (nullable)── Screening  (resulting_screening)
```

This is the one place every relationship in the schema appears together.

## 4.8 Core flow: seat selection and holds

There's a gap between a customer selecting seats and completing payment. Without handling it, someone could pick seats, spend time in checkout, and be told at the payment step that somebody else got there first. So seat selection uses a short-lived hold, separate from a confirmed booking.

`SeatHold`: `screening` (FK), `seat` (FK), `session_key`, `user` (nullable FK, see 4.16), `expires_at`, `extension_count` (default 0). `unique_together = ('screening', 'seat')`.

`SeatHold` is a separate model from `SeatBooking` (4.2) because a hold is provisional and expires if unused, whereas a `SeatBooking` means the seat has been paid for. Keeping them apart means an abandoned checkout can never permanently block a seat.

The hold times below are defaults (10 minutes, 5 minutes per extension, 30 minutes in total). The venue can change them, see 4.23.

1. Page load. The seat grid is rendered on the server with each seat's live status (available, held or booked), so the customer is never looking at stale information. Each status is a single `data-seat-status` attribute, styled through the CSS exception layer (see [section 3](ux_design.md)).
2. Selecting seats. This is client-side toggling while browsing the grid, with no server call yet.
3. Proceeding to checkout. One request sends the chosen seat IDs and a ticket type for each. In a single transaction the server clears any expired holds for that screening, checks the requested seats are still free against both live holds and confirmed bookings, and if they are, creates fresh `SeatHold` rows.
4. Conflict. If a seat was taken between page load and this request, the server returns exactly which seats failed. The page marks only those as taken, deselects them, and shows an inline message. The customer's other selections are kept.
5. A failed payment attempt (declined card, insufficient funds, wrong details) does not release the hold. The customer sees the specific reason and can try again, with a different card or corrected details, as many times as they like within the hold window. Each failure extends `expires_at` by a short amount and increments `extension_count`, up to a hard cap on total hold time. A real retry isn't punished, but a hold can't be kept alive forever.
6. Explicit cancellation. A Cancel button releases the hold immediately instead of waiting out the timer.
7. Successful payment. In the same transaction that creates the `Booking` and its `SeatBooking` rows, the originating `SeatHold` rows are deleted instead of being left to expire (4.13 covers exactly when this happens relative to Stripe's confirmation). That keeps `SeatHold` meaning one thing at all times, a seat still in progress, with no stale rows for seats that were paid for long ago.
8. True abandonment (tab closed, no cancel, no retry). Nothing needs to release the seat. The hold expires when its time runs out, and the next hold attempt's cleanup step (step 3) removes it.
9. Hold expires mid-checkout. Payment confirmation checks the hold still exists before accepting the charge. If it has expired, the customer returns to the seat map with a plain explanation, not a confusing card decline for seats they no longer hold.
10. Back and forward navigation. The seat grid re-fetches live state when the page is shown, so the back button can never display an out-of-date "your seats" view.
11. Going back and amending. Until payment is submitted, the customer can go back and change anything without starting again: add or remove seats, change a seat's ticket type, change the infant count, or edit food and drink. The hold, not the browser, is the source of truth for what the customer has selected, and each step is an ordinary server-rendered page reachable with the back button. Changing seats releases the holds on the seats removed and creates holds on the seats added in one transaction, so the customer never ends up holding nothing, or holding both. Each change restarts the hold timer, within the hard cap.
12. Cancelling releases seats at once. Choosing Cancel, or switching to a different set of seats, releases the old holds immediately. A seat is never left unavailable to other customers because someone changed their mind.

## 4.9 `staff`

This app has no customer-facing models. It owns the one new cross-cutting concern, accountability for staff actions, and otherwise only reads data that lives in the other apps, for reporting. Keeping it separate avoids scattering staff-only concerns across every domain app, and avoids copying booking and sales data into a second model just to report on it.

`AuditLogEntry`: `actor` (FK to `User`), `action_type` (refund, screening_cancelled, booking_cancelled, voucher_issued), `related_booking` (nullable FK), `related_voucher` (nullable FK), `reason` (text, required), `created_at`.

Logging is automatic. An `AuditLogEntry` is created by the same server-side action that performs the sensitive operation, not filled in by staff afterwards on a separate form. It can't be forgotten or skipped, so the who and why exist for anything sensitive that happened.

Permissions, not fixed roles. What a staff member can do is controlled by Django's permission system. Each sensitive action has its own small permission, for example `cancel_booking`, `issue_voucher`, `refund_booking`, `cancel_screening`, `create_in_venue_booking`, `manage_screenings`, `manage_films`, `manage_enquiries`, `manage_venue_settings` and `view_sales_dashboard`. Groups are named bundles of these permissions. Application code never asks whether someone is a Manager. It asks whether the user holds the specific permission the action needs.

I ship two groups as starting points, `FrontOfHouse` and `Manager`. By default Front of House can take in-venue bookings, manage enquiries, cancel a booking and issue a voucher. Manager holds every permission, including card refunds, cancelling a screening and the sales dashboard. These are defaults, not rules. A venue that wants front of house to refund on their own judgement, or wants every refund to go through one person, changes the group's permissions in the admin without touching the code.

Discretion is accountable. Whoever holds a permission, using it records who did it and a required reason in an `AuditLogEntry`. The system doesn't decide who is trusted with a refund, but it does decide that nobody refunds invisibly.

Business overview. This is a set of read-only views, available to holders of `view_sales_dashboard`, built on Django's aggregate queries over existing data: revenue by day, week and month, revenue and seat occupancy by screening, top-selling concessions, tickets sold by type, and the total value of discounts and vouchers redeemed. Because it's computed live from `Booking`, `SeatBooking` and `OrderItem`, the numbers can't drift out of sync with the bookings.

Access. The staff views (and the staff-only views in other apps) sit under their own `/staff/` path with their own login page, separate from the customer site. No customer-facing template links to it. Everything stays reachable in one deployment, which matters for assessment, while staff tooling still has a separate identity from the public site. See [4.12](#412-note-staff-system-separation-beyond-this-submission) for how this would develop for a real venue.

## 4.10 Business rule: discount and voucher order

Ticket prices, membership discounts and vouchers can all touch the same booking, so the order they're applied in has to be fixed and documented. Otherwise the same logic is easy to implement two different ways in two places.

Ticket-class pricing isn't part of this stack. A screening's `ScreeningPrice` rows already reflect its class (4.1) before any of the following runs, so a Silver Screen showing is simply priced lower from the start. There's nothing to apply.

The order is:

1. Start from the sum of each seated ticket's own price (the `ScreeningPrice` for its ticket type, stored on its `SeatBooking`) and any concessions. Infant tickets are free and add nothing.
2. Apply the customer's membership tier discount, if any, and snapshot it onto `discount_applied_percent` (4.2).
3. Deduct what's left from the customer's voucher balance, if a code was entered, up to the voucher's remaining balance.
4. Charge the remainder to Stripe. If the voucher covers the whole total, no Stripe charge is needed, but the `Booking` is still marked paid.

A voucher can never take a booking below £0. Any unused balance stays on the voucher for a future booking and isn't paid out as cash.

An earlier version of this design also had a staff discretionary discount and a promo-code layer, each with its own stacking rule. I've moved those to [Marketing development thoughts](future_ideas.md) as future ideas.

## 4.11 Business rule: screening cancellation

If a screening has to be cancelled (a technical fault, for example), a staff member holding the `cancel_screening` permission triggers the following for every existing `Booking` against it. The booking is marked `cancelled` and its seats are released immediately (`released_at` is set, see 4.2). The customer is then offered their money back in one of two ways: a `Voucher` for the full amount they paid (`source='screening_cancelled'`), which is the default, or a refund to their original card.

I offer both because the venue has failed to provide what was paid for, and general guidance on UK consumer rights is that the customer is then entitled to a refund of the ticket price, not just credit. The voucher is the convenient option, not an imposed one. See 4.22 for the legal background. Each affected booking produces one `AuditLogEntry`, with the staff member as actor and "screening cancelled" as the reason, so there is a single reviewable batch of entries and not an invisible change.

The screening itself isn't deleted. It gets `cancelled_at` set, and it stays in the public listings until its date has passed, greyed out and labelled "Cancelled", with no way to book it. Someone who saw a showing listed yesterday should be able to find out what happened to it, not find it quietly gone. It uses the same text label and accessible description as a greyed-out priority screening (4.17, 4.18), so the state never depends on colour alone. A cancelled screening no longer holds its screen, so staff can schedule a replacement in the same slot.

## 4.12 Note: staff system separation beyond this submission

This section describes a possible future direction and is out of scope for the submitted project. For assessment, the staff tooling runs in the same Django deployment as the public site, at its own `/staff/` URL with its own login page and no link to it anywhere in the customer templates. That shows the intended separation of concerns and keeps the whole project testable through one deployment.

If this were taken further for a real venue, the same split between customer-facing and staff-only would be worth making an actual infrastructure boundary and not just a routing one:

- Network isolation: the staff area restricted to the venue's own network or a VPN, so only the public booking site faces the internet.
- Separate staff authentication: a proper provisioning and offboarding process instead of ad hoc `User` rows created by a superuser, so a leaver's access is reliably revoked, plus two-factor authentication for anyone who can process refunds.
- Device controls: the venue's tablets and terminals in a locked-down kiosk browser profile pointed only at the staff URL, with passcodes and remote wipe, since they sit in a publicly accessible building.
- Shift-appropriate sessions: a short auto-logout, so one person's session isn't still active for the next person on a shared tablet. This matters for the audit log's attribution to stay meaningful.
- Reporting load: if volume made the dashboard queries heavy, running them against a read replica so a sales report can never slow down a customer mid-checkout.
- Dual authorisation: a second manager's sign-off for refunds above a set amount. The audit log already records who did what, so this would extend it naturally.

None of this is needed to meet the assessment criteria, and building it now would add complexity for no credit. I've recorded it because the reasoning is worth keeping if this becomes more than coursework.

## 4.13 Business rule: payment lifecycle (online)

The main principle is that a Stripe webhook, not the customer's browser, is the source of truth for whether payment succeeded. If the connection drops or the customer closes the tab mid-payment, the app can't rely on them ever reaching a success page. The booking only becomes real when Stripe tells the server it has been paid.

1. Checkout starts, and a `SeatHold` already exists (see 4.8). The server calculates the final total using the order in 4.10 and creates a Stripe PaymentIntent for that amount. Stripe runs in test mode throughout.
2. If the total is £0 (a voucher covers it), there's no Stripe interaction. The booking is marked paid on the server straight away.
3. Otherwise the customer pays through Stripe's client-side card element. Card details never touch this application's server.
4. The server's only immediate response to the browser is "payment submitted", not "payment succeeded".
5. Stripe sends a `payment_intent.succeeded` webhook, and this is what finalises everything. The hold converts to confirmed `SeatBooking` rows, the voucher balance is reduced (not before, see below), and a confirmation is sent.
6. A declined or failed attempt (`payment_intent.payment_failed`) does not release the hold. See the retry behaviour in 4.8, step 5.
7. Uncertain outcomes, such as the connection dropping after submission but before the browser heard back, are resolved by checking the PaymentIntent's real status with Stripe before allowing a new attempt, never by assuming failure because the client got no response. That avoids charging a card twice when the first payment did go through.

Two implementation details are easy to get subtly wrong:

- Webhook signature verification. Stripe signs every webhook payload. The endpoint must verify the signature before trusting it, or anyone could post a fake "payment succeeded" event.
- Idempotency. Stripe can deliver the same webhook event more than once. The finalising logic checks whether the booking is already marked paid before acting, so a redelivered webhook can't reduce a voucher twice.

A voucher's balance is only reduced once the webhook confirms payment, not at checkout. Otherwise an abandoned or failed payment would have spent someone's voucher for nothing. It's the same provisional-then-committed pattern as the seat hold, applied again.

Refunds (4.22) call Stripe's refund API directly and get an immediate response, unlike the original payment, so they don't wait on a webhook.

There's one known limitation I'm not solving. A voucher's balance isn't held the way a seat is. If the same code were entered in two simultaneous checkouts, there's a narrow window where both could succeed against the same balance before either payment confirms. A voucher has to be typed in by hand, so this is unlikely and low in severity, and fixing it properly would need a second holding mechanism like `SeatHold`, which is out of proportion to the risk. It's listed under [Known issues](testing.md#9-known-issues).

## 4.14 In-venue bookings (staff-assisted, card only)

A walk-up customer should be able to book much the same way an online customer does, with the same seat map, concessions and discounts, while a member of staff completes it for them. The real Regal is cashless, so this project is card only, in the venue as well as online.

Channel (online or in venue) is a separate decision from payment method. A customer at the venue pays by card without that counting as online, and without needing to give an email address or create an account. That matters to customers who'd rather not hand over an email just to pay at the counter.

This reuses the existing booking flow. The same `SeatHold` to `SeatBooking` mechanics, the same ticket types (including any infants) and the same discount order (4.10) apply unchanged. The differences are who starts it and how payment is recorded:

- `Booking.channel = 'in_venue'`, `Booking.payment_method = 'card_in_person'`, and `Booking.created_by` is the staff member completing the sale.
- `card_in_person` means the customer paid on the venue's own card machine, not through Stripe. That terminal sits outside this application, like a till would, and staff mark the booking paid once payment is confirmed. No PaymentIntent is created, so `stripe_payment_intent_id` stays empty.
- `Booking.user` is blank for a walk-up sale. No account or email is required, as at a real box office. If the customer wants their membership discount, staff look up their account (by email, for example) and attach it. Otherwise it's an anonymous guest sale.
- A same-day in-person purchase needs no email confirmation, though staff can send one if the customer gives an address. The booking screen serves as the receipt.

This is available to anyone holding `create_in_venue_booking`, which Front of House has by default. It is a routine box-office sale, not a discretionary override.

## 4.15 TMDb integration

Building on the `Film` model (4.1) and the hybrid approach I settled on, with real film data from TMDb and scheduling of my own, this section sets out when TMDb is called and what happens when it isn't available.

The live API is only called in the staff "add a film" flow. The public site never calls TMDb. Customers see the `Film` rows already saved locally. So if TMDb is slow or down, the only effect is on a staff member adding a new film that day. Customers browsing or booking aren't affected, because that data comes entirely from the local database.

Adding a film:

1. Staff search by title. Titles aren't unique (sequels, remakes, foreign-language titles), so results appear as a short list with poster thumbnail, title and release year, and staff pick the right match instead of the system guessing.
2. On selecting a result, the app fetches the film's full detail (synopsis, runtime, genres), its trailer videos, and its UK age certification from TMDb's release-dates data, filtered to the GB entry.
3. The results are pre-filled, not saved automatically. Staff see the synopsis, poster, a suggested trailer and a suggested age rating on a review screen before anything is saved. The age rating matters most, because TMDb's certification coverage is inconsistent and a wrong certificate on age-restricted content has real consequences. A person confirms before it goes live, and the API only saves the typing.
4. Once confirmed, it's saved as a local `Film` row and isn't queried again unless staff choose to refresh it.

Films with no TMDb entry. Not everything a venue shows is a commercial release with a TMDb page. Event cinema (a National Theatre Live broadcast), a Q&A screening or a private hire's own content wouldn't have one. Staff can add a `Film` by hand, leave `tmdb_id` empty and fill in the same fields. A `Screening` doesn't need to know which path a film came from.

Images. I don't download and re-host posters. `Film.poster_path` stores TMDb's relative image path and the display URL is built from TMDb's image CDN address at render time. TMDb serves these images for exactly this kind of use.

Trailers. A film can have several videos on TMDb (teasers, clips, trailers in different languages). The system suggests the likeliest candidate, an official YouTube trailer where it can find one, and staff confirm it or choose another from the list. If no suitable video exists, the trailer embed is left out instead of showing a broken player.

Failure handling. If TMDb is unreachable or returns an error during the add-film flow, staff see a plain, specific message ("Couldn't reach the film database, try again in a moment") with a retry option, not a generic crash. It's staff-only and not time-critical, so a clear message and a retry button is proportionate. A queued background retry would be overbuilt.

Rate limits and the API key. TMDb's limits are generous, and calls only happen when staff add a film, never on a customer page view. The API key is a server-side environment variable, like the Stripe keys, and the browser never sees it.

Refresh. Cached film data won't pick up a poster or synopsis that TMDb later corrects. A "Refresh from TMDb" action on a film's staff edit page re-runs steps 2 and 3 and overwrites the local record, again after staff review. That covers it without a background sync job.

## 4.16 Authentication and registration flow

Signup asks for an email and password only. `Profile` (4.5) is created automatically by a signal when a `User` is created, so there's no second form. A membership tier is added later, on the profile page, if the customer chooses to become a Friend (see 4.18).

I'm using a custom user model, `accounts.User`, with email as the login field and no username. It subclasses Django's `AbstractUser`, removes `username`, sets `USERNAME_FIELD = 'email'`, and has its own manager so `createsuperuser` asks for an email. A custom user model has to exist before the first migration runs, because swapping one in later means rebuilding every table that points at `User`. So it goes in at the very start of the `accounts` app, before anything else is migrated. Django's own documentation recommends this for any new project, and doing it now costs almost nothing.

Email is unique in the database. Django's default `User` doesn't enforce unique email addresses, which is easy to forget because it feels like it should. Here the email field has `unique=True`, so one address can't create two accounts, and with no username there's nothing generated behind the scenes that could collide.

Emails are lowercased before they're saved or looked up, so `J.Smith@example.com` and `j.smith@example.com` are the same account. Strictly, the part before `@` can be case-sensitive, but mainstream providers don't treat it that way, and keeping them separate would let one person register twice by accident.

`Profile` stays separate from `User`. The user model holds only what's needed to log in, and membership data lives on the profile, so the auth model stays small.

Login and registration pages are for anonymous users only. A logged-in user who visits them is redirected away. This is a pass-level requirement, not a nicety.

Email verification is sent but doesn't block. A verification email goes out on registration, but the account works immediately. Someone registering to book a seat in the next five minutes shouldn't be stuck waiting for an email. Verification is a gentle reminder, such as a banner, not a gate. Password reset uses the signed-token approach Django already provides, so I don't need a second token-storage model for verification.

Registration is required to complete an online checkout, but not to browse or select seats, and not for an in-venue card sale. These are two rules for two real-world contexts, not an inconsistency. Browsing and picking seats works anonymously, but finishing an online purchase needs an account, which gives the clear reason to register that the assessment criteria ask for, since booking history and the membership discount both depend on having one. In-venue sales stay guest-friendly (4.14) because a walk-up customer at a box office was never going to be asked to create an account first.

Seat holds surviving a mid-checkout login. Django rotates a user's session ID when they log in, as a defence against session fixation. `SeatHold` (4.8) is tied to `session_key`, so a customer who selects seats anonymously and then registers or logs in mid-checkout (exactly what "continue to checkout" prompts) would silently lose their hold the moment login succeeded. To prevent that, `SeatHold` carries a nullable `user` FK alongside `session_key`, and on a successful login any holds under the current session are reassigned to that user. It's a small addition, but without it the failure would be confusing and hard to reproduce, at exactly the moment a customer is trying to buy.

Staff logins are entirely separate: a different URL and a different login template (4.9, 4.12), unrelated to whether a staff member also has a personal customer account.

## 4.17 Accessibility implementation

The captioned and audio-described flags on `Screening` (4.1) are about the film experience. This section is about the website: making it usable by someone on a keyboard alone, with a screen reader, or with low vision.

The target is WCAG 2.1 AA, the practical, widely used baseline, which makes the "meets accessibility guidelines" pass criterion checkable instead of aspirational.

Structure and semantics. One `<h1>` per page, a logical heading order, and semantic landmarks (`<nav>`, `<main>`, `<footer>`) so a screen reader user can jump to a section instead of reading the page from the top. Anything clickable is a real `<button>` or `<a>`, never a `<div>` with a click handler, which gives keyboard and screen reader support without extra work.

Colour and contrast. The dark palette from [section 3 (Surface)](ux_design.md#v-surface) gets checked against WCAG's contrast ratios before I finalise it, not judged by eye. Text needs 4.5:1 against its background, and the gold accent needs checking wherever it's used for anything beyond large or decorative text, since a colour chosen for mood isn't automatically legible. Nothing is conveyed by colour alone. The seat map's states (available, selected, held by someone else, booked) each get a second signal, an icon or pattern plus a text label for screen readers. A greyed-out priority screening (4.18) is conveyed by its text label and an accessible description, not just its dimmed colour.

The seat map is the most complex interactive component, so it gets specific treatment:

- Every seat is a real, focusable `<button>`, reachable by Tab and activated with Enter or Space. Nothing is hover-only or click-only.
- Each seat's accessible name says what a screen reader user needs ("Row C, seat 4, circle, available"), not just a grid coordinate.
- When a seat-hold conflict happens (4.8) and the page updates inline, the change is announced through an ARIA live region. A sighted user sees the seat change. A screen reader user has to be told it became unavailable, or the inline-update design from 4.8 fails for them.

Forms (registration, checkout, enquiries, staff tools). Every input has a real, associated `<label>`. Validation errors are stated in text, not colour alone, and tied to their field so a screen reader announces which field the error belongs to.

Focus and motion. I'm defining a visible, high-contrast focus style for the dark theme instead of relying on the browser default, which can be hard to see on a very dark background, or removing it because it looks cleaner. Transitions and layout shifts respect `prefers-reduced-motion`, and trailers never autoplay, which is as much an accessibility decision as a stylistic one.

The fluid layout approach from _Every Layout_, chosen for its own reasons, also makes the site more resilient to text zoom and large-text browser settings than a pixel-fixed layout would be. Two separate decisions help each other here.

Verification. I won't assume accessible markup is accessible in practice. An automated pass (Lighthouse or axe) catches the mechanical issues: contrast, missing labels, landmark structure. A manual keyboard-only pass through the booking flow, the highest-risk journey, catches what tools can't, such as whether the live region announces a lost seat sensibly. See [Testing](testing.md).

## 4.18 Ticket classes, membership tiers and priority booking

This replaces an earlier draft of the membership design, after I checked it against how the real Regal in Evesham structures things. Two changes came out of that: discounted showings belong to the screening, not the customer, and membership is a paid Friends scheme instead of a free, self-selected discount category.

Ticket classes. The real venue's site lists named categories (Silver Screen, Summer Saver, Family Super Saver, Subtitled, Live Event and others). A customer review confirms what one of these is: a specifically discounted showing (Silver Screen, priced around £8 against a higher standard price), not a discount worked out from who is booking. I model that directly. `TicketClass` (4.1) is a label with an optional default price, assigned to a `Screening` when it's created. Staff pick the class, the system suggests prices, and staff can override any of them. There is no age or identity check, because there isn't meant to be one. Anyone can book a Silver Screen showing. It's priced for that audience.

Membership as a paid Friends scheme. `MembershipTier` (4.4) replaces the free, self-selected OAP/Family/Student category from the earlier draft with a paid, tiered scheme of the kind UK theatres commonly use, such as Chelmsford Theatre's entry tier with priority booking and a higher tier adding discounts. A customer buys a tier with a one-off Stripe charge (the same `card_online` pattern as a booking, not a new payment mechanism), which sets `Profile.membership_tier` and `membership_expires_at` to one year from purchase.

No auto-renewal. Membership doesn't renew or charge a saved card when it lapses. That would mean recurring billing, a much bigger feature involving Stripe subscriptions and their own webhook events, and out of proportion to this project. A lapsed member sees a "renew your membership" prompt and repeats the same one-off purchase. This is a scope boundary, like the other "beyond this submission" notes in 4.12.

Priority booking. `Screening.public_onsale_at` (4.1) is when a screening opens to the general public. Before that, only a member whose tier's `priority_booking_hours` covers the gap can book it, that is, when `now >= public_onsale_at - tier.priority_booking_hours`. If `public_onsale_at` is blank, the screening is members-only permanently, instead of counting down to a public date. That's the same mechanism as something like a members' Q&A event, with no eventual public on-sale. One field serves both purposes, with no pair of booleans that could contradict each other.

Priority screenings stay visible. A screening that isn't yet open to the public still appears in listings to everyone, greyed out with a clear text label: "Friends can book from Thursday 9am, open to all from Saturday 9am", or just "Friends only" where `public_onsale_at` is blank. The label links to the membership page. A non-member can see a showing they want and exactly what would let them book it, which gives the membership scheme a concrete reason to exist at the moment it matters.

Ticket and food and drink discounts from a member's tier apply through the order in 4.10.

What this removes from the earlier design: the old self-declared membership category and the staff "verify a member's ID" action. A paid membership's validity is a `membership_expires_at` check, not a judgement staff make in person. That's one less thing for Front of House to manage and one less field in the schema without a clear purpose.

## 4.19 Private hire and screening visibility

`EnquiryRequest` (4.6) handles the first private hire or event conversation, but nothing so far connected it to an actual bookable (or unbookable) `Screening`. I had to settle how an agreed hire becomes a real screening, and whether the public should see or book it.

There's no automatic conversion. Once terms are agreed with a hirer, staff create a `Screening` the same way as any other: pick a film (or, for a non-film event, a manually added `Film` per 4.15), a screen and a date and time, and tick `is_private`. Automating enquiry to screening would also mean handling quoting and invoicing, a different and larger feature area than a booking system. A manual step here is a scope boundary. For traceability, `EnquiryRequest.resulting_screening` links back to the `Screening` that came out of the conversation.

What `is_private = True` changes:

- The screening doesn't appear in public "what's on" listings.
- Online booking by customers is blocked for it entirely, since there's no public seat map to book against.
- It still takes part in the overlap check (4.1). A private hire occupies the screen for that slot, so it has to block public screenings from clashing with it like any other.
- If the hirer wants individual seats tracked instead of a single flat-fee block, staff create those bookings through the in-venue flow (4.14). A private hire's seats are no different from a staff-assisted walk-up sale arranged in advance.

Payment for the hire itself stays outside this system. The fee is negotiated and settled through the enquiry conversation (an invoice, a bank transfer, whatever the venue already does) and not through Stripe. A quoting and invoicing flow is out of scope, and private hire agreements are usually too bespoke (catering add-ons, differing durations, negotiated rates) for a fixed per-seat checkout. `is_private` reserves the slot and controls visibility. It doesn't process the hire's payment.

## 4.20 Live booking summary ("Ledger")

A booking involves several things that change independently as a customer moves through it: seats selected, ticket types, concessions added, a voucher entered, a membership discount applied. A summary that only updates on the next page turn is a common weak point in booking flows, so I'm designing it out from the start.

The pattern is a sticky summary panel, visible throughout seat selection and checkout, that updates the moment something changes, with a line for each ticket type. Two things make it correct as well as responsive:

- Optimistic client-side updates, reconciled on the server. The displayed total recalculates in the browser the moment something changes, using prices already on the page, so it feels instant. At each real step (moving from seat selection to checkout, for example) the server recalculates the total from scratch using the order in 4.10, and that figure is what's charged. The client-side number is a responsive preview and the server-side number is the source of truth. A customer should never see a total that later turns out to be wrong, and since both use the same logic they shouldn't disagree in practice.
- It's a block, not a composition pattern, in CUBE CSS terms (3.II). `.booking-summary` is a specific, scoped component with its own behaviour, using a stack internally for its vertical rhythm, not a general layout primitive reused elsewhere.

This supports the principle in the design scope (3.II) that the customer is shown progress and feedback on transactions.

## 4.21 Data integrity and deletion policy

Every foreign key in Django needs an explicit `on_delete` behaviour, and the tempting default of `CASCADE` everywhere is dangerous here. Deleting a `Film` must never be able to wipe every `Screening`, and through it every `Booking`, ever made against it. A manager tidying old film entries is exactly the kind of action that could destroy sales history the business would want: which screenings sold well, at what times, and when.

I've stated the policy once instead of deciding model by model.

`PROTECT` applies to any foreign key pointing at something with financial or historical value: `Booking.screening`, `SeatBooking.seat`, `SeatBooking.screening`, `SeatBooking.ticket_type`, `OrderItem.product`, `AuditLogEntry.related_booking`, `AuditLogEntry.related_voucher`, `Screening.film`, `Screening.screen`, `Screening.ticket_class` and `ScreeningPrice.ticket_type`. The database refuses the delete. A film, screen, product, ticket class or ticket type that needs retiring is marked inactive instead, so the record stays intact and queryable.

`SET_NULL` applies only where losing the reference is harmless: `Booking.created_by` (if a staff account is later removed, the sale and its figures stand), `Booking.voucher_used` and `Booking.membership_tier_at_booking`, since the snapshot fields on `Booking` already capture what mattered at the time.

`CASCADE` is for true parent and child ownership, where the child has no meaning without its parent: `Profile` on `User`, `SeatHold` and `ScreeningPrice` on `Screening`, and `Seat` on `Screen`. Deleting a screening created in error, before it had any bookings, takes its holds and prices with it.

## 4.22 Customer cancellations and refunds

What the law says, and what it doesn't. Tickets for a specific date and time fall under an exemption in Regulation 28(1)(h) of the Consumer Contracts Regulations 2013, which removes the 14-day change-of-mind right for services related to leisure activities where the contract sets a specific date or period. A customer therefore has no statutory right to cancel a cinema booking because they chose the wrong showing, and any cancellation window is the venue's own goodwill policy. The opposite case is different. When the venue cancels a showing, the customer generally has a right to their money back, which is why 4.11 offers a card refund alongside the voucher.

Membership may be different. A one-year membership sold online is a service without a fixed performance date, so the 14-day right may apply to it. I haven't yet checked this against official guidance (Citizens Advice, GOV.UK), and I need to before building the membership purchase flow. It may mean a short "cancel within 14 days" path. This section is general information, not legal advice.

The flow. From My Bookings, a customer can request cancellation of an upcoming booking up to a venue-set number of hours before the showing (24 by default, see 4.23). The request moves the booking to `cancellation_requested`, with an optional reason. A staff member holding `cancel_booking` reviews and approves it. Approving means choosing how the money goes back: a voucher (needs `issue_voucher`) or a card refund (needs `refund_booking`). Either way the seats are released immediately, the booking becomes `cancelled` or `refunded`, and an `AuditLogEntry` records who approved it and why. This reuses the refund path from journey 15, so it adds one status and one queue and not a second mechanism.

Inside the cutoff, the answer is a phone call. Within the window, the cancellation page doesn't offer the request form. It shows the venue's phone number and opening hours and explains that staff may be able to help. This is a human decision on purpose. A half-empty showing two hours away is a different judgement from one that is nearly sold out, and the system can't make that call. A staff member with the permission can cancel any booking at any time, since the cutoff limits the customer's self-service request, not the venue.

Making the phone route work. The cancellation policy is shown before payment, next to the total, as well as on the confirmation screen and in My Bookings. The booking reference appears prominently on the confirmation so it can be read out over the phone, and staff can find a booking by reference or by the email lookup used for in-venue sales (4.14).

A grace period is a Could, and I haven't built it. A short window after purchase (30 minutes, say) would let a customer cancel online even inside the cutoff, for someone who notices a wrong date seconds after booking. The cutoff would become the later of "cutoff hours before the showing" and "30 minutes after booking". The phone route covers the same case, so it stays out until real use shows it's missed.

Sources for the legal background: [NI Business Info, exemptions from the right to cancel consumer contracts](https://www.nibusinessinfo.co.uk/content/exemptions-right-cancel-consumer-contracts); [Legal Documents, event ticketing consumer rights and protections](https://www.legaldocuments.co.uk/consumer-law-rights-and-remedies/event-ticketing-consumer-rights-and-protections/).

## 4.23 Venue settings, and what is law versus policy

The system provides mechanisms and the venue owns the policy. A made-up cinema's choices shouldn't be baked into a booking platform that any venue could use. A single `VenueSettings` record in the `venue` app, editable by staff holding `manage_venue_settings`, holds the values a venue is most likely to want to change:

- the cancellation cutoff, in hours (default 24)
- the venue's phone number and opening hours, shown on the cancellation page
- the seat-hold length, the extension per failed payment, and the hard cap (defaults 10, 5 and 30 minutes, see 4.8)
- the trailer time before a film and the turnaround time after it, used for the no-overlap rule (defaults 20 and 15 minutes, see 4.1)

Membership tiers, prices, ticket classes and permission groups are already data, so they need no special handling. The numbers quoted elsewhere in this document (24 hours, 10 minutes and so on) are shipped defaults, not rules. If time gets tight, a plain settings file is an acceptable first version of this record, and I'd describe the settings model as the next step.

Some behaviours stay fixed because they bind a venue whatever its preferences: the refund owed when the venue cancels a showing (4.11), the required reason and named actor on every sensitive action (4.9), and the cancellation-right position in 4.22. Everything else is a default the venue can change.

## 4.24 Project structure

Every app follows the same layout, so finding a file never depends on which app it's in.

```text
regal-cinema/
├── regal/                  project package: settings.py, urls.py, wsgi.py
├── accounts/ screenings/ bookings/ concessions/ membership/ venue/ staff/
│   ├── models.py           data and the rules that must always hold
│   ├── services.py         business logic (only where an app has any)
│   ├── views.py  forms.py  admin.py
│   ├── urls.py             customer routes
│   ├── staff_urls.py       staff routes, mounted under /staff/ (only where needed)
│   ├── templates/<app>/    the app's own templates
│   └── tests/              test_models.py, test_services.py, test_views.py
├── templates/              base.html, shared partials, error pages
├── static/
│   ├── css/                main.css, plus one folder per CUBE CSS layer: global, composition, utility, block, exception
│   └── js/                 hand-written scripts, one file per feature (seat-map.js)
├── docs/
├── manage.py  requirements.txt  .env.example
```

There's one settings module. Anything that differs between my machine and Render (the database URL, secret key, Stripe and TMDb keys, `DEBUG`) comes from environment variables, and `DEBUG` defaults to off, so a missing variable fails safe. `.env.example` lists every variable with a dummy value. The real `.env` is never committed.

`static/css/main.css` is the only stylesheet a page links. It declares CSS cascade layers in CUBE order (`@layer global, composition, utility, block, exception`) and imports each folder's files into its layer. A later layer always wins over an earlier one, whatever the selectors' specificity, so an exception reliably overrides the block it adjusts without stronger selectors or `!important`. The `global` folder holds the design tokens as custom properties and the base styles for plain elements. CUBE CSS treats these as the starting point the other four layers build on, and I'd left it out of the list above at first. There's still no build step: the browser reads the imports directly, and WhiteNoise serves each file compressed with a long cache lifetime.

Third-party code stays out of these folders. Python libraries come in through `requirements.txt`, and if I ever include anything vendored by hand it goes in `static/vendor/`, credited in the README.

## 4.25 URL conventions

Paths are lowercase, use hyphens between words, end with a slash, and name things in the plural for a list (`/films/`) and by key for one item (`/films/<slug>/`). Films use a slug because their pages are public and worth reading. Screenings and bookings use their primary key, or the booking reference where a customer might read it out. Each app's `urls.py` sets an `app_name`, and every route has a name in the form `<app>:<thing>_<action>`, such as `screenings:screening_detail` or `bookings:checkout_pay`. Templates and redirects always use `{% url %}` or `reverse()` with that name, never a typed path.

| Path                         | App                    | What it is                                                     |
| :--------------------------- | :--------------------- | :------------------------------------------------------------- |
| `/`                          | `screenings`           | What's on, in Reel rows                                        |
| `/films/<slug>/`             | `screenings`           | Film detail and showtimes                                      |
| `/screenings/<id>/`          | `bookings`             | Seat map and ticket types for one screening                    |
| `/booking/...`               | `bookings`             | Checkout steps, confirmation and the Stripe webhook            |
| `/account/...`               | `accounts`, `bookings` | Register, log in, log out, profile, My Bookings                |
| `/membership/`               | `membership`           | Tiers and buying a membership                                  |
| `/hire/`                     | `venue`                | Private hire enquiry form                                      |
| `/about/`, `/accessibility/` | `venue`                | Static pages                                                   |
| `/staff/<app>/...`           | each app               | Staff routes from each app's `staff_urls.py` (4.9)             |

Staff URLs are mounted under `/staff/` in the project's `urls.py`, one prefix per app (`/staff/screenings/`, `/staff/bookings/`), so the staff area has a single entry point while each view still lives in the app that owns its data.

---

[← 3. UX design strategy (the five planes)](ux_design.md) · [README](../README.md) · [5. Core features →](features.md)
