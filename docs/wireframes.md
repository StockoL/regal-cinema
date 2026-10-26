# Wireframes

This is the brief I'm drawing the wireframes against, and where they'll sit once they're done. It belongs to the skeleton plane of the [UX design strategy](ux_design.md). Each screen lists what has to be on it, taken from the [user journeys](user_stories.md) and the [architecture](architecture.md), the questions only a drawing will answer, and the wording I still need to write.

I'm drawing them in Excalidraw, low fidelity: grey boxes, real labels, a crossed box for each image, and notes in the margin wherever behaviour isn't visible. Every screen gets two frames, phone (375px) and desktop (1280px). The exports and the `.excalidraw` source files both go in `docs/wireframes/`, named by number and width, such as `01-home-mobile.png`, `01-home-desktop.png` and `01-home.excalidraw`, and the exports get added under their screen below.

The order follows when each screen is needed. Screens 1 to 8 are this week's. The membership page comes before 7 December, and the gift voucher page, the TMDb review screen and the private hire form before 21 December. I'm not wireframing the Django admin or the sales dashboard's layout.

## Status

| #   | Screen                                             | Due       | Journeys      | Phone | Desktop |
| :-- | :------------------------------------------------- | :-------- | :------------ | :---- | :------ |
| 1   | Home: the Reel and the discounted row              | 1 Nov     | 1, 9          | To do | To do   |
| 2   | Film page and showtimes by date                    | 1 Nov     | 1             | To do | To do   |
| 3   | Seat map with ticket types and the live summary    | 1 Nov     | 2             | To do | To do   |
| 4   | Basket and checkout                                | 1 Nov     | 3, 5, 6       | To do | To do   |
| 5   | Return pages: confirming, not completed, outcomes  | 1 Nov     | 6             | To do | To do   |
| 6   | Customer cancellation request and decline message  | 1 Nov     | 7             | To do | To do   |
| 7   | Staff: the till                                    | 1 Nov     | 14            | To do | To do   |
| 8   | Staff: the cancellation queue                      | 1 Nov     | 7, 15         | To do | To do   |
| 9   | Membership page                                    | 7 Dec     | 8, 9          | To do | To do   |
| 10  | Gift voucher page                                  | 21 Dec    | 18            | To do | To do   |
| 11  | Staff: TMDb review screen                          | 21 Dec    | 13            | To do | To do   |
| 12  | Private hire enquiry form                          | 21 Dec    | 10            | To do | To do   |

## Shared layout

Every customer page uses the same header, menu and footer, so I'll draw these once on the home page and reuse them.

- Header with the site name linking home.
- Main menu. Logged out: What's on, Membership, Private hire, About, Log in, Register. Logged in: What's on, Membership, Private hire, About, My bookings, Account, Log out. It wraps onto a second line on a phone instead of hiding behind a menu button.
- Footer with the venue's phone number, address and opening hours, the accessibility policy, the membership terms, and the line "Regal Cinema is a fictional venue created for a course project."
- A "Skip to main content" link, shown when it has keyboard focus.

The staff pages (screens 7, 8 and 11) have their own header and menu, clearly different from the customer site, showing only the items a staff member's permissions allow.

## This week

### 1. Home: the Reel and the discounted row

- Named rows that scroll sideways (the Reel, 3.II): What's On, Coming Soon, and the discounted row, which holds screenings whose ticket class is marked as discounted, such as Silver Screen (4.1).
- Each film card: poster, title, age rating, and the captions and audio description flags, visible without opening the film.
- A priority screening shown greyed out with its text label, linking to the membership page (4.18).
- A showing whose online sales have closed, labelled with the phone number. By default sales close at the listed start time (4.23).
- An empty row.

Cancelled screenings don't appear at all (4.11), so there's nothing to draw for them here.

Questions to answer: does a card stand for a film or a single screening? Where do the priority and sales-closed labels sit on a card? How does a row show that it scrolls?

Wording to write: the priority label with dates, the "Friends only" label, the sales-closed label and the empty-row message.

### 2. Film page and showtimes by date

- Poster, title, the age rating shown prominently, runtime and synopsis.
- The line asking customers to bring photo ID showing their date of birth (4.1).
- The trailer, played only when clicked and never automatically. With no trailer, the space isn't shown at all.
- A date strip, and that date's showtimes as pill buttons. Each pill shows the time, the ticket class, the captions and audio description flags, and its state: available, priority or sales closed. Cancelled and private screenings never appear.
- "The circle is reached by stairs only. The stalls are step-free." (4.17)
- A date with nothing showing.
- The separate page for an old link to a cancelled screening: "This screening has been cancelled", with a link back to the listings.

Question to answer: on a phone, does the synopsis come before or after the showtimes?

Wording to write: the photo ID line, the message for a date with nothing showing, and the cancelled screening page.

### 3. Seat map with ticket types and the live summary

- Stalls and circle, labelled, with the screen's position marked. Rows and seats sit on a grid, with empty columns for aisles and gaps (4.1).
- The key has four states: available, selected, sold (crossed out) and outside section, for an area closed for this screening. Wheelchair spaces and seats out of use have their own marks. No state relies on colour alone (4.17).
- A sofa drawn as one shape holding two separately numbered seats, and the circle boxes labelled "Box C" and "Box D".
- The stairs line from screen 2, next to the key.
- After choosing seats, a ticket type and its price for each seat. Only the types the film's rating allows are offered, and each shows its age band from its description.
- The infant counter, with "Under 2s sit on a lap. If they need their own seat, add a Child ticket." It isn't offered on 15 and 18 films.
- The message for a booking that has infants or Child tickets but no ticket that doesn't need an adult.
- A seat taken by someone else in the meantime: that seat marked, the other selections kept.
- Once seats are held, the hold timer and a Cancel button.
- The sales-closed state, with the phone number instead of a seat map.
- The live summary (4.20): kept in view, with a line per ticket type, the infants and the total, updating the moment anything changes.

The map is one tab stop with arrow keys between seats (4.17), which doesn't need drawing, but the frame should show where focus would start.

Questions to answer: how do long rows fit a phone, by scrolling sideways or by shrinking? Where does the live summary sit on a phone, and what changes in it?

Wording to write: the seat-taken message, the hold timer text, the screen reader name for each seat state, the accompanying-ticket message and the sales-closed message.

### 4. Basket and checkout

Payment happens on Stripe's hosted Checkout page (4.13), so there's no card field on this site.

- The basket from the pending booking: seats and ticket types, infants, food and drink with plus and minus buttons, the voucher field, and the membership discounts.
- The total, with the cancellation policy next to it.
- "Bring proof of age or status", for any ticket type that needs it.
- The test-mode warning: never enter a real card, use Stripe's test cards.
- Back and Change links, the hold timer, and a button that goes to Stripe.
- A box in the flow standing for Stripe's page, where card entry and declined cards are handled.

Wording to write: the test card warning and the proof reminder.

### 5. Return pages: confirming, not completed, outcomes

- Confirming: the customer is back before Stripe's webhook has arrived. The page says the payment is being confirmed and updates itself.
- Success: a prominent booking reference that works as a ticket on a phone, the film, date, time and screen, the seats and ticket types, the infant count, the amount paid by card and any voucher amount applied, the proof reminder if it applies, what to do on arrival, the cancellation policy, and links to My bookings and What's on.
- Not completed: the customer backed out of Stripe's page, no payment was taken, the seats are still held with the time left, and they can try again.
- Hold expired: back to the seat map with a plain explanation.
- Refunded: a payment landed after the seats had gone, and it's been refunded automatically.

Wording to write: all five messages.

### 6. Customer cancellation request and decline message

- My bookings, with each booking's status and reference, upcoming and past separated, and a booking's detail.
- Outside the cutoff: the request form, with an optional reason, and what the customer will get back (a voucher for the booking's value minus any cancellation fee, 4.22).
- Inside the cutoff: no form, and the venue's phone number and opening hours instead.
- The confirmation after a request, saying staff will look at it.
- The decline message, with the staff member's note, and the booking back to paid.
- A booking for a cancelled screening, showing as cancelled with its voucher or refund.

Wording to write: the request confirmation, the inside-the-cutoff text and the decline message.

### 7. Staff: the till

- Choosing a screening, then the same seat map and ticket type choices as screen 3.
- Looking up a member by email to apply their discount, or carrying on as an anonymous sale.
- Food and drink, and the total.
- Marking the booking paid once the venue's card machine has taken payment (4.14).
- The proof reminder for concessionary tickets, and the booking reference to give the customer.
- Finding an existing booking by its reference.

### 8. Staff: the cancellation queue

- The queue of customer cancellation requests, oldest first, with each booking's details.
- Approving with a voucher (the booking's value minus any fee) or declining, with a note required either way (4.22).
- The Manager's version, which also offers a card refund as an exception, with a reason.

Wording to write: the headings and the confirmation messages for approving and declining.

## Before 7 December

### 9. Membership page

- The tiers, each with its price and benefits: priority booking hours, ticket discount, and the food and drink discount for the higher tier (4.4, 4.18).
- Buying a tier, through the same Stripe hand-off as a booking.
- The 14-day refund rule in one sentence (4.22).
- A lapsed member's renewal prompt.

## Before 21 December

### 10. Gift voucher page

- Buttons for £10, £20, £50 and £100, and an "other amount" field for whole pounds within the venue's limits (4.26).
- The 14-day refund rule in one sentence (4.22).
- The note that buying needs an account.
- The code shown on screen after payment, and the optional gift message (a Could).
- The remaining balance after a part-covered booking, and a used-up code's message.

### 11. Staff: TMDb review screen

- Search results as a list with poster, title and year.
- The review screen: synopsis, poster, the suggested trailer with alternatives, and the suggested UK age rating, nothing saved until staff confirm (4.15).
- The message and retry button for when TMDb can't be reached.
- Adding a film by hand, for events with no TMDb entry.

### 12. Private hire enquiry form

- The enquiry form: name, email, event type, preferred date, party size and message (4.6).
- The confirmation after sending.

---

[← 3. UX design strategy (the five planes)](ux_design.md) · [README](../README.md)
