import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import pytz
import io

# --- CONFIGURAÇÃO DE FUSO HORÁRIO ---
fuso_br = pytz.timezone('America/Sao_Paulo')

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Gestão Logística", layout="wide")

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
    user_input = st.text_input("Digite seu ID de Acesso", type="password")
    if st.button("Acessar Sistema"):
        if user_input in [ID_DONO, ID_MOTORISTA]:
            st.session_state.logado = True
            st.session_state.user_id = user_input
            st.rerun()
        else:
            st.error("ID não autorizado.")

else:
    # Barra lateral
    st.sidebar.write(f"Sessão Ativa: **{'Proprietário' if st.session_state.user_id == ID_DONO else 'Motorista'}**")
    if st.sidebar.button("Encerrar Sessão"):
        st.session_state.logado = False
        st.rerun()

    # --- TELA DO DONO (DOWNLOADS) ---
    if st.session_state.user_id == ID_DONO:
        st.title("📊 Painel de Controle Administrativo")
        
        if not st.session_state.banco_dados:
            st.info("Nenhum relatório enviado nesta sessão.")
        else:
            df = pd.DataFrame(st.session_state.banco_dados)
            st.write("### Registros Recebidos")
            st.dataframe(df, use_container_width=True)

            st.divider()
            c1, c2 = st.columns(2)

            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            c1.download_button("📥 Baixar Planilha Geral (Excel)", data=buffer.getvalue(), file_name="relatorio_logistica.xlsx")

            pdf_data = gerar_pdf(st.session_state.banco_dados[-1])
            c2.download_button("📄 Baixar Último Envio em PDF", data=pdf_data, file_name="comprovante_viagem.pdf")

    # --- TELA DO MOTORISTA (FORMULÁRIO COM CAMPOS VAZIOS) ---
    else:
        st.title("🚛 Cadastro de Relatório de Viagem")
        
        with st.form("form_viagem", clear_on_submit=True):
            st.subheader("📍 Trajeto e Cliente")
            cliente = st.text_input("Nome do Cliente", value="")
            col1, col2 = st.columns(2)
            origem = col1.text_input("Cidade Origem", value="")
            destino = col2.text_input("Cidade Destino", value="")
            
            st.subheader("🏁 Quilometragem")
            col3, col4 = st.columns(2)
            # value=None deixa o campo vazio para preenchimento
            km_ini = col3.number_input("KM Inicial", min_value=0, step=1, value=None)
            km_fim = col4.number_input("KM Final", min_value=0, step=1, value=None)
            
            st.divider()
            st.subheader("⛽ Detalhes do Abastecimento")
            col5, col6 = st.columns(2)
            litros = col5.number_input("Quantidade de Litros", min_value=0.0, step=0.1, format="%.1f", value=None)
            v_litro = col6.number_input("Valor do Litro (R$ x.xx)", min_value=0.0, step=0.01, format="%.2f", value=None)
            
            st.divider()
            st.subheader("💰 Gastos Adicionais")
            col7, col8 = st.columns(2)
            g_mot = col7.number_input("Gastos Motorista (Alimentação/Hospedagem)", min_value=0.0, step=0.01, format="%.2f", value=None)
            g_cam = col8.number_input("Gastos Caminhão (Peças/Manutenção)", min_value=0.0, step=0.01, format="%.2f", value=None)
            
            obs = st.text_area("Observações Gerais", value="")
            
            if st.form_submit_button("🚀 ENVIAR RELATÓRIO DEFINITIVO"):
                # Validação simples para evitar envio de campos vazios críticos
                if None in [km_ini, km_fim, litros, v_litro]:
                    st.error("Por favor, preencha todos os campos numéricos (KM e Abastecimento).")
                else:
                    agora = datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
                    total_abast = litros * v_litro
                    
                    relatorio = {
                        "Data/Hora": agora,
                        "Cliente": cliente,
                        "Origem": origem,
                        "Destino": destino,
                        "KM Inicial": km_ini,
                        "KM Final": km_fim,
                        "KM Rodado": km_fim - km_ini,
                        "Litros": litros,
                        "Valor Unit. Litro": f"R$ {v_litro:.2f}",
                        "Valor Total Abast.": f"R$ {total_abast:.2f}",
                        "Gastos Motorista": f"R$ {g_mot if g_mot else 0:.2f}",
                        "Gastos Caminhão": f"R$ {g_cam if g_cam else 0:.2f}",
                        "Observações": obs
                    }
                    
                    st.session_state.banco_dados.append(relatorio)
                    st.success("Relatório enviado com sucesso!")
                    st.balloons()
