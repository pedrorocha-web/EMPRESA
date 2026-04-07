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
    st.error("Erro nos Secrets. Verifique se o link da planilha está correto.")

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

# --- SISTEMA DE LOGIN ---
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
        if st.button("🔄 Atualizar Tabela"):
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
                c1.download_button("📥 Baixar Excel", data=buffer.getvalue(), file_name="relatorio_logistica.xlsx")
                
                pdf_data = gerar_pdf(df.iloc[-1].to_dict())
                c2.download_button("📄 Baixar Último PDF", data=pdf_data, file_name="comprovante.pdf")
            else:
                st.info("Nenhum dado encontrado na planilha.")
        except Exception as e:
            st.error(f"Erro ao carregar dados: {e}")

    # --- TELA DO MOTORISTA (LISTA VERTICAL ATUALIZADA) ---
    else:
        st.title("🚛 Cadastro de Viagem")
        st.write("Preencha as informações abaixo:")
        
        with st.form("form_viagem", clear_on_submit=True):
            data_v = st.date_input("📅 Data da Viagem", value=datetime.now(fuso_br))
            cliente = st.text_input("👤 Nome do Cliente")
            origem = st.text_input("📍 Cidade Origem")
            destino = st.text_input("🏁 Cidade Destino")
            
            # Campo de Distância (Substituiu KM Inicial e Final)
            distancia = st.number_input("📏 Distância Total da Viagem (KM)", min_value=0, value=None, step=1)
            
            # Novo Campo de Frete
            v_frete = st.number_input("💰 Valor do Frete (R$)", min_value=0.0, value=None, format="%.2f")
            
            litros = st.number_input("⛽ Quantidade de Litros", min_value=0.0, value=None, format="%.1f")
            v_litro = st.number_input("💵 Preço por Litro (R$)", min_value=0.0, value=None, format="%.2f")
            
            # Campos que aceitam Enter para pular linha
            g_mot = st.text_area("🍔 Gastos Motorista (Detalhado)", height=100)
            g_cam = st.text_area("🛠️ Gastos Caminhão (Detalhado)", height=100)
            obs = st.text_area("📝 Observações Gerais", height=100)
            
            st.markdown("---")
            enviar = st.form_submit_button("🚀 ENVIAR RELATÓRIO DEFINITIVO")
            
            if enviar:
                v_dist = distancia if distancia is not None else 0
                v_fr = v_frete if v_frete is not None else 0.0
                v_lt = litros if litros is not None else 0.0
                v_vl = v_litro if v_litro is not None else 0.0
                total_abast = round(v_lt * v_vl, 2)
                
                payload = {
                    "data_v": data_v.strftime("%d/%m/%Y"),
                    "cliente": str(cliente),
                    "origem": str(origem),
                    "destino": str(destino),
                    "distancia": v_dist,
                    "v_frete": f"R$ {v_fr:.2f}",
                    "litros": v_lt,
                    "total_abast": f"R$ {total_abast:.2f}",
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
                        st.error("Erro ao salvar os dados na planilha.")
                except Exception as e:
                    st.error(f"Erro de conexão: {e}")
