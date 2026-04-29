import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime

# --- 1. CONFIGURAÇÃO ---
st.set_page_config(page_title="CheckPoint Shift 🏁", layout="wide")

# --- 2. VISUAL FIXO (SEM CARREGAR ARQUIVO LOCAL) ---
def aplicar_estilo_fixo():
    # Aqui usamos um link de imagem profissional (textura escura/carbono)
    # E um efeito de "vidro" nos cartões
    st.markdown("""
    <style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.6), rgba(0, 0, 0, 0.6)), 
                    url("https://images.unsplash.com/photo-1618005182384-a83a8bd57fbe?q=80&w=1964&auto=format&fit=crop");
        background-size: cover;
        background-attachment: fixed;
    }
    
    /* Estilo dos blocos (Efeito Vidro) */
    [data-testid="stForm"], .st-expander, .stMetric, .stMarkdown div[style*="background-color"] {
        background-color: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px !important;
        color: white !important;
    }

    /* Ajuste de cor dos textos para o fundo escuro */
    h1, h2, h3, p, label, .stMetric div {
        color: #ffffff !important;
    }
    
    .stButton>button {
        border-radius: 10px;
        background-color: #28a745;
        color: white;
        border: none;
    }
    </style>
    """, unsafe_allow_html=True)

aplicar_estilo_fixo()

# --- 3. BANCO DE DADOS ---
def conectar():
    conn = sqlite3.connect("checkpoint_shift_final.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS veiculo (usuario TEXT PRIMARY KEY, fipe REAL, guardado_ipva REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS ganhos (id INTEGER PRIMARY KEY, usuario TEXT, data TEXT, ganho REAL, gasto REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS metas (id INTEGER PRIMARY KEY, usuario TEXT, item TEXT, valor REAL, guardado REAL)")
    conn.commit()
    return conn, cursor

conn, cursor = conectar()

# --- 4. LOGIN SIMPLIFICADO ---
if "autenticado" not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🏁 CheckPoint Shift")
    with st.container():
        u = st.text_input("Usuário").lower().strip()
        s = st.text_input("Senha", type="password")
        if st.button("Acessar Painel"):
            if u == "mateus" and s == "123": # Altere aqui seu login
                st.session_state.autenticado, st.session_state.user = True, u
                st.rerun()
            else: st.error("Acesso Negado")
    st.stop()

user = st.session_state.user

# --- 5. INTERFACE ---
st.title(f"🚀 CHECKPOINT: {user.upper()}")

tab1, tab2, tab3 = st.tabs(["💰 GANHOS", "⚙️ IPVA", "🎯 CAIXINHAS"])

with tab1:
    with st.form("ganho"):
        g = st.number_input("Quanto faturou hoje?", min_value=0.0)
        gst = st.number_input("Quanto gastou (Combustível)?", min_value=0.0)
        if st.form_submit_button("SALVAR JORNADA"):
            cursor.execute("INSERT INTO ganhos (usuario, data, ganho, gasto) VALUES (?,?,?,?)", 
                           (user, str(date.today()), g, gst))
            conn.commit()
            st.success("Checkpoint registrado!")
            st.rerun()

    # Histórico Rápido
    st.subheader("Histórico")
    df = pd.read_sql_query(f"SELECT * FROM ganhos WHERE usuario='{user}' ORDER BY id DESC LIMIT 5", conn)
    st.dataframe(df)

with tab2:
    # Lógica do IPVA (Simplificada e robusta)
    v_data = cursor.execute("SELECT * FROM veiculo WHERE usuario=?", (user,)).fetchone()
    if not v_data:
        f = st.number_input("Valor FIPE do Carro", value=40000.0)
        if st.button("Configurar Carro"):
            cursor.execute("INSERT INTO veiculo VALUES (?,?,?)", (user, f, 0.0))
            conn.commit(); st.rerun()
    else:
        fipe, guardado = v_data[1], v_data[2]
        total_ipva = fipe * 0.04
        st.metric("Total IPVA", f"R$ {total_ipva:.2f}")
        st.metric("Já Guardado", f"R$ {guardado:.2f}", delta=f"Falta: {total_ipva-guardado:.2f}")
        
        val = st.number_input("Valor para movimentar", value=0.0)
        c1, c2 = st.columns(2)
        if c1.button("📥 Depositar"):
            cursor.execute("UPDATE veiculo SET guardado_ipva = guardado_ipva + ? WHERE usuario=?", (val, user))
            conn.commit(); st.rerun()
        if c2.button("📤 Retirar"):
            cursor.execute("UPDATE veiculo SET guardado_ipva = guardado_ipva - ? WHERE usuario=?", (val, user))
            conn.commit(); st.rerun()

with tab3:
    # Caixinhas de Sonhos
    with st.expander("Nova Caixinha"):
        nome = st.text_input("Nome do Sonho")
        meta = st.number_input("Valor Alvo")
        if st.button("Criar"):
            cursor.execute("INSERT INTO metas (usuario, item, valor, guardado) VALUES (?,?,?,?)", (user, nome, meta, 0.0))
            conn.commit(); st.rerun()
            
    metas = pd.read_sql_query(f"SELECT * FROM metas WHERE usuario='{user}'", conn)
    for i, m in metas.iterrows():
        st.write(f"### {m['item']}")
        st.progress(min(m['guardado']/m['valor'], 1.0) if m['valor'] > 0 else 0)
        st.write(f"R$ {m['guardado']} de R$ {m['valor']}")
        if st.button("🗑️ Apagar", key=f"del_{i}"):
            cursor.execute("DELETE FROM metas WHERE id=?", (m['id'],))
            conn.commit(); st.rerun()
