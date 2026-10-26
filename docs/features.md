# 5. Core features

Each app's customer-facing and staff-facing features, following from the [data model](architecture.md) and the [user journeys](user_stories.md).

## Permission model

There are two kinds of user: registered customers and staff. A superuser grants staff status (`is_staff`), and there's no public way to become staff. What staff can do is set by individual permissions, bundled into groups (see [4.9](architecture.md#49-staff)). Below, "Front of House" and "Manager" mean who holds the permission by default. A venue can move any permission between groups in the admin.

Staff don't use Django's built-in `/admin` for day-to-day work. It exposes every field on every model, which is more power, and more room for accidental mistakes, than daily duties need, and it doesn't match the rest of the site or guide someone unfamiliar with Django through their tasks. The day-to-day tools are custom pages instead, built with the same templates and design system as the public site and gated by permission checks: the till for in-venue bookings, the cancellation queue, the prep list and screening occupancy. The admin is for back-office configuration that changes rarely: the catalogue, ticket types and classes, seating layouts, the venue settings, and users and groups. Anything done there that's sensitive goes through the same service functions as the custom pages, so the audit log is written either way.

Anything financial or sensitive (a refund, a cancellation, a voucher issued) is recorded in the audit log with who did it and why. See [4.9](architecture.md#49-staff).

## 5.1 `screenings`

Customer-facing:

- Browse current and upcoming screenings, filterable by date, each showing its ticket class (for example Silver Screen or Family Super Saver) and prices by ticket type
- Film detail page (synopsis, trailer, age rating, captioned and audio-described indicators)
- Seat selection on an interactive seating plan of stalls and circle, with a ticket type for each seat
- Priority screenings shown greyed out with who can book them and when
- Cancelled screenings left out of every listing, with a plain "This screening has been cancelled" page for anyone following an old link ([4.11](architecture.md#411-business-rule-screening-cancellation))

Staff-facing:

- Front of House: see a screening's current seat occupancy at a glance
- Manager: search TMDb and add a film to the local catalogue, reviewing and confirming the fetched details (including age rating) before saving. See [4.15](architecture.md#415-tmdb-integration)
- Manager: add a film by hand for anything without a TMDb entry, or refresh an existing film's cached details
- Manager: create, edit or cancel a screening (film, screen, date and time, prices by ticket type, ticket class, priority booking window, private or public). The system prevents overlapping screenings on a screen, and cancelling one starts the [screening cancellation flow](architecture.md#411-business-rule-screening-cancellation)
- Manager: mark a screening private for a confirmed private hire, which hides it from public listings and blocks public online booking ([4.19](architecture.md#419-private-hire-and-screening-visibility))
- Manager: choose a screening's seating layout, and close an area such as the circle for a quiet screening ([4.1](architecture.md#41-screenings))
- Manager, in the admin: manage ticket classes, their default prices, the ticket types and the seating layouts ([4.18](architecture.md#418-ticket-classes-membership-tiers-and-priority-booking))

## 5.2 `bookings`

Customer-facing:

- Seat selection with a short-lived hold (see [4.8](architecture.md#48-core-flow-seat-selection-and-holds))
- Going back to amend seats, ticket types, infants or food and drink before paying
- Checkout: seats, concessions and voucher or discount, then Stripe payment
- Order confirmation showing the booking reference, which works as a ticket on a phone, and booking history with cancellation requests on their profile

Staff-facing:

- Front of House: create a booking for a walk-up customer by card, with no email or account needed, using the same seat map, ticket types, concessions and discount rules as the online flow ([4.14](architecture.md#414-in-venue-bookings-staff-assisted-card-only))
- Front of House: view the bookings for a screening, for door and headcount purposes
- Front of House: view a single booking in full (seats, ticket types, concessions, payment status), to resolve a customer query at the door or by phone
- Front of House: find a booking by its reference
- Front of House: review customer cancellation requests, and approve them with a voucher or decline them, with a note required either way. Both are logged ([4.22](architecture.md#422-customer-cancellations-and-refunds))
- Manager: refund to the original card, including the exception for a cancellation the customer started, and cancel or refund any booking. Seats are released immediately and the action is logged

## 5.3 `concessions`

Customer-facing:

- Add drinks or snacks to a booking during checkout

Staff-facing:

- Manager: manage the product catalogue (add, edit or retire items and prices)
- Front of House: a prep list for each screening of what has been ordered and needs to be ready

## 5.4 `membership`

Customer-facing:

- Buy or renew a Friend membership tier, with the discount and priority booking window applying immediately ([4.18](architecture.md#418-ticket-classes-membership-tiers-and-priority-booking))
- Book a screening during its priority window, if their tier covers it
- Buy a gift voucher, for a preset or whole-pound amount within the venue's limits ([4.26](architecture.md#426-gift-vouchers))
- Enter a gift voucher code at checkout

Staff-facing:

- Front of House: view a member's tier and expiry if a query comes up
- Front of House: view a gift voucher's status and remaining balance, but not issue or refund it
- Manager: issue a voucher by hand
- Manager: refund a membership or an unspent gift voucher within 14 days of purchase, under the rule in [4.22](architecture.md#422-customer-cancellations-and-refunds). A refunded membership resets the member's tier and expiry

## 5.5 `venue`

Customer-facing:

- Static pages: About, Accessibility policy, Membership terms
- Private hire and event enquiry form

Staff-facing:

- Front of House: view and update the status of enquiries (new, contacted, booked, declined), and see which `Screening` an enquiry became ([4.19](architecture.md#419-private-hire-and-screening-visibility))
- Manager, in the admin: edit the venue settings (cancellation cutoff and fee, hold length, online sales cut-off, trailer and turnaround times, gift voucher limits, phone number, address and opening hours) ([4.23](architecture.md#423-venue-settings-and-what-is-law-versus-policy))

## 5.6 `staff`

- Manager: sales overview with revenue by day, week and month, revenue and occupancy by screening, tickets sold by type, top-selling concessions, and total vouchers redeemed
- Manager: audit log, a searchable and filterable list of refunds, cancellations and vouchers issued, with who did it and why
- This app has nothing customer-facing. It exists to support the other apps.

---

[← 4. System architecture and data model](architecture.md) · [README](../README.md) · [6. Development log and engineering phases →](development_log.md)
