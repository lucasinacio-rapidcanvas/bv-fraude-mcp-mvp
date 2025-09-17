#!/usr/bin/env python3
"""
Sistema Avançado de Verificação de Fraude em Lojistas de Veículos
Interface Web Aprimorada usando Streamlit com visualizações detalhadas
VERSÃO INTEGRADA COMPLETA - Com todas as funcionalidades das duas versões
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

# Importa nossa classe principal integrada
from enhanced_fraud_checker import EnhancedDealerFraudChecker
from jusbrasil_service import JusBrasilService
from receita_federal_service import ReceitaFederalService
from google_places_service import GooglePlacesService
from social_media_service import SocialMediaService
from vehicle_owner_service import VehicleOwnerService

# Configuração da página
st.set_page_config(
    page_title="BV - Verificação de Fraude | Lojistas de Veículos",
    page_icon="🏦",
    layout="wide",
    initial_sidebar_state="expanded"
)


def init_session_state():
    """Inicializa o session state do Streamlit"""
    if 'fraud_checker' not in st.session_state:
        st.session_state.fraud_checker = EnhancedDealerFraudChecker()

    if 'analysis_results' not in st.session_state:
        st.session_state.analysis_results = {}

    # Inicialização dos serviços individuais
    if 'jusbrasil_service' not in st.session_state:
        st.session_state.jusbrasil_service = JusBrasilService()

    if 'receita_federal_service' not in st.session_state:
        st.session_state.receita_federal_service = ReceitaFederalService()

    if 'google_places_service' not in st.session_state:
        st.session_state.google_places_service = GooglePlacesService()

    if 'social_media_service' not in st.session_state:
        st.session_state.social_media_service = SocialMediaService()

    if 'vehicle_owner_service' not in st.session_state:
        st.session_state.vehicle_owner_service = VehicleOwnerService()

# Função para executar operações async
def run_async_operation(coro):
    """Helper para executar operações assíncronas no Streamlit"""
    try:
        loop = asyncio.get_event_loop()
    except RuntimeError:
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
    return loop.run_until_complete(coro)

# Função para humanizar status do negócio
def generate_vehicle_report(plate_input: str, result: dict) -> dict:
    """Gera um relatório estruturado para consulta de veículo"""
    report = {
        "metadata": {
            "report_type": "vehicle_owner_consultation",
            "version": "2.2",
            "generated_at": datetime.now().isoformat(),
            "generated_by": "BV - Sistema de Verificação de Fraude",
            "plate": plate_input.upper(),
            "consultation_status": "success" if result["success"] else "error"
        },
        "consultation_info": {
            "data_source": result.get("source", "unknown"),
            "cached_at": result.get("cached_at", None),
            "consulted_at": result.get("consulted_at", None),
            "timeout_used": result.get("timeout_used", None),
            "error_message": result.get("error", None)
        },
        "vehicle_data": {},
        "owner_data": {},
        "restrictions_data": {},
        "registration_data": {},
        "raw_api_response": {}
    }

    if result["success"] and result.get("data"):
        data = result["data"]

        # Dados do veículo
        if data.get("vehicle_info"):
            vehicle = data["vehicle_info"]
            report["vehicle_data"] = {
                "identification": {
                    "plate": vehicle.get("plate", ""),
                    "renavam": vehicle.get("renavam", ""),
                    "chassis": vehicle.get("chassis", "")
                },
                "specifications": {
                    "brand": vehicle.get("brand", ""),
                    "model": vehicle.get("model", ""),
                    "year_manufacture": vehicle.get("year_manufacture", ""),
                    "year_model": vehicle.get("year_model", ""),
                    "color": vehicle.get("color", ""),
                    "fuel_type": vehicle.get("fuel_type", ""),
                    "category": vehicle.get("category", "")
                }
            }

        # Dados do proprietário
        if data.get("owner_info"):
            owner = data["owner_info"]
            report["owner_data"] = {
                "personal_info": {
                    "name": owner.get("name", ""),
                    "document": owner.get("document", ""),
                    "document_type": owner.get("document_type", "")
                },
                "address": owner.get("address", {})
            }

        # Restrições
        if data.get("restrictions"):
            restrictions = data["restrictions"]
            report["restrictions_data"] = {
                "has_restrictions": restrictions.get("has_restrictions", False),
                "general_restrictions": restrictions.get("restriction_list", []),
                "judicial_restrictions": restrictions.get("judicial_restrictions", []),
                "administrative_restrictions": restrictions.get("administrative_restrictions", [])
            }

        # Dados de registro
        if data.get("registration_info"):
            registration = data["registration_info"]
            report["registration_data"] = {
                "registration_date": registration.get("registration_date", ""),
                "last_transfer": registration.get("last_transfer", ""),
                "municipal_registration": registration.get("municipal_registration", ""),
                "origin_state": registration.get("origin_state", "")
            }

        # Resposta bruta da API
        if data.get("raw_data"):
            report["raw_api_response"] = data["raw_data"]

    return report

def humanize_business_status(status):
    """Converte status do Google Places para linguagem amigável"""
    status_map = {
        'OPERATIONAL': 'Funcionando',
        'CLOSED_TEMPORARILY': 'Fechado Temporariamente',
        'CLOSED_PERMANENTLY': 'Fechado Definitivamente',
        'UNKNOWN': 'Status Desconhecido',
        'OPEN': 'Aberto',
        'CLOSED': 'Fechado',
        'N/A': 'Não Informado'
    }
    return status_map.get(status, f'❓ {status}')

# Função para criar gráfico de gauge para score de confiança
def create_gauge_chart(value, title="Score de Confiança"):
    """Cria um gráfico de gauge para mostrar score de confiança"""
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
        st.markdown("### Informações Oficiais da Empresa")
        
        # Criar colunas para informações básicas
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.markdown("#### Dados Cadastrais")
            st.write(f"**Razão Social:** {data.get('razao_social', 'N/A')}")
            st.write(f"**Nome Fantasia:** {data.get('nome_fantasia', 'N/A')}")
            st.write(f"**CNPJ:** {data.get('cnpj', 'N/A')}")
            st.write(f"**Data Abertura:** {data.get('data_abertura', 'N/A')}")
            st.write(f"**Anos em Funcionamento:** {data.get('anos_funcionamento', 'N/A')}")
        
        with col2:
            st.markdown("#### Informações Empresariais")
            st.write(f"**Situação Cadastral:** {data.get('situacao_cadastral', 'N/A')}")
            st.write(f"**Capital Social:** {data.get('capital_social', 'N/A')}")
            st.write(f"**Porte:** {data.get('porte_empresa', 'N/A')}")
            st.write(f"**CNAE Principal:** {data.get('atividade_principal', 'N/A')}")
            st.write(f"**CNAE Adequado:** {data.get('adequacao_cnae', 'N/A')}")
        
        with col3:
            st.markdown("#### Localização")
            st.write(f"**Endereço:** {data.get('endereco', 'N/A')}")
            
            # Sócios
            if data.get('socios'):
                st.markdown("#### Quadro Societário")
                for socio in data['socios']:
                    st.write(f"• {socio}")
        
        # Status Summary
        if data.get('status_summary'):
            st.markdown("#### Resumo da Situação")
            st.info(data['status_summary'])
        
        # Red Flags
        if data.get('red_flags') and len(data['red_flags']) > 0:
            st.markdown("#### Alertas Identificados")
            for flag in data['red_flags']:
                st.error(f"ALERTA: {flag}")
    
    elif data_type == "Reputação Online":
        st.markdown("### Análise Detalhada de Reputação")
        
        # Score de confiança com gauge
        if data.get('reputation_score', 'N/A') != 'N/A':
            try:
                score = int(data['reputation_score'])
                col1, col2 = st.columns([1, 2])
                with col1:
                    fig = create_gauge_chart(score, "Score de Confiança")
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    st.markdown("#### Resumo da Reputação")
                    st.write(data.get('reputation_summary', 'N/A'))
            except:
                st.info(f"Score de Reputação: {data.get('reputation_score', 'N/A')}")
        
        # Métricas detalhadas
        st.markdown("#### Métricas de Avaliação")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            google_rating = data.get('google_rating', 'N/A')
            if google_rating != 'N/A':
                st.metric("Google Rating", f"{google_rating}/5")
            else:
                st.metric("Google Rating", "N/A")
        
        with col2:
            reviews_count = data.get('google_reviews_count', 'N/A')
            st.metric("Total Reviews", reviews_count)
        
        with col3:
            business_status = data.get('business_status', 'N/A')
            friendly_status = humanize_business_status(business_status)
            st.metric("Status", friendly_status)
        
        with col4:
            complaints = data.get('complaint_count', 'N/A')
            st.metric("Reclamações", complaints)
        
        # Problemas principais
        if data.get('main_issues') and len(data['main_issues']) > 0:
            st.markdown("#### Principais Problemas Reportados")
            cols = st.columns(2)
            for i, issue in enumerate(data['main_issues']):
                with cols[i % 2]:
                    st.warning(f"• {issue}")
        
        # Red flags
        if data.get('red_flags') and len(data['red_flags']) > 0:
            st.markdown("#### Alertas Críticos")
            for flag in data['red_flags']:
                st.error(f"ALERTA: {flag}")
        
        # Fontes consultadas
        if data.get('sources_checked'):
            st.markdown("#### Fontes Consultadas")
            sources_str = " | ".join(data['sources_checked'])
            st.success(f"VERIFICADO: {sources_str}")
    
    elif data_type == "Questões Legais":
        st.markdown("### Análise Legal Detalhada")
        
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
        st.markdown("#### Processos e Investigações")
        
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
        
        if process_data['Tipo']:
            df = pd.DataFrame(process_data)
            
            # Gráfico de processos
            fig = px.bar(df.groupby('Tipo').size().reset_index(name='Quantidade'), 
                        x='Tipo', y='Quantidade',
                        color='Tipo',
                        title='Distribuição de Processos e Sanções')
            st.plotly_chart(fig, use_container_width=True)
            
            # Tabela detalhada
            st.markdown("##### Detalhamento Completo")
            for _, row in df.iterrows():
                tipo_label = {
                    'Criminal': 'Criminal',
                    'Cível': 'Cível',
                    'Investigação': 'Investigação',
                    'Sanção/Multa': 'Sanção/Multa'
                }.get(row['Tipo'], row['Tipo'])

                st.markdown(f"**{tipo_label}:**")
                st.write(row['Detalhes'])
                st.markdown("---")
        
        # Indicadores de fraude
        if data.get('fraud_indicators') and len(data['fraud_indicators']) > 0:
            st.markdown("#### Indicadores de Fraude")
            for indicator in data['fraud_indicators']:
                st.error(f"ALERTA: {indicator}")
        
        # Fontes consultadas
        if data.get('sources_found'):
            st.markdown("#### Fontes Legais Consultadas")
            cols = st.columns(3)
            for i, source in enumerate(data['sources_found']):
                with cols[i % 3]:
                    st.info(f"{source}")
    
    elif data_type == "Redes Sociais":
        st.markdown("### Análise de Redes Sociais")
        
        # Score de confiança digital com gauge
        if data.get('social_presence_score', 'N/A') != 'N/A':
            try:
                score = int(data['social_presence_score'])
                col1, col2 = st.columns([1, 2])
                with col1:
                    fig = create_gauge_chart(score, "Score de Confiança Digital")
                    st.plotly_chart(fig, use_container_width=True)
                with col2:
                    st.markdown("#### Resumo da Análise")
                    st.write(data.get('analysis_summary', 'N/A'))
            except:
                st.info(f"Score de Presença Digital: {data.get('social_presence_score', 'N/A')}")
        
        # Métricas gerais
        st.markdown("#### Métricas Gerais")
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_followers = data.get('total_followers', 0)
            st.metric("Total de Seguidores", f"{total_followers:,}")
        
        with col2:
            platforms_active = data.get('platforms_active', 0)
            st.metric("Plataformas Ativas", platforms_active)
        
        with col3:
            activity = data.get('activity_analysis', {}).get('overall_activity', 'N/A')
            st.metric("Nível de Atividade", activity)
        
        with col4:
            last_activity = data.get('activity_analysis', {}).get('last_activity', 'N/A')
            st.metric("Última Atividade", last_activity)
        
        # Detalhes das plataformas
        social_profiles = data.get('social_profiles', {})
        if social_profiles:
            st.markdown("#### Perfis por Plataforma")
            
            # Criar tabs para cada plataforma
            platform_names = list(social_profiles.keys())
            if len(platform_names) == 1:
                platform_tabs = [st.container()]
                platform_tabs[0].markdown(f"**{platform_names[0].title()}**")
            else:
                platform_tabs = st.tabs([platform.title() for platform in platform_names])
            
            for i, (platform, profile_data) in enumerate(social_profiles.items()):
                with platform_tabs[i]:
                    if platform == 'facebook':
                        st.markdown("#### Facebook")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**URL:** {profile_data.get('url', 'N/A')}")
                            st.write(f"**Seguidores:** {profile_data.get('followers', 0):,}")
                            st.write(f"**Rating:** {profile_data.get('rating', 'N/A')}/5")
                        with col2:
                            st.write(f"**Reviews:** {profile_data.get('reviews_count', 0)}")
                            st.write(f"**Última Postagem:** {profile_data.get('last_post', 'N/A')}")
                            if profile_data.get('verified', False):
                                st.success("VERIFICADO")
                    
                    elif platform == 'instagram':
                        st.markdown("#### Instagram")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**URL:** {profile_data.get('url', 'N/A')}")
                            st.write(f"**Seguidores:** {profile_data.get('followers', 0):,}")
                            st.write(f"**Seguindo:** {profile_data.get('following', 0):,}")
                        with col2:
                            st.write(f"**Posts:** {profile_data.get('posts_count', 0):,}")
                            st.write(f"**Taxa de Engajamento:** {profile_data.get('engagement_rate', 'N/A')}%")
                            st.write(f"**Última Postagem:** {profile_data.get('last_post', 'N/A')}")
                    
                    elif platform == 'linkedin':
                        st.markdown("#### LinkedIn")
                        col1, col2 = st.columns(2)
                        with col1:
                            st.write(f"**URL:** {profile_data.get('url', 'N/A')}")
                            st.write(f"**Seguidores:** {profile_data.get('followers', 0):,}")
                        with col2:
                            st.write(f"**Funcionários na Plataforma:** {profile_data.get('employees_on_platform', 0)}")
                            st.write(f"**Tamanho da Empresa:** {profile_data.get('company_size', 'N/A')}")
                    
                    # Nível de atividade para todas as plataformas
                    activity_level = profile_data.get('activity_level', 'N/A')
                    if activity_level == 'MUITO_ALTO':
                        st.success(f"Atividade: {activity_level}")
                    elif activity_level == 'ALTO':
                        st.info(f"Atividade: {activity_level}")
                    elif activity_level == 'MÉDIO':
                        st.warning(f"Atividade: {activity_level}")
                    else:
                        st.error(f"Atividade: {activity_level}")
        
        # Red flags
        if data.get('red_flags') and len(data['red_flags']) > 0:
            st.markdown("#### Alertas Identificados")
            for flag in data['red_flags']:
                st.error(f"ALERTA: {flag}")
        
        # Recomendações
        if data.get('recommendations') and len(data['recommendations']) > 0:
            st.markdown("#### Recomendações")
            for recommendation in data['recommendations']:
                st.info(f"• {recommendation}")
    
    elif data_type == "JusBrasil Criminal":
        st.markdown("### Análise Criminal - JusBrasil")
        
        # Risk Level com visual destacado
        risk_level = data.get('risk_level', 'N/A')
        risk_score = data.get('risk_score', 0)
        
        if risk_level != 'N/A':
            col1, col2 = st.columns([1, 2])
            with col1:
                # Gauge chart para score
                fig = create_gauge_chart(risk_score, "Score de Confiança Criminal")
                st.plotly_chart(fig, use_container_width=True)
            
            with col2:
                st.markdown("#### Análise de Risco")
                if risk_level == "BAIXO":
                    st.markdown('<div class="risk-badge risk-low">RISCO BAIXO</div>', unsafe_allow_html=True)
                elif risk_level == "MÉDIO":
                    st.markdown('<div class="risk-badge risk-medium">RISCO MÉDIO</div>', unsafe_allow_html=True)
                elif risk_level == "ALTO":
                    st.markdown('<div class="risk-badge risk-high">RISCO ALTO</div>', unsafe_allow_html=True)
                elif risk_level == "CRÍTICO":
                    st.markdown('<div class="risk-badge risk-critical">RISCO CRÍTICO</div>', unsafe_allow_html=True)
                
                st.write(f"**Recomendação:** {data.get('recommendation', 'N/A')}")
        
        # Métricas dos processos
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            st.metric("Total Processos", data.get('total_processos', 0))
        with col2:
            st.metric("Processos Ativos", data.get('processos_ativos', 0))
        with col3:
            st.metric("Processos Recentes", data.get('processos_recentes', 0))
        with col4:
            tipos_crime = data.get('tipos_crime', [])
            st.metric("Tipos de Crime", len(tipos_crime) if tipos_crime else 0)
        
        # Detalhes dos processos se existirem
        if data.get('process_details') and len(data['process_details']) > 0:
            st.markdown("#### Detalhes dos Processos")
            df_processes = pd.DataFrame(data['process_details'])
            st.dataframe(df_processes, use_container_width=True)
        
        # Tipos de crime se existirem
        if tipos_crime:
            st.markdown("#### Tipos de Crime Identificados")
            for crime in tipos_crime:
                st.warning(f"• {crime}")


def main():
    """
    Função principal do aplicativo Streamlit
    """
    # CSS customizado com paleta BV
    st.markdown("""
    <style>
        @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');
        
        :root {
            --bv-blue-primary: #3B4FFF;
            --bv-blue-secondary: #2E3A8C;
            --bv-cyan: #00D4FF;
            --bv-black: #000000;
            --bv-white: #FFFFFF;
            --bv-gray-light: #F8F9FA;
            --bv-gray-medium: #E9ECEF;
        }
        
        * {
            font-family: 'Inter', sans-serif;
        }
        
        /* Streamlit sidebar customização */
        .css-1d391kg {
            background: var(--bv-gray-light);
        }
        
        /* Main content area */
        .main .block-container {
            background: var(--bv-white);
            padding-top: 2rem;
        }
        
        .main-header {
            background: linear-gradient(135deg, var(--bv-blue-primary) 0%, var(--bv-blue-secondary) 100%);
            padding: 2rem;
            border-radius: 15px;
            color: var(--bv-white);
            margin-bottom: 2rem;
            box-shadow: 0 10px 30px rgba(59, 79, 255, 0.2);
            position: relative;
            overflow: hidden;
        }
        
        .main-header::before {
            content: '';
            position: absolute;
            top: 0;
            right: 0;
            width: 200px;
            height: 200px;
            background: var(--bv-cyan);
            opacity: 0.1;
            border-radius: 50%;
            transform: translate(50px, -50px);
        }
        
        .main-header h1 {
            font-size: 2.5rem;
            font-weight: 700;
            margin-bottom: 0.5rem;
            color: var(--bv-white);
            position: relative;
            z-index: 1;
        }
        
        /* BV Logo Style */
        .bv-logo {
            display: inline-block;
            font-weight: 900;
            font-size: 2rem;
            background: var(--bv-cyan);
            color: var(--bv-white);
            padding: 0.5rem 1rem;
            border-radius: 8px;
            margin-right: 1rem;
        }
        
        .metric-card {
            background: var(--bv-white);
            padding: 1.5rem;
            border-radius: 12px;
            box-shadow: 0 4px 6px rgba(59, 79, 255, 0.1);
            border-left: 4px solid var(--bv-blue-primary);
            margin: 1rem 0;
            transition: transform 0.2s;
            border: 1px solid var(--bv-gray-medium);
        }
        
        .metric-card:hover {
            transform: translateY(-2px);
            box-shadow: 0 8px 16px rgba(59, 79, 255, 0.15);
            border-left-color: var(--bv-cyan);
        }
        
        .info-card {
            background: linear-gradient(135deg, var(--bv-gray-light) 0%, var(--bv-gray-medium) 100%);
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
            border: 1px solid var(--bv-blue-primary);
        }
        
        .warning-card {
            background: linear-gradient(135deg, #FFF3E0 0%, #FFE0B2 100%);
            border: 2px solid #FF9800;
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
            box-shadow: 0 4px 6px rgba(255, 152, 0, 0.2);
        }
        
        .danger-card {
            background: linear-gradient(135deg, #FFEBEE 0%, #FFCDD2 100%);
            border: 2px solid #F44336;
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
            box-shadow: 0 4px 6px rgba(244, 67, 54, 0.2);
        }
        
        .success-card {
            background: linear-gradient(135deg, #E8F5E8 0%, #C8E6C9 100%);
            border: 2px solid #4CAF50;
            padding: 1.5rem;
            border-radius: 12px;
            margin: 1rem 0;
            box-shadow: 0 4px 6px rgba(76, 175, 80, 0.2);
        }
        
        .detail-section {
            background: var(--bv-white);
            padding: 2rem;
            border-radius: 12px;
            margin: 1.5rem 0;
            box-shadow: 0 4px 6px rgba(59, 79, 255, 0.08);
            border: 1px solid var(--bv-gray-medium);
        }
        
        .detail-section h3 {
            color: var(--bv-blue-secondary);
            margin-bottom: 1.5rem;
            padding-bottom: 0.5rem;
            border-bottom: 3px solid var(--bv-cyan);
            font-weight: 600;
        }
        
        /* Buttons customização */
        .stButton > button {
            background: linear-gradient(135deg, var(--bv-blue-primary) 0%, var(--bv-cyan) 100%);
            border: none;
            color: var(--bv-white);
            font-weight: 600;
            border-radius: 25px;
            padding: 0.75rem 2rem;
            box-shadow: 0 4px 12px rgba(59, 79, 255, 0.3);
            transition: all 0.3s ease;
        }
        
        .stButton > button:hover {
            background: linear-gradient(135deg, var(--bv-cyan) 0%, var(--bv-blue-primary) 100%);
            transform: translateY(-2px);
            box-shadow: 0 6px 16px rgba(59, 79, 255, 0.4);
        }
        
        /* Sidebar buttons */
        .css-1q1n0ol > button {
            background: var(--bv-blue-primary);
            color: var(--bv-white);
            border: none;
            border-radius: 20px;
        }
        
        .risk-badge {
            display: inline-block;
            padding: 0.5rem 1rem;
            border-radius: 25px;
            font-weight: 700;
            text-align: center;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }
        
        .risk-low { 
            background: linear-gradient(135deg, #4CAF50 0%, #81C784 100%);
            color: var(--bv-white);
            box-shadow: 0 2px 8px rgba(76, 175, 80, 0.3);
        }
        
        .risk-medium { 
            background: linear-gradient(135deg, #FF9800 0%, #FFB74D 100%);
            color: var(--bv-white);
            box-shadow: 0 2px 8px rgba(255, 152, 0, 0.3);
        }
        
        .risk-high { 
            background: linear-gradient(135deg, #FF5722 0%, #FF8A65 100%);
            color: var(--bv-white);
            box-shadow: 0 2px 8px rgba(255, 87, 34, 0.3);
        }
        
        .risk-critical { 
            background: linear-gradient(135deg, #F44336 0%, var(--bv-black) 100%);
            color: var(--bv-white);
            box-shadow: 0 2px 8px rgba(244, 67, 54, 0.4);
        }
        
        .stat-number {
            font-size: 2.2rem;
            font-weight: 700;
            color: var(--bv-blue-primary);
            text-shadow: 0 2px 4px rgba(59, 79, 255, 0.1);
        }
        
        .stat-label {
            color: var(--bv-blue-secondary);
            font-size: 0.9rem;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            font-weight: 600;
        }
        
        /* Tabs customização */
        .stTabs [data-baseweb="tab-list"] {
            gap: 8px;
            background: var(--bv-gray-light);
            border-radius: 25px;
            padding: 0.5rem;
        }
        
        .stTabs [data-baseweb="tab"] {
            background: transparent;
            border-radius: 20px;
            color: var(--bv-blue-secondary);
            font-weight: 600;
            border: 2px solid transparent;
        }
        
        .stTabs [aria-selected="true"] {
            background: var(--bv-blue-primary);
            color: var(--bv-white);
            border-color: var(--bv-cyan);
        }
        
        /* Progress bars */
        .stProgress .st-bo {
            background: var(--bv-cyan);
        }
        
        /* Metrics */
        [data-testid="metric-container"] {
            background: var(--bv-white);
            border: 2px solid var(--bv-gray-medium);
            padding: 1rem;
            border-radius: 12px;
            box-shadow: 0 2px 8px rgba(59, 79, 255, 0.05);
        }
        
        [data-testid="metric-container"]:hover {
            border-color: var(--bv-cyan);
            box-shadow: 0 4px 12px rgba(0, 212, 255, 0.15);
        }
        
        /* Expander customização */
        .streamlit-expanderHeader {
            background: linear-gradient(135deg, var(--bv-blue-primary) 0%, var(--bv-cyan) 100%);
            color: var(--bv-white);
            border-radius: 12px;
            font-weight: 600;
        }
        
        /* Footer BV Style */
        .bv-footer {
            background: linear-gradient(135deg, var(--bv-blue-secondary) 0%, var(--bv-black) 100%);
            color: #ffffff !important;
            padding: 2rem;
            border-radius: 15px;
            margin-top: 3rem;
            position: relative;
            overflow: hidden;
        }

        .bv-footer h3 {
            color: #ffffff !important;
            font-weight: 600;
        }

        .bv-footer p {
            color: #ffffff !important;
        }
        
        .bv-footer::before {
            content: '';
            position: absolute;
            bottom: 0;
            left: 0;
            width: 100%;
            height: 4px;
            background: linear-gradient(90deg, var(--bv-cyan) 0%, var(--bv-blue-primary) 100%);
        }
        
        /* Custom scrollbar */
        ::-webkit-scrollbar {
            width: 8px;
        }
        
        ::-webkit-scrollbar-track {
            background: var(--bv-gray-light);
        }
        
        ::-webkit-scrollbar-thumb {
            background: linear-gradient(180deg, var(--bv-blue-primary) 0%, var(--bv-cyan) 100%);
            border-radius: 4px;
        }
        
        ::-webkit-scrollbar-thumb:hover {
            background: linear-gradient(180deg, var(--bv-cyan) 0%, var(--bv-blue-primary) 100%);
        }

        /* Aumentar tamanho do botão principal */
        .stButton > button[kind="primary"] {
            height: 60px !important;
            font-size: 18px !important;
            font-weight: 600 !important;
            border-radius: 12px !important;
            background: linear-gradient(135deg, var(--bv-blue-primary) 0%, var(--bv-blue-secondary) 100%) !important;
            border: none !important;
            box-shadow: 0 4px 15px rgba(59, 79, 255, 0.3) !important;
        }

        .stButton > button[kind="primary"]:hover {
            transform: translateY(-1px) !important;
            box-shadow: 0 6px 20px rgba(59, 79, 255, 0.4) !important;
        }
    </style>
    """, unsafe_allow_html=True)

    # Header principal com identidade BV
    st.markdown("""
    <div class="main-header">
        <span></span>
        <h1>Sistema de Verificação de Fraude</h1>
        <p style="font-size: 1.2rem; margin-bottom: 1rem; position: relative; z-index: 1;">Análise completa e detalhada de confiabilidade para lojistas de veículos no Brasil</p>
    </div>
    """, unsafe_allow_html=True)

    # Inicialização do session state
    init_session_state()
    
    # Sidebar aprimorado
    with st.sidebar:
        # Logo BV oficial no topo
        try:
            # Centralizando a logo no sidebar
            col1, col2, col3 = st.columns([1, 2, 1])
            with col2:
                st.image("logo_bv.png", width=120)
        
        except:
            # Fallback caso não encontre a imagem
            st.markdown("""
            <div style='text-align: center; padding: 1rem; background: linear-gradient(135deg, #3B4FFF 0%, #00D4FF 100%); border-radius: 10px; margin-bottom: 1rem; box-shadow: 0 4px 12px rgba(59, 79, 255, 0.3);'>
                <span style='font-size: 2.5rem; font-weight: 900; color: white; text-shadow: 0 2px 4px rgba(0,0,0,0.3);'>BV</span>
                <div style='font-size: 0.8rem; color: white; margin-top: 0.5rem; opacity: 0.9; font-weight: 500;'>Sistema de Verificação</div>
            </div>
            """, unsafe_allow_html=True)

        st.markdown("---")

        # Estatísticas da sessão
        st.markdown("### Estatísticas da Sessão")
        if st.session_state.analysis_results:
            st.metric("Análises Realizadas", len(st.session_state.analysis_results))
        
        st.markdown("---")
        
        # Informações do sistema
        st.markdown("### Sistema BV")
        st.info("""
        **Banco BV** - Sistema de Verificação de Fraude
        **Versão:** 2.1 Enhanced Integrated
        **APIs:** Receita Federal + Google Places + JusBrasil + Redes Sociais
        **Dados:** Reais e Atualizados em Tempo Real
        **Cache:** Sistema Otimizado para Performance
        **Segurança:** Análise Completa de Riscos
        """)

    # Interface principal
    st.markdown("## Central de Verificação")

    # Sistema de tabs
    tab1, tab2 = st.tabs(["Verificação de CNPJ", "Consulta de Veículos"])

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
        st.markdown("### Selecione as Verificações")
        
        # Primeira linha de checkboxes
        col1, col2, col3, col4 = st.columns(4)
        
        checks_to_perform = {}
        
        with col1:
            checks_to_perform['validate'] = st.checkbox("Validar CNPJ", value=True)
        with col2:
            checks_to_perform['receita_federal'] = st.checkbox("Receita Federal", value=True)
        with col3:
            checks_to_perform['google_places'] = st.checkbox("Google Places", value=True)
        with col4:
            checks_to_perform['jusbrasil'] = st.checkbox("JusBrasil", value=True)
        
        # Segunda linha de checkboxes
        col5, col6, col7, col8 = st.columns(4)
        
        with col5:
            checks_to_perform['social_media'] = st.checkbox("Redes Sociais", value=True)
        
        # Botão principal de execução
        if st.button("EXECUTAR ANÁLISE", use_container_width=True, type="primary"):
            if cnpj_input:
                checker = st.session_state.fraud_checker
                
                # Container para resultados
                results_container = st.container()
                
                with results_container:
                    st.markdown("## Resultados da Análise")
                    
                    # Validação
                    if checks_to_perform['validate']:
                        with st.spinner("Validando CNPJ..."):
                            is_valid = checker._validate_cnpj(cnpj_input)
                            formatted = checker._format_cnpj(cnpj_input)

                            if is_valid:
                                st.success(f"CNPJ Válido: {formatted}")
                            else:
                                st.error(f"CNPJ Inválido: {cnpj_input}")
                                st.stop()

                    # ANÁLISE CONSOLIDADA PRIMEIRO
                    if analyze_all:
                        with st.spinner("Executando análise completa integrada..."):
                            result = run_async_operation(
                                checker.comprehensive_check(cnpj_input, company_name)
                            )
                            st.session_state.analysis_results[f"{cnpj_input}_complete"] = result

                            # Análise de confiança consolidada
                            if "risk_analysis" in result:
                                with st.expander("ANÁLISE DE CONFIANÇA CONSOLIDADA", expanded=True):
                                    risk = result["risk_analysis"]

                                    col1, col2, col3 = st.columns(3)

                                    with col1:
                                        score = risk.get("risk_score", 0)
                                        # Inverter score para confiança (100 - risk_score)
                                        confidence_score = 100 - score
                                        fig = create_gauge_chart(confidence_score, "Score de Confiança Final")
                                        st.plotly_chart(fig, use_container_width=True)

                                    with col2:
                                        st.markdown("#### Nível de Confiança")
                                        level = risk.get("risk_level", "N/A")
                                        if level == "BAIXO":  # Baixo risco = Alta confiança
                                            st.markdown('<div class="success-card"><h2>ALTA CONFIANÇA</h2></div>', unsafe_allow_html=True)
                                        elif level == "MÉDIO":
                                            st.markdown('<div class="warning-card"><h2>MÉDIA CONFIANÇA</h2></div>', unsafe_allow_html=True)
                                        elif level == "ALTO":
                                            st.markdown('<div class="warning-card"><h2>BAIXA CONFIANÇA</h2></div>', unsafe_allow_html=True)
                                        else:
                                            st.markdown('<div class="danger-card"><h2>CONFIANÇA CRÍTICA</h2></div>', unsafe_allow_html=True)

                                    with col3:
                                        st.markdown("#### Recomendação")
                                        st.info(risk.get("recommendation", "N/A"))

                                        # Mostrar legenda apenas aqui
                                        st.markdown("**Legenda de Confiança:**")
                                        st.markdown("""
                                        <div style='font-size: 0.8rem; margin-top: 1rem;'>
                                        <div style='padding: 0.3rem; background: #d4edda; border-radius: 3px; margin: 0.1rem 0;'>Alta Confiança (76-100)</div>
                                        <div style='padding: 0.3rem; background: #fff3cd; border-radius: 3px; margin: 0.1rem 0;'>Média Confiança (51-75)</div>
                                        <div style='padding: 0.3rem; background: #f8d7da; border-radius: 3px; margin: 0.1rem 0;'>Baixa Confiança (26-50)</div>
                                        <div style='padding: 0.3rem; background: #721c24; color: white; border-radius: 3px; margin: 0.1rem 0;'>Confiança Crítica (0-25)</div>
                                        </div>
                                        """, unsafe_allow_html=True)

                                    # Fatores de risco
                                    if risk.get("risk_factors"):
                                        st.markdown("#### Fatores de Risco Identificados")
                                        for factor in risk["risk_factors"]:
                                            st.warning(f"• {factor}")

                    st.markdown("---")
                    st.markdown("### Detalhamento por Fonte")

                    # Receita Federal  
                    if checks_to_perform['receita_federal']:
                        with st.spinner("Consultando Receita Federal..."):
                            result = run_async_operation(
                                checker.verify_cnpj_status(cnpj_input)
                            )
                            st.session_state.analysis_results[f"{cnpj_input}_receita_federal"] = result
                            
                            with st.expander("Dados da Receita Federal", expanded=True):
                                display_detailed_data(result, "Status Oficial")
                    
                    # Google Places
                    if checks_to_perform['google_places']:
                        with st.spinner("Consultando Google Places..."):
                            result = run_async_operation(
                                checker.check_dealer_reputation(cnpj_input, company_name)
                            )
                            st.session_state.analysis_results[f"{cnpj_input}_google_places"] = result
                            
                            with st.expander("Análise de Reputação", expanded=True):
                                display_detailed_data(result, "Reputação Online")
                    
                    # Análise Criminal JusBrasil
                    if checks_to_perform['jusbrasil']:
                        with st.spinner("Consultando processos criminais no JusBrasil..."):
                            jusbrasil_service = st.session_state.jusbrasil_service
                            
                            # Análise de risco criminal
                            criminal_analysis = jusbrasil_service.analyze_criminal_risk(cnpj_input)
                            
                            # Busca detalhes dos processos
                            process_details = jusbrasil_service.get_process_details(cnpj_input)
                            criminal_analysis['process_details'] = process_details
                            
                            st.session_state.analysis_results[f"{cnpj_input}_jusbrasil"] = criminal_analysis
                            
                            with st.expander("Análise Criminal - JusBrasil", expanded=True):
                                display_detailed_data(criminal_analysis, "JusBrasil Criminal")
                    
                    # Análise de Redes Sociais
                    if checks_to_perform['social_media']:
                        with st.spinner("Analisando presença em redes sociais..."):
                            result = run_async_operation(
                                checker.check_social_media(cnpj_input, company_name)
                            )
                            st.session_state.analysis_results[f"{cnpj_input}_social_media"] = result
                            
                            with st.expander("Análise de Redes Sociais", expanded=True):
                                display_detailed_data(result, "Redes Sociais")
                    
                    # Análise consolidada já foi movida para o topo
                    # Botão para baixar relatório
                    st.markdown("---")
                    col1, col2 = st.columns(2)
                    with col1:
                        if st.button("Salvar Relatório JSON", use_container_width=True):
                            # Consolidar todos os resultados
                            full_report = {
                                "cnpj": cnpj_input,
                                "company_name": company_name,
                                "analysis_date": datetime.now().isoformat(),
                                "results": st.session_state.analysis_results
                            }
                            st.download_button(
                                label="Baixar JSON",
                                data=json.dumps(full_report, indent=2, ensure_ascii=False),
                                file_name=f"analise_{cnpj_input}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                mime="application/json"
                            )
                    
                    with col2:
                        if st.button("Nova Análise", use_container_width=True):
                            st.rerun()
            
            else:
                st.error("Por favor, digite um CNPJ válido")

    with tab2:
        st.markdown("### Consulta de Proprietário de Veículo")
        st.markdown("Digite a placa do veículo para consultar dados do proprietário")

        # Input da placa
        col1, col2 = st.columns([2, 1])
        with col1:
            plate_input = st.text_input(
                "Placa do Veículo:",
                placeholder="ABC1234 ou ABC1A23",
                help="Digite a placa no formato antigo (ABC1234) ou Mercosul (ABC1A23)"
            )

        with col2:
            if st.button("🔍 Consultar Veículo", use_container_width=True, type="primary"):
                if plate_input:
                    # Placeholder para status da consulta
                    status_placeholder = st.empty()
                    progress_bar = st.progress(0)

                    status_placeholder.info("🔍 Iniciando consulta...")
                    progress_bar.progress(10)

                    vehicle_service = st.session_state.vehicle_owner_service

                    # Verifica cache primeiro
                    status_placeholder.info("📋 Verificando cache...")
                    progress_bar.progress(30)

                    result = vehicle_service.lookup_vehicle_owner(plate_input)

                    if result["source"] == "cache":
                        status_placeholder.success("✅ Dados encontrados no cache!")
                        progress_bar.progress(100)
                    elif result["success"]:
                        status_placeholder.success("✅ Consulta API concluída!")
                        progress_bar.progress(100)
                    else:
                        status_placeholder.error("❌ Erro na consulta")
                        progress_bar.progress(100)

                    # Remover indicators após 2 segundos
                    import time
                    time.sleep(1)
                    status_placeholder.empty()
                    progress_bar.empty()

                    if result["success"]:
                        st.success(f"✅ Consulta realizada com sucesso!")

                        # Fonte dos dados
                        if result["source"] == "cache":
                            st.info(f"📋 Dados obtidos do cache (atualizados em: {result['cached_at'][:10]})")
                        else:
                            st.info(f"🌐 Dados obtidos da API em tempo real")

                        data = result["data"]

                        # Informações do Veículo
                        if data.get("vehicle_info"):
                            with st.expander("🚗 Informações do Veículo", expanded=True):
                                vehicle = data["vehicle_info"]

                                col1, col2, col3 = st.columns(3)
                                with col1:
                                    st.metric("Placa", vehicle.get("plate", "N/A"))
                                    st.metric("Marca", vehicle.get("brand", "N/A"))
                                    st.metric("Modelo", vehicle.get("model", "N/A"))

                                with col2:
                                    st.metric("Ano Fabricação", vehicle.get("year_manufacture", "N/A"))
                                    st.metric("Ano Modelo", vehicle.get("year_model", "N/A"))
                                    st.metric("Cor", vehicle.get("color", "N/A"))

                                with col3:
                                    st.metric("Combustível", vehicle.get("fuel_type", "N/A"))
                                    st.metric("Categoria", vehicle.get("category", "N/A"))
                                    st.metric("RENAVAM", vehicle.get("renavam", "N/A"))

                        # Informações do Proprietário
                        if data.get("owner_info"):
                            with st.expander("👤 Informações do Proprietário", expanded=True):
                                    owner = data["owner_info"]

                                    col1, col2 = st.columns(2)
                                    with col1:
                                        st.metric("Nome", owner.get("name", "N/A"))
                                        st.metric("Documento", owner.get("document", "N/A"))
                                        st.metric("Tipo Documento", owner.get("document_type", "N/A"))

                                    with col2:
                                        address = owner.get("address", {})
                                        if any(address.values()):
                                            st.markdown("**Endereço:**")
                                            full_address = f"{address.get('street', '')} {address.get('number', '')}"
                                            if full_address.strip():
                                                st.text(full_address)
                                            neighborhood_city = f"{address.get('neighborhood', '')} - {address.get('city', '')}/{address.get('state', '')}"
                                            if neighborhood_city.strip() != " - /":
                                                st.text(neighborhood_city)
                                            if address.get('zip_code'):
                                                st.text(f"CEP: {address.get('zip_code')}")

                            # Restrições
                            if data.get("restrictions"):
                                with st.expander("⚠️ Restrições e Impedimentos", expanded=True):
                                    restrictions = data["restrictions"]

                                    if restrictions.get("has_restrictions"):
                                        st.error("🚨 Veículo possui restrições!")

                                        if restrictions.get("restriction_list"):
                                            st.markdown("**Lista de Restrições:**")
                                            for restriction in restrictions["restriction_list"]:
                                                st.warning(f"• {restriction}")

                                        if restrictions.get("judicial_restrictions"):
                                            st.markdown("**Restrições Judiciais:**")
                                            for restriction in restrictions["judicial_restrictions"]:
                                                st.error(f"• {restriction}")

                                        if restrictions.get("administrative_restrictions"):
                                            st.markdown("**Restrições Administrativas:**")
                                            for restriction in restrictions["administrative_restrictions"]:
                                                st.warning(f"• {restriction}")
                                    else:
                                        st.success("✅ Nenhuma restrição encontrada")

                            # Informações de Registro
                            if data.get("registration_info"):
                                with st.expander("📋 Informações de Registro", expanded=False):
                                    registration = data["registration_info"]

                                    col1, col2 = st.columns(2)
                                    with col1:
                                        if registration.get("registration_date"):
                                            st.metric("Data de Registro", registration["registration_date"])
                                        if registration.get("origin_state"):
                                            st.metric("Estado de Origem", registration["origin_state"])

                                    with col2:
                                        if registration.get("last_transfer"):
                                            st.metric("Última Transferência", registration["last_transfer"])
                                        if registration.get("municipal_registration"):
                                            st.metric("Registro Municipal", registration["municipal_registration"])

                            # Dados brutos (para debug)
                            with st.expander("🔧 Dados Técnicos (Debug)", expanded=False):
                                st.json(data.get("raw_data", {}))

                            # Botões de ação
                            st.markdown("---")
                            col1, col2, col3 = st.columns(3)

                            with col1:
                                # Gerar relatório estruturado
                                vehicle_report = generate_vehicle_report(plate_input, result)
                                st.download_button(
                                    label="📄 Relatório JSON Completo",
                                    data=json.dumps(vehicle_report, indent=2, ensure_ascii=False),
                                    file_name=f"relatorio_veiculo_{plate_input}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                    mime="application/json",
                                    use_container_width=True,
                                    help="Baixa um relatório JSON estruturado com todos os dados da consulta"
                                )

                            with col2:
                                # Dados brutos da API
                                if result.get("data", {}).get("raw_data"):
                                    raw_data = result["data"]["raw_data"]
                                    st.download_button(
                                        label="🔧 Dados Brutos (API)",
                                        data=json.dumps(raw_data, indent=2, ensure_ascii=False),
                                        file_name=f"dados_brutos_{plate_input}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                        mime="application/json",
                                        use_container_width=True,
                                        help="Baixa apenas a resposta bruta da API"
                                    )

                            with col3:
                                if st.button("🔄 Nova Consulta", use_container_width=True):
                                    st.rerun()

                    else:
                        error_msg = result.get('error', 'Erro desconhecido')
                        st.error(f"❌ Erro na consulta: {error_msg}")

                        # Diferentes tipos de erro com dicas específicas
                        if result.get("source") == "validation":
                            st.info("💡 **Dica:** Verifique se a placa está no formato correto (ABC1234 ou ABC1A23)")
                        elif result.get("source") == "api_business_error":
                            if "QUANTIDADE DE CONSULTAS" in error_msg.upper():
                                st.warning("⚠️ **Limite de consultas excedido** - O token da API atingiu o limite diário de consultas.")
                                st.info("💼 **Solução:** Entre em contato com o administrador para renovar o token ou aguarde a renovação automática.")
                        elif "timeout" in error_msg.lower():
                            st.info("⏱️ **Timeout:** A API demorou mais que o esperado. Tente novamente em alguns minutos.")
                        elif "connection" in error_msg.lower():
                            st.info("🌐 **Conexão:** Verifique sua conexão com a internet e tente novamente.")

                        # Botão para baixar relatório de erro (para auditoria)
                        st.markdown("---")
                        col1, col2 = st.columns(2)
                        with col1:
                            error_report = generate_vehicle_report(plate_input, result)
                            st.download_button(
                                label="📋 Relatório de Erro (JSON)",
                                data=json.dumps(error_report, indent=2, ensure_ascii=False),
                                file_name=f"erro_veiculo_{plate_input}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json",
                                mime="application/json",
                                use_container_width=True,
                                help="Baixa relatório com detalhes do erro para análise"
                            )
                        with col2:
                            if st.button("🔄 Tentar Novamente", use_container_width=True):
                                st.rerun()

                else:
                    st.warning("⚠️ Por favor, digite uma placa válida")

        # Estatísticas do cache
        st.markdown("---")
        with st.expander("📊 Estatísticas do Cache de Veículos", expanded=False):
            vehicle_service = st.session_state.vehicle_owner_service
            cache_stats = vehicle_service.get_cache_stats()

            col1, col2, col3 = st.columns(3)
            with col1:
                st.metric("Total de Entradas", cache_stats["total_entries"])
            with col2:
                st.metric("Entradas Válidas", cache_stats["valid_entries"])
            with col3:
                st.metric("Entradas Expiradas", cache_stats["expired_entries"])

            if cache_stats["expired_entries"] > 0:
                if st.button("🧹 Limpar Cache Expirado"):
                    removed = vehicle_service.clear_expired_cache()
                    st.success(f"✅ {removed} entradas expiradas removidas do cache")
                    st.rerun()

    # Footer BV
    st.markdown("---")
    st.markdown("""
    <div class='bv-footer'>
        <div style='text-align: center;'>
            <h3 style='color: #666666;'>Sistema de Verificação de Fraude v2.2 Integrated</h3>
            <p style='font-size: 0.9rem; color: #888888;'>© 2025 Banco BV - Desenvolvido para máxima segurança em transações automotivas</p>
            <p style='font-size: 0.8rem; color: #999999; margin-top: 1rem;'>Conheça o banco que tem crédito para todas as suas versões.</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

# Executa a aplicação
if __name__ == "__main__":
    main()
