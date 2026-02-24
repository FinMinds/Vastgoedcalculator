from invest_engine import InvestmentEngine, ParameterStore
from invest_engine.models import (
    AmortizationType,
    BuyerType,
    ExitAssumptions,
    Financing,
    OperatingExpenseAssumptions,
    Purpose,
    Regime,
    Region,
    RentalAssumptions,
    Scenario,
    TaxProfile,
)


def make_scenario(region: Region, buyer: BuyerType, purpose: Purpose, loan_amount: float = 250000):
    return Scenario(
        scenario_id="s1",
        name="test",
        region=region,
        purchase_year=2026,
        buyer_type=buyer,
        purpose=purpose,
        regime=Regime.EXISTING,
        price_excl_costs=300000,
        tax_profile=TaxProfile(
            vat_applicable=False,
            registration_rate_code="DEFAULT",
            brussels_abatement_eligible=(region == Region.BRU),
            tax_version="2026.1",
        ),
        financing=Financing(
            loan_amount=loan_amount,
            rate_nominal=0.035,
            term_months=240,
            amortization_type=AmortizationType.ANNUITY,
            file_fee=500,
            appraisal_fee=350,
            mortgage_deed_cost_estimate=1600,
        ),
        rental=RentalAssumptions(monthly_rent_start=1450, vacancy_value=0.04),
        opex=OperatingExpenseAssumptions(property_tax_annual=1200, insurance_annual=450, repairs_annual=600),
        exit=ExitAssumptions(holding_period_years=10),
    )


def test_regions_supported():
    engine = InvestmentEngine(ParameterStore("config/parameter_sets.json"))
    for region in [Region.VL, Region.BRU, Region.WAL]:
        out = engine.compute(make_scenario(region, BuyerType.NATURAL_PERSON, Purpose.RENTAL))
        assert out["purchase_breakdown"]["transfer_tax"] > 0


def test_private_vs_company_runs():
    engine = InvestmentEngine(ParameterStore("config/parameter_sets.json"))
    out_np = engine.compute(make_scenario(Region.VL, BuyerType.NATURAL_PERSON, Purpose.RENTAL))
    out_co = engine.compute(make_scenario(Region.VL, BuyerType.COMPANY, Purpose.RENTAL))
    assert out_np["kpis"]["gross_yield"] > 0
    assert out_co["kpis"]["net_yield"] > 0


def test_rental_vs_owner_occupied_runs():
    engine = InvestmentEngine(ParameterStore("config/parameter_sets.json"))
    out_rental = engine.compute(make_scenario(Region.WAL, BuyerType.NATURAL_PERSON, Purpose.RENTAL))
    out_owner = engine.compute(make_scenario(Region.WAL, BuyerType.NATURAL_PERSON, Purpose.OWNER_OCCUPIED))
    assert "decision" in out_rental
    assert "decision" in out_owner


def test_financed_vs_cash_purchase():
    engine = InvestmentEngine(ParameterStore("config/parameter_sets.json"))
    financed = engine.compute(make_scenario(Region.VL, BuyerType.NATURAL_PERSON, Purpose.RENTAL, loan_amount=200000))
    cash = engine.compute(make_scenario(Region.VL, BuyerType.NATURAL_PERSON, Purpose.RENTAL, loan_amount=0))
    assert financed["financing_breakdown"]["ltv"] > 0
    assert cash["annual_cashflows"][0]["debt_service"] == 0
