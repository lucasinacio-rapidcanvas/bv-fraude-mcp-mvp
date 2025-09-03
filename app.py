#!/usr/bin/env python3
"""
🚗 Sistema de Verificação de Fraude em Lojistas de Veículos
Interface Web usando Streamlit

Este app permite verificar a confiabilidade de lojistas de veículos
através de análise de CNPJ, reputação online e questões legais.
"""

import streamlit as st
import asyncio
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Any
import plotly.express as px
import plotly.graph_objects as go

# Importa nossa classe principal
from mvp_dealer_fraud_mcp import DealerFraudChecker

# Configuração da página
st.set_page_config(
    page_title="🚗 Verificação de Fraude - Lojistas de Veículos",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado
st.markdown("""
<style>
    .main-header {
        background: linear-gradient(90deg, #1f4e79 0%, #2d5aa0 100%);
        padding: 1rem;
        border-radius: 10px;
        color: white;
        margin-bottom: 2rem;
    }
    .metric-card {
        background: #f8f9fa;
        padding: 1rem;
        border-radius: 8px;
        border-left: 4px solid #007bff;
        margin: 0.5rem 0;
    }
    .warning-card {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .danger-card {
        background: #f8d7da;
        border: 1px solid #f1556c;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
    .success-card {
        background: #d4edda;
        border: 1px solid #7fb069;
        padding: 1rem;
        border-radius: 8px;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

# Header principal
st.markdown("""
<div class="main-header">
    <h1>🚗 Sistema de Verificação de Fraude em Lojistas</h1>
    <p>Análise completa de confiabilidade para lojistas de veículos no Brasil</p>
</div>
""", unsafe_allow_html=True)

# Inicialização do session state
if 'fraud_checker' not in st.session_state:
    # Você pode colocar sua API key aqui ou usar um input seguro
    api_key = "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"
    st.session_state.fraud_checker = DealerFraudChecker(api_key)

# Sidebar
st.sidebar.title("🔍 Configurações")
st.sidebar.markdown("---")

# Sidebar - Informações do sistema
st.sidebar.info("""
### 📋 Funcionalidades
- ✅ Validação de CNPJ
- ✅ Status oficial (Receita Federal)
- ✅ Reputação online (Reclame Aqui, Google)
- ✅ Questões legais (JusBrasil, Tribunais)
- ✅ Imagens do negócio (fachada, interior, veículos)
- ✅ Análise completa com score de risco
""")

st.sidebar.markdown("---")

# Sidebar - Score de risco
st.sidebar.markdown("""
### 📊 Score de Risco
- 🟢 **0-24**: Baixo risco
- 🟡 **25-49**: Médio risco  
- 🟠 **50-74**: Alto risco
- 🔴 **75-100**: Risco crítico
""")

# Função para executar operações async
def run_async_operation(coro):
    """Helper para executar operações assíncronas no Streamlit"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    
    return loop.run_until_complete(coro)

def display_json_pretty(data: Dict[str, Any], title: str):
    """Exibe JSON de forma organizada e bonita"""
    st.subheader(f"📄 {title}")
    
    # Cria expansor para o JSON
    with st.expander("Ver JSON Completo", expanded=False):
        st.json(data)
    
    # Exibe informações principais de forma organizada
    if "status" in data and data["status"] == "success":
        display_structured_data(data, title)
    else:
        st.error(f"❌ Erro: {data.get('error', 'Erro desconhecido')}")

def display_structured_data(data: Dict[str, Any], data_type: str):
    """Exibe dados estruturados de forma organizada"""
    
    if data_type == "Validação de CNPJ":
        col1, col2 = st.columns(2)
        with col1:
            if data.get("cnpj_valid", False):
                st.success("✅ CNPJ Válido")
            else:
                st.error("❌ CNPJ Inválido")
        with col2:
            st.info(f"**CNPJ:** {data.get('cnpj', 'N/A')}")
    
    elif data_type == "Status Oficial":
        if "company_data" in data:
            company = data["company_data"]
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("### 🏢 Dados da Empresa")
                st.write(f"**Razão Social:** {company.get('razao_social', 'N/A')}")
                st.write(f"**Nome Fantasia:** {company.get('nome_fantasia', 'N/A')}")
                st.write(f"**Situação:** {company.get('situacao_cadastral', 'N/A')}")
                st.write(f"**Data Abertura:** {company.get('data_abertura', 'N/A')}")
            
            with col2:
                st.markdown("### 💼 Informações Comerciais")
                st.write(f"**Atividade Principal:** {company.get('atividade_principal', 'N/A')}")
                st.write(f"**Capital Social:** {company.get('capital_social', 'N/A')}")
                st.write(f"**Endereço:** {company.get('endereco', 'N/A')}")
        
        # Business Profile
        if "business_profile" in data:
            profile = data["business_profile"]
            st.markdown("### 📊 Perfil do Negócio")
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.write(f"**Porte:** {profile.get('company_size', 'N/A')}")
                st.write(f"**Estrutura:** {profile.get('corporate_structure', 'N/A')}")
            with col2:
                st.write(f"**Tipo de Endereço:** {profile.get('business_address_type', 'N/A')}")
                st.write(f"**Anos no Mercado:** {profile.get('years_in_business', 'N/A')}")
            with col3:
                st.write(f"**Localização:** {profile.get('location_analysis', 'N/A')}")
        
        # Red Flags
        if data.get("red_flags"):
            st.markdown("### ⚠️ Alertas Encontrados")
            for flag in data["red_flags"]:
                st.warning(f"⚠️ {flag}")
    
    elif data_type == "Reputação Online":
        # Dealership Profile
        if "dealership_profile" in data:
            profile = data["dealership_profile"]
            st.markdown("### 🏪 Perfil da Loja")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Tamanho", profile.get('size', 'N/A'))
            with col2:
                st.metric("Segmento", profile.get('segment', 'N/A'))
            with col3:
                st.metric("Localização", profile.get('location_type', 'N/A'))
            with col4:
                st.metric("Público", profile.get('target_audience', 'N/A'))
            
            if profile.get('price_range', 'N/A') != 'N/A':
                st.write(f"**Faixa de Preços:** {profile.get('price_range', 'N/A')}")
        
        # Reclame Aqui
        if "reclame_aqui" in data and data["reclame_aqui"].get("nota", "N/A") != "N/A":
            st.markdown("### 📝 Reclame Aqui")
            reclame = data["reclame_aqui"]
            
            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Nota", reclame.get("nota", "N/A"))
            with col2:
                st.metric("Total Reclamações", reclame.get("total_reclamacoes", "N/A"))
            with col3:
                st.metric("Taxa Resposta", reclame.get("reclamacoes_respondidas", "N/A"))
            
            if reclame.get("principais_problemas"):
                st.write("**Principais Problemas:**")
                for problema in reclame["principais_problemas"]:
                    st.write(f"• {problema}")
        
        # Google Reviews
        if "google_reviews" in data and data["google_reviews"].get("nota", "N/A") != "N/A":
            st.markdown("### ⭐ Google Reviews")
            google = data["google_reviews"]
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Nota Google", google.get("nota", "N/A"))
            with col2:
                st.metric("Total Avaliações", google.get("total_avaliacoes", "N/A"))
        
        # Score e Red Flags
        col1, col2 = st.columns(2)
        with col1:
            score = data.get("reputation_score", "N/A")
            if score != "N/A" and str(score).isdigit():
                score_int = int(score)
                if score_int < 25:
                    st.success(f"🟢 Score: {score}/100 (Baixo Risco)")
                elif score_int < 50:
                    st.warning(f"🟡 Score: {score}/100 (Médio Risco)")
                elif score_int < 75:
                    st.warning(f"🟠 Score: {score}/100 (Alto Risco)")
                else:
                    st.error(f"🔴 Score: {score}/100 (Risco Crítico)")
            else:
                st.info(f"📊 Score: {score}")
        
        with col2:
            if data.get("red_flags"):
                st.markdown("**🚩 Red Flags:**")
                for flag in data["red_flags"]:
                    st.write(f"• {flag}")
    
    elif data_type == "Questões Legais":
        if "legal_issues" in data:
            issues = data["legal_issues"]
            st.markdown("### ⚖️ Processos Encontrados")
            
            col1, col2 = st.columns(2)
            with col1:
                st.write(f"**Criminais:** {len(issues.get('criminal_processes', []))}")
                st.write(f"**Cíveis:** {len(issues.get('civil_processes', []))}")
            with col2:
                st.write(f"**Trabalhistas:** {len(issues.get('labor_processes', []))}")
                st.write(f"**Administrativos:** {len(issues.get('administrative_processes', []))}")
        
        risk_level = data.get("risk_level", "N/A")
        if risk_level == "BAIXO":
            st.success(f"✅ Risco Legal: {risk_level}")
        elif risk_level == "MÉDIO":
            st.warning(f"⚠️ Risco Legal: {risk_level}")
        elif risk_level == "ALTO":
            st.error(f"🚨 Risco Legal: {risk_level}")
        elif risk_level == "CRÍTICO":
            st.error(f"🚫 Risco Legal: {risk_level}")
        else:
            st.info(f"📊 Risco Legal: {risk_level}")
    
    elif data_type == "Imagens do Negócio":
        if "business_images" in data:
            images = data["business_images"]
            st.markdown("### 🖼️ Imagens Encontradas")
            
            # Organizar imagens em grid
            image_types = [
                ("facade", "🏪 Fachada", images.get("facade", {})),
                ("logo", "🎨 Logotipo", images.get("logo", {})),
                ("interior", "🏢 Interior", images.get("interior", {})),
                ("staff", "👥 Equipe", images.get("staff", {})),
                ("vehicles", "🚗 Veículos", images.get("vehicles", {})),
                ("location", "📍 Localização", images.get("location", {}))
            ]
            
            # Exibir imagens em grid 2x3
            for i in range(0, len(image_types), 3):
                cols = st.columns(3)
                for j in range(3):
                    if i + j < len(image_types):
                        img_key, img_title, img_data = image_types[i + j]
                        with cols[j]:
                            st.subheader(img_title)
                            
                            url = img_data.get("url", "N/A")
                            description = img_data.get("description", "N/A")
                            source = img_data.get("source", "N/A")
                            verified = img_data.get("verified", False)
                            
                            if url and url != "N/A" and url.startswith(("http://", "https://")):
                                try:
                                    st.image(url, caption=description, use_column_width=True)
                                    if verified:
                                        st.success("✅ Verificada")
                                    else:
                                        st.warning("⚠️ Não verificada")
                                    st.caption(f"Fonte: {source}")
                                except:
                                    st.error(f"❌ Erro ao carregar imagem")
                                    st.write(f"**URL:** {url}")
                                    st.write(f"**Descrição:** {description}")
                                    st.caption(f"Fonte: {source}")
                            else:
                                st.info("📷 Imagem não encontrada")
                                if description != "N/A":
                                    st.write(f"**Descrição:** {description}")
                                if source != "N/A":
                                    st.caption(f"Fonte: {source}")
        
        # Análise das imagens
        if "image_analysis" in data:
            analysis = data["image_analysis"]
            st.markdown("### 📊 Análise Visual")
            
            col1, col2, col3, col4 = st.columns(4)
            with col1:
                st.metric("Total Encontradas", analysis.get("total_images_found", 0))
            with col2:
                st.metric("Verificadas", analysis.get("verified_images", 0))
            with col3:
                consistency = analysis.get("visual_consistency", "N/A")
                if consistency == "ALTA":
                    st.success(f"✅ {consistency}")
                elif consistency == "MÉDIA":
                    st.warning(f"⚠️ {consistency}")
                elif consistency == "BAIXA":
                    st.error(f"❌ {consistency}")
                else:
                    st.info(f"📊 {consistency}")
            with col4:
                appearance = analysis.get("business_appearance", "N/A")
                if appearance == "PROFISSIONAL":
                    st.success(f"✅ {appearance}")
                elif appearance == "BÁSICO":
                    st.warning(f"⚠️ {appearance}")
                elif appearance == "DUVIDOSO":
                    st.error(f"❌ {appearance}")
                else:
                    st.info(f"📊 {appearance}")
            
            # Indicadores positivos
            if analysis.get("legitimacy_indicators"):
                st.markdown("**✅ Indicadores Positivos:**")
                for indicator in analysis["legitimacy_indicators"]:
                    st.write(f"• {indicator}")
            
            # Red flags visuais
            if analysis.get("red_flags"):
                st.markdown("**🚩 Red Flags Visuais:**")
                for flag in analysis["red_flags"]:
                    st.write(f"• {flag}")
        
        # Presença nas redes sociais
        if "social_media_presence" in data:
            social = data["social_media_presence"]
            st.markdown("### 📱 Redes Sociais")
            
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("#### Instagram")
                insta = social.get("instagram", {})
                if insta.get("url", "N/A") != "N/A":
                    st.write(f"**Perfil:** [Ver Instagram]({insta['url']})")
                    st.write(f"**Seguidores:** {insta.get('followers', 'N/A')}")
                    st.write(f"**Posts:** {insta.get('posts', 'N/A')}")
                    activity = insta.get("recent_activity", "N/A")
                    if activity == "ATIVO":
                        st.success(f"✅ {activity}")
                    elif activity == "INATIVO":
                        st.error(f"❌ {activity}")
                    else:
                        st.info(f"📊 {activity}")
                else:
                    st.info("📱 Instagram não encontrado")
            
            with col2:
                st.markdown("#### Facebook")
                fb = social.get("facebook", {})
                if fb.get("url", "N/A") != "N/A":
                    st.write(f"**Página:** [Ver Facebook]({fb['url']})")
                    st.write(f"**Curtidas:** {fb.get('likes', 'N/A')}")
                    st.write(f"**Avaliações:** {fb.get('reviews', 'N/A')}")
                    activity = fb.get("recent_activity", "N/A")
                    if activity == "ATIVO":
                        st.success(f"✅ {activity}")
                    elif activity == "INATIVO":
                        st.error(f"❌ {activity}")
                    else:
                        st.info(f"📊 {activity}")
                else:
                    st.info("📘 Facebook não encontrado")

# Interface principal
st.markdown("## 🔍 Verificação de Lojista")

# Input do CNPJ
col1, col2 = st.columns([3, 1])
with col1:
    cnpj_input = st.text_input(
        "Digite o CNPJ do lojista:",
        placeholder="00.000.000/0000-00",
        help="Digite o CNPJ com ou sem formatação"
    )

with col2:
    company_name = st.text_input(
        "Nome da empresa (opcional):",
        placeholder="Ex: AutoCenter Premium"
    )

# Botões de ação
st.markdown("### 🎯 Escolha o tipo de verificação:")

col1, col2, col3, col4, col5 = st.columns(5)

with col1:
    if st.button("✅ Validar CNPJ", use_container_width=True):
        if cnpj_input:
            with st.spinner("Validando CNPJ..."):
                checker = st.session_state.fraud_checker
                is_valid = checker._validate_cnpj(cnpj_input)
                formatted = checker._format_cnpj(cnpj_input)
                
                result = {
                    "cnpj": formatted,
                    "cnpj_valid": is_valid,
                    "status": "success",
                    "query_date": datetime.now().isoformat()
                }
                
                display_json_pretty(result, "Validação de CNPJ")
        else:
            st.error("⚠️ Por favor, digite um CNPJ")

with col2:
    if st.button("🏢 Status Oficial", use_container_width=True):
        if cnpj_input:
            with st.spinner("Consultando status oficial..."):
                checker = st.session_state.fraud_checker
                result = run_async_operation(
                    checker.verify_cnpj_status(cnpj_input)
                )
                display_json_pretty(result, "Status Oficial")
        else:
            st.error("⚠️ Por favor, digite um CNPJ")

with col3:
    if st.button("⭐ Reputação", use_container_width=True):
        if cnpj_input:
            with st.spinner("Verificando reputação online..."):
                checker = st.session_state.fraud_checker
                result = run_async_operation(
                    checker.check_dealer_reputation(cnpj_input, company_name)
                )
                display_json_pretty(result, "Reputação Online")
        else:
            st.error("⚠️ Por favor, digite um CNPJ")

with col4:
    if st.button("⚖️ Questões Legais", use_container_width=True):
        if cnpj_input:
            with st.spinner("Verificando questões legais..."):
                checker = st.session_state.fraud_checker
                result = run_async_operation(
                    checker.check_legal_issues(cnpj_input, company_name)
                )
                display_json_pretty(result, "Questões Legais")
        else:
            st.error("⚠️ Por favor, digite um CNPJ")

with col5:
    if st.button("🖼️ Imagens", use_container_width=True):
        if cnpj_input:
            with st.spinner("Buscando imagens do negócio..."):
                checker = st.session_state.fraud_checker
                result = run_async_operation(
                    checker.search_business_images(cnpj_input, company_name)
                )
                display_json_pretty(result, "Imagens do Negócio")
        else:
            st.error("⚠️ Por favor, digite um CNPJ")

# Botão de análise completa
st.markdown("---")
if st.button("🔍 ANÁLISE COMPLETA", use_container_width=True, type="primary"):
    if cnpj_input:
        with st.spinner("Executando análise completa... Isso pode levar alguns minutos."):
            checker = st.session_state.fraud_checker
            result = run_async_operation(
                checker.comprehensive_check(cnpj_input, company_name)
            )
            
            st.markdown("## 📊 Resultado da Análise Completa")
            
            # Exibe informações básicas
            st.info(f"**CNPJ:** {result.get('cnpj', 'N/A')} | **Empresa:** {result.get('company_name', 'N/A')}")
            
            # Análise de risco
            if "risk_analysis" in result:
                risk = result["risk_analysis"]
                
                col1, col2, col3 = st.columns(3)
                with col1:
                    score = risk.get("risk_score", 0)
                    if score < 25:
                        st.success(f"🟢 Score: {score}/100")
                    elif score < 50:
                        st.warning(f"🟡 Score: {score}/100")
                    elif score < 75:
                        st.warning(f"🟠 Score: {score}/100")
                    else:
                        st.error(f"🔴 Score: {score}/100")
                
                with col2:
                    level = risk.get("risk_level", "N/A")
                    if level == "BAIXO":
                        st.success(f"✅ {level}")
                    elif level == "MÉDIO":
                        st.warning(f"⚠️ {level}")
                    else:
                        st.error(f"🚨 {level}")
                
                with col3:
                    recommendation = risk.get("recommendation", "N/A")
                    st.info(f"📋 {recommendation}")
                
                # Próximos passos
                if risk.get("next_steps"):
                    st.markdown("### 📝 Próximos Passos Recomendados:")
                    for i, step in enumerate(risk["next_steps"], 1):
                        st.write(f"{i}. {step}")
            
            # Exibe cada verificação
            if "checks_performed" in result:
                checks = result["checks_performed"]
                
                st.markdown("### 📋 Detalhes das Verificações:")
                
                # Tabs para cada verificação
                tab1, tab2, tab3, tab4 = st.tabs(["🏢 Status", "⭐ Reputação", "⚖️ Legal", "🖼️ Imagens"])
                
                with tab1:
                    if "cnpj_status" in checks:
                        display_structured_data(checks["cnpj_status"], "Status Oficial")
                
                with tab2:
                    if "reputation" in checks:
                        display_structured_data(checks["reputation"], "Reputação Online")
                
                with tab3:
                    if "legal_issues" in checks:
                        display_structured_data(checks["legal_issues"], "Questões Legais")
                
                with tab4:
                    if "business_images" in checks:
                        display_structured_data(checks["business_images"], "Imagens do Negócio")
            
            # JSON completo
            with st.expander("📄 Ver JSON Completo da Análise", expanded=False):
                st.json(result)
    else:
        st.error("⚠️ Por favor, digite um CNPJ")

def main():
    """
    Função principal do aplicativo Streamlit.
    Esta função é chamada pelo entry.py para iniciar a aplicação.
    """
    pass

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem;'>
    <p>🚗 Sistema de Verificação de Fraude em Lojistas v1.0</p>
    <p>Desenvolvido com OpenAI Responses API | Dados em tempo real via web search</p>
</div>
""", unsafe_allow_html=True)

# Executa a aplicação se for chamado diretamente
if __name__ == "__main__":
    main()