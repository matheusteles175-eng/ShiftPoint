import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="CheckPoint Shift 🏁", layout="wide")

# --- 2. ESTILO VISUAL GLOBAL (Login e Interno) ---
def aplicar_estilo():
    st.markdown("""
    <style>
    /* Imagem de Fundo Fixa em todas as telas */
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.7), rgba(0, 0, 0, 0.7)), 
                    url("https://images.unsplash.com/photo-1614850523296-d8c1af93d400?q=80&w=2070&auto=format&fit=crop");
        background-size: cover;
        background-attachment: fixed;
    }
    
    /* Efeito de Vidro nos Containers */
    [data-testid="stForm"], .st-expander, .stMetric, .stTabs, div[data-testid="stVerticalBlock"] > div {
        background-color: rgba(255, 255, 255, 0.05) !important;
        backdrop-filter: blur(10px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 15px !important;
        padding: 20px;
    }

    /* Cores de Texto */
    h1, h2, h3, h4, span, label, p, .stMetric div {
        color: #ffffff !important;
    }
    
    /* Botões */
    .stButton>button {
        width: 100%;
        border-radius: 10px;
        background-color: #28a745;
        color: white;
        font-weight: bold;
    }
    </style>
    """, unsafe_allow_html=True)

aplicar_estilo()

# --- 3. BANCO DE DADOS ---
def conectar():
    # Usei um nome de banco novo para evitar conflitos de colunas antigas
    conn = sqlite3.connect("checkpoint_v2_final.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS veiculo (usuario TEXT PRIMARY KEY, fipe REAL, guardado_ipva REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS ganhos (id INTEGER PRIMARY KEY, usuario TEXT, data TEXT, ganho REAL, gasto REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS metas (id INTEGER PRIMARY KEY, usuario TEXT, item TEXT, valor REAL, guardado REAL)")
    conn.commit()
    return conn, cursor

conn, cursor = conectar()

# --- 4. SISTEMA DE ACESSO (LOGIN E CADASTRO) ---
if "autenticado" not in st.session_state: 
    st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align: center;'>🏁 CheckPoint Shift</h1>", unsafe_allow_html=True)
    
    # Abas de Login e Cadastro bem claras
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
                st.error("Usuário ou senha não encontrados.")
                
    with aba_cadastro:
        st.subheader("Cadastre-se para começar")
        nu = st.text_input("Escolha um Usuário", key="cad_u").lower().strip()
        ns = st.text_input("Escolha uma Senha", type="password", key="cad_s")
        confirm_s = st.text_input("Confirme a Senha", type="password", key="cad_s_conf")
        
        if st.button("FINALIZAR CADASTRO"):
            if nu and ns == confirm_s:
                try:
                    cursor.execute("INSERT INTO usuarios VALUES (?,?)", (nu, ns))
                    conn.commit()
                    st.success("Conta criada com sucesso! Agora vá na aba 'Entrar'.")
                except:
                    st.error("Este nome de usuário já está em uso.")
            else:
                st.warning("As senhas não coincidem ou campos estão vazios.")
    st.stop()

# --- 5. APP LOGADO ---
user = st.session_state.user
st.markdown(f"## 🚀 Bem-vindo, {user.upper()}")

tab1, tab2, tab3 = st.tabs(["💰 GANHOS", "⚙️ IPVA", "🎯 CAIXINHAS"])

# --- Lógica de Ganhos ---
with tab1:
    with st.form("f_ganhos"):
        g = st.number_input("Ganho Bruto hoje", min_value=0.0)
        gst = st.number_input("Gasto hoje", min_value=0.0)
        if st.form_submit_button("GRAVAR CHECKPOINT"):
            cursor.execute("INSERT INTO ganhos (usuario, data, ganho, gasto) VALUES (?,?,?,?)", 
                           (user, str(date.today()), g, gst))
            conn.commit()
            st.rerun()
    
    df = pd.read_sql_query(f"SELECT data, ganho, gasto FROM ganhos WHERE usuario='{user}' ORDER BY id DESC", conn)
    if not df.empty:
        st.subheader("Histórico Recente")
        st.dataframe(df, use_container_width=True)

# --- Lógica de IPVA ---
with tab2:
    v_data = cursor.execute("SELECT * FROM veiculo WHERE usuario=?", (user,)).fetchone()
    if not v_data:
        st.info("Configure seu carro para calcular o IPVA.")
        f = st.number_input("Valor FIPE", value=45000.0)
        if st.button("Salvar Veículo"):
            cursor.execute("INSERT INTO veiculo VALUES (?,?,?)", (user, f, 0.0))
            conn.commit(); st.rerun()
    else:
        fipe, guardado = v_data[1], v_data[2]
        total_ipva = fipe * 0.04
        c1, c2 = st.columns(2)
        c1.metric("IPVA Estimado", f"R$ {total_ipva:.2f}")
        c2.metric("Guardado", f"R$ {guardado:.2f}")
        
        val = st.number_input("Valor da Operação", value=0.0)
        b1, b2 = st.columns(2)
        if b1.button("📥 Depositar"):
            cursor.execute("UPDATE veiculo SET guardado_ipva = guardado_ipva + ? WHERE usuario=?", (val, user))
            conn.commit(); st.rerun()
        if b2.button("📤 Retirar"):
            cursor.execute("UPDATE veiculo SET guardado_ipva = guardado_ipva - ? WHERE usuario=?", (val, user))
            conn.commit(); st.rerun()

# --- Lógica de Caixinhas ---
with tab3:
    with st.expander("➕ Novo Objetivo"):
        nome = st.text_input("Qual o seu sonho?")
        meta = st.number_input("Quanto custa?")
        if st.button("Lançar"):
            cursor.execute("INSERT INTO metas (usuario, item, valor, guardado) VALUES (?,?,?,?)", (user, nome, meta, 0.0))
            conn.commit(); st.rerun()
            
    metas = pd.read_sql_query(f"SELECT * FROM metas WHERE usuario='{user}'", conn)
    for i, m in metas.iterrows():
        with st.container():
            st.write(f"### {m['item']}")
            st.progress(min(m['guardado']/m['valor'], 1.0) if m['valor'] > 0 else 0)
            st.write(f"R$ {m['guardado']} de R$ {m['valor']}")
            if st.button("🗑️ Excluir", key=f"del_{i}"):
                cursor.execute("DELETE FROM metas WHERE id=?", (m['id'],))
                conn.commit(); st.rerun()

if st.sidebar.button("Sair"):
    st.session_state.autenticado = False
    st.rerun()
