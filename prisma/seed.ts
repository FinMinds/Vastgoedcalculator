import { PrismaClient } from "@prisma/client";
import fs from "node:fs";
import path from "node:path";

const prisma = new PrismaClient();

async function main() {
  const config = fs.readFileSync(path.join(process.cwd(), "rules/v2026-01.be.json"), "utf-8");

  await prisma.ruleset.upsert({
    where: { version: "v2026-01" },
    update: { jsonConfig: config, isActive: true },
    create: {
      version: "v2026-01",
      effectiveFrom: new Date("2026-01-01T00:00:00.000Z"),
      effectiveTo: new Date("2026-12-31T23:59:59.999Z"),
      jsonConfig: config,
      isActive: true
    }
  });

  await prisma.project.create({
    data: {
      region: "Vlaanderen",
      purchasePrice: 285000,
      estimatedValue: 300000,
      rentMonthly: 1350,
      loanAmount: 220000,
      loanYears: 20,
      interestRate: 0.036,
      isPrimaryResidence: false,
      isInvestment: true,
      isNewBuild: false,
      assumptions: {
        create: {
          vacancyRate: 0.05,
          maintenanceRate: 0.1,
          insuranceMonthly: 50,
          managementMonthly: 70,
          taxModel: "private",
          indexationRate: 0.02
        }
      }
    }
  });
}

main().finally(() => prisma.$disconnect());
