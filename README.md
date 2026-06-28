# The Regal Cinema: Hospitality-First Booking Engine

## 🎭 A Full-Stack Django Application & Algorithmic Design System

## 🎬 Introduction

**The Regal Cinema Booking Engine** is a boutique, commercial-grade business-to-business (B2B) showcase web application engineered for independent, high-end picture houses. Inspired by the premium hospitality models of elite cinema groups like Everyman and Tivoli, this application shifts the digital window of independent cinema from a static noticeboard into an immersive, ambient transaction experience.
The platform is purpose-built to solve a critical commercial bottleneck for boutique venues: standard, off-the-shelf ticketing systems treat cinema seats as uniform inventory, completely decoupling the ticket purchase from premium hospitality workflows. This application introduces an intelligent, full-stack composition that bridges relational database integrity with container-aware user interfaces to maximise bar margins and optimise premium seat configurations.

```text

┌─────────────────────────────────────────────────────────────────┐
  │  THE REGAL CINEMA ENGINE ── Relational continuo architecture     │
  ├─────────────────────────────────────────────────────────────────┤
  │  [Django Backend]   ──►  Atomic SQL validation & Inventory      │
  │  [Every Layout]     ──►  Self-governing viewports (No Break)   │
  │  [Design System]    ──►  Obsidian/Ivory Perceptual Tokens      │
  └─────────────────────────────────────────────────────────────────┘

```

### The Technical Instrumentation

To ensure the codebase remains strictly **DRY (Don't Repeat Yourself)** and highly cohesive, the system architecture treats the backend and frontend as distinct but perfectly harmonised parts of a contrapuntal composition:

- **The Core Database & Ledger:** Built on Python and the Django MVC framework, utilising a relational SQL database layout. The schema is engineered around concrete, real-world constraints, treating showtimes, auditoriums, luxury sofa tiers, and culinary inventories as strict relational nodes to eliminate data anomalies and double-booking race conditions.
- **The Algorithmic Frontend:** Built with raw, highly semantic HTML and bespoke modern CSS primitives inspired by Heydon Pickering and Andy Bell's Every Layout axioms. Rather than loading heavy framework runtimes to map a responsive interface, the application uses self-governing layout primitives (such as the Switcher, Stack, and Sidebar) that allow the browser's native algorithms to handle viewport transitions seamlessly.
- **The Perceptual Design Language:** Guided by Alla Kholmatova's **Design Systems** philosophy, the visual skin uses an integrated set of design patterns and shared vocabulary. The user interface utilises a deep, cinematic dark-mode palette tokenised via global CSS custom properties to replicate the visual gravity and premium weight of a luxury theatre lounge.

---

## <a name="top"></a>📋 Table of Contents

1. [📖 Project Purpose & User Stories](#purpose)
2. [🔬 Strategic Research](#research)
3. [🖼️ UX Design Strategy (The 5 Planes)](#ux-strategy)
4. [🗺️ System Architecture & Logic Maps](#architecture)
5. [✨ Core Features & UI Overhauls](#features)
6. [🌐 Deployment Guide](#deployment)
7. [🤝 Credits & Acknowledgements](#credits)
8. [🏗️ Development Log & Engineering Phases](#dev-log)
9. [🧪 Testing & Quality Assurance Portfolio](#testing)

---

## 1. <a name="purpose"></a> 📖 Project Purpose & User Stories

The overarching purpose of The Regal Cinematic Platform is to modernise the last mile of local independent theater commerce. By replacing a rigid, uninspired layout with an algorithmic, immersive interface, the application bridges the gap between premium physical hospitality and modern digital booking systems.

### 1. The Luxury Patron

_Focus: Frictionless Seat Booking & Table Service Upgrades_

- **User Story:** As a cinema-goer looking for a date night, I want to seamlessly browse showtimes on my smartphone and select specific luxury sofas on an interactive seating chart so that I can secure the best view without rendering glitches.
  - _Acceptance Criterion:_ The seating matrix component must use fluid wrapping mechanics to fit standard phone viewports cleanly, ensuring selectable touch target regions never drop below 44px by 44px.
- **User Story:** As a premium ticket holder, I want to pre-order a bottle of wine and snacks during the checkout flow to be delivered directly to my seat number so that I can skip the bar queue upon arrival.
  - _Acceptance Criterion (BDD):_ **Given** the user has selected a 'Balcony Sofa' ticket, **When** they advance to the optional upgrades phase, **Then** the interface must dynamically render an inventory grid of approved bar items linked explicitly to their session ticket ID.

### 2. The Theater Front-of-House Manager

_Focus: Automated Schedule Orchestration & Inventory Control_

- **User Story:** As the theater manager, I want an administrative dashboard where I can assign a film to a specific screen, set showtimes, and automatically push updates live to the customer-facing front-end.
  - _Acceptance Criterion:_ Creating a new screening entry must trigger automatic validation rules to prevent scheduling overlaps or double-booking conflicts in the database.

## <p align="right">(<a href="#top">Back to top</a>)</p>

## 2. <a name="research"></a>🔬 Strategic Research

### 1. Everyman & Tivoli Cinema Group (The Luxury Hospitality Benchmark)

- **The High Note (What works):** Masterful use of Perceptual Patterns to establish brand identity. The interface utilises full-bleed dark themes, cinematic typography scales, and high-contrast gold accents that make the digital window feel precisely like entering a physical, premium theater lounge. Their checkout flow prioritises food-and-drink "seat service" upsells as a native, elegant feature module rather than a clumsy afterthought.
- **The Flat Note (What fails):** Because they operate as massive corporate chains, their systems are heavily integrated with enterprise ticketing software (like Vista). This creates a highly rigid scheduling layout that cannot easily adapt to hyper-local community events, single-screen live theater rentals, or bespoke artisan screenings.
- **Innovation:** The Regal Cinematic Engine will borrow the dark, immersive aesthetic qualities and table-service transaction logic of the Everyman group but pair it with a lightweight, flexible Django-backed administration model. This empowers local managers to dynamically reconfigure seat matrices, handle local membership clubs, and adjust screen schedules instantly without enterprise corporate bloat.

## <p align="right">(<a href="#top">Back to top</a>)</p>

## 3. <a name="ux-strategy"></a> 🖼️ UX Design Strategy (The 5 Planes)

### Wireframes

![Description](./docs/wireframes/….png)

### I. Strategy

The Strategy Plane establishes the overarching why of the platform, aligning the commercial objectives of a luxury boutique cinema with the lifestyle expectations of its user base.

- **User Goals:**
  - **The Experience Seekers:** Patrons want to transition seamlessly from checking film availability on a mobile phone to configuring a premium night out (selecting luxury sofas, pre-ordering bar refreshments) without experiencing cognitive friction or layout regressions.
  - **The Theatre Administrators:** Managers require an absolute, single source of truth database system to coordinate showtimes, prevent seat inventory overlapping, and track catering fulfillment without technical complexity.
- **Target Audience:** Discerning film enthusiasts, local theatre club members, families looking for premium comfort, and private event hirers in the Evesham and wider Worcestershire area who appreciate the historical Art Deco hospitality of The Regal but expect modern, digital transaction speed.
- **The Future Runway:** The underlying system is engineered to scale from a single-site ticket booker into a regional, multi-tenant boutique theatre SaaS. The architecture leaves a clean, non-breaking runway open to implement localised loyalty schemes, automatic membership subscription recurring billings, and live in-seat table service tracking utilising persistent WebSocket connections.

### II. Scope

#### 1. Core Feature Matrix

To deliver a platform that rivals the premium experience of groups like Everyman or Tivoli, the application's scope must bridge relational database integrity with intuitive, content-driven presentation.

| Feature Area            | In-Scope (MVP Release)                                                                                                            | Out-of-Scope (Future Iterations)                                                                          |
| :---------------------- | :-------------------------------------------------------------------------------------------------------------------------------- | :-------------------------------------------------------------------------------------------------------- |
| **Patron Booking**      | Dynamic selection of specific auditorium seats or premium seating via an interactive, wrapped matrix layout.                      | Real-time split-payment processing between multiple patron wallets.                                       |
| **Hospitality Upgrade** | Contextual food-and-drink pre-ordering mapped to ticket tiers, triggering downstream production tickets for staff.                | Live in-theatre table summoning or post-purchase order amendments via native SMS.                         |
| **Staff Dashboard**     | Relational CRUD interface to map films to screens, establish single-session timelines, and automatically track seat availability. | Predictive algorithmic modelling for ticket price optimisation based on historical local box-office data. |

#### 2. Interface & Presentation Scope (System Axioms)

We reject the convention of writing arbitrary, localised layout hacks or heavy framework wrappers. Instead, the layout generation relies on fundamental rendering logic and native browser algorithms.

- **Dark-Mode Tokens:** The system implements a deeply ambient palette tokenised via global CSS custom properties. The backdrop utilises an obsidian colorway (#0b0b0d) to mimic a cinematic blackout environment, offset by premium ivory text typography (#f5f5f7) and warm gold active states.
- **The Switcher Component:** The checkout interface utilises the native Switcher structural primitive. When rendering the ticket breakdown alongside the interactive seating matrix on a desktop browser, they sit in a horizontal counterpoint. On mobile viewports, the layout self-governs and fluidly shifts into a vertical single-column layout without manual, fragile media query breakpoints.
- **The Frame Primitive:** All film trailers, promotional billing banners, and movie posters are bound tightly within a Frame primitive. This dictates explicit cinematic aspect ratios (such as 16:9 and 2:3) through native properties, ensuring that media scales smoothly without layout shifting or asset skewing.

#### III. Data Security & Integrity

As Marijn Haverbeke notes in Eloquent JavaScript, computers are completely pedantic beasts that require absolute logical clarity. Our system scope enforces strict data boundaries:

- **Concurrency Resolution:** The booking backend handles double-booking conflicts as a strict, atomic database validation layer rather than relying on client-side state.
- **Sensitive Data Constraints:** The backend intentionally restricts the storage of sensitive diagnostic data, customer credentials, or raw payment details. Financial transactions are offloaded entirely to encrypted third-party webhooks, passing only reference receipts back to our local SQL ledger.

### III. Structure (Interaction Design & Information Architecture)

The Structure Plane maps out how the system behaves in response to user intent and details how information flows logically through the application using the Model-View-Controller (MVC) framework.

#### 1. The Interaction Model (The Event Loop)

Following the structural discipline of Eloquent JavaScript, user interactions are managed via asynchronous event orchestration rather than synchronous page refreshes.

```text

[User Clicks "Reserve Sofa"]
          │
          ▼
[View Layer triggers Event Listener]
          │
          ▼
[Controller initiates Asynchronous Fetch API Request]
          │
          ▼
[Model runs Validation Check against PostgreSQL State]
    ├── SUCCESS ──► [Database commits Atomic Transaction] ──► [View Updates DOM State]
    └── CONFLICT ─► [Database rolls back Transaction]    ──► [View renders Error Primitive]

```

#### 2. Information Architecture (Node Mapping)

The site’s data nodes are hierarchically nested to keep user traversal routes as short and clear as possible:

```text

Home View (Current Screenings & Promotional Billing)
  ├── Film Detail View (Trailers, Synopsis, Metadata Tokens)
  │     └── Screening Selection (Date / Time Relational Matrix)
  │           └── Checkout Flow (The Secure Transaction Pipeline)
  │                 ├── Step 1: Seat Allocation Grid (Standalone Primitive)
  │                 ├── Step 2: Hospitality Inventory Menu (Contextual Upgrades)
  │                 └── Step 3: Payment Gate & Ledger Confirmation
  ├── Membership Portal (User Profiles, Passports, Loyalty Ledger)
  └── About / Venue Hire (Static Content, Contact Vectors)

```

### IV. Skeleton (Interface, Navigation, & Information Design)

The Skeleton Plane translates our abstract structures into tangible, wireframe-ready structural layouts. Following Heydon Pickering and Andy Bell's Every Layout axioms, the visual blueprint relies completely on self-governing primitives that treat content as a flexible hypothesis.

- **Interface Layout Design:** The ticket dashboard utilises a dual-axis presentation managed via The Sidebar and The Switcher primitives.
  - On wide media (desktops), the heavy interactive element (the Auditorium Seating Matrix) fills the dominant horizontal space, while the billing breakdown and ticket configuration parameters remain docked to the side.

  - If space is constrained below a strict operational threshold, the layout engine drops the elements into a single-column, linearly stacked vertical layout, preventing clipping or overflow scrolling.

- **Navigation Architecture:** The top navigation bar is orchestrated using The Cluster primitive. Link items, branding marks, and login triggers are distributed evenly. If a patron opens the platform on a narrow viewport, the items automatically wrap or condense into an accessible, touch-friendly tray without breaking the document's header box margins.

- **Information Density & Rhythm:** Vertical relationships throughout long text layouts (such as film synopses, terms of service, or event schedules) are governed entirely by The Stack primitive. Spacing is governed via standard CSS custom properties (var(--space-m)), eliminating the presence of unpredictable margin-collusion errors and maintaining an unbroken reading cadence based on a rigid Modular Scale.

### V. Surface

- **The Cinematic Palette:** The root theme employs dark, rich obsidian backdrops (`#0b0b0d`) to mimic a blacked-out cinema hall, contrasting against sharp ivory text typography (`#f5f5f7`) and striking "Popcorn Gold" or "Velvet Crimson" accent boundaries for active focus states.
- **The Box Primitive:** Applied to film billing cards. Captures padding rhythm entirely through system token variables (`var(--space-m)`), establishing crisp borders (`1px solid var(--border-subtle)`) that cleanly frame the cinematic posters.
- **The Switcher Primitive:** Orchestrates the ticket checkout flow. When space is plentiful on an office screen, the interactive seating chart and the billing sidebar sit elegantly side-by-side. On narrow mobile viewports, the layout algorithmically stacks them into a singular vertical timeline layer—preventing catastrophic horizontal page blowouts.
- **The Frame Primitive:** Applied universally to film trailer video embeddings and poster images. Enforces a strict cinematic aspect ratio (e.g., `16:9` or `2:3`) via raw CSS layout algorithms, guaranteeing content scales smoothly without skewing the dimensions or forcing unexpected runtime component jumps.

## <p align="right">(<a href="#top">Back to top</a>)</p>

## 4. <a name="architecture"></a> 🗺️ System Architecture & Logic Maps

```text

1. Film Model (The Source of Truth) ├── id (PK) ├── title (CharField) ├── duration_minutes (IntegerField) ├── age_rating (CharField: 'PG', '12A', '15', etc.) └── poster_image (ImageField) 2. Screen Model (The Venue Layout) ├── id (PK) ├── name (CharField: 'Main Auditorium', 'Studio Screen') └── total_capacity (IntegerField) 3. Screening Model (The Relational Bridge) ├── id (PK) ├── film_id (FK -> Film) ├── screen_id (FK -> Screen) ├── date_time (DateTimeField) └── base_ticket_price (DecimalField) 4. Seat Model (The Grid Array) ├── id (PK) ├── screen_id (FK -> Screen) ├── row_label (CharField: 'A', 'B', 'C') ├── seat_number (IntegerField) └── tier (CharField: 'Standard Seat', 'Luxury Sofa') 5. Booking Model (The Transaction) ├── id (PK) ├── screening_id (FK -> Screening) ├── user_id (FK -> User) ├── seat_id (FK -> Seat) ├── pre_ordered_bar_items (JSONField / Relational Model) └── is_paid (BooleanField)

```

## <p align="right">(<a href="#top">Back to top</a>)</p>

## 5. <a name="features"></a> ✨ Core Features & UI Overhauls

## <p align="right">(<a href="#top">Back to top</a>)</p>

## 6. <a name="deployment"></a> 🌐 Deployment Guide

This project was developed using Git version control and is hosted on GitHub. It has been deployed as a live web application using **GitHub Pages**.

### Deployment Steps

To deploy the site to GitHub Pages, the following steps were executed:

1. **Repository Access:** Click on the **Settings** tab located in the repository's main navigation bar.
2. **Pages Configuration:** In the left-hand sidebar, click on **Pages**.
3. **Source Selection:** Ensure the "Source" dropdown is set to **Deploy from a branch**.
4. **Branch Targeting:** Select the **`main`** branch, and ensure the folder dropdown is set to **`/ (root)`**.
5. **Save & Build:** Click the **Save** button to trigger the automated GitHub Actions build workflow.
6. **Live Link:** After a few minutes, the link appears at the top of the settings page: _"Your site is live at [[URL](https://)]"_.

### Local Deployment (Cloning)

To run this project locally on your own machine:

### ⚡ Quick Local Spin-Up Alternatives

## <p align="right">(<a href="#top">Back to top</a>)</p>

## 7. <a name="credits"></a> 🤝 Credits & Acknowledgements

### AI Pair Programming & Academic Integrity

Artificial Intelligence (LLMs) was utilised strictly as a "Pair Programmer" and strict linter throughout the development lifecycle to accelerate cross-browser debugging, reflow profiling, and formatting, ensuring absolute human ownership and comprehension of the overarching engine code.

### Technologies Used

### 📂 Repository Structural Layout

## <p align="right">(<a href="#top">Back to top</a>)</p>

## 8. <a name="dev-log"></a>🏗️ Development Log & Engineering Phases

### Phase 1:

<details>
<summary><b>🔍 Expand Engineering Case Study: Phase 1</b></summary>

####

</details>

### Phase 2:

<details>
<summary><b>🔍 Expand Engineering Case Study: Phase 2</b></summary>

####

####

</details>

### Phase 3:

<details>
<summary><b>🔍 Expand Engineering Case Study: Phase 3</b></summary>

####

####

</details>

###

<details>
<summary><b>🔍 Expand Engineering Case Study: Phase 4</b></summary>

####

####

</details>

###

<details>
<summary><b>🔍 Expand Engineering Case Study: Phase 5</b></summary>

####

####

###

</details>

###

###

<details>
<summary><b>🔍 Expand Engineering Case Study: Phase 7</b></summary>

####

####

####

####

</details>

###

## <p align="right">(<a href="#top">Back to top</a>)</p>

## 9. <a name="testing"></a> 🧪 Testing & Quality Assurance Portfolio

This section outlines the holistic verification suite executed to guarantee the engineering integrity, mathematical precision, and cross-platform accessibility of…

### 1. Manual Testing Matrix (Boundary Explorations)

### 2. User Story Testing (Behavior-Driven Verification)

Verification of core target audience features mapped back to the primary user requirements.

### 3. Validator Testing

### 4. Lighthouse Testing

### 5. Browser Compatibility

Cross-origin audio context rendering pipelines were explicitly verified across major rendering engines:

### 6. Responsiveness Testing

### 7. Automated End-to-End Testing

### 8. Bugs Fixed (Sprint Log)

### 9. Known Issues

<p align="right">(<a href="#top">Back to top</a>)</p>
