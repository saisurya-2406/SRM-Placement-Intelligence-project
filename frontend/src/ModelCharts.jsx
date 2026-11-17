import React from "react";
import {
  Area, AreaChart, Bar, BarChart, CartesianGrid, Cell, Pie, PieChart,
  ResponsiveContainer, Tooltip, XAxis, YAxis,
} from "recharts";

export function EvaluationBarChart({ data }) {
  return <ResponsiveContainer width="100%" height="100%"><BarChart data={data} margin={{ top: 8, right: 8, left: -20, bottom: 0 }} barGap={5}><CartesianGrid strokeDasharray="3 5" vertical={false} stroke="#e9ebf2" /><XAxis dataKey="name" axisLine={false} tickLine={false} tick={{ fill: "#858ba0", fontSize: 10 }} interval={0} angle={-12} textAnchor="end" height={48} /><YAxis axisLine={false} tickLine={false} tick={{ fill: "#969bad", fontSize: 10 }} domain={[0, 100]} /><Tooltip cursor={{ fill: "#f6f5fa" }} contentStyle={{ border: "1px solid #ececf3", borderRadius: 12, boxShadow: "0 12px 30px #1e214012" }} /><Bar dataKey="accuracy" name="Accuracy" fill="#b6a2ff" radius={[5, 5, 0, 0]} maxBarSize={20} /><Bar dataKey="f1" name="Suitable F1" fill="#5545d7" radius={[5, 5, 0, 0]} maxBarSize={20} /></BarChart></ResponsiveContainer>;
}

export function RoleDistributionChart({ data, roles }) {
  const colors = ["#5b4bd8", "#8b7ee8", "#b4aaf1", "#73a6dc", "#77c7ad", "#e9b57c"];
  return <><ResponsiveContainer width="100%" height="100%"><PieChart><Pie data={data} dataKey="value" innerRadius={36} outerRadius={49} startAngle={90} endAngle={-270} stroke="none">{data.map((item, index) => <Cell key={item.name} fill={colors[index % colors.length]} />)}</Pie></PieChart></ResponsiveContainer><div className="ring-center"><strong>{roles}</strong><small>roles</small></div></>;
}

export function ModelF1Chart({ data }) {
  return <ResponsiveContainer width="100%" height="100%"><AreaChart data={data} margin={{ top: 10, right: 18, left: -20, bottom: 2 }}><defs><linearGradient id="f1Fill" x1="0" y1="0" x2="0" y2="1"><stop offset="0%" stopColor="#5b4bd8" stopOpacity={0.2} /><stop offset="100%" stopColor="#5b4bd8" stopOpacity={0.01} /></linearGradient></defs><CartesianGrid strokeDasharray="4 5" vertical={false} stroke="#e9ebf2" /><XAxis dataKey="model" axisLine={false} tickLine={false} tick={{ fill: "#777e94", fontSize: 11 }} /><YAxis domain={[0, 100]} axisLine={false} tickLine={false} tick={{ fill: "#969bad", fontSize: 10 }} /><Tooltip contentStyle={{ borderRadius: 12, border: "1px solid #e9e8f0" }} /><Area type="monotone" dataKey="suitable_f1_pct" name="Suitable-class F1 (%)" stroke="#5b4bd8" fill="url(#f1Fill)" strokeWidth={3} activeDot={{ r: 5 }} /></AreaChart></ResponsiveContainer>;
}
