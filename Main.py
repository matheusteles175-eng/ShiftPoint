import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="CheckPoint Shift 🏁", layout="wide")

# --- 2. ESTILO VISUAL ---
def aplicar_estilo():
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), 
                    url("https://images.unsplash.com/photo-1614850523296-d8c1af93d400?q=80&w=2070&auto=format&fit=crop");
        background-size: cover;
        background-attachment: fixed;
    }
    [data-testid="stForm"], .st-expander, .stMetric, .stTabs, div[data-testid="stVerticalBlock"] > div {
        background-color: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px !important;
        padding: 20px;
    }
    h1, h2, h3, h4, span, label, p, .stMetric div { color: #ffffff !important; }
    .stButton>button { width: 100%; border-radius: 10px; background-color: #28a745; color: white; font-weight: bold; }
    </style>
    """, unsafe_allow_html=True)

aplicar_estilo()

# --- 3. BANCO DE DADOS ---
def conectar():
    conn = sqlite3.connect("checkpoint_v2_final.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS veiculo (usuario TEXT PRIMARY KEY, fipe REAL, guardado_ipva REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS ganhos (id INTEGER PRIMARY KEY, usuario TEXT, data TEXT, ganho REAL, gasto REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS metas (id INTEGER PRIMARY KEY, usuario TEXT, item TEXT, valor REAL, guardado REAL)")
    conn.commit()
    return conn, cursor

conn, cursor = conectar()

# --- 4. ACESSO ---
if "autenticado" not in st.session_state: 
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align: center;'>🏁 CheckPoint Shift</h1>", unsafe_allow_html=True)
    aba_login, aba_cadastro = st.tabs(["🔑 Entrar", "📝 Criar Nova Conta"])
    
    with aba_login:
        u = st.text_input("Seu Usuário", key="login_u").lower().strip()
        s = st.text_input("Sua Senha", type="password", key="login_s")
        if st.button("ACESSAR PAINEL"):
            user_db = cursor.execute("SELECT * FROM usuarios WHERE usuario=? AND senha=?", (u, s)).fetchone()
            if user_db:
                st.session_state.autenticado = True
                st.session_state.user = u
                st.rerun()
            else:
                st.error("Usuário ou senha incorretos.")
                
    with aba_cadastro:
        nu = st.text_input("Escolha um Usuário", key="cad_u").lower().strip()
        ns = st.text_input("Escolha uma Senha", type="password", key="cad_s")
        cs = st.text_input("Confirme a Senha", type="password", key="cad_s_conf")
        if st.button("FINALIZAR CADASTRO"):
            if nu and ns == cs:
                try:
                    cursor.execute("INSERT INTO usuarios VALUES (?,?)", (nu, ns))
                    conn.commit()
                    st.success("Conta criada! Vá em 'Entrar'.")
                except: st.error("Usuário já existe.")
    st.stop()

# --- 5. LOGADO ---
user = st.session_state.user
tab1, tab2, tab3 = st.tabs(["💰 GANHOS", "⚙️ IPVA", "🎯 CAIXINHAS"])

with tab1:
    with st.form("f_ganhos"):
        g = st.number_input("Ganho Bruto hoje", min_value=0.0)
        gst = st.number_input("Gasto hoje", min_value=0.0)
        if st.form_submit_button("GRAVAR CHECKPOINT"):
            cursor.execute("INSERT INTO ganhos (usuario, data, ganho, gasto) VALUES (?,?,?,?)", 
                           (user, str(date.today()), g, gst))
            conn.commit()
            st.rerun()
    
    # Correção na query de histórico
    df = pd.read_sql_query("SELECT data, ganho, gasto FROM ganhos WHERE usuario=? ORDER BY id DESC", conn, params=(user,))
    if not df.empty:
        st.dataframe(df, use_container_width=True)

with tab2:
    v_data = cursor.execute("SELECT * FROM veiculo WHERE usuario=?", (user,)).fetchone()
    if not v_data:
        f = st.number_input("Valor FIPE", value=45000.0)
        if st.button("Salvar Veículo"):
            cursor.execute("INSERT INTO veiculo VALUES (?,?,?)", (user, f, 0.0))
            conn.commit()
            st.rerun
