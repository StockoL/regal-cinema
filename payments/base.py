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


@dataclass(frozen=True)
class WebhookEvent:
    """An event the provider sent, once its signature has been checked:
    its id, its type, and the object it's about as plain data."""

    id: str
    type: str
    object: dict


class InvalidSignature(Exception):
    """A webhook that wasn't signed by the provider. Nothing in it can
    be trusted (4.13)."""


class PaymentProvider(ABC):
    """What the site needs from a payment provider. Kept small, so a
    second provider could fit behind it (4.27). Amounts are integer
    pence."""

    @abstractmethod
    def create_checkout_session(self, *, reference, amount_pence,
                                description, success_url, cancel_url,
                                expires_at, idempotency_key):
        """Return a CheckoutSession. The same idempotency_key returns
        the same session, so a repeated request can't make two."""

    @abstractmethod
    def parse_webhook(self, payload, signature):
        """Check the webhook's signature and return a WebhookEvent, or
        raise InvalidSignature."""
