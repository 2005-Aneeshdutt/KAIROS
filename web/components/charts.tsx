"use client";

import {
  Area, AreaChart, CartesianGrid, Line, LineChart, ReferenceDot, ReferenceLine,
  ResponsiveContainer, Scatter, ScatterChart, Tooltip, XAxis, YAxis, ZAxis, Cell,
} from "recharts";
import { BUCKET_COLOR } from "@/lib/api";

const axis = { stroke: "#5b6680", fontSize: 11 };
const grid = "#1d2638";

export function QiniChart({ data }: { data: { x: number[]; y: number[]; auuc: number } }) {
  const pts = (data.x || []).map((x, i) => ({ x, model: data.y[i], random: x }));
  return (
    <ResponsiveContainer width="100%" height={220}>
      <AreaChart data={pts} margin={{ top: 8, right: 10, left: -18, bottom: 0 }}>
        <defs>
          <linearGradient id="qini" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#e6005a" stopOpacity={0.5} />
            <stop offset="100%" stopColor="#e6005a" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={grid} />
        <XAxis dataKey="x" tickFormatter={(v) => `${Math.round(v * 100)}%`} {...axis} />
        <YAxis {...axis} />
        <Tooltip contentStyle={tip} formatter={(v: number) => v.toFixed(3)} />
        <Area type="monotone" dataKey="model" stroke="#e6005a" strokeWidth={2} fill="url(#qini)" name="Kairos" />
        <Line type="monotone" dataKey="random" stroke="#5b6680" strokeDasharray="4 4" dot={false} name="Random" />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function MarginalRoiChart({
  curve, knee, budget,
}: { curve: any[]; knee: any; budget: number }) {
  return (
    <ResponsiveContainer width="100%" height={240}>
      <AreaChart data={curve} margin={{ top: 8, right: 12, left: -8, bottom: 0 }}>
        <defs>
          <linearGradient id="roi" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#3b82f6" stopOpacity={0.5} />
            <stop offset="100%" stopColor="#3b82f6" stopOpacity={0} />
          </linearGradient>
        </defs>
        <CartesianGrid stroke={grid} />
        <XAxis dataKey="budget" tickFormatter={(v) => `$${Math.round(v)}`} {...axis} />
        <YAxis tickFormatter={(v) => `$${Math.round(v / 1000)}k`} {...axis} />
        <Tooltip contentStyle={tip}
          formatter={(v: number, n) => [n === "revenue" ? `$${Math.round(v).toLocaleString()}` : v, n]}
          labelFormatter={(v) => `Budget $${Math.round(Number(v)).toLocaleString()}`} />
        <Area type="monotone" dataKey="revenue" stroke="#3b82f6" strokeWidth={2} fill="url(#roi)" />
        {knee?.budget != null && (
          <ReferenceDot x={knee.budget} y={knee.revenue} r={5} fill="#22c55e" stroke="#fff"
            label={{ value: "knee — stop here", position: "top", fill: "#22c55e", fontSize: 11 }} />
        )}
        <ReferenceLine x={budget} stroke="#e6005a" strokeWidth={2} />
      </AreaChart>
    </ResponsiveContainer>
  );
}

export function BanditChart({ curve }: { curve: any[] }) {
  return (
    <ResponsiveContainer width="100%" height={220}>
      <LineChart data={curve} margin={{ top: 8, right: 10, left: -18, bottom: 0 }}>
        <CartesianGrid stroke={grid} />
        <XAxis dataKey="round" {...axis} />
        <YAxis {...axis} />
        <Tooltip contentStyle={tip} />
        <Line type="monotone" dataKey="oracle" stroke="#5b6680" strokeDasharray="4 4" dot={false} name="Oracle (ceiling)" />
        <Line type="monotone" dataKey="thompson" stroke="#e6005a" strokeWidth={2} dot={false} name="Kairos (learning)" />
        <Line type="monotone" dataKey="random" stroke="#64748b" strokeWidth={1.5} dot={false} name="Random" />
      </LineChart>
    </ResponsiveContainer>
  );
}

export function SegmentScatter({ points, live = [], onPick }: { points: any[]; live?: any[]; onPick: (id: string) => void }) {
  return (
    <ResponsiveContainer width="100%" height={300}>
      <ScatterChart margin={{ top: 10, right: 16, left: -6, bottom: 8 }}>
        <CartesianGrid stroke={grid} />
        <XAxis type="number" dataKey="base_rate" name="Baseline P(buy)"
          tickFormatter={(v) => `${Math.round(v * 100)}%`} {...axis}
          label={{ value: "Would buy anyway →", position: "insideBottom", offset: -2, fill: "#5b6680", fontSize: 11 }} />
        <YAxis type="number" dataKey="uplift" name="Incremental lift"
          tickFormatter={(v) => `${(v * 100).toFixed(0)}%`} {...axis}
          label={{ value: "↑ Marketing changes outcome", angle: -90, position: "insideLeft", fill: "#5b6680", fontSize: 11 }} />
        <ZAxis type="number" dataKey="inc_revenue" range={[20, 240]} />
        <ReferenceLine y={0} stroke="#5b6680" strokeOpacity={0.5} />
        <Tooltip contentStyle={tip} cursor={{ strokeDasharray: "3 3" }}
          formatter={(v: number, n) => [typeof v === "number" ? v.toFixed(3) : v, n]} />
        <Scatter data={points} onClick={(e: any) => e?.customer_id && onPick(e.customer_id)}>
          {points.map((p, i) => (
            <Cell key={i} fill={BUCKET_COLOR[p.bucket] || "#64748b"} fillOpacity={0.7} />
          ))}
        </Scatter>
        {live.length > 0 && (
          <Scatter data={live} shape="star" name="Live shoppers">
            {live.map((p, i) => (
              <Cell key={i} fill="#e6005a" stroke="#fff" strokeWidth={1.5} />
            ))}
          </Scatter>
        )}
      </ScatterChart>
    </ResponsiveContainer>
  );
}

const tip = {
  background: "#0d1320",
  border: "1px solid #222c42",
  borderRadius: 10,
  fontSize: 12,
  color: "#e7ecf5",
};
