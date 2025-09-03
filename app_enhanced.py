#!/usr/bin/env python3
"""
🚗 Sistema Avançado de Verificação de Fraude em Lojistas de Veículos
Interface Web Aprimorada usando Streamlit com visualizações detalhadas
"""

import streamlit as st
import asyncio
import json
import pandas as pd
from datetime import datetime
from typing import Dict, Any, List
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots

# Importa nossa classe principal
from mvp_dealer_fraud_mcp import DealerFraudChecker

# Configuração da página
st.set_page_config(
    page_title="🚗 Verificação de Fraude - Lojistas de Veículos",
    page_icon="🚗",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS customizado aprimorado
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
    
    * {
        font-family: 'Inter', sans-serif;
    }
    
    .main-header {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 2rem;
        border-radius: 15px;
        color: white;
        margin-bottom: 2rem;
        box-shadow: 0 10px 30px rgba(0,0,0,0.1);
    }
    
    .main-header h1 {
        font-size: 2.5rem;
        font-weight: 700;
        margin-bottom: 0.5rem;
    }
    
    .metric-card {
        background: white;
        padding: 1.5rem;
        border-radius: 12px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.07);
        border-left: 4px solid #667eea;
        margin: 1rem 0;
        transition: transform 0.2s;
    }
    
    .metric-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 6px 12px rgba(0,0,0,0.1);
    }
    
    .info-card {
        background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%);
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
    }
    
    .warning-card {
        background: linear-gradient(135deg, #fff3cd 0%, #ffeaa7 100%);
        border: 1px solid #ffc107;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(255, 193, 7, 0.2);
    }
    
    .danger-card {
        background: linear-gradient(135deg, #f8d7da 0%, #f5c6cb 100%);
        border: 1px solid #dc3545;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(220, 53, 69, 0.2);
    }
    
    .success-card {
        background: linear-gradient(135deg, #d4edda 0%, #c3e6cb 100%);
        border: 1px solid #28a745;
        padding: 1.5rem;
        border-radius: 12px;
        margin: 1rem 0;
        box-shadow: 0 4px 6px rgba(40, 167, 69, 0.2);
    }
    
    .detail-section {
        background: white;
        padding: 2rem;
        border-radius: 12px;
        margin: 1.5rem 0;
        box-shadow: 0 4px 6px rgba(0,0,0,0.07);
    }
    
    .detail-section h3 {
        color: #2d3748;
        margin-bottom: 1.5rem;
        padding-bottom: 0.5rem;
        border-bottom: 2px solid #667eea;
    }
    
    .data-table {
        background: white;
        border-radius: 8px;
        overflow: hidden;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
    }
    
    .risk-badge {
        display: inline-block;
        padding: 0.5rem 1rem;
        border-radius: 20px;
        font-weight: 600;
        text-align: center;
    }
    
    .risk-low { background: #d4edda; color: #155724; }
    .risk-medium { background: #fff3cd; color: #856404; }
    .risk-high { background: #f8d7da; color: #721c24; }
    .risk-critical { background: #721c24; color: white; }
    
    .stat-number {
        font-size: 2rem;
        font-weight: 700;
        color: #667eea;
    }
    
    .stat-label {
        color: #718096;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.05em;
    }
</style>
""", unsafe_allow_html=True)

# Header principal
st.markdown("""
<div class="main-header">
    <h1>🚗 Sistema Avançado de Verificação de Fraude</h1>
    <p style="font-size: 1.2rem;">Análise completa e detalhada de confiabilidade para lojistas de veículos no Brasil</p>
    <p style="font-size: 0.9rem; opacity: 0.9;">Powered by OpenAI GPT-4o com busca web em tempo real</p>
</div>
""", unsafe_allow_html=True)

# Inicialização do session state
if 'fraud_checker' not in st.session_state:
    api_key = "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"
    st.session_state.fraud_checker = DealerFraudChecker(api_key)

if 'analysis_results' not in st.session_state:
    st.session_state.analysis_results = {}

# Função para executar operações async
def run_async_operation(coro):
    """Helper para executar operações assíncronas no Streamlit"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# Função para criar gráfico de gauge para score
def create_gauge_chart(value, title="Score"):
    """Cria um gráfico de gauge para mostrar scores"""
    fig = go.Figure(go.Indicator(
        mode = "gauge+number+delta",
        value = value,
        domain = {'x': [0, 1], 'y': [0, 1]},
        title = {'text': title, 'font': {'size': 20}},
        gauge = {
            'axis': {'range': [None, 100], 'tickwidth': 1, 'tickcolor': "darkblue"},
            'bar': {'color': "darkblue"},
            'bgcolor': "white",
            'borderwidth': 2,
            'bordercolor': "gray",
            'steps': [
                {'range': [0, 25], 'color': '#d4edda'},
                {'range': [25, 50], 'color': '#fff3cd'},
                {'range': [50, 75], 'color': '#f8d7da'},
                {'range': [75, 100], 'color': '#721c24'}
            ],
            'threshold': {
                'line': {'color': "red", 'width': 4},
                'thickness': 0.75,
                'value': 90
            }
        }
    ))
    fig.update_layout(height=250, margin=dict(l=20, r=20, t=40, b=20))
    return fig

# Função para exibir dados detalhados de forma estruturada
def display_detailed_data(data: Dict[str, Any], data_type: str):
    """Exibe dados de forma muito mais detalhada e organizada"""
    
    if data_type == "Status Oficial":
        st.markdown("### 🏢 Informações Oficiais da Empresa")
        
        # Criar colunas para informações básicas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### 📋 Dados Cadastrais")
            st.write(f"**Razão Social:** {data.get('razao_social', 'N/A')}")
            st.write(f"**Nome Fantasia:** {data.get('nome_fantasia', 'N/A')}")
            st.write(f"**CNPJ:** {data.get('cnpj', 'N/A')}")
            st.write(f"**Data Abertura:** {data.get('data_abertura', 'N/A')}")
            st.write(f"**Anos em Funcionamento:** {data.get('anos_funcionamento', 'N/A')}")
        
        with col2:
            st.markdown("#### 💼 Informações Empresariais")
            st.write(f"**Situação Cadastral:** {data.get('situacao_cadastral', 'N/A')}")
            st.write(f"**Capital Social:** {data.get('capital_social', 'N/A')}")
            st.write(f"**Porte:** {data.get('porte_empresa', 'N/A')}")
            st.write(f"**CNAE Principal:** {data.get('atividade_principal', 'N/A')}")
            st.write(f"**CNAE Adequado:** {data.get('adequacao_cnae', 'N/A')}")
        
        with col3:
            st.markdown("#### 📍 Localização")
            st.write(f"**Endereço:** {data.get('endereco', 'N/A')}")
            
            # Sócios
            if data.get('socios'):
                st.markdown("#### 👥 Quadro Societário")
                for socio in data['socios']:
                    st.write(f"• {socio}")
        
        # Status Summary
        if data.get('status_summary'):
            st.markdown("#### 📊 Resumo da Situação")
            st.info(data['status_summary'])
        
        # Red Flags
        if data.get('red_flags') and len(data['red_flags']) > 0:
            st.markdown("#### 🚩 Alertas Identificados")
            for flag in data['red_flags']:
                st.error(f"⚠️ {flag}")
    
    elif data_type == "Reputação Online":
        st.markdown("### ⭐ Análise Detalhada de Reputação")
        
        # Score de reputação com gauge
        if data.get('reputation_score', 'N/A') != 'N/A':
            try:
                score = int(data['reputation_score'])
                col1, col2 = st.columns([1, 2])
                with col1:
                    fig = create_gauge_chart(score, "Score de Reputação")
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    st.markdown("#### 📊 Resumo da Reputação")
                    st.write(data.get('reputation_summary', 'N/A'))
            except:
                st.info(f"Score de Reputação: {data.get('reputation_score', 'N/A')}")
        
        # Métricas detalhadas
        st.markdown("#### 📈 Métricas de Avaliação")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            score_ra = data.get('reclame_aqui_score', 'N/A')
            if score_ra != 'N/A':
                st.metric("Reclame Aqui", score_ra, delta=None)
            else:
                st.metric("Reclame Aqui", "N/A")
        
        with col2:
            google_rating = data.get('google_rating', 'N/A')
            if google_rating != 'N/A':
                st.metric("Google Rating", f"⭐ {google_rating}")
            else:
                st.metric("Google Rating", "N/A")
        
        with col3:
            complaints = data.get('complaint_count', 'N/A')
            st.metric("Total Reclamações", complaints)
        
        with col4:
            business_size = data.get('business_size', 'N/A')
            st.metric("Porte", business_size.upper() if business_size != 'N/A' else 'N/A')
        
        # Problemas principais
        if data.get('main_issues') and len(data['main_issues']) > 0:
            st.markdown("#### 🔍 Principais Problemas Reportados")
            cols = st.columns(2)
            for i, issue in enumerate(data['main_issues']):
                with cols[i % 2]:
                    st.warning(f"• {issue}")
        
        # Red flags
        if data.get('red_flags') and len(data['red_flags']) > 0:
            st.markdown("#### 🚨 Alertas Críticos")
            for flag in data['red_flags']:
                st.error(f"⚠️ {flag}")
        
        # Fontes consultadas
        if data.get('sources_checked'):
            st.markdown("#### 📚 Fontes Consultadas")
            sources_str = " | ".join(data['sources_checked'])
            st.success(f"✅ {sources_str}")
    
    elif data_type == "Questões Legais":
        st.markdown("### ⚖️ Análise Legal Detalhada")
        
        # Risk Level com visual destacado
        risk_level = data.get('risk_level', 'N/A')
        if risk_level != 'N/A':
            col1, col2 = st.columns([1, 3])
            with col1:
                if risk_level == "BAIXO":
                    st.markdown('<div class="risk-badge risk-low">RISCO BAIXO</div>', unsafe_allow_html=True)
                elif risk_level == "MÉDIO":
                    st.markdown('<div class="risk-badge risk-medium">RISCO MÉDIO</div>', unsafe_allow_html=True)
                elif risk_level == "ALTO":
                    st.markdown('<div class="risk-badge risk-high">RISCO ALTO</div>', unsafe_allow_html=True)
                elif risk_level == "CRÍTICO":
                    st.markdown('<div class="risk-badge risk-critical">RISCO CRÍTICO</div>', unsafe_allow_html=True)
            with col2:
                st.write(data.get('legal_summary', 'N/A'))
        
        # Processos detalhados
        st.markdown("#### 📑 Processos e Investigações")
        
        process_data = {
            'Tipo': [],
            'Quantidade': [],
            'Detalhes': []
        }
        
        # Processos criminais
        criminal = data.get('criminal_cases', [])
        if criminal:
            for case in criminal:
                process_data['Tipo'].append('Criminal')
                process_data['Quantidade'].append(1)
                process_data['Detalhes'].append(case)
        
        # Processos cíveis
        civil = data.get('civil_cases', [])
        if civil:
            for case in civil:
                process_data['Tipo'].append('Cível')
                process_data['Quantidade'].append(1)
                process_data['Detalhes'].append(case)
        
        # Investigações
        investigations = data.get('investigations', [])
        if investigations:
            for inv in investigations:
                process_data['Tipo'].append('Investigação')
                process_data['Quantidade'].append(1)
                process_data['Detalhes'].append(inv)
        
        # Sanções
        sanctions = data.get('sanctions', [])
        if sanctions:
            for sanction in sanctions:
                process_data['Tipo'].append('Sanção/Multa')
                process_data['Quantidade'].append(1)
                process_data['Detalhes'].append(sanction)
        
        if process_data['Tipo']:
            df = pd.DataFrame(process_data)
            
            # Gráfico de processos
            fig = px.bar(df.groupby('Tipo').size().reset_index(name='Quantidade'), 
                        x='Tipo', y='Quantidade',
                        color='Tipo',
                        title='Distribuição de Processos e Sanções')
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela detalhada
            st.markdown("##### 📋 Detalhamento Completo")
            for _, row in df.iterrows():
                tipo_emoji = {
                    'Criminal': '🚔',
                    'Cível': '⚖️',
                    'Investigação': '🔍',
                    'Sanção/Multa': '💰'
                }.get(row['Tipo'], '📄')
                
                # Use container instead of nested expander
                st.markdown(f"**{tipo_emoji} {row['Tipo']}:**")
                st.write(row['Detalhes'])
                st.markdown("---")
        
        # Indicadores de fraude
        if data.get('fraud_indicators') and len(data['fraud_indicators']) > 0:
            st.markdown("#### 🚨 Indicadores de Fraude")
            for indicator in data['fraud_indicators']:
                st.error(f"⚠️ {indicator}")
        
        # Fontes consultadas
        if data.get('sources_found'):
            st.markdown("#### 📚 Fontes Legais Consultadas")
            cols = st.columns(3)
            for i, source in enumerate(data['sources_found']):
                with cols[i % 3]:
                    st.info(f"📌 {source}")

# Sidebar aprimorado
with st.sidebar:
    st.markdown("### 🎯 Análise Rápida")
    
    # Input do CNPJ na sidebar
    cnpj_sidebar = st.text_input(
        "CNPJ para análise rápida:",
        placeholder="00.000.000/0000-00",
        key="sidebar_cnpj"
    )
    
    if st.button("🚀 Análise Express", use_container_width=True):
        if cnpj_sidebar:
            with st.spinner("Executando análise express..."):
                checker = st.session_state.fraud_checker
                
                # Validação rápida
                is_valid = checker._validate_cnpj(cnpj_sidebar)
                if is_valid:
                    # Busca reputação rapidamente
                    result = run_async_operation(
                        checker.check_dealer_reputation(cnpj_sidebar)
                    )
                    
                    if result.get('reputation_score', 'N/A') != 'N/A':
                        try:
                            score = int(result['reputation_score'])
                            if score < 50:
                                st.success(f"✅ Score: {score}/100 - Baixo risco")
                            elif score < 75:
                                st.warning(f"⚠️ Score: {score}/100 - Risco moderado")
                            else:
                                st.error(f"🚨 Score: {score}/100 - Alto risco")
                        except:
                            st.info("Análise completa necessária")
                else:
                    st.error("❌ CNPJ inválido")
    
    st.markdown("---")
    
    # Estatísticas da sessão
    st.markdown("### 📊 Estatísticas da Sessão")
    if st.session_state.analysis_results:
        st.metric("Análises Realizadas", len(st.session_state.analysis_results))
        
        # Calcular média de risco
        risk_scores = []
        for result in st.session_state.analysis_results.values():
            if isinstance(result, dict) and 'reputation_score' in result:
                try:
                    risk_scores.append(int(result['reputation_score']))
                except:
                    pass
        
        if risk_scores:
            avg_risk = sum(risk_scores) / len(risk_scores)
            st.metric("Risco Médio", f"{avg_risk:.1f}/100")
    
    st.markdown("---")
    
    # Legenda de cores
    st.markdown("### 🎨 Legenda de Cores")
    st.markdown("""
    <div style='padding: 0.5rem; background: #d4edda; border-radius: 5px; margin: 0.2rem 0;'>🟢 Baixo Risco (0-24)</div>
    <div style='padding: 0.5rem; background: #fff3cd; border-radius: 5px; margin: 0.2rem 0;'>🟡 Médio Risco (25-49)</div>
    <div style='padding: 0.5rem; background: #f8d7da; border-radius: 5px; margin: 0.2rem 0;'>🟠 Alto Risco (50-74)</div>
    <div style='padding: 0.5rem; background: #721c24; color: white; border-radius: 5px; margin: 0.2rem 0;'>🔴 Crítico (75-100)</div>
    """, unsafe_allow_html=True)
    
    st.markdown("---")
    
    # Informações do sistema
    st.markdown("### ℹ️ Sobre o Sistema")
    st.info("""
    **Versão:** 2.0 Enhanced
    **API:** OpenAI GPT-4o
    **Busca:** Web Search
    **Atualização:** Tempo Real
    """)
    
    # Custos da API
    if 'fraud_checker' in st.session_state:
        checker = st.session_state.fraud_checker
        cost_summary = checker.get_cost_summary()
        
        if cost_summary['total_cost_usd'] > 0:
            st.markdown("### 💰 Custos da API")
            
            col1, col2 = st.columns(2)
            with col1:
                st.metric("Custo Total", f"${cost_summary['total_cost_usd']:.4f}")
                st.metric("Requisições", cost_summary['total_requests'])
            
            with col2:
                st.metric("Tokens Totais", f"{cost_summary['total_tokens']:,}")
                st.metric("Custo Médio", f"${cost_summary['average_cost_per_request']:.4f}")
            
            # Custos por modelo
            if cost_summary['cost_by_model']:
                st.markdown("#### 📊 Custos por Modelo")
                for model, data in cost_summary['cost_by_model'].items():
                    st.write(f"**{model}**: ${data['cost']:.4f} ({data['requests']} requests, {data['tokens']:,} tokens)")
            
            if st.button("🔄 Reset Custos", key="reset_costs"):
                checker.reset_cost_tracking()
                st.success("Custos resetados!")

# Interface principal
st.markdown("## 🔍 Central de Verificação")

# Abas para diferentes modos
tab1, tab2, tab3 = st.tabs(["🎯 Verificação Individual", "📊 Análise Comparativa", "📈 Dashboard"])

with tab1:
    # Input principal
    col1, col2, col3 = st.columns([3, 2, 1])
    with col1:
        cnpj_input = st.text_input(
            "CNPJ do Lojista:",
            placeholder="00.000.000/0000-00",
            help="Digite o CNPJ com ou sem formatação"
        )
    
    with col2:
        company_name = st.text_input(
            "Nome da Empresa (opcional):",
            placeholder="Ex: Auto Center Premium",
            help="Melhora a precisão da busca"
        )
    
    with col3:
        st.markdown("<br>", unsafe_allow_html=True)
        analyze_all = st.checkbox("Análise Completa", value=True)
    
    # Botões de ação organizados
    st.markdown("### 🎯 Selecione as Verificações")
    
    col1, col2, col3, col4, col5, col6 = st.columns(6)
    
    checks_to_perform = {}
    
    with col1:
        checks_to_perform['validate'] = st.checkbox("✅ Validar CNPJ", value=True)
    with col2:
        checks_to_perform['status'] = st.checkbox("🏢 Status Oficial", value=True)
    with col3:
        checks_to_perform['reputation'] = st.checkbox("⭐ Reputação", value=True)
    with col4:
        checks_to_perform['legal'] = st.checkbox("⚖️ Legal", value=True)
    with col5:
        checks_to_perform['images'] = st.checkbox("🖼️ Imagens", value=False)
    with col6:
        checks_to_perform['complete'] = st.checkbox("🔍 Completa", value=False)
    
    # Botão principal de execução
    if st.button("🚀 EXECUTAR ANÁLISE", use_container_width=True, type="primary"):
        if cnpj_input:
            checker = st.session_state.fraud_checker
            
            # Container para resultados
            results_container = st.container()
            
            with results_container:
                st.markdown("## 📊 Resultados da Análise")
                
                # Validação
                if checks_to_perform['validate']:
                    with st.spinner("Validando CNPJ..."):
                        is_valid = checker._validate_cnpj(cnpj_input)
                        formatted = checker._format_cnpj(cnpj_input)
                        
                        if is_valid:
                            st.success(f"✅ CNPJ Válido: {formatted}")
                        else:
                            st.error(f"❌ CNPJ Inválido: {cnpj_input}")
                            st.stop()
                
                # Status Oficial
                if checks_to_perform['status']:
                    with st.spinner("📋 Consultando situação oficial..."):
                        result = run_async_operation(
                            checker.verify_cnpj_status(cnpj_input)
                        )
                        st.session_state.analysis_results[f"{cnpj_input}_status"] = result
                        
                        with st.expander("🏢 Status Oficial da Empresa", expanded=True):
                            display_detailed_data(result, "Status Oficial")
                
                # Reputação
                if checks_to_perform['reputation']:
                    with st.spinner("⭐ Analisando reputação online..."):
                        result = run_async_operation(
                            checker.check_dealer_reputation(cnpj_input, company_name)
                        )
                        st.session_state.analysis_results[f"{cnpj_input}_reputation"] = result
                        
                        with st.expander("⭐ Análise de Reputação", expanded=True):
                            display_detailed_data(result, "Reputação Online")
                
                # Questões Legais
                if checks_to_perform['legal']:
                    with st.spinner("⚖️ Verificando questões legais..."):
                        result = run_async_operation(
                            checker.check_legal_issues(cnpj_input, company_name)
                        )
                        st.session_state.analysis_results[f"{cnpj_input}_legal"] = result
                        
                        with st.expander("⚖️ Questões Legais e Processos", expanded=True):
                            display_detailed_data(result, "Questões Legais")
                
                # Análise Completa
                if checks_to_perform['complete'] or analyze_all:
                    with st.spinner("🔍 Executando análise completa detalhada..."):
                        result = run_async_operation(
                            checker.comprehensive_check(cnpj_input, company_name)
                        )
                        st.session_state.analysis_results[f"{cnpj_input}_complete"] = result
                        
                        # Análise de risco consolidada
                        if "risk_analysis" in result:
                            st.markdown("### 🎯 Análise de Risco Consolidada")
                            risk = result["risk_analysis"]
                            
                            col1, col2, col3 = st.columns(3)
                            
                            with col1:
                                score = risk.get("risk_score", 0)
                                fig = create_gauge_chart(score, "Score de Risco")
                                st.plotly_chart(fig, use_container_width=True)
                            
                            with col2:
                                st.markdown("#### 📊 Nível de Risco")
                                level = risk.get("risk_level", "N/A")
                                if level == "BAIXO":
                                    st.markdown('<div class="success-card"><h2>✅ BAIXO</h2></div>', unsafe_allow_html=True)
                                elif level == "MÉDIO":
                                    st.markdown('<div class="warning-card"><h2>⚠️ MÉDIO</h2></div>', unsafe_allow_html=True)
                                elif level == "ALTO":
                                    st.markdown('<div class="warning-card"><h2>🟠 ALTO</h2></div>', unsafe_allow_html=True)
                                else:
                                    st.markdown('<div class="danger-card"><h2>🔴 CRÍTICO</h2></div>', unsafe_allow_html=True)
                            
                            with col3:
                                st.markdown("#### 💡 Recomendação")
                                st.info(risk.get("recommendation", "N/A"))
                            
                            # Fatores de risco
                            if risk.get("risk_factors"):
                                st.markdown("#### 🚨 Fatores de Risco Identificados")
                                for factor in risk["risk_factors"]:
                                    st.warning(f"• {factor}")
                            
                            # Próximos passos
                            if risk.get("next_steps"):
                                st.markdown("#### ✅ Próximos Passos Recomendados")
                                for i, step in enumerate(risk["next_steps"], 1):
                                    st.success(f"{i}. {step}")
                
                # Botão para baixar relatório
                st.markdown("---")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("💾 Salvar Relatório JSON", use_container_width=True):
                        # Consolidar todos os resultados
                        full_report = {
                            "cnpj": cnpj_input,
                            "company_name": company_name,
                            "analysis_date": datetime.now().isoformat(),
                            "results": st.session_state.analysis_results
                        }
                        st.download_button(
                            label="📥 Baixar JSON",
                            data=json.dumps(full_report, indent=2, ensure_ascii=False),
                            file_name=f"analise_{cnpj_input}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                            mime="application/json"
                        )
                
                with col2:
                    if st.button("🔄 Nova Análise", use_container_width=True):
                        st.rerun()
        
        else:
            st.error("⚠️ Por favor, digite um CNPJ válido")

with tab2:
    st.markdown("### 📊 Análise Comparativa de Múltiplos CNPJs")
    
    # Textarea para múltiplos CNPJs
    cnpjs_text = st.text_area(
        "Digite os CNPJs (um por linha):",
        height=150,
        placeholder="11.222.333/0001-81\n44.555.666/0001-92\n77.888.999/0001-03"
    )
    
    if st.button("🔍 Analisar Todos", use_container_width=True):
        if cnpjs_text:
            cnpjs = [line.strip() for line in cnpjs_text.split('\n') if line.strip()]
            
            comparison_results = []
            progress_bar = st.progress(0)
            
            for i, cnpj in enumerate(cnpjs):
                with st.spinner(f"Analisando {cnpj}..."):
                    checker = st.session_state.fraud_checker
                    
                    if checker._validate_cnpj(cnpj):
                        result = run_async_operation(
                            checker.check_dealer_reputation(cnpj)
                        )
                        
                        comparison_results.append({
                            'CNPJ': cnpj,
                            'Empresa': result.get('company_name', 'N/A'),
                            'Score': result.get('reputation_score', 'N/A'),
                            'Reclame Aqui': result.get('reclame_aqui_score', 'N/A'),
                            'Google': result.get('google_rating', 'N/A'),
                            'Reclamações': result.get('complaint_count', 'N/A')
                        })
                    
                    progress_bar.progress((i + 1) / len(cnpjs))
            
            if comparison_results:
                # Criar DataFrame
                df = pd.DataFrame(comparison_results)
                
                # Exibir tabela
                st.markdown("### 📋 Resultados Comparativos")
                st.dataframe(df, use_container_width=True)
                
                # Gráfico comparativo
                if 'Score' in df.columns:
                    fig = px.bar(df, x='CNPJ', y='Score', color='Score',
                                color_continuous_scale='RdYlGn_r',
                                title='Comparação de Scores de Reputação')
                    st.plotly_chart(fig, use_container_width=True)

with tab3:
    st.markdown("### 📈 Dashboard de Análises")
    
    if st.session_state.analysis_results:
        # Estatísticas gerais
        st.markdown("#### 📊 Estatísticas Gerais")
        
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.markdown('<div class="metric-card">', unsafe_allow_html=True)
            st.markdown('<div class="stat-number">{}</div>'.format(len(st.session_state.analysis_results)), unsafe_allow_html=True)
            st.markdown('<div class="stat-label">Análises Realizadas</div>', unsafe_allow_html=True)
            st.markdown('</div>', unsafe_allow_html=True)
        
        # Histórico de análises
        st.markdown("#### 📜 Histórico de Análises")
        
        history_data = []
        for key, result in st.session_state.analysis_results.items():
            if isinstance(result, dict):
                history_data.append({
                    'Chave': key,
                    'CNPJ': result.get('cnpj', 'N/A'),
                    'Empresa': result.get('company_name', 'N/A'),
                    'Data': result.get('query_date', 'N/A'),
                    'Status': result.get('status', 'N/A')
                })
        
        if history_data:
            df_history = pd.DataFrame(history_data)
            st.dataframe(df_history, use_container_width=True)
        
        # Botão para limpar histórico
        if st.button("🗑️ Limpar Histórico", use_container_width=True):
            st.session_state.analysis_results = {}
            st.rerun()
    else:
        st.info("📊 Nenhuma análise realizada ainda. Faça sua primeira verificação!")

# Footer
st.markdown("---")
st.markdown("""
<div style='text-align: center; color: #666; padding: 2rem; background: linear-gradient(135deg, #f5f7fa 0%, #c3cfe2 100%); border-radius: 15px;'>
    <h3>🚗 Sistema Avançado de Verificação de Fraude v2.0</h3>
    <p>Powered by OpenAI GPT-4o | Busca Web em Tempo Real | Análise Completa de Riscos</p>
    <p style='font-size: 0.9rem; opacity: 0.8;'>© 2025 - Desenvolvido para máxima segurança em transações automotivas</p>
</div>
""", unsafe_allow_html=True)

# Executa a aplicação
if __name__ == "__main__":
    pass