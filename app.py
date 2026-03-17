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

# Visual estilo App (Remoção de brechas visuais e menus)
st.markdown("""
    <style>
        #MainMenu {visibility: hidden;}
        footer {visibility: hidden;}
        header {visibility: hidden;}
        .stApp { max-width: 100%; padding-top: 0rem; }
    </style>
    """, unsafe_allow_html=True)

# --- CONEXÃO ---
# Criamos a conexão com tratamento de erro robusto
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except Exception as e:
    st.error("Erro na conexão com o Banco de Dados. Verifique os Secrets.")

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
        pdf.cell(200, 8, txt=f"{key}: {str(value)}", ln=True)
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

    # --- TELA DO DONO (CORREÇÃO DE CACHE) ---
    if st.session_state.user_id == ID_DONO:
        st.title("📊 Painel Administrativo")
        # Botão para forçar atualização manual se necessário
        if st.button("🔄 Atualizar Dados"):
            st.cache_data.clear()
            st.rerun()

        try:
            df = conn.read(ttl=0) # ttl=0 evita cache persistente
            if df is not None and not df.empty:
                # Remove colunas fantasmas que o Sheets cria
                df = df.dropna(how='all', axis=0).dropna(how='all', axis=1)
                st.dataframe(df, use_container_width=True)
                
                st.divider()
                c1, c2 = st.columns(2)
                
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                c1.download_button("📥 Baixar Excel", data=buffer.getvalue(), file_name="relatorio_geral.xlsx")
                
                pdf_data = gerar_pdf(df.iloc[-1].to_dict())
                c2.download_button("📄 Baixar Último PDF", data=pdf_data, file_name="ultimo_envio.pdf")
            else:
                st.info("Planilha vazia ou aguardando dados.")
        except Exception as e:
            st.error(f"Erro ao ler planilha: {e}")

    # --- TELA DO MOTORISTA (CORREÇÃO DE ENVIO) ---
    else:
        st.title("🚛 Novo Relatório")
        with st.form("form_viagem", clear_on_submit=True):
            st.subheader("📅 Dados Gerais")
            data_v = st.date_input("Data da Viagem", value=datetime.now(fuso_br))
            cliente = st.text_input("Nome do Cliente")
            origem = st.text_input("Cidade Origem")
            destino = st.text_input("Cidade Destino")
            
            st.subheader("🏁 KM e Abastecimento")
            col1, col2 = st.columns(2)
            km_i = col1.number_input("KM Inicial", min_value=0, step=1, value=None)
            km_f = col2.number_input("KM Final", min_value=0, step=1, value=None)
            litros = col1.number_input("Litros", min_value=0.0, step=0.1, value=None)
            v_litro = col2.number_input("Valor Litro (R$)", min_value=0.0, step=0.01, value=None)
            
            st.subheader("💰 Gastos Extras")
            g_mot = col1.number_input("Gasto Motorista", min_value=0.0, value=None)
            g_cam = col2.number_input("Gasto Caminhão", min_value=0.0, value=None)
            
            obs = st.text_area("Observações")
            
            enviar = st.form_submit_button("🚀 ENVIAR RELATÓRIO")
            
            if enviar:
                # Preenchimento de nulos para evitar quebra de concatenação
                v_km_i = km_i if km_i else 0
                v_km_f = km_f if km_f else 0
                v_litros = litros if litros else 0.0
                v_preco = v_litro if v_litro else 0.0
                
                total_abast = round(v_litros * v_preco, 2)
                agora_envio = datetime.now(fuso_br).strftime("%d/%m/%Y %H:%M")
                
                novo_dado = {
                    "Data da Viagem": data_v.strftime("%d/%m/%Y"),
                    "Cliente": str(cliente),
                    "Origem": str(origem),
                    "Destino": str(destino),
                    "KM Inicial": v_km_i,
                    "KM Final": v_km_f,
                    "KM Rodado": v_km_f - v_km_i,
                    "Litros": v_litros,
                    "Valor Unit. Litro": v_preco,
                    "Valor Total Abast.": total_abast,
                    "Gastos Motorista": g_mot if g_mot else 0.0,
                    "Gastos Caminhão": g_cam if g_cam else 0.0,
                    "Observações": str(obs),
                    "Enviado em": agora_envio
                }
                
                try:
                    # Lógica de atualização robusta
                    # 1. Busca dados atuais
                    df_existente = conn.read(ttl=0)
                    # 2. Concatena (trata se a planilha estiver vazia)
                    if df_existente is not None:
                        df_final = pd.concat([df_existente, pd.DataFrame([novo_dado])], ignore_index=True)
                    else:
                        df_final = pd.DataFrame([novo_dado])
                    
                    # 3. Atualiza e limpa cache imediatamente
                    conn.update(data=df_final)
                    st.cache_data.clear() # BRECHA DE CACHE FECHADA
                    
                    st.success("✅ Relatório salvo com sucesso!")
                    st.balloons()
                except Exception as e:
                    st.error(f"Erro crítico ao salvar: {e}. Verifique se a planilha está aberta ou protegida.")
