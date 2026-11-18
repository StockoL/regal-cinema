# 7. Testing and quality assurance

This section is a testing plan, not yet a set of results. The pass and fail outcomes, screenshots and bug log can only be filled in once the application exists. It lists what I'll test and why, drawn from the edge cases and risks I found while designing the project in [section 4](architecture.md), so the testing isn't improvised afterwards.

I'm building test-first. For each journey step I write a test from its Given/When/Then scenario, watch it fail, then write the smallest code that makes it pass. The test and the code go into the same commit, so the history shows each behaviour arriving with its test. Where it's useful as evidence, a failing test is committed on its own first on the feature branch. Automated tests can't cover everything, which is why the manual checks below sit alongside them.

## 1. Manual testing matrix (boundary explorations)

The edge cases identified during design, to be checked by hand once built:

- Seat concurrency (4.8): two browser sessions selecting the same seat at nearly the same moment; a hold expiring mid-checkout; backing out of Stripe's page and coming back to find the seats still held; the hard cap on total hold time after repeated amendments; the holds extending to cover the Stripe session when the customer chooses Pay; changing seats mid-checkout releasing the old holds in the same step; cancelling making the seats available to a second browser at once; booking refused once online sales have closed.
- Pending bookings (4.2, 4.8): the basket (ticket types, infants, food and drink, voucher) survives going back from payment; an abandoned pending booking disappears with its holds, without touching any paid booking.
- Seating (4.1): a closed area's seats can't be selected and don't count towards capacity; a screening's layout can't be changed once it has a booking; a wheelchair space in the circle is refused; a stalls layout without a wheelchair space is refused.
- Booking rules (4.1, 4.2): infants, or a Child ticket, without a ticket that doesn't need an adult are refused; infants on a 15 or 18 film are refused; a ticket type whose maximum age is below the film's minimum age isn't offered; a ticket type that needs proof shows the reminder at checkout and on the confirmation. A Companion ticket without a full-fare ticket is refused, and so are more companions than full-fare tickets; picking a wheelchair space offers the seats beside it first.
- Food and drink (4.3): an order attaches to the pending booking and is paid in the same Checkout Session; the seat choice is hidden when seat delivery is off for the screening; ordering is refused inside the food cutoff; an item marked sold out disappears from the menu and comes back when switched on; an age-restricted item shows the ID note on the order check and the confirmation; the food step works with JavaScript off; each status change on the service list writes an audit entry; cancelling a booking cancels its food and the voucher covers the whole total.
- Check-in (4.2): a booking can be found by reference or by email; checking in stamps the booking with the staff member and time and writes an audit entry; checking in twice is refused.
- Seat release (4.2): a cancelled booking's seats can be booked again immediately, and the original `SeatBooking` rows are still present with `released_at` set.
- Payment (4.13): a webhook with an invalid signature is rejected; the same webhook delivered twice doesn't double-process; a booking fully covered by a voucher skips Stripe; a connection dropping after paying but before the customer gets back doesn't cause a double charge; returning while a Checkout Session is still open reuses that session; a customer back before the webhook sees the confirming page; a payment that succeeds after the seats were lost and resold is refunded automatically.
- Vouchers (4.4, 4.13, 4.26): a voucher's balance spreads correctly across two bookings; it's only reduced on confirmed payment, not at checkout; a purchased voucher can't be spent until the success webhook has activated it, and a repeated webhook doesn't activate or email it twice; a voucher can't be used after its one-year expiry; refunding a part-voucher booking returns the card amount to the card and restores the voucher amount; the known limitation of two simultaneous checkouts on one code (see Known issues).
- Pricing and discounts (4.10): a booking with two adults and two children totals the right amount; infants add nothing; the ticket and food and drink discounts apply to their own lines and are both snapshotted on the booking; editing a screening's prices later doesn't change an existing booking's total; a lapsed membership doesn't change an old booking's discount.
- Customer cancellation (4.22): a request more than the cutoff away becomes `cancellation_requested`; a request inside the cutoff isn't offered and the phone details are shown; approval gives a voucher minus the venue's cancellation fee, releases the seats and writes an audit entry; a Manager's card refund does the same; declining returns the booking to `paid` and is logged; a staff member can still cancel inside the cutoff.
- Screening cancellation (4.11): cancelling a screening with several bookings gives every customer a voucher or refund, with no fee, and produces one `Cancellation` and one audit entry per booking; the cancelled screening is absent from the public listing, and an old link to it shows the cancelled page.
- Permissions (4.9): each sensitive action is refused for a staff member without that permission, on the server and not just in the interface; moving a permission between groups changes who can do the action without a code change; a sensitive action taken in the Django admin writes an audit entry too.
- Membership and priority booking (4.18): a screening becomes publicly bookable at exactly its `public_onsale_at`; a member whose `priority_booking_hours` doesn't yet cover the gap is refused; a members-only screening (blank `public_onsale_at`) never opens to the public; a priority screening shows greyed out with the right label; a membership refunded within 14 days, with no booking having used it, resets the profile's tier and expiry; an unspent gift voucher can be refunded within 14 days.
- Venue settings (4.23): `get_settings()` returns the migration's defaults on a fresh database; a change in the admin is used straight away; changing `withdrawal_days` changes the refund window without a code change.
- Data deletion (4.21): deleting a customer's account leaves their bookings and the sales figures in place, with no user attached.
- Private hire (4.19): a private screening is absent from public listings and public booking is blocked; it still blocks a public screening from being scheduled in the same slot.
- TMDb integration (4.15): a search with no results; a timeout or error during the add-film flow giving a clear message; the manual path for events with no TMDb page.
- Authentication (4.16): a session's seat holds reassign to the logged-in user despite Django's session rotation on login; registering an already-used email is rejected, including the same address with different capitals; `createsuperuser` asks for an email and not a username.
- Abuse controls (4.29): going over each rate limit gives the 429 page; a staff account is asked for its second step and a customer isn't; the production settings pass Django's deployment check.
- Reports (4.28): attendance and occupancy match a count by hand on seeded data; each Excel download holds the same rows as its page.
- Personal data (4.30): the download holds the account and its bookings and nothing about anyone else; a deleted account leaves its bookings in place with no user.
- Promo codes (4.4, 4.10): each eligibility rule refuses with its own plain reason; usage counts include unexpired pending bookings; a ticket never gets both a promo and a membership discount, only the lower price.
- Stock (4.3): available stock matches the ledger less paid and unexpired pending orders; two customers racing for the last item can't both have it.
- Email (4.2): a confirmation is written to the outbox with its booking and sent after the commit; a failed send is retried up to five times; a booking never gets two confirmations.
- Refunds (4.2, 4.32): a part refund makes one row for the snapshotted amount; a failed refund is retried with the same idempotency key and never pays twice; the amount refunded is the total of succeeded rows.
- VAT (4.10): net, VAT and gross worked out per line add up to the report's totals with no penny lost to rounding.
- Reconciliation (4.28): the report's totals equal the sum of the bookings it covers.
- Venue settings (4.23): with online sales paused, no new hold starts but a pending booking can still be paid; a session can't hold more seats than the ticket limit.
- Till reconciliation (4.14): a closed day can't be edited, and closing it writes an audit entry.
- Membership (4.4): a free ticket goes on the cheapest eligible ticket, counts only once paid, and comes back when the booking is cancelled.
- Backups (4.31): a dump restores into an empty database, and the row counts match the original.
- Query counts: `assertNumQueries` fixes the number of queries on the seat map, the showtimes page, the service list and each report, and the numbers are recorded here. The seat map's occupancy is two queries whatever the size of the room (4.33).
- Caching (4.33): a listing is served from the cache within 60 seconds, a seat's availability never is, and a booking or staff page sends `private, no-store`.
- Service list refresh (4.3): an unchanged list answers "not modified", and a changed one keeps the scroll position and announces the new count.
- Accessibility (4.17): the seat map is fully operable by keyboard alone, with one tab stop and arrow keys between seats; a seat-hold conflict is announced by the live region; seat states are distinguishable without colour; every seat button is at least 24 by 24 CSS pixels.

## 2. User story testing (behaviour-driven verification)

Each Given/When/Then scenario in [section 1](user_stories.md) is a pass or fail check. Once the application exists I'll run each scenario against the real behaviour and record the result next to it, instead of writing a separate set of test cases. The journey's success line says what must hold across all of its scenarios.

## 3. Validator testing

- HTML validated with the W3C Markup Validator, with no errors.
- CSS validated with the W3C Jigsaw CSS validator.
- Python checked against PEP 8 with a linter such as `flake8`.
- JavaScript checked with a linter such as ESLint, for the small amount of hand-written JS (mainly the seat map, 4.8).
- Dependencies checked for known vulnerabilities with `pip-audit`, with the output recorded here (4.29).

## 4. Lighthouse testing

Run against the highest-risk pages instead of every page equally: the home and listings page, a film detail page, and the seat selection and checkout flow, since that is where most of the complexity, and so the risk of a poor score, sits. Accessibility and performance are the two categories most worth tracking given [4.17](architecture.md#417-accessibility-implementation).

The budget, on mobile once warm, for the film page, a screening's seats page and the seat map (4.33): 90 or more in every category, largest contentful paint at or under 2.5 seconds and layout shift at or under 0.1. An automated axe check runs over the same pages in a development-only browser test, and its results go here.

## 5. Browser compatibility

Checked on current Chrome, Firefox, Safari and Edge, plus mobile Safari and Chrome. The seat map has to work on a phone-sized screen, per the acceptance criteria in section 1, not just on desktop.

Real devices: an iPhone in Safari on iOS 17.4 or later, an Android phone in Chrome, and a 320 pixel wide window. The phone ticket's QR code is scanned from a second phone.

## 6. Responsiveness testing

Checked at a handful of reference widths instead of only conventional breakpoints, consistent with the fluid layout approach in [section 3](ux_design.md). The point of that approach is that it shouldn't only work at the widths a media query targets. Also checked at 200% browser zoom and with the OS large-text setting on, per [4.17](architecture.md#417-accessibility-implementation).

## 7. Automated end-to-end testing

Priority order, highest risk first: the seat hold, checkout and payment flow (4.8, 4.13), including concurrent holds, amending and releasing seats; the authentication flow (4.16), including the session rotation edge case; and the discount, voucher and ticket-type pricing order (4.10). Django's test framework covers model and view logic. Anything that has to exercise the seat map's JavaScript needs a browser-level tool such as Playwright.

## 8. Bugs fixed (sprint log)

Real bugs found and fixed during development, newest last. Each one names the test that now guards against it coming back.

### Bug 1: overlapping screenings got past forms (25 October 2026)

What happened: a form for creating or editing a screening accepted one that overlapped another on the same screen. The database constraint would then have rejected the save with an error page, instead of the form showing the overlap message from journey 12, "Overlap rejected".

How I found it: while planning the admin for screenings. The model tests passed because they call `full_clean()` with nothing left out, which isn't how a form calls it.

Cause: a form leaves out every field it doesn't show, and Django skips any constraint that refers to a left-out field. The overlap constraint (4.1) refers to `ends_at`, which is worked out on save and never typed in, and to `cancelled_at` in its "not cancelled" condition. Staff never type either in, so the check never ran.

Fix: `Screening.validate_constraints()` keeps both fields in the check. That's safe because `clean()` sets `ends_at` just before it, and `cancelled_at` holds its saved value. My first fix only kept `ends_at`, so the condition was still skipped and the test still failed. I'd committed it before noticing, so the history shows both commits: [`d9afab8`](https://github.com/StockoL/regal-cinema/commit/d9afab898280d0a0859e85cc7a591315fda77185) (incomplete) and [`b761b6c`](https://github.com/StockoL/regal-cinema/commit/b761b6cf4c5d262fe4c4f1e58430a9dbe265be2d) (the working fix). Since then I only commit once the test runner's exit code says the whole suite passed.

Test: `test_a_form_reports_an_overlap_instead_of_crashing` in `screenings/tests/test_screenings.py` submits an overlapping screening through a form and checks the form is invalid with the overlap message.

## 9. Known issues

Limitations I've accepted on purpose, as opposed to things yet to be discovered:

- Voucher race condition (4.13): a voucher's balance isn't held the way a seat is, so two simultaneous checkouts on one code have a narrow window in which both could succeed. This is unlikely and low in severity given a voucher has to be typed in, and solving it would need a second holding mechanism like `SeatHold`.
- No membership auto-renewal (4.18): a lapsed membership must be repurchased by hand. Automatic recurring billing was out of scope.
- No dual authorisation for large refunds (4.12): one person with the refund permission can refund any amount. A second sign-off is a future consideration.
- Reporting queries run against the primary database (4.12): at very high volume the dashboard queries could compete with customer traffic. A read replica is a future consideration and isn't needed at this scale.
- Cancellation inside the cutoff is by phone (4.22): there's no online route inside the window, by design.
- Older iPhones and iPads aren't supported: LooseLeaf UI needs Chrome 117, Safari 17.4 or Firefox 129 or later, so on Apple devices that means iOS and iPadOS 17.4 or later. Whether that's acceptable for a cinema's audience is still to be decided.

## 10. Failure modes

Each way a payment can go wrong has a named test, run against the fake payment provider (4.27, 4.32). The names are planned and get filled in as the tests are written.

| Failure | Expected behaviour | Test |
| :------ | :----------------- | :--- |
| A payment arrives after the hold expired and the seats were sold | Refunded automatically, and the customer is told (4.13) | `test_a_payment_after_the_seats_went_is_refunded` |
| The webhook arrives before the customer is back from Stripe | Confirmed once, and the success page shows the booking | `test_a_webhook_before_the_redirect_confirms_once` |
| The customer presses Pay twice | One Checkout Session, and the second submit is ignored | `test_a_double_submit_makes_one_session` |
| A second payment for a booking already paid | The second payment is refunded and listed for staff | `test_a_second_payment_is_refunded` |
| The card is declined | Stripe shows it, and the booking stays pending | `test_a_declined_card_leaves_the_booking_pending` |
| Stripe times out | Nothing is confirmed, and the customer can try again | `test_a_timeout_confirms_nothing` |
| The same webhook arrives twice | Handled once, through `StripeEvent` | `test_a_repeated_webhook_changes_nothing` |
| The webhook arrives late | Confirmed when it arrives, or earlier by the scheduled check | `test_a_late_webhook_confirms_once` |
| The webhook never arrives | `reconcile_pending` or Check with Stripe confirms it | `test_a_missing_webhook_is_recovered` |
| Confirming fails halfway | Nothing partial is saved | `test_a_failed_confirmation_saves_nothing` |
| A refund fails | Stored as failed, retried by the scheduled job with the same key, and listed for staff | `test_a_failed_refund_is_retried_once` |
| An email can't be sent | The booking stands, the email is retried, and after five tries it's listed for staff | `test_a_failed_email_is_retried_then_listed` |

## 11. Load testing

A Locust script, a development dependency only, simulates a popular on-sale: many visitors browsing, opening the seat map and holding seats on one screening at once. The run records the 95th percentile response time and the error rate here, and the check that matters most: zero seats sold twice.

---

[← 6. Development log and engineering phases](development_log.md) · [README](../README.md) · [8. Marketing development thoughts (future business ideas) →](future_ideas.md)
