from abc import ABC, abstractmethod
from dataclasses import dataclass
from datetime import datetime


@dataclass(frozen=True)
class CheckoutSession:
    """A hosted payment page: its id, where to send the customer, and
    when it stops taking payment."""

    id: str
    url: str
    expires_at: datetime
    amount_pence: int
    # Still taking payment: not paid, expired or closed.
    is_open: bool = True
    # Paid, and by which payment, for when a webhook never came (4.32).
    paid: bool = False
    payment_intent_id: str | None = None


@dataclass(frozen=True)
class WebhookEvent:
    """An event the provider sent, once its signature has been checked:
    its id, its type, and the object it's about as plain data."""

    id: str
    type: str
    object: dict


@dataclass(frozen=True)
class PaymentFee:
    """What the provider kept from a payment, and what reached the
    venue, in pence."""

    fee_pence: int
    net_pence: int


class FeeUnavailable(Exception):
    """The provider couldn't say what it kept yet. The booking stands,
    and a later try fills the fee in (4.13)."""


class InvalidSignature(Exception):
    """A webhook that wasn't signed by the provider. Nothing in it can
    be trusted (4.13)."""


class PaymentUnavailable(Exception):
    """The provider couldn't be reached or didn't answer in time, so no
    session was made. Nothing is confirmed, and the customer can try
    again (4.32)."""


class RefundFailed(Exception):
    """The provider refused a refund. The message is its reason, kept so
    staff can see why (4.2, 4.32)."""


class PaymentProvider(ABC):
    """What the site needs from a payment provider. Kept small, so a
    second provider could fit behind it (4.27). Amounts are integer
    pence."""

    @abstractmethod
    def create_checkout_session(self, *, reference, amount_pence,
                                description, success_url, cancel_url,
                                expires_at, idempotency_key):
        """Return a CheckoutSession, or raise PaymentUnavailable. The
        same idempotency_key returns the same session, so a repeated
        request can't make two."""

    @abstractmethod
    def get_checkout_session(self, session_id):
        """Return the CheckoutSession with this id as it is now."""

    @abstractmethod
    def parse_webhook(self, payload, signature):
        """Check the webhook's signature and return a WebhookEvent, or
        raise InvalidSignature."""

    @abstractmethod
    def refund(self, *, payment_intent_id, amount_pence, idempotency_key):
        """Refund part or all of a payment and return the refund's id,
        or raise RefundFailed. The same idempotency_key refunds once."""

    @abstractmethod
    def payment_fee(self, payment_intent_id):
        """Return the PaymentFee for a payment, or raise
        FeeUnavailable."""
