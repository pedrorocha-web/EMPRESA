import streamlit as st
import pandas as pd
from streamlit_gsheets import GSheetsConnection
from fpdf import FPDF
from datetime import datetime
import io

# --- CONFIGURAÇÃO DA PÁGINA ---
st.set_page_config(page_title="Sistema Logística Pro", layout="centered")

# --- CONEXÃO COM GOOGLE SHEETS ---
# O ttl=0 garante que o app sempre busque dados novos, sem "esquecer" nada
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CONFIGURAÇÃO DE ACESSO ---
ID_DONO = "62322332399"
ID_MOTORISTA = "76565874204"

# --- FUNÇÃO PARA GERAR PDF ---
def gerar_pdf(dados):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(200, 10, txt="Comprovante de Envio - Logística", ln=True, align='C')
    pdf.ln(10)
    pdf.set_font("Arial", size=12)
    for key, value in dados.items():
        pdf.cell(200, 10, txt=f"{key}: {value}", ln=True)
    return pdf.output(dest='S').encode('latin-1')

# --- CONTROLE DE LOGIN ---
if 'logado' not in st.session_state:
    st.session_state.logado = False

if not st.session_state.logado:
    st.title("🚚 Acesso ao Sistema")
    user_input = st.text_input("ID de Usuário", type="password")
    if st.button("Entrar"):
        if user_input in [ID_DONO, ID_MOTORISTA]:
            st.session_state.logado = True
            st.session_state.user_id = user_input
            st.rerun()
        else:
            st.error("ID não reconhecido.")

else:
    # Menu Lateral
    st.sidebar.write(f"Logado como: {'Dono' if st.session_state.user_id == ID_DONO else 'Motorista'}")
    if st.sidebar.button("Sair"):
        st.session_state.logado = False
        st.rerun()

    # --- TELA DO DONO ---
    if st.session_state.user_id == ID_DONO:
        st.title("📊 Painel Administrativo")
        
        try:
            # ttl=0 força a leitura em tempo real da planilha
            df = conn.read(ttl=0)
            
            if df is not None and not df.empty:
                st.write("### Histórico Completo")
                st.dataframe(df)

                # Exportar para Excel
                buffer = io.BytesIO()
                with pd.ExcelWriter(buffer, engine='openpyxl') as writer:
                    df.to_excel(writer, index=False)
                st.download_button("📥 Baixar Planilha (Excel)", data=buffer.getvalue(), file_name="relatorio_geral.xlsx")
            else:
                st.info("Nenhum dado encontrado na planilha ainda.")
        except Exception as e:
            st.error(f"Erro ao conectar com a planilha: {e}")

    # --- TELA DO MOTORISTA ---
    else:
        st.title("🚛 Envio de Relatório")
        
        with st.form("form_viagem", clear_on_submit=True):
            col1, col2 = st.columns(2)
            with col1:
                rota = st.text_input("Origem / Destino")
                cliente = st.text_input("Cliente")
                km = st.text_input("KM Inicial / Final")
            with col2:
                frete = st.number_input("Frete Bruto (R$)", min_value=0.0, step=50.0)
                posto = st.text_input("Posto")
                litros = st.number_input("Litros Abastecidos", min_value=0.0, step=1.0)
            
            obs = st.text_area("Observações (Despesas, Manutenção, etc)")
            
            if st.form_submit_button("🚀 ENVIAR AGORA"):
                try:
                    # Coleta os dados
                    dados_novos = {
                        "Data/Hora": datetime.now().strftime("%d/%m/%Y %H:%M"),
                        "Rota": rota,
                        "Cliente": cliente,
                        "KM": km,
                        "Frete": str(frete),
                        "Posto": posto,
                        "Litros": str(litros),
                        "Observações": obs
                    }
                    
                    # Lê o que já existe e adiciona o novo
                    df_antigo = conn.read(ttl=0)
                    df_atualizado = pd.concat([df_antigo, pd.DataFrame([dados_novos])], ignore_index=True)
                    
                    # Salva no Google Sheets
                    conn.update(data=df_atualizado)
                    
                    # Limpa memória temporária para garantir que o dono veja na hora
                    st.cache_data.clear()
                    
                    st.success("✅ Relatório salvo com sucesso na nuvem!")
                    st.balloons()
                    
                    # Oferece o PDF do envio
                    pdf_data = gerar_pdf(dados_novos)
                    st.download_button("📄 Baixar Comprovante (PDF)", data=pdf_data, file_name="comprovante.pdf")
                    
                except Exception as e:
                    st.error(f"Falha ao salvar: {e}")
