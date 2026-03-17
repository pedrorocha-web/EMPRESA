import streamlit as st
import pandas as pd
from datetime import datetime

# --- CONFIGURAÇÃO E DADOS SIMULADOS ---
# Em um app real, usaríamos um banco de dados (SQLite/Firebase)
if 'db_relatorios' not in st.session_state:
    st.session_state.db_relatorios = []
if 'rascunho_motorista' not in st.session_state:
    st.session_state.rascunho_motorista = {}

# --- LOGIN SIMPLIFICADO ---
st.sidebar.title("🚚 Logística App")
user_id = st.sidebar.text_input("Digite seu ID de Usuário", type="password")

# --- LÓGICA DE ACESSO ---
ID_DONO = "62322332399"
ID_MOTORISTA = "76565874204"

if user_id == ID_DONO:
    st.title("📊 Painel do Proprietário")
    st.subheader("Relatórios Recebidos dos Motoristas")
    
    if not st.session_state.db_relatorios:
        st.info("Nenhum relatório enviado hoje.")
    else:
        for i, rel in enumerate(reversed(st.session_state.db_relatorios)):
            with st.expander(f"Relatório enviado às {rel['horario']} - Dia: {rel['data_ref']}"):
                st.write("**A. Controle de Viagem:**")
                st.json(rel['viagem'])
                st.write("**B. Combustível:**")
                st.json(rel['combustivel'])
                st.write("**C. Manutenção e Diversos:**")
                st.write(rel['manutencao'])

elif user_id == ID_MOTORISTA:
    st.title("🚛 Área do Motorista")
    
    aba1, aba2 = st.tabs(["📝 Novo Formulário", "history Histórico de Envios"])

    with aba1:
        st.info("Os campos não são obrigatórios. Você pode salvar como rascunho e enviar depois.")
        
        # --- SEÇÃO A: VIAGEM ---
        with st.expander("A. Controle de Viagens", expanded=True):
            data_viagem = st.date_input("Data de Saída/Chegada")
            origem_destino = st.text_input("Origem / Destino")
            cliente = st.text_input("Cliente / Transportadora")
            frete = st.number_input("Valor Frete Bruto (R$)", min_value=0.0)
            km = st.text_input("KM Inicial / KM Final")

        # --- SEÇÃO B: COMBUSTÍVEL ---
        with st.expander("B. Gastos com Combustível"):
            posto = st.text_input("Posto")
            litros = st.number_input("Litros Abastecidos", min_value=0.0)
            vlr_litro = st.number_input("Valor por Litro (R$)", min_value=0.0)
            total_comb = litros * vlr_litro
            st.write(f"**Total Combustível: R$ {total_comb:.2f}**")

        # --- SEÇÃO C: MANUTENÇÃO E DIVERSOS ---
        with st.expander("C. Manutenção e Outras Despesas"):
            obs = st.text_area("Descreva manutenções ou gastos com alimentação/diversos")

        col1, col2 = st.columns(2)
        
        if col1.button("💾 Salvar Rascunho"):
            st.session_state.rascunho_motorista = {
                "viagem": {"origem": origem_destino, "cliente": cliente, "frete": frete, "km": km},
                "combustivel": {"posto": posto, "total": total_comb},
                "manutencao": obs
            }
            st.success("Rascunho salvo localmente!")

        if col2.button("🚀 ENVIAR AO DONO"):
            # Alerta de Confirmação
            st.warning("⚠️ Certifique-se de que todas as informações estão corretas antes de enviar.")
            
            # Novo dicionário para envio
            relatorio_final = {
                "horario": datetime.now().strftime("%H:%M:%S"),
                "data_ref": datetime.now().strftime("%d/%m/%Y"),
                "viagem": {"data": str(data_viagem), "rota": origem_destino, "cliente": cliente, "frete": frete, "km": km},
                "combustivel": {"posto": posto, "litros": litros, "vlr_un": vlr_litro, "total": total_comb},
                "manutencao": obs
            }
            
            st.session_state.db_relatorios.append(relatorio_final)
            st.balloons()
            st.success("Relatório enviado com sucesso ao proprietário!")

    with aba2:
        st.subheader("Seus envios de hoje")
        if not st.session_state.db_relatorios:
            st.write("Nenhum relatório enviado ainda.")
        else:
            for r in st.session_state.db_relatorios:
                st.write(f"✅ Enviado às {r['horario']} | Rota: {r['viagem']['rota']}")

elif user_id == "":
    st.info("Por favor, insira seu ID de acesso na barra lateral.")
else:
    st.error("Usuário não reconhecido.")