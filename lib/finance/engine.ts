import crypto from "node:crypto";
import rules from "@/rules/v2026-01.be.json";
import { AssumptionsInput, ExplainedValue, ProjectInput, Scenario, TraceItem } from "./types";

const r2 = (n: number) => Math.round(n * 100) / 100;

const scenarioFactor: Record<Scenario, number> = { low: 0.9, base: 1, high: 1.1 };

const annuity = (principal: number, annualRate: number, years: number) => {
  const monthlyRate = annualRate / 12;
  const n = years * 12;
  if (monthlyRate === 0) return principal / n;
  return principal * (monthlyRate / (1 - (1 + monthlyRate) ** -n));
};

const getRegionRule = (region: ProjectInput["region"]) => {
  const cfg = rules.regions.find((r) => r.region === region);
  if (!cfg) throw new Error(`No rules for region ${region}`);
  return cfg;
};

export function computeAcquisitionCosts(input: ProjectInput): ExplainedValue<Record<Scenario, number>> {
  const regionRule = getRegionRule(input.region);
  const reduced = input.flags.isPrimaryResidence && regionRule.registrationTax.reducedRate.conditions.length > 0;
  const regRate = reduced ? regionRule.registrationTax.reducedRate.rate : regionRule.registrationTax.defaultRate;
  const baseAbatement = regionRule.abattement.enabled && input.flags.isPrimaryResidence ? regionRule.abattement.amount : 0;
  const taxableBase = Math.max(input.purchasePrice - baseAbatement, 0);

  const notaryBase = regionRule.notaryHonorariumBrackets.reduce(
    (acc, b, idx, arr) => {
      const prev = idx === 0 ? 0 : arr[idx - 1].upTo;
      const width = Math.max(0, Math.min(input.purchasePrice, b.upTo) - prev);
      return acc + width * b.rate;
    },
    0
  );

  const values = (["low", "base", "high"] as Scenario[]).reduce((acc, scenario) => {
    const factor = scenarioFactor[scenario];
    const registration = taxableBase * regRate;
    const notary = notaryBase * factor;
    const mortgage = regionRule.mortgageCostEstimate.base * factor;
    const admin = regionRule.adminCostsEstimate.base * factor;
    acc[scenario] = r2(input.purchasePrice + registration + notary + mortgage + admin);
    return acc;
  }, {} as Record<Scenario, number>);

  const trace: TraceItem[] = [
    {
      step: "registration_tax",
      formula: "max(purchasePrice - abattement,0) * registrationRate",
      values: { purchasePrice: input.purchasePrice, abattement: baseAbatement, registrationRate: regRate },
      result: r2(taxableBase * regRate)
    },
    {
      step: "notary_and_fees",
      formula: "notaryByBrackets + mortgageEstimate + adminEstimate",
      values: { notaryBase: r2(notaryBase), mortgageEstimate: regionRule.mortgageCostEstimate.base, adminEstimate: regionRule.adminCostsEstimate.base },
      result: r2(notaryBase + regionRule.mortgageCostEstimate.base + regionRule.adminCostsEstimate.base)
    }
  ];

  return {
    value: values,
    formula: "AllIn = Purchase + Registration + Notary + MortgageCosts + AdminCosts",
    explanation: reduced
      ? "Reduced rate applied because user indicated primary residence eligibility."
      : "Default registration rate applied.",
    confidenceLevel: "base",
    calculationTrace: trace
  };
}

export function computeLoan(input: ProjectInput): ExplainedValue<{ monthlyPayment: number; annualDebtService: number }> {
  const monthly = annuity(input.loanAmount, input.interestRate, input.loanYears);
  return {
    value: { monthlyPayment: r2(monthly), annualDebtService: r2(monthly * 12) },
    formula: "M = P * [r / (1 - (1+r)^-n)]",
    explanation: "Annuity model with fixed monthly instalments.",
    confidenceLevel: "base",
    calculationTrace: [
      {
        step: "annuity_payment",
        formula: "loanAmount * (monthlyRate / (1 - (1+monthlyRate)^-periods))",
        values: { loanAmount: input.loanAmount, monthlyRate: input.interestRate / 12, periods: input.loanYears * 12 },
        result: r2(monthly)
      }
    ]
  };
}

export function computeOperationalCashflow(input: ProjectInput, assumptions: AssumptionsInput) {
  const grossRentAnnual = input.rentMonthly * 12;
  const effectiveRent = grossRentAnnual * (1 - assumptions.vacancyRate);
  const operatingCosts =
    effectiveRent * assumptions.maintenanceRate + assumptions.insuranceMonthly * 12 + assumptions.managementMonthly * 12;
  const noi = effectiveRent - operatingCosts;
  return {
    grossRentAnnual: r2(grossRentAnnual),
    effectiveRent: r2(effectiveRent),
    operatingCosts: r2(operatingCosts),
    noi: r2(noi)
  };
}

export function computeKPIs(input: ProjectInput, assumptions: AssumptionsInput) {
  const acquisition = computeAcquisitionCosts(input).value;
  const loan = computeLoan(input).value;
  const op = computeOperationalCashflow(input, assumptions);
  const equity = acquisition.base - input.loanAmount;
  const annualCashflow = op.noi - loan.annualDebtService;

  return {
    grossYield: r2(op.grossRentAnnual / input.purchasePrice),
    netYield: r2(op.noi / acquisition.base),
    cashOnCash: r2(annualCashflow / Math.max(equity, 1)),
    dscr: r2(op.noi / Math.max(loan.annualDebtService, 1)),
    ltv: r2(input.loanAmount / acquisition.base),
    breakEvenVacancy: r2(1 - (op.operatingCosts + loan.annualDebtService) / op.grossRentAnnual),
    annualCashflow: r2(annualCashflow),
    equityInvested: r2(equity),
    totalInvestment: acquisition.base
  };
}

export function computeSensitivity(input: ProjectInput, assumptions: AssumptionsInput) {
  const rentShocks = [-0.1, 0, 0.1];
  const interestShocks = [0, 0.01, 0.02];
  const vacancyShocks = [0, 0.05, 0.1];

  return rentShocks.flatMap((rentDelta) =>
    interestShocks.flatMap((iDelta) =>
      vacancyShocks.map((vRate) => {
        const testInput = { ...input, rentMonthly: input.rentMonthly * (1 + rentDelta), interestRate: input.interestRate + iDelta };
        const testAssumption = { ...assumptions, vacancyRate: vRate };
        const kpi = computeKPIs(testInput, testAssumption);
        return {
          rentDelta,
          iDelta,
          vacancy: vRate,
          dscr: kpi.dscr,
          cashOnCash: kpi.cashOnCash,
          netYield: kpi.netYield
        };
      })
    )
  );
}

export function scoreInvestment(kpi: ReturnType<typeof computeKPIs>, sensitivity: ReturnType<typeof computeSensitivity>) {
  const cashflowStrength = Math.max(0, Math.min(100, 50 + kpi.cashOnCash * 500 + (kpi.dscr - 1) * 25));
  const leverageRisk = Math.max(0, Math.min(100, 100 - kpi.ltv * 100));
  const yieldQuality = Math.max(0, Math.min(100, kpi.netYield * 600));
  const riskyScenarios = sensitivity.filter((s) => s.dscr < 1).length;
  const sensitivityRisk = Math.max(0, Math.min(100, 100 - (riskyScenarios / sensitivity.length) * 100));

  const weighted = cashflowStrength * 0.3 + leverageRisk * 0.25 + yieldQuality * 0.25 + sensitivityRisk * 0.2;
  const grade = weighted >= 80 ? "A" : weighted >= 65 ? "B" : weighted >= 50 ? "C" : "D";

  return {
    categories: {
      cashflowStrength: r2(cashflowStrength),
      leverageRisk: r2(leverageRisk),
      yieldQuality: r2(yieldQuality),
      sensitivityRisk: r2(sensitivityRisk)
    },
    overallScore: r2(weighted),
    grade
  };
}

export function generateNarrative(kpi: ReturnType<typeof computeKPIs>, score: ReturnType<typeof scoreInvestment>) {
  const positives = [
    `DSCR at ${kpi.dscr.toFixed(2)} indicates debt service resilience`,
    `Net yield at ${(kpi.netYield * 100).toFixed(2)}% supports income quality`,
    `LTV at ${(kpi.ltv * 100).toFixed(2)}% keeps leverage contained`
  ];
  const risks = [
    kpi.dscr < 1 ? "DSCR below 1 in base case." : "DSCR resilient in base case.",
    kpi.annualCashflow < 0 ? "Negative annual pre-tax cashflow." : "Annual pre-tax cashflow remains positive.",
    score.categories.sensitivityRisk < 60 ? "High sensitivity to rent/interest/vacancy shocks." : "Moderate sensitivity risk."
  ];
  const recommendations = [
    "Negotiate purchase price or add equity if DSCR margin is thin.",
    "Stress-test rent assumptions with local comparables before closing.",
    "Request final deed and tax simulation from notary before signing."
  ];

  return { positives, risks, recommendations };
}

export function buildAnalysis(input: ProjectInput, assumptions: AssumptionsInput) {
  const acquisition = computeAcquisitionCosts(input);
  const loan = computeLoan(input);
  const kpis = computeKPIs(input, assumptions);
  const sensitivity = computeSensitivity(input, assumptions);
  const score = scoreInvestment(kpis, sensitivity);
  const narrative = generateNarrative(kpis, score);

  const output = {
    rulesetVersion: rules.version,
    calculatedAt: new Date().toISOString(),
    assumptions,
    acquisition,
    loan,
    kpis,
    sensitivity,
    score,
    narrative,
    warnings: {
      loanAboveInvestment: input.loanAmount > kpis.totalInvestment,
      negativeCashflow: kpis.annualCashflow < 0,
      dscrBelowOne: kpis.dscr < 1,
      unrealisticRent: input.rentMonthly * 12 / input.purchasePrice > 0.2
    },
    disclaimers: getRegionRule(input.region).requiredDisclaimers
  };

  return {
    ...output,
    calculationHash: crypto.createHash("sha256").update(JSON.stringify({ input, assumptions, output })).digest("hex")
  };
}
