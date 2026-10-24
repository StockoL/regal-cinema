# 2. Research

## Everyman and Tivoli

Both are cinema groups with a dark, premium look that matches the in-person experience, and both put food and drink ordering inside the booking flow instead of leaving it as an extra. I've taken the dark visual language and the idea that pre-ordering belongs in checkout.

What I haven't taken is the technology. Large chains run enterprise ticketing platforms (Vista, for example) built to serve many venues at once. That is far more than a single independent site needs, and it makes small-venue details such as a local membership scheme or one-off private hire harder to support. This project does the same job with a much smaller, single-venue Django backend.

## The Regal in Evesham

The real venue gave me concrete facts to model instead of guesses. It has two seating areas, stalls and circle, and the price doesn't change with where you sit. It sells four kinds of ticket: adult, student, OAP (discounted), and free baby tickets. A baby doesn't need a seat, since they sit on a lap or stay in a pushchair. It also prices whole showings differently (Silver Screen, Family Super Saver, Subtitled and so on), which is why a screening has a ticket class as well as a ticket type per customer. See [4.1](architecture.md#41-screenings) and [4.18](architecture.md#418-ticket-classes-membership-tiers-and-priority-booking).

From using its booking pages as a customer, I set three goals for this project:

- A seat should be available to other people as soon as I let it go, whether I cancel or choose different seats.
- I should be able to go back a step and change my seats or tickets without starting the booking again.
- The price I'm shown should match the ticket type I chose, whichever seat I pick.

## Modern cinema booking interfaces (Dribbble)

I also reviewed three contemporary cinema and booking concepts on Dribbble for interaction and layout ideas: [Cinema Ticket Booking](https://dribbble.com/shots/20127096-Cinema-Ticket-Booking), [Movie theatre website](https://dribbble.com/shots/22698980-Movie-theatre-website) and [Cinema Website Design](https://dribbble.com/shots/25157583-Cinema-Website-Design). I wasn't after their branding. They lean on a bold, corporate multiplex colour scheme that doesn't suit a boutique venue. What I took was patterns of behaviour and structure, translated into this project's own look. Section [3](ux_design.md) shows how each became a named design pattern.

- Horizontal, categorised browsing rows, in the style of Netflix, suit grouping screenings by category (What's On, Coming Soon, discounted showings). I built this as a named composition pattern, the Reel (3.II), instead of a generic carousel.
- A date strip with a grouped, pill-shaped showtime picker is clearer at a glance than a plain list of times, and it works as well in a dark, gold-accented palette as in the original colours.
- A live-updating order summary during booking is a usability principle I wanted to design in from the start (see 4.20).
- Letting real film posters and stills carry the visual weight, with minimal interface around them, suits a project that uses real TMDb imagery (4.15) instead of stock photography.
- Smooth transitions between pages are possible with the browser's native View Transitions API on top of ordinary server-rendered pages, with no client-side framework.

I decided against three things:

- Hover-triggered autoplay video previews, which conflict with the no-autoplay accessibility commitment in 4.17.
- A true single-page-app architecture, which conflicts with the server-rendered templates decision in section 3. I only want the transition feel.
- Dense catalogue layouts. Several of the concepts are built for chains with dozens of screens. A single-screen venue showing a handful of films a week would look sparse trying to match that, so I use fewer, roomier rows.

---

[← 1. Project purpose and user stories](user_stories.md) · [README](../README.md) · [3. UX design strategy (the five planes) →](ux_design.md)
