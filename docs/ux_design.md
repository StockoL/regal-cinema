# 3. UX design strategy (the five planes)

This section follows Jesse James Garrett's five planes (strategy, scope, structure, skeleton, surface), moving from the most abstract decisions to the most concrete.

## Wireframes

The brief for each wireframe, and the wireframes themselves once they're drawn, are in [Wireframes](wireframes.md). It lists the screens in build order, what each has to show, and the questions each drawing has to answer.

## I. Strategy

- User goals: customers want an easy way to see what's on, book the seats they want, and add food and drink if they like. Staff want a simple way to manage screenings and see bookings without a developer.
- Site goals: encourage food and drink add-ons, and build repeat custom through the membership scheme.
- Target audience: local film-goers who want a more comfortable, hospitality-led experience than a multiplex. That includes families and older customers (served by discounted showings such as Family Super Saver and Silver Screen), students, and people hiring the venue privately.

## II. Scope

### Feature summary

| Area           | In scope                                                                                                                                           | Out of scope (for now)                               |
| :------------- | :------------------------------------------------------------------------------------------------------------------------------------------------- | :--------------------------------------------------- |
| Booking        | Seat selection on an interactive seating plan (stalls and circle), a ticket type for each seat, free infant tickets, going back to amend a booking | Split payments between several people on one booking |
| Food and drink | Pre-ordering linked to a booking                                                                                                                   | Live in-seat ordering during a screening             |
| Membership     | Paid, tiered Friend membership (priority booking, ticket and food discounts), gift vouchers                                                        | Automatic recurring renewal and billing              |
| Staff          | Permission-based staff tools for films, screens, screenings, bookings, cancellations and enquiries                                                 | Automated pricing based on historical sales data     |

### Design principles

I'm not using a frontend framework. The interface is plain, semantic HTML and CSS, with no React or Vue and no build step, organised with Andy Bell's CUBE CSS: composition, utility, block and exception. CUBE CSS uses _Every Layout_ as its composition layer, so adopting it extends the no-framework decision instead of adding a competing one.

- Composition is the _Every Layout_ patterns: a stack for consistent vertical spacing, and a switcher for elements that sit side by side on desktop and stack on mobile without manual breakpoints. I've added one of my own, the Reel, a horizontally scrolling, snap-aligned row for browsing screenings by category (see [2](research.md)). It uses native `overflow-x` and `scroll-snap` instead of a JavaScript carousel library, so touch scrolling and keyboard access come with the browser. These patterns control arrangement, not appearance.
- Utility is small single-purpose classes for common needs. A `.visually-hidden` class holds text that a screen reader announces but sighted users don't see, and I use it for the seat map's accessible seat names ([4.17](architecture.md#417-accessibility-implementation)). Spacing utilities are built on the same CSS custom properties as the design tokens, such as `var(--space-m)`.
- Block is the reusable components, each with its own scoped styles: `.seat-map`, `.film-card`, `.nav`, and the pill-shaped showtime picker beside a date strip. This is where the film poster cards from the Surface plane are built, as a named self-contained block.
- Exception is a scoped override for a component in an unusual state, applied through data attributes instead of more classes. It maps directly onto the seat map's states ([4.8](architecture.md#48-core-flow-seat-selection-and-holds)). Each seat carries a single `data-seat-status` attribute, and the exception layer defines what changes for each value, so the styling for every state lives in one place.

Beyond keeping the CSS organised, this gives the project a consistent naming convention. "Why is this class named like that?" has a one-word answer: which of the four layers it belongs to.

Navigation between pages uses the browser's native View Transitions API to soften the change into a brief crossfade. It borrows the feel of a single-page app without its architecture, which would conflict with the server-rendered approach.

- Palette: a dark background, light text, and a warm accent colour for interactive states, to evoke an auditorium instead of a typical light-mode web app.
- Media framing: posters and trailers sit at fixed aspect ratios so the layout doesn't jump as images load.

### Data and security principles

- Double-booking is prevented at the database level with a unique constraint, not just in the interface, so it holds even if two requests arrive almost together.
- No card details or passwords are stored by me. Payments go through Stripe and only a payment reference is kept locally.

## III. Structure

### Interaction model

Actions that need a live check against the database, most importantly reserving a seat, use a JavaScript fetch request instead of a full page reload. The page can then show an inline error such as "that seat was just taken" without losing the customer's other selections.

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

Every later step is an ordinary server-rendered page, so the browser's back button works and a customer can return to an earlier step and change their choices (see 4.8).

### Site map

```text
Home (what's on)
  └─ Film detail (synopsis, trailer, showtimes)
        └─ Screening (seat selection, ticket types)
              └─ Checkout (add food/drink → pay)
  My bookings (history, cancellation requests)
  Membership / account (profile, vouchers)
  About / private hire (static content, enquiry form)
```

## IV. Skeleton

- Booking page layout: the seating plan and order summary sit side by side on wide screens and stack on narrow ones, using the switcher pattern instead of a breakpoint for each screen size.
- Navigation: a simple top nav bar (the cluster pattern) that wraps onto a second line on small screens instead of switching to a separate mobile menu. The full design is below.
- Content spacing: long text such as synopses and policies uses consistent vertical spacing from CSS custom properties, so I don't repeat one-off margin values.

### Main navigation

The site name links home, followed by the same short menu on every customer page, defined once in `base.html`:

- Logged out: What's on, Membership, Private hire, About, Log in, Register.
- Logged in: What's on, Membership, Private hire, About, My bookings, Account, Log out.

Six or seven links fit on one line at desktop width and wrap cleanly on a phone, which is why I don't need a hamburger menu. Log out is a small form with a button, since logging out changes state and shouldn't happen from a plain link. The current page's link carries `aria-current="page"`, styled so it's visible without relying on colour. A "Skip to main content" link comes first on every page and appears when focused.

The footer holds the venue's phone number and opening hours, the accessibility policy and the membership terms. The phone number is there because it's the route for a cancellation inside the cutoff (4.22).

The staff area has its own navigation in its own base template: Screenings, Films, Bookings, Enquiries, Sales, Audit log and Settings. A link only appears if the staff member holds the permission that area needs, but hiding it is a convenience. The view still checks the permission on the server (4.9). Nothing in the customer navigation links to `/staff/`.

## V. Surface

- Palette: dark background (`#0b0b0d`), light text (`#f5f5f7`), and a warm gold accent for active and selected states.
- Cards: film posters and information sit in a simple bordered card with consistent internal padding.
- Media: trailers and posters are constrained to fixed aspect ratios (16:9 for video, 2:3 for posters) so they scale without distortion or layout shift.

---

[← 2. Research](research.md) · [README](../README.md) · [4. System architecture and data model →](architecture.md)
