from __future__ import annotations

from dataclasses import asdict
from math import isclose
from typing import Any

from .models import AuditEntry, ExitMethod, Scenario, VacancyMethod
from .parameters import ParameterStore
from .rules import get_strategy


def _npv(rate: float, cashflows: list[float]) -> float:
    return sum(cf / ((1 + rate) ** t) for t, cf in enumerate(cashflows))


def _irr(cashflows: list[float], low: float = -0.95, high: float = 2.0, max_iter: int = 100) -> float:
    for _ in range(max_iter):
        mid = (low + high) / 2
        val = _npv(mid, cashflows)
        if abs(val) < 1e-7:
            return mid
        if val > 0:
            low = mid
        else:
            high = mid
    return mid


class InvestmentEngine:
    def __init__(self, parameter_store: ParameterStore):
        self.parameter_store = parameter_store

    def compute(self, scenario: Scenario, include_extras: bool = True) -> dict[str, Any]:
        pset = self.parameter_store.resolve(scenario.region.value, scenario.purchase_year, scenario.tax_profile.tax_version)
        params = pset.params
        audit: list[AuditEntry] = []

        strategy = get_strategy(scenario.region.value)
        transfer = strategy.compute_transfer_tax(scenario.price_excl_costs, params, asdict(scenario.tax_profile))
        notary = self._notary_cost(scenario.price_excl_costs, params["notary_fee_schedule"])
        o_other = params["default_assumptions"].get("purchase_other_costs", 0.0)
        capex0 = scenario.works.capex_total if not scenario.works.phased else 0.0

        tac = scenario.price_excl_costs + transfer.transfer_tax + notary + o_other + capex0
        fin_upfront = (
            scenario.financing.file_fee
            + scenario.financing.appraisal_fee
            + scenario.financing.mortgage_deed_cost_estimate
        )
        tcnc = tac + fin_upfront - scenario.financing.loan_amount
        equity0 = tcnc

        audit.append(
            AuditEntry(
                label="Total Acquisition Cost",
                inputs={"P": scenario.price_excl_costs, "REG/VAT": transfer.transfer_tax, "NOT": notary, "OTH": o_other, "CAPEX0": capex0},
                parameters_used={"transfer_mode": transfer.transfer_mode, "transfer_rate": transfer.rate},
                formula="TAC = P + REG + NOT + OTH + CAPEX0",
                result=tac,
            )
        )

        amort = self._amortization_schedule(
            scenario.financing.loan_amount,
            scenario.financing.rate_nominal,
            scenario.financing.term_months,
            scenario.financing.amortization_type.value,
        )

        annual_cashflows = []
        annual_principal = []
        holding = scenario.exit.holding_period_years
        for y in range(1, max(20, holding) + 1):
            rent_gross = 12 * scenario.rental.monthly_rent_start * ((1 + scenario.rental.rent_indexation_rate) ** (y - 1))
            if scenario.rental.vacancy_method == VacancyMethod.PERCENT:
                vacancy = rent_gross * scenario.rental.vacancy_value
            else:
                vacancy = rent_gross * (scenario.rental.vacancy_value / 12)
            bad_debt = rent_gross * scenario.rental.bad_debt_rate
            egi = rent_gross - vacancy - bad_debt

            infl = (1 + scenario.opex.expense_inflation_rate) ** (y - 1)
            fixed_opex = (
                scenario.opex.property_tax_annual
                + scenario.opex.insurance_annual
                + scenario.opex.syndic_annual
                + scenario.opex.repairs_annual
                + scenario.opex.other_annual
            ) * infl
            maintenance = egi * scenario.opex.maintenance_reserve_rate
            management = egi * scenario.opex.management_fee_rate
            opex = fixed_opex + maintenance + management
            noi = egi - opex

            m_start, m_end = (y - 1) * 12, y * 12
            debt_service = sum(m["payment"] for m in amort[m_start:m_end]) + scenario.financing.insurance_monthly * 12
            principal = sum(m["principal"] for m in amort[m_start:m_end])
            capex_y = sum(i["amount"] for i in scenario.works.phased if i["year"] == y) if scenario.works.phased else 0.0
            cfbt = noi - debt_service - capex_y
            annual_cashflows.append(
                {
                    "year": y,
                    "rent_gross": rent_gross,
                    "egi": egi,
                    "opex": opex,
                    "noi": noi,
                    "debt_service": debt_service,
                    "cfbt": cfbt,
                    "principal_repaid": principal,
                    "remaining_loan": amort[min(m_end, len(amort)) - 1]["balance"] if amort else 0.0,
                }
            )
            annual_principal.append(principal)

        exit_result = self._compute_exit(scenario, annual_cashflows[holding - 1]["noi"], amort, params)
        annual_cashflows[holding - 1]["cfbt_with_exit"] = annual_cashflows[holding - 1]["cfbt"] + exit_result["net_sale_proceeds"]

        kpis = self._kpis(annual_cashflows, tac, equity0, scenario, exit_result)
        decision = self._decision(kpis, annual_cashflows, params["default_thresholds"], scenario) if include_extras else {"decision":"N/A","reasons":[],"fix_suggestions":[]}

        sensitivity = self._sensitivity(scenario) if include_extras else {}

        result = {
            "scenario_id": scenario.scenario_id,
            "purchase_breakdown": {
                "price": scenario.price_excl_costs,
                "transfer_tax": transfer.transfer_tax,
                "notary": notary,
                "other": o_other,
                "capex0": capex0,
                "tac": tac,
                "tcnc": tcnc,
            },
            "financing_breakdown": {
                "loan_amount": scenario.financing.loan_amount,
                "equity0": equity0,
                "ltv": scenario.financing.loan_amount / scenario.price_excl_costs if scenario.price_excl_costs else 0.0,
                "amortization_table": amort,
            },
            "annual_cashflows": annual_cashflows,
            "exit": exit_result,
            "kpis": kpis,
            "decision": decision["decision"],
            "decision_reasons": decision["reasons"],
            "fix_suggestions": decision["fix_suggestions"],
            "sensitivity": sensitivity,
            "audit_trail": [asdict(a) for a in audit],
        }
        return result

    def _notary_cost(self, price: float, schedule: list[dict[str, float]]) -> float:
        remaining = price
        prev = 0.0
        total = 0.0
        for bracket in schedule:
            upto = bracket["upto"]
            rate = bracket["rate"]
            width = max(0.0, min(remaining, upto - prev))
            total += width * rate
            remaining -= width
            prev = upto
            if remaining <= 0:
                break
        if remaining > 0:
            total += remaining * schedule[-1]["rate"]
        return total + 1200.0

    def _amortization_schedule(self, loan: float, annual_rate: float, months: int, kind: str) -> list[dict[str, float]]:
        if isclose(loan, 0.0):
            return [{"month": m, "payment": 0.0, "interest": 0.0, "principal": 0.0, "balance": 0.0} for m in range(1, months + 1)]
        i = annual_rate / 12
        balance = loan
        rows = []
        if kind == "ANNUITY":
            pmt = loan / months if isclose(i, 0.0) else loan * (i * ((1 + i) ** months)) / (((1 + i) ** months) - 1)
            for m in range(1, months + 1):
                interest = balance * i
                principal = pmt - interest
                balance = max(0.0, balance - principal)
                rows.append({"month": m, "payment": pmt, "interest": interest, "principal": principal, "balance": balance})
        elif kind == "LINEAR":
            principal_const = loan / months
            for m in range(1, months + 1):
                interest = balance * i
                payment = principal_const + interest
                balance = max(0.0, balance - principal_const)
                rows.append({"month": m, "payment": payment, "interest": interest, "principal": principal_const, "balance": balance})
        else:  # INTEREST_ONLY
            for m in range(1, months + 1):
                interest = balance * i
                principal = loan if m == months else 0.0
                payment = interest + principal
                balance = max(0.0, balance - principal)
                rows.append({"month": m, "payment": payment, "interest": interest, "principal": principal, "balance": balance})
        return rows

    def _compute_exit(self, scenario: Scenario, noi_h: float, amort: list[dict[str, float]], params: dict) -> dict[str, float]:
        h = scenario.exit.holding_period_years
        if scenario.exit.exit_method == ExitMethod.CAP_RATE:
            sale_price = noi_h / scenario.exit.exit_cap_rate
        else:
            sale_price = scenario.price_excl_costs * ((1 + scenario.exit.price_growth_rate) ** h)
        sell_costs = sale_price * scenario.exit.selling_cost_rate + scenario.exit.selling_cost_fixed
        rem_balance = amort[min(h * 12, len(amort)) - 1]["balance"] if amort else 0.0
        net = sale_price - sell_costs - rem_balance
        return {
            "sale_price": sale_price,
            "sell_costs": sell_costs,
            "remaining_balance": rem_balance,
            "net_sale_proceeds": net,
        }

    def _kpis(self, annual: list[dict[str, float]], tac: float, equity0: float, scenario: Scenario, exit_result: dict[str, float]) -> dict[str, float]:
        rent1 = annual[0]["rent_gross"]
        noi1 = annual[0]["noi"]
        ds1 = annual[0]["debt_service"]
        cf1 = annual[0]["cfbt"]
        h = scenario.exit.holding_period_years
        cashflows = [-equity0] + [a["cfbt"] for a in annual[: h - 1]] + [annual[h - 1]["cfbt"] + exit_result["net_sale_proceeds"]]
        irr = _irr(cashflows)
        discount = 0.08
        npv = _npv(discount, cashflows)
        total_return = (sum(a["cfbt"] for a in annual[:h]) + exit_result["net_sale_proceeds"]) / equity0 if equity0 else 0.0
        var_rate = scenario.opex.maintenance_reserve_rate + scenario.opex.management_fee_rate
        fixed_opex_1 = annual[0]["opex"] - annual[0]["egi"] * var_rate
        egi_be = (ds1 + fixed_opex_1) / (1 - var_rate) if (1 - var_rate) > 0 else float("inf")
        vacancy = scenario.rental.vacancy_value if scenario.rental.vacancy_method == VacancyMethod.PERCENT else scenario.rental.vacancy_value / 12
        monthly_be = egi_be / (12 * max(1e-9, 1 - vacancy - scenario.rental.bad_debt_rate))
        return {
            "gross_yield": rent1 / tac if tac else 0.0,
            "net_yield": noi1 / tac if tac else 0.0,
            "cash_on_cash": cf1 / equity0 if equity0 else 0.0,
            "dscr_1": noi1 / ds1 if ds1 else 999.0,
            "ltv": scenario.financing.loan_amount / scenario.price_excl_costs if scenario.price_excl_costs else 0.0,
            "irr": irr,
            "npv": npv,
            "total_return": total_return,
            "break_even_monthly_rent": monthly_be,
            "payback_years": next((i + 1 for i, a in enumerate(annual) if sum(x["cfbt"] for x in annual[: i + 1]) >= equity0), None),
        }

    def _decision(self, kpis: dict[str, float], annual: list[dict[str, float]], thresholds: dict[str, float], scenario: Scenario) -> dict[str, Any]:
        reasons = []
        score = 0
        if kpis["dscr_1"] >= thresholds["DSCR_min"]:
            score += 1
        else:
            reasons.append("DSCR below threshold")
        if kpis["cash_on_cash"] >= thresholds["CoC_min"]:
            score += 1
        else:
            reasons.append("Cash-on-cash below threshold")
        if kpis["irr"] >= thresholds["IRR_min"]:
            score += 1
        else:
            reasons.append("IRR below threshold")
        if min(a["cfbt"] for a in annual) >= -thresholds["MaxNegCF_allowed"]:
            score += 1
        else:
            reasons.append("Negative cashflow exceeds allowed threshold")

        if score >= 4:
            decision = "GO"
        elif score >= 2:
            decision = "CONDITIONAL"
        else:
            decision = "NO_GO"

        return {"decision": decision, "reasons": reasons, "fix_suggestions": self._fix_suggestions(kpis, scenario, thresholds)}

    def _fix_suggestions(self, kpis: dict[str, float], scenario: Scenario, thresholds: dict[str, float]) -> list[str]:
        suggestions = []
        if kpis["dscr_1"] < thresholds["DSCR_min"]:
            suggestions.append(f"Huur moet naar minstens €{kpis['break_even_monthly_rent']:.2f}/maand voor DSCR=1.")
        if kpis["cash_on_cash"] < thresholds["CoC_min"] and scenario.financing.loan_amount > 0:
            l_star = self._solve_max_loan_for_non_negative_cf(scenario)
            suggestions.append(f"Eigen inbreng +€{max(0.0, scenario.financing.loan_amount - l_star):.2f} om jaar-1 cashflow >= 0 te maken.")
        if kpis["irr"] < thresholds["IRR_min"]:
            p_star = self._solve_max_price_for_target_irr(scenario, thresholds["IRR_min"])
            suggestions.append(f"Maximum biedprijs ongeveer €{p_star:.2f} voor target IRR.")
        return suggestions

    def _solve_max_loan_for_non_negative_cf(self, scenario: Scenario) -> float:
        low, high = 0.0, scenario.financing.loan_amount
        for _ in range(40):
            mid = (low + high) / 2
            original = scenario.financing.loan_amount
            scenario.financing.loan_amount = mid
            output = self.compute(scenario, include_extras=False)
            scenario.financing.loan_amount = original
            if output["annual_cashflows"][0]["cfbt"] >= 0:
                low = mid
            else:
                high = mid
        return low

    def _solve_max_price_for_target_irr(self, scenario: Scenario, target: float) -> float:
        low, high = scenario.price_excl_costs * 0.4, scenario.price_excl_costs * 1.4
        for _ in range(40):
            mid = (low + high) / 2
            original = scenario.price_excl_costs
            scenario.price_excl_costs = mid
            output = self.compute(scenario, include_extras=False)
            scenario.price_excl_costs = original
            if output["kpis"]["irr"] >= target:
                low = mid
            else:
                high = mid
        return low

    def _sensitivity(self, scenario: Scenario) -> dict[str, Any]:
        def run(mod_r=0.0, mod_h=0.0, mod_v=0.0):
            base_rate = scenario.financing.rate_nominal
            base_rent = scenario.rental.monthly_rent_start
            base_vac = scenario.rental.vacancy_value
            scenario.financing.rate_nominal += mod_r
            scenario.rental.monthly_rent_start *= (1 + mod_h)
            scenario.rental.vacancy_value += mod_v
            out = self.compute(scenario, include_extras=False)
            scenario.financing.rate_nominal = base_rate
            scenario.rental.monthly_rent_start = base_rent
            scenario.rental.vacancy_value = base_vac
            return {"irr": out["kpis"]["irr"], "cashflow_year_1": out["annual_cashflows"][0]["cfbt"]}

        return {
            "base_case": run(),
            "stress_case": run(mod_r=0.01, mod_h=-0.10, mod_v=0.05),
            "optimistic_case": run(mod_r=-0.005, mod_h=0.05, mod_v=-0.02),
        }
