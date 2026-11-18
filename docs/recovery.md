# Recovery plan

What happens if the site, its database, the payment provider or email stops working, and how to get back. It goes with [4.31](architecture.md#431-backups-and-restoring) and the [deployment guide](../README.md#deployment).

## What is backed up

The database is the only thing that needs backing up. The code is on GitHub, the static files are rebuilt on every deploy, and the theme is in the repository. A management command dumps the whole database to a file. The routine I'm aiming for is a dump before every release that changes the data model. That's a target: the command isn't built yet, so no dump has been taken.

The database is on Neon's free plan. How often Neon keeps its own copies on that plan, and for how long, is something I haven't checked, so I don't rely on it. The dumps are the backup.

## How much could be lost

Anything since the last dump. Payments are the exception: Stripe keeps its own record of every payment and refund, and `reconcile_pending` can rebuild a booking's payment state from Stripe, so a paid booking can't be lost without trace.

## How long to be back

The target is under an hour from deciding to restore to the site taking bookings again. No restore has been run or timed yet. When I've run one, I'll record how long it took in the development log, and this section will give that time instead of a target.

## Restoring

1. Pause online sales in the venue settings, if the site is still up, so nothing new is sold during the restore.
2. Create an empty database, on Neon or locally, and point `DATABASE_URL` at it for that terminal only, as the deployment guide does for `createsuperuser`.
3. Load the latest dump into it.
4. Run `python manage.py migrate`, which applies any migrations newer than the dump.
5. Run the test suite against it, and check the row counts for bookings, payments and refunds against the dump's.
6. Point the live service's `DATABASE_URL` at the restored database, redeploy, and check the home page, a seat map and the staff needs-attention page.
7. Run the reconciliation check, so any payment Stripe took during the outage is confirmed or refunded.
8. Turn online sales back on.

## While something is down

- The site is down: the routine I'm aiming for is that staff print each screening's guest list before the show, so the door works from paper. Walk-up customers are sold seats at the counter through in-venue booking once the site is back, or turned away if the screening is full on the printed list.
- Stripe is down: pause online sales. In-venue card sales still work, since the card terminal doesn't depend on Stripe.
- Email is down: bookings still go through, and every email waits in the outbox and is retried. The needs-attention page shows anything that failed for good, and staff resend it once email is back.
