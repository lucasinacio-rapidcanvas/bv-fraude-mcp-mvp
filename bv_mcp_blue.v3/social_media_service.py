#!/usr/bin/env python3
"""
Social Media Service - Análise de Presença em Redes Sociais
Analisa Facebook, Instagram e outras redes sociais para lojistas de veículos
"""

import json
import random
import time
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional
import urllib.parse
import re


class SocialMediaService:
    """
    Serviço para análise de presença em redes sociais
    Simula busca por Facebook, Instagram, Twitter/X, LinkedIn
    """
    
    def __init__(self):
        """Inicializa o serviço de redes sociais"""
        self.service_name = "Social Media Analyzer v1.0"
        self.supported_platforms = ['facebook', 'instagram', 'twitter', 'linkedin', 'tiktok']
        
        # Simulação de dados para demonstração
        self.sample_companies = {
            "11.222.333/0001-81": {
                "razao_social": "Auto Center Premium Ltda",
                "nome_fantasia": "Premium Veículos",
                "social_profiles": {
                    "facebook": {
                        "exists": True,
                        "url": "facebook.com/premiumveiculos",
                        "followers": 12500,
                        "rating": 4.2,
                        "reviews_count": 89,
                        "last_post": "3 dias atrás",
                        "verified": False,
                        "activity_level": "ALTO"
                    },
                    "instagram": {
                        "exists": True,
                        "url": "instagram.com/premiumveiculos_oficial",
                        "followers": 8900,
                        "following": 445,
                        "posts_count": 1205,
                        "last_post": "1 dia atrás",
                        "verified": False,
                        "activity_level": "MUITO_ALTO",
                        "engagement_rate": 3.4
                    }
                }
            }
        }
    
    def analyze_social_presence(self, cnpj: str, company_name: str = None, 
                              address: str = None) -> Dict[str, Any]:
        """
        Analisa presença nas redes sociais da empresa
        """
        try:
            # Remove formatação do CNPJ
            clean_cnpj = re.sub(r'[^0-9]', '', cnpj)
            
            # Simula tempo de processamento
            time.sleep(random.uniform(1, 3))
            
            # Se temos dados simulados, usa eles
            if clean_cnpj in self.sample_companies:
                return self._process_known_company(clean_cnpj, company_name)
            
            # Caso contrário, gera dados simulados baseados no CNPJ e nome
            return self._generate_social_analysis(clean_cnpj, company_name, address)
            
        except Exception as e:
            return {
                'status': 'error',
                'error': f'Erro na análise de redes sociais: {str(e)}',
                'cnpj': cnpj,
                'query_date': datetime.now().isoformat()
            }
    
    def _process_known_company(self, cnpj: str, company_name: str) -> Dict[str, Any]:
        """Processa empresa com dados conhecidos"""
        company_data = self.sample_companies[cnpj]
        social_profiles = company_data["social_profiles"]
        
        # Calcula métricas gerais
        total_followers = sum([
            profile.get('followers', 0) 
            for profile in social_profiles.values() 
            if profile.get('exists', False)
        ])
        
        platforms_active = len([
            platform for platform, data in social_profiles.items() 
            if data.get('exists', False)
        ])
        
        # Análise de atividade
        activity_analysis = self._analyze_activity_level(social_profiles)
        
        # Score de presença digital
        digital_score = self._calculate_digital_presence_score(social_profiles)
        
        # Red flags das redes sociais
        red_flags = self._identify_social_red_flags(social_profiles)
        
        return {
            'status': 'success',
            'cnpj': f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}",
            'company_name': company_name or company_data["nome_fantasia"],
            'social_presence_score': digital_score,
            'total_followers': total_followers,
            'platforms_active': platforms_active,
            'platforms_found': list(social_profiles.keys()),
            'activity_analysis': activity_analysis,
            'social_profiles': social_profiles,
            'red_flags': red_flags,
            'recommendations': self._generate_social_recommendations(social_profiles, digital_score),
            'analysis_summary': self._generate_social_summary(social_profiles, digital_score),
            'query_date': datetime.now().isoformat(),
            'data_source': 'Social Media APIs (Facebook, Instagram)'
        }
    
    def _generate_social_analysis(self, cnpj: str, company_name: str, address: str) -> Dict[str, Any]:
        """Gera análise simulada baseada nos dados fornecidos"""
        
        # Determina probabilidade de ter redes sociais baseado no tipo de empresa
        has_social_probability = 0.7 if company_name else 0.3
        
        social_profiles = {}
        
        # Facebook
        if random.random() < has_social_probability:
            social_profiles['facebook'] = self._generate_facebook_profile(company_name)
        
        # Instagram
        if random.random() < has_social_probability * 0.8:  # Instagram é um pouco menos comum
            social_profiles['instagram'] = self._generate_instagram_profile(company_name)
        
        # LinkedIn (menos comum para lojistas)
        if random.random() < 0.3:
            social_profiles['linkedin'] = self._generate_linkedin_profile(company_name)
        
        # Twitter/X (menos comum)
        if random.random() < 0.2:
            social_profiles['twitter'] = self._generate_twitter_profile(company_name)
        
        # Se não encontrou nenhuma rede social
        if not social_profiles:
            return {
                'status': 'warning',
                'cnpj': f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}",
                'company_name': company_name or 'N/A',
                'social_presence_score': 85,  # Score alto = risco alto (sem presença)
                'total_followers': 0,
                'platforms_active': 0,
                'platforms_found': [],
                'activity_analysis': {
                    'overall_activity': 'INEXISTENTE',
                    'last_activity': 'N/A',
                    'posting_frequency': 'N/A'
                },
                'social_profiles': {},
                'red_flags': [
                    'Ausência total de presença em redes sociais',
                    'Empresa sem estratégia digital aparente',
                    'Possível falta de transparência online'
                ],
                'recommendations': [
                    'Investigar canais de comunicação alternativos',
                    'Verificar legitimidade através de outros meios',
                    'Considerar empresa tradicional ou com perfil baixo'
                ],
                'analysis_summary': 'Empresa sem presença identificável em redes sociais principais.',
                'query_date': datetime.now().isoformat(),
                'data_source': 'Social Media Search Engine'
            }
        
        # Calcula métricas
        total_followers = sum([
            profile.get('followers', 0) 
            for profile in social_profiles.values() 
            if profile.get('exists', False)
        ])
        
        platforms_active = len(social_profiles)
        activity_analysis = self._analyze_activity_level(social_profiles)
        digital_score = self._calculate_digital_presence_score(social_profiles)
        red_flags = self._identify_social_red_flags(social_profiles)
        
        return {
            'status': 'success',
            'cnpj': f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}",
            'company_name': company_name or 'N/A',
            'social_presence_score': digital_score,
            'total_followers': total_followers,
            'platforms_active': platforms_active,
            'platforms_found': list(social_profiles.keys()),
            'activity_analysis': activity_analysis,
            'social_profiles': social_profiles,
            'red_flags': red_flags,
            'recommendations': self._generate_social_recommendations(social_profiles, digital_score),
            'analysis_summary': self._generate_social_summary(social_profiles, digital_score),
            'query_date': datetime.now().isoformat(),
            'data_source': 'Social Media Search Engine'
        }
    
    def _generate_facebook_profile(self, company_name: str) -> Dict[str, Any]:
        """Gera perfil simulado do Facebook"""
        followers = random.randint(100, 25000)
        rating = round(random.uniform(2.8, 4.9), 1)
        reviews = random.randint(5, 200)
        
        # Atividade recente
        days_since_post = random.randint(1, 30)
        last_post = f"{days_since_post} dias atrás" if days_since_post > 1 else "hoje"
        
        # Nível de atividade baseado na frequência de posts
        if days_since_post <= 3:
            activity_level = "MUITO_ALTO"
        elif days_since_post <= 7:
            activity_level = "ALTO"
        elif days_since_post <= 15:
            activity_level = "MÉDIO"
        else:
            activity_level = "BAIXO"
        
        return {
            'exists': True,
            'url': f"facebook.com/{self._generate_username(company_name)}",
            'followers': followers,
            'rating': rating,
            'reviews_count': reviews,
            'last_post': last_post,
            'verified': followers > 10000 and random.random() < 0.3,
            'activity_level': activity_level,
            'page_type': 'Business',
            'created_date': self._generate_creation_date()
        }
    
    def _generate_instagram_profile(self, company_name: str) -> Dict[str, Any]:
        """Gera perfil simulado do Instagram"""
        followers = random.randint(200, 15000)
        following = random.randint(50, 1000)
        posts = random.randint(50, 2000)
        
        days_since_post = random.randint(1, 20)
        last_post = f"{days_since_post} dias atrás" if days_since_post > 1 else "hoje"
        
        if days_since_post <= 2:
            activity_level = "MUITO_ALTO"
        elif days_since_post <= 5:
            activity_level = "ALTO"
        elif days_since_post <= 10:
            activity_level = "MÉDIO"
        else:
            activity_level = "BAIXO"
        
        # Taxa de engajamento simulada
        engagement_rate = round(random.uniform(1.5, 8.0), 1)
        
        return {
            'exists': True,
            'url': f"instagram.com/{self._generate_username(company_name)}_oficial",
            'followers': followers,
            'following': following,
            'posts_count': posts,
            'last_post': last_post,
            'verified': followers > 5000 and random.random() < 0.2,
            'activity_level': activity_level,
            'engagement_rate': engagement_rate,
            'account_type': 'Business',
            'created_date': self._generate_creation_date()
        }
    
    def _generate_linkedin_profile(self, company_name: str) -> Dict[str, Any]:
        """Gera perfil simulado do LinkedIn"""
        followers = random.randint(50, 5000)
        employees = random.randint(2, 50)
        
        return {
            'exists': True,
            'url': f"linkedin.com/company/{self._generate_username(company_name)}",
            'followers': followers,
            'employees_on_platform': employees,
            'industry': 'Automotive',
            'verified': random.random() < 0.4,
            'activity_level': random.choice(['BAIXO', 'MÉDIO']),
            'company_size': self._determine_company_size(employees)
        }
    
    def _generate_twitter_profile(self, company_name: str) -> Dict[str, Any]:
        """Gera perfil simulado do Twitter/X"""
        followers = random.randint(100, 8000)
        following = random.randint(50, 1500)
        tweets = random.randint(100, 5000)
        
        return {
            'exists': True,
            'url': f"twitter.com/{self._generate_username(company_name)}",
            'followers': followers,
            'following': following,
            'tweets_count': tweets,
            'verified': followers > 3000 and random.random() < 0.15,
            'activity_level': random.choice(['BAIXO', 'MÉDIO', 'ALTO']),
            'account_created': self._generate_creation_date()
        }
    
    def _generate_username(self, company_name: str) -> str:
        """Gera username baseado no nome da empresa"""
        if not company_name:
            return f"empresa{random.randint(1000, 9999)}"
        
        # Limpa o nome da empresa
        clean_name = re.sub(r'[^\w\s]', '', company_name.lower())
        words = clean_name.split()
        
        if len(words) >= 2:
            return f"{words[0]}{words[1]}"
        elif len(words) == 1:
            return f"{words[0]}{random.randint(10, 99)}"
        else:
            return f"lojista{random.randint(100, 999)}"
    
    def _generate_creation_date(self) -> str:
        """Gera data de criação aleatória"""
        start_date = datetime.now() - timedelta(days=random.randint(365, 2555))  # 1-7 anos atrás
        return start_date.strftime("%Y-%m")
    
    def _determine_company_size(self, employees: int) -> str:
        """Determina tamanho da empresa"""
        if employees <= 10:
            return "Pequena Empresa"
        elif employees <= 50:
            return "Média Empresa"
        else:
            return "Grande Empresa"
    
    def _analyze_activity_level(self, social_profiles: Dict) -> Dict[str, Any]:
        """Analisa nível geral de atividade"""
        if not social_profiles:
            return {
                'overall_activity': 'INEXISTENTE',
                'last_activity': 'N/A',
                'posting_frequency': 'N/A'
            }
        
        activity_levels = []
        last_posts = []
        
        for platform, data in social_profiles.items():
            if data.get('exists', False):
                level = data.get('activity_level', 'BAIXO')
                activity_levels.append(level)
                
                last_post = data.get('last_post', 'N/A')
                if 'dia' in last_post or 'hoje' in last_post:
                    last_posts.append(last_post)
        
        # Determina atividade geral
        if 'MUITO_ALTO' in activity_levels:
            overall_activity = 'MUITO_ALTO'
        elif 'ALTO' in activity_levels:
            overall_activity = 'ALTO'
        elif 'MÉDIO' in activity_levels:
            overall_activity = 'MÉDIO'
        else:
            overall_activity = 'BAIXO'
        
        # Última atividade
        if last_posts:
            last_activity = min(last_posts, key=lambda x: int(re.findall(r'\d+', x)[0]) if re.findall(r'\d+', x) else 0)
        else:
            last_activity = 'Há mais de 30 dias'
        
        # Frequência de postagem
        frequency_map = {
            'MUITO_ALTO': 'Diária ou quase diária',
            'ALTO': 'Várias vezes por semana',
            'MÉDIO': 'Semanal',
            'BAIXO': 'Esporádica ou mensal'
        }
        
        return {
            'overall_activity': overall_activity,
            'last_activity': last_activity,
            'posting_frequency': frequency_map.get(overall_activity, 'Indeterminada')
        }
    
    def _calculate_digital_presence_score(self, social_profiles: Dict) -> int:
        """Calcula score de presença digital (0-100, onde 0 é melhor)"""
        if not social_profiles:
            return 85  # Alto risco por não ter presença
        
        base_score = 50  # Score neutro
        
        # Número de plataformas (reduz risco)
        platforms_count = len(social_profiles)
        base_score -= platforms_count * 10
        
        # Analisa cada plataforma
        for platform, data in social_profiles.items():
            if not data.get('exists', False):
                continue
            
            # Seguidores
            followers = data.get('followers', 0)
            if followers > 10000:
                base_score -= 15
            elif followers > 5000:
                base_score -= 10
            elif followers > 1000:
                base_score -= 5
            elif followers < 100:
                base_score += 10
            
            # Atividade
            activity = data.get('activity_level', 'BAIXO')
            if activity == 'MUITO_ALTO':
                base_score -= 10
            elif activity == 'ALTO':
                base_score -= 5
            elif activity == 'BAIXO':
                base_score += 10
            
            # Verificação
            if data.get('verified', False):
                base_score -= 15
            
            # Rating (Facebook)
            rating = data.get('rating')
            if rating:
                if rating >= 4.0:
                    base_score -= 10
                elif rating < 3.0:
                    base_score += 15
        
        return max(0, min(100, base_score))
    
    def _identify_social_red_flags(self, social_profiles: Dict) -> List[str]:
        """Identifica red flags nas redes sociais"""
        red_flags = []
        
        if not social_profiles:
            return [
                'Ausência total de presença em redes sociais',
                'Falta de transparência digital',
                'Possível empresa fantasma ou inativa'
            ]
        
        total_followers = sum([data.get('followers', 0) for data in social_profiles.values()])
        
        # Poucos seguidores em todas as redes
        if total_followers < 500:
            red_flags.append('Baixo engajamento digital')
        
        # Atividade muito baixa
        low_activity = all([
            data.get('activity_level') == 'BAIXO' 
            for data in social_profiles.values()
        ])
        if low_activity:
            red_flags.append('Redes sociais abandonadas ou com baixa atividade')
        
        # Rating baixo no Facebook
        for platform, data in social_profiles.items():
            if platform == 'facebook' and data.get('rating', 5) < 3.0:
                red_flags.append(f'Avaliação baixa no Facebook: {data.get("rating")}/5')
            
            # Conta muito nova
            created_date = data.get('created_date', '')
            if created_date and created_date > '2023-01':
                red_flags.append(f'Conta {platform} muito recente')
        
        return red_flags
    
    def _generate_social_recommendations(self, social_profiles: Dict, score: int) -> List[str]:
        """Gera recomendações baseadas na análise"""
        recommendations = []
        
        if score <= 30:
            recommendations.extend([
                'Empresa com boa presença digital estabelecida',
                'Verificar consistência das informações entre plataformas'
            ])
        elif score <= 50:
            recommendations.extend([
                'Presença digital moderada - verificar atividade recente',
                'Considerar analisar engajamento dos clientes'
            ])
        else:
            recommendations.extend([
                'Investigar métodos alternativos de comunicação',
                'Verificar legitimidade através de canais tradicionais',
                'Considerar risco elevado por falta de transparência digital'
            ])
        
        # Recomendações específicas por plataforma
        if not social_profiles:
            recommendations.append('Buscar informações em diretórios comerciais tradicionais')
        else:
            if 'facebook' in social_profiles:
                recommendations.append('Verificar reviews e comentários no Facebook')
            if 'instagram' in social_profiles:
                recommendations.append('Analisar fotos dos veículos e instalações no Instagram')
        
        return recommendations
    
    def _generate_social_summary(self, social_profiles: Dict, score: int) -> str:
        """Gera resumo da análise social"""
        if not social_profiles:
            return "Empresa sem presença identificável nas principais redes sociais."
        
        platforms_count = len(social_profiles)
        total_followers = sum([data.get('followers', 0) for data in social_profiles.values()])
        
        if score <= 30:
            return f"Empresa com forte presença digital em {platforms_count} plataformas e {total_followers:,} seguidores totais."
        elif score <= 50:
            return f"Presença digital moderada em {platforms_count} plataformas com {total_followers:,} seguidores."
        else:
            return f"Presença digital limitada ou preocupante. Investigação adicional recomendada."


# Função de teste
if __name__ == "__main__":
    service = SocialMediaService()
    
    # Teste
    test_cnpj = "11.222.333/0001-81"
    result = service.analyze_social_presence(test_cnpj, "Auto Center Premium")
    
    print("🔍 Testando Social Media Service...")
    print(f"Status: {result.get('status')}")
    print(f"Score: {result.get('social_presence_score')}")
    print(f"Plataformas: {result.get('platforms_active')}")
    print(f"Seguidores: {result.get('total_followers')}")