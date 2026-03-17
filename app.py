import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
from datetime import datetime
import pytz
import io

# --- CONFIGURAÇÃO ---
fuso_br = pytz.timezone('America/Sao_Paulo')
st.set_page_config(page_title="Logística Pro", layout="wide")

# --- CONEXÃO COM GOOGLE SHEETS ---
# Usamos o st.cache_resource para evitar que a conexão caia
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Erro Crítico de Conexão. Verifique os Secrets.")

# IDs DE ACESSO
ID_DONO = "62322332399"
ID_MOTORISTA = "76565874204"

# --- FUNÇÃO PDF ---
def gerar_pdf(dados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Relatorio de Viagem", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    for key, value in dados.items():
        pdf.cell(200, 8, txt=f"{key}: {str(value)}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🚚 Sistema de Logística")
    user_input = st.text_input("ID de Acesso", type="password")
    if st.button("Entrar"):
        if user_input in [ID_DONO, ID_MOTORISTA]:
            st.session_state.logado = True
            st.session_state.user_id = user_input
            st.rerun()
        else:
            st.error("ID Inválido")

else:
    # Barra lateral de navegação
    st.sidebar.title("Menu")
    if st.sidebar.button("Sair / Logout"):
        st.session_state.logado = False
        st.rerun()

    # --- TELA DO DONO ---
    if st.session_state.user_id == ID_DONO:
        st.title("📊 Painel Administrativo (Proprietário)")
        
        try:
            # TTL=0 garante que ele busque o dado novo na planilha agora
            df = conn.read(ttl=0)
            
            if df is not None and not df.empty:
                # Limpa linhas fantasmas do Google Sheets
                df = df.dropna(how='all')
                st.write("### Relatórios em Tempo Real")
                st.dataframe(df, use_container_width=True)
                
                st.divider()
                c1, c2 = st.columns(2)
                
                # Download Excel
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                c1.download_button("📥 Baixar Planilha Completa (Excel)", data=buffer.getvalue(), file_name="relatorio_logistica.xlsx")
                
                # PDF do último envio
                ultimo_registro = df.iloc[-1].to_dict()
                pdf_data = gerar_pdf(ultimo_registro)
                c2.download_button("📄 Baixar Último Registro (PDF)", data=pdf_data, file_name="comprovante.pdf")
            else:
                st.info("Aguardando o primeiro envio de dados...")
        except Exception as e:
            st.error(f"Erro ao ler a planilha: {e}")
            st.warning("Verifique se o link da planilha nos Secrets está correto e se ela está como 'Editor' para 'Qualquer pessoa com o link'.")

    # --- TELA DO MOTORISTA ---
    else:
        st.title("🚛 Cadastro de Relatório")
        
        with st.form("form_viagem", clear_on_submit=True):
            st.subheader("📅 Informações da Viagem")
            data_v = st.date_input("Data", value=datetime.now(fuso_br))
            cliente = st.text_input("Cliente")
            col1, col2 = st.columns(2)
            origem = col1.text_input("Origem")
            destino = col2.text_input("Destino")
            
            st.subheader("🏁 KM e Combustível")
            km_i = col1.number_input("KM Inicial", min_value=0, value=None)
            km_f = col2.number_input("KM Final", min_value=0, value=None)
            litros = col1.number_input("Litros Abastecidos", min_value=0.0, format="%.1f", value=None)
            v_litro = col2.number_input("Preço por Litro (R$)", min_value=0.0, format="%.2f", value=None)
            
            st.subheader("💰 Gastos Adicionais")
            g_mot = col1.number_input("Gasto Motorista", min_value=0.0, value=None)
            g_cam = col2.number_input("Gasto Caminhão", min_value=0.0, value=None)
            
            obs = st.text_area("Observações")
            
            if st.form_submit_button("🚀 ENVIAR RELATÓRIO AGORA"):
                # Tratamento de valores vazios (Brecha de erro corrigida)
                v_km_i = km_i if km_i else 0
                v_km_f = km_f if km_f else 0
                v_litros = litros if litros else 0.0
                v_preco = v_litro if v_litro else 0.0
                v_g_mot = g_mot if g_mot else 0.0
                v_g_cam = g_cam if g_cam else 0.0
                
                total_abast = round(v_litros * v_preco, 2)
                agora = datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
                
                novo_relatorio = {
