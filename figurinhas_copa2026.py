import streamlit as st
import sqlite3
import pandas as pd
import re

# ─── CONFIG ────────────────────────────────────────────────────────────────────
st.set_page_config(
    page_title="Álbum Copa 2026 🏆",
    page_icon="⚽",
    layout="wide",
    initial_sidebar_state="expanded",
)

DB_PATH = "figurinhas_copa2026.db"

# ─── ESTRUTURA REAL DO ÁLBUM (Ludopédio PDF) ─────────────────────────────────
FLAGS = {
    "MEX": "🇲🇽", "RSA": "🇿🇦", "KOR": "🇰🇷", "CZE": "🇨🇿",
    "CAN": "🇨🇦", "BIH": "🇧🇦", "QAT": "🇶🇦", "SUI": "🇨🇭",
    "BRA": "🇧🇷", "MAR": "🇲🇦", "HAI": "🇭🇹", "SCO": "🏴󠁧󠁢󠁳󠁣󠁴󠁿",
    "USA": "🇺🇸", "PAR": "🇵🇾", "AUS": "🇦🇺", "TUR": "🇹🇷",
    "GER": "🇩🇪", "CUW": "🇨🇼", "CIV": "🇨🇮", "ECU": "🇪🇨",
    "NED": "🇳🇱", "JPN": "🇯🇵", "SWE": "🇸🇪", "TUN": "🇹🇳",
    "BEL": "🇧🇪", "EGY": "🇪🇬", "IRN": "🇮🇷", "NZL": "🇳🇿",
    "ESP": "🇪🇸", "CPV": "🇨🇻", "KSA": "🇸🇦", "URU": "🇺🇾",
    "FRA": "🇫🇷", "SEN": "🇸🇳", "IRQ": "🇮🇶", "NOR": "🇳🇴",
    "ARG": "🇦🇷", "ALG": "🇩🇿", "AUT": "🇦🇹", "JOR": "🇯🇴",
    "POR": "🇵🇹", "COD": "🇨🇩", "UZB": "🇺🇿", "COL": "🇨🇴",
    "ENG": "🏴󠁧󠁢󠁥󠁮󠁧󠁿", "CRO": "🇭🇷", "GHA": "🇬🇭", "PAN": "🇵🇦",
    "FWC": "🌍", "CC": "🥤",
}

COUNTRIES = {
    "MEX": "México",         "RSA": "África do Sul",    "KOR": "Coreia do Sul",  "CZE": "Rep. Tcheca",
    "CAN": "Canadá",         "BIH": "Bósnia",            "QAT": "Catar",          "SUI": "Suíça",
    "BRA": "Brasil",         "MAR": "Marrocos",          "HAI": "Haiti",          "SCO": "Escócia",
    "USA": "Estados Unidos", "PAR": "Paraguai",          "AUS": "Austrália",      "TUR": "Turquia",
    "GER": "Alemanha",       "CUW": "Curaçao",           "CIV": "Costa do Marfim","ECU": "Equador",
    "NED": "Holanda",        "JPN": "Japão",             "SWE": "Suécia",         "TUN": "Tunísia",
    "BEL": "Bélgica",        "EGY": "Egito",             "IRN": "Irã",            "NZL": "Nova Zelândia",
    "ESP": "Espanha",        "CPV": "Cabo Verde",        "KSA": "Arábia Saudita", "URU": "Uruguai",
    "FRA": "França",         "SEN": "Senegal",           "IRQ": "Iraque",         "NOR": "Noruega",
    "ARG": "Argentina",      "ALG": "Argélia",           "AUT": "Áustria",        "JOR": "Jordânia",
    "POR": "Portugal",       "COD": "Congo",             "UZB": "Uzbequistão",    "COL": "Colômbia",
    "ENG": "Inglaterra",     "CRO": "Croácia",           "GHA": "Gana",           "PAN": "Panamá",
}

GROUPS = {
    "Grupo A": ["MEX", "RSA", "KOR", "CZE"],
    "Grupo B": ["CAN", "BIH", "QAT", "SUI"],
    "Grupo C": ["BRA", "MAR", "HAI", "SCO"],
    "Grupo D": ["USA", "PAR", "AUS", "TUR"],
    "Grupo E": ["GER", "CUW", "CIV", "ECU"],
    "Grupo F": ["NED", "JPN", "SWE", "TUN"],
    "Grupo G": ["BEL", "EGY", "IRN", "NZL"],
    "Grupo H": ["ESP", "CPV", "KSA", "URU"],
    "Grupo I": ["FRA", "SEN", "IRQ", "NOR"],
    "Grupo J": ["ARG", "ALG", "AUT", "JOR"],
    "Grupo K": ["POR", "COD", "UZB", "COL"],
    "Grupo L": ["ENG", "CRO", "GHA", "PAN"],
}

# Reverse lookup: pais_code → grupo
PAIS_TO_GRUPO = {}
for g, codes in GROUPS.items():
    for c in codes:
        PAIS_TO_GRUPO[c] = g

# ─── DATABASE ────────────────────────────────────────────────────────────────
def get_conn():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_conn()
    c = conn.cursor()
    c.execute("""
        CREATE TABLE IF NOT EXISTS figurinhas (
            codigo     TEXT PRIMARY KEY,
            secao      TEXT NOT NULL,
            grupo      TEXT NOT NULL,
            pais_code  TEXT NOT NULL,
            numero     INTEGER NOT NULL,
            tenho      INTEGER DEFAULT 0,
            repetidas  INTEGER DEFAULT 0,
            colada     INTEGER DEFAULT 0,
            updated_at TEXT DEFAULT (datetime('now'))
        )
    """)
    c.execute("SELECT COUNT(*) FROM figurinhas")
    if c.fetchone()[0] == 0:
        rows = []
        # Figurinha 00
        rows.append(("00", "Especiais", "Especiais", "FWC", 0, 0, 0, 0))
        # FWC1-FWC19
        for i in range(1, 20):
            rows.append((f"FWC{i}", "Especiais", "Especiais", "FWC", i, 0, 0, 0))
        # Seleções: 20 cada
        for grupo, codes in GROUPS.items():
            for pais_code in codes:
                nome = COUNTRIES.get(pais_code, pais_code)
                for i in range(1, 21):
                    codigo = f"{pais_code}{i}"
                    rows.append((codigo, nome, grupo, pais_code, i, 0, 0, 0))
        # Coca-Cola CC1-CC14
        for i in range(1, 15):
            rows.append((f"CC{i}", "Coca-Cola", "Especiais", "CC", i, 0, 0, 0))

        c.executemany(
            "INSERT OR IGNORE INTO figurinhas (codigo, secao, grupo, pais_code, numero, tenho, repetidas, colada) VALUES (?,?,?,?,?,?,?,?)",
            rows
        )
    conn.commit()
    conn.close()

def load_all():
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM figurinhas", conn)
    conn.close()
    return df

def load_pais(pais_code):
    conn = get_conn()
    df = pd.read_sql("SELECT * FROM figurinhas WHERE pais_code=? ORDER BY numero", conn, params=(pais_code,))
    conn.close()
    return df

def update_fig(codigo, tenho, repetidas, colada):
    conn = get_conn()
    conn.execute(
        "UPDATE figurinhas SET tenho=?, repetidas=?, colada=?, updated_at=datetime('now') WHERE codigo=?",
        (int(tenho), int(repetidas), int(colada), codigo)
    )
    conn.commit(); conn.close()

def mark_all_pais(pais_code, tenho):
    conn = get_conn()
    conn.execute("UPDATE figurinhas SET tenho=?, updated_at=datetime('now') WHERE pais_code=?", (int(tenho), pais_code))
    conn.commit(); conn.close()

def get_stats():
    conn = get_conn()
    row = conn.execute("""
        SELECT COUNT(*) total,
               SUM(tenho) tenho,
               SUM(repetidas) repetidas,
               SUM(colada) coladas
        FROM figurinhas
    """).fetchone()
    conn.close()
    total = row["total"]
    tenho = int(row["tenho"] or 0)
    repetidas = int(row["repetidas"] or 0)
    coladas = int(row["coladas"] or 0)
    faltam = total - tenho
    pct = round(tenho / total * 100, 1) if total else 0
    return total, tenho, faltam, repetidas, coladas, pct

# ─── CSS ─────────────────────────────────────────────────────────────────────
def inject_css():
    st.markdown("""
    <style>
    @import url('https://fonts.googleapis.com/css2?family=Bebas+Neue&family=Outfit:wght@400;500;600;700&display=swap');
    html,[class*="css"]{ font-family:'Outfit',sans-serif; }
    .stApp{ background:linear-gradient(150deg,#060b18 0%,#0c1628 60%,#080f1a 100%); min-height:100vh; }

    .hero-title{
        font-family:'Bebas Neue',sans-serif; font-size:3.2rem; letter-spacing:4px;
        background:linear-gradient(90deg,#FFD700,#FF6B35,#FFD700);
        -webkit-background-clip:text; -webkit-text-fill-color:transparent;
        text-align:center; line-height:1; margin-bottom:2px;
    }
    .hero-sub{
        text-align:center; color:#7a8599; font-size:0.8rem;
        letter-spacing:3px; text-transform:uppercase; margin-top:2px;
    }
    .sec-title{
        font-family:'Bebas Neue',sans-serif; font-size:1.45rem; letter-spacing:2px;
        color:#FFD700; border-bottom:2px solid rgba(255,215,0,0.2);
        padding-bottom:5px; margin:16px 0 12px;
    }
    .stat-card{
        background:linear-gradient(135deg,rgba(255,255,255,0.06),rgba(255,255,255,0.02));
        border:1px solid rgba(255,215,0,0.18); border-radius:13px; padding:16px 12px; text-align:center;
    }
    .sn{ font-family:'Bebas Neue',sans-serif; font-size:2.4rem; line-height:1; }
    .sl{ color:#7a8599; font-size:0.7rem; text-transform:uppercase; letter-spacing:1.5px; margin-top:3px; }
    .pw{ background:rgba(255,255,255,0.08); border-radius:20px; height:20px; overflow:hidden; margin:8px 0 4px; }
    .pf{ height:100%; background:linear-gradient(90deg,#FFD700,#FF6B35); border-radius:20px;
         display:flex; align-items:center; justify-content:flex-end; padding-right:7px; min-width:3%; }
    .pt{ color:#060b18; font-weight:700; font-size:0.7rem; }
    .code-b{
        font-family:'Bebas Neue',sans-serif; font-size:0.95rem; color:#FFD700;
        background:rgba(255,215,0,0.1); border:1px solid rgba(255,215,0,0.25);
        border-radius:6px; padding:2px 8px; letter-spacing:1px;
        min-width:52px; text-align:center; display:inline-block;
    }
    .bt{ background:rgba(34,197,94,.15); border:1px solid #22c55e; color:#22c55e;
         border-radius:6px; padding:2px 9px; font-size:.7rem; font-weight:600; }
    .bf{ background:rgba(239,68,68,.12); border:1px solid rgba(239,68,68,.5); color:#ef4444;
         border-radius:6px; padding:2px 9px; font-size:.7rem; font-weight:600; }
    .br{ background:rgba(245,158,11,.15); border:1px solid #f59e0b; color:#f59e0b;
         border-radius:6px; padding:2px 8px; font-size:.7rem; font-weight:600; }

    div[data-testid="stSidebar"]{ background:rgba(6,11,24,.97)!important; border-right:1px solid rgba(255,215,0,.1)!important; }
    .stButton>button{
        background:linear-gradient(135deg,#FFD700,#FF6B35)!important; color:#060b18!important;
        font-weight:700!important; border:none!important; border-radius:8px!important;
    }
    .stButton>button:hover{ opacity:.82!important; }
    h1,h2,h3{ color:#e8edf5!important; }
    p,label,.stMarkdown p{ color:#c8d0de!important; }
    div[data-testid="stCheckbox"] label span{ color:#c8d0de!important; }
    .stSelectbox>div>div,
    .stTextInput>div>div>input,
    .stNumberInput>div>div>input,
    .stTextArea>div>textarea{
        background:rgba(255,255,255,.06)!important;
        border-color:rgba(255,215,0,.2)!important;
        color:#e8edf5!important; border-radius:8px!important;
    }
    .stTabs [data-baseweb="tab"]{ color:#7a8599!important; font-weight:500; }
    .stTabs [aria-selected="true"]{ color:#FFD700!important; border-bottom-color:#FFD700!important; }
    </style>
    """, unsafe_allow_html=True)

# ─── INIT ────────────────────────────────────────────────────────────────────
init_db()
inject_css()

st.markdown('<h1 class="hero-title">⚽ ÁLBUM COPA 2026</h1>', unsafe_allow_html=True)
st.markdown('<p class="hero-sub">Panini FIFA World Cup 2026 • Controle de Figurinhas</p>', unsafe_allow_html=True)
st.markdown("<br>", unsafe_allow_html=True)

# ─── SIDEBAR ─────────────────────────────────────────────────────────────────
with st.sidebar:
    st.markdown("### 🗂️ Menu")
    pagina = st.radio("", [
        "📊 Dashboard",
        "🌍 Gerenciar por Grupo",
        "🔁 Repetidas / Trocas",
        "🔍 Buscar Figurinha",
        "📥 Importar / Exportar",
    ], label_visibility="collapsed")
    st.markdown("---")
    total, tenho, faltam, repetidas, coladas, pct = get_stats()
    p = max(pct, 1)
    st.markdown(f"""
    <div class="stat-card">
        <div class="sn" style="color:#FFD700">{pct}%</div>
        <div class="sl">Álbum Completo</div>
        <div class="pw"><div class="pf" style="width:{p}%"><span class="pt">{tenho}/{total}</span></div></div>
    </div><br>
    <div style="display:grid;grid-template-columns:1fr 1fr;gap:7px;text-align:center;">
        <div style="background:rgba(34,197,94,.1);border:1px solid rgba(34,197,94,.3);border-radius:10px;padding:9px 4px;">
            <div style="font-family:'Bebas Neue';font-size:1.7rem;color:#22c55e">{tenho}</div>
            <div style="color:#7a8599;font-size:.65rem;text-transform:uppercase">Tenho</div>
        </div>
        <div style="background:rgba(239,68,68,.1);border:1px solid rgba(239,68,68,.3);border-radius:10px;padding:9px 4px;">
            <div style="font-family:'Bebas Neue';font-size:1.7rem;color:#ef4444">{faltam}</div>
            <div style="color:#7a8599;font-size:.65rem;text-transform:uppercase">Faltam</div>
        </div>
        <div style="background:rgba(245,158,11,.1);border:1px solid rgba(245,158,11,.3);border-radius:10px;padding:9px 4px;">
            <div style="font-family:'Bebas Neue';font-size:1.7rem;color:#f59e0b">{repetidas}</div>
            <div style="color:#7a8599;font-size:.65rem;text-transform:uppercase">Repetidas</div>
        </div>
        <div style="background:rgba(96,165,250,.1);border:1px solid rgba(96,165,250,.3);border-radius:10px;padding:9px 4px;">
            <div style="font-family:'Bebas Neue';font-size:1.7rem;color:#60a5fa">{coladas}</div>
            <div style="color:#7a8599;font-size:.65rem;text-transform:uppercase">Coladas</div>
        </div>
    </div>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# 📊 DASHBOARD
# ════════════════════════════════════════════════════════════════════════════
if pagina == "📊 Dashboard":
    c1,c2,c3,c4,c5 = st.columns(5)
    for col,label,val,icon,color in [
        (c1,"Total Álbum",total,"📖","#FFD700"),
        (c2,"Tenho",tenho,"✅","#22c55e"),
        (c3,"Faltam",faltam,"❌","#ef4444"),
        (c4,"Repetidas",repetidas,"🔁","#f59e0b"),
        (c5,"Coladas",coladas,"📌","#60a5fa"),
    ]:
        with col:
            st.markdown(f"""
            <div class="stat-card">
                <div style="font-size:1.5rem">{icon}</div>
                <div class="sn" style="color:{color}">{val}</div>
                <div class="sl">{label}</div>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("<br>", unsafe_allow_html=True)
    df_all = load_all()

    # Progresso por Grupo
    st.markdown('<div class="sec-title">PROGRESSO POR GRUPO</div>', unsafe_allow_html=True)
    df_grp = df_all[df_all["grupo"] != "Especiais"].groupby("grupo").agg(
        total=("codigo","count"), tenho=("tenho","sum")
    ).reset_index()
    df_grp["pct"] = (df_grp["tenho"]/df_grp["total"]*100).round(1)
    order = list(GROUPS.keys())
    df_grp["_o"] = df_grp["grupo"].map({g:i for i,g in enumerate(order)})
    df_grp = df_grp.sort_values("_o")

    cl, cr = st.columns(2)
    for i, (_, row) in enumerate(df_grp.iterrows()):
        ps = row["pct"]
        color = "#22c55e" if ps==100 else ("#FFD700" if ps>=70 else ("#f59e0b" if ps>=30 else "#ef4444"))
        bar = "#22c55e" if ps==100 else "linear-gradient(90deg,#FFD700,#FF6B35)"
        teams = " ".join([f'{FLAGS.get(c,"")}' for c in GROUPS.get(row["grupo"],[])])
        with (cl if i%2==0 else cr):
            st.markdown(f"""
            <div style="background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);border-radius:10px;padding:11px 14px;margin:5px 0;">
                <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:4px;">
                    <span style="color:#e8edf5;font-weight:600;font-size:.92rem;">{row['grupo']} <span style="font-size:.85rem">{teams}</span></span>
                    <span style="color:{color};font-size:.82rem;font-weight:700;">{int(row['tenho'])}/{int(row['total'])} ({ps}%)</span>
                </div>
                <div style="background:rgba(255,255,255,.08);border-radius:5px;height:6px;overflow:hidden;">
                    <div style="width:{max(ps,1)}%;height:100%;background:{bar};border-radius:5px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Grid de seleções
    st.markdown('<div class="sec-title">PROGRESSO POR SELEÇÃO</div>', unsafe_allow_html=True)
    df_pais = df_all[df_all["pais_code"].isin(COUNTRIES.keys())].groupby("pais_code").agg(
        total=("codigo","count"), tenho=("tenho","sum")
    ).reset_index()
    df_pais["pct"] = (df_pais["tenho"]/df_pais["total"]*100).round(0).astype(int)
    df_pais = df_pais.sort_values("pct", ascending=False)

    cols = st.columns(8)
    for i, (_, row) in enumerate(df_pais.iterrows()):
        ps = row["pct"]
        c = "#22c55e" if ps==100 else ("#FFD700" if ps>=50 else ("#f59e0b" if ps>0 else "#ef4444"))
        with cols[i%8]:
            st.markdown(f"""
            <div style="text-align:center;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);border-radius:9px;padding:8px 4px;margin:3px 0;">
                <div style="font-size:1.3rem">{FLAGS.get(row['pais_code'],'')}</div>
                <div style="font-family:'Bebas Neue';font-size:.8rem;color:#FFD700;letter-spacing:1px">{row['pais_code']}</div>
                <div style="font-family:'Bebas Neue';font-size:1.2rem;color:{c};">{ps}%</div>
                <div style="color:#7a8599;font-size:.6rem;">{int(row['tenho'])}/20</div>
                <div style="background:rgba(255,255,255,.08);border-radius:3px;height:4px;margin-top:4px;overflow:hidden;">
                    <div style="width:{max(ps,1)}%;height:100%;background:{c};border-radius:3px;"></div>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # Especiais
    st.markdown('<div class="sec-title">ESPECIAIS</div>', unsafe_allow_html=True)
    df_esp = df_all[df_all["grupo"] == "Especiais"]
    t_esp = len(df_esp); h_esp = int(df_esp["tenho"].sum())
    p_esp = round(h_esp/t_esp*100,1) if t_esp else 0
    st.markdown(f"""
    <div style="background:rgba(255,215,0,.06);border:1px solid rgba(255,215,0,.2);border-radius:10px;padding:12px 18px;">
        <span style="font-family:'Bebas Neue';color:#FFD700;font-size:1.1rem;">🌍 FWC History (00 + FWC1-19) &nbsp;+&nbsp; 🥤 Coca-Cola (CC1-14)</span><br>
        <span style="color:#c8d0de;font-size:.88rem;">{h_esp} de {t_esp} figurinhas especiais ({p_esp}%)</span>
    </div>
    """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# 🌍 GERENCIAR POR GRUPO
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "🌍 Gerenciar por Grupo":
    st.markdown('<div class="sec-title">GERENCIAR FIGURINHAS</div>', unsafe_allow_html=True)

    grupo_options = list(GROUPS.keys()) + ["🌍 Especiais FWC", "🥤 Coca-Cola"]
    grupo_sel = st.selectbox("Selecione o Grupo:", grupo_options)

    # Resolve pais_code list
    if grupo_sel in GROUPS:
        codes_in_group = GROUPS[grupo_sel]
        pais_options = {c: f"{FLAGS.get(c,'')} {COUNTRIES.get(c,c)} ({c})" for c in codes_in_group}
        pais_label = st.selectbox("Selecione a Seleção:", list(pais_options.values()))
        pais_code_sel = [k for k,v in pais_options.items() if v==pais_label][0]
    elif "FWC" in grupo_sel:
        pais_code_sel = "FWC"
    else:
        pais_code_sel = "CC"

    df = load_pais(pais_code_sel)
    tenho_s = int(df["tenho"].sum())
    total_s = len(df)
    pct_s   = round(tenho_s/total_s*100,1) if total_s else 0

    flag_s = FLAGS.get(pais_code_sel,"")
    name_s = COUNTRIES.get(pais_code_sel, {"FWC":"FIFA World Cup History","CC":"Coca-Cola"}.get(pais_code_sel, pais_code_sel))

    ca, cb = st.columns(2)
    with ca:
        if st.button(f"✅ Marcar TODAS — {name_s}"):
            mark_all_pais(pais_code_sel, True); st.rerun()
    with cb:
        if st.button("❌ Desmarcar TODAS"):
            mark_all_pais(pais_code_sel, False); st.rerun()

    st.markdown(f"""
    <div style="background:rgba(255,255,255,.04);border:1px solid rgba(255,255,255,.09);border-radius:12px;padding:13px 18px;margin:10px 0;">
        <div style="display:flex;justify-content:space-between;align-items:center;margin-bottom:7px;">
            <span style="font-size:1.9rem">{flag_s}</span>
            <div style="text-align:right;">
                <span style="font-family:'Bebas Neue';color:#FFD700;font-size:1.25rem;">{name_s}</span>
                <br><span style="color:#7a8599;font-size:.8rem;">{tenho_s} de {total_s} figurinhas ({pct_s}%)</span>
            </div>
        </div>
        <div style="background:rgba(255,255,255,.08);border-radius:6px;height:8px;overflow:hidden;">
            <div style="width:{max(pct_s,1)}%;height:100%;background:linear-gradient(90deg,#FFD700,#FF6B35);border-radius:6px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("---")

    # Renderiza figurinhas em grade de 5 colunas
    changed = False
    rows_list = list(df.iterrows())
    chunk_size = 5
    for start in range(0, len(rows_list), chunk_size):
        chunk = rows_list[start:start+chunk_size]
        cols = st.columns(chunk_size)
        for i, (_, row) in enumerate(chunk):
            with cols[i]:
                has = bool(row["tenho"])
                bg  = "rgba(34,197,94,.09)" if has else "rgba(255,255,255,.03)"
                bd  = "rgba(34,197,94,.4)" if has else "rgba(255,255,255,.07)"
                rep_txt = f'<div style="color:#f59e0b;font-size:.65rem;margin-top:2px;">🔁 {row["repetidas"]}x</div>' if row["repetidas"]>0 else ""
                pin_txt = '<div style="color:#60a5fa;font-size:.65rem;">📌 Colada</div>' if row["colada"] else ""

                st.markdown(f"""
                <div style="background:{bg};border:1px solid {bd};border-radius:9px;padding:10px 8px;text-align:center;margin-bottom:3px;">
                    <div style="font-family:'Bebas Neue';font-size:1rem;color:#FFD700;letter-spacing:1px">{row['codigo']}</div>
                    {rep_txt}{pin_txt}
                </div>
                """, unsafe_allow_html=True)

                new_t = st.checkbox("Tenho", value=has, key=f"t_{row['codigo']}")
                new_r, new_c = 0, False
                if new_t:
                    new_r = st.number_input("Extras", 0, 20, int(row["repetidas"]), key=f"r_{row['codigo']}")
                    new_c = st.checkbox("Colada", bool(row["colada"]), key=f"c_{row['codigo']}")

                if has!=new_t or int(row["repetidas"])!=new_r or bool(row["colada"])!=new_c:
                    update_fig(row["codigo"], new_t, new_r, new_c)
                    changed = True

    if changed:
        st.rerun()

# ════════════════════════════════════════════════════════════════════════════
# 🔁 REPETIDAS / TROCAS
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "🔁 Repetidas / Trocas":
    st.markdown('<div class="sec-title">FIGURINHAS REPETIDAS</div>', unsafe_allow_html=True)

    df_all = load_all()
    df_rep = df_all[df_all["repetidas"]>0].copy()

    if df_rep.empty:
        st.markdown('<div style="text-align:center;padding:40px;color:#7a8599;"><div style="font-size:3rem">🎉</div><div style="margin-top:8px;font-size:1.1rem">Nenhuma figurinha repetida cadastrada!</div></div>', unsafe_allow_html=True)
    else:
        tot_rep = int(df_rep["repetidas"].sum())
        qt_dif  = len(df_rep)

        st.markdown(f"""
        <div style="background:rgba(245,158,11,.08);border:1px solid rgba(245,158,11,.3);border-radius:12px;padding:14px 20px;margin-bottom:18px;display:flex;gap:30px;align-items:center;">
            <div style="text-align:center">
                <div style="font-family:'Bebas Neue';font-size:2.3rem;color:#f59e0b;line-height:1">{tot_rep}</div>
                <div style="color:#7a8599;font-size:.68rem;text-transform:uppercase">Total Repetidas</div>
            </div>
            <div style="text-align:center">
                <div style="font-family:'Bebas Neue';font-size:2.3rem;color:#FFD700;line-height:1">{qt_dif}</div>
                <div style="color:#7a8599;font-size:.68rem;text-transform:uppercase">Figurinhas Diferentes</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        for grupo, codes in GROUPS.items():
            df_g = df_rep[df_rep["pais_code"].isin(codes)]
            if df_g.empty: continue
            st.markdown(f"**{grupo}**")
            for pc in codes:
                df_p = df_g[df_g["pais_code"]==pc]
                if df_p.empty: continue
                badges = " ".join([f'<span class="br">{r["codigo"]} ({r["repetidas"]}x)</span>' for _,r in df_p.iterrows()])
                st.markdown(f"""
                <div style="display:flex;align-items:center;gap:10px;padding:7px 12px;background:rgba(255,255,255,.03);border-radius:8px;margin:3px 0;">
                    <span style="font-size:1.2rem">{FLAGS.get(pc,'')}</span>
                    <span style="color:#c8d0de;font-size:.87rem;font-weight:600;min-width:130px">{COUNTRIES.get(pc,pc)}</span>
                    <div style="flex:1;display:flex;flex-wrap:wrap;gap:4px">{badges}</div>
                </div>
                """, unsafe_allow_html=True)

        df_esp = df_rep[~df_rep["pais_code"].isin(COUNTRIES.keys())]
        if not df_esp.empty:
            st.markdown("**Especiais / Coca-Cola**")
            badges = " ".join([f'<span class="br">{r["codigo"]} ({r["repetidas"]}x)</span>' for _,r in df_esp.iterrows()])
            st.markdown(f'<div style="padding:7px 12px">{badges}</div>', unsafe_allow_html=True)

        st.markdown("---")
        st.markdown("#### 📋 Lista para troca (copie e envie)")
        lines = [f'{r["codigo"]}({r["repetidas"]}x)' for _,r in df_rep.sort_values("codigo").iterrows()]
        st.text_area("Repetidas:", "  |  ".join(lines), height=90)

        st.markdown("#### ❌ Figurinhas que FALTAM")
        df_falta = df_all[df_all["tenho"]==0]
        lines_f = list(df_falta["codigo"])
        st.text_area("Faltam:", "  |  ".join(lines_f), height=90)

# ════════════════════════════════════════════════════════════════════════════
# 🔍 BUSCAR
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "🔍 Buscar Figurinha":
    st.markdown('<div class="sec-title">BUSCAR FIGURINHA</div>', unsafe_allow_html=True)

    ca, cb = st.columns(2)
    with ca:
        busca_cod = st.text_input("🔢 Código (ex: BRA1, FWC5, CC3):", "").upper().strip()
    with cb:
        opts = ["Todas as seleções"] + [f"{FLAGS.get(c,'')} {COUNTRIES.get(c,c)} ({c})" for c in sorted(COUNTRIES.keys())]
        pais_fil = st.selectbox("🌍 Seleção:", opts)

    filtro = st.radio("Status:", ["Todas","✅ Tenho","❌ Faltam","🔁 Repetidas"], horizontal=True)

    df_all = load_all()
    df_f = df_all.copy()
    if busca_cod:
        df_f = df_f[df_f["codigo"].str.startswith(busca_cod)]
    if pais_fil != "Todas as seleções":
        pc = re.search(r'\((\w+)\)', pais_fil)
        if pc: df_f = df_f[df_f["pais_code"]==pc.group(1)]
    if filtro=="✅ Tenho":    df_f = df_f[df_f["tenho"]==1]
    elif filtro=="❌ Faltam": df_f = df_f[df_f["tenho"]==0]
    elif filtro=="🔁 Repetidas": df_f = df_f[df_f["repetidas"]>0]

    st.markdown(f"*{len(df_f)} figurinha(s)*")
    for _, row in df_f.iterrows():
        pc = row["pais_code"]
        badge = f'<span class="bt">✅ Tenho</span>' if row["tenho"] else f'<span class="bf">❌ Falta</span>'
        rep_b = f'<span class="br">🔁 {row["repetidas"]}x</span>' if row["repetidas"]>0 else ""
        pin_b = '<span style="color:#60a5fa;font-size:.73rem">📌</span>' if row["colada"] else ""
        st.markdown(f"""
        <div style="display:flex;align-items:center;gap:10px;padding:9px 14px;background:rgba(255,255,255,.03);border:1px solid rgba(255,255,255,.07);border-radius:9px;margin:3px 0;">
            <span style="font-size:1.2rem">{FLAGS.get(pc,'')}</span>
            <span class="code-b">{row['codigo']}</span>
            <span style="color:#c8d0de;font-size:.87rem;flex:1">{COUNTRIES.get(pc, row['secao'])}</span>
            {badge} {rep_b} {pin_b}
        </div>
        """, unsafe_allow_html=True)

# ════════════════════════════════════════════════════════════════════════════
# 📥 IMPORTAR / EXPORTAR
# ════════════════════════════════════════════════════════════════════════════
elif pagina == "📥 Importar / Exportar":
    st.markdown('<div class="sec-title">IMPORTAR / EXPORTAR</div>', unsafe_allow_html=True)

    tab1, tab2, tab3, tab4 = st.tabs(["📤 Exportar CSV","📥 Marcar por Código","🔁 Repetidas em Lote","🔄 Resetar"])

    with tab1:
        df_all = load_all()
        csv = df_all[["codigo","secao","grupo","pais_code","numero","tenho","repetidas","colada"]].to_csv(index=False).encode("utf-8")
        st.download_button("⬇️ Baixar CSV completo", data=csv, file_name="album_copa2026.csv", mime="text/csv")
        resumo = df_all.groupby("pais_code").agg(
            Seleção=("secao","first"), Total=("codigo","count"),
            Tenho=("tenho","sum"), Repetidas=("repetidas","sum")
        ).reset_index()
        resumo["Faltam"] = resumo["Total"]-resumo["Tenho"]
        resumo["%"] = (resumo["Tenho"]/resumo["Total"]*100).round(1)
        resumo = resumo.rename(columns={"pais_code":"Código"})
        st.dataframe(resumo[["Código","Seleção","Total","Tenho","Faltam","Repetidas","%"]], use_container_width=True, height=380)

    with tab2:
        st.markdown("""
**Cole os CÓDIGOS das figurinhas separados por vírgula, espaço ou linha:**

Exemplo: `BRA1, BRA3, FWC5, MEX10, CC2`
        """)
        inp = st.text_area("Códigos:", height=130, placeholder="BRA1, BRA2, ARG5, MEX10, FWC3...")
        modo = st.radio("Ação:", ["✅ Marcar como TENHO","❌ Desmarcar"], horizontal=True)
        if st.button("Aplicar", use_container_width=True):
            tokens = re.findall(r'[A-Za-z]+\d+', inp.upper())
            if tokens:
                conn = get_conn()
                ok = err = 0
                for t in tokens:
                    cur = conn.execute("SELECT codigo FROM figurinhas WHERE codigo=?", (t,))
                    if cur.fetchone():
                        conn.execute("UPDATE figurinhas SET tenho=? WHERE codigo=?", (1 if "TENHO" in modo else 0, t))
                        ok+=1
                    else: err+=1
                conn.commit(); conn.close()
                st.success(f"✅ {ok} figurinha(s) atualizada(s)!")
                if err: st.warning(f"⚠️ {err} código(s) não encontrado(s).")
                st.rerun()
            else:
                st.warning("Nenhum código válido encontrado.")

    with tab3:
        st.markdown("""
**Informe repetidas no formato `CÓDIGO:QUANTIDADE`:**

Exemplo: `BRA1:3, ARG5:2, FWC1:1, MEX10:4`
        """)
        inp_r = st.text_area("Repetidas:", height=120, placeholder="BRA1:3, ARG5:2, MEX10:1...")
        if st.button("Aplicar repetidas", use_container_width=True):
            pares = re.findall(r'([A-Za-z]+\d+):(\d+)', inp_r.upper())
            if pares:
                conn = get_conn()
                ok = err = 0
                for cod, qtd in pares:
                    if conn.execute("SELECT 1 FROM figurinhas WHERE codigo=?", (cod,)).fetchone():
                        conn.execute("UPDATE figurinhas SET tenho=1, repetidas=? WHERE codigo=?", (int(qtd), cod))
                        ok+=1
                    else: err+=1
                conn.commit(); conn.close()
                st.success(f"✅ {ok} repetida(s) atualizada(s)!")
                if err: st.warning(f"⚠️ {err} código(s) não encontrado(s).")
                st.rerun()
            else:
                st.warning("Use o formato CÓDIGO:QUANTIDADE (ex: BRA1:3)")

    with tab4:
        st.warning("⚠️ Isso apagará TODO o progresso do álbum!")
        conf = st.text_input("Digite RESETAR para confirmar:")
        if st.button("🔄 Resetar Álbum", use_container_width=True):
            if conf == "RESETAR":
                conn = get_conn()
                conn.execute("UPDATE figurinhas SET tenho=0, repetidas=0, colada=0")
                conn.commit(); conn.close()
                st.success("✅ Álbum resetado!"); st.rerun()
            else:
                st.error("Digite exatamente RESETAR para confirmar.")