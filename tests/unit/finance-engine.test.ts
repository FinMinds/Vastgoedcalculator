import { buildAnalysis, computeAcquisitionCosts, computeKPIs, computeLoan, computeOperationalCashflow, computeSensitivity } from "@/lib/finance/engine";

const project = {
  region: "Vlaanderen" as const,
  purchasePrice: 300000,
  rentMonthly: 1400,
  loanAmount: 240000,
  loanYears: 20,
  interestRate: 0.035,
  flags: { isPrimaryResidence: false, isInvestment: true, isNewBuild: false }
};

const assumptions = {
  vacancyRate: 0.05,
  maintenanceRate: 0.1,
  insuranceMonthly: 50,
  managementMonthly: 75,
  taxModel: "private",
  indexationRate: 0.02
};

describe("finance engine", () => {
  test("computes acquisition scenarios", () => {
    const res = computeAcquisitionCosts(project);
    expect(res.value.low).toBeLessThan(res.value.base);
    expect(res.value.high).toBeGreaterThan(res.value.base);
    expect(res.calculationTrace.length).toBeGreaterThan(0);
  });

  test("computes annuity loan", () => {
    const res = computeLoan(project);
    expect(res.value.monthlyPayment).toBeGreaterThan(0);
    expect(res.value.annualDebtService).toBeCloseTo(res.value.monthlyPayment * 12, 1);
  });

  test("computes cashflow and KPIs with strict definitions", () => {
    const op = computeOperationalCashflow(project, assumptions);
    const kpi = computeKPIs(project, assumptions);
    expect(op.noi).toBeGreaterThan(0);
    expect(kpi.grossYield).toBeCloseTo((project.rentMonthly * 12) / project.purchasePrice, 2);
    expect(kpi.dscr).toBeGreaterThan(0);
  });

  test("builds sensitivity grid", () => {
    const sens = computeSensitivity(project, assumptions);
    expect(sens).toHaveLength(27);
  });

  test("build analysis with hash", () => {
    const report = buildAnalysis(project, assumptions);
    expect(report.calculationHash).toHaveLength(64);
    expect(report.rulesetVersion).toBe("v2026-01");
  });
});
