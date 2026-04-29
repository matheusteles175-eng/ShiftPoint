import streamlit as st
import sqlite3
import pandas as pd
import base64
from datetime import date, datetime, timedelta

# --- 1. CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(
    page_title="CheckPoint Shift 🏁", 
    page_icon="🏁", 
    layout="wide",
    initial_sidebar_state="collapsed"
)

# --- 2. FUNÇÕES DE ESTILO (WALLPAPER E CARDS) ---
def get_base64(bin_file):
    with open(bin_file, 'rb') as f:
        data = f.read()
    return base64.b64encode(data).decode()

def aplicar_visual(caminho_img=None):
    if caminho_img:
        try:
            bin_str = get_base64(caminho_img)
            bg_style = f'''
            <style>
            .stApp {{
                background-image: url("data:image/png;base64,{bin_str}");
                background-size: cover;
                background-attachment: fixed;
            }}
            </style>
            '''
            st.markdown(bg_style, unsafe_allow_html=True)
        except:
            pass
    
    # CSS para transparência e cores
    st.markdown("""
    <style>
        /* Estilo Vidro para os containers */
        [data-testid="stForm"], .st-expander, .stMetric, .stMarkdown div[style*="background-color"] {
            background-color: rgba(255, 255, 255, 0.8) !important;
            backdrop-filter: blur(10px);
            border-radius: 15px !important;
            border: 1px solid rgba(255,255,255,0.3);
            padding: 15px;
        }
        .card-verde { background-color: rgba(40, 167, 69, 0.2) !important; border-left: 5px solid #28a745 !important; }
        .card-amarelo { background-color: rgba(255, 193, 7, 0.2) !important; border-left: 5px solid #ffc107 !important; }
    </style>
    """, unsafe_allow_html=True)

# --- 3. BANCO DE DADOS (SQLite) ---
def conectar():
    conn = sqlite3.connect("checkpoint_shift_v1.db", check_same_thread=False)
    cursor = conn.cursor()
    # Tabelas
    cursor.execute("CREATE TABLE IF NOT EXISTS usuarios (usuario TEXT PRIMARY KEY, senha TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS veiculo (usuario TEXT PRIMARY KEY, fipe REAL, guardado_ipva REAL, wallpaper TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS ganhos (id INTEGER PRIMARY KEY, usuario TEXT, data TEXT, ganho REAL, gasto REAL, h_ini TEXT, h_fim TEXT)")
    cursor.execute("CREATE TABLE IF NOT EXISTS metas (id INTEGER PRIMARY KEY, usuario TEXT, item TEXT, valor REAL, data_alvo TEXT, guardado REAL)")
    conn.commit()
    return conn, cursor

conn, cursor = conectar()

# --- 4. SISTEMA DE LOGIN ---
if "autenticado" not in st.session_state: st.session_state.autenticado = False

if not st.session_state.autenticado:
    st.title("🏁 CheckPoint Shift - Acesso")
    aba1, aba2 = st.tabs(["🔑 Login", "📝 Criar Conta"])
    with aba1:
        u = st.text_input("Usuário").lower().strip()
        s = st.text_input("Senha", type="password")
        if st.button("Entrar"):
            user = cursor.execute("SELECT * FROM usuarios WHERE usuario=? AND senha=?", (u, s)).fetchone()
            if user:
                st.session_state.autenticado, st.session_state.user = True, u
                st.rerun()
            else: st.error("Usuário ou senha inválidos.")
    with aba2:
        nu = st.text_input("Novo Usuário").lower().strip()
        ns = st.text_input("Nova Senha", type="password")
        if st.button("Cadastrar"):
            try:
                cursor.execute("INSERT INTO usuarios VALUES (?,?)", (nu, ns))
                conn.commit(); st.success("Conta criada!")
            except: st.error("Usuário já existe.")
    st.stop()

# --- 5. CARREGAR PREFERÊNCIAS E DADOS ---
user = st.session_state.user
v_data = cursor.execute("SELECT * FROM veiculo WHERE usuario=?", (user,)).fetchone()

# Aplicar Wallpaper
if v_data and v_data[3]:
    aplicar_visual(v_data[3])
else:
    aplicar_visual()

# Se não tem carro configurado, obriga a configurar
if v_data is None:
    st.warning("⚠️ Olá Mateus! Configure sua FIPE para ativar o CheckPoint.")
    with st.form("set_car"):
        fipe_ini = st.number_input("Valor FIPE do Carro", value=45000.0)
        if st.form_submit_button("Ativar Sistema"):
            cursor.execute("INSERT INTO veiculo VALUES (?,?,?,?)", (user, fipe_ini, 0.0, None))
            conn.commit(); st.rerun()
    st.stop()

# --- 6. INTERFACE PRINCIPAL ---
st.title(f"CheckPoint Shift 🏁 - {user.upper()}")

tab1, tab2, tab3, tab4 = st.tabs(["💰 Jornada Diária", "⚙️ Gestão IPVA", "🎯 Caixinhas", "🖼️ Personalizar"])

# --- ABA 1: GANHOS ---
with tab1:
    with st.form("jornada", clear_on_submit=True):
        c1, c2 = st.columns(2)
        h_i = c1.text_input("Início", "08:00")
        h_f = c2.text_input("Fim", "18:00")
        g, gst = st.columns(2)
        v_g = g.number_input("Ganho Bruto (R$)", min_value=0.0)
        v_gst = gst.number_input("Gasto/Combustível (R$)", min_value=0.0)
        if st.form_submit_button("🏁 FINALIZAR CHECKPOINT"):
            cursor.execute("INSERT INTO ganhos (usuario, data, ganho, gasto, h_ini, h_fim) VALUES (?,?,?,?,?,?)",
                           (user, str(date.today()), v_g, v_gst, h_i, h_f))
            conn.commit(); st.rerun()

    st.subheader("📜 Últimos Registros")
    df_g = pd.read_sql_query(f"SELECT * FROM ganhos WHERE usuario='{user}' ORDER BY id DESC", conn)
    for i, r in df_g.iterrows():
        with st.container():
            col1, col2, col3, col4 = st.columns([1, 2, 1, 0.5])
            col1.write(f"📅 {r['data']}")
            col2.write(f"💰 **Líquido: R$ {r['ganho']-r['gasto']:.2f}**")
            col3.write(f"⏰ {r['h_ini']} - {r['h_fim']}")
            if col4.button("🗑️", key=f"dg_{r['id']}"):
                cursor.execute("DELETE FROM ganhos WHERE id=?", (r['id'],))
                conn.commit(); st.rerun()

# --- ABA 2: IPVA ---
with tab2:
    fipe_v, guardado_ipva = v_data[1], v_data[2]
    total_ipva = fipe_v * 0.04
    meses_falta = max(1, (13 - date.today().month))
    precisa_mensal = (total_ipva - guardado_ipva) / meses_falta

    st.markdown(f"""
    <div class='card-amarelo'>
        <h3>Planejamento IPVA</h3>
        <p>Base: FIPE R$ {fipe_v:,.2f} | Alíquota: 4%</p>
        <h4>Total a Pagar em Janeiro: R$ {total_ipva:.2f}</h4>
    </div>
    """, unsafe_allow_html=True)
    
    c1, c2 = st.columns(2)
    c1.metric("Já Guardado", f"R$ {guardado_ipva:.2f}")
    c2.metric("Falta p/ Mês", f"R$ {precisa_mensal:.2f}")

    st.info(f"💡 Conta: (R$ {total_ipva:.2f} Total - R$ {guardado_ipva:.2f} Guardado) / {meses_falta} meses.")
    
    val_ipva = st.number_input("Valor para Movimentar (R$)", key="val_ipva")
    col_a, col_b, col_z = st.columns(3)
    if col_a.button("📥 Adicionar", use_container_width=True):
        cursor.execute("UPDATE veiculo SET guardado_ipva = guardado_ipva + ? WHERE usuario=?", (val_ipva, user))
        conn.commit(); st.rerun()
    if col_b.button("📤 Estornar/Retirar", use_container_width=True):
        cursor.execute("UPDATE veiculo SET guardado_ipva = guardado_ipva - ? WHERE usuario=?", (val_ipva, user))
        conn.commit(); st.rerun()
    if col_z.button("🔄 Zerar Fundo", use_container_width=True):
        cursor.execute("UPDATE veiculo SET guardado_ipva = 0 WHERE usuario=?", (user,))
        conn.commit(); st.rerun()

# --- ABA 3: CAIXINHAS ---
with tab3:
    st.subheader("🎯 Meus Objetivos")
    with st.expander("➕ Nova Caixinha"):
        with st.form("meta_f"):
            it = st.text_input("Qual o Sonho?"); v = st.number_input("Valor Total"); d = st.date_input("Data Alvo")
            if st.form_submit_button("Criar Caixinha"):
                cursor.execute("INSERT INTO metas (usuario, item, valor, data_alvo, guardado) VALUES (?,?,?,?,?)",
                               (user, it, v, str(d), 0.0))
                conn.commit(); st.rerun()

    df_m = pd.read_sql_query(f"SELECT * FROM metas WHERE usuario='{user}'", conn)
    for i, m in df_m.iterrows():
        with st.container():
            st.markdown(f"### 🚀 {m['item']}")
            prog = min(m['guardado'] / m['valor'], 1.0) if m['valor'] > 0 else 0
            st.progress(prog)
            st.write(f"Guardado: **R$ {m['guardado']:.2f}** / Meta: R$ {m['valor']:.2f}")
            
            c_val, c_in, c_out, c_del = st.columns([1, 1, 1, 0.5])
            v_mov = c_val.number_input("Valor:", key=f"v{m['id']}", value=0.0)
            if c_in.button("📥 Depósito", key=f"in{m['id']}"):
                cursor.execute("UPDATE metas SET guardado = guardado + ? WHERE id=?", (v_mov, m['id']))
                conn.commit(); st.rerun()
            if c_out.button("📤 Saque", key=f"out{m['id']}"):
                cursor.execute("UPDATE metas SET guardado = guardado - ? WHERE id=?", (v_mov, m['id']))
                conn.commit(); st.rerun()
            if c_del.button("🗑️", key=f"delm{m['id']}"):
                cursor.execute("DELETE FROM metas WHERE id=?", (m['id'],))
                conn.commit(); st.rerun()

# --- ABA 4: PERSONALIZAR ---
with tab4:
    st.subheader("🖼️ Customizar Wallpaper")
    img_file = st.file_uploader("Escolha uma foto da sua galeria", type=['png', 'jpg', 'jpeg'])
    if img_file:
        with open("bg_user.png", "wb") as f:
            f.write(img_file.getbuffer())
        cursor.execute("UPDATE veiculo SET wallpaper = ? WHERE usuario=?", ("bg_user.png", user))
        conn.commit(); st.success("Wallpaper salvo! Clique no botão abaixo:"); st.button("🔄 Aplicar Agora")
    
    if st.button("❌ Remover Wallpaper"):
        cursor.execute("UPDATE veiculo SET wallpaper = NULL WHERE usuario=?", (user,))
        conn.commit(); st.rerun()
    
    st.divider()
    if st.button("🚪 Sair do Aplicativo"):
        st.session_state.autenticado = False; st.rerun()

