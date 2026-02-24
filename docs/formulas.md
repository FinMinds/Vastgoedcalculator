# Formule-documentatie — Belgische Vastgoed Investeringsengine

## Kernformules
- **TAC** = `P + REG + NOT + OTH + CAPEX0`
- **TCNC** = `(TAC + FIN_UPFRONT) - LoanProceedsClosing`
- **PMT (annuïteit)** = `L * ( i * (1+i)^n ) / ( (1+i)^n - 1 )`
- **NOI** = `EGI - OPEX`
- **CFBT** = `NOI - DebtService - Capex_y`
- **SalePrice (growth)** = `P * (1 + growth)^H`
- **SalePrice (cap rate)** = `NOI_H / exit_cap_rate`
- **NetSaleProceeds** = `SalePrice - SellCosts - RemainingLoanBalance`

## KPI-definities
- **Gross Yield** = `RentGross_1 / TAC`
- **Net Yield** = `NOI_1 / TAC`
- **Cash-on-Cash** = `CFBT_1 / Equity0`
- **DSCR** = `NOI_1 / DebtService_1`
- **IRR** op cashflowreeks `[CF_0..CF_H]`
- **NPV** = `Σ CF_y / (1+d)^y`
- **Total Return** = `(Σ CFBT_y + NetSaleProceeds) / Equity0`

## Beslissingsregels
- Score +1 per geslaagde drempel: DSCR, CoC, IRR, max negatieve cashflow.
- **GO**: score 4, **CONDITIONAL**: score 2-3, **NO_GO**: score 0-1.

## Audit trail
Iedere berekende output bevat:
1. inputwaarden
2. parameterwaarden
3. gebruikte formule
4. resultaat
