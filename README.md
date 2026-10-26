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

The live site is at [regal-cinema.onrender.com](https://regal-cinema.onrender.com).

The project needs a host that can run a Python and Django application with a PostgreSQL database. A static host such as GitHub Pages isn't enough, since the app relies on server-side logic, a live database and Stripe. The web service runs on Render's free plan, and the database is on Neon's free plan, because Render's free databases expire after 30 days. Both are in Frankfurt. The reasons are in the [development log](docs/development_log.md#24-october-2026-production-database-on-neon).

The service is defined in [`render.yaml`](render.yaml). On each deploy Render runs [`build.sh`](build.sh), which installs the requirements, collects static files and applies migrations, then starts gunicorn. WhiteNoise serves the static files from the same process.

To deploy your own copy:

1. Create a project on [Neon](https://neon.tech) with PostgreSQL 17 in AWS Europe Central (Frankfurt). Under Connect, turn connection pooling off and copy the connection string. Django needs the direct connection, not the pooled one.
2. Fork or clone this repository to your own GitHub account.
3. In Render, choose New, then Blueprint, and connect the repository on the `main` branch. Render reads `render.yaml`.
4. When Render asks for `DATABASE_URL`, paste the Neon connection string. Render generates `SECRET_KEY` itself, and `render.yaml` sets `DEBUG` to `False`.
5. Apply the blueprint and wait for the first build. The build log shows the migrations running against Neon.
6. Open `/health/` on the new site. It should return `ok`.
7. Create an admin account. The free plan has no shell on Render, so run `createsuperuser` from your own machine with `DATABASE_URL` set to the Neon string for that terminal session only. Real environment variables take priority over `.env`.

   ```powershell
   $env:DATABASE_URL = "your-neon-connection-string"
   .venv\Scripts\python manage.py createsuperuser
   Remove-Item Env:DATABASE_URL
   ```

8. On [cron-job.org](https://cron-job.org), create a job that requests `/health/` every 10 minutes. Render's free service sleeps after 15 minutes without traffic, and `/health/` makes no database query, so the ping doesn't use Neon's compute allowance.

Every push to `main` deploys automatically. The Stripe keys, webhook secret and TMDb API key will be added to Render's environment settings when those features are built. None of them are committed.

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

### Code from other sources

- The fluid type and space scales in [`static/css/global/tokens.css`](static/css/global/tokens.css) were generated with [Utopia](https://utopia.fyi), by James Gilyead and Trys Mudford, using its default settings. The file notes the settings and links to the calculator that regenerates them.

### Repository layout

To be completed once the structure settles.
