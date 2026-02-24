import { NextRequest, NextResponse } from "next/server";
import { buildAnalysis } from "@/lib/finance/engine";
import { checkRateLimit } from "@/lib/server/rate-limit";
import { logger } from "@/lib/server/logger";
import { prisma } from "@/lib/server/prisma";
import { analyzePayloadSchema } from "@/lib/server/validation";

export async function POST(request: NextRequest) {
  const ip = request.headers.get("x-forwarded-for") || "local";
  if (!checkRateLimit(ip)) return NextResponse.json({ error: "Rate limit exceeded" }, { status: 429 });

  const payload = analyzePayloadSchema.safeParse(await request.json());
  if (!payload.success) return NextResponse.json({ error: payload.error.flatten() }, { status: 400 });

  const { project, assumptions } = payload.data;
  const analysis = buildAnalysis(project, assumptions);

  const created = await prisma.project.create({
    data: {
      region: project.region,
      purchasePrice: project.purchasePrice,
      estimatedValue: project.estimatedValue,
      rentMonthly: project.rentMonthly,
      loanAmount: project.loanAmount,
      loanYears: project.loanYears,
      interestRate: project.interestRate,
      isPrimaryResidence: project.flags.isPrimaryResidence,
      isInvestment: project.flags.isInvestment,
      isNewBuild: project.flags.isNewBuild,
      assumptions: { create: assumptions },
      snapshots: {
        create: {
          computedJson: JSON.stringify(analysis),
          calculationHash: analysis.calculationHash,
          narrative: JSON.stringify(analysis.narrative)
        }
      }
    },
    include: { snapshots: true }
  });

  logger.info({ projectId: created.id, hash: analysis.calculationHash }, "analysis created");
  return NextResponse.json({ projectId: created.id, snapshotId: created.snapshots[0].id, analysis });
}
