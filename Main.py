import streamlit as st
import sqlite3
import pandas as pd
from datetime import date

# --- 1. CONFIGURAÇÃO E ESTILO ---
st.set_page_config(page_title="CheckPoint Shift 🏁", layout="wide")

st.markdown("""
<style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.8), rgba(0, 0, 0, 0.8)), 
                    url("https://images.unsplash.com/photo-1614850523296-d8c1af93d400?q=80&w=2070&auto=format&fit=crop");
        background-size: cover;
        background-attachment: fixed;
    }
    .stTabs [data-baseweb="tab"] { color: white !important; font-size: 20px !important; font-weight: bold; }
    [data-testid="stForm"], .st-expander, .stMetric, div[data-testid="stVerticalBlock"] > div {
        background-color: rgba(255, 255, 255, 0.07) !important;
        backdrop-filter: blur(15px);
        border: 1px solid rgba(255, 255, 255, 0.2);
        border-radius: 15px !important;
        padding: 20px;
    }
    .card-meta {
        padding: 30px; border-radius: 20px; text-align: center; margin: 20px 0; border: 3px solid;
    }
    .meta-sucesso { background-color: rgba(0, 255, 127, 0.2); border-color: #00FF7F; color: #00FF7F; }
    .meta-falta { background-color: rgba(255, 75, 75, 0.2); border-color: #FF4B4B; color: #FF4B4B; }
    .stButton>button {
        width: 100%; border-radius: 10px; font-weight: bold; font-size: 16px !important; height: 3.2em;
        background-color: rgba(255, 255, 255, 0.1) !important; color: white !important; border: 1px solid rgba(255, 255, 255, 0.4) !important;
    }
    .stButton>button:hover { background-color: white !important; color: black !important; }
    h1, h2, h3, h4, label, p, span { color: white !important; text-shadow: 1px 1px 2px #000; }
</style>
""", unsafe_allow_html=True)

def conectar():
    conn = sqlite3.connect("checkpoint_shift_mateus.db", check_same_thread=False)
    cursor = conn.cursor()
    # Adicionada coluna km_config para salvar o KM inicial da configuração e calcular o progresso real
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS veiculo (usuario TEXT PRIMARY KEY, km_ini REAL, km_alvo REAL, custo REAL, fipe REAL, guardado_ipva REAL, km_config REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS metas (id INTEGER PRIMARY KEY, usuario TEXT, item TEXT, valor REAL, data TEXT, guardado REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS ganhos (id INTEGER PRIMARY KEY, usuario TEXT, data TEXT, ganho REAL, gasto REAL, km REAL, h_ini TEXT, h_fim TEXT)")
    conn.commit()
    return conn, cursor

conn, cursor = conectar()

if "autenticado" not in st.session_state: st.session_state.autenticado = False

# --- 2. TELA DE ACESSO ---
if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align: center;'>🏁 CheckPoint Shift</h1>", unsafe_allow_html=True)
    aba_login, aba_cad = st.tabs(["🔑 ACESSAR", "📝 CRIAR CONTA"])
    with aba_login:
        u = st.text_input("Usuário", key="login_user").lower().strip()
        s = st.text_input("Senha", type="password", key="login_pass")
        if st.button("ENTRAR NO PAINEL"):
            if cursor.execute("SELECT * FROM usuarios WHERE usuario=? AND senha=?", (u, s)).fetchone():
                st.session_state.autenticado, st.session_state.user = True, u
                st.rerun()
            else: st.error("Usuário ou senha incorretos.")
    with aba_cad:
        nu = st.text_input("Definir Novo Usuário", key="cad_user").lower().strip()
        ns = st.text_input("Definir Senha", type="password", key="cad_pass")
        if st.button("CADASTRAR CONTA"):
            if nu and ns:
                try:
                    cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES (?,?)", (nu, ns))
                    conn.commit(); st.success("✅ Conta criada! Vá para Login.")
                except: st.error("❌ Este usuário já existe.")
    st.stop()

user = st.session_state.user
hoje = date.today()

# --- 3. VEÍCULO ---
v_data = cursor.execute("SELECT * FROM veiculo WHERE usuario=?", (user,)).fetchone()
if "editando_veiculo" not in st.session_state: st.session_state.editando_veiculo = False

if v_data is None or st.session_state.editando_veiculo:
    st.header("⚙️ Configuração do Veículo")
    with st.form("cfg_carro"):
        fipe_val = st.number_input("Valor FIPE do Carro", value=45000.0)
        km_atual_input = st.number_input("KM Atual do Painel", value=204650.0, step=1.0)
        prox_troca = st.number_input("KM da Próxima Troca de Óleo", value=km_atual_input + 5000, step=1.0)
        if st.form_submit_button("SALVAR CONFIGURAÇÃO"):
            # Salvamos o km_ini (atual) e também o km_config (referência inicial)
            cursor.execute("INSERT OR REPLACE INTO veiculo (usuario, km_ini, km_alvo, custo, fipe, guardado_ipva, km_config) VALUES (?,?,?,?,?,?,?)", 
                           (user, int(km_atual_input), int(prox_troca), 350.0, fipe_val, 0.0 if v_data is None else v_data[5], int(km_atual_input)))
            conn.commit(); st.session_state.editando_veiculo = False; st.rerun()
    st.stop()

km_atual_bd = int(v_data[1])
km_alvo_revisao = int(v_data[2])
km_inicial_config = int(v_data[6]) if len(v_data) > 6 else km_atual_bd

# --- 4. PAINEL PRINCIPAL ---
st.title(f"🚀 PAINEL: {user.upper()}")
tab_resumo, tab_ganhos, tab_caixinhas = st.tabs(["📊 RESUMO & MANUTENÇÃO", "💰 GANHOS & METAS", "🎯 CAIXINHAS"])

with tab_resumo:
    fipe, guardado_ipva = v_data[4], v_data[5]
    total_ipva = fipe * 0.04
    
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💰 Fundo IPVA")
        st.metric("Falta Guardar", f"R$ {total_ipva - guardado_ipva:.2f}", f"Total: R$ {total_ipva:.2f}")
        val_ipva = st.number_input("Valor Operação IPVA (R$):", value=0.0)
        if st.button("📥 DEPOSITAR"):
            cursor.execute("UPDATE veiculo SET guardado_ipva = guardado_ipva + ? WHERE usuario=?", (val_ipva, user))
            conn.commit(); st.rerun()

    with col2:
        st.subheader("🔧 Revisão (Troca de Óleo)")
        km_restante = km_alvo_revisao - km_atual_bd
        intervalo_total = km_alvo_revisao - km_inicial_config
        
        # Cálculo de progresso real
        if intervalo_total > 0:
            progresso_km = max(0.0, min(1.0, (km_atual_bd - km_inicial_config) / intervalo_total))
        else:
            progresso_km = 1.0
        
        st.metric("KM Atual do Carro", f"{km_atual_bd} km")
        st.write(f"Próxima troca em: **{km_alvo_revisao} km**")
        st.progress(progresso_km)
        
        if km_restante <= 0:
            st.error(f"🚨 REVISÃO VENCIDA! Passou {abs(km_restante)} km")
        elif km_restante <= 1000:
            st.warning(f"⚠️ ALERTA: Falta apenas {km_restante} km para a troca!")
        else:
            st.info(f"Tudo certo. Faltam {km_restante} km.")

with tab_ganhos:
    meta_diaria = st.number_input("Sua Meta Diária (R$):", value=400.0)
    with st.form("ganho_diario", clear_on_submit=True):
        st.subheader("Registrar Trabalho")
        g1, g2, g3 = st.columns(3)
        v_bruto = g1.number_input("Ganhos Brutos (R$)")
        v_gastos = g2.number_input("Total Gastos (R$)")
        v_km_rodada = g3.number_input("KM Rodada Hoje", step=1.0)
        if st.form_submit_button("💾 SALVAR DIA E ATUALIZAR KM"):
            cursor.execute("INSERT INTO ganhos (usuario, data, ganho, gasto, km, h_ini, h_fim) VALUES (?,?,?,?,?,?,?)", 
                           (user, str(hoje), v_bruto, v_gastos, int(v_km_rodada), "00:00", "00:00"))
            cursor.execute("UPDATE veiculo SET km_ini = km_ini + ? WHERE usuario=?", (int(v_km_rodada), user))
            conn.commit(); st.rerun()

    df_h = pd.read_sql_query(f"SELECT * FROM ganhos WHERE usuario='{user}'", conn)
    if not df_h.empty:
        lucro_total = df_h['ganho'].sum() - df_h['gasto'].sum()
        meta_total = len(df_h) * meta_diaria
        if lucro_total >= meta_total:
            excedente = lucro_total - meta_total
            st.markdown(f'<div class="card-meta meta-sucesso"><h1>META ATINGIDA! 🎯</h1><p style="font-size: 50px; font-weight: bold;">R$ {lucro_total:.2f}</p><p>🚀 Parabéns! Extra de <b>R$ {excedente:.2f}</b>!</p></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="card-meta meta-falta"><h1>DÉFICIT ⚠️</h1><p style="font-size: 50px; font-weight: bold;">R$ {lucro_total:.2f}</p><p>Faltam <b>R$ {meta_total - lucro_total:.2f}</b>.</p></div>', unsafe_allow_html=True)

with tab_caixinhas:
    st.subheader("🎯 Suas Caixinhas")
    m_db = pd.read_sql_query(f"SELECT * FROM metas WHERE usuario='{user}'", conn)
    for i, m in m_db.iterrows():
        with st.container():
            st.write(f"### 🚀 {m['item']}")
            st.write(f"**💰 Guardado: R$ {m['guardado']:.2f}** de **R$ {m['valor']:.2f}**")
            st.progress(min(m['guardado']/m['valor'], 1.0) if m['valor'] > 0 else 0)
            v_m = st.number_input("Valor:", key=f"v_{m['id']}", value=0.0)
            if st.button("📥 Guardar", key=f"in_{m['id']}"):
                cursor.execute("UPDATE metas SET guardado = guardado + ? WHERE id=?", (v_m, m['id'])); conn.commit(); st.rerun()

# --- SIDEBAR ---
st.sidebar.title("⚙️ OPÇÕES")
if st.sidebar.button("🚗 RECONFIGURAR CARRO/KM"):
    st.session_state.editando_veiculo = True; st.rerun()
if st.sidebar.button("🚪 SAIR DO APP"):
    st.session_state.autenticado = False; st.rerun()
