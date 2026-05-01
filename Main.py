import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="CheckPoint Ganhos 💰", layout="wide")

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.85), rgba(0, 0, 0, 0.85)), 
                    url("https://images.unsplash.com/photo-1554224155-6726b3ff858f?q=80&w=2011&auto=format&fit=crop");
        background-size: cover;
        background-attachment: fixed;
    }
    .stTabs [data-baseweb="tab"] { color: white !important; font-size: 20px !important; font-weight: bold; }
    [data-testid="stForm"], div[data-testid="stVerticalBlock"] > div {
        background-color: rgba(255, 255, 255, 0.07) !important;
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 15px !important;
        padding: 20px;
    }
    .card-meta { padding: 30px; border-radius: 20px; text-align: center; margin: 20px 0; border: 3px solid; }
    .meta-sucesso { background-color: rgba(0, 255, 127, 0.2); border-color: #00FF7F; color: #00FF7F; }
    .meta-falta { background-color: rgba(255, 75, 75, 0.2); border-color: #FF4B4B; color: #FF4B4B; }
    .stButton>button {
        width: 100%; border-radius: 10px; font-weight: bold; background-color: rgba(255, 255, 255, 0.1) !important; 
        color: white !important; border: 1px solid rgba(255, 255, 255, 0.4) !important;
    }
    .stButton>button:hover { background-color: white !important; color: black !important; }
    h1, h2, h3, h4, label, p, span { color: white !important; text-shadow: 1px 1px 2px #000; }
</style>
""", unsafe_allow_html=True)

def conectar():
    conn = sqlite3.connect("ganhos_shift.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS ganhos (id INTEGER PRIMARY KEY, usuario TEXT, data TEXT, ganho REAL, gasto REAL, km REAL, h_ini TEXT, h_fim TEXT)")
    conn.commit()
    return conn, cursor

conn, cursor = conectar()

if "autenticado" not in st.session_state: st.session_state.autenticado = False

# --- TELA DE ACESSO ---
if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align: center;'>💰 CheckPoint Ganhos</h1>", unsafe_allow_html=True)
    aba_login, aba_cad = st.tabs(["🔑 ACESSAR", "📝 CRIAR CONTA"])
    with aba_login:
        u = st.text_input("Usuário", key="login_user").lower().strip()
        s = st.text_input("Senha", type="password", key="login_pass")
        if st.button("ENTRAR NO PAINEL"):
            if cursor.execute("SELECT * FROM usuarios WHERE usuario=? AND senha=?", (u, s)).fetchone():
                st.session_state.autenticado, st.session_state.user = True, u
                st.rerun()
            else: st.error("Acesso negado.")
    with aba_cad:
        nu = st.text_input("Def Novo Usuário", key="cad_user").lower().strip()
        ns = st.text_input("Def Senha", type="password", key="cad_pass")
        if st.button("CADASTRAR MINHA CONTA"):
            if nu and ns:
                try:
                    cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES (?,?)", (nu, ns))
                    conn.commit(); st.success("✅ Conta criada!")
                except: st.error("❌ Usuário já existe.")
    st.stop()

user = st.session_state.user
hoje = date.today()

# --- DASHBOARD DE GANHOS ---
st.title(f"🚀 PERFORMANCE: {user.upper()}")

# Configuração da Meta Diária fixa ou variável
meta_dia = st.sidebar.number_input("Sua Meta Diária (R$)", value=400.0)

# Registro de Trabalho
with st.form("job"):
    st.subheader("📝 Registrar Turno de Hoje")
    g1, g2, g3 = st.columns(3)
    v_bruto = g1.number_input("Ganho Bruto (R$)", min_value=0.0)
    v_gasto = g2.number_input("Gasto Combustível/Alimentação (R$)", min_value=0.0)
    v_km = g3.number_input("KM Rodada no Dia", step=1.0)
    
    t1, t2 = st.columns(2)
    h_ini = t1.text_input("Horário Início", value="08:00")
    h_fim = t2.text_input("Horário Fim", value="18:00")
    
    if st.form_submit_button("SALVAR RESULTADOS"):
        cursor.execute("INSERT INTO ganhos (usuario, data, ganho, gasto, km, h_ini, h_fim) VALUES (?,?,?,?,?,?,?)", 
                       (user, str(hoje), v_bruto, v_gasto, int(v_km), h_ini, h_fim))
        conn.commit(); st.rerun()

# --- RELATÓRIOS ---
df_g = pd.read_sql_query(f"SELECT * FROM ganhos WHERE usuario='{user}'", conn)

if not df_g.empty:
    lucro_total = df_g['ganho'].sum() - df_g['gasto'].sum()
    meta_acumulada = len(df_g) * meta_dia
    
    # Card de Status da Meta
    if lucro_total >= meta_acumulada:
        diferenca = lucro_total - meta_acumulada
        st.markdown(f'<div class="card-meta meta-sucesso"><h1>META SUPERADA! 🎯</h1><p style="font-size:40px; font-weight:bold;">Lucro Total: R$ {lucro_total:.2f}</p><p style="font-size:20px;">Você está <b>ACIMA</b> da meta em: <b>R$ {diferenca:.2f}</b></p></div>', unsafe_allow_html=True)
    else:
        diferenca = meta_acumulada - lucro_total
        st.markdown(f'<div class="card-meta meta-falta"><h1>DÉFICIT ACUMULADO ⚠️</h1><p style="font-size:40px; font-weight:bold;">Lucro Total: R$ {lucro_total:.2f}</p><p style="font-size:20px;">Faltam <b>R$ {diferenca:.2f}</b> para atingir o objetivo.</p></div>', unsafe_allow_html=True)

    st.subheader("📜 Histórico de Ganhos")
    for _, r in df_g.sort_values(by='id', ascending=False).iterrows():
        lucro_dia = r['ganho'] - r['gasto']
        try:
            fmt = '%H:%M'
            tdiff = datetime.strptime(r['h_fim'], fmt) - datetime.strptime(r['h_ini'], fmt)
            horas_trab = tdiff.total_seconds() / 3600
        except: horas_trab = 0
        
        # Indicadores de Performance
        r_km = r['ganho'] / r['km'] if r['km'] > 0 else 0
        r_h = r['ganho'] / horas_trab if horas_trab > 0 else 0
        
        with st.expander(f"📅 {r['data']} | Lucro Líquido: R$ {lucro_dia:.2f}"):
            c1, c2, c3, c4 = st.columns(4)
            c1.metric("Bruto", f"R$ {r['ganho']:.2f}")
            c2.metric("Km Rodado", f"{int(r['km'])} km")
            c3.metric("R$ / KM", f"R$ {r_km:.2f}")
            c4.metric("R$ / Hora", f"R$ {r_h:.2f}")
            
            if st.button("🗑️ EXCLUIR REGISTRO", key=f"del_{r['id']}"):
                cursor.execute("DELETE FROM ganhos WHERE id=?", (r['id'],))
                conn.commit(); st.rerun()
else:
    st.info("Nenhum registro encontrado. Comece a rodar e registre seus ganhos!")

# --- BARRA LATERAL ---
st.sidebar.markdown("---")
if st.sidebar.button("⚠️ ZERAR TODOS OS MEUS GANHOS"):
    cursor.execute("DELETE FROM ganhos WHERE usuario=?", (user,))
    conn.commit(); st.rerun()
if st.sidebar.button("🚪 SAIR"):
    st.session_state.autenticado = False
    st.rerun()
