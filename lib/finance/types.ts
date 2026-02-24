export type Scenario = "low" | "base" | "high";

export type TraceItem = {
  step: string;
  formula: string;
  values: Record<string, number | string | boolean>;
  result: number | string;
};

export type ExplainedValue<T = number> = {
  value: T;
  formula: string;
  explanation: string;
  confidenceLevel: Scenario;
  calculationTrace: TraceItem[];
};

export type ProjectInput = {
  region: "Vlaanderen" | "Brussel" | "Wallonie";
  purchasePrice: number;
  estimatedValue?: number;
  rentMonthly: number;
  loanAmount: number;
  loanYears: number;
  interestRate: number;
  flags: {
    isPrimaryResidence: boolean;
    isInvestment: boolean;
    isNewBuild: boolean;
  };
};

export type AssumptionsInput = {
  vacancyRate: number;
  maintenanceRate: number;
  insuranceMonthly: number;
  managementMonthly: number;
  taxModel: string;
  indexationRate: number;
};
