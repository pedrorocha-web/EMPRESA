import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
from datetime import datetime
import pytz
import io
import requests
import json

# --- CONFIGURAÇÃO ---
fuso_br = pytz.timezone('America/Sao_Paulo')
st.set_page_config(page_title="Logística Pro", layout="wide")

# URL da ponte que você gerou no Apps Script
URL_PONTE = "https://script.google.com/macros/s/AKfycbxzrb0qWWT3Kh88qrXp7g7xnVZptqwNhc802RWpglqEn4Qc1bQonhg5npayqwVk7sWG/exec"

# IDs DE ACESSO
ID_DONO = "62322332399"
ID_MOTORISTA = "76565874204"

# --- CONEXÃO PARA LEITURA (PROPRIETÁRIO) ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("Erro na conexão de leitura. Verifique os Secrets.")

def gerar_pdf(dados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Comprovante de Viagem", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    for key, value in dados.items():
        pdf.cell(200, 8, txt=f"{key}: {value}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🚚 Sistema de Logística")
    user_input = st.text_input("Digite o seu ID de Acesso", type="password")
    if st.button("Entrar no Sistema"):
        if user_input in [ID_DONO, ID_MOTORISTA]:
            st.session_state.logado = True
            st.session_state.user_id = user_input
            st.rerun()
        else:
            st.error("ID não autorizado.")
else:
    st.sidebar.write(f"Usuário: **{'Proprietário' if st.session_state.user_id == ID_DONO else 'Motorista'}**")
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- TELA DO DONO ---
    if st.session_state.user_id == ID_DONO:
        st.title("📊 Painel Administrativo")
        
        if st.button("🔄 Atualizar Dados"):
            st.cache_data.clear()
            st.rerun()

        try:
            df = conn.read(ttl=0)
            if df is not None and not df.empty:
                st.write("### Registros Recebidos")
                st.dataframe(df, use_container_width=True)

                st.divider()
                c1, c2 = st.columns(2)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                c1.download_button("📥 Baixar Excel", data=buffer.getvalue(), file_name="relatorio.xlsx")

                pdf_data = gerar_pdf(df.iloc[-1].to_dict())
                c2.download_button("📄 Baixar PDF do Último Envio", data=pdf_data, file_name="comprovante.pdf")
            else:
                st.info("Nenhum dado encontrado na planilha.")
        except Exception as e:
            st.error(f"Erro ao acessar dados: {e}")

    # --- TELA DO MOTORISTA ---
    else:
        st.title("🚛 Cadastro de Relatório")
        
        with st.form("form_viagem", clear_on_submit=True):
            data_v = st.date_input("Data da Viagem", value=datetime.now(fuso_br))
            cliente = st.text_input("Nome do Cliente")
            
            col1, col2 = st.columns(2)
            origem = col1.text_input("Cidade Origem")
            destino = col2.text_input("Cidade Destino")
            km_i = col1.number_input("KM Inicial", min_value=0, value=None)
            km_f = col2.number_input("KM Final", min_value=0, value=None)
            
            litros = col1.number_input("Litros", min_value=0.0, format="%.1f", value=None)
            v_litro = col2.number_input("Valor Litro (R$)", min_value=0.0, format="%.2f", value=None)
            g_mot = col1.number_input("Gastos Motorista", min_value=0.0, value=None)
            g_cam = col2.number_input("Gastos Caminhão", min_value=0.0, value=None)
            
            obs = st.text_area("Observações")
            
            if st.form_submit_button("🚀 ENVIAR RELATÓRIO"):
                # Tratamento para campos não obrigatórios
                v_km_i = km_i if km_i else 0
                v_km_f = km_f if km_f else 0
                v_litros = litros if litros else 0.0
                v_v_litro = v_litro if v_litro else 0.0
                total_abast = round(v_litros * v_v_litro, 2)
                
                payload = {
                    "data_v": data_v.strftime("%d/%m/%Y"),
                    "cliente": str(cliente),
                    "origem": str(origem),
                    "destino": str(destino),
                    "km_i": v_km_i,
                    "km_f": v_km_f,
                    "km_rodado": v_km_f - v_km_i,
                    "litros": v_litros,
                    "total_abast": f"R$ {total_abast:.2f}",
                    "g_mot": f"R$ {g_mot if g_mot else 0.0:.2f}",
                    "g_cam": f"R$ {g_cam if g_cam else 0.0:.2f}",
                    "obs": str(obs),
                    "enviado": datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
                }
                
                try:
                    # Envia os dados para a URL do Apps Script
                    res = requests.post(URL_PONTE, data=json.dumps(payload))
                    if res.status_code == 200:
                        st.success("✅ Enviado com sucesso!")
                        st.balloons()
                    else:
                        st.error("Falha no servidor de destino.")
                except Exception as e:
                    st.error(f"Erro de conexão: {e}")
