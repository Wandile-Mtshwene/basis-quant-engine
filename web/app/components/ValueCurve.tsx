"use client";
import type { OptionResult } from "../lib/api";

// Option value vs spot (Black-Scholes) with the intrinsic payoff and strike marked.
export function ValueCurve({ res, strike, spot }: { res: OptionResult; strike: number; spot: number }) {
  const W = 760, H = 300, padL = 50, padR = 16, padT = 16, padB = 30;
  const pts = res.value_curve;
  const xs = pts.map((p) => p.spot);
  const maxV = Math.max(...pts.map((p) => Math.max(p.value, p.intrinsic))) || 1;
  const minX = xs[0], maxX = xs[xs.length - 1];

  const x = (s: number) => padL + ((s - minX) / (maxX - minX)) * (W - padL - padR);
  const y = (v: number) => padT + (1 - v / maxV) * (H - padT - padB);
  const line = (key: "value" | "intrinsic") =>
    "M" + pts.map((p) => `${x(p.spot)},${y(p[key])}`).join(" L");

  const yticks = [0, 0.33, 0.66, 1].map((f) => f * maxV);
  return (
    <svg viewBox={`0 0 ${W} ${H}`} className="w-full h-auto">
      {yticks.map((v, i) => (
        <g key={i}>
          <line x1={padL} x2={W - padR} y1={y(v)} y2={y(v)} stroke="var(--border)" />
          <text x={padL - 6} y={y(v) + 4} textAnchor="end" fontSize={11} fill="var(--muted)">{v.toFixed(0)}</text>
        </g>
      ))}
      {/* strike + current spot markers */}
      <line x1={x(strike)} x2={x(strike)} y1={padT} y2={H - padB} stroke="var(--muted)" strokeDasharray="3 3" />
      <text x={x(strike) + 3} y={padT + 11} fontSize={11} fill="var(--muted)">K={strike}</text>
      <line x1={x(spot)} x2={x(spot)} y1={padT} y2={H - padB} stroke="var(--warn)" strokeDasharray="4 3" />
      <text x={x(spot) + 3} y={padT + 24} fontSize={11} fill="var(--warn)">spot={spot}</text>

      <path d={line("intrinsic")} fill="none" stroke="var(--muted)" strokeWidth={1.4} strokeDasharray="5 4" />
      <path d={line("value")} fill="none" stroke="var(--accent)" strokeWidth={2.4} />

      {xs.filter((_, i) => i % 6 === 0).map((s) => (
        <text key={s} x={x(s)} y={H - padB + 18} textAnchor="middle" fontSize={11} fill="var(--muted)">{Math.round(s)}</text>
      ))}
    </svg>
  );
}
