import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
from datetime import datetime
import pytz
import io
import requests

# --- CONFIGURAÇÃO ---
fuso_br = pytz.timezone('America/Sao_Paulo')
st.set_page_config(page_title="Logística Pro", layout="wide")

# IDs DE ACESSO
ID_DONO = "62322332399"
ID_MOTORISTA = "76565874204"

# --- CONEXÃO PARA LEITURA (DONO) ---
conn = st.connection("gsheets", type=GSheetsConnection)

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
            # O Dono continua lendo a planilha normalmente
            df = conn.read(ttl=0)
            if df is not None and not df.empty:
                st.dataframe(df, use_container_width=True)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                st.download_button("📥 Baixar Excel", data=buffer.getvalue(), file_name="relatorio.xlsx")
            else:
                st.info("Nenhum dado encontrado na planilha.")
        except:
            st.error("Erro ao ler planilha. Verifique se o link nos Secrets está correto.")

    # --- TELA DO MOTORISTA ---
    else:
        st.title("🚛 Novo Relatório de Viagem")
        with st.form("form_viagem", clear_on_submit=True):
            data_v = st.date_input("Data da Viagem", value=datetime.now(fuso_br))
            cliente = st.text_input("Nome do Cliente")
            col1, col2 = st.columns(2)
            origem = col1.text_input("Origem")
            destino = col2.text_input("Destino")
            km_i = col1.number_input("KM Inicial", min_value=0, value=None)
            km_f = col2.number_input("KM Final", min_value=0, value=None)
            litros = col1.number_input("Litros", min_value=0.0, format="%.1f", value=None)
            v_litro = col2.number_input("Valor Litro", min_value=0.0, format="%.2f", value=None)
            g_mot = col1.number_input("Gasto Motorista", min_value=0.0, value=None)
            g_cam = col2.number_input("Gasto Caminhão", min_value=0.0, value=None)
            obs = st.text_area("Observações")
            
            if st.form_submit_button("🚀 ENVIAR RELATÓRIO"):
                # LINK DO FORMULÁRIO (Substitua aqui pelo link que você copiou no Passo 1)
                # O link deve terminar em /formResponse
                url_form = "COLOQUE_AQUI_O_LINK_DO_SEU_GOOGLE_FORM/formResponse"
                
                # Para que funcione, precisamos mapear os IDs das perguntas. 
                # Como isso é técnico, usaremos o método de salvamento direto por enquanto 
                # e eu te guiarei se este falhar.
                
                st.info("Enviando dados para a nuvem...")
                
                # Dados para salvar (Backup visual)
                agora = datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
                
                # TENTATIVA DE SALVAMENTO DIRETO (Corrigida)
                try:
                    df_atual = conn.read(ttl=0)
                    novo_dado = pd.DataFrame([{
                        "Data da Viagem": data_v.strftime("%d/%m/%Y"),
                        "Cliente": cliente, "Origem": origem, "Destino": destino,
                        "KM Inicial": km_i if km_i else 0,
                        "KM Final": km_f if km_f else 0,
                        "Litros": litros if litros else 0,
                        "Preço Litro": v_litro if v_litro else 0,
                        "Gasto Motorista": g_mot if g_mot else 0,
                        "Gasto Caminhão": g_cam if g_cam else 0,
                        "Observações": obs, "Enviado em": agora
                    }])
                    df_final = pd.concat([df_atual, novo_dado], ignore_index=True)
                    conn.update(data=df_final)
                    st.success("✅ Relatório enviado com sucesso!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro de permissão do Google: {e}")
                    st.warning("O Google bloqueou a escrita direta. Use o método do Formulário ou Service Account.")
