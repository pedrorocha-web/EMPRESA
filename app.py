import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
from datetime import datetime
import pytz
import io

# --- CONFIGURAÇÃO ---
fuso_br = pytz.timezone('America/Sao_Paulo')
st.set_page_config(page_title="Logística Pro", layout="centered")

# Visual estilo App (Esconde menus do Streamlit)
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stApp { max-width: 100%; padding-top: 0rem; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO ---
conn = st.connection("gsheets", type=GSheetsConnection)

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
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- TELA DO DONO ---
    if st.session_state.user_id == ID_DONO:
        st.title("📊 Painel Administrativo")
        try:
            df = conn.read(ttl=0)
            if df is not None and not df.empty:
                st.dataframe(df)
                st.divider()
                c1, c2 = st.columns(2)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                c1.download_button("📥 Baixar Excel", data=buffer.getvalue(), file_name="relatorio_geral.xlsx")
                
                pdf_data = gerar_pdf(df.iloc[-1].to_dict())
                c2.download_button("📄 Baixar Último PDF", data=pdf_data, file_name="ultimo_envio.pdf")
            else:
                st.info("Nenhum dado salvo na planilha.")
        except Exception as e:
            st.error(f"Erro ao acessar dados: {e}")

    # --- TELA DO MOTORISTA ---
    else:
        st.title("🚛 Novo Relatório")
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
            
            g_mot = col1.number_input("Gasto Motorista", min_value=0.0, format="%.2f", value=None)
            g_cam = col2.number_input("Gasto Caminhão", min_value=0.0, format="%.2f", value=None)
            
            obs = st.text_area("Observações")
            
            if st.form_submit_button("🚀 ENVIAR RELATÓRIO"):
                if None in [km_i, km_f, litros, v_litro]:
                    st.error("Por favor, preencha os campos de KM e Abastecimento.")
                else:
                    agora_envio = datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
                    total_abast = litros * v_litro
                    
                    novo_dado = {
                        "Data da Viagem": data_v.strftime("%d/%m/%Y"),
                        "Cliente": cliente,
                        "Origem": origem,
                        "Destino": destino,
                        "KM Inicial": km_i,
                        "KM Final": km_f,
                        "KM Rodado": km_f - km_i,
                        "Litros": litros,
                        "Valor Unit. Litro": f"{v_litro:.2f}",
                        "Valor Total Abast.": f"{total_abast:.2f}",
                        "Gastos Motorista": f"{g_mot if g_mot else 0:.2f}",
                        "Gastos Caminhão": f"{g_cam if g_cam else 0:.2f}",
                        "Observações": obs,
                        "Enviado em": agora_envio
                    }
                    
                    try:
                        # Lê o atual, junta com o novo e salva
                        df_atual = conn.read(ttl=0)
                        df_novo = pd.concat([df_atual, pd.DataFrame([novo_dado])], ignore_index=True)
                        conn.update(data=df_novo)
                        st.success("✅ Relatório salvo com sucesso!")
                        st.balloons()
                    except Exception as e:
                        st.error(f"Erro ao salvar na planilha: {e}")
