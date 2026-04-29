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
    .card-meta { padding: 30px; border-radius: 20px; text-align: center; margin: 20px 0; border: 3px solid; }
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
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS veiculo (usuario TEXT PRIMARY KEY, km_ini REAL, km_alvo REAL, custo REAL, fipe REAL, guardado_ipva REAL, km_config REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS metas (id INTEGER PRIMARY KEY, usuario TEXT, item TEXT, valor REAL, data TEXT, guardado REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS ganhos (id INTEGER PRIMARY KEY, usuario TEXT, data TEXT, ganho REAL, gasto REAL, km REAL, h_ini TEXT, h_fim TEXT)")
    conn.commit()
    return conn, cursor

conn, cursor = conectar()

if "autenticado" not in st.session_state: st.session_state.autenticado = False

# --- LOGIN ---
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
            else: st.error("Acesso negado.")
    with aba_cad:
        nu = st.text_input("Novo Usuário", key="cad_user").lower().strip()
        ns = st.text_input("Senha", type="password", key="cad_pass")
        if st.button("CADASTRAR"):
            try:
                cursor.execute("INSERT INTO usuarios (usuario, senha) VALUES (?,?)", (nu, ns))
                conn.commit(); st.success("✅ Conta criada!")
            except: st.error("❌ Usuário já existe.")
    st.stop()

user = st.session_state.user
hoje = date.today()

# --- CONFIGURAÇÃO DO VEÍCULO ---
v_data = cursor.execute("SELECT * FROM veiculo WHERE usuario=?", (user,)).fetchone()
if "editando_veiculo" not in st.session_state: st.session_state.editando_veiculo = False

if v_data is None or st.session_state.editando_veiculo:
    with st.form("cfg_veiculo"):
        st.header("⚙️ Configuração do Veículo")
        fipe_val = st.number_input("Valor FIPE do Carro", value=v_data[4] if v_data else 45000.0)
        km_at = st.number_input("KM Atual do Painel", value=v_data[1] if v_data else 204000.0)
        km_tr = st.number_input("KM da Próxima Troca", value=v_data[2] if v_data else 214000.0)
        if st.form_submit_button("SALVAR CONFIGURAÇÃO"):
            cursor.execute("INSERT OR REPLACE INTO veiculo VALUES (?,?,?,?,?,?,?)", 
                           (user, km_at, km_tr, 350.0, fipe_val, v_data[5] if v_data else 0.0, km_at))
            conn.commit(); st.session_state.editando_veiculo = False; st.rerun()
    st.stop()

km_atual_bd = int(v_data[1])
km_alvo_revisao = int(v_data[2])
km_inicial_config = int(v_data[6])

# --- DASHBOARD PRINCIPAL ---
st.title(f"🚀 PAINEL: {user.upper()}")
tab_resumo, tab_ganhos, tab_caixinhas = st.tabs(["📊 MANUTENÇÃO", "💰 GANHOS & RELATÓRIOS", "🎯 CAIXINHA DOS SONHOS"])

with tab_resumo:
    fipe, guardado_ipva = v_data[4], v_data[5]
    total_ipva = fipe * 0.04
    col1, col2 = st.columns(2)
    with col1:
        st.subheader("💰 Fundo IPVA")
        st.metric("Falta Guardar", f"R$ {total_ipva - guardado_ipva:.2f}")
        v_ipva = st.number_input("Depositar R$:", key="ipva_in")
        if st.button("CONFIRMAR DEPÓSITO IPVA"):
            cursor.execute("UPDATE veiculo SET guardado_ipva = guardado_ipva + ? WHERE usuario=?", (v_ipva, user))
            conn.commit(); st.rerun()
    with col2:
        st.subheader("🔧 Revisão de Óleo")
        km_falta = km_alvo_revisao - km_atual_bd
        total_ciclo = km_alvo_revisao - km_inicial_config
        prog = max(0.0, min(1.0, (km_atual_bd - km_inicial_config) / total_ciclo)) if total_ciclo > 0 else 1.0
        st.metric("KM Atual", f"{km_atual_bd} km")
        st.progress(prog)
        if km_falta <= 0: st.error(f"🚨 VENCIDO HÁ {abs(km_falta)} KM!")
        elif km_falta <= 1000: st.warning(f"⚠️ ATENÇÃO: Faltam {km_falta} km")
        else: st.info(f"Tudo ok. Faltam {km_falta} km.")

with tab_ganhos:
    meta_dia = st.number_input("Meta Diária (R$)", value=400.0)
    with st.form("job"):
        st.subheader("Registrar Trabalho de Hoje")
        g1, g2, g3 = st.columns(3)
        v_bruto = g1.number_input("Ganho Bruto")
        v_gasto = g2.number_input("Gasto (Combustível/Alimentação)")
        v_km = g3.number_input("KM Rodada Hoje", step=1.0)
        h_ini = st.text_input("Início Trabalho", value="08:00")
        h_fim = st.text_input("Fim Trabalho", value="18:00")
        if st.form_submit_button("SALVAR DIA"):
            cursor.execute("INSERT INTO ganhos (usuario, data, ganho, gasto, km, h_ini, h_fim) VALUES (?,?,?,?,?,?,?)", 
                           (user, str(hoje), v_bruto, v_gasto, int(v_km), h_ini, h_fim))
            cursor.execute("UPDATE veiculo SET km_ini = km_ini + ? WHERE usuario=?", (int(v_km), user))
            conn.commit(); st.rerun()

    df_g = pd.read_sql_query(f"SELECT * FROM ganhos WHERE usuario='{user}'", conn)
    if not df_g.empty:
        lucro_total = df_g['ganho'].sum() - df_g['gasto'].sum()
        meta_acumulada = len(df_g) * meta_dia
        if lucro_total >= meta_acumulada:
            st.markdown(f'<div class="card-meta meta-sucesso"><h1>META ATINGIDA! 🎯</h1><p style="font-size:40px;">R$ {lucro_total:.2f}</p><p>Saldo Positivo: R$ {lucro_total - meta_acumulada:.2f}</p></div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="card-meta meta-falta"><h1>DÉFICIT ACUMULADO ⚠️</h1><p style="font-size:40px;">R$ {lucro_total:.2f}</p><p>Faltam R$ {meta_acumulada - lucro_total:.2f} para a meta total.</p></div>', unsafe_allow_html=True)

    st.subheader("📜 Histórico e Relatórios")
    for _, r in df_g.sort_values(by='id', ascending=False).iterrows():
        with st.expander(f"📅 {r['data']} | Lucro: R$ {r['ganho']-r['gasto']:.2f}"):
            st.write(f"⏱ **Horário:** {r['h_ini']} - {r['h_fim']} | 🚗 **KM Rodada:** {int(r['km'])} km")
            st.write(f"💰 Bruto: R$ {r['ganho']:.2f} | ⛽ Gasto: R$ {r['gasto']:.2f}")
            if st.button("🗑️ EXCLUIR", key=f"del_{r['id']}"):
                cursor.execute("UPDATE veiculo SET km_ini = km_ini - ? WHERE usuario=?", (r['km'], user))
                cursor.execute("DELETE FROM ganhos WHERE id=?", (r['id'],))
                conn.commit(); st.rerun()

with tab_caixinhas:
    st.subheader("🎯 Suas Metas e Sonhos")
    with st.expander("➕ ADICIONAR NOVO OBJETIVO"):
        with st.form("meta_new"):
            n_m = st.text_input("Qual o seu sonho?"); v_m = st.number_input("Valor Necessário")
            if st.form_submit_button("CRIAR CAIXINHA"):
                cursor.execute("INSERT INTO metas (usuario, item, valor, data, guardado) VALUES (?,?,?,?,?)", (user, n_m, v_m, str(hoje), 0.0))
                conn.commit(); st.rerun()
    
    df_m = pd.read_sql_query(f"SELECT * FROM metas WHERE usuario='{user}'", conn)
    for _, m in df_m.iterrows():
        with st.container():
            st.markdown(f"### 🚀 {m['item']}")
            st.write(f"**Guardado: R$ {m['guardado']:.2f}** de R$ {m['valor']:.2f}")
            st.progress(min(m['guardado']/m['valor'], 1.0) if m['valor'] > 0 else 0)
            v_acao = st.number_input("Valor da Operação:", key=f"v_{m['id']}")
            c1, c2, c3 = st.columns(3)
            if c1.button("📥 DEPOSITAR", key=f"in_{m['id']}"):
                cursor.execute("UPDATE metas SET guardado = guardado + ? WHERE id=?", (v_acao, m['id'])); conn.commit(); st.rerun()
            if c2.button("📤 RETIRAR", key=f"out_{m['id']}"):
                cursor.execute("UPDATE metas SET guardado = guardado - ? WHERE id=?", (v_acao, m['id'])); conn.commit(); st.rerun()
            if c3.button("🗑️ EXCLUIR META", key=f"del_m_{m['id']}"):
                cursor.execute("DELETE FROM metas WHERE id=?", (m['id'],)); conn.commit(); st.rerun()

# --- SIDEBAR (CONFIGURAÇÕES GERAIS) ---
st.sidebar.title("⚙️ CONFIGURAÇÕES")
if st.sidebar.button("🚗 RECONFIGURAR VEÍCULO"):
    st.session_state.editando_veiculo = True
    st.rerun()

st.sidebar.markdown("---")
st.sidebar.subheader("🚨 ZONA DE PERIGO")
if st.sidebar.button("⚠️ ZERAR TODOS OS DADOS"):
    cursor.execute("DELETE FROM ganhos WHERE usuario=?", (user,))
    cursor.execute("DELETE FROM metas WHERE usuario=?", (user,))
    cursor.execute("DELETE FROM veiculo WHERE usuario=?", (user,))
    conn.commit(); st.rerun()

if st.sidebar.button("🚪 SAIR DO APLICATIVO"):
    st.session_state.autenticado = False
    st.rerun()
