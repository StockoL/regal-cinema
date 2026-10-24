# 1. Project purpose and user stories

Regal Cinema gives a boutique independent cinema a booking experience that matches what it offers: two seating areas, tickets for different kinds of customer, food and drink, and a membership scheme. I've worked out the user journeys first and written each one as a set of Given/When/Then scenarios, with a MoSCoW priority on every step. The scenarios are also the checklist for [user story testing](testing.md#2-user-story-testing-behaviour-driven-verification).

## How I've prioritised

I've used MoSCoW at the level of each step in a journey, not just each feature.

- Must: needed for the project to work and be assessable.
- Should: valuable, and planned once the core is complete.
- Could: wanted if time allows.
- Won't (this time): left out on purpose and recorded as future work.

The same split drives the build order in [section 6](development_log.md). A journey's success measure is that its scenarios hold under manual and automated testing. I'm not measuring live conversion figures, because there's no live audience.

## The journeys

For the cinema-goer:

1. [Browse and discover](#journey-1-browse-and-discover)
2. [Select seats and hold them](#journey-2-select-seats-and-hold-them)
3. [Add food and drink](#journey-3-add-food-and-drink)
4. [Register or log in](#journey-4-register-or-log-in)
5. [Apply a voucher](#journey-5-apply-a-voucher)
6. [Check out and pay](#journey-6-check-out-and-pay)
7. [Manage my bookings and request a cancellation](#journey-7-manage-my-bookings-and-request-a-cancellation)
8. [Buy a membership](#journey-8-buy-a-membership)
9. [Book in a priority window](#journey-9-book-in-a-priority-window)
10. [Send a private-hire enquiry](#journey-10-send-a-private-hire-enquiry)

For staff:

11. [Log in to the staff area](#journey-11-log-in-to-the-staff-area)
12. [Create or edit a screening](#journey-12-create-or-edit-a-screening)
13. [Add a film from TMDb](#journey-13-add-a-film-from-tmdb)
14. [Take an in-venue booking](#journey-14-take-an-in-venue-booking)
15. [Cancel or refund a booking](#journey-15-cancel-or-refund-a-booking)
16. [Cancel a screening](#journey-16-cancel-a-screening)
17. [View the sales dashboard](#journey-17-view-the-sales-dashboard)

In the staff journeys, "a staff member" means anyone who holds the permission that action needs (see [4.9](architecture.md#49-staff)).

## Journey 1: Browse and discover

Success: a customer can get from the landing page to a specific screening's seat selection without searching elsewhere or asking anyone.

| Step                        | Scenario                                                                                                                                                                               | MoSCoW |
| --------------------------- | -------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| Reel rows                   | Given screenings exist across categories, when the customer lands on the home page, then they are grouped into named rows (What's On, Coming Soon, discounted showings).               | Must   |
| Film detail                 | Given a film has upcoming screenings, when its page loads, then the synopsis, age rating and a click-to-play trailer (never autoplay) are shown.                                       | Must   |
| Access flags                | Given a screening has captions or audio description, when it appears in a listing, then that is visible without opening the detail page.                                               | Must   |
| Date and showtime picker    | Given a film's screenings span several dates, when the customer picks a date, then only that date's showtimes appear in the pill picker.                                               | Should |
| Private screenings hidden   | Given a screening is private, when the public browses, then it never appears.                                                                                                          | Must   |
| Priority screenings visible | Given a screening isn't yet open to the public, when it appears in a listing, then it is greyed out with a text label saying who can book it and when, linking to the membership page. | Must   |
| Empty date                  | Given a chosen date has no showings, when it is displayed, then a clear empty state appears.                                                                                           | Could  |

## Journey 2: Select seats and hold them

Success: no seat is ever double-booked under concurrent access, shown by an automated concurrency test and a manual two-tab check.

| Step                 | Scenario                                                                                                                                                                                                      | MoSCoW |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| Live grid            | Given a screening page loads, when the seat grid renders, then every seat's live status is shown through `data-seat-status`, never a stale one.                                                               | Must   |
| Selecting            | Given seats are available, when the customer taps them, then they are selected without a server call.                                                                                                         | Must   |
| Ticket types         | Given seats are selected, when the customer proceeds, then each seat is given a ticket type (adult, student, OAP, child) with its price shown, and infants can be added free without taking a seat.           | Must   |
| Hold created         | Given seats are selected, when the customer proceeds, then the server re-validates and creates holds for the venue's hold time.                                                                               | Must   |
| Conflict             | Given a seat was taken in the gap, when the hold is attempted, then only the conflicting seats are flagged and the other selections are kept.                                                                 | Must   |
| Failed-payment retry | Given a payment attempt fails, when it does, then the hold is extended up to the hard cap rather than released.                                                                                               | Must   |
| Amend                | Given a customer has moved on to checkout, when they go back and change their seats, then the holds on removed seats are released and holds on the new seats are created in one step, without starting again. | Must   |
| Seats never stuck    | Given a customer cancels or switches to different seats, when they do, then the previous seats are immediately available to everyone else.                                                                    | Must   |
| Cancel               | Given the customer decides not to continue, when they choose Cancel, then the hold is released immediately.                                                                                                   | Must   |
| Expired mid-checkout | Given a hold has expired, when payment is attempted, then the customer returns to the seat map with a plain explanation.                                                                                      | Must   |
| Back button          | Given the browser's back button is used, when the seat grid reappears, then it re-fetches live state.                                                                                                         | Should |

## Journey 3: Add food and drink

Success: every `OrderItem` belongs to exactly one finalised booking, with the price recorded at the time, and is never orphaned or duplicated.

| Step             | Scenario                                                                                                                                         | MoSCoW |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------ | ------ |
| Browse products  | Given checkout is open, when the customer views items, then drinks and snacks are shown with prices.                                             | Must   |
| Add              | Given an item is added, when it is added, then an `OrderItem` attaches to the in-progress booking.                                               | Should |
| Adjust           | Given a quantity changes, when it is changed, then the total reflects it, instantly if the live summary is built and on the next step otherwise. | Should |
| Survives payment | Given payment succeeds, when the booking is finalised, then every item is recorded with its unit price at that moment.                           | Must   |

## Journey 4: Register or log in

Success: no customer loses a seat hold by registering or logging in during checkout.

| Step                 | Scenario                                                                                                                        | MoSCoW |
| -------------------- | ------------------------------------------------------------------------------------------------------------------------------- | ------ |
| Anonymous browsing   | Given no account, when a customer browses or selects seats, then nothing requires login yet.                                    | Must   |
| Gate at checkout     | Given an anonymous customer reaches online checkout, when they try to pay, then they are asked to register or log in.           | Must   |
| Anonymous-only pages | Given a logged-in customer, when they visit login or registration, then they are redirected away.                               | Must   |
| Username collision   | Given two emails share a local part, when both register, then usernames derive with an incrementing suffix and never collide.   | Should |
| Duplicate email      | Given an email is already registered, when someone reuses it, then registration is rejected with a clear message.               | Must   |
| Hold survives login  | Given holds exist under an anonymous session, when the customer logs in mid-checkout, then the holds reassign to their account. | Must   |
| Verification         | Given a new account, when registration completes, then a verification email is sent but the account works immediately.          | Should |

## Journey 5: Apply a voucher

Success: a voucher's balance never goes negative and only ever decreases when payment is confirmed.

| Step             | Scenario                                                                                                                                                           | MoSCoW            |
| ---------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ----------------- |
| Valid code       | Given a voucher has balance, when it is entered at checkout, then it is deducted following the order in 4.10.                                                      | Should            |
| Used-up code     | Given a voucher's balance is zero, when it is entered, then it is rejected with that reason.                                                                       | Must              |
| Partial cover    | Given a voucher covers only part of the total, when checkout completes, then the remainder is charged to Stripe and the voucher decreases only after confirmation. | Must              |
| Simultaneous use | Given one code is entered in two checkouts at once, when both pay, then the documented race window applies (see Known Issues).                                     | Won't (this time) |

## Journey 6: Check out and pay

Success: the customer is never told a payment succeeded unless Stripe has confirmed it, and always knows what happened and what to do next.

| Step                       | Scenario                                                                                                                                                                                                                                                                                                               | MoSCoW |
| -------------------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| Seats re-validated         | Given a hold exists, when the customer proceeds to checkout, then the server re-checks the seats are still free.                                                                                                                                                                                                       | Must   |
| Going back                 | Given the customer is in checkout, when they use the back button or a Change link, then they return to the previous step with their selections intact and can amend them before paying.                                                                                                                                | Must   |
| Policy shown before paying | Given the customer is about to pay, when the total is displayed, then the cancellation policy is shown beside it.                                                                                                                                                                                                      | Should |
| Live summary               | Given seats, items or a voucher change, when they do, then the displayed total, with a line per ticket type, updates immediately and is recalculated by the server at payment (4.20).                                                                                                                                  | Could  |
| Payment submitted          | Given a non-zero total, when payment is submitted, then the response is "submitted", and confirmation comes only from Stripe's webhook (4.13).                                                                                                                                                                         | Must   |
| Payment succeeds           | Given the verified success webhook arrives, when it is processed, then the holds convert and are deleted, the voucher decreases, `amount_charged_pence` is stored, and the customer sees a confirmation with a prominent booking reference, the screening details, what to do on arrival, and the cancellation policy. | Must   |
| Payment fails              | Given a payment failure arrives, when it is processed, then the customer sees the specific reason, the hold is kept, and a clear retry is offered.                                                                                                                                                                     | Must   |
| Zero total                 | Given a voucher covers the full total, when checkout completes, then the booking is marked paid without contacting Stripe, with an identical confirmation screen.                                                                                                                                                      | Must   |
| Dropped connection         | Given the browser loses connection after submitting, when the customer returns, then the real payment status is checked with Stripe before any new attempt, so no one is charged twice.                                                                                                                                | Should |

## Journey 7: Manage my bookings and request a cancellation

Success: a customer can see every booking and request a cancellation without phoning, except inside the cutoff, where they are told clearly how to reach the venue.

| Step                        | Scenario                                                                                                                                                                                    | MoSCoW |
| --------------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| List                        | Given a logged-in customer, when they open My Bookings, then all their bookings are shown with status.                                                                                      | Must   |
| Detail                      | Given a booking, when it is opened, then the screening, seats, items, amount charged and reference are shown, using stored figures, not recalculated ones.                                  | Must   |
| Request outside cutoff      | Given an upcoming booking more than the cutoff hours away, when the customer requests cancellation, then the booking becomes `cancellation_requested` and they are told staff will confirm. | Should |
| Inside cutoff               | Given a booking inside the cutoff window, when the customer opens the cancellation page, then no request form is offered, and the venue's phone number and opening hours are shown.         | Should |
| Staff decision              | Given a staff member approves a request, when they choose a voucher or card refund, then the seats are released immediately, the status updates, and the action is logged with a reason.    | Should |
| Past or cancelled           | Given a booking is past or already cancelled, when it is viewed, then no cancellation option is shown.                                                                                      | Should |
| Grace period after purchase | Given a customer cancels within minutes of booking, when inside the cutoff, then the request is still allowed.                                                                              | Could  |

## Journey 8: Buy a membership

Success: membership validity is always a plain expiry-date check, never a staff judgement.

| Step             | Scenario                                                                                                                                | MoSCoW    |
| ---------------- | --------------------------------------------------------------------------------------------------------------------------------------- | --------- |
| View tiers       | Given a logged-in customer, when they view membership, then each tier's price and benefits are clear.                                   | Must      |
| Purchase         | Given a tier is selected, when payment succeeds, then the tier and an expiry one year ahead are set on their profile.                   | Must      |
| Lapsed           | Given the expiry has passed, when the customer views their profile, then a renewal prompt appears and nothing is charged automatically. | Must      |
| Failed payment   | Given a purchase fails, when it does, then the same success and failure pattern as journey 6 applies.                                   | Should    |
| Withdrawal right | Given the 14-day cancellation right turns out to apply (see 4.22), when a member cancels inside it, then a path exists to do so.        | To verify |

## Journey 9: Book in a priority window

Success: the boundary (`now >= public_onsale_at - priority_booking_hours`) is enforced to the second, with no off-by-one or timezone error, and has its own test at that exact moment.

| Step            | Scenario                                                                                                                                                                       | MoSCoW |
| --------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------ |
| Eligible member | Given a member's priority hours cover the gap, when they book, then it succeeds.                                                                                               | Must   |
| Not eligible    | Given a non-member or lower tier, when they try before the public on-sale, then booking is blocked with an "opens at" message, and the screening stays visible and greyed out. | Must   |
| Public on-sale  | Given the public on-sale time has passed, when anyone books, then it succeeds.                                                                                                 | Must   |
| Friends only    | Given no public on-sale time is set, when a non-member tries at any time, then it remains blocked and is labelled "Friends only".                                              | Must   |

## Journey 10: Send a private-hire enquiry

Success: enquiry capture and the visibility rules for the resulting private screening work. Quoting and invoicing are out of scope.

| Step                 | Scenario                                                                                                                      | MoSCoW |
| -------------------- | ----------------------------------------------------------------------------------------------------------------------------- | ------ |
| Submit               | Given a prospective hirer fills in the form, when it is submitted, then an `EnquiryRequest` is created.                       | Must   |
| Staff list           | Given enquiries exist, when staff open the venue area, then they appear in one list.                                          | Must   |
| Conversion           | Given terms are agreed, when staff create a private screening, then the enquiry links to it.                                  | Should |
| Hidden               | Given a private screening exists, when the public browses, then it never appears.                                             | Must   |
| Still blocks overlap | Given a private screening occupies a slot, when staff try to schedule a public one over it, then the overlap rule rejects it. | Must   |

## Journey 11: Log in to the staff area

Success: no customer-facing page ever links to staff tooling, checked by crawling every customer template for `/staff/`.

| Step                  | Scenario                                                                                                                                  | MoSCoW |
| --------------------- | ----------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| Separate login        | Given a staff member visits `/staff/` logged out, when the page loads, then a login page distinct from the customer site appears.         | Must   |
| Direct access blocked | Given any staff URL, when it is requested while logged out, then the user is redirected to the staff login.                               | Must   |
| Permission-gated      | Given a logged-in staff member lacking a permission, when they request that action, then it is refused, not just hidden in the interface. | Must   |
| No public link        | Given any customer page, when it is rendered, then nothing links to `/staff/`.                                                            | Must   |

## Journey 12: Create or edit a screening

Success: the no-overlap rule holds on every save, not only on creation, and edits never change what a past booking shows.

| Step               | Scenario                                                                                                                                                    | MoSCoW |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| Overlap rejected   | Given a screening overlaps another on the same screen, when it is saved, then it is rejected with a clear message.                                          | Must   |
| Valid save         | Given no overlap, when it is saved, then it appears immediately in staff and (if public) customer listings.                                                 | Must   |
| Price table        | Given staff choose a ticket class, when the form loads, then a price for each ticket type is pre-filled from the class default and each line can be edited. | Must   |
| Price edited later | Given a paid booking exists, when a ticket price on that screening is later edited, then the booking still shows the amount charged at the time.            | Must   |

## Journey 13: Add a film from TMDb

Success: nothing from TMDb is saved without a person confirming it, the age rating especially.

| Step             | Scenario                                                                                                                                              | MoSCoW |
| ---------------- | ----------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| Search           | Given staff search by title, when results return, then a list with poster, title and year is shown.                                                   | Must   |
| Review           | Given a result is picked, when it is fetched, then the synopsis, runtime, trailer and UK age rating appear on a review screen and are not auto-saved. | Must   |
| Confirm          | Given staff confirm, when it is saved, then it is stored locally and not re-queried unless refreshed.                                                 | Must   |
| TMDb unreachable | Given TMDb errors or times out, when it does, then a specific message and a retry are shown.                                                          | Must   |
| No TMDb entry    | Given an event with no listing, when staff add it manually, then every field can be filled in by hand with no TMDb ID.                                | Must   |
| Refresh          | Given staff refresh a film, when it runs, then the same review step applies.                                                                          | Should |

## Journey 14: Take an in-venue booking

Success: `stripe_payment_intent_id` stays empty on every in-venue booking, so the two payment paths never cross.

| Step            | Scenario                                                                                                                                                               | MoSCoW |
| --------------- | ---------------------------------------------------------------------------------------------------------------------------------------------------------------------- | ------ |
| Shared flow     | Given a walk-up customer, when staff complete the sale, then the same hold, booking and discount order apply, including a ticket type for each seat and any infants.   | Must   |
| Flags set       | Given the customer pays on the venue's card terminal, when staff mark it paid, then channel, payment method and `created_by` are set and no Stripe payment is created. | Must   |
| Member discount | Given the customer wants their discount, when staff look up their account by email, then the booking links to it.                                                      | Should |
| Anonymous sale  | Given the customer gives no details, when the sale completes, then the booking has no user.                                                                            | Must   |

## Journey 15: Cancel or refund a booking

Success: every cancellation or refund has a required reason and a named staff member, and the seats are available to sell again at once.

| Step                | Scenario                                                                                                                                                                 | MoSCoW |
| ------------------- | ------------------------------------------------------------------------------------------------------------------------------------------------------------------------ | ------ |
| Permission check    | Given a staff member, when they try to cancel, refund or issue a voucher, then each action requires its own permission.                                                  | Must   |
| Voucher route       | Given a booking is cancelled with a voucher, when it is processed, then a voucher for the amount charged is issued and the action is logged with a reason.               | Must   |
| Card refund         | Given a card refund is chosen, when it is processed, then Stripe's refund is called directly, the status becomes `refunded`, and the action is logged with a reason.     | Must   |
| Seats released      | Given the cancellation is confirmed before the screening, when it completes, then the seats are released immediately (`released_at` is set) and can be booked again.     | Must   |
| After the screening | Given the screening has already happened, when a goodwill refund is made, then the money is handled and no seat is released.                                             | Could  |
| Any time            | Given a booking inside the customer cutoff, when a staff member cancels it at the customer's request by phone, then it works, since the cutoff only limits self-service. | Must   |

## Journey 16: Cancel a screening

Success: the number of customer outcomes (voucher or refund) always equals the number of bookings that existed, with no one missed or paid twice.

| Step               | Scenario                                                                                                                      | MoSCoW |
| ------------------ | ----------------------------------------------------------------------------------------------------------------------------- | ------ |
| Batch              | Given a screening with bookings is cancelled, when it is triggered, then every booking is cancelled and its seats released.   | Must   |
| Customer's choice  | Given the batch has run, when each customer is contacted, then a voucher is issued by default and a card refund is available. | Must   |
| One log entry each | Given the batch completes, when it is reviewed, then one audit entry exists per affected booking.                             | Must   |
| No bookings        | Given a screening has none, when it is cancelled, then it simply cancels.                                                     | Should |

## Journey 17: View the sales dashboard

Success: figures can never drift from the underlying data, because nothing is stored twice.

| Step              | Scenario                                                                                                                           | MoSCoW |
| ----------------- | ---------------------------------------------------------------------------------------------------------------------------------- | ------ |
| Live revenue      | Given the dashboard loads, when it renders, then revenue by day, week and month is computed from stored `amount_charged_pence`.    | Must   |
| Occupancy         | Given a booking is cancelled or refunded, when it is, then occupancy counts only unreleased seats.                                 | Must   |
| Paid only         | Given top sellers are shown, when they are computed, then only paid bookings count.                                                | Must   |
| Discounts         | Given discounts and vouchers redeemed are shown, when they are computed, then they match the paid bookings.                        | Should |
| Sold and released | Given a seat was sold then released, when sell-through is analysed, then the original demand can still be seen.                    | Could  |
| Ticket mix        | Given the dashboard loads, when sales are broken down, then tickets sold by type (adult, student, OAP, child, infant) can be seen. | Could  |

---

[README](../README.md) · [2. Research →](research.md)
