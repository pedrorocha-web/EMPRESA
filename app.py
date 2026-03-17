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
st.set_page_config(page_title="Logística Pro", layout="centered")

# SUA URL DE IMPLANTAÇÃO CONFIGURADA
URL_PONTE = "https://script.google.com/macros/s/AKfycbxzrb0qWWT3Kh88qrXp7g7xnVZptqwNhc802RWpglqEn4 (Link encurtado para o exemplo) ..."
# Use a sua URL completa abaixo:
URL_OFICIAL = "https://script.google.com/macros/s/AKfycbxzrb0qWWT3Kh88qrXp7g7xnVZptqwNhc802RWpglqEn4Qc1bQonhg5npayqwVk7sWG/exec"

# IDs DE ACESSO
ID_DONO = "62322332399"
ID_MOTORISTA = "76565874204"

# --- CONEXÃO PARA LEITURA (DONO) ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("Erro nos Secrets. Verifique a conexão com a planilha.")

def gerar_pdf(dados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Relatorio de Viagem", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=10)
    for key, value in dados.items():
        pdf.cell(200, 8, txt=f"{key}: {value}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- SISTEMA DE LOGIN ---
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
            st.error("Acesso negado.")
else:
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- TELA DO DONO ---
    if st.session_state.user_id == ID_DONO:
        st.title("📊 Painel Administrativo")
        if st.button("🔄 Atualizar Tabela"):
            st.cache_data.clear()
            st.rerun()
        
        try:
            df = conn.read(ttl=0)
            if df is not None and not df.empty:
                st.dataframe(df, use_container_width=True)
                st.divider()
                # Exportação
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                st.download_button("📥 Baixar Excel", data=buffer.getvalue(), file_name="relatorio.xlsx")
            else:
                st.info("Aguardando registros...")
        except:
            st.warning("Não foi possível carregar os dados. Verifique os Secrets.")

    # --- TELA DO MOTORISTA (LISTA VERTICAL E ORDEM CORRIGIDA) ---
    else:
        st.title("🚛 Cadastro de Viagem")
        st.info("💡 Use 'Enter' para pular linha nos campos de texto.")
        
        with st.form("form_viagem", clear_on_submit=True):
            data_v = st.date_input("Data da Viagem", value=datetime.now(fuso_br))
            cliente = st.text_input("Nome do Cliente")
            origem = st.text_input("Cidade Origem")
            destino = st.text_input("Cidade Destino")
            km_i = st.number_input("KM Inicial", min_value=0, value=None)
            km_f = st.number_input("KM Final", min_value=0, value=None)
            litros = st.number_input("Litros Abastecidos", min_value=0.0, format="%.1f", value=None)
            v_litro = st.number_input("Preço por Litro", min_value=0.0, format="%.2f", value=None)
            
            # Campos que aceitam Enter para pular linha
            g_mot = st.text_area("Gastos Motorista (Detalhado)", height=80)
            g_cam = st.text_area("Gastos Caminhão (Detalhado)", height=80)
            obs = st.text_area("Observações", height=80)
            
            st.markdown("---")
            if st.form_submit_button("🚀 ENVIAR RELATÓRIO"):
                # Cálculos e tratamento de dados
                v_ki = km_i if km_i else 0
                v_kf = km_f if km_f else 0
                v_lt = litros if litros else 0.0
                v_vl = v_litro if v_litro else 0.0
                total_ab = f"R$ {v_lt * v_vl:.2f}"
                agora = datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")

                # ESTA ORDEM PRECISA SER IGUAL À DO APPS SCRIPT
                payload = {
                    "data_v": data_v.strftime("%d/%m/%Y"), # Coluna A
                    "cliente": str(cliente),              # Coluna B
                    "origem": str(origem),                # Coluna C
                    "destino": str(destino),              # Coluna D
                    "km_i": v_ki,                         # Coluna E
                    "km_f": v_kf,                         # Coluna F
                    "km_rodado": v_kf - v_ki,             # Coluna G
                    "litros": v_lt,                       # Coluna H
                    "total_abast": total_ab,              # Coluna I
                    "g_mot": g_mot.replace("\n", " | "),  # Coluna J
                    "g_cam": g_cam.replace("\n", " | "),  # Coluna K
                    "obs": obs.replace("\n", " | "),      # Coluna L
                    "enviado": agora                      # Coluna M
                }
                
                try:
                    res = requests.post(URL_OFICIAL, data=json.dumps(payload))
                    if res.status_code == 200:
                        st.success("✅ Relatório gravado com sucesso na planilha!")
                        st.balloons()
                    else:
                        st.error("Erro de comunicação com a planilha.")
                except Exception as e:
                    st.error(f"Erro de conexão: {e}")
