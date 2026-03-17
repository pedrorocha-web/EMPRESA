import streamlit as st
import pandas as pd
from fpdf import FPDF
from datetime import datetime
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Relatórios de Logística", layout="centered")

# --- BANCO DE DADOS TEMPORÁRIO (Memória Local) ---
if 'db_relatorios' not in st.session_state:
    st.session_state.db_relatorios = []
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
    pdf.cell(200, 10, txt="Relatorio de Viagem", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    for key, value in dados.items():
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- TELA DE LOGIN ---
if not st.session_state.logado:
    st.title("🔒 Acesso ao Sistema")
    user_input = st.text_input("Digite seu ID", type="password")
    if st.button("Entrar"):
        if user_input in [ID_DONO, ID_MOTORISTA]:
            st.session_state.logado = True
            st.session_state.user_id = user_input
            st.rerun()
        else:
            st.error("ID incorreto.")

else:
    # Barra Lateral
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- VISÃO DO DONO (DOWNLOADS) ---
    if st.session_state.user_id == ID_DONO:
        st.title("📊 Painel de Exportação (Dono)")
        
        if not st.session_state.db_relatorios:
            st.info("Nenhum relatório foi enviado nesta sessão ainda.")
        else:
            df = pd.DataFrame(st.session_state.db_relatorios)
            st.write("### Dados Disponíveis para Baixar:")
            st.dataframe(df)

            st.divider()
            col1, col2 = st.columns(2)

            # Opção 1: Baixar tudo em EXCEL
            buffer = io.BytesIO()
            with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                df.to_excel(writer, index=False)
            col1.download_button(
                label="📥 Baixar Tudo em Excel",
                data=buffer.getvalue(),
                file_name=f"logistica_{datetime.now().strftime('%d_%m_%Y')}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )

            # Opção 2: Baixar o ÚLTIMO em PDF
            ultimo_dado = st.session_state.db_relatorios[-1]
            pdf_data = gerar_pdf(ultimo_dado)
            col2.download_button(
                label="📄 Baixar Último em PDF",
                data=pdf_data,
                file_name="comprovante_viagem.pdf",
                mime="application/pdf"
            )

    # --- VISÃO DO MOTORISTA (ENVIO) ---
    else:
        st.title("🚛 Envio de Relatório")
        
        with st.form("meu_form", clear_on_submit=True):
            rota = st.text_input("Rota (Origem/Destino)")
            cliente = st.text_input("Cliente")
            km = st.text_input("KM")
            frete = st.number_input("Valor do Frete", min_value=0.0)
            posto = st.text_input("Posto")
            litros = st.number_input("Litros", min_value=0.0)
            obs = st.text_area("Observações")
            
            if st.form_submit_button("Enviar Relatório"):
                novo_item = {
                    "Data": datetime.now().strftime("%d/%m/%Y %H:%M"),
                    "Rota": rota,
                    "Cliente": cliente,
                    "KM": km,
                    "Frete": frete,
                    "Posto": posto,
                    "Litros": litros,
                    "Obs": obs
                }
                # Adiciona na lista temporária
                st.session_state.db_relatorios.append(novo_item)
                st.success("Relatório enviado! O dono já pode baixar os arquivos.")
                st.balloons()
