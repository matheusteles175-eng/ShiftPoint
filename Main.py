import streamlit as st
import sqlite3
import pandas as pd
from datetime import date, datetime, timedelta

# --- 1. CONFIGURAÇÃO E ESTILO (VISUAL PROFISSIONAL) ---
st.set_page_config(page_title="CheckPoint Shift 🏁", layout="wide")

# CSS para fundo personalizado e efeito de vidro (Glassmorphism)
st.markdown("""
<style>
    .stApp {
        background: linear-gradient(rgba(0, 0, 0, 0.75), rgba(0, 0, 0, 0.75)), 
                    url("https://images.unsplash.com/photo-1614850523296-d8c1af93d400?q=80&w=2070&auto=format&fit=crop");
        background-size: cover;
        background-attachment: fixed;
    }
    /* Estilização dos blocos e abas */
    [data-testid="stForm"], .st-expander, .stMetric, .stTabs, div[data-testid="stVerticalBlock"] > div {
        background-color: rgba(255, 255, 255, 0.07) !important;
        backdrop-filter: blur(12px);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 20px !important;
        padding: 20px;
    }
    /* Cores de texto e botões */
    h1, h2, h3, h4, span, label, p, .stMetric div { color: #ffffff !important; }
    .stButton>button {
        width: 100%;
        border-radius: 12px;
        font-weight: bold;
    }
</style>
""", unsafe_allow_html=True)

def conectar():
    # Banco de dados SQLite para segurança total dos dados
    conn = sqlite3.connect("checkpoint_shift_mateus.db", check_same_thread=False)
    cursor = conn.cursor()
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS veiculo (usuario TEXT PRIMARY KEY, km_ini REAL, km_alvo REAL, custo REAL, fipe REAL, guardado_ipva REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS metas (id INTEGER PRIMARY KEY, usuario TEXT, item TEXT, valor REAL, data TEXT, guardado REAL)")
    cursor.execute("CREATE TABLE IF NOT EXISTS ganhos (id INTEGER PRIMARY KEY, usuario TEXT, data TEXT, ganho REAL, gasto REAL, km REAL, h_ini TEXT, h_fim TEXT)")
    conn.commit()
    return conn, cursor

conn, cursor = conectar()

# --- 2. ACESSO (LOGIN E CADASTRO) ---
if "autenticado" not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.markdown("<h1 style='text-align: center;'>🏁 CheckPoint Shift</h1>", unsafe_allow_html=True)
    aba_login, aba_cad = st.tabs(["🔑 Acessar", "📝 Criar Minha Conta"])
    
    with aba_login:
        u = st.text_input("Usuário").lower().strip()
        s = st.text_input("Senha", type="password")
        if st.button("ENTRAR NO PAINEL"):
            if cursor.execute("SELECT * FROM usuarios WHERE usuario=? AND senha=?", (u, s)).fetchone():
                st.session_state.autenticado, st.session_state.user = True, u
                st.rerun()
            else: st.error("Usuário ou senha incorretos.")
            
    with aba_cad:
        st.subheader("Comece sua gestão agora")
        nu = st.text_input("Novo Usuário").lower().strip()
        ns = st.text_input("Sua Senha", type="password")
        ns_c = st.text_input("Confirme a Senha", type="password")
        if st.button("CADASTRAR E FINALIZAR"):
            if nu and ns == ns_c:
                try:
                    cursor.execute("INSERT INTO usuarios VALUES (?,?)", (nu, ns))
                    conn.commit(); st.success("✅ Conta criada! Agora entre na aba 'Acessar'.")
                except: st.error("❌ Nome de usuário já existe.")
            else: st.warning("⚠️ As senhas não batem ou campos estão vazios.")
    st.stop()

user = st.session_state.user
hoje = date.today()

# --- 3. CONFIGURAÇÃO INICIAL DO VEÍCULO ---
v_data = cursor.execute("SELECT * FROM veiculo WHERE usuario=?", (user,)).fetchone()
if v_data is None:
    st.header(f"Seja bem-vindo, {user.upper()}! 🚀")
    st.subheader("Configure seu carro para liberar o painel:")
    with st.form("cfg_carro"):
        f1 = st.number_input("Valor FIPE do seu Carro", value=45000.0)
        f2 = st.number_input("KM Atual do Painel", value=100000.0)
        if st.form_submit_button("SALVAR E ABRIR MEU CHECKPOINT"):
            cursor.execute("INSERT INTO veiculo VALUES (?,?,?,?,?,?)", (user, f2, f2+10000, 350.0, f1, 0.0))
            conn.commit(); st.rerun()
    st.stop()

# --- 4. PAINEL DE CONTROLE (O CORAÇÃO DO APP) ---
st.title(f"🚀 PAINEL CHECKPOINT: {user.upper()}")
tab_ipva, tab_ganhos, tab_metas = st.tabs(["📊 IPVA & Resumo", "💰 Ganhos Diários", "🎯 Caixinhas (Sonhos)"])

# ABA IPVA
with tab_ipva:
    fipe, guardado_ipva = v_data[4], v_data[5]
    total_ipva = fipe * 0.04
    meses_jan = max(1, (13 - hoje.month))
    falta_ipva = total_ipva - guardado_ipva
    
    st.subheader("📌 Planejamento IPVA Próximo Ano")
    c1, c2, c3 = st.columns(3)
    c1.metric("IPVA Total Estimado", f"R$ {total_ipva:.2f}")
    c2.metric("Já Guardado", f"R$ {guardado_ipva:.2f}")
    c3.metric("Falta Guardar", f"R$ {falta_ipva:.2f}")
    
    st.info(f"💡 Mateus, você precisa guardar **R$ {falta_ipva/meses_jan:.2f} por mês** para pagar o IPVA tranquilo.")
    
    val_ipva = st.number_input("Valor para Alterar IPVA:", value=0.0)
    col_a, col_b = st.columns(2)
    if col_a.button("📥 Adicionar ao Fundo"):
        cursor.execute("UPDATE veiculo SET guardado_ipva = guardado_ipva + ? WHERE usuario=?", (val_ipva, user))
        conn.commit(); st.rerun()
    if col_b.button("📤 Retirar / Estornar"):
        cursor.execute("UPDATE veiculo SET guardado_ipva = guardado_ipva - ? WHERE usuario=?", (val_ipva, user))
        conn.commit(); st.rerun()

# ABA GANHOS
with tab_ganhos:
    with st.form("form_ganhos", clear_on_submit=True):
        st.subheader("Gravar Trabalho de Hoje")
        c_hora1, c_hora2 = st.columns(2)
        h_i = c_hora1.text_input("Início", "08:00")
        h_f = c_hora2.text_input("Fim", "18:00")
        g, gst, k = st.columns(3)
        v_g = g.number_input("Ganho Bruto")
        v_gst = gst.number_input("Gasto total")
        v_k = k.number_input("KM Rodado")
        if st.form_submit_button("GRAVAR JORNADA"):
            cursor.execute("INSERT INTO ganhos (usuario, data, ganho, gasto, km, h_ini, h_fim) VALUES (?,?,?,?,?,?,?)", 
                           (user, str(hoje), v_g, v_gst, v_k, h_i, h_f))
            conn.commit(); st.success("Gravado com sucesso!"); st.rerun()

    st.subheader("📜 Histórico de Ganhos")
    df_g = pd.read_sql_query(f"SELECT * FROM ganhos WHERE usuario='{user}' ORDER BY id DESC", conn)
    for i, r in df_g.iterrows():
        with st.container():
            col_d, col_v, col_h, col_del = st.columns([1, 2, 1, 0.5])
            col_d.write(f"📅 {r['data']}")
            col_v.write(f"💰 **Lucro: R$ {r['ganho']-r['gasto']:.2f}**")
            col_h.write(f"⏰ {r['h_ini']}-{r['h_fim']}")
            if col_del.button("🗑️", key=f"del_g_{r['id']}"):
                cursor.execute("DELETE FROM ganhos WHERE id=?", (r['id'],))
                conn.commit(); st.rerun()

# ABA CAIXINHAS
with tab_metas:
    st.subheader("🎯 Suas Caixinhas de Sonhos")
    with st.expander("➕ Criar Nova Caixinha"):
        with st.form("meta_sonho"):
            it = st.text_input("Qual o seu sonho?"); v = st.number_input("Valor Necessário R$"); d = st.date_input("Data Alvo")
            if st.form_submit_button("CRIAR"):
                cursor.execute("INSERT INTO metas (usuario, item, valor, data, guardado) VALUES (?,?,?,?,?)", 
                               (user, it, v, str(d), 0.0))
                conn.commit(); st.rerun()

    metas_db = pd.read_sql_query(f"SELECT * FROM metas WHERE usuario='{user}'", conn)
    for i, m in metas_db.iterrows():
        with st.container():
            st.write(f"### 🚀 {m['item']}")
            ja = m['guardado'] or 0.0
            st.progress(min(ja / m['valor'], 1.0) if m['valor'] > 0 else 0)
            st.write(f"Guardado: **R$ {ja:.2f}** | Meta: R$ {m['valor']:.2f} (Data: {m['data']})")
            
            v_mov = st.number_input("Valor da Operação:", key=f"val_{m['id']}", value=0.0)
            c_in, c_out, c_del = st.columns([1, 1, 1])
            if c_in.button("📥 Depositar", key=f"in_{m['id']}"):
                cursor.execute("UPDATE metas SET guardado = guardado + ? WHERE id=?", (v_mov, m['id']))
                conn.commit(); st.rerun()
            if c_out.button("📤 Retirar", key=f"out_{m['id']}"):
                cursor.execute("UPDATE metas SET guardado = guardado - ? WHERE id=?", (v_mov, m['id']))
                conn.commit(); st.rerun()
            if c_del.button("🗑️ Apagar Meta", key=f"del_m_{m['id']}"):
                cursor.execute("DELETE FROM metas WHERE id=?", (m['id'],))
                conn.commit(); st.rerun()

# Barra lateral para Logoff
if st.sidebar.button("Sair do Aplicativo"):
    st.session_state.autenticado = False
    st.rerun()
