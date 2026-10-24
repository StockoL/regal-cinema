# Regal Cinema booking platform

A full-stack Django application

## Introduction

Regal Cinema is a fictional boutique cinema, modelled on the Regal in Evesham, and this is the Django booking platform I'm building for it as my Milestone 4 submission. The real Regal is an independent cinema with stalls and circle seating, a bar, a membership scheme and private hire, and those are the things I wanted the software to handle properly.

Many small independent cinemas run on generic ticketing systems that treat every seat and every ticket the same. Food and drink, membership, and private hire get bolted on afterwards, if they're handled at all. I've built them in as core features instead. I also wanted the booking flow itself to be forgiving: a customer can go back and change their mind without starting again, and a seat they let go of is available to someone else straight away.

```text
Django (data model, business logic)
  └─ Server-rendered templates
       └─ CSS design system + a small amount of hand-written JavaScript
```

### Technical approach

- The backend is Django with a PostgreSQL database. The schema follows the venue's real domain (screenings, seats, ticket types, bookings, concessions, membership), and constraints in the database stop the same seat being sold twice.
- The frontend is server-rendered Django templates, plain CSS and a small amount of JavaScript. I haven't used a frontend framework. The reasoning is in the [UX design strategy](docs/ux_design.md#design-principles).
- The visual style is a dark, cinema-inspired design system made from a small set of reusable layout and colour patterns, based on _Every Layout_ (Heydon Pickering and Andy Bell) and Alla Kholmatova's _Design Systems_.

### Key features

- Seat selection on an interactive stalls and circle seating plan, with short-lived holds so a seat is never double-booked ([4.8](docs/architecture.md#48-core-flow-seat-selection-and-holds))
- A ticket type for each seat (adult, student, OAP, child), free infant tickets, and ticket classes for discounted showings such as Silver Screen ([4.18](docs/architecture.md#418-ticket-classes-membership-tiers-and-priority-booking))
- Food and drink pre-ordered in the same checkout, paid through Stripe ([4.13](docs/architecture.md#413-business-rule-payment-lifecycle-online))
- Paid Friend membership with priority booking and discounts, plus gift vouchers ([4.10](docs/architecture.md#410-business-rule-discount-and-voucher-order))
- Private hire enquiries, and permission-based staff tools with an audit log and sales dashboard ([4.9](docs/architecture.md#49-staff))

The full list, app by app, is in [Core features](docs/features.md).

## Contents

- [Documentation](#documentation)
- [Deployment guide](#deployment)
- [Credits and acknowledgements](#credits)

## <a name="documentation"></a> Documentation

I've kept the design and planning detail in [`docs/`](docs/) so this README stays short. The documents are numbered in reading order, and when I write a cross-reference such as "see 4.10", it points at a numbered section in them.

| #   | Document                                                     | What's in it                                                                                           |
| :-- | :----------------------------------------------------------- | :----------------------------------------------------------------------------------------------------- |
| 1   | [Project purpose and user stories](docs/user_stories.md)     | MoSCoW prioritisation, and 17 customer and staff journeys written as Given/When/Then scenarios          |
| 2   | [Research](docs/research.md)                                 | Everyman and Tivoli, the real Regal in Evesham, and the Dribbble booking concepts I drew on             |
| 3   | [UX design strategy](docs/ux_design.md)                      | The five planes: strategy, scope, structure, skeleton and surface, including the CUBE CSS approach     |
| 4   | [System architecture and data model](docs/architecture.md)   | The seven Django apps, every model and relationship, and the business rules (holds, payment, refunds) |
| 5   | [Core features](docs/features.md)                            | Customer-facing and staff-facing features for each app, and the permission model                      |
| 6   | [Development log](docs/development_log.md)                   | The planned build phases, to be filled in as development happens                                      |
| 7   | [Testing and quality assurance](docs/testing.md)             | The testing plan, validators, Lighthouse, browser checks and known issues                              |
| 8   | [Future business ideas](docs/future_ideas.md)                | Loyalty points, newsletters and goodwill discounts, kept out of the initial build on purpose           |

## <a name="deployment"></a> Deployment guide

The project needs a host that can run a Python and Django application with a PostgreSQL database. A static host such as GitHub Pages isn't enough, since the app relies on server-side logic, a live database and Stripe. I'm deploying to Render. Its free web service stops after a period without traffic, so a scheduled request from cron-job.org keeps the site responsive.

This section will be filled in with the exact steps once the project is deployed. The plan:

1. Push the project to GitHub, including a `requirements.txt`.
2. Create a web service on Render connected to the GitHub repository, with the build and start commands for Django and gunicorn.
3. Add a managed PostgreSQL database and connect it with an environment variable such as `DATABASE_URL`.
4. Set environment variables for `SECRET_KEY`, the Stripe keys and webhook secret, and the TMDb API key. None of these are committed to the repository.
5. Set `DEBUG = False` for production.
6. Run migrations against the production database.
7. Point the Stripe webhook (in test mode) at the deployed endpoint.
8. Check that the live site matches the development version and that static files are served correctly.
9. Set up the cron-job.org request to the site.

### Local deployment

The project runs on PostgreSQL locally as well as in production, never SQLite. The reasons are in the [development log](docs/development_log.md#24-october-2026-local-postgresql). On Windows:

1. Install PostgreSQL 17 with `winget install PostgreSQL.PostgreSQL.17`. The installer asks you to set a password for the `postgres` superuser.
2. Create a role and a database for the project. `psql` is in `C:\Program Files\PostgreSQL\17\bin` if it isn't on your PATH.

   ```text
   psql -U postgres -c "CREATE ROLE regal WITH LOGIN PASSWORD 'choose-a-password' CREATEDB;"
   psql -U postgres -c "CREATE DATABASE regal_cinema OWNER regal;"
   ```

   The role needs `CREATEDB` so Django's test runner can create and drop its own test database.
3. Add the connection string to a `.env` file in the project root. This file is never committed.

   ```text
   DATABASE_URL=postgres://regal:choose-a-password@localhost:5432/regal_cinema
   ```

On macOS or Linux, install PostgreSQL 17 with your package manager (Homebrew, apt) and run the same two `psql` commands.

The remaining steps (clone, virtual environment, install requirements, migrate, run the server) will be added once the project skeleton exists.

### Quick local spin-up alternatives

To be completed.

## <a name="credits"></a> Credits and acknowledgements

### Technologies used

Django, PostgreSQL, Stripe (test mode), The Movie Database (TMDb) API, Render and cron-job.org. The design system draws on CUBE CSS, _Every Layout_ and the View Transitions API. To be completed with versions as the build goes on.

This product uses the TMDB API but is not endorsed or certified by TMDB.

### Design references

- Andy Bell, CUBE CSS
- Heydon Pickering and Andy Bell, _Every Layout_
- Alla Kholmatova, _Design Systems_
- Jesse James Garrett, _The Elements of User Experience_
- The three Dribbble concepts linked in [Research](docs/research.md#modern-cinema-booking-interfaces-dribbble)

### Repository layout

To be completed once the structure settles.
