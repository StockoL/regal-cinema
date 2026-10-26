# Wireframes

This is the brief I'm drawing the wireframes against, and where they'll sit once they're done. It belongs to the skeleton plane of the [UX design strategy](ux_design.md). Each screen lists what has to be on it, taken from the [user journeys](user_stories.md) and the [architecture](architecture.md), the questions only a drawing will answer, and the wording I still need to write.

I'm drawing them in Excalidraw, low fidelity: grey boxes, real labels, a crossed box for each image, and notes in the margin wherever behaviour isn't visible. Every screen gets two frames, phone (375px) and desktop (1280px). The exports go in `docs/wireframes/`, named by number and width, such as `01-home-mobile.png` and `01-home-desktop.png`, and get added under their screen below.

The order follows the build plan's scope cut. Group A is the five screens the plan names, all part of the spine. Group B is the rest of the spine. Group C is stretch work, drawn before its build week and not before.

## Status

| #   | Screen                                   | Group | Journeys     | Phone | Desktop |
| :-- | :--------------------------------------- | :---- | :----------- | :---- | :------ |
| 1   | Home: the Reel and greyed-out listings   | A     | 1, 9, 16     | To do | To do   |
| 2   | Screening page: seat map, ticket types   | A     | 2            | To do | To do   |
| 3   | Booking summary, step by step and live   | A     | 2, 3, 6      | To do | To do   |
| 4   | Checkout hand-off and Stripe return      | A     | 6            | To do | To do   |
| 5   | Film detail and showtimes by date        | B     | 1            | To do | To do   |
| 6   | Log in and register                      | B     | 4            | To do | To do   |
| 7   | My bookings                              | B     | 7            | To do | To do   |
| 8   | Staff: screenings                        | B     | 11, 12       | To do | To do   |
| 9   | Membership page                          | C     | 8, 9         | To do | To do   |
| 10  | Gift voucher page                        | C     | 5            | To do | To do   |
| 11  | Staff: cancellation queue                | C     | 7, 15        | To do | To do   |
| 12  | Staff: TMDb review screen                | C     | 13           | To do | To do   |
| 13  | Private hire enquiry form                | C     | 10           | To do | To do   |

## Shared layout

Every customer page uses the same header, menu and footer, so I'll draw these once on the home page and reuse them.

- Header with the site name linking home.
- Main menu. Logged out: What's on, Membership, Private hire, About, Log in, Register. Logged in: What's on, Membership, Private hire, About, My bookings, Account, Log out. It wraps onto a second line on a phone instead of hiding behind a menu button.
- Footer with the venue's phone number and opening hours, the accessibility policy and the membership terms.
- A "Skip to main content" link, shown when it has keyboard focus.

## Group A: the screens the build plan names

### 1. Home: the Reel and greyed-out listings

- Named rows that scroll sideways (the Reel, 3.II): What's On, Coming Soon, and a discounted class such as Silver Screen.
- Each film card: poster, title, age rating, and the captions and audio description flags, visible without opening the film.
- A priority screening shown greyed out with its text label, linking to the membership page (4.18).
- A cancelled screening shown greyed out and labelled "Cancelled" until its date (4.11).
- A showing whose online sales have closed, labelled with the phone number. When sales close is still to decide.
- An empty row or date.

Questions to answer: does a card stand for a film or a single screening? Where do the priority, cancelled and sales-closed labels sit on a card? How does a row show that it scrolls?

Wording to write: the priority label with dates, the "Friends only" label, the cancelled label, the sales-closed label and the empty-row message.

### 2. Screening page: seat map and ticket types

- Stalls and circle, labelled, with the screen's position marked.
- The seat key: available, selected, held by someone else and booked, each with a shape or pattern as well as a colour (4.17). Also wheelchair spaces, seats out of use and aisle gaps. The data model can't hold those three yet, so whether and how they're stored is still to decide.
- After choosing seats, a ticket type and its price for each seat, and a counter for free infant tickets with no seat.
- A seat taken by someone else in the meantime: that seat marked, the other selections kept.
- Once seats are held, the hold timer and a Cancel button.
- The sales-closed state, with the phone number instead of a seat map.

Questions to answer: how do long rows fit a phone, by scrolling sideways or by shrinking? How does the keyboard move around the map? I'm leaning towards one tab stop with arrow keys between seats rather than tabbing through every seat, which would change 4.17, so that's still to decide.

Wording to write: the seat-taken message, the hold timer text, the screen reader name for each seat state, and the sales-closed message.

### 3. Booking summary, step by step and live

- The spine version: the summary on each step, updated when the customer moves on. One line per ticket type, the infants, the total and a Continue button.
- The stretch version, the live summary (4.20): the same panel kept in view, updating the moment seats, ticket types or food and drink change.

Questions to answer: where does the live summary sit on a phone, and what changes in it as the customer works through the booking? One frame each, or one frame with notes, is enough.

### 4. Checkout hand-off and Stripe return

Payment happens on Stripe's hosted Checkout page (4.13), so there's no card field on this site.

- The checkout page: the summary and total, the cancellation policy next to the total, Back and Change links, the hold timer, and a button that goes to Stripe.
- A box in the flow standing for Stripe's page, to show that card entry and declined cards are handled there.
- The success page: a prominent booking reference, the film, date, time and screen, the seats and ticket types, the infant count, the amount paid by card and any voucher amount applied, what to do on arrival, the cancellation policy, and links to My bookings and What's on.
- The "confirming your payment" state, for when the customer is back before Stripe's webhook has arrived.
- Payment not completed: the customer backed out of Stripe's page, no payment was taken, the seats are still held with the time left, and they can try again.
- Hold expired: back to the seat map with a plain explanation.

Wording to write: the confirming, success, not completed and hold expired messages.

## Group B: the rest of the spine

### 5. Film detail and showtimes by date

- Poster, title, age rating, runtime and synopsis.
- The trailer, played only when clicked and never automatically. With no trailer, the space isn't shown at all.
- A date strip, and that date's showtimes as pill buttons. Each pill shows the time, the ticket class, the captions and audio description flags, and its state: available, priority, cancelled or sales closed. Private screenings never appear.
- A date with nothing showing.

Question to answer: on a phone, does the synopsis come before or after the showtimes?

Wording to write: the message for a date with nothing showing.

### 6. Log in and register

- Email and password only. Register asks for the password twice.
- Errors written out next to the field they belong to.
- The mid-checkout version, with a note that the seats are held while the customer logs in, and the timer.
- The verification banner after registering. The account works straight away, so this is a reminder, not a block.

Wording to write: the duplicate email error, the mid-checkout note and the verification banner.

### 7. My bookings

- The list of bookings with status and reference, upcoming and past separated.
- A booking's detail: seats, ticket types, infants, amount charged and reference.
- A marked space for the cancellation request, which is stretch. It gets drawn properly with screen 11.

### 8. Staff: screenings

- The staff area's own header and menu (Screenings, Films, Bookings, Enquiries, Sales, Audit log, Settings), clearly different from the customer site, showing only the items a staff member's permissions allow.
- The screening list.
- The create and edit form: film, screen, date and time, ticket class, the price table filled from the class's default with every line editable, the public on-sale time (blank means Friends only), and the private, captions and audio description tick boxes. "Ends at" shown, so staff can see why a clash happens.
- The overlap message next to the time field.
- On the film edit page, the runtime-change version: the new runtime kept on the form, and a list of the screenings it would make overlap, each with a link to move it (4.1).

Wording to write: the overlap message and the heading for the runtime clash list.

## Group C: stretch, drawn before each one's build week

These follow the build plan's stretch order. Each needs a wireframe before its build week, which for most of them is December.

### 9. Membership page

- The tiers, each with its price and benefits: priority booking hours, ticket discount, and the food and drink discount for the higher tier (4.4, 4.18).
- Buying a tier, through the same Stripe hand-off as a booking.
- A lapsed member's renewal prompt.
- A space for the 14-day cancellation path, if the withdrawal right turns out to apply (4.22).

### 10. Gift voucher page

- Buying a voucher, and entering a code at checkout.
- The remaining balance after a part-covered booking.
- A used-up code's rejection message.

### 11. Staff: cancellation queue

- The queue of customer cancellation requests, oldest first.
- The approve or decline screen: the booking's details, the choice of voucher or card refund (each behind its own permission), and the required reason (4.22).
- The customer's side: the request form outside the cutoff, and the phone number and opening hours inside it.

### 12. Staff: TMDb review screen

- Search results as a list with poster, title and year.
- The review screen: synopsis, poster, the suggested trailer with alternatives, and the suggested UK age rating, nothing saved until staff confirm (4.15).
- The message and retry button for when TMDb can't be reached.
- Adding a film by hand, for events with no TMDb entry.

### 13. Private hire enquiry form

- The enquiry form: name, email, event type, preferred date, party size and message (4.6).
- The confirmation after sending.
- The staff list of enquiries with their status, and the screening an enquiry became (4.19).

---

[← 3. UX design strategy (the five planes)](ux_design.md) · [README](../README.md)
