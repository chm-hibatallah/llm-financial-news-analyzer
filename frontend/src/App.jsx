import { useState, useEffect, useCallback } from "react";
import {
  LineChart, Line, BarChart, Bar, XAxis, YAxis, CartesianGrid,
  Tooltip, ResponsiveContainer, Cell, ComposedChart, Area,
  ReferenceLine, ScatterChart, Scatter, Legend,
} from "recharts";

// ─── Logo Components ─────────────────────────────────────────────────────────
const AppleLogo = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M17.05 13.5c0 3.04-2.31 5.5-5.05 5.5-2.74 0-5.05-2.46-5.05-5.5 0-3.04 2.31-5.5 5.05-5.5 2.74 0 5.05 2.46 5.05 5.5zm3.59-1.47c.62.8.96 1.79.96 2.97 0 3.86-3.13 7-7 7-3.87 0-7-3.14-7-7 0-1.18.34-2.17.96-2.97a7 7 0 0 0-1.01-1.21C5.15 10.16 4.5 11.3 4.5 12.5c0 4.69 3.81 8.5 8.5 8.5s8.5-3.81 8.5-8.5c0-1.2-.65-2.34-1.62-2.92-.31.39-.67.75-1.06 1.05z"/>
    <path d="M19 4.5c0 .83-.67 1.5-1.5 1.5S16 5.33 16 4.5 16.67 3 18 3 19 3.67 19 4.5z"/>
  </svg>
);

const TeslaLogo = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <path d="M12 2C6.48 2 2 6.48 2 12s4.48 10 10 10 10-4.48 10-10S17.52 2 12 2zm0 18c-4.41 0-8-3.59-8-8s3.59-8 8-8 8 3.59 8 8-3.59 8-8 8z"/>
    <path d="M12.5 7h-1v7h1V7zm0 9h-1v1h1v-1zM8 9h6v1H8zm0 3h6v1H8z"/>
  </svg>
);

const MicrosoftLogo = ({ size = 20 }) => (
  <svg width={size} height={size} viewBox="0 0 24 24" fill="currentColor">
    <rect x="3" y="3" width="7" height="7"/>
    <rect x="14" y="3" width="7" height="7"/>
    <rect x="3" y="14" width="7" height="7"/>
    <rect x="14" y="14" width="7" height="7"/>
  </svg>
);

// ─── Theme tokens ────────────────────────────────────────────────────────────
const THEMES = {
  dark: {
    bg:         "#080c14",
    surface:    "#0d1526",
    surfaceHi:  "#111d33",
    border:     "#1a2d4a",
    text:       "#e8f0fe",
    textMuted:  "#5a7499",
    textDim:    "#2d4a6a",
    accent:     "#00d4ff",
    accentSoft: "#003d5c",
    bull:       "#00e5a0",
    bear:       "#ff4d6d",
    bullSoft:   "#00251a",
    bearSoft:   "#2d0011",
    neutral:    "#f5c842",
    grid:       "#0f1e33",
    cardGlow:   "0 0 40px rgba(0,212,255,0.06)",
  },
  light: {
    bg:         "#f0f4fc",
    surface:    "#ffffff",
    surfaceHi:  "#f8faff",
    border:     "#dce6f5",
    text:       "#0d1a2e",
    textMuted:  "#6b84a3",
    textDim:    "#b0c4de",
    accent:     "#0057d9",
    accentSoft: "#deeaff",
    bull:       "#00a86b",
    bear:       "#e0003c",
    bullSoft:   "#e6fff5",
    bearSoft:   "#fff0f3",
    neutral:    "#d4960a",
    grid:       "#edf2fb",
    cardGlow:   "0 2px 20px rgba(0,87,217,0.08)",
  },
};

// ─── Mock data (replaced by real API when backend runs) ────────────────────
const TICKERS = ["AAPL", "TSLA", "MSFT"];
const TICKER_COLORS = { AAPL: "#00d4ff", TSLA: "#ff4d6d", MSFT: "#00e5a0" };
const TICKER_LOGOS = {
  AAPL: AppleLogo,
  TSLA: TeslaLogo,
  MSFT: MicrosoftLogo,
};

function generateTimeline(ticker, n = 60) {
  let price = { AAPL: 185, TSLA: 215, MSFT: 420 }[ticker];
  let score = 0.1;
  return Array.from({ length: n }, (_, i) => {
    const date = new Date(2025, 8, 1);
    date.setDate(date.getDate() + i);
    score += (Math.random() - 0.48) * 0.15;
    score  = Math.max(-0.9, Math.min(0.9, score));
    price *= 1 + score * 0.012 + (Math.random() - 0.5) * 0.018;
    return {
      date:  date.toISOString().slice(0, 10),
      score: +score.toFixed(3),
      price: +price.toFixed(2),
      vol:   +(Math.abs(score) * 0.02 + Math.random() * 0.01).toFixed(4),
      label: score > 0.15 ? "bullish" : score < -0.15 ? "bearish" : "neutral",
    };
  });
}

const MOCK_LEADERBOARD = [
  { ticker:"TSLA", model:"XGBoostClassifier",  auc:0.638, accuracy:0.571, f1:0.563, hit_rate:0.571, sharpe:1.24, cum_return:0.183 },
  { ticker:"MSFT", model:"XGBoostClassifier",  auc:0.612, accuracy:0.558, f1:0.541, hit_rate:0.558, sharpe:1.01, cum_return:0.142 },
  { ticker:"AAPL", model:"XGBoostClassifier",  auc:0.601, accuracy:0.545, f1:0.528, hit_rate:0.545, sharpe:0.87, cum_return:0.108 },
  { ticker:"TSLA", model:"LSTM",               auc:0.591, accuracy:0.536, f1:0.519, hit_rate:0.536, sharpe:0.74, cum_return:0.091 },
  { ticker:"AAPL", model:"LogisticRegression", auc:0.554, accuracy:0.518, f1:0.492, hit_rate:0.518, sharpe:0.41, cum_return:0.044 },
  { ticker:"MSFT", model:"LogisticRegression", auc:0.548, accuracy:0.512, f1:0.488, hit_rate:0.512, sharpe:0.38, cum_return:0.039 },
  { ticker:"POOLED",model:"XGBoostClassifier", auc:0.589, accuracy:0.534, f1:0.521, hit_rate:0.534, sharpe:0.93, cum_return:0.121 },
];

const MOCK_IMPORTANCE = [
  { feature:"sentiment_zscore",     score:0.182 },
  { feature:"vol_ratio_5_21",       score:0.154 },
  { feature:"rsi_14d",              score:0.131 },
  { feature:"sentiment_cross_7_30", score:0.118 },
  { feature:"price_vs_sma_30d",     score:0.097 },
  { feature:"return_5d",            score:0.088 },
  { feature:"atr_14d_pct",          score:0.076 },
  { feature:"mean_score",           score:0.062 },
  { feature:"bullish_ratio_roll_7d",score:0.054 },
  { feature:"news_day",             score:0.038 },
];

const MOCK_GRANGER = [
  { ticker:"AAPL",   cause:"sentiment_roll_7d",    effect:"daily_return",     lag:2, p:0.024, sig:true  },
  { ticker:"TSLA",   cause:"mean_score",            effect:"daily_return",     lag:1, p:0.031, sig:true  },
  { ticker:"TSLA",   cause:"sentiment_zscore",      effect:"forward_vol_5d",   lag:3, p:0.018, sig:true  },
  { ticker:"MSFT",   cause:"sentiment_cross_7_30",  effect:"daily_return",     lag:2, p:0.074, sig:false },
  { ticker:"AAPL",   cause:"mean_score",            effect:"forward_vol_5d",   lag:4, p:0.041, sig:true  },
  { ticker:"POOLED", cause:"sentiment_roll_7d",     effect:"daily_return",     lag:1, p:0.012, sig:true  },
  { ticker:"MSFT",   cause:"mean_score",            effect:"daily_return",     lag:3, p:0.119, sig:false },
  { ticker:"POOLED", cause:"sentiment_zscore",      effect:"forward_vol_5d",   lag:2, p:0.008, sig:true  },
];

const CORR_FEATURES = ["mean_score","sent_roll_7d","sent_zscore","rsi_14d","vol_ratio","return_5d","atr_pct","news_day"];
function genCorr() {
  return CORR_FEATURES.map(f => ({
    feature: f,
    ...Object.fromEntries(CORR_FEATURES.map(g => [g, f === g ? 1 : +((Math.random()*1.4-0.7)).toFixed(2)])),
  }));
}
const MOCK_CORR = genCorr();

// ─── Utility ─────────────────────────────────────────────────────────────────
const fmt  = (v, d=3) => v == null ? "—" : (+v).toFixed(d);
const pct  = v => v == null ? "—" : `${(+v*100).toFixed(1)}%`;
const sign = v => v >= 0 ? "+" : "";

function LogoComponent({ ticker, size = 14, color = "currentColor" }) {
  if (ticker === "AAPL") return <AppleLogo size={size} />;
  if (ticker === "TSLA") return <TeslaLogo size={size} />;
  if (ticker === "MSFT") return <MicrosoftLogo size={size} />;
  return null;
}

// ─── Sub-components ───────────────────────────────────────────────────────────

function TopBar({ theme, onToggle, activeView, setView, T }) {
  const views = ["timeline","overlay","heatmap","importance","granger","leaderboard"];
  const labels = { timeline:"Sentiment", overlay:"Price+Sentiment", heatmap:"Correlation", importance:"Features", granger:"Granger", leaderboard:"Models" };
  return (
    <header style={{
      background: T.surface, borderBottom:`1px solid ${T.border}`,
      display:"flex", alignItems:"center", gap:0,
      padding:"0 24px", height:56, position:"sticky", top:0, zIndex:100,
      boxShadow:`0 1px 0 ${T.border}`,
    }}>
      {/* Logo */}
      <div style={{ display:"flex", alignItems:"center", gap:10, marginRight:32, flexShrink:0 }}>
        <div style={{
          width:28, height:28, borderRadius:6,
          background:`linear-gradient(135deg,${T.accent},${T.bull})`,
          display:"flex", alignItems:"center", justifyContent:"center",
          fontSize:13, fontWeight:900, color:"#000",
        }}>FS</div>
        <span style={{ fontFamily:"'DM Serif Display',serif", fontSize:17, color:T.text, letterSpacing:-0.3 }}>
          FinSentiment<span style={{ color:T.accent }}>Lab</span>
        </span>
      </div>

      {/* Nav */}
      <nav style={{ display:"flex", gap:2, flex:1, overflowX:"auto" }}>
        {views.map(v => (
          <button key={v} onClick={() => setView(v)} style={{
            background: activeView === v ? T.accentSoft : "transparent",
            border: "none", borderRadius:6, padding:"6px 14px",
            color: activeView === v ? T.accent : T.textMuted,
            fontFamily:"'DM Mono',monospace", fontSize:11, fontWeight:500,
            cursor:"pointer", whiteSpace:"nowrap", letterSpacing:0.3,
            textTransform:"uppercase", transition:"all 0.15s",
          }}>{labels[v]}</button>
        ))}
      </nav>

      {/* Theme toggle */}
      <button onClick={onToggle} style={{
        background: T.surfaceHi, border:`1px solid ${T.border}`, borderRadius:20,
        padding:"5px 14px", color:T.textMuted, fontSize:11,
        fontFamily:"'DM Mono',monospace", cursor:"pointer", flexShrink:0,
        letterSpacing:0.5, transition:"all 0.2s",
      }}>{theme === "dark" ? "☀ LIGHT" : "● DARK"}</button>
    </header>
  );
}

function Card({ title, subtitle, children, T, style={} }) {
  return (
    <div style={{
      background: T.surface, border:`1px solid ${T.border}`, borderRadius:12,
      padding:24, boxShadow:T.cardGlow, ...style,
    }}>
      {(title || subtitle) && (
        <div style={{ marginBottom:20 }}>
          {title && <div style={{ fontFamily:"'DM Serif Display',serif", fontSize:16, color:T.text, marginBottom:3 }}>{title}</div>}
          {subtitle && <div style={{ fontFamily:"'DM Mono',monospace", fontSize:11, color:T.textMuted, letterSpacing:0.5 }}>{subtitle}</div>}
        </div>
      )}
      {children}
    </div>
  );
}

function TickerPill({ ticker, active, onClick, T }) {
  const c = TICKER_COLORS[ticker] || T.accent;
  return (
    <button onClick={onClick} style={{
      background: active ? c + "22" : "transparent",
      border:`1px solid ${active ? c : T.border}`, borderRadius:20,
      padding:"4px 12px", color: active ? c : T.textMuted,
      fontFamily:"'DM Mono',monospace", fontSize:11, cursor:"pointer",
      fontWeight: active ? 700 : 400, transition:"all 0.15s",
      display:"flex", alignItems:"center", gap:6,
    }}>
      <span style={{ display:"flex", color: c }}>
        <LogoComponent ticker={ticker} size={14} />
      </span>
      {ticker}
    </button>
  );
}

// ─── View: Sentiment Timeline ─────────────────────────────────────────────────
function SentimentTimeline({ T }) {
  const [ticker, setTicker] = useState("AAPL");
  const data = generateTimeline(ticker);

  const CustomDot = ({ cx, cy, payload }) => {
    if (!payload) return null;
    const color = payload.label === "bullish" ? T.bull : payload.label === "bearish" ? T.bear : T.neutral;
    return <circle cx={cx} cy={cy} r={3} fill={color} stroke="none" opacity={0.8} />;
  };

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:20 }}>
      <div style={{ display:"flex", gap:8 }}>
        {TICKERS.map(t => <TickerPill key={t} ticker={t} active={ticker===t} onClick={() => setTicker(t)} T={T} />)}
      </div>

      <Card title="Daily Sentiment Score" subtitle="FINBERT + CLAUDE ESCALATION · [-1, +1]" T={T}>
        <ResponsiveContainer width="100%" height={260}>
          <ComposedChart data={data} margin={{ top:8, right:8, bottom:0, left:-20 }}>
            <defs>
              <linearGradient id="bullGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={T.bull} stopOpacity={0.3}/>
                <stop offset="95%" stopColor={T.bull} stopOpacity={0}/>
              </linearGradient>
              <linearGradient id="bearGrad" x1="0" y1="0" x2="0" y2="1">
                <stop offset="5%"  stopColor={T.bear} stopOpacity={0.3}/>
                <stop offset="95%" stopColor={T.bear} stopOpacity={0}/>
              </linearGradient>
            </defs>
            <CartesianGrid stroke={T.grid} strokeDasharray="4 4" />
            <XAxis dataKey="date" tick={{ fontSize:10, fill:T.textMuted, fontFamily:"DM Mono" }}
              tickFormatter={d => d.slice(5)} interval={9} />
            <YAxis domain={[-1,1]} tick={{ fontSize:10, fill:T.textMuted, fontFamily:"DM Mono" }} />
            <Tooltip
              contentStyle={{ background:T.surfaceHi, border:`1px solid ${T.border}`, borderRadius:8,
                fontFamily:"DM Mono", fontSize:11 }}
              labelStyle={{ color:T.textMuted }}
              formatter={(v,n) => [fmt(v), n]}
            />
            <ReferenceLine y={0}  stroke={T.textDim} strokeDasharray="3 3" />
            <ReferenceLine y={0.15}  stroke={T.bull} strokeDasharray="2 4" strokeOpacity={0.4} />
            <ReferenceLine y={-0.15} stroke={T.bear} strokeDasharray="2 4" strokeOpacity={0.4} />
            <Area type="monotone" dataKey="score" stroke="none"
              fill="url(#bullGrad)" baseValue={0}
              data={data.map(d => ({ ...d, score: d.score > 0 ? d.score : 0 }))} />
            <Area type="monotone" dataKey="score" stroke="none"
              fill="url(#bearGrad)" baseValue={0}
              data={data.map(d => ({ ...d, score: d.score < 0 ? d.score : 0 }))} />
            <Line type="monotone" dataKey="score" stroke={TICKER_COLORS[ticker]}
              strokeWidth={2} dot={<CustomDot />} activeDot={{ r:5 }} />
          </ComposedChart>
        </ResponsiveContainer>
      </Card>

      {/* Rolling 7d */}
      <Card title="7-Day Rolling Sentiment" subtitle="SMOOTHED SIGNAL" T={T}>
        <ResponsiveContainer width="100%" height={160}>
          <LineChart data={data} margin={{ top:4, right:8, bottom:0, left:-20 }}>
            <CartesianGrid stroke={T.grid} strokeDasharray="4 4" />
            <XAxis dataKey="date" tick={{ fontSize:10, fill:T.textMuted, fontFamily:"DM Mono" }}
              tickFormatter={d => d.slice(5)} interval={9} />
            <YAxis domain={[-0.6,0.6]} tick={{ fontSize:10, fill:T.textMuted, fontFamily:"DM Mono" }} />
            <Tooltip contentStyle={{ background:T.surfaceHi, border:`1px solid ${T.border}`,
              borderRadius:8, fontFamily:"DM Mono", fontSize:11 }} />
            <ReferenceLine y={0} stroke={T.textDim} strokeDasharray="3 3" />
            <Line type="monotone" dataKey="score" stroke={T.accent}
              strokeWidth={2.5} dot={false}
              data={data.map((d,i,arr) => ({
                ...d, score: +arr.slice(Math.max(0,i-6),i+1).reduce((a,x)=>a+x.score,0) /
                              Math.min(7,i+1)
              }))} />
          </LineChart>
        </ResponsiveContainer>
      </Card>
    </div>
  );
}

// ─── View: Price + Sentiment Overlay ─────────────────────────────────────────
function PriceOverlay({ T }) {
  const [ticker, setTicker] = useState("TSLA");
  const data = generateTimeline(ticker, 90);
  const c = TICKER_COLORS[ticker];

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:20 }}>
      <div style={{ display:"flex", gap:8 }}>
        {TICKERS.map(t => <TickerPill key={t} ticker={t} active={ticker===t} onClick={() => setTicker(t)} T={T} />)}
      </div>

      <Card title={`${ticker} · Price + Sentiment`} subtitle="DUAL-AXIS OVERLAY · 90 DAYS" T={T}>
        <ResponsiveContainer width="100%" height={320}>
          <ComposedChart data={data} margin={{ top:8, right:50, bottom:0, left:0 }}>
            <CartesianGrid stroke={T.grid} strokeDasharray="4 4" />
            <XAxis dataKey="date" tick={{ fontSize:10, fill:T.textMuted, fontFamily:"DM Mono" }}
              tickFormatter={d => d.slice(5)} interval={14} />
            <YAxis yAxisId="price" orientation="left"
              tick={{ fontSize:10, fill:c, fontFamily:"DM Mono" }}
              tickFormatter={v => `$${v.toFixed(0)}`} />
            <YAxis yAxisId="score" orientation="right" domain={[-1,1]}
              tick={{ fontSize:10, fill:T.textMuted, fontFamily:"DM Mono" }} />
            <Tooltip contentStyle={{ background:T.surfaceHi, border:`1px solid ${T.border}`,
              borderRadius:8, fontFamily:"DM Mono", fontSize:11 }}
              formatter={(v,n) => [n==="price" ? `$${fmt(v,2)}` : fmt(v), n]} />
            <Area yAxisId="price" type="monotone" dataKey="price"
              stroke={c} strokeWidth={2} fill={c + "18"} />
            <Bar yAxisId="score" dataKey="score" maxBarSize={4} opacity={0.7}>
              {data.map((d, i) => (
                <Cell key={i} fill={d.score > 0 ? T.bull : T.bear} />
              ))}
            </Bar>
          </ComposedChart>
        </ResponsiveContainer>
        <div style={{ display:"flex", gap:20, marginTop:12, paddingTop:12,
          borderTop:`1px solid ${T.border}`, fontFamily:"DM Mono", fontSize:11 }}>
          <span style={{ color:T.bull }}>▐ Bullish sentiment</span>
          <span style={{ color:T.bear }}>▐ Bearish sentiment</span>
          <span style={{ color:c }}>── Price</span>
        </div>
      </Card>

      {/* Stat cards */}
      <div style={{ display:"grid", gridTemplateColumns:"repeat(4,1fr)", gap:12 }}>
        {[
          { label:"Avg Sentiment", val: fmt(data.reduce((a,d)=>a+d.score,0)/data.length) },
          { label:"Bullish Days",  val: data.filter(d=>d.label==="bullish").length },
          { label:"Bearish Days",  val: data.filter(d=>d.label==="bearish").length },
          { label:"Price Change",  val: pct((data[data.length-1].price-data[0].price)/data[0].price) },
        ].map(s => (
          <div key={s.label} style={{ background:T.surfaceHi, border:`1px solid ${T.border}`,
            borderRadius:10, padding:"14px 16px" }}>
            <div style={{ fontFamily:"DM Mono", fontSize:10, color:T.textMuted,
              letterSpacing:0.5, marginBottom:6 }}>{s.label.toUpperCase()}</div>
            <div style={{ fontFamily:"'DM Serif Display',serif", fontSize:22, color:T.text }}>{s.val}</div>
          </div>
        ))}
      </div>
    </div>
  );
}

// ─── View: Correlation Heatmap ────────────────────────────────────────────────
function CorrelationHeatmap({ T }) {
  const [ticker, setTicker] = useState("POOLED");
  const tickers = ["AAPL","TSLA","MSFT","POOLED"];

  function corrColor(v) {
    if (v === 1) return T.accent;
    if (v > 0.5)  return T.bull;
    if (v > 0.2)  return T.bull + "88";
    if (v > -0.2) return T.textDim;
    if (v > -0.5) return T.bear + "88";
    return T.bear;
  }

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:20 }}>
      <div style={{ display:"flex", gap:8 }}>
        {tickers.map(t => (
          <button key={t} onClick={() => setTicker(t)} style={{
            background: ticker===t ? T.accentSoft : "transparent",
            border:`1px solid ${ticker===t ? T.accent : T.border}`, borderRadius:6,
            padding:"5px 14px", color: ticker===t ? T.accent : T.textMuted,
            fontFamily:"DM Mono", fontSize:11, cursor:"pointer", transition:"all 0.15s",
          }}>{t}</button>
        ))}
      </div>

      <Card title="Pearson Correlation Matrix" subtitle={`FEATURES × FEATURES · ${ticker}`} T={T}>
        <div style={{ overflowX:"auto" }}>
          <table style={{ borderCollapse:"collapse", width:"100%", fontFamily:"DM Mono", fontSize:11 }}>
            <thead>
              <tr>
                <th style={{ padding:"6px 8px", color:T.textMuted, textAlign:"left", whiteSpace:"nowrap" }}></th>
                {CORR_FEATURES.map(f => (
                  <th key={f} style={{ padding:"6px 8px", color:T.textMuted,
                    fontSize:10, whiteSpace:"nowrap", fontWeight:500,
                    transform:"rotate(-30deg)", transformOrigin:"bottom left",
                    height:60, verticalAlign:"bottom",
                  }}>{f}</th>
                ))}
              </tr>
            </thead>
            <tbody>
              {MOCK_CORR.map(row => (
                <tr key={row.feature}>
                  <td style={{ padding:"4px 8px", color:T.textMuted, whiteSpace:"nowrap",
                    fontSize:10, paddingRight:12 }}>{row.feature}</td>
                  {CORR_FEATURES.map(f => {
                    const v = row[f];
                    return (
                      <td key={f} style={{
                        padding:"3px 2px", textAlign:"center",
                        background: v === 1 ? T.accent + "33" :
                          v > 0 ? T.bull + Math.round(Math.abs(v)*80).toString(16).padStart(2,"0") :
                                  T.bear + Math.round(Math.abs(v)*80).toString(16).padStart(2,"0"),
                        borderRadius:3, minWidth:38,
                      }}>
                        <span style={{ color: corrColor(v), fontWeight: v===1 ? 700 : 400 }}>
                          {v === 1 ? "1.00" : fmt(v,2)}
                        </span>
                      </td>
                    );
                  })}
                </tr>
              ))}
            </tbody>
          </table>
        </div>

        {/* Legend */}
        <div style={{ display:"flex", alignItems:"center", gap:4, marginTop:16,
          fontFamily:"DM Mono", fontSize:10, color:T.textMuted }}>
          <span style={{ color:T.bear }}>-1.0</span>
          {[-0.8,-0.6,-0.4,-0.2,0,0.2,0.4,0.6,0.8,1.0].map(v => (
            <div key={v} style={{
              width:20, height:12, borderRadius:2,
              background: v >= 0
                ? T.bull + Math.round(Math.abs(v)*80).toString(16).padStart(2,"0")
                : T.bear + Math.round(Math.abs(v)*80).toString(16).padStart(2,"0"),
            }} />
          ))}
          <span style={{ color:T.bull }}>+1.0</span>
        </div>
      </Card>
    </div>
  );
}

// ─── View: Feature Importance ─────────────────────────────────────────────────
function FeatureImportance({ T }) {
  const [model, setModel] = useState("XGBoostClassifier");
  const models = ["XGBoostClassifier","XGBoostRegressor","LogisticRegression"];
  const maxScore = MOCK_IMPORTANCE[0].score;

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:20 }}>
      <div style={{ display:"flex", gap:8 }}>
        {models.map(m => (
          <button key={m} onClick={() => setModel(m)} style={{
            background: model===m ? T.accentSoft : "transparent",
            border:`1px solid ${model===m ? T.accent : T.border}`, borderRadius:6,
            padding:"5px 14px", color: model===m ? T.accent : T.textMuted,
            fontFamily:"DM Mono", fontSize:11, cursor:"pointer", transition:"all 0.15s",
          }}>{m}</button>
        ))}
      </div>

      <Card title="Feature Importance" subtitle={`POOLED · ${model.toUpperCase()} · TOP 10`} T={T}>
        <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
          {MOCK_IMPORTANCE.map((item, i) => {
            const isSentiment = item.feature.includes("sentiment") || item.feature.includes("score") ||
                                item.feature.includes("bull") || item.feature.includes("bear") || item.feature.includes("news");
            const barColor = isSentiment ? T.accent : T.textMuted;
            const pct = item.score / maxScore;

            return (
              <div key={item.feature} style={{ display:"flex", alignItems:"center", gap:12 }}>
                <div style={{ fontFamily:"DM Mono", fontSize:11, color:T.textMuted,
                  width:16, textAlign:"right", flexShrink:0 }}>{i+1}</div>
                <div style={{ fontFamily:"DM Mono", fontSize:11, color: isSentiment ? T.accent : T.text,
                  width:190, flexShrink:0, overflow:"hidden", textOverflow:"ellipsis",
                  whiteSpace:"nowrap" }}>{item.feature}</div>
                <div style={{ flex:1, background:T.grid, borderRadius:3, height:8 }}>
                  <div style={{
                    width:`${pct*100}%`, height:"100%", borderRadius:3,
                    background:`linear-gradient(90deg,${barColor},${barColor}88)`,
                    transition:"width 0.6s ease",
                  }} />
                </div>
                <div style={{ fontFamily:"DM Mono", fontSize:11, color:T.textMuted,
                  width:48, textAlign:"right", flexShrink:0 }}>{fmt(item.score,4)}</div>
                {isSentiment && (
                  <div style={{ background:T.accentSoft, color:T.accent, borderRadius:4,
                    padding:"1px 6px", fontSize:9, fontFamily:"DM Mono",
                    letterSpacing:0.5, flexShrink:0 }}>SENT</div>
                )}
              </div>
            );
          })}
        </div>
        <div style={{ marginTop:20, padding:"12px 14px", background:T.surfaceHi,
          borderRadius:8, border:`1px solid ${T.border}`, fontFamily:"DM Mono",
          fontSize:11, color:T.textMuted, lineHeight:1.6 }}>
          <span style={{ color:T.accent }}>SENT</span> = sentiment-derived feature.
          {" "}Sentiment features account for{" "}
          <span style={{ color:T.accent }}>
            {pct(MOCK_IMPORTANCE.filter(i => i.feature.includes("sentiment")||i.feature.includes("score")||i.feature.includes("bull")||i.feature.includes("bear")||i.feature.includes("news"))
              .reduce((a,x)=>a+x.score,0))}
          </span> of total importance mass.
        </div>
      </Card>
    </div>
  );
}

// ─── View: Granger Causality ──────────────────────────────────────────────────
function GrangerView({ T }) {
  const sig  = MOCK_GRANGER.filter(r => r.sig);
  const nsig = MOCK_GRANGER.filter(r => !r.sig);

  return (
    <div style={{ display:"flex", flexDirection:"column", gap:20 }}>
      <Card title="Granger Causality Analysis" subtitle="LAGGED SENTIMENT → PRICE/VOL (SIGNIFICANT P<0.05)" T={T}>
        <div style={{ display:"flex", flexDirection:"column", gap:14 }}>
          {sig.map((r, i) => (
            <div key={i} style={{ padding:"10px 12px", background:T.surfaceHi, borderRadius:8,
              display:"flex", alignItems:"center", gap:16, border:`1px solid ${T.border}` }}>
              <div style={{ fontFamily:"DM Mono", fontSize:10, color:T.accent,
                fontWeight:700, minWidth:60 }}>{r.ticker}</div>
              <div style={{ flex:1, fontFamily:"DM Mono", fontSize:11, color:T.text }}>
                {r.cause} → {r.effect} (lag {r.lag})
              </div>
              <div style={{ fontFamily:"DM Mono", fontSize:10, color:T.bull,
                fontWeight:700 }}>p={r.p.toFixed(3)}</div>
            </div>
          ))}
        </div>
      </Card>

      <Card title="Non-Significant Relations (P≥0.05)" subtitle="NOT INCLUDED IN ANALYSIS" T={T}>
        <div style={{ display:"flex", flexDirection:"column", gap:10 }}>
          {nsig.map((r, i) => (
            <div key={i} style={{ padding:"8px 12px", background:T.grid, borderRadius:6,
              display:"flex", alignItems:"center", gap:16, fontFamily:"DM Mono", fontSize:11, color:T.textMuted }}>
              <span>{r.ticker}</span>
              <span style={{ flex:1 }}>{r.cause} → {r.effect}</span>
              <span>p={r.p.toFixed(3)}</span>
            </div>
          ))}
        </div>
      </Card>
    </div>
  );
}

// ─── View: Leaderboard ────────────────────────────────────────────────────────
function Leaderboard({ T }) {
  const cols = ["ticker","model","auc","accuracy","f1","hit_rate","sharpe","cum_return"];
  const labels = { ticker:"TICKER", model:"MODEL", auc:"AUC", accuracy:"ACCURACY", f1:"F1", hit_rate:"HIT RATE", sharpe:"SHARPE", cum_return:"CUM. RETURN" };

  return (
    <Card title="Model Leaderboard" subtitle="RANKED BY AUC (PRIMARY) · DESCENDING" T={T}>
      <div style={{ overflowX:"auto" }}>
        <table style={{ borderCollapse:"collapse", width:"100%", fontFamily:"DM Mono", fontSize:11 }}>
          <thead>
            <tr style={{ borderBottom:`1px solid ${T.border}` }}>
              {cols.map(c => (
                <th key={c} style={{
                  padding:"8px 12px", color:T.textMuted, fontSize:10,
                  fontWeight:700, textAlign:["ticker","model"].includes(c) ? "left" : "right",
                  whiteSpace:"nowrap",
                }}>{labels[c]}</th>
              ))}
            </tr>
          </thead>
          <tbody>
            {MOCK_LEADERBOARD.map((row, i) => (
              <tr key={i} style={{
                borderBottom:`1px solid ${T.grid}`,
                background: i % 2 ? T.surface : T.surfaceHi,
              }}>
                <td style={{ padding:"10px 12px", color:T.accent, display:"flex", alignItems:"center", gap:8 }}>
                  <span style={{ display:"flex", color: TICKER_COLORS[row.ticker] }}>
                    <LogoComponent ticker={row.ticker} size={14} />
                  </span>
                  {row.ticker}
                </td>
                <td style={{ padding:"10px 12px", color:T.text }}>{row.model}</td>
                {cols.slice(2).map(c => (
                  <td key={c} style={{
                    padding:"10px 12px", textAlign:"right",
                    color: c === "cum_return" && row[c] > 0.1 ? T.bull :
                           c === "cum_return" ? T.bear : T.text,
                    fontWeight: c === "auc" && i < 3 ? 700 : 400,
                  }}>{fmt(row[c], 3)}</td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </Card>
  );
}

// ─── Root App ─────────────────────────────────────────────────────────────────
export default function App() {
  const [theme, setTheme] = useState("dark");
  const [view,  setView]  = useState("overlay");
  const T = THEMES[theme];

  const VIEWS = {
    timeline:    <SentimentTimeline T={T} />,
    overlay:     <PriceOverlay T={T} />,
    heatmap:     <CorrelationHeatmap T={T} />,
    importance:  <FeatureImportance T={T} />,
    granger:     <GrangerView T={T} />,
    leaderboard: <Leaderboard T={T} />,
  };

  return (
    <div style={{
      minHeight:"100vh", background:T.bg, color:T.text,
      fontFamily:"system-ui,sans-serif", transition:"background 0.3s,color 0.3s",
    }}>
      <link href="https://fonts.googleapis.com/css2?family=DM+Serif+Display&family=DM+Mono:wght@300;400;500&display=swap" rel="stylesheet" />

      <TopBar theme={theme} onToggle={() => setTheme(t => t==="dark"?"light":"dark")}
        activeView={view} setView={setView} T={T} />

      <main style={{ maxWidth:1200, margin:"0 auto", padding:"28px 24px" }}>
        {VIEWS[view]}
      </main>

      {/* Footer */}
      <footer style={{ borderTop:`1px solid ${T.border}`, padding:"16px 24px",
        display:"flex", justifyContent:"center", gap:32,
        fontFamily:"DM Mono", fontSize:10, color:T.textDim }}>
        <span>FINSENTIMENT LAB</span>
        <span>FinBERT + Claude Haiku</span>
        <span>AAPL · TSLA · MSFT</span>
        <span>90-DAY WINDOW</span>
      </footer>
    </div>
  );
}
