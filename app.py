import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import pytz
import io

# --- CONFIGURAÇÃO DE FUSO HORÁRIO ---
fuso_br = pytz.timezone('America/Sao_Paulo')

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão Logística", layout="centered")

# --- BANCO DE DADOS EM MEMÓRIA ---
if 'banco_dados' not in st.session_state:
    st.session_state.banco_dados = []
if 'logado' not in st.session_state:
    st.session_state.logado = False

# --- IDs DE ACESSO ---
ID_DONO = "62322332399"
ID_MOTORISTA = "76565874204"

# --- FUNÇÃO PARA GERAR PDF ---
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
if not st.session_state.logado:
    st.title("🚚 Sistema de Logística")
    user_input = st.text_input("Digite seu ID", type="password")
    if st.button("Acessar"):
        if user_input in [ID_DONO, ID_MOTORISTA]:
            st.session_state.logado = True
            st.session_state.user_id = user_input
            st.rerun()
        else:
            st.error("ID não autorizado.")

else:
    # Barra lateral
    st.sidebar.write(f"Usuário: {'Proprietário' if st.session_state.user_id == ID_DONO else 'Motorista'}")
    if st.sidebar.button("Encerrar Sessão"):
        st.session_state.logado = False
        st.rerun()

    # --- TELA DO DONO (DOWNLOADS) ---
    if st.session_state.user_id == ID_DONO:
        st.title("📊 Painel de Controle")
        
        if not st.session_state.banco_dados:
            st.info("Aguardando novos envios de relatórios...")
        else:
            df = pd.DataFrame(st.session_state.banco_dados)
            st.write("### Relatórios na Sessão Atual")
            st.dataframe(df)

            st.divider()
            c1, c2 = st.columns(2)

            # Download EXCEL
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            c1.download_button("📥 Baixar Planilha (Excel)", data=buffer.getvalue(), file_name="logistica_export.xlsx")

            # Download PDF do último
            pdf_data = gerar_pdf(st.session_state.banco_dados[-1])
            c2.download_button("📄 Baixar Último PDF", data=pdf_data, file_name="comprovante.pdf")

    # --- TELA DO MOTORISTA (FORMULÁRIO) ---
    else:
        st.title("🚛 Cadastro de Viagem")
        
        with st.form("form_viagem", clear_on_submit=True):
            st.subheader("📍 Trajeto")
            col1, col2 = st.columns(2)
            origem = col1.text_input("Cidade Origem")
            destino = col2.text_input("Cidade Destino")
            
            st.subheader("🏁 Quilometragem")
            col3, col4 = st.columns(2)
            km_ini = col3.number_input("KM Inicial", min_value=0)
            km_fim = col4.number_input("KM Final", min_value=0)
            
            st.divider()
            st.subheader("⛽ Abastecimento")
            col5, col6 = st.columns(2)
            litros = col5.number_input("Litros", min_value=0.0)
            v_litro = col6.number_input("Valor do Litro (R$)", min_value=0.0)
            
            st.divider()
            st.subheader("💰 Gastos Diversos")
            g_mot = st.number_input("Gastos Motorista (Alimentação/Outros)", min_value=0.0)
            g_cam = st.number_input("Gastos Caminhão (Manutenção/Outros)", min_value=0.0)
            
            cliente = st.text_input("Cliente")
            obs = st.text_area("Observações Adicionais")
            
            if st.form_submit_button("🚀 ENVIAR RELATÓRIO"):
                agora = datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
                
                relatorio = {
                    "Data/Hora": agora,
                    "Cliente": cliente,
                    "Origem": origem,
                    "Destino": destino,
                    "KM Inicial": km_ini,
                    "KM Final": km_fim,
                    "Total KM": km_fim - km_ini,
                    "Litros": litros,
                    "Vlr Litro": v_litro,
                    "Total Abast.": litros * v_litro,
                    "Gastos Motorista": g_mot,
                    "Gastos Caminhão": g_cam,
                    "Obs": obs
                }
                
                st.session_state.banco_dados.append(relatorio)
                st.success("Enviado com sucesso! Avise ao administrador para baixar os dados.")
                st.balloons()
