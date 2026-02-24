from __future__ import annotations

from dataclasses import dataclass


@dataclass
class TaxOutcome:
    transfer_tax: float
    transfer_mode: str
    rate: float


class RegionalTaxStrategy:
    def compute_transfer_tax(self, price: float, params: dict, tax_profile: dict) -> TaxOutcome:
        if tax_profile.get("vat_applicable", False):
            code = tax_profile.get("vat_rate_code", "STANDARD")
            rate = params["vat_rates"][code]
            return TaxOutcome(price * rate, "VAT", rate)
        code = tax_profile.get("registration_rate_code", "DEFAULT")
        rate = params["registration_duty_rates"][code]
        return TaxOutcome(price * rate, "REGISTRATION", rate)


class FlandersTaxStrategy(RegionalTaxStrategy):
    pass


class BrusselsTaxStrategy(RegionalTaxStrategy):
    def compute_transfer_tax(self, price: float, params: dict, tax_profile: dict) -> TaxOutcome:
        result = super().compute_transfer_tax(price, params, tax_profile)
        if result.transfer_mode == "REGISTRATION" and tax_profile.get("brussels_abatement_eligible"):
            abatement = params["abatement_rules"].get("BRU", {})
            base = min(abatement.get("max_basis", 0.0), price)
            reduction = base * result.rate
            return TaxOutcome(max(result.transfer_tax - reduction, 0.0), "REGISTRATION_ABATED", result.rate)
        return result


class WalloniaTaxStrategy(RegionalTaxStrategy):
    pass


def get_strategy(region: str) -> RegionalTaxStrategy:
    mapping = {
        "VL": FlandersTaxStrategy(),
        "BRU": BrusselsTaxStrategy(),
        "WAL": WalloniaTaxStrategy(),
    }
    return mapping[region]
