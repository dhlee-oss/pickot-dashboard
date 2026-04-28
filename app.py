"""픽옷 대시보드 — Streamlit + Google Sheets (public CSV)"""

import numpy as np
import pandas as pd
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import streamlit as st

st.set_page_config(
    page_title="픽옷 Dashboard",
    page_icon="👗",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Brand colors ──────────────────────────────────────────────────────────────
C = {
    "primary": "#1D4ED8",
    "teal":    "#0E7490",
    "green":   "#047857",
    "orange":  "#B45309",
    "purple":  "#6D28D9",
    "red":     "#B91C1C",
    "text":    "#0F172A",
    "muted":   "#64748B",
    "bg":      "#F1F5F9",
    "card":    "#FFFFFF",
    "border":  "#CBD5E1",
    "light":   "#E2E8F0",
}

SHEET_ID = "1Y_qMUf6jwc6aW_TYQUL57eMF-6EbszulREa10wtNlWE"
GID      = "418868753"
CSV_URL  = (
    f"https://docs.google.com/spreadsheets/d/{SHEET_ID}"
    f"/export?format=csv&gid={GID}"
)

# ── CSS ───────────────────────────────────────────────────────────────────────
st.markdown(f"""
<style>
html, body, [data-testid="stAppViewContainer"] {{
    background: {C["bg"]} !important;
    font-family: -apple-system, 'Segoe UI', sans-serif;
}}
[data-testid="stSidebar"] {{ background: {C["text"]} !important; }}
[data-testid="stSidebar"] p,
[data-testid="stSidebar"] label,
[data-testid="stSidebar"] span {{ color: {C["light"]} !important; }}
[data-testid="stSidebar"] .stButton > button {{
    background: {C["primary"]}; color: white;
    border: none; border-radius: 8px; font-weight: 600;
}}
.block-container {{ padding: 2.5rem 2rem 3rem !important; max-width: 1400px; }}
/* Streamlit 기본 상단 여백 제거 후 재지정 */
[data-testid="stAppViewBlockContainer"] {{ padding-top: 2.5rem !important; }}
header[data-testid="stHeader"] {{ display: none; }}  /* 툴바 숨김 → 본문이 더 잘 보임 */

/* Header */
.dash-header {{
    border-bottom: 2px solid {C["primary"]};
    padding-bottom: .9rem; margin-bottom: 1.5rem;
}}
.dash-title {{
    font-size: 1.55rem; font-weight: 700; color: {C["text"]};
    margin: 0 0 3px; letter-spacing: -.5px;
}}
.dash-sub {{ font-size: .8rem; color: {C["muted"]}; }}
.badge {{
    background: {C["primary"]}20; color: {C["primary"]};
    border: 1px solid {C["primary"]}40; border-radius: 999px;
    font-size: .68rem; font-weight: 700; padding: 1px 9px;
    margin-left: 8px; vertical-align: middle; letter-spacing: .8px;
}}

/* KPI cards */
.kpi-card {{
    background: {C["card"]}; border: 1px solid {C["border"]};
    border-radius: 14px; padding: 1.1rem 1.3rem .9rem;
    box-shadow: 0 1px 4px rgba(0,0,0,.07);
    border-top: 3px solid var(--accent, {C["primary"]});
}}
.kpi-icon  {{ font-size: 1rem; margin-bottom: 5px; }}
.kpi-label {{
    font-size: .68rem; font-weight: 700; color: {C["muted"]};
    text-transform: uppercase; letter-spacing: .8px;
}}
.kpi-value {{
    font-size: 1.8rem; font-weight: 700; color: {C["text"]};
    line-height: 1.1; margin: 3px 0 5px;
}}
.kpi-sub {{ font-size: .76rem; color: {C["muted"]}; }}

/* Section headers */
.sec-title {{
    font-size: .88rem; font-weight: 700; color: {C["text"]};
    border-left: 3px solid var(--accent, {C["primary"]});
    padding-left: 10px; margin: .2rem 0 .7rem;
}}

/* Dataframe */
[data-testid="stDataFrame"] {{ border-radius: 10px; overflow: hidden; }}

/* Tab style */
.stTabs [data-baseweb="tab-list"] {{
    gap: 3px; background: {C["bg"]};
    border-bottom: 2px solid {C["border"]}; padding-bottom: 0;
}}
.stTabs [data-baseweb="tab"] {{
    font-weight: 600; font-size: .84rem; color: {C["muted"]};
    padding: 8px 18px; border-radius: 8px 8px 0 0;
}}
.stTabs [aria-selected="true"] {{
    background: {C["card"]}; color: {C["primary"]} !important;
}}
</style>
""", unsafe_allow_html=True)


# ── Helpers ───────────────────────────────────────────────────────────────────
def to_num(v) -> float:
    try:
        return float(str(v).replace(",", "").replace("원", "").strip())
    except Exception:
        return np.nan


def parse_month(label: str):
    s = str(label).strip()
    try:
        if "년" in s:
            y, m = s.replace("년", "|").replace("월", "").split("|")
            return pd.Timestamp(year=2000 + int(y), month=int(m.strip()), day=1)
        elif "월" in s:
            return pd.Timestamp(year=2024, month=int(s.replace("월", "").strip()), day=1)
    except Exception:
        pass
    return pd.NaT


def sec(title, accent=None):
    a = accent or C["primary"]
    st.markdown(
        f'<div class="sec-title" style="--accent:{a}">{title}</div>',
        unsafe_allow_html=True,
    )


def kpi_html(label, value, sub="", accent=None, icon=""):
    a = accent or C["primary"]
    return f"""
<div class="kpi-card" style="--accent:{a}">
  <div class="kpi-icon">{icon}</div>
  <div class="kpi-label">{label}</div>
  <div class="kpi-value">{value}</div>
  <div class="kpi-sub">{sub}</div>
</div>"""


def fmt(n, unit="", d=0) -> str:
    """차트·테이블용 — 만/억 단위로 축약"""
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "—"
    if abs(n) >= 1_0000_0000:
        return f"{n/1_0000_0000:.1f}억{unit}"
    if abs(n) >= 10_000:
        return f"{n/10_000:.0f}만{unit}"
    return f"{n:,.{d}f}{unit}"


def fmt_kpi(n, unit="") -> str:
    """KPI 카드용 — 정확한 수치를 콤마 포맷으로 표시"""
    if n is None or (isinstance(n, float) and np.isnan(n)):
        return "—"
    if abs(n) >= 1_0000_0000:
        return f"{n/1_0000_0000:.2f}억{unit}"
    return f"{n:,.0f}{unit}"


def rgba(hex_color: str, alpha: float) -> str:
    """'#rrggbb' + alpha → 'rgba(r,g,b,alpha)'  (Plotly fillcolor용)"""
    h = hex_color.lstrip("#")
    r, g, b = int(h[0:2], 16), int(h[2:4], 16), int(h[4:6], 16)
    return f"rgba({r},{g},{b},{alpha})"


def chart_base(fig, height=360, secondary=False):
    fig.update_layout(
        height=height,
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        font=dict(family="-apple-system, 'Segoe UI', sans-serif", size=12, color=C["text"]),
        margin=dict(l=8, r=8, t=44, b=8),
        legend=dict(
            orientation="h", yanchor="bottom", y=1.02,
            xanchor="right", x=1, bgcolor="rgba(0,0,0,0)", font_size=11,
        ),
        hoverlabel=dict(bgcolor="white", bordercolor=C["border"], font_size=12),
    )
    fig.update_xaxes(showgrid=False, zeroline=False, tickfont_size=11)
    if secondary:
        # subplot 전용 — secondary_y 키워드는 make_subplots 결과에만 유효
        fig.update_yaxes(
            showgrid=True, gridcolor="#F1F5F9", zeroline=False,
            tickfont_size=11, secondary_y=False,
        )
        fig.update_yaxes(showgrid=False, zeroline=False, secondary_y=True)
    else:
        fig.update_yaxes(
            showgrid=True, gridcolor="#F1F5F9", zeroline=False,
            tickfont_size=11,
        )
    return fig


# ── Data loading ──────────────────────────────────────────────────────────────
@st.cache_data(ttl=300, show_spinner=False)
def load_all():
    raw = pd.read_csv(CSV_URL, header=None, encoding="utf-8")

    # ── Summary KPIs — 행 인덱스로 직접 읽음 ────────────────────────────────────
    summary = {
        "수거건수":    to_num(raw.iloc[6, 2]),   # 수거 건수 합계
        "수거량_kg":  to_num(raw.iloc[7, 2]),   # 수거량 합계
        "건당평균_kg": to_num(raw.iloc[8, 2]),   # 건당 평균
        "cac_avg":   to_num(raw.iloc[9, 2]),   # 회원가입 비용(평균)
        "재이용건수":  to_num(raw.iloc[10, 2]),  # 재이용 건수
        "택배건수":   to_num(raw.iloc[12, 2]),  # 택배건수(발송)  ← row 11은 빈 행
        "가입자수":   to_num(raw.iloc[13, 2]),  # 가입자 수      ← row 13으로 이동
    }

    # ── 수거량 (rows 18-52, cols 1/2/3/4) ─────────────────────────────────────
    col_df = raw.iloc[18:53, [1, 2, 3, 4]].copy()
    col_df.columns = ["월", "수거량_kg", "수거건수", "평균_kg"]
    col_df["date"]     = col_df["월"].apply(parse_month)
    col_df["수거량_kg"] = col_df["수거량_kg"].apply(to_num)
    col_df["수거건수"]  = col_df["수거건수"].apply(to_num)
    col_df["평균_kg"]   = col_df["평균_kg"].apply(to_num)
    col_df = (
        col_df.dropna(subset=["date"])
              .query("수거량_kg > 0")
              .sort_values("date")
              .reset_index(drop=True)
    )

    # ── 가입자 (rows 18-52, cols 8/9/10/11) ───────────────────────────────────
    mem_df = raw.iloc[18:53, [8, 9, 10, 11]].copy()
    mem_df.columns = ["월", "광고비", "신규가입자", "CAC"]
    mem_df["date"]     = mem_df["월"].apply(parse_month)
    mem_df["광고비"]    = mem_df["광고비"].apply(to_num)
    mem_df["신규가입자"] = mem_df["신규가입자"].apply(to_num)
    mem_df["CAC"]       = mem_df["CAC"].apply(to_num)
    mem_df = (
        mem_df.dropna(subset=["date"])
              .query("신규가입자 > 0")
              .sort_values("date")
              .reset_index(drop=True)
    )
    mem_df["누적가입자"] = mem_df["신규가입자"].cumsum()

    # ── 매출 (rows 18-52, cols 14/15/16/17) ───────────────────────────────────
    rev_df = raw.iloc[18:53, [14, 15, 16, 17]].copy()
    rev_df.columns = ["월", "도매", "소매", "기타"]
    rev_df["date"]  = rev_df["월"].apply(parse_month)
    rev_df["도매"]  = rev_df["도매"].apply(to_num)
    rev_df["소매"]  = rev_df["소매"].apply(to_num)
    rev_df["기타"]  = rev_df["기타"].apply(to_num)
    rev_df["합계"]  = rev_df[["도매", "소매", "기타"]].fillna(0).sum(axis=1)
    rev_df = (
        rev_df.dropna(subset=["date"])
              .sort_values("date")
              .reset_index(drop=True)
    )

    # ── 적립금 (rows 59-93, cols 2/3/4/5/6) ───────────────────────────────────
    pts_df = raw.iloc[59:94, [2, 3, 4, 5, 6]].copy()
    pts_df.columns = ["월", "지급", "차감", "자사몰", "출금"]
    pts_df["date"]   = pts_df["월"].apply(parse_month)
    pts_df["지급"]   = pts_df["지급"].apply(to_num)
    pts_df["차감"]   = pts_df["차감"].apply(to_num)
    pts_df["자사몰"] = pts_df["자사몰"].apply(to_num)
    pts_df["출금"]   = pts_df["출금"].apply(to_num)
    pts_df = (
        pts_df.dropna(subset=["date"])
              .dropna(subset=["지급"])
              .sort_values("date")
              .reset_index(drop=True)
    )
    pts_df["누적잔액"] = (
        pts_df["지급"].fillna(0) - pts_df["차감"].fillna(0)
    ).cumsum()

    # ── 적립금 요약 — 행 인덱스 직접 접근 (행 1개 추가로 전체 +1 이동) ─────────────
    pts_summary = {
        "총지급액":    to_num(raw.iloc[99, 2]),
        "현금출금액":  to_num(raw.iloc[100, 2]),
        "현금전환율":  str(raw.iloc[101, 2]).strip(),
        "자사몰사용액": to_num(raw.iloc[102, 2]),
        "자사몰사용율": str(raw.iloc[103, 2]).strip(),
        "수수료수입":  to_num(raw.iloc[104, 2]),
        "미사용잔액":  to_num(raw.iloc[105, 2]),
    }

    return col_df, mem_df, rev_df, pts_df, summary, pts_summary


# ── App ───────────────────────────────────────────────────────────────────────
def main():
    with st.spinner("데이터 불러오는 중…"):
        col_df, mem_df, rev_df, pts_df, summary, pts_summary = load_all()

    # ── Sidebar ───────────────────────────────────────────────────────────────
    with st.sidebar:
        st.markdown("## 👗 픽옷")
        st.markdown("뉴올코퍼레이션 데이터 대시보드")
        st.markdown("---")

        all_dates = sorted(
            set(list(col_df["date"]) + list(mem_df["date"]))
        )
        if all_dates:
            min_d, max_d = all_dates[0].date(), all_dates[-1].date()
            st.markdown("**📅 기간 필터**")
            start_d = st.date_input("시작", min_d, min_value=min_d, max_value=max_d)
            end_d   = st.date_input("종료", max_d, min_value=min_d, max_value=max_d)

            def filt(df):
                return df[
                    (df["date"].dt.date >= start_d) &
                    (df["date"].dt.date <= end_d)
                ]
            col_f = filt(col_df)
            mem_f = filt(mem_df)
            rev_f = filt(rev_df)
            pts_f = filt(pts_df)
        else:
            col_f, mem_f, rev_f, pts_f = col_df, mem_df, rev_df, pts_df

        st.markdown("---")
        if st.button("🔄 데이터 새로고침", use_container_width=True):
            st.cache_data.clear()
            st.rerun()

        st.markdown("---")
        with st.expander("🔍 읽힌 Summary 값 확인"):
            st.write({
                "수거량(kg)":   summary["수거량_kg"],
                "수거건수":      summary["수거건수"],
                "건당평균(kg)":  summary["건당평균_kg"],
                "CAC(원)":       summary["cac_avg"],
                "가입자수(명)":  summary["가입자수"],
                "적립금잔액(원)": pts_summary["미사용잔액"],
                "자사몰사용율":   pts_summary["자사몰사용율"],
                "현금전환율":     pts_summary["현금전환율"],
            })
        st.markdown("---")
        st.caption(f"업데이트: {pd.Timestamp.now().strftime('%Y-%m-%d %H:%M')}")

    # ── Header ────────────────────────────────────────────────────────────────
    st.markdown(f"""
<div class="dash-header">
  <div class="dash-title">
    픽옷 <span style="font-weight:400;color:{C['muted']}">Dashboard</span>
    <span class="badge">CONFIDENTIAL</span>
  </div>
  <div class="dash-sub">비대면 의류수거 서비스 · pickot.kr · 뉴올코퍼레이션</div>
</div>""", unsafe_allow_html=True)

    # ── Summary KPI cards ─────────────────────────────────────────────────────
    k1, k2, k3, k4 = st.columns(4, gap="small")

    # Summary — 인덱스 직접 파싱값 사용
    total_kg  = summary["수거량_kg"]
    total_cnt = summary["수거건수"]
    total_mem = summary["가입자수"]
    cac       = summary["cac_avg"]
    pts_bal   = pts_summary["미사용잔액"] if pts_summary["미사용잔액"] else 0
    mall_rate = pts_summary["자사몰사용율"]

    with k1:
        st.markdown(kpi_html(
            "총 수거량 (완료기준)", fmt_kpi(total_kg, " kg"),
            f"완료건수 {int(total_cnt):,}건 · 건당 {summary['건당평균_kg']:.1f}kg", C["teal"], "♻️",
        ), unsafe_allow_html=True)
    with k2:
        st.markdown(kpi_html(
            "누적 가입자", fmt_kpi(total_mem, " 명"),
            f"평균 CAC {fmt_kpi(cac, '원')}", C["primary"], "👤",
        ), unsafe_allow_html=True)
    with k3:
        total_rev = rev_f["합계"].sum()
        st.markdown(kpi_html(
            "누적 매출", fmt_kpi(total_rev) if total_rev > 0 else "입력 전",
            "도매 · 소매 · 기타 합산", C["green"], "💰",
        ), unsafe_allow_html=True)
    with k4:
        st.markdown(kpi_html(
            "적립금 잔액", fmt_kpi(pts_bal, " 원"),
            f"자사몰 전환율 {mall_rate} · 현금전환율 {pts_summary['현금전환율']}", C["orange"], "🎁",
        ), unsafe_allow_html=True)

    st.markdown("<div style='height:1.2rem'></div>", unsafe_allow_html=True)

    # ── Tabs ──────────────────────────────────────────────────────────────────
    tab1, tab2, tab3, tab4 = st.tabs(
        ["♻️ 수거량", "👤 가입자", "💰 매출", "🎁 적립금"]
    )

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 1 — 수거량
    # ══════════════════════════════════════════════════════════════════════════
    with tab1:
        left, right = st.columns([3, 1], gap="medium")

        with left:
            sec("월별 수거량 (kg) / 수거건수", C["teal"])
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(
                x=col_f["date"], y=col_f["수거량_kg"],
                name="수거량(kg)", marker_color=C["teal"], marker_line_width=0,
                text=col_f["수거량_kg"],
                texttemplate="%{y:,.0f}",
                textposition="outside",
                textfont=dict(size=9, color=C["muted"]),
                hovertemplate="%{x|%Y-%m}<br><b>%{y:,.1f} kg</b><extra></extra>",
            ), secondary_y=False)
            fig.add_trace(go.Scatter(
                x=col_f["date"], y=col_f["수거건수"],
                name="수거건수(건)", mode="lines+markers",
                line=dict(color=C["primary"], width=2),
                marker=dict(size=5, color=C["primary"]),
                texttemplate="",
                hovertemplate="%{x|%Y-%m}<br>수거건수: <b>%{y:,}건</b><extra></extra>",
            ), secondary_y=True)
            fig.update_yaxes(
                title_text="수거량 (kg)", secondary_y=False,
                showgrid=True, gridcolor="#F1F5F9", zeroline=False,
            )
            fig.update_yaxes(
                title_text="수거건수 (건)", secondary_y=True,
                showgrid=False, zeroline=False,
            )
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            chart_base(fig, secondary=True)
            st.plotly_chart(fig, use_container_width=True)

        with right:
            sec("건당 평균 수거량", C["teal"])
            avg_valid = col_f[col_f["평균_kg"] > 0]
            fig2 = go.Figure(go.Scatter(
                x=avg_valid["date"], y=avg_valid["평균_kg"],
                mode="lines+markers",
                line=dict(color=C["teal"], width=2.5),
                marker=dict(size=5, color=C["teal"]),
                fill="tozeroy", fillcolor=rgba(C["teal"], 0.09),
                hovertemplate="%{x|%Y-%m}<br><b>%{y:.1f} kg/건</b><extra></extra>",
            ))
            chart_base(fig2, height=220)
            st.plotly_chart(fig2, use_container_width=True)
            if len(avg_valid):
                st.metric("기간 평균", f"{avg_valid['평균_kg'].mean():.1f} kg/건")
                st.metric("최고 기록",  f"{avg_valid['평균_kg'].max():.1f} kg/건")

        # Table
        sec("월별 수거 현황")
        tbl = col_f[["date", "수거건수", "수거량_kg", "평균_kg"]].copy()
        tbl["월"] = tbl["date"].dt.strftime("%Y-%m")
        tbl = tbl[["월", "수거건수", "수거량_kg", "평균_kg"]].sort_values("월", ascending=False)
        tbl.columns = ["월", "수거건수(건)", "수거량(kg)", "건당평균(kg)"]
        st.dataframe(tbl, use_container_width=True, hide_index=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 2 — 가입자
    # ══════════════════════════════════════════════════════════════════════════
    with tab2:
        left, right = st.columns([3, 1], gap="medium")

        with left:
            sec("월별 신규가입자 & 광고비", C["primary"])
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            fig.add_trace(go.Bar(
                x=mem_f["date"], y=mem_f["신규가입자"],
                name="신규가입자(명)",
                marker_color=C["primary"], marker_line_width=0,
                text=mem_f["신규가입자"],
                texttemplate="%{y:,.0f}",
                textposition="outside",
                textfont=dict(size=9, color=C["muted"]),
                hovertemplate="%{x|%Y-%m}<br><b>%{y:,}명</b><extra></extra>",
            ), secondary_y=False)
            ad_valid = mem_f[mem_f["광고비"] > 0]
            if len(ad_valid):
                fig.add_trace(go.Scatter(
                    x=ad_valid["date"], y=ad_valid["광고비"],
                    name="광고비(원)", mode="lines+markers",
                    line=dict(color=C["orange"], width=2),
                    marker=dict(size=5, color=C["orange"]),
                    hovertemplate="%{x|%Y-%m}<br>광고비: %{y:,}원<extra></extra>",
                ), secondary_y=True)
            fig.update_yaxes(
                title_text="신규가입자 (명)", secondary_y=False,
                showgrid=True, gridcolor="#F1F5F9", zeroline=False,
            )
            fig.update_yaxes(
                title_text="광고비 (원)", secondary_y=True,
                showgrid=False, zeroline=False,
            )
            chart_base(fig, secondary=True)
            fig.update_layout(paper_bgcolor="rgba(0,0,0,0)", plot_bgcolor="rgba(0,0,0,0)")
            st.plotly_chart(fig, use_container_width=True)

        with right:
            sec("CAC 추이", C["orange"])
            cac_valid = mem_f[mem_f["CAC"] > 0]
            if len(cac_valid):
                fig3 = go.Figure(go.Scatter(
                    x=cac_valid["date"], y=cac_valid["CAC"],
                    mode="lines+markers",
                    line=dict(color=C["orange"], width=2.5),
                    marker=dict(size=5),
                    fill="tozeroy", fillcolor=rgba(C["orange"], 0.09),
                    hovertemplate="%{x|%Y-%m}<br><b>CAC %{y:,}원</b><extra></extra>",
                ))
                chart_base(fig3, height=200)
                st.plotly_chart(fig3, use_container_width=True)
                st.metric("최근 CAC", f"{cac_valid['CAC'].iloc[-1]:,.0f}원")
                st.metric("평균 CAC",  f"{cac_valid['CAC'].mean():,.0f}원")
                st.metric("최저 CAC",  f"{cac_valid['CAC'].min():,.0f}원")
            else:
                st.info("광고비 데이터 없음")

        sec("누적 가입자 성장", C["primary"])
        fig4 = go.Figure()
        fig4.add_trace(go.Scatter(
            x=mem_f["date"], y=mem_f["누적가입자"],
            mode="lines", name="누적가입자",
            line=dict(color=C["primary"], width=3),
            fill="tozeroy", fillcolor=rgba(C["primary"], 0.08),
            hovertemplate="%{x|%Y-%m}<br>누적: <b>%{y:,}명</b><extra></extra>",
        ))
        chart_base(fig4, height=230)
        st.plotly_chart(fig4, use_container_width=True)

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 3 — 매출
    # ══════════════════════════════════════════════════════════════════════════
    with tab3:
        has_rev = rev_f["합계"].sum() > 0

        if not has_rev:
            st.info(
                "💡 매출 데이터가 Google Sheet에 아직 입력되지 않았습니다.  \n"
                "Sheet '대시보드용 데이터' → 매출 섹션 (도매/소매/기타 열)에 "
                "월별 매출 금액을 입력하면 자동으로 반영됩니다."
            )
        else:
            sec("채널별 월간 매출 (도매 / 소매 / 기타)", C["green"])
            fig = go.Figure()
            for col_n, color in [("도매", C["green"]), ("소매", C["primary"]), ("기타", C["orange"])]:
                d = rev_f[rev_f[col_n].fillna(0) > 0]
                if len(d):
                    fig.add_trace(go.Bar(
                        x=d["date"], y=d[col_n],
                        name=col_n, marker_color=color, marker_line_width=0,
                        hovertemplate=f"%{{x|%Y-%m}}<br>{col_n}: %{{y:,}}원<extra></extra>",
                    ))
            fig.update_layout(barmode="stack")
            chart_base(fig, height=360)
            st.plotly_chart(fig, use_container_width=True)

            cl, cr = st.columns([1, 2], gap="medium")
            with cl:
                sec("매출 구성비", C["green"])
                totals = {
                    k: rev_f[k].sum()
                    for k in ["도매", "소매", "기타"]
                    if rev_f[k].sum() > 0
                }
                fig_pie = go.Figure(go.Pie(
                    labels=list(totals.keys()),
                    values=list(totals.values()),
                    hole=0.58,
                    marker_colors=[C["green"], C["primary"], C["orange"]],
                    textinfo="label+percent", textfont_size=12,
                    hovertemplate="%{label}: %{value:,}원 (%{percent})<extra></extra>",
                ))
                fig_pie.update_layout(
                    height=250, paper_bgcolor="rgba(0,0,0,0)",
                    margin=dict(l=10, r=10, t=10, b=10),
                    legend=dict(font_size=12),
                )
                st.plotly_chart(fig_pie, use_container_width=True)

            with cr:
                sec("월별 매출 테이블", C["green"])
                tbl_rev = rev_f[["date", "도매", "소매", "기타", "합계"]].copy()
                tbl_rev["월"] = tbl_rev["date"].dt.strftime("%Y-%m")
                st.dataframe(
                    tbl_rev[["월", "도매", "소매", "기타", "합계"]]
                    .sort_values("월", ascending=False),
                    use_container_width=True, hide_index=True,
                )

    # ══════════════════════════════════════════════════════════════════════════
    # TAB 4 — 적립금
    # ══════════════════════════════════════════════════════════════════════════
    with tab4:
        left, right = st.columns([3, 2], gap="medium")

        with left:
            sec("월별 적립금 지급 / 차감 / 자사몰 추이", C["orange"])
            pts_valid = pts_f[pts_f["지급"] > 0]
            fig = make_subplots(specs=[[{"secondary_y": True}]])
            for col_n, color in [("지급", C["green"]), ("차감", C["red"]), ("자사몰", C["purple"])]:
                d = pts_valid[pts_valid[col_n].fillna(0) > 0]
                if len(d):
                    fig.add_trace(go.Bar(
                        x=d["date"], y=d[col_n],
                        name=col_n, marker_color=color, marker_line_width=0,
                        text=d[col_n],
                        texttemplate="%{y:,.0f}",
                        textposition="outside",
                        textfont=dict(size=9, color=C["muted"]),
                        hovertemplate=f"%{{x|%Y-%m}}<br>{col_n}: %{{y:,}}원<extra></extra>",
                    ), secondary_y=False)
            fig.add_trace(go.Scatter(
                x=pts_valid["date"], y=pts_valid["누적잔액"],
                name="누적잔액", mode="lines+markers",
                line=dict(color=C["orange"], width=2.5, dash="dot"),
                marker=dict(size=5),
                hovertemplate="%{x|%Y-%m}<br>잔액: <b>%{y:,}원</b><extra></extra>",
            ), secondary_y=True)
            fig.update_yaxes(
                title_text="금액 (원)", secondary_y=False,
                showgrid=True, gridcolor="#F1F5F9", zeroline=False,
            )
            fig.update_yaxes(
                title_text="누적잔액 (원)", secondary_y=True,
                showgrid=False, zeroline=False,
            )
            fig.update_layout(
                barmode="group",
                paper_bgcolor="rgba(0,0,0,0)",
                plot_bgcolor="rgba(0,0,0,0)",
            )
            chart_base(fig, height=360, secondary=True)
            st.plotly_chart(fig, use_container_width=True)

        with right:
            # Gauge — 자사몰 전환율
            sec("자사몰 전환율 게이지", C["purple"])
            try:
                mall_pct = float(
                    pts_summary.get("자사몰 사용율", "0").replace("%", "").replace(",", "")
                )
            except Exception:
                mall_pct = 0.0

            fig_g = go.Figure(go.Indicator(
                mode="gauge+number",
                value=mall_pct,
                number={"suffix": "%", "font": {"size": 28, "color": C["text"]}},
                title={"text": "자사몰 사용율", "font": {"size": 12, "color": C["muted"]}},
                gauge={
                    "axis": {"range": [0, 10], "ticksuffix": "%", "tickfont": {"size": 10}},
                    "bar": {"color": C["purple"]},
                    "steps": [
                        {"range": [0, 3],  "color": "#FEF3C7"},
                        {"range": [3, 6],  "color": "#D1FAE5"},
                        {"range": [6, 10], "color": "#DBEAFE"},
                    ],
                    "threshold": {
                        "line": {"color": C["red"], "width": 2.5},
                        "thickness": 0.8, "value": 5,
                    },
                },
            ))
            fig_g.update_layout(
                height=200, paper_bgcolor="rgba(0,0,0,0)",
                margin=dict(l=20, r=20, t=20, b=10),
                font=dict(family="-apple-system, 'Segoe UI', sans-serif"),
            )
            st.plotly_chart(fig_g, use_container_width=True)

            # Stats table
            sec("적립금 주요 지표", C["orange"])
            stats = [
                ("총 지급액",        fmt(pts_summary["총지급액"], "원")),
                ("현금 출금액",      fmt(pts_summary["현금출금액"], "원")),
                ("현금 전환율",      pts_summary["현금전환율"]),
                ("자사몰 사용액",    fmt(pts_summary["자사몰사용액"], "원")),
                ("전환 수수료 수입", fmt(pts_summary["수수료수입"], "원")),
                ("미사용 잔액",      fmt(pts_summary["미사용잔액"], "원")),
            ]
            for label, val in stats:
                sc1, sc2 = st.columns([3, 2])
                sc1.markdown(
                    f"<div style='font-size:.78rem;color:{C['muted']};padding:3px 0'>{label}</div>",
                    unsafe_allow_html=True,
                )
                sc2.markdown(
                    f"<div style='font-size:.82rem;font-weight:600;color:{C['text']};padding:3px 0'>{val}원</div>",
                    unsafe_allow_html=True,
                )


if __name__ == "__main__":
    main()
