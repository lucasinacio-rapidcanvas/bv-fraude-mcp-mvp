#!/usr/bin/env python3
"""
Enhanced Dealer Fraud Checker - Versão com APIs Reais Integradas
Integra serviços da Receita Federal, Google Places e JusBrasil
"""

import asyncio
import json
import re
from datetime import datetime
from typing import Dict, Any, List, Optional
import warnings
warnings.filterwarnings('ignore')

# Importa os serviços reais
from receita_federal_service import ReceitaFederalService
from google_places_service import GooglePlacesService
from jusbrasil_service import JusBrasilService
from social_media_service import SocialMediaService


class EnhancedDealerFraudChecker:
    """
    Sistema integrado de verificação de fraude usando APIs reais
    """
    
    def __init__(self):
        """Inicializa todos os serviços"""
        self.rf_service = ReceitaFederalService()
        self.gplaces_service = GooglePlacesService()
        self.jusbrasil_service = JusBrasilService()
        self.social_service = SocialMediaService()
        
        # Configurações
        self.system_name = "Enhanced Dealer Fraud Checker v2.1"
        self.last_check = datetime.now().isoformat()
    
    def _validate_cnpj(self, cnpj: str) -> bool:
        """Valida CNPJ usando algoritmo brasileiro"""
        if not cnpj:
            return False
        
        # Remove caracteres especiais
        cnpj = re.sub(r'[^0-9]', '', str(cnpj))
        
        # Verifica se tem 14 dígitos
        if len(cnpj) != 14:
            return False
        
        # Verifica se todos os dígitos são iguais (CNPJ inválido)
        if cnpj == cnpj[0] * 14:
            return False
        
        # Algoritmo de validação do CNPJ
        def calculate_digit(cnpj_digits, weights):
            total = sum(int(digit) * weight for digit, weight in zip(cnpj_digits, weights))
            remainder = total % 11
            return 0 if remainder < 2 else 11 - remainder
        
        # Pesos para cálculo dos dígitos verificadores
        weights_1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        weights_2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        
        # Calcula primeiro dígito verificador
        first_digit = calculate_digit(cnpj[:12], weights_1)
        
        # Calcula segundo dígito verificador
        second_digit = calculate_digit(cnpj[:12] + str(first_digit), weights_2)
        
        # Verifica se os dígitos calculados conferem
        return cnpj[12:14] == f"{first_digit}{second_digit}"
    
    def _format_cnpj(self, cnpj: str) -> str:
        """Formata CNPJ com máscara"""
        cleaned = re.sub(r'[^0-9]', '', str(cnpj))
        if len(cleaned) == 14:
            return f"{cleaned[:2]}.{cleaned[2:5]}.{cleaned[5:8]}/{cleaned[8:12]}-{cleaned[12:]}"
        return cnpj
    
    async def verify_cnpj_status(self, cnpj: str) -> Dict[str, Any]:
        """
        Verifica status oficial do CNPJ na Receita Federal
        """
        try:
            if not self._validate_cnpj(cnpj):
                return {
                    'status': 'error',
                    'error': 'CNPJ inválido',
                    'cnpj': cnpj,
                    'query_date': datetime.now().isoformat()
                }
            
            # Busca dados na Receita Federal
            rf_data = self.rf_service.fetch_cnpj_data(cnpj)
            
            if 'error' in rf_data:
                return {
                    'status': 'error',
                    'error': rf_data['error'],
                    'cnpj': self._format_cnpj(cnpj),
                    'query_date': datetime.now().isoformat()
                }
            
            # Processa e retorna dados estruturados
            processed_data = {
                'status': 'success',
                'cnpj': self._format_cnpj(cnpj),
                'razao_social': rf_data.get('razao_social', 'N/A'),
                'nome_fantasia': rf_data.get('nome_fantasia', 'N/A'),
                'situacao_cadastral': rf_data.get('situacao_cadastral', 'N/A'),
                'data_abertura': rf_data.get('data_abertura', 'N/A'),
                'anos_funcionamento': rf_data.get('years_since_opening', 0),
                'capital_social': rf_data.get('capital_social', 'N/A'),
                'porte_empresa': rf_data.get('porte', 'N/A'),
                'atividade_principal': rf_data.get('cnae_principal_desc', 'N/A'),
                'adequacao_cnae': 'SIM' if rf_data.get('allowed_cnae', False) else 'NÃO',
                'endereco': rf_data.get('endereco_completo', 'N/A'),
                'socios': [socio.get('nome', 'N/A') for socio in rf_data.get('socios', [])],
                'status_summary': f"Empresa {rf_data.get('situacao_cadastral', 'N/A')} com {rf_data.get('years_since_opening', 0)} anos de funcionamento.",
                'red_flags': rf_data.get('risk_indicators', []),
                'query_date': datetime.now().isoformat(),
                'data_source': 'Receita Federal - minhareceita.org'
            }
            
            return processed_data
            
        except Exception as e:
            return {
                'status': 'error',
                'error': f'Erro na consulta à Receita Federal: {str(e)}',
                'cnpj': self._format_cnpj(cnpj),
                'query_date': datetime.now().isoformat()
            }
    
    async def check_dealer_reputation(self, cnpj: str, company_name: str = None) -> Dict[str, Any]:
        """
        Verifica reputação online usando Google Places
        """
        try:
            if not self._validate_cnpj(cnpj):
                return {
                    'status': 'error',
                    'error': 'CNPJ inválido',
                    'cnpj': cnpj,
                    'query_date': datetime.now().isoformat()
                }
            
            # Se não tem nome da empresa, busca na RF primeiro
            if not company_name:
                rf_data = self.rf_service.fetch_cnpj_data(cnpj)
                if 'error' not in rf_data:
                    company_name = rf_data.get('razao_social') or rf_data.get('nome_fantasia')
                    company_address = rf_data.get('endereco_completo')
                else:
                    company_address = None
            else:
                company_address = None
            
            if not company_name:
                return {
                    'status': 'error',
                    'error': 'Nome da empresa não disponível',
                    'cnpj': self._format_cnpj(cnpj),
                    'query_date': datetime.now().isoformat()
                }
            
            # Busca no Google Places
            places_data = self.gplaces_service.search_place(
                company_name=company_name,
                address=company_address,
                cnpj=cnpj
            )
            
            if 'error' in places_data:
                # Se não encontrar no Google, retorna dados básicos
                return {
                    'status': 'warning',
                    'company_name': company_name,
                    'cnpj': self._format_cnpj(cnpj),
                    'reputation_score': 'N/A',
                    'google_rating': 'N/A',
                    'reclame_aqui_score': 'N/A',
                    'complaint_count': 'N/A',
                    'business_size': 'N/A',
                    'main_issues': ['Sem presença online significativa'],
                    'red_flags': ['Empresa não encontrada em plataformas de avaliação'],
                    'sources_checked': ['Google Places'],
                    'reputation_summary': 'Empresa com presença online limitada ou inexistente.',
                    'query_date': datetime.now().isoformat(),
                    'data_source': 'Google Places API'
                }
            
            # Calcula score de reputação baseado nos dados do Google
            reputation_score = self._calculate_reputation_score(places_data)
            
            # Monta resposta estruturada
            reputation_data = {
                'status': 'success',
                'company_name': places_data.get('name', company_name),
                'cnpj': self._format_cnpj(cnpj),
                'reputation_score': reputation_score,
                'google_rating': places_data.get('g_rating', 'N/A'),
                'google_reviews_count': places_data.get('g_user_ratings_total', 0),
                'business_status': places_data.get('business_status', 'UNKNOWN'),
                'complaint_count': len(places_data.get('g_common_complaints', [])),
                'main_issues': places_data.get('g_common_complaints', []),
                'red_flags': places_data.get('g_risk_factors', []),
                'sources_checked': ['Google Places'],
                'reputation_summary': self._generate_reputation_summary(places_data, reputation_score),
                'contact_info': {
                    'phone': places_data.get('g_phone', 'N/A'),
                    'website': places_data.get('g_website', 'N/A'),
                    'address': places_data.get('formatted_address', 'N/A')
                },
                'recent_reviews': places_data.get('g_recent_reviews', []),
                'query_date': datetime.now().isoformat(),
                'data_source': places_data.get('data_source', 'Google Places API')
            }
            
            return reputation_data
            
        except Exception as e:
            return {
                'status': 'error',
                'error': f'Erro na verificação de reputação: {str(e)}',
                'cnpj': self._format_cnpj(cnpj),
                'query_date': datetime.now().isoformat()
            }
    
    async def check_social_media(self, cnpj: str, company_name: str = None) -> Dict[str, Any]:
        """
        Verifica presença nas redes sociais (Facebook, Instagram, etc.)
        """
        try:
            if not self._validate_cnpj(cnpj):
                return {
                    'status': 'error',
                    'error': 'CNPJ inválido',
                    'cnpj': cnpj,
                    'query_date': datetime.now().isoformat()
                }
            
            # Se não tem nome da empresa, busca na RF primeiro
            if not company_name:
                rf_data = self.rf_service.fetch_cnpj_data(cnpj)
                if 'error' not in rf_data:
                    company_name = rf_data.get('razao_social') or rf_data.get('nome_fantasia')
                    company_address = rf_data.get('endereco_completo')
                else:
                    company_address = None
            else:
                company_address = None
            
            # Análise de redes sociais
            social_data = self.social_service.analyze_social_presence(
                cnpj, company_name, company_address
            )
            
            # Adiciona campos padronizados se necessário
            if social_data.get('status') == 'success':
                social_data['cnpj'] = self._format_cnpj(cnpj)
                social_data['query_date'] = datetime.now().isoformat()
            
            return social_data
            
        except Exception as e:
            return {
                'status': 'error',
                'error': f'Erro na verificação de redes sociais: {str(e)}',
                'cnpj': self._format_cnpj(cnpj),
                'query_date': datetime.now().isoformat()
            }

    async def check_legal_issues(self, cnpj: str, company_name: str = None) -> Dict[str, Any]:
        """
        Verifica questões legais usando JusBrasil
        """
        try:
            if not self._validate_cnpj(cnpj):
                return {
                    'status': 'error',
                    'error': 'CNPJ inválido',
                    'cnpj': cnpj,
                    'query_date': datetime.now().isoformat()
                }
            
            # Busca processos criminais
            criminal_analysis = self.jusbrasil_service.analyze_criminal_risk(cnpj)
            
            # Busca detalhes dos processos
            process_details = self.jusbrasil_service.get_process_details(cnpj)
            
            # Categoriza processos por tipo
            criminal_cases = []
            civil_cases = []
            investigations = []
            sanctions = []
            
            for process in process_details:
                process_type = process.get('tipo_processo', '').lower()
                process_info = f"{process.get('numero_processo', 'N/A')} - {process.get('forum', 'N/A')}"
                
                if 'criminal' in process_type or 'penal' in process_type:
                    criminal_cases.append(process_info)
                else:
                    civil_cases.append(process_info)
            
            # Monta resposta estruturada
            legal_data = {
                'status': 'success',
                'cnpj': self._format_cnpj(cnpj),
                'risk_level': criminal_analysis.get('risk_level', 'INDETERMINADO'),
                'risk_score': criminal_analysis.get('risk_score', 0),
                'legal_summary': criminal_analysis.get('recommendation', 'N/A'),
                'total_processes': criminal_analysis.get('total_processos', 0),
                'active_processes': criminal_analysis.get('processos_ativos', 0),
                'recent_processes': criminal_analysis.get('processos_recentes', 0),
                'criminal_cases': criminal_cases[:5],  # Limita a 5
                'civil_cases': civil_cases[:5],        # Limita a 5
                'investigations': investigations,
                'sanctions': sanctions,
                'crime_types': criminal_analysis.get('tipos_crime', []),
                'courts': criminal_analysis.get('tribunais', []),
                'fraud_indicators': self._extract_fraud_indicators(criminal_analysis),
                'sources_found': ['JusBrasil'],
                'query_date': datetime.now().isoformat(),
                'data_source': criminal_analysis.get('data_source', 'JusBrasil API')
            }
            
            return legal_data
            
        except Exception as e:
            return {
                'status': 'error',
                'error': f'Erro na verificação legal: {str(e)}',
                'cnpj': self._format_cnpj(cnpj),
                'query_date': datetime.now().isoformat()
            }
    
    async def comprehensive_check(self, cnpj: str, company_name: str = None) -> Dict[str, Any]:
        """
        Análise completa integrando todos os serviços
        """
        try:
            if not self._validate_cnpj(cnpj):
                return {
                    'status': 'error',
                    'error': 'CNPJ inválido',
                    'cnpj': cnpj,
                    'query_date': datetime.now().isoformat()
                }
            
            # Executa todas as verificações em paralelo
            rf_task = self.verify_cnpj_status(cnpj)
            reputation_task = self.check_dealer_reputation(cnpj, company_name)
            legal_task = self.check_legal_issues(cnpj, company_name)
            social_task = self.check_social_media(cnpj, company_name)
            
            # Aguarda todas as verificações
            rf_data, reputation_data, legal_data, social_data = await asyncio.gather(
                rf_task, reputation_task, legal_task, social_task
            )
            
            # Análise consolidada de risco
            risk_analysis = self._calculate_consolidated_risk(
                rf_data, reputation_data, legal_data, social_data
            )
            
            # Monta resposta completa
            comprehensive_data = {
                'status': 'success',
                'cnpj': self._format_cnpj(cnpj),
                'company_info': {
                    'razao_social': rf_data.get('razao_social', 'N/A'),
                    'nome_fantasia': rf_data.get('nome_fantasia', 'N/A'),
                    'situacao_cadastral': rf_data.get('situacao_cadastral', 'N/A'),
                    'anos_funcionamento': rf_data.get('anos_funcionamento', 0)
                },
                'receita_federal': rf_data,
                'reputation_analysis': reputation_data,
                'legal_analysis': legal_data,
                'social_media_analysis': social_data,
                'risk_analysis': risk_analysis,
                'query_date': datetime.now().isoformat(),
                'system_version': self.system_name
            }
            
            return comprehensive_data
            
        except Exception as e:
            return {
                'status': 'error',
                'error': f'Erro na análise completa: {str(e)}',
                'cnpj': self._format_cnpj(cnpj),
                'query_date': datetime.now().isoformat()
            }
    
    def _calculate_reputation_score(self, places_data: Dict[str, Any]) -> int:
        """Calcula score de reputação baseado nos dados do Google Places"""
        if 'error' in places_data:
            return 60  # Score neutro se não encontrar dados
        
        base_score = 50  # Score neutro
        
        # Ajuste baseado no rating do Google
        rating = places_data.get('g_rating')
        if rating is not None:
            if rating >= 4.5:
                base_score -= 30
            elif rating >= 4.0:
                base_score -= 20
            elif rating >= 3.5:
                base_score -= 10
            elif rating >= 3.0:
                base_score += 0
            elif rating >= 2.0:
                base_score += 20
            else:
                base_score += 40
        
        # Ajuste baseado no número de reviews
        reviews_count = places_data.get('g_user_ratings_total', 0)
        if reviews_count < 5:
            base_score += 15
        elif reviews_count > 50:
            base_score -= 10
        
        # Ajuste baseado em reclamações
        complaints = places_data.get('g_common_complaints', [])
        base_score += len(complaints) * 5
        
        # Status do negócio
        business_status = places_data.get('business_status', 'UNKNOWN')
        if business_status not in ['OPERATIONAL', 'OPEN']:
            base_score += 20
        
        return max(0, min(100, base_score))
    
    def _generate_reputation_summary(self, places_data: Dict[str, Any], score: int) -> str:
        """Gera resumo da reputação"""
        rating = places_data.get('g_rating', 0)
        reviews_count = places_data.get('g_user_ratings_total', 0)
        
        if score <= 25:
            return f"Excelente reputação online com rating {rating}/5 baseado em {reviews_count} avaliações."
        elif score <= 50:
            return f"Boa reputação online com rating {rating}/5 e {reviews_count} avaliações."
        elif score <= 75:
            return f"Reputação moderada com rating {rating}/5. Algumas preocupações identificadas."
        else:
            return f"Reputação preocupante com rating baixo ou ausência de presença online significativa."
    
    def _extract_fraud_indicators(self, criminal_analysis: Dict[str, Any]) -> List[str]:
        """Extrai indicadores específicos de fraude dos dados criminais"""
        indicators = []
        
        crime_types = criminal_analysis.get('tipos_crime', [])
        fraud_keywords = ['fraude', 'estelionato', 'lavagem', 'sonegação', 'fiscal']
        
        for crime_type in crime_types:
            for keyword in fraud_keywords:
                if keyword.lower() in crime_type.lower():
                    indicators.append(f"Processo relacionado a {crime_type}")
                    break
        
        if criminal_analysis.get('processos_ativos', 0) > 0:
            indicators.append("Processos criminais ativos")
        
        if criminal_analysis.get('risk_level') in ['ALTO', 'CRÍTICO']:
            indicators.append("Alto risco criminal identificado")
        
        return indicators
    
    def _calculate_consolidated_risk(self, rf_data: Dict, reputation_data: Dict, legal_data: Dict, social_data: Dict) -> Dict[str, Any]:
        """Calcula risco consolidado baseado em todas as análises"""
        total_score = 0
        risk_factors = []
        
        # Score da Receita Federal (peso 25%)
        if rf_data.get('status') == 'success':
            rf_risk_indicators = rf_data.get('red_flags', [])
            rf_score = min(len(rf_risk_indicators) * 15, 100)
            total_score += rf_score * 0.25
            
            if rf_risk_indicators:
                risk_factors.extend(rf_risk_indicators[:3])  # Top 3
        else:
            total_score += 50 * 0.25  # Score neutro se erro
            risk_factors.append("Dados da Receita Federal indisponíveis")
        
        # Score de reputação (peso 30%)
        if reputation_data.get('status') in ['success', 'warning']:
            rep_score = reputation_data.get('reputation_score', 50)
            if rep_score == 'N/A':
                rep_score = 60
            total_score += rep_score * 0.30
            
            rep_red_flags = reputation_data.get('red_flags', [])
            if rep_red_flags:
                risk_factors.extend(rep_red_flags[:2])  # Top 2
        else:
            total_score += 60 * 0.30  # Score neutro se erro
            risk_factors.append("Dados de reputação indisponíveis")
        
        # Score legal (peso 25%)
        if legal_data.get('status') == 'success':
            legal_score = legal_data.get('risk_score', 0)
            total_score += legal_score * 0.25
            
            fraud_indicators = legal_data.get('fraud_indicators', [])
            if fraud_indicators:
                risk_factors.extend(fraud_indicators[:2])  # Top 2
        else:
            total_score += 30 * 0.25  # Score baixo se erro (benefício da dúvida)
            risk_factors.append("Dados legais indisponíveis")
        
        # Score de redes sociais (peso 20%)
        if social_data.get('status') in ['success', 'warning']:
            social_score = social_data.get('social_presence_score', 50)
            total_score += social_score * 0.20
            
            social_red_flags = social_data.get('red_flags', [])
            if social_red_flags:
                risk_factors.extend(social_red_flags[:2])  # Top 2
        else:
            total_score += 60 * 0.20  # Score neutro se erro
            risk_factors.append("Dados de redes sociais indisponíveis")
        
        # Arredonda score final
        final_score = round(total_score)
        
        # Categoriza risco
        if final_score <= 25:
            risk_level = 'BAIXO'
            recommendation = 'CNPJ aprovado para operações normais'
        elif final_score <= 50:
            risk_level = 'MÉDIO'
            recommendation = 'CNPJ aprovado com monitoramento recomendado'
        elif final_score <= 75:
            risk_level = 'ALTO'
            recommendation = '🚨 CUIDADO - Investigar mais profundamente antes de negociar'
        else:
            risk_level = 'CRÍTICO'
            recommendation = '❌ NÃO RECOMENDADO - Alto risco identificado'
        
        # Próximos passos
        next_steps = []
        if risk_level in ['ALTO', 'CRÍTICO']:
            next_steps.append("Solicitar documentação adicional")
            next_steps.append("Verificar referências comerciais")
            next_steps.append("Consultar advogado se necessário")
        elif risk_level == 'MÉDIO':
            next_steps.append("Monitorar transações iniciais")
            next_steps.append("Verificar referências básicas")
        else:
            next_steps.append("Prosseguir com processo normal")
        
        return {
            'risk_score': final_score,
            'risk_level': risk_level,
            'recommendation': recommendation,
            'risk_factors': list(set(risk_factors))[:5],  # Remove duplicatas, máximo 5
            'next_steps': next_steps,
            'analysis_date': datetime.now().isoformat()
        }


# Funções assíncronas para compatibilidade
async def main():
    """Função de teste"""
    checker = EnhancedDealerFraudChecker()
    
    # Teste com CNPJ válido
    test_cnpj = "11.222.333/0001-81"
    
    print("🔍 Testando Enhanced Dealer Fraud Checker...")
    result = await checker.comprehensive_check(test_cnpj)
    
    print(f"Status: {result.get('status')}")
    print(f"Risco: {result.get('risk_analysis', {}).get('risk_level')}")
    print(f"Score: {result.get('risk_analysis', {}).get('risk_score')}")


if __name__ == "__main__":
    asyncio.run(main())