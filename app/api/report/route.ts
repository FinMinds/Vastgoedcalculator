import { NextRequest, NextResponse } from "next/server";
import puppeteer from "puppeteer";
import { prisma } from "@/lib/server/prisma";

export async function GET(req: NextRequest) {
  const projectId = req.nextUrl.searchParams.get("projectId");
  if (!projectId) return NextResponse.json({ error: "projectId required" }, { status: 400 });

  const project = await prisma.project.findUnique({ where: { id: projectId }, include: { snapshots: { orderBy: { createdAt: "desc" } } } });
  if (!project || project.snapshots.length === 0) return NextResponse.json({ error: "Not found" }, { status: 404 });

  const snapshot = JSON.parse(project.snapshots[0].computedJson);
  const html = `<!doctype html><html><body><h1>Belgian Investment Report</h1>
  <h2>Executive Summary</h2><p>Grade ${snapshot.score.grade}, Score ${snapshot.score.overallScore}</p>
  <h2>Investment Overview</h2><pre>${JSON.stringify(snapshot.kpis, null, 2)}</pre>
  <h2>Acquisition Breakdown</h2><pre>${JSON.stringify(snapshot.acquisition, null, 2)}</pre>
  <h2>Financing Summary</h2><pre>${JSON.stringify(snapshot.loan, null, 2)}</pre>
  <h2>Sensitivity Analysis</h2><pre>${JSON.stringify(snapshot.sensitivity.slice(0, 9), null, 2)}</pre>
  <h2>Conclusion</h2><pre>${JSON.stringify(snapshot.narrative, null, 2)}</pre>
  <h2>Assumptions Table</h2><pre>${JSON.stringify(snapshot.assumptions, null, 2)}</pre>
  <p>Ruleset ${snapshot.rulesetVersion} | Hash ${snapshot.calculationHash} | Calculated ${snapshot.calculatedAt}</p>
  <p>Legal Disclaimer: This report is deterministic and informational only; consult a notary and tax advisor.</p>
  </body></html>`;

  const browser = await puppeteer.launch({ headless: true, args: ["--no-sandbox"] });
  const page = await browser.newPage();
  await page.setContent(html, { waitUntil: "networkidle0" });
  const pdf = await page.pdf({ format: "A4", printBackground: true });
  await browser.close();

  return new NextResponse(pdf, {
    headers: { "Content-Type": "application/pdf", "Content-Disposition": `attachment; filename=report-${projectId}.pdf` }
  });
}
