# 8. Marketing development thoughts (future business ideas)

Everything in this section is out of scope for the initial build. The core of the project follows the real Regal in Evesham as closely as I can (ticket classes, ticket types, paid Friend membership, gift cards, cashless payments) instead of features I invented without a real equivalent to check them against. These ideas came out of earlier design sessions. I've kept them in full, not because I'm building them now, but because the reasoning took effort and could become a business development pitch later, once the core platform exists and perhaps after a conversation with the venue.

## 8.1 Loyalty points scheme

A free, automatic points scheme, separate from the paid Friend tiers. Anyone with an account earns points on each booking, redeemable toward a free ticket once a threshold is reached.

`LoyaltyTransaction`: `user` (FK), `points_change`, `reason`, `related_booking` (nullable FK), `created_at`. This is a ledger of individual earn and spend events, not a single changing counter on the profile. It gives an auditable history and avoids two simultaneous transactions corrupting a shared counter. A user's balance is the sum of their transactions.

To avoid inventing a second redemption mechanism, when a member's balance crosses the reward threshold the system would issue a `Voucher` (worth one standard ticket, `source='loyalty_reward'`), which then goes through the same checkout logic as a purchased gift card. One mechanism, two ways of earning it, the same principle as screening-cancellation refunds reusing `Voucher`.

A proposed rate, illustrative and not taken from the real scheme. The real Regal does run a loyalty scheme (its terms and conditions cover it in sections 5.12, 7.6, 7.7 and 8.9), but mine stays a future idea, outside the initial build, and the numbers here are my own starting proposal rather than a copy of theirs. A simple, easily explained rate would be 1 point per £1 spent (tickets and concessions) with 100 points earning a free standard ticket, roughly a "buy nine, get the tenth free" card, which most customers recognise. Both values would be stored as single configurable settings instead of hard-coded, so they could be tuned once real spending data showed whether it's sustainable for the venue's margins. That is a business decision I shouldn't guess at permanently.

Points would also need an expiry rule, so that a balance from years ago doesn't sit on the books indefinitely. The simplest version expires points a set time after they were earned, recorded as a negative `LoyaltyTransaction` so the ledger still adds up.

## 8.2 Newsletter and promotional emails

- `NewsletterSubscriber`: `email` (unique), `user` (nullable FK, linked automatically if the email matches a registered account), `opt_in_deals`, `opt_in_digest` (both boolean, default `False`), `subscribed_at`, `is_active`. It isn't part of `Profile`, because anyone could subscribe from the site footer without an account.
- `NewsletterCampaign`: `subject`, `body`, `campaign_type` (`one_off_deal` or `monthly_digest`), `status` (`draft` or `sent`), `created_by` (FK to staff), `sent_at`.
- `PromoCode`: `code`, `discount_percent`, `valid_from`, `valid_until`, `max_total_redemptions` (nullable, unlimited if blank), `times_redeemed`, `is_active`. This is a shared, rule-based marketing code, modelled separately from `Voucher`. A `Voucher` is a personal balance spent down by one holder over time, while a promo code is redeemed by potentially hundreds of subscribers, once each, within a date window. Forcing that into a balance would let the first few customers drain a "balance" meant to serve everyone.

Consent. There would be two separate opt-in checkboxes at subscribe time, for deals and for the monthly digest, both unticked by default. Having an account would never imply consent to marketing email, in line with UK PECR rules on marketing communications.

There would be two campaign types, each with a "Book now" button:

- The monthly digest would be drafted by the system and not written from scratch. It would pull newly added films and upcoming screenings since the last digest, reusing data in `screenings`, and compose a draft with a "Book now" button under each item linking to that film or screening. As with TMDb (4.15), the system drafts and a person confirms before it sends. It would never send automatically.
- A one-off deal would be written by staff, since "£5 tickets this weekend" isn't something a system could sensibly invent. It could link to a `PromoCode`, with the code pre-filled at checkout by a URL parameter on the button.

The membership upsell. The subscription confirmation and every digest would include a short block ("Members get priority booking and ticket discounts, create an account"), but only for subscribers without a linked account.

Unsubscribe would reuse the signed-token pattern from email verification and password reset (4.16), one mechanism for several uses.

At real scale, bulk marketing email and transactional email (confirmations, password resets) are usually sent through separate infrastructure, because a spam-flagged newsletter can damage deliverability for the transactional email that matters. I'd want to know that, but it isn't worth solving at this stage.

## 8.3 Staff goodwill discounts

The motivating scenario was a disgruntled patron, or someone whose membership hadn't quite synced, and front-of-house staff having the flexibility to put it right on the spot.

Part of this is now in the core build. Staff with the right permission can issue a voucher or a refund on their own judgement, with a required reason in the audit log (4.9, 4.22). What stays out of the initial build is the flat discretionary discount on a booking:

- `Booking.staff_discount_pence` (nullable), a flat discretionary discount applied on top of whatever the booking already qualifies for.
- A configurable cap on that discount for Front of House, stored as a single changeable value, with Manager able to exceed it.
- Every use logged to `AuditLogEntry` (`action_type='manual_discount'`) with a required reason.

I moved this out because there's no evidence the real Regal operates this way. Its site shows fixed ticket classes and a structured membership scheme, not visible discretionary pricing. Keeping the first build close to what I can verify took priority over a plausible feature with no real-world counterpart. The mechanism (bounded discretion, mandatory logging) would be a reasonable addition if a venue wanted it.

## 8.4 A per-ticket booking fee

The real Regal adds a booking fee of £3.75 to each ticket, and doesn't refund it. I've left it out. Customers see the ticket price they pay, the totals in 4.10 stay simple, and a refund or voucher covers the whole amount paid. If a venue wanted one, it would be a venue setting (4.23), shown as its own line in the booking summary and kept out of the refundable amount, with the rule stated before payment.

## 8.5 Notice for cancelling a membership

The real Regal asks for 30 days' notice to cancel a membership. That kind of rule belongs with a membership that renews and charges automatically. Mine doesn't renew (4.18), so there's nothing to give notice about, and the 14-day refund in 4.22 covers changing your mind just after buying. If recurring billing were ever added, a notice period would come with it.

---

[← 7. Testing and quality assurance](testing.md) · [README](../README.md)
