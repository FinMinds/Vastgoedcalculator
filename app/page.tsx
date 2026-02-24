"use client";

import { useState } from "react";
import { Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";

type AnalysisResponse = { projectId: string; analysis: any };

const defaultPayload = {
  project: {
    region: "Vlaanderen",
    purchasePrice: 300000,
    estimatedValue: 320000,
    rentMonthly: 1400,
    loanAmount: 240000,
    loanYears: 20,
    interestRate: 0.0375,
    flags: { isPrimaryResidence: false, isInvestment: true, isNewBuild: false }
  },
  assumptions: {
    vacancyRate: 0.05,
    maintenanceRate: 0.1,
    insuranceMonthly: 55,
    managementMonthly: 60,
    taxModel: "private",
    indexationRate: 0.02
  }
};

export default function HomePage() {
  const [payload, setPayload] = useState(defaultPayload);
  const [result, setResult] = useState<AnalysisResponse | null>(null);

  const runAnalysis = async () => {
    const res = await fetch("/api/analyze", { method: "POST", body: JSON.stringify(payload) });
    const data = await res.json();
    setResult(data);
  };

  return (
    <main className="mx-auto max-w-6xl space-y-6 p-6">
      <h1 className="text-3xl font-semibold">Belgian Real Estate Investment Analyzer</h1>
      <section className="grid grid-cols-1 gap-4 md:grid-cols-2">
        <div className="card space-y-2">
          <h2 className="font-medium">Wizard Step 1-4 Input</h2>
          <label>Purchase Price<input className="input" type="number" value={payload.project.purchasePrice} onChange={(e) => setPayload({ ...payload, project: { ...payload.project, purchasePrice: Number(e.target.value) } })} /></label>
          <label>Rent Monthly<input className="input" type="number" value={payload.project.rentMonthly} onChange={(e) => setPayload({ ...payload, project: { ...payload.project, rentMonthly: Number(e.target.value) } })} /></label>
          <label>Loan Amount<input className="input" type="number" value={payload.project.loanAmount} onChange={(e) => setPayload({ ...payload, project: { ...payload.project, loanAmount: Number(e.target.value) } })} /></label>
          <label>Interest Rate<input className="input" type="number" step="0.0001" value={payload.project.interestRate} onChange={(e) => setPayload({ ...payload, project: { ...payload.project, interestRate: Number(e.target.value) } })} /></label>
          <button className="btn" onClick={runAnalysis}>Step 5: Review & Analyze</button>
        </div>
        {result && (
          <div className="card space-y-2">
            <h2 className="font-medium">KPI Cards</h2>
            <p>Gross Yield: {(result.analysis.kpis.grossYield * 100).toFixed(2)}%</p>
            <p>Net Yield: {(result.analysis.kpis.netYield * 100).toFixed(2)}%</p>
            <p>Cash-on-Cash: {(result.analysis.kpis.cashOnCash * 100).toFixed(2)}%</p>
            <p>DSCR: {result.analysis.kpis.dscr}</p>
            <p>Grade: {result.analysis.score.grade} ({result.analysis.score.overallScore})</p>
            <a className="btn inline-block" href={`/api/report?projectId=${result.projectId}`}>Download deterministic PDF</a>
          </div>
        )}
      </section>
      {result && (
        <section className="card">
          <h2 className="mb-3 font-medium">Sensitivity Tab</h2>
          <div className="h-72">
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={result.analysis.sensitivity}>
                <XAxis dataKey="vacancy" />
                <YAxis />
                <Tooltip />
                <Line dataKey="dscr" stroke="#60a5fa" />
              </LineChart>
            </ResponsiveContainer>
          </div>
        </section>
      )}
    </main>
  );
}
