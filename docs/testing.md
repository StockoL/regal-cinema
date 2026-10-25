# 7. Testing and quality assurance

This section is a testing plan, not yet a set of results. The pass and fail outcomes, screenshots and bug log can only be filled in once the application exists. It lists what I'll test and why, drawn from the edge cases and risks I found while designing the project in [section 4](architecture.md), so the testing isn't improvised afterwards.

I'm building test-first. For each journey step I write a test from its Given/When/Then scenario, watch it fail, then write the smallest code that makes it pass. The test and the code go into the same commit, so the history shows each behaviour arriving with its test. Where it's useful as evidence, a failing test is committed on its own first on the feature branch. Automated tests can't cover everything, which is why the manual checks below sit alongside them.

## 1. Manual testing matrix (boundary explorations)

The edge cases identified during design, to be checked by hand once built:

- Seat concurrency (4.8): two browser sessions selecting the same seat at nearly the same moment; a hold expiring mid-checkout; a failed payment extending the hold instead of releasing it; the hard cap on total hold time after repeated retries; changing seats mid-checkout releasing the old holds in the same step; cancelling making the seats available to a second browser at once.
- Seat release (4.2): a cancelled booking's seats can be booked again immediately, and the original `SeatBooking` rows are still present with `released_at` set.
- Payment (4.13): a webhook with an invalid signature is rejected; the same webhook delivered twice doesn't double-process; a booking fully covered by a voucher skips Stripe; a connection dropping after submission but before confirmation doesn't cause a double charge.
- Vouchers (4.4, 4.13): a voucher's balance spreads correctly across two bookings; it's only reduced on confirmed payment, not at checkout; the known limitation of two simultaneous checkouts on one code (see Known issues).
- Pricing and discounts (4.10): a booking with two adults and two children totals the right amount; infants add nothing; the membership discount applies correctly and is snapshotted on the booking; editing a screening's prices later doesn't change an existing booking's total; a lapsed membership doesn't change an old booking's discount.
- Customer cancellation (4.22): a request more than the cutoff away becomes `cancellation_requested`; a request inside the cutoff isn't offered and the phone details are shown; approval with a voucher and with a card refund both release the seats and write an audit entry; a staff member can still cancel inside the cutoff.
- Screening cancellation (4.11): cancelling a screening with several bookings gives every customer a voucher or refund and produces one audit entry per booking.
- Permissions (4.9): each sensitive action is refused for a staff member without that permission, on the server and not just in the interface; moving a permission between groups changes who can do the action without a code change.
- Membership and priority booking (4.18): a screening becomes publicly bookable at exactly its `public_onsale_at`; a member whose `priority_booking_hours` doesn't yet cover the gap is refused; a members-only screening (blank `public_onsale_at`) never opens to the public; a priority screening shows greyed out with the right label.
- Private hire (4.19): a private screening is absent from public listings and public booking is blocked; it still blocks a public screening from being scheduled in the same slot.
- TMDb integration (4.15): a search with no results; a timeout or error during the add-film flow giving a clear message; the manual path for events with no TMDb page.
- Authentication (4.16): a session's seat holds reassign to the logged-in user despite Django's session rotation on login; registering an already-used email is rejected, including the same address with different capitals; `createsuperuser` asks for an email and not a username.
- Accessibility (4.17): the seat map is fully operable by keyboard alone; a seat-hold conflict is announced by the live region; seat states are distinguishable without colour.

## 2. User story testing (behaviour-driven verification)

Each Given/When/Then scenario in [section 1](user_stories.md) is a pass or fail check. Once the application exists I'll run each scenario against the real behaviour and record the result next to it, instead of writing a separate set of test cases. The journey's success line says what must hold across all of its scenarios.

## 3. Validator testing

- HTML validated with the W3C Markup Validator, with no errors.
- CSS validated with the W3C Jigsaw CSS validator.
- Python checked against PEP 8 with a linter such as `flake8`.
- JavaScript checked with a linter such as ESLint, for the small amount of hand-written JS (mainly the seat map, 4.8).

## 4. Lighthouse testing

Run against the highest-risk pages instead of every page equally: the home and listings page, a film detail page, and the seat selection and checkout flow, since that is where most of the complexity, and so the risk of a poor score, sits. Accessibility and performance are the two categories most worth tracking given [4.17](architecture.md#417-accessibility-implementation).

## 5. Browser compatibility

Checked on current Chrome, Firefox, Safari and Edge, plus mobile Safari and Chrome. The seat map has to work on a phone-sized screen, per the acceptance criteria in section 1, not just on desktop.

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

---

[← 6. Development log and engineering phases](development_log.md) · [README](../README.md) · [8. Marketing development thoughts (future business ideas) →](future_ideas.md)
