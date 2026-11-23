# 7. Testing and quality assurance

This covers the automated tests, the checks I ran on the code, the manual tests, and the bugs found along the way. Each check says what I used, what it found and whether that's resolved. The project is still being built, so where a check hasn't been run yet it says so instead of giving a result, and its row fills in when it's run.

The automated tests and the checks in [section 1](#1-checks-run-findings-and-how-each-was-resolved) were run on 19 November 2026 at `92741de`, and flake8 and pip-audit at `4bb9454` once they were installed, on a local copy of the site with the demo seat plan from `seed_seats`. The manual results so far come from checking each feature in a browser as I built it, recorded with screenshots in the [development log](development_log.md), and each row links to its entry. A full manual run of every row, in Google Chrome on Windows and on real devices, is planned for the testing pass in Phase 7.

I'm building test-first. For each journey step I write a test from its Given/When/Then scenario, watch it fail, then write the smallest code that makes it pass. The test and the code go into the same commit, so the history shows each behaviour arriving with its test. Where it's useful as evidence, a failing test is committed on its own first on the feature branch.

## Contents

- [1. Checks run, findings and how each was resolved](#1-checks-run-findings-and-how-each-was-resolved)
- [2. HTML and CSS validation](#2-html-and-css-validation)
- [3. Lighthouse scores](#3-lighthouse-scores)
- [4. Automated tests](#4-automated-tests)
  - [Query counts](#query-counts)
  - [Failure modes](#failure-modes)
  - [Load testing](#load-testing)
- [5. Manual tests](#5-manual-tests)
  - [Journeys as checks](#journeys-as-checks)
  - [5.1 Accounts](#51-accounts)
  - [5.2 Browsing](#52-browsing)
  - [5.3 Choosing and holding seats](#53-choosing-and-holding-seats)
  - [5.4 Paying](#54-paying)
  - [5.5 Staff and the admin](#55-staff-and-the-admin)
  - [5.6 Edge cases still to run](#56-edge-cases-still-to-run)
- [6. Responsiveness, usability and the keyboard](#6-responsiveness-usability-and-the-keyboard)
  - [Widths and browsers](#widths-and-browsers)
  - [Real devices](#real-devices)
- [7. Bugs found and fixed](#7-bugs-found-and-fixed)
  - [The overlap bug in full](#the-overlap-bug-in-full)
  - [Known issues](#known-issues)
- [8. Deployment check](#8-deployment-check)

## 1. Checks run, findings and how each was resolved

| Check | What I used | What it found on 19 November | Resolved? |
| ----- | ----------- | ---------------------------- | --------- |
| Automated tests | `python manage.py test` (Django's test runner, with the fake payment provider swapped in by `regal.test_runner`) | 444 tests, all passing, at `92741de` ([section 4](#4-automated-tests)) | Nothing to resolve |
| Deployment settings | `python manage.py check --deploy` with `DEBUG` off and Render's host name | Two warnings: HSTS isn't set for every subdomain, and the site isn't on the browsers' HSTS preload list. One check is silenced on purpose, `security.W008`, Django's own HTTPS redirect, because Render redirects plain HTTP to HTTPS itself ([dev log, 25 October](development_log.md#25-october-2026-first-deploy)) | Both warnings left as they are on purpose: the site is on `onrender.com`, which Render shares between all its customers, so its subdomains aren't mine to make promises about ([dev log, 9 November](development_log.md#9-november-2026-deploying-the-accounts-and-a-500)). The error reported at the first deploy, the console email backend, went with the email setup on 9 November |
| Migrations | `python manage.py makemigrations --check --dry-run` | No changes detected | Nothing to resolve |
| Leftover debugging | `git grep` for `print(`, `breakpoint(`, `pdb`, `TODO` and `FIXME` in the Python, JavaScript and templates, outside migrations | None | Nothing to resolve |
| Files that shouldn't be tracked | `git ls-files`, searched for `.env`, database files, keys, a virtual environment and uploaded media; `git grep` for Stripe secret keys and webhook secrets | None tracked, and no keys in the code | Nothing to resolve |
| Python style | flake8 7.4.1 with the settings in `.flake8` (PEP 8's 79-character lines, with the virtual environment, migrations and collected static files left out), from `requirements-dev.txt` | No findings at `4bb9454`. The first run found six lines over 79 characters, four of them Django's generated password validator paths, and a variable named `l` | Fixed in `4bb9454`, with the suite still passing |
| HTML validation | The W3C's Nu HTML Checker, every page ([section 2](#2-html-and-css-validation)) | Not run yet | |
| CSS validation | The W3C CSS Validator, on the project's own stylesheets ([section 2](#2-html-and-css-validation)) | Not run yet | |
| JavaScript | ESLint with its recommended rules, over `static/js/` | Not run yet | |
| Dependencies | pip-audit 2.10.0, from `requirements-dev.txt`, over `requirements.txt` and `requirements-dev.txt` (4.29) | No known vulnerabilities in either, at `4bb9454` | Nothing to resolve |
| Lighthouse | Lighthouse in Chrome, mobile, on the film page, a screening's seats page and the seat map ([section 3](#3-lighthouse-scores)) | Not run yet | |
| Widths and browsers | Each page at 320, 375, 768, 1024 and 1280 pixels in Chromium, Firefox and WebKit ([section 6](#6-responsiveness-usability-and-the-keyboard)) | Not run yet as a recorded check. Looking at the seat map in a browser on 9 November found the page 992 pixels wide on a phone ([section 7](#7-bugs-found-and-fixed)) | That one fixed on 9 November |

[↑ Back to contents](#contents)

## 2. HTML and CSS validation

Not run yet. Every page goes through the W3C's Nu HTML Checker, aiming for no errors, and the project's own stylesheets through the W3C CSS Validator. LooseLeaf UI's stylesheet is my separate library, checked in its own project, so the results here cover Regal's blocks in `static/css/`. Anything the validators don't know yet, such as cascade layers, is listed with the browsers that support it rather than removed.

[↑ Back to contents](#contents)

## 3. Lighthouse scores

Not run yet. It runs against the highest-risk pages instead of every page equally: the home and listings page, a film page, and the seat selection and checkout flow, since that's where most of the complexity, and so the risk of a poor score, sits. Accessibility and performance are the two categories most worth tracking, given [4.17](architecture.md#417-accessibility-implementation).

The budget, on mobile once warm, for the film page, a screening's seats page and the seat map (4.33): 90 or more in every category, largest contentful paint at or under 2.5 seconds and layout shift at or under 0.1. An automated axe check runs over the same pages in a development-only browser test, and its results go here.

[↑ Back to contents](#contents)

## 4. Automated tests

The suite has 444 tests, run on 19 November 2026 at `92741de`; all passed. The test runner swaps in the fake payment provider whatever the environment says, so the suite never calls Stripe, and a test checks that it does. The two concurrency tests open two real database connections, which is one reason the project runs on PostgreSQL even on my own machine ([dev log, 9 November](development_log.md#9-november-2026-the-double-booking-spike)).

| File | Tests | What it covers |
| ---- | ----- | -------------- |
| `accounts/tests/test_admin.py` | 3 | The user list, editing a user and adding one by email in the admin |
| `accounts/tests/test_models.py` | 15 | The email-login user: no username, addresses stored in lower case and unique in any case, superusers, verification, and the inactive system user nobody can log in as |
| `accounts/tests/test_views.py` | 43 | Registering, the duplicate and password checks, returning to a booking after registering and never to another site, logging in and out, the menu for visitors and customers, password reset, the verification email and its reminder |
| `bookings/tests/test_admin.py` | 3 | The bookings list, and Mark as paid, including a booking that lost a seat |
| `bookings/tests/test_basket.py` | 12 | The booking rules: a seat needed, children and infants with a ticket that doesn't need an adult, no cap on infants, no infants on a 15 film, and companions with a full-price ticket and never outnumbering them |
| `bookings/tests/test_bookings.py` | 11 | A new booking, its phone-readable reference without 0, O, 1, I or L, one Checkout Session per booking, the deletion policy, and a pending booking's holds |
| `bookings/tests/test_concurrency.py` | 2 | Two customers holding the same seat at the same instant, and a seat taken between the check and the insert |
| `bookings/tests/test_holds.py` | 5 | One hold per seat per screening, expired holds left out, and a hold belonging to its user |
| `bookings/tests/test_login_handover.py` | 3 | Held seats and their booking moving to the account at login, through the real login form, and someone else's booking left alone |
| `bookings/tests/test_payment_views.py` | 15 | The checkout page's total, test-card warning and Pay button, logging in to pay, going to Stripe's page with the right return links, seats whose hold ran out, coming back unpaid, the confirming page, a paid booking's seats and a late payment's refund message |
| `bookings/tests/test_pricing.py` | 9 | Discounts per ticket in whole pence, rounding half a penny up and just under it down, and the limits |
| `bookings/tests/test_refunds.py` | 2 | A refund row starting pending, and a booking with a refund protected from deletion |
| `bookings/tests/test_seat_bookings.py` | 3 | A sold seat keeping its price and VAT rate, one live sale per seat, and a released seat sold again |
| `bookings/tests/test_services.py` | 37 | Holding seats all or none, closed areas, seats out of use and sold seats, starting, amending and cancelling a booking, the 30-minute cap, confirming a booking once and saving nothing when a seat is lost, starting a payment, the same session for a second click and a new one after expiry, and releasing seats |
| `bookings/tests/test_stripe_events.py` | 2 | Each Stripe event recorded once |
| `bookings/tests/test_views.py` | 55 | The seats page: private, cancelled and closed screenings, the seat map's grid, names, states and key, choosing seats and ticket types without JavaScript, a seat taken meanwhile, holding, changing and releasing seats, and the arrow-key markup |
| `bookings/tests/test_webhook.py` | 12 | The webhook: its address, a paid session confirming its booking and recording the payment, a repeated or forged event, an unpaid or expired session, a session for something else, a payment after the seats went, and a refund that fails |
| `payments/tests/test_fake.py` | 10 | The fake provider: sessions, the same idempotency key, expiry, signed and forged webhooks, refunds and a refund told to fail |
| `payments/tests/test_stripe_provider.py` | 11 | The Stripe provider against a stand-in client: test-mode keys only, the session it asks for, looking one up, refunds and Stripe's error kept, a real webhook signature from a made-up secret, and the test runner keeping the suite off Stripe |
| `regal/tests.py` | 14 | The health page, the stylesheets and their layers, every token defined and text contrast against WCAG AA, the email settings, and checking kept database connections |
| `screenings/tests/test_admin.py` | 11 | The admin pages for screens, layouts and screenings, a layout without a wheelchair space refused, the price table filled when a screening is added, and the overlap message |
| `screenings/tests/test_film_page.py` | 19 | The film page: rating and advice, photo ID and under 2s notes, the stairs note, a trailer link that never autoplays, the day's times, and films not found |
| `screenings/tests/test_films.py` | 22 | Films: slugs, the TMDb id, BBFC ratings, runtimes, which ticket types each rating allows, and infants by rating |
| `screenings/tests/test_layouts.py` | 26 | Seating layouts, fixed and layout seats, grid positions, wheelchair spaces only in the stalls, a screening's seats and capacity, and closed areas |
| `screenings/tests/test_listings.py` | 7 | What the public sees: never a private, cancelled or retired film's screening, one day in the venue's time, and online sales closing |
| `screenings/tests/test_prices.py` | 6 | A price per ticket type per screening, in pence, and the deletion policy |
| `screenings/tests/test_screenings.py` | 18 | When a screening ends, the no-overlap rule with trailers and turnaround, through a form as well as the model, and cancelling |
| `screenings/tests/test_screens.py` | 15 | Screens, capacity, unique seats, and seat labels |
| `screenings/tests/test_seed.py` | 10 | The demo seat plan: its layouts, circle, wheelchair spaces with companion seats, tables, and running it again |
| `screenings/tests/test_services.py` | 4 | Filling a screening's price table from its ticket class |
| `screenings/tests/test_tickets.py` | 18 | Ticket classes and types, the VAT rate, the rule flags, and the six seeded types |
| `screenings/tests/test_views.py` | 21 | The base template's landmarks, skip link and footer, and What's on by day |

To run them, see [Local deployment](../README.md#local-deployment) in the README.

### Query counts

Fixed with `assertNumQueries`, so a page that starts querying per seat or per row fails its test (4.33).

| Page | Queries | What they are | Test |
| ---- | ------- | ------------- | ---- |
| A screening's seat map, for a visitor | 6 | The screening, the venue settings for the online cut-off, any booking of theirs, the closed areas, live holds and live sales. The room's seats come from the cache, and nearly thirty times as many seats make no more queries | `test_the_seat_map_page_makes_a_fixed_number_of_queries`, `test_a_bigger_room_makes_no_more_queries` |
| A layout's seats, cached | 0 | Served from the cache until a seat or layout of the screen changes | `test_the_second_call_makes_no_query` |
| My bookings | 5 | The session, the customer, their bookings with each screening, film and screen, every seat with its ticket type, and the venue settings for the cancellation cutoff | `test_more_bookings_make_no_more_queries` |

### Failure modes

Each way a payment can go wrong has a named test, run against the fake payment provider (4.27, 4.32). Where a planned name was written differently when the test arrived, the table gives the real one.

| Failure | Expected behaviour | Test | State |
| ------- | ------------------ | ---- | ----- |
| A payment arrives after the hold expired and the seats were sold | Refunded automatically, and the customer is told (4.13) | `test_a_payment_after_the_seats_went_is_refunded` | Written |
| The same webhook arrives twice | Handled once, through `StripeEvent` | `test_a_repeated_webhook_changes_nothing` | Written |
| A forged webhook | Refused with a 400, and nothing recorded | `test_a_forged_webhook_is_refused` | Written |
| The customer presses Pay twice | One Checkout Session | `test_paying_again_returns_the_same_session` | Written |
| A session expires unpaid | Nothing is booked, and paying again gets a new session | `test_a_session_that_expired_unpaid_books_nothing`, `test_paying_after_the_session_expired_gets_a_new_one` | Written |
| A refund fails | Stored as failed with the provider's reason | `test_a_refund_that_fails_is_kept_with_its_reason` | Written. Retrying it waits for the scheduled job |
| Confirming fails halfway | Nothing partial is saved | `test_a_lost_seat_saves_nothing` | Partly: a lost seat saves nothing; a failure forced halfway is planned as `test_a_failed_confirmation_saves_nothing` |
| The webhook arrives before the customer is back from Stripe | Confirmed once, and the confirming page shows the booking | `test_a_webhook_before_the_redirect_confirms_once` | Planned |
| A second payment for a booking already paid | The second payment is refunded against itself, and the booking left as it was | `test_a_second_payment_is_refunded` | Written. Listing it for staff waits for the needs-attention page |
| The card is declined | Stripe shows it and lets the customer try another card; the booking stays pending with its seats | `test_a_declined_card_leaves_the_booking_pending` | Written |
| Stripe times out | Nothing is saved, and the customer is back on checkout with their seats held and a message to try again | `test_a_timeout_confirms_nothing` | Written |
| The webhook arrives late | Confirmed when it arrives, or earlier by the scheduled check | `test_a_late_webhook_confirms_once` | Planned |
| The webhook never arrives | `reconcile_pending` or Check with Stripe confirms it | `test_a_missing_webhook_is_recovered` | Planned |
| An email can't be sent | The booking stands, the email is retried, and after five tries it's listed for staff | `test_an_email_that_cant_be_sent_leaves_the_booking_paid`, `test_after_five_tries_it_is_marked_failed` | Written. The retries wait for the scheduled job, and the list for the needs-attention page |

### Load testing

Not run yet. A Locust script, a development dependency only, simulates a popular on-sale: many visitors browsing, opening the seat map and holding seats on one screening at once. The run records the 95th percentile response time and the error rate here, and the check that matters most: zero seats sold twice.

[↑ Back to contents](#contents)

## 5. Manual tests

Grouped by feature, in the order a customer meets them; each row keeps its number. Every row also has automated tests in [section 4](#4-automated-tests), so the manual run checks what a test can't see: the layout, the wording, the keyboard and real devices. A result with a date was seen in a browser on that day and has its screenshots in the linked development log entry. "Not run yet" means just that.

### Journeys as checks

Each Given/When/Then scenario in the [user stories](user_stories.md) is a pass or fail check in its own right. The rows below are written from them, and the journey's success line says what must hold across all of its scenarios.

### 5.1 Accounts

Registering, logging in and out, and the emails (journey 4).

| ID | Feature | Steps | Expected | Result |
| -- | ------- | ----- | -------- | ------ |
| <a id="m01"></a>M01 | Register | Register, give an email address and a password twice | Logged in straight away, with nothing asked but the email and password | Pass, 9 November: the page asks for the email and the password twice ([dev log](development_log.md#9-november-2026-registering-logging-in-and-out)) |
| <a id="m02"></a>M02 | Register with errors | Submit with a short password and a confirmation that doesn't match | Each error under its own field, with one plain password hint | Pass, 9 November, after replacing Django's list of four rules with one hint ([dev log](development_log.md#9-november-2026-registering-logging-in-and-out)) |
| <a id="m03"></a>M03 | Wrong password | Log in with a wrong password | A plain message that doesn't claim the email is case-sensitive | Pass, 9 November, after writing my own message ([dev log](development_log.md#9-november-2026-registering-logging-in-and-out)) |
| <a id="m04"></a>M04 | The menu | Open the menu as a visitor and as a customer, on a phone and at desktop width | Log in and Register for a visitor, a Log out button for a customer | Pass, 9 November ([dev log](development_log.md#9-november-2026-registering-logging-in-and-out)) |
| <a id="m05"></a>M05 | Password reset | Ask for a reset, follow the link, then try the link again | The same page whether or not the address has an account; a used link offers a new one | Pass, 9 November ([dev log](development_log.md#9-november-2026-password-reset-and-verification)) |
| <a id="m06"></a>M06 | Verification | Register, see the reminder, send the link again, follow it | The reminder on every page until confirmed; "We've sent a new link"; then confirmed | Pass, 9 November, after spacing the reminder away from the header ([dev log](development_log.md#9-november-2026-password-reset-and-verification)) |
| <a id="m07"></a>M07 | Register to pay | Hold seats as a visitor, choose create an account on the checkout page, register | Back on the checkout page with the seats still held | Not run yet |

### 5.2 Browsing

What's on and the film page (journey 1).

| ID | Feature | Steps | Expected | Result |
| -- | ------- | ----- | -------- | ------ |
| <a id="m08"></a>M08 | What's on by day | Open the home page, choose another day, then a day with nothing on | Films grouped with their times; the chosen day marked; "Nothing is showing" on an empty day | Pass, 4 November, on a phone and at desktop width ([dev log](development_log.md#4-november-2026-browsing-by-day-and-the-film-page)) |
| <a id="m09"></a>M09 | Film page | Open a 15-rated film and one with no rating yet | The rating with its advice, the photo ID, under 2s and stairs notes; "Rating to be confirmed" | Pass, 4 November ([dev log](development_log.md#4-november-2026-browsing-by-day-and-the-film-page)) |
| <a id="m10"></a>M10 | A cancelled screening | Follow an old link to a cancelled screening | A plain page saying it was cancelled, with a way back to what's on | Pass, 9 November ([dev log](development_log.md#9-november-2026-choosing-seats-without-javascript)) |
| <a id="m11"></a>M11 | Online sales closed | Open the seats page for a screening that has started | The box office number instead of the seats | Pass, 9 November ([dev log](development_log.md#9-november-2026-choosing-seats-without-javascript)) |

### 5.3 Choosing and holding seats

The seats page, the seat map and holds (journey 2).

| ID | Feature | Steps | Expected | Result |
| -- | ------- | ----- | -------- | ------ |
| <a id="m12"></a>M12 | Seats without JavaScript | With JavaScript off, open a screening's seats | Every seat a checkbox, grouped by area and row; held seats marked sold; the stairs note | Pass, 9 November ([dev log](development_log.md#9-november-2026-choosing-seats-without-javascript)) |
| <a id="m13"></a>M13 | Nothing chosen | Continue with no seat ticked | "Choose at least one seat" | Pass, 9 November ([dev log](development_log.md#9-november-2026-choosing-seats-without-javascript)) |
| <a id="m14"></a>M14 | A broken booking rule | Choose three Child tickets and nothing else | Refused in words, with the choices kept | Pass, 9 November ([dev log](development_log.md#9-november-2026-choosing-seats-without-javascript)) |
| <a id="m15"></a>M15 | A seat taken meanwhile | Choose seats, have another browser hold one, then continue | Back on the seats with that seat named and the others still ticked | Pass, 9 November ([dev log](development_log.md#9-november-2026-choosing-seats-without-javascript)) |
| <a id="m16"></a>M16 | Hold, change and release | Hold seats, change them from checkout, then cancel | The held seats and when the hold ends; changes keep the booking; "Your seats have been released" | Pass, 9 November ([dev log](development_log.md#9-november-2026-choosing-seats-without-javascript)) |
| <a id="m17"></a>M17 | The seat map | Open a screening's seats with JavaScript on | Each area a grid under the screen; sold, chosen, wheelchair and closed seats each shown without relying on colour, with a key in words | Pass, 9 November ([dev log](development_log.md#9-november-2026-the-seat-map)) |
| <a id="m18"></a>M18 | A closed circle | Open a screening with the circle closed | Every circle seat outside section | Pass, 9 November ([dev log](development_log.md#9-november-2026-the-seat-map)) |
| <a id="m19"></a>M19 | The keyboard | Tab to the map, move with the arrow keys, Home and End, choose with Enter, Tab out | One tab stop; Down runs on from the stalls into the circle; Enter chooses; Tab leaves to Continue | Pass, 9 November, with the key presses recorded ([dev log](development_log.md#9-november-2026-the-seat-map)) |
| <a id="m20"></a>M20 | The seat map on a phone | Open the seat map at 390 pixels | The page no wider than the screen; each area scrolls sideways in its own frame | Pass, 9 November, after fixing the page running to 992 pixels ([dev log](development_log.md#9-november-2026-the-seat-map)) |
| <a id="m21"></a>M21 | Sold seats | Mark a booking paid, then open the same screening's seats | Its seats crossed out as sold | Pass, 19 November ([dev log](development_log.md#19-november-2026-selling-the-seats)) |

### 5.4 Paying

Paying with Stripe Checkout in test mode (journey 6).

| ID | Feature | Steps | Expected | Result |
| -- | ------- | ----- | -------- | ------ |
| <a id="m22"></a>M22 | Log in to pay | Hold seats as a visitor and open the checkout page | Log in or create an account offered instead of Pay; after logging in, the same seats still held | Partly, 19 November: a visitor is offered log in or create an account, with no Pay button ([dev log](development_log.md#19-november-2026-paying-with-stripe-checkout)). Logging in with seats held not run yet |
| <a id="m23"></a>M23 | Go to Stripe | As a customer, press Pay | Stripe's test page with the film, the number of tickets and the total from the checkout page | Partly, 19 November: Stripe's page showed "Paddington in Peru, 2 tickets" and £18.00. It also offered Klarna, Revolut Pay, Amazon Pay and Link, which have to be switched off in the Stripe dashboard ([Known issues](#known-issues)) |
| <a id="m24"></a>M24 | Pay with the test card | Pay with 4242 4242 4242 4242, with `stripe listen` forwarding the webhook | "We're confirming your payment", then "Booking confirmed" with the reference and seats; the listener shows the event answered 200 | Not run yet: waits until screenings are created through the real flow ([Known issues](#known-issues)) |
| <a id="m25"></a>M25 | Back out of Stripe | Press Pay, then the back link on Stripe's page | "No payment was taken", with the seats still held | Partly, 19 November: the checkout page Stripe's back link returns to says "No payment was taken" with the seats held ([dev log](development_log.md#19-november-2026-paying-with-stripe-checkout)). Pressing the back link on Stripe's own page not run yet |
| <a id="m26"></a>M26 | Test-card warning | Open the checkout page | The warning never to use a real card, with the test card number | Pass, 19 November ([dev log](development_log.md#19-november-2026-paying-with-stripe-checkout)) |
| <a id="m31"></a>M31 | A signed webhook | Send the local site a `checkout.session.completed` event signed with the real webhook secret, for a pending booking and for one whose seat was sold first | The first booking confirmed; the second marked refunded, its refund sent to Stripe and its result stored | Pass, 19 November: both answered 200; the first was paid with its two seats; the second was refunded, and Stripe's test API refused the made-up payment, so the refund was stored as failed with "No such payment_intent" ([dev log](development_log.md#19-november-2026-paying-with-stripe-checkout)) |

### 5.5 Staff and the admin

The back office, until the staff pages exist (journey 12).

| ID | Feature | Steps | Expected | Result |
| -- | ------- | ----- | -------- | ------ |
| <a id="m27"></a>M27 | Screens and layouts | Open a screen and its Standard layout in the admin; save a layout without a wheelchair space | The seats listed with their grid places; the layout refused with a message | Pass, 4 November ([dev log](development_log.md#4-november-2026-seats-layouts-and-ticket-types)) |
| <a id="m28"></a>M28 | A screening's prices | Add a screening in the admin | Its price table filled from the ticket class | Pass, 4 November ([dev log](development_log.md#4-november-2026-seats-layouts-and-ticket-types)) |
| <a id="m29"></a>M29 | An overlapping screening | Add a screening that overlaps another on the same screen | The overlap message on the form, not an error page | Not run yet ([the overlap bug in full](#the-overlap-bug-in-full)) |
| <a id="m30"></a>M30 | Mark as paid | Tick a pending booking and run Mark as paid | Paid, with its seat count and the time | Pass, 19 November ([dev log](development_log.md#19-november-2026-selling-the-seats)) |

### 5.6 Edge cases still to run

The edge cases I found while designing the project in [section 4](architecture.md), to check by hand as each feature is built. Some are covered by rows above; the rest become rows as they're run.

- Seat concurrency (4.8): two browser sessions selecting the same seat at nearly the same moment; a hold expiring mid-checkout; backing out of Stripe's page and coming back to find the seats still held; the hard cap on total hold time after repeated amendments; the holds extending to cover the Stripe session when the customer chooses Pay; changing seats mid-checkout releasing the old holds in the same step; cancelling making the seats available to a second browser at once; booking refused once online sales have closed.
- Pending bookings (4.2, 4.8): the basket (ticket types, infants, food and drink, voucher) survives going back from payment; an abandoned pending booking disappears with its holds, without touching any paid booking.
- Seating (4.1): a closed area's seats can't be selected and don't count towards capacity; a screening's layout can't be changed once it has a booking; a wheelchair space in the circle is refused; a stalls layout without a wheelchair space is refused.
- Booking rules (4.1, 4.2): infants, or a Child ticket, without a ticket that doesn't need an adult are refused; infants on a 15 or 18 film are refused; a ticket type whose maximum age is below the film's minimum age isn't offered; a ticket type that needs proof shows the reminder at checkout and on the confirmation. A Companion ticket without a full-fare ticket is refused, and so are more companions than full-fare tickets; picking a wheelchair space offers the seats beside it first.
- Food and drink (4.3): an order attaches to the pending booking and is paid in the same Checkout Session; the seat choice is hidden when seat delivery is off for the screening; ordering is refused inside the food cutoff; an item marked sold out disappears from the menu and comes back when switched on; an age-restricted item shows the ID note on the order check and the confirmation; the food step works with JavaScript off; each status change on the service list writes an audit entry; cancelling a booking cancels its food and the voucher covers the whole total.
- Check-in (4.2): a booking can be found by reference or by email; checking in stamps the booking with the staff member and time and writes an audit entry; checking in twice is refused.
- Seat release (4.2): a cancelled booking's seats can be booked again immediately, and the original `SeatBooking` rows are still present with `released_at` set.
- Payment (4.13): a webhook with an invalid signature is rejected; the same webhook delivered twice doesn't double-process; a booking fully covered by a voucher skips Stripe; a connection dropping after paying but before the customer gets back doesn't cause a double charge; returning while a Checkout Session is still open reuses that session; a customer back before the webhook sees the confirming page; a payment that succeeds after the seats were lost and resold is refunded automatically.
- Vouchers (4.4, 4.13, 4.26): a voucher's balance spreads correctly across two bookings; it's only reduced on confirmed payment, not at checkout; a purchased voucher can't be spent until the success webhook has activated it, and a repeated webhook doesn't activate or email it twice; a voucher can't be used after its one-year expiry; refunding a part-voucher booking returns the card amount to the card and restores the voucher amount; the known limitation of two simultaneous checkouts on one code (see [Known issues](#known-issues)).
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

[↑ Back to contents](#contents)

## 6. Responsiveness, usability and the keyboard

### Widths and browsers

Not run yet as a recorded check. Each page is to be checked at 320, 375, 768, 1024 and 1280 pixels, rather than only at conventional breakpoints, consistent with the fluid layout approach in [section 3](ux_design.md): the point of that approach is that it shouldn't only work at the widths a media query targets. Also at 200% browser zoom and with the operating system's large-text setting on, per [4.17](architecture.md#417-accessibility-implementation). Browsers: current Chrome, Firefox, Safari and Edge, plus mobile Safari and Chrome. The seat map has to work on a phone-sized screen, not just on desktop.

So far, the pages have been looked at in a browser at phone and desktop widths as each was built ([section 5](#5-manual-tests)), which caught the bugs marked "found in a browser" in [section 7](#7-bugs-found-and-fixed).

### Real devices

Not run yet. An iPhone in Safari on iOS 17.4 or later, an Android phone in Chrome, and a 320 pixel wide window. The phone ticket's QR code is scanned from a second phone.

[↑ Back to contents](#contents)

## 7. Bugs found and fixed

Taken from the commit history and the development log. Each was found while building or testing, fixed, and covered by a test where it could be.

| Commit | What was wrong and fixed |
| ------ | ------------------------ |
| `d9afab8`, `b761b6c` | A form for adding or editing a screening let one overlap another on the same screen, which the database would then have refused with an error page. `test_a_form_reports_an_overlap_instead_of_crashing` ([in full below](#the-overlap-bug-in-full)) |
| `f05c6d3` | The footer gave the town of the real cinema the project is modelled on, so it read as if the site were that cinema. It now says the venue isn't connected to any real cinema. `test_page_doesnt_name_the_real_cinemas_town` |
| `f655cf4` | After renaming `Seat.seat_number` to `number`, the migration state's unique constraint still named the old field, so `makemigrations` still had a change waiting |
| `65ce08e` | The header and footer kept class names from before LooseLeaf, which it doesn't style, so the site name showed as a plain link and the footer ran to the page's edge. Found in a browser ([dev log](development_log.md#4-november-2026-what-the-browser-showed-that-the-tests-didnt)) |
| `af046f4` | The day strip, the film cards and the times were indented, as LooseLeaf's reset keeps the browser's padding on a list marked `role="list"`. Found in a browser. `test_unstyled_lists_lose_the_browsers_indent` |
| `dda5cf2` | The home page's cards said "106 minutes" where the film page said "1 hour 46 minutes". Spotted in the screenshots for the development log. `test_runtime_reads_as_hours_and_minutes` |
| `4ed4f2d` | The live site showed a 500 once. The likeliest cause was a database connection Neon had dropped while idle, reused without a check; kept connections are now checked first ([dev log](development_log.md#9-november-2026-deploying-the-accounts-and-a-500)). `test_kept_connections_are_checked_before_reuse` |
| Seat selection, 9 November | A time at the end of a sentence came out as "6:00 p.m..", since Django writes the full stops. Found in a browser; the sentences were reworded and a test looks for the doubled stop ([dev log](development_log.md#9-november-2026-choosing-seats-without-javascript)) |
| Seat map, 9 November | A chosen seat showed the browser's own checkbox, because LooseLeaf's visually-hidden class reveals an element with focus. Found in a browser; the seat's checkbox now has its own hiding ([dev log](development_log.md#9-november-2026-the-seat-map)) |
| Seat map, 9 November | On a phone the page was 992 pixels wide, because a fieldset won't shrink below its contents. Found in a browser ([dev log](development_log.md#9-november-2026-the-seat-map), [row M20](#m20)) |
| `cb1d88a` | A chosen seat was still read out as "available". Found in a browser |
| `ebbd471` | The screen above the seat map was narrower than the seats, because it was capped at a paragraph's width. Found in a browser |
| `4190363` | Booking references could contain L, which the docs leave out with 0, O, 1 and I as easy to mishear. `test_references_leave_out_characters_easily_misheard` |
| `3fcb66c` | Holding seats only looked at other holds, so once a hold became a sale its seat would have looked free. `test_a_sold_seat_cant_be_held` |
| `981c6d7` | The seat map had the same gap, and would have shown a sold seat as free. `test_a_sold_seat_shows_as_sold` |
| `499d63b`, `ba03a6b` | A hold that ran out could be cleared and its seat held by someone else, and confirming would then have sold the booking's other seats without noticing one was missing. The booking now keeps a seat count. `test_a_hold_that_ran_out_and_went_to_someone_else_saves_nothing` |
| `fbac223` | Registering from the checkout page ignored where it was sent from, so a new customer lost their way back to their seats. `test_registering_to_pay_goes_back_to_the_booking`, and `test_next_cant_send_anyone_to_another_site` |
| `1983569`, `b4232ae` | Stripe's page offered Klarna, Revolut Pay, Amazon Pay and Link as well as cards. Asking Stripe for card-only sessions made every Pay fail, as its API no longer accepts that, so it was undone; the methods are set in the Stripe dashboard instead. Found by a real test-mode payment |
| `92741de` | Paying again after a session expired built the same idempotency key, so Stripe would have handed back the expired session and the customer could never pay. `test_paying_after_the_session_expired_gets_a_new_one` |
| `7f80e4e` | Pay was a plain outlined button under a filled Cancel, so the page's main action looked weaker than letting the seats go. Found in a screenshot for the development log. `test_the_checkout_page_has_a_pay_button` |
| `1eb564e`, `676aac9` | Tickets that need proof, such as Student or Companion, didn't say so at checkout or on the confirmation, though journey 2 and 4.2 ask for it. Found in a screenshot for the development log. `test_checkout_reminds_them_beside_the_ticket` and `test_the_confirmation_reminds_them_too` |
| `493f1aa` | A payment on a session that had been replaced, after the basket changed, found no booking and was kept with nothing to show for it. The webhook now falls back to the booking reference every session carries. `test_a_payment_on_a_replaced_session_still_finds_its_booking` |

### The overlap bug in full

What happened: a form for creating or editing a screening accepted one that overlapped another on the same screen. The database constraint would then have rejected the save with an error page, instead of the form showing the overlap message from journey 12, "Overlap rejected".

How I found it: while planning the admin for screenings. The model tests passed because they call `full_clean()` with nothing left out, which isn't how a form calls it.

Cause: a form leaves out every field it doesn't show, and Django skips any constraint that refers to a left-out field. The overlap constraint (4.1) refers to `ends_at`, which is worked out on save and never typed in, and to `cancelled_at` in its "not cancelled" condition. Staff never type either in, so the check never ran.

Fix: `Screening.validate_constraints()` keeps both fields in the check. That's safe because `clean()` sets `ends_at` just before it, and `cancelled_at` holds its saved value. My first fix only kept `ends_at`, so the condition was still skipped and the test still failed. I'd committed it before noticing, so the history shows both commits: [`d9afab8`](https://github.com/StockoL/regal-cinema/commit/d9afab898280d0a0859e85cc7a591315fda77185) (incomplete) and [`b761b6c`](https://github.com/StockoL/regal-cinema/commit/b761b6cf4c5d262fe4c4f1e58430a9dbe265be2d) (the working fix). Since then I only commit once the test runner's exit code says the whole suite passed.

Test: `test_a_form_reports_an_overlap_instead_of_crashing` in `screenings/tests/test_screenings.py` submits an overlapping screening through a form and checks the form is invalid with the overlap message.

### Known issues

Limitations I've accepted, or that wait for a later phase, as opposed to things yet to be discovered.

| Issue | Effect | Why it's not fixed yet |
| ----- | ------ | ---------------------- |
| A real payment hasn't been made end to end | The webhook, confirming and refunds are tested against the fake provider and signed test events, not yet against a real Stripe payment | Deferred until screenings can be created through the real flow, so the journey starts where a customer's would ([row M24](#m24)) |
| Stripe's page offers payment methods other than cards | A customer could pay with Klarna, Revolut Pay, Amazon Pay or Link, which the refund and reconciliation design doesn't cover | Stripe's API no longer takes the methods per session; they have to be switched off in the Stripe dashboard |
| A session that was replaced stays open at Stripe | If a customer changes their basket after pressing Pay, the old session can still be paid. The payment is matched to the booking by its reference, and refunded if the booking is already paid, but the customer is charged and refunded when they needn't be | The old session should be expired when the basket changes (4.32). That comes with changing a booking during payment |
| A failed refund stays failed | Nothing retries it yet | The retry is part of the scheduled job (4.32), not built yet |
| An email that couldn't be sent waits in the outbox | The booking stands and the attempt is recorded, but nothing tries again until the scheduled job is built | The retry is part of the same scheduled job (4.32) |
| A Stripe fee that couldn't be looked up stays empty | The booking is paid, but its fee and net are missing from the reports until filled in | The later try is part of the same scheduled job (4.32) |
| Voucher race condition (4.13) | Two simultaneous checkouts on one code have a narrow window in which both could succeed | Unlikely and low in severity, since a voucher has to be typed in. Solving it would need a second holding mechanism like `SeatHold` |
| No membership auto-renewal (4.18) | A lapsed membership must be bought again by hand | Automatic recurring billing is out of scope |
| No dual authorisation for large refunds (4.12) | One person with the refund permission can refund any amount | A second sign-off is a future consideration |
| Reporting queries run against the primary database (4.12) | At very high volume the reports could compete with customer traffic | A read replica isn't needed at this scale |
| Cancellation inside the cutoff is by phone (4.22) | There's no online route inside the window | By design |
| Older iPhones and iPads aren't supported | LooseLeaf UI needs Chrome 117, Safari 17.4 or Firefox 129 or later, so on Apple devices that means iOS and iPadOS 17.4 or later | Whether that's acceptable for a cinema's audience is still to be decided |

[↑ Back to contents](#contents)

## 8. Deployment check

On the [live site](https://regal-cinema.onrender.com), after each deploy. The first two columns come from the [development log](development_log.md). The last was checked from my computer on 20 November, after `f736d35` deployed with the payment work. The deploy before it, `ef2fdf3`, timed out: its build and migration succeeded, but the instance never started, with no output from gunicorn at all. It booted and answered its health check on my machine with production settings, so I deployed again, and that one went live. Render kept the previous deploy running in between.

| ID | Check | Expected | At the first deploy, 25 October | After the accounts, 9 November | After the payment work, 20 November |
| -- | ----- | -------- | ------------------------------- | ------------------------------ | ------------------------------ |
| <a id="d01"></a>D01 | The site loads | `/health/` and the pages answer 200 | Pass: `/health/` and the admin login answered 200 from gunicorn | Pass: every page checked loaded. One 500 earlier that day, fixed in `4ed4f2d` | Pass: `/health/` and the home page answered 200 |
| <a id="d02"></a>D02 | `http://` goes to `https://` | A plain HTTP request ends on the `https://` address | Pass: 301 to HTTPS, from Render | Not recorded | Pass: 301 to `https://regal-cinema.onrender.com/` |
| <a id="d03"></a>D03 | `DEBUG` is off | A made-up address shows a plain 404, not Django's debug page | Pass: a plain 404 with no debug page | Not recorded | Pass: 404 with the site's own page, and no debug page |
| <a id="d04"></a>D04 | Security headers | HSTS, `X-Frame-Options: DENY`, and a `Secure` CSRF cookie | Pass: all three | Not recorded | Pass: HSTS and `X-Frame-Options: DENY` on the home page, and the admin's CSRF cookie marked `Secure` |
| <a id="d05"></a>D05 | Static files | Hashed stylesheets load through WhiteNoise | Pass: the admin's hashed CSS loaded | Not recorded | Pass: the hashed `main.css` answered 200 |
| <a id="d06"></a>D06 | The deployment check | `check --deploy` with only the warnings left on purpose | One error: the console email backend, refused in production | Pass: only the two HSTS warnings, left on purpose | Not run against the live settings; locally with `DEBUG` off, only the two HSTS warnings ([section 1](#1-checks-run-findings-and-how-each-was-resolved)) |
| <a id="d07"></a>D07 | The admin | Log in to the live admin with the production superuser | Pass: created from my own machine against Neon, and logged in | Not recorded | Not recorded |
| <a id="d08"></a>D08 | Payments | A test-mode payment on the live site confirmed by the dashboard's webhook endpoint | Not part of this deploy | Not part of this deploy | Partly: the webhook refuses an unsigned request with a 400. A test-mode payment waits for the real screening flow ([row M24](#m24)) |

[↑ Back to contents](#contents)

---

[← 6. Development log and engineering phases](development_log.md) · [README](../README.md) · [8. Marketing development thoughts (future business ideas) →](future_ideas.md)
