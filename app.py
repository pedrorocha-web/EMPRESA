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

# --- CONEXÃO ---
try:
    conn = st.connection("gsheets", type=GSheetsConnection)
except:
    st.error("Erro nos Secrets. Verifique a conexão com a planilha.")

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
            st.error("Acesso Negado.")
else:
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
            st.dataframe(df, use_container_width=True)
        except:
            st.error("Erro ao ler dados.")

    # --- TELA DO MOTORISTA (TOTALMENTE ANTI-ENVIO) ---
    else:
        st.title("🚛 Relatório de Viagem")
        st.warning("⚠️ A tecla 'Enter' agora pula linha em TODOS os campos. O envio só ocorre no botão final.")
        
        with st.form("form_viagem", clear_on_submit=True):
            data_v = st.date_input("📅 Data da Viagem", value=datetime.now(fuso_br))
            
            # TODOS OS CAMPOS DE TEXTO COMO TEXT_AREA PARA BLOQUEAR O ENTER
            cliente = st.text_area("👤 Nome do Cliente", height=70, placeholder="Digite o nome do cliente...")
            origem = st.text_area("📍 Cidade Origem", height=70, placeholder="De onde saiu?")
            destino = st.text_area("🏁 Cidade Destino", height=70, placeholder="Para onde vai?")
            
            # Campos Numéricos (Enter aqui apenas pula para o próximo campo)
            distancia = st.number_input("📏 Distância da Viagem (KM)", min_value=0, value=None)
            v_frete = st.number_input("💰 Valor do Frete (R$)", min_value=0.0, value=None, format="%.2f")
            
            st.markdown("---")
            st.subheader("⛽ Abastecimento")
            litros = st.number_input("Quantidade de Litros", min_value=0.0, value=None, format="%.1f")
            v_litro = st.number_input("Preço por Litro (R$)", min_value=0.0, value=None, format="%.2f")
            v_abast_total = st.number_input("Valor TOTAL Pago no Posto (R$)", min_value=0.0, value=None, format="%.2f")
            
            st.markdown("---")
            g_mot = st.text_area("🍔 Gastos Motorista", height=100, placeholder="Liste os gastos aqui...")
            g_cam = st.text_area("🛠️ Gastos Caminhão", height=100, placeholder="Manutenção, pneu, etc...")
            obs = st.text_area("📝 Observações Gerais", height=100)
            
            st.markdown("---")
            enviar = st.form_submit_button("🚀 ENVIAR RELATÓRIO DEFINITIVO")
            
            if enviar:
                # Lógica de cálculo automática se o total do posto estiver vazio
                calc_abast = (litros if litros else 0) * (v_litro if v_litro else 0)
                total_final = v_abast_total if (v_abast_total and v_abast_total > 0) else calc_abast
                
                payload = {
                    "data_v": data_v.strftime("%d/%m/%Y"),
                    # Limpa quebras de linha acidentais nos campos curtos
                    "cliente": str(cliente).replace("\n", " ").strip(),
                    "origem": str(origem).replace("\n", " ").strip(),
                    "destino": str(destino).replace("\n", " ").strip(),
                    "distancia": distancia if distancia else 0,
                    "v_frete": f"R$ {v_frete if v_frete else 0:.2f}",
                    "litros": litros if litros else 0,
                    "total_abast": f"R$ {total_final:.2f}",
                    # Preserva a organização de lista usando barras
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
                        st.error("Erro ao salvar. Verifique sua internet ou o link do script.")
                except Exception as e:
                    st.error(f"Erro de conexão: {e}")
