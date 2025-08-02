
"""Payment gateway factory implementation."""

from abc import ABC, abstractmethod
from typing import Dict
from datetime import datetime
from dataclasses import dataclass


@dataclass
class PaymentResult:
    """Data class for payment results."""

    success: bool
    transaction_id: str
    message: str
    fee: float = 0.0

    def to_dict(self) -> Dict:
        """Convert PaymentResult to dictionary."""
        return {
            "success": self.success,
            "transaction_id": self.transaction_id,
            "message": self.message,
            "fee": self.fee,
        }


class PaymentProcessor(ABC):
    """Abstract base class for payment processors."""

    @abstractmethod
    def process_payment(
        self, amount: float, currency: str, customer_info: Dict
    ) -> PaymentResult:
        """Process a payment transaction."""
        pass


class PaymentProcessorFactory(ABC):
    """Abstract factory for creating payment processors."""

    @abstractmethod
    def create_processor(self, payment_method: str) -> PaymentProcessor:
        """Create a payment processor for the given method."""
        pass


class CreditCardProcessor(PaymentProcessor):
    """Credit card payment processor."""

    def __init__(self):
        """Initialize credit card processor."""
        self.supported_currencies = {"USD", "EUR", "GBP"}
        self.fee_percentage = 0.029
        self.flat_fee = 0.30

    def process_payment(
        self, amount: float, currency: str, customer_info: Dict
    ) -> PaymentResult:
        """Process credit card payment."""
        if amount <= 0:
            return PaymentResult(False, "", "Invalid payment parameters", 0.0)

        if (
            not self._is_valid_currency(currency)
            or currency not in self.supported_currencies
        ):
            return PaymentResult(False, "", "Invalid payment parameters", 0.0)

        if not customer_info or "card_number" not in customer_info:
            return PaymentResult(False, "", "Missing card information", 0.0)

        fee = round(amount * self.fee_percentage + self.flat_fee, 2)
        customer_id = customer_info.get("customer_id", "unknown")
        transaction_id = (
            f"CC_{datetime.now().strftime('%Y%m%d%H%M%S')}_{customer_id}"
        )

        return PaymentResult(
            True,
            transaction_id,
            f"Credit card payment of {amount} {currency} processed "
            "successfully",
            fee,
        )

    def _is_valid_currency(self, currency: str) -> bool:
        """Validate currency format."""
        return (
            isinstance(currency, str)
            and len(currency) == 3
            and currency.isupper()
        )


class PayPalProcessor(PaymentProcessor):
    """PayPal payment processor."""

    def __init__(self):
        """Initialize PayPal processor."""
        self.supported_currencies = {"USD", "EUR", "GBP", "CAD", "AUD"}
        self.fee_percentage = 0.0349
        self.flat_fee = 0.49

    def process_payment(
        self, amount: float, currency: str, customer_info: Dict
    ) -> PaymentResult:
        """Process PayPal payment."""
        if amount <= 0:
            return PaymentResult(False, "", "Invalid payment parameters", 0.0)

        if (
            not self._is_valid_currency(currency)
            or currency not in self.supported_currencies
        ):
            return PaymentResult(False, "", "Invalid payment parameters", 0.0)

        if not customer_info or "email" not in customer_info:
            return PaymentResult(False, "", "Missing PayPal email", 0.0)

        fee = round(amount * self.fee_percentage + self.flat_fee, 2)
        customer_id = customer_info.get("customer_id", "unknown")
        transaction_id = (
            f"PP_{datetime.now().strftime('%Y%m%d%H%M%S')}_{customer_id}"
        )

        return PaymentResult(
            True,
            transaction_id,
            f"PayPal payment of {amount} {currency} processed successfully",
            fee,
        )

    def _is_valid_currency(self, currency: str) -> bool:
        """Validate currency format."""
        return (
            isinstance(currency, str)
            and len(currency) == 3
            and currency.isupper()
        )


class BankTransferProcessor(PaymentProcessor):
    """Bank transfer payment processor."""

    def __init__(self):
        """Initialize bank transfer processor."""
        self.supported_currencies = {"USD", "EUR"}
        self.flat_fee = 15.0
        self.minimum_amount = 100.0

    def process_payment(
        self, amount: float, currency: str, customer_info: Dict
    ) -> PaymentResult:
        """Process bank transfer payment."""
        if amount <= 0 or amount < self.minimum_amount:
            return PaymentResult(False, "", "Invalid payment parameters", 0.0)

        if (
            not self._is_valid_currency(currency)
            or currency not in self.supported_currencies
        ):
            return PaymentResult(False, "", "Invalid payment parameters", 0.0)

        if (
            not customer_info
            or "account_number" not in customer_info
            or "routing_number" not in customer_info
        ):
            return PaymentResult(
                False, "", "Missing bank account information", 0.0
            )

        customer_id = customer_info.get("customer_id", "unknown")
        transaction_id = (
            f"BT_{datetime.now().strftime('%Y%m%d%H%M%S')}_{customer_id}"
        )

        return PaymentResult(
            True,
            transaction_id,
            f"Bank transfer of {amount} {currency} initiated successfully",
            self.flat_fee,
        )

    def _is_valid_currency(self, currency: str) -> bool:
        """Validate currency format."""
        return (
            isinstance(currency, str)
            and len(currency) == 3
            and currency.isupper()
        )


class StandardPaymentProcessorFactory(PaymentProcessorFactory):
    """Production factory implementation."""

    def __init__(self):
        """Initialize standard payment processor factory."""
        self._processors = {
            "credit_card": CreditCardProcessor,
            "paypal": PayPalProcessor,
            "bank_transfer": BankTransferProcessor,
        }

    def create_processor(self, payment_method: str) -> PaymentProcessor:
        """Create processor for the given payment method."""
        processor_class = self._processors.get(payment_method)
        if not processor_class:
            raise ValueError(f"Unsupported payment method: {payment_method}")
        return processor_class()


class FakePaymentProcessorFactory(PaymentProcessorFactory):
    """Test factory implementation with configurable results."""

    def __init__(self):
        """Initialize fake payment processor factory."""
        self._mock_results = {}
        self._mock_fees = {}

    def set_mock_result(
        self,
        payment_method: str,
        success: bool,
        transaction_id: str = "",
        message: str = "",
    ):
        """Configure mock result for a payment method."""
        self._mock_results[payment_method] = {
            "success": success,
            "transaction_id": transaction_id,
            "message": message,
        }

    def set_mock_fee(self, payment_method: str, fee: float):
        """Configure mock fee for a payment method."""
        self._mock_fees[payment_method] = fee

    def create_processor(self, payment_method: str) -> PaymentProcessor:
        """Create mock processor for the given payment method."""
        if payment_method not in self._mock_results:
            raise ValueError(f"Unsupported payment method: {payment_method}")

        class MockProcessor(PaymentProcessor):
            def __init__(self, result_config, fee):
                self.result_config = result_config
                self.fee = fee

            def process_payment(
                self, amount: float, currency: str, customer_info: Dict
            ) -> PaymentResult:
                return PaymentResult(
                    self.result_config["success"],
                    self.result_config["transaction_id"],
                    self.result_config["message"],
                    self.fee,
                )

        return MockProcessor(
            self._mock_results[payment_method],
            self._mock_fees.get(payment_method, 0.0),
        )


class PaymentGateway:
    """Main payment gateway with dependency injection."""

    def __init__(self, processor_factory: PaymentProcessorFactory):
        """Initialize payment gateway."""
        self._factory = processor_factory
        self._transaction_log = []

    def process_transaction(
        self,
        payment_method: str,
        amount: float,
        currency: str,
        customer_info: Dict,
    ) -> Dict:
        """Process a payment transaction."""
        try:
            processor = self._factory.create_processor(payment_method)
            result = processor.process_payment(amount, currency, customer_info)

            self._transaction_log.append(
                {
                    "timestamp": datetime.now().isoformat(),
                    "payment_method": payment_method,
                    "amount": amount,
                    "currency": currency,
                    "result": result.to_dict(),
                }
            )

            return result.to_dict()

        except ValueError as e:
            return {
                "success": False,
                "transaction_id": "",
                "message": str(e),
                "fee": 0.0,
            }


def process_transaction(
    payment_method: str, amount: float, currency: str, customer_info: Dict
) -> Dict:
    """Process a transaction using the standard factory."""
    factory = StandardPaymentProcessorFactory()
    gateway = PaymentGateway(factory)
    return gateway.process_transaction(
        payment_method, amount, currency, customer_info
    )

