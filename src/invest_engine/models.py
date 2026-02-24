from __future__ import annotations

from dataclasses import dataclass, field
from enum import Enum
from typing import Any


class Region(str, Enum):
    VL = "VL"
    BRU = "BRU"
    WAL = "WAL"


class BuyerType(str, Enum):
    NATURAL_PERSON = "NATURAL_PERSON"
    COMPANY = "COMPANY"


class Purpose(str, Enum):
    OWNER_OCCUPIED = "OWNER_OCCUPIED"
    RENTAL = "RENTAL"
    MIXED = "MIXED"


class Regime(str, Enum):
    EXISTING = "EXISTING"
    NEW_BUILD = "NEW_BUILD"
    MIXED_NEW_EXISTING = "MIXED_NEW_EXISTING"


class AmortizationType(str, Enum):
    ANNUITY = "ANNUITY"
    LINEAR = "LINEAR"
    INTEREST_ONLY = "INTEREST_ONLY"


class VacancyMethod(str, Enum):
    PERCENT = "PERCENT"
    MONTHS = "MONTHS"


class ExitMethod(str, Enum):
    GROWTH = "GROWTH"
    CAP_RATE = "CAP_RATE"


@dataclass
class TaxProfile:
    is_only_and_own_home: bool = False
    is_primary_residence: bool = False
    rental_use_type: str = "NONE"
    brussels_abatement_eligible: bool = False
    vat_applicable: bool = False
    vat_rate_code: str = "STANDARD"
    registration_rate_code: str = "DEFAULT"
    tax_version: str = "2026.1"


@dataclass
class Financing:
    loan_amount: float
    rate_nominal: float
    term_months: int
    amortization_type: AmortizationType = AmortizationType.ANNUITY
    payment_frequency: str = "MONTHLY"
    rate_type: str = "FIXED"
    down_payment: float = 0.0
    file_fee: float = 0.0
    appraisal_fee: float = 0.0
    mortgage_deed_cost_estimate: float = 0.0
    insurance_monthly: float = 0.0


@dataclass
class RentalAssumptions:
    monthly_rent_start: float = 0.0
    vacancy_method: VacancyMethod = VacancyMethod.PERCENT
    vacancy_value: float = 0.0
    rent_indexation_rate: float = 0.02
    bad_debt_rate: float = 0.0


@dataclass
class OperatingExpenseAssumptions:
    property_tax_annual: float = 0.0
    insurance_annual: float = 0.0
    maintenance_reserve_rate: float = 0.05
    management_fee_rate: float = 0.0
    syndic_annual: float = 0.0
    repairs_annual: float = 0.0
    other_annual: float = 0.0
    expense_inflation_rate: float = 0.02


@dataclass
class ExitAssumptions:
    holding_period_years: int = 10
    exit_method: ExitMethod = ExitMethod.GROWTH
    price_growth_rate: float = 0.02
    exit_cap_rate: float = 0.05
    selling_cost_rate: float = 0.03
    selling_cost_fixed: float = 0.0


@dataclass
class WorksPlan:
    capex_total: float = 0.0
    phased: list[dict[str, float]] = field(default_factory=list)


@dataclass
class Scenario:
    scenario_id: str
    name: str
    region: Region
    purchase_year: int
    buyer_type: BuyerType
    purpose: Purpose
    regime: Regime
    price_excl_costs: float
    tax_profile: TaxProfile
    financing: Financing
    rental: RentalAssumptions
    opex: OperatingExpenseAssumptions
    exit: ExitAssumptions
    works: WorksPlan = field(default_factory=WorksPlan)


@dataclass
class AuditEntry:
    label: str
    inputs: dict[str, Any]
    parameters_used: dict[str, Any]
    formula: str
    result: Any
    notes: str = ""
