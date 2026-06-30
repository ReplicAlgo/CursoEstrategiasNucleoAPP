import streamlit as st
import pandas as pd
import numpy as np
from plotly.subplots import make_subplots
import plotly.graph_objects as go

# --- Load Excel for historical data ---
@st.cache_data
def load_data():
    raw = pd.read_excel("DatosResultadosEstrategiasAPP.xlsx", header=None)
    
    # Names of strategies from Row 4 (Index 3), Columns C to I (Indices 2 to 8)
    strategies = list(raw.iloc[3, 2:9].values)
    
    # Extract data starting from Row 5 (Index 4) down
    # Column B (Index 1) is Date. Columns C to I (Indices 2 to 8) are the Equities.
    historical_df = raw.iloc[4:, [1] + list(range(2, 9))].copy()
    historical_df.columns = ['time'] + strategies
    
    # Ensure proper datetime parsing for the index
    historical_df['time'] = pd.to_datetime(historical_df['time'])
    historical_df['year'] = historical_df['time'].dt.year
    
    # Clean and force numeric conversions
    for col in strategies:
        historical_df[col] = pd.to_numeric(historical_df[col], errors='coerce').ffill().fillna(100000)
        
    return historical_df, strategies

historical_df, strategies = load_data()

# --- Branding ---
st.image("EstrategiasNucleo.png", width=900)

# Description text box
st.markdown(
    """
    <div style='border:2px solid #ccc; border-radius:8px; padding:20px; margin-bottom:20px; font-size:16px; line-height:1.6;'>
        <strong style='font-size:18px;'>Uso:</strong><br>
        Esta app está diseñada para simular portafolios combinando diferentes estrategias de inversión núcleo. 
        El objetivo principal es combinar sistemas con baja correlación para mejorar el perfil riesgo-retorno general.
        <ul>
            <li>Maximizar el retorno esperado del portafolio combinado.</li>
            <li>Minimizar el Max Drawdown (pérdida máxima de la cartera).</li>
            <li><strong>Lo ideal:</strong> aumentar el retorno y reducir el riesgo mediante diversificación sistemática.</li>
        </ul>
        <strong style='font-size:18px;'>Inputs:</strong>
        <ul>
            <li><strong>Asset Allocation:</strong> los sliders indican el porcentaje (%) asignado a cada estrategia núcleo.</li>
            <li>Si elegimos <strong>RotacionDefensiva D4</strong>, podemos tener asignaciones que lleguen hasta 110-120% sin que el apalancamiento sea real. Esto porque la estrategia de Rotación Defensiva entra cuando muchas de las otras no están activas y están en efectivo.</li>
        </ul>
    </div>
    """, 
    unsafe_allow_html=True
)

st.markdown("<h2 style='text-align: center; margin-top:10px;'>Estrategias Núcleo Portafolio Simulacion</h2>", unsafe_allow_html=True)

# --- Sidebar: Portfolio Settings ---
st.sidebar.header("Portfolio Settings")

# Checkbox to toggle benchmarks on/off
show_benchmarks = st.sidebar.checkbox("Show Benchmarks (SPY & 60/40)", value=True, help="Toggle to show/hide standard comparison benchmarks on the charts and summary metric blocks.")

st.sidebar.subheader("Strategy Allocations (%)")

allocations = {}
for strat in strategies:
    strat_lower = strat.lower()
    
    # Assign correct default positions using robust case-insensitive keyword checks
    if "perezoso" in strat_lower:
        default_val = 10
    elif "seis" in strat_lower:
        default_val = 30
    elif "defensiva" in strat_lower or "d4" in strat_lower:
        default_val = 20
    elif "weather" in strat_lower or "taa" in strat_lower:
        default_val = 30
    elif "core9" in strat_lower or "core 9" in strat_lower:
        default_val = 30
    else:
        default_val = 0
            
    allocations[strat] = st.sidebar.slider(f"{strat}", 0, 200, default_val, step=5,
                                           help="0 = off, 100 = full size, >100 = leverage")

total_alloc = sum(allocations.values())
st.sidebar.markdown(f"**Total Allocation: {total_alloc}%**")

if total_alloc > 100:
    st.sidebar.warning(f"⚠️ Leverage applied: {total_alloc - 100}% over 100%")

# --- Portfolio Performance Calculations ---
portfolio_equity = np.zeros(len(historical_df))

for strat in strategies:
    weight = allocations[strat] / 100.0
    strat_fluctuations = historical_df[strat].values - 100000
    portfolio_equity += strat_fluctuations * weight

# Re-apply the baseline starting equity to get final portfolio value
final_portfolio_equity = portfolio_equity + 100000

# Peak tracking for Percentage Drawdown
cummax_equity = np.maximum.accumulate(final_portfolio_equity)
drawdown_pct = ((final_portfolio_equity - cummax_equity) / cummax_equity) * 100

total_return = final_portfolio_equity[-1] - 100000
max_drawdown_pct = drawdown_pct.min()
dates = historical_df['time'].values

# --- Pre-calculate Benchmarks Baseline For KPIs ---
spy_return, spy_max_dd = 0.0, 0.0
if "BuyHold SPY" in historical_df.columns:
    spy_eq = historical_df["BuyHold SPY"].values
    spy_return = spy_eq[-1] - 100000
    spy_cm = np.maximum.accumulate(spy_eq)
    spy_max_dd = (((spy_eq - spy_cm) / spy_cm) * 100).min()

yf_return, yf_max_dd = 0.0, 0.0
if "BuyHold 60/40" in historical_df.columns:
    yf_eq = historical_df["BuyHold 60/40"].values
    yf_return = yf_eq[-1] - 100000
    yf_cm = np.maximum.accumulate(yf_eq)
    yf_max_dd = (((yf_eq - yf_cm) / yf_cm) * 100).min()

# Calculate exact yearly contributions as % returns
historical_df['portfolio_val'] = final_portfolio_equity
yearly_data = []
for year, group in historical_df.groupby('year'):
    # Main portfolio returns
    p_start = group['portfolio_val'].iloc[0]
    p_end = group['portfolio_val'].iloc[-1]
    p_return = ((p_end / p_start) - 1) * 100
    
    row_dict = {"Year": int(year), "Return": p_return}
    
    # Optional Benchmark calculations per year
    if "BuyHold SPY" in historical_df.columns:
        spy_start = group["BuyHold SPY"].iloc[0]
        spy_end = group["BuyHold SPY"].iloc[-1]
        row_dict["BuyHold SPY"] = ((spy_end / spy_start) - 1) * 100
        
    if "BuyHold 60/40" in historical_df.columns:
        yf_start = group["BuyHold 60/40"].iloc[0]
        yf_end = group["BuyHold 60/40"].iloc[-1]
        row_dict["BuyHold 60/40"] = ((yf_end / yf_start) - 1) * 100
        
    yearly_data.append(row_dict)

yearly_df = pd.DataFrame(yearly_data)

# --- Metric Display Cards ---
col1, col2 = st.columns(2)

# Build sub-metrics strings conditionally
spy_ret_str = f"<div style='font-size:13px; color:#888; margin-top:4px;'>SPY: ${spy_return:,.0f}</div>" if show_benchmarks and "BuyHold SPY" in historical_df.columns else ""
yf_ret_str = f"<div style='font-size:13px; color:#888;'>60/40: ${yf_return:,.0f}</div>" if show_benchmarks and "BuyHold 60/40" in historical_df.columns else ""

spy_dd_str = f"<div style='font-size:13px; color:#888; margin-top:4px;'>SPY: {spy_max_dd:.2f}%</div>" if show_benchmarks and "BuyHold SPY" in historical_df.columns else ""
yf_dd_str = f"<div style='font-size:13px; color:#888;'>60/40: {yf_max_dd:.2f}%</div>" if show_benchmarks and "BuyHold 60/40" in historical_df.columns else ""

with col1:
    st.markdown(
        f"""
        <div style='border:2px solid #ccc; border-radius:8px; padding:12px; text-align:center;'>
            <h5 style='margin:0;'>Total Net Return</h5>
            <p style='font-size:18px; color:{"green" if total_return >= 0 else "red"}; margin:4px 0 0 0;'>${total_return:,.0f}</p>
            {spy_ret_str}
            {yf_ret_str}
        </div>
        """, unsafe_allow_html=True
    )
with col2:
    st.markdown(
        f"""
        <div style='border:2px solid #ccc; border-radius:8px; padding:12px; text-align:center;'>
            <h5 style='margin:0;'>Max Drawdown (%)</h5>
            <p style='font-size:18px; color:red; margin:4px 0 0 0;'>{max_drawdown_pct:.2f}%</p>
            {spy_dd_str}
            {yf_dd_str}
        </div>
        """, unsafe_allow_html=True
    )

# --- Plotly Charting Engine ---
fig = make_subplots(
    rows=2, cols=1,
    shared_xaxes=True,
    vertical_spacing=0.04,
    subplot_titles=("Portfolio Equity Curve ($)", "Drawdown (%)"),
    row_heights=[0.65, 0.35]
)

# Upper Plot: Main Portfolio Equity Curve ($)
fig.add_trace(go.Scatter(x=dates, y=final_portfolio_equity, mode="lines", name="My Portfolio", line=dict(color="green", width=2.5)), row=1, col=1)

# Lower Plot: Main Portfolio Drawdown (%)
fig.add_trace(go.Scatter(x=dates, y=drawdown_pct, fill="tozeroy", name="Portfolio Drawdown", line=dict(color="red"), fillcolor="rgba(255,0,0,0.15)"), row=2, col=1)

# Dynamic Benchmark Injections
if show_benchmarks:
    # --- BuyHold SPY Calculations ---
    if "BuyHold SPY" in historical_df.columns:
        spy_equity = historical_df["BuyHold SPY"].values
        spy_cummax = np.maximum.accumulate(spy_equity)
        spy_dd_pct = ((spy_equity - spy_cummax) / spy_cummax) * 100
        
        fig.add_trace(go.Scatter(x=dates, y=spy_equity, mode="lines", name="BuyHold SPY", line=dict(color="orange", dash="dash", width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=dates, y=spy_dd_pct, mode="lines", name="BuyHold SPY", line=dict(color="orange", dash="dash", width=1.5), showlegend=False), row=2, col=1)

    # --- BuyHold 60/40 Calculations ---
    if "BuyHold 60/40" in historical_df.columns:
        yf_equity = historical_df["BuyHold 60/40"].values
        yf_cummax = np.maximum.accumulate(yf_equity)
        yf_dd_pct = ((yf_equity - yf_cummax) / yf_cummax) * 100
        
        fig.add_trace(go.Scatter(x=dates, y=yf_equity, mode="lines", name="BuyHold 60/40", line=dict(color="darkcyan", dash="dot", width=1.5)), row=1, col=1)
        fig.add_trace(go.Scatter(x=dates, y=yf_dd_pct, mode="lines", name="BuyHold 60/40", line=dict(color="darkcyan", dash="dot", width=1.5), showlegend=False), row=2, col=1)

fig.update_layout(height=650, showlegend=True, hovermode="x unified", dragmode="zoom")
fig.update_xaxes(
    rangeselector=dict(
        buttons=list([
            dict(count=1, label="1y", step="year", stepmode="backward"),
            dict(count=5, label="5y", step="year", stepmode="backward"),
            dict(count=10, label="10y", step="year", stepmode="backward"),
            dict(step="all", label="All")
        ]),
        bgcolor="lightgray", activecolor="gray"
    ),
    type="date", row=1, col=1
)

# Add % suffix to hover and axis labels for the second drawdown subplot
fig.update_yaxes(ticksuffix="%", row=2, col=1)

# Configure hover templates uniquely per row assignment
fig.update_traces(hovertemplate="$%{y:,.0f}", row=1, col=1)
fig.update_traces(hovertemplate="%{y:.2f}%", row=2, col=1)

st.plotly_chart(fig, use_container_width=True)

# --- Yearly Returns Table with Conditional Formatting ---
st.subheader("Yearly Returns")
if not yearly_df.empty:
    # Build clean formatting dictionary and isolate styling columns
    format_dict = {"Year": "{:d}", "Return": "{:+.2f}%"}
    style_target_cols = ['Return']
    
    if show_benchmarks:
        if "BuyHold SPY" in yearly_df.columns:
            format_dict["BuyHold SPY"] = "{:+.2f}%"
            style_target_cols.append("BuyHold SPY")
        if "BuyHold 60/40" in yearly_df.columns:
            format_dict["BuyHold 60/40"] = "{:+.2f}%"
            style_target_cols.append("BuyHold 60/40")
    else:
        # Drop columns explicitly if benchmarks are unchecked
        columns_to_keep = ['Year', 'Return']
        yearly_df = yearly_df[columns_to_keep]

    # Color negative numbers red, positive numbers green
    def color_returns(val):
        return 'color: red' if val < 0 else 'color: green'
    
    # Notice: changed .applymap() to .map() to support modern Pandas deployment on the cloud!
    styled_yearly_df = yearly_df.style.map(color_returns, subset=style_target_cols)\
                                      .format(format_dict)
    
    # Display dataframe with hidden tracking index column
    st.dataframe(styled_yearly_df, hide_index=True, use_container_width=True)
else:
    st.write("No data available.")
