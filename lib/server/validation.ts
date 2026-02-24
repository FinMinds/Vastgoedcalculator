import { z } from "zod";

export const projectSchema = z.object({
  region: z.enum(["Vlaanderen", "Brussel", "Wallonie"]),
  purchasePrice: z.number().positive(),
  estimatedValue: z.number().positive().optional(),
  rentMonthly: z.number().positive(),
  loanAmount: z.number().positive(),
  loanYears: z.number().int().min(1).max(40),
  interestRate: z.number().min(0).max(0.25),
  flags: z.object({
    isPrimaryResidence: z.boolean(),
    isInvestment: z.boolean(),
    isNewBuild: z.boolean()
  })
});

export const assumptionsSchema = z.object({
  vacancyRate: z.number().min(0).max(0.5),
  maintenanceRate: z.number().min(0).max(0.5),
  insuranceMonthly: z.number().min(0),
  managementMonthly: z.number().min(0),
  taxModel: z.string().min(1),
  indexationRate: z.number().min(0).max(0.2)
});

export const analyzePayloadSchema = z.object({
  project: projectSchema,
  assumptions: assumptionsSchema
});
