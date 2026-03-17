import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection # Conexão com a planilha
from fpdf import FPDF
from datetime import datetime
import pytz
import io

fuso_br = pytz.timezone('America/Sao_Paulo')
st.set_page_config(page_title="Gestão Logística", layout="wide")

# --- CONEXÃO CENTRAL ---
conn = st.connection("gsheets", type=GSheetsConnection)

if 'logado' not in st.session_state: st.session_state.logado = False

ID_DONO = "62322332399"
ID_MOTORISTA = "76565874204"

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

if not st.session_state.logado:
    st.title("🚚 Sistema de Logística")
    user_input = st.text_input("Digite o seu ID de Acesso", type="password")
    if st.button("Aceder ao Sistema"):
        if user_input in [ID_DONO, ID_MOTORISTA]:
            st.session_state.logado = True
            st.session_state.user_id = user_input
            st.rerun()
        else:
            st.error("ID não autorizado.")
else:
    st.sidebar.write(f"Sessão Ativa: **{'Proprietário' if st.session_state.user_id == ID_DONO else 'Motorista'}**")
    if st.sidebar.button("Encerrar Sessão"):
        st.session_state.logado = False
        st.rerun()

    if st.session_state.user_id == ID_DONO:
        st.title("📊 Painel Administrativo")
        # Lê os dados REAIS da planilha (ttl=0 força a atualização)
        df = conn.read(ttl=0) 
        
        if df is None or df.empty:
            st.info("Nenhum relatório encontrado na planilha.")
        else:
            st.write("### Registos Recebidos")
            st.dataframe(df, use_container_width=True)
            st.divider()
            c1, c2 = st.columns(2)
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            c1.download_button("📥 Baixar Planilha Geral", data=buffer.getvalue(), file_name="logistica.xlsx")
            pdf_data = gerar_pdf(df.iloc[-1].to_dict())
            c2.download_button("📄 Baixar Último PDF", data=pdf_data, file_name="comprovante.pdf")

    else:
        st.title("🚛 Cadastro de Relatório")
        with st.form("form_viagem", clear_on_submit=True):
            data_viagem = st.date_input("Data da Viagem", value=datetime.now(fuso_br))
            cliente = st.text_input("Nome do Cliente")
            col1, col2 = st.columns(2)
            origem = col1.text_input("Cidade Origem")
            destino = col2.text_input("Cidade Destino")
            km_ini = col1.number_input("KM Inicial", min_value=0, value=None)
            km_fim = col2.number_input("KM Final", min_value=0, value=None)
            litros = col1.number_input("Litros", min_value=0.0, format="%.1f", value=None)
            v_litro = col2.number_input("Valor do Litro", min_value=0.0, format="%.2f", value=None)
            g_mot = col1.number_input("Gastos Motorista", min_value=0.0, value=None)
            g_cam = col2.number_input("Gastos Caminhão", min_value=0.0, value=None)
            obs = st.text_area("Observações")
            
            if st.form_submit_button("🚀 ENVIAR RELATÓRIO"):
                # Cálculos automáticos mesmo se campos estiverem vazios
                v_km_i = km_ini if km_ini else 0
                v_km_f = km_fim if km_fim else 0
                v_li = litros if litros else 0.0
                v_vl = v_litro if v_litro else 0.0
                
                novo_dado = {
                    "Data da Viagem": data_viagem.strftime("%d/%m/%Y"),
                    "Cliente": cliente, "Origem": origem, "Destino": destino,
                    "KM Inicial": v_km_i, "KM Final": v_km_f, "KM Rodado": v_km_f - v_km_i,
                    "Litros": v_li, "Total Abast.": f"R$ {v_li * v_vl:.2f}",
                    "Gastos Motorista": f"R$ {g_mot if g_mot else 0:.2f}",
                    "Gastos Caminhão": f"R$ {g_cam if g_cam else 0:.2f}",
                    "Observações": obs,
                    "Enviado em": datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
                }
                
                # ENVIA PARA A PLANILHA
                df_atual = conn.read(ttl=0)
                df_novo = pd.concat([df_atual, pd.DataFrame([novo_dado])], ignore_index=True)
                conn.update(data=df_novo)
                st.success("Enviado com sucesso! Agora o proprietário já consegue ver.")
                st.balloons()
