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

# URL DA SUA IMPLANTAÇÃO (APPS SCRIPT)
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
            st.error("ID Inválido.")
else:
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
                st.dataframe(df, use_container_width=True)
                st.divider()
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                st.download_button("📥 Baixar Excel", data=buffer.getvalue(), file_name="relatorio.xlsx")
            else:
                st.info("Nenhum registro encontrado.")
        except:
            st.error("Erro ao carregar planilha.")

    # --- TELA DO MOTORISTA (LISTA VERTICAL ANTI-ENVIO) ---
    else:
        st.title("🚛 Cadastro de Viagem")
        st.info("💡 A tecla 'Enter' agora pula linha. O envio só acontece no botão final.")
        
        with st.form("form_viagem", clear_on_submit=True):
            data_v = st.date_input("📅 Data da Viagem", value=datetime.now(fuso_br))
            
            # Usando text_area em vez de text_input para travar o "Enter"
            cliente = st.text_area("👤 Nome do Cliente", height=65)
            origem = st.text_area("📍 Cidade Origem", height=65)
            destino = st.text_area("🏁 Cidade Destino", height=65)
            
            distancia = st.number_input("📏 Distância Total (KM)", min_value=0, value=None)
            v_frete = st.number_input("💰 Valor do Frete (R$)", min_value=0.0, value=None, format="%.2f")
            
            st.markdown("---")
            st.subheader("⛽ Detalhes do Abastecimento")
            litros = st.number_input("Quantidade de Litros", min_value=0.0, value=None, format="%.1f")
            v_litro = st.number_input("Preço por Litro (R$)", min_value=0.0, value=None, format="%.2f")
            v_abast_total = st.number_input("Valor Total Abastecimento (R$)", min_value=0.0, value=None, format="%.2f")
            
            st.markdown("---")
            # Campos de gastos e observações (também em text_area)
            g_mot = st.text_area("🍔 Gastos Motorista (Pode listar itens)", height=100)
            g_cam = st.text_area("🛠️ Gastos Caminhão (Pode listar itens)", height=100)
            obs = st.text_area("📝 Observações", height=100)
            
            st.markdown("---")
            if st.form_submit_button("🚀 ENVIAR RELATÓRIO DEFINITIVO"):
                # Cálculo de segurança para o abastecimento (caso o total esteja zerado)
                calc_abast = (litros if litros else 0) * (v_litro if v_litro else 0)
                final_abast_val = v_abast_total if (v_abast_total and v_abast_total > 0) else calc_abast
                
                payload = {
                    "data_v": data_v.strftime("%d/%m/%Y"),
                    "cliente": str(cliente).strip().replace("\n", " "),
                    "origem": str(origem).strip().replace("\n", " "),
                    "destino": str(destino).strip().replace("\n", " "),
                    "distancia": distancia if distancia else 0,
                    "v_frete": f"R$ {v_frete if v_frete else 0:.2f}",
                    "litros": litros if litros else 0,
                    "total_abast": f"R$ {final_abast_val:.2f}",
                    "g_mot": str(g_mot).replace("\n", " | "),
                    "g_cam": str(g_cam).replace("\n", " | "),
                    "obs": str(obs).replace("\n", " | "),
                    "enviado": datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
                }
                
                try:
                    res = requests.post(URL_OFICIAL, data=json.dumps(payload))
                    if res.status_code == 200:
                        st.success("✅ Relatório enviado com sucesso!")
                        st.balloons()
                    else:
                        st.error("Falha ao salvar. Verifique a conexão.")
                except Exception as e:
                    st.error(f"Erro de conexão: {e}")
