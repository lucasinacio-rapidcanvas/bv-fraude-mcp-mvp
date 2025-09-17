#!/usr/bin/env python3
"""
Serviço de Integração com Receita Federal
Baseado na implementação original do projeto BV usando API minhareceita.org
"""

import os
import json
import requests
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import re
import warnings
warnings.filterwarnings('ignore')


class ReceitaFederalService:
    """
    Serviço para consulta de dados da Receita Federal
    Integração com API minhareceita.org com sistema de cache
    """
    
    def __init__(self, base_url: str = "https://minhareceita.org", 
                 cache_file: str = 'rf_cnpj_cache.json', 
                 use_api: bool = True):
        """
        Inicializa o serviço da Receita Federal
        
        Args:
            base_url: URL base da API
            cache_file: Arquivo de cache
            use_api: Se deve usar API ou apenas cache
        """
        self.base_url = base_url
        self.cache_file = cache_file
        self.use_api = use_api
        self.cnpj_cache = self._load_cache()
        
        # CNAEs permitidos para setor automotivo (baseado no projeto original)
        self.allowed_cnaes = [
            4511102, 4511101,  # Comércio de automóveis
            4512902,           # Comércio de veículos
            7490104,           # Atividades de intermediação
            4541203, 4541204,  # Comércio de motocicletas
            7711000            # Locação de veículos
        ]
        
        # Situações cadastrais ativas
        self.active_situations = [
            'ATIVA',
            'ATIVO', 
            'SITUACAO_NORMAL'
        ]
        
        # Timeout para requisições
        self.request_timeout = 10
    
    def _load_cache(self) -> Dict:
        """Carrega cache do arquivo JSON"""
        if os.path.exists(self.cache_file):
            try:
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
            except Exception as e:
                print(f"Erro ao carregar cache RF: {e}")
                return {}
        return {}
    
    def _save_cache(self):
        """Salva cache no arquivo JSON"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(self.cnpj_cache, f, ensure_ascii=False, indent=2)
        except Exception as e:
            print(f"Erro ao salvar cache RF: {e}")
    
    def _clean_cnpj(self, cnpj: str) -> str:
        """Limpa e formata CNPJ"""
        if not cnpj:
            return ""
        
        # Remove caracteres especiais
        cleaned = re.sub(r'[^0-9]', '', str(cnpj))
        
        # Padroniza com 14 dígitos
        cleaned = cleaned.zfill(14)
        
        return cleaned
    
    def _format_cnpj(self, cnpj: str) -> str:
        """Formata CNPJ com máscara"""
        cleaned = self._clean_cnpj(cnpj)
        if len(cleaned) == 14:
            return f"{cleaned[:2]}.{cleaned[2:5]}.{cleaned[5:8]}/{cleaned[8:12]}-{cleaned[12:]}"
        return cnpj
    
    def fetch_cnpj_data(self, cnpj: str) -> Dict[str, Any]:
        """
        Busca dados do CNPJ na Receita Federal
        
        Args:
            cnpj: CNPJ para consulta
            
        Returns:
            Dict com dados da empresa ou erro
        """
        cleaned_cnpj = self._clean_cnpj(cnpj)
        
        if not cleaned_cnpj or len(cleaned_cnpj) != 14:
            return {'error': 'CNPJ inválido'}
        
        # Verifica cache
        if cleaned_cnpj in self.cnpj_cache:
            cached_data = self.cnpj_cache[cleaned_cnpj]
            # Verifica se cache não está muito antigo (30 dias)
            if 'query_date' in cached_data:
                try:
                    cache_date = datetime.fromisoformat(cached_data['query_date'])
                    if datetime.now() - cache_date < timedelta(days=30):
                        return cached_data
                except:
                    pass
        
        # Se não usar API, retorna apenas cache
        if not self.use_api:
            return self.cnpj_cache.get(cleaned_cnpj, {'error': 'Dados não disponíveis no cache'})
        
        # Faz requisição para API
        try:
            url = f"{self.base_url}/{cleaned_cnpj}"
            response = requests.get(url, timeout=self.request_timeout)
            
            if response.status_code == 200:
                data = response.json()
                
                # Processa e padroniza dados
                processed_data = self._process_rf_data(data, cleaned_cnpj)
                
                # Salva no cache
                self.cnpj_cache[cleaned_cnpj] = processed_data
                self._save_cache()
                
                return processed_data
            
            elif response.status_code == 404:
                error_data = {
                    'error': 'CNPJ não encontrado na Receita Federal',
                    'cnpj': cleaned_cnpj,
                    'query_date': datetime.now().isoformat()
                }
                self.cnpj_cache[cleaned_cnpj] = error_data
                self._save_cache()
                return error_data
            
            else:
                error_data = {
                    'error': f'Erro na consulta: HTTP {response.status_code}',
                    'cnpj': cleaned_cnpj,
                    'query_date': datetime.now().isoformat()
                }
                return error_data
                
        except Exception as e:
            error_data = {
                'error': f'Erro na requisição: {str(e)}',
                'cnpj': cleaned_cnpj,
                'query_date': datetime.now().isoformat()
            }
            return error_data
    
    def _process_rf_data(self, raw_data: Dict, cnpj: str) -> Dict[str, Any]:
        """
        Processa dados brutos da RF para formato padronizado
        
        Args:
            raw_data: Dados brutos da API
            cnpj: CNPJ consultado
            
        Returns:
            Dados processados e padronizados
        """
        try:
            
            processed = {
                'cnpj': cnpj,
                'razao_social': raw_data.get('razao_social', ''),
                'nome_fantasia': raw_data.get('nome_fantasia', ''),
                'situacao_cadastral': raw_data.get('descricao_situacao_cadastral', ''),
                'data_situacao_cadastral': raw_data.get('data_situacao_cadastral', ''),
                'data_abertura': raw_data.get('data_inicio_atividade', ''),
                'natureza_juridica': raw_data.get('natureza_juridica', ''),
                'capital_social': raw_data.get('capital_social', 0),
                'porte': raw_data.get('porte', ''),
                'query_date': datetime.now().isoformat()
            }
            
            # Processa endereço
            processed.update(self._process_address(raw_data))
            
            # Processa atividades
            processed.update(self._process_activities(raw_data))
            
            # Processa sócios
            processed['socios'] = self._process_partners(raw_data.get('qsa', []))
            
            # Calcula métricas derivadas
            processed.update(self._calculate_derived_metrics(processed))
            
            return processed
            
        except Exception as e:
            return {
                'error': f'Erro ao processar dados: {str(e)}',
                'cnpj': cnpj,
                'raw_data': raw_data,
                'query_date': datetime.now().isoformat()
            }
    
    def _process_address(self, data: Dict) -> Dict[str, Any]:
        """Processa dados de endereço"""
        # Monta logradouro completo com tipo
        tipo_log = data.get('descricao_tipo_de_logradouro', '')
        logradouro = data.get('logradouro', '')
        logradouro_completo = f"{tipo_log} {logradouro}".strip() if tipo_log else logradouro
        
        address_data = {
            'logradouro': logradouro_completo,
            'numero': data.get('numero', ''),
            'complemento': data.get('complemento', ''),
            'bairro': data.get('bairro', ''),
            'municipio': data.get('municipio', ''),
            'uf': data.get('uf', ''),
            'cep': data.get('cep', ''),
            'endereco_completo': ''
        }
        
        # Monta endereço completo
        parts = []
        if address_data['logradouro']:
            parts.append(address_data['logradouro'])
        if address_data['numero']:
            parts.append(address_data['numero'])
        if address_data['bairro']:
            parts.append(address_data['bairro'])
        if address_data['municipio']:
            parts.append(address_data['municipio'])
        if address_data['uf']:
            parts.append(address_data['uf'])
        
        address_data['endereco_completo'] = ', '.join(parts)
        
        return address_data
    
    def _process_activities(self, data: Dict) -> Dict[str, Any]:
        """Processa atividades da empresa"""
        activities = {
            'cnae_principal': None,
            'cnae_principal_desc': '',
            'cnaes_secundarios': [],
            'allowed_cnae': False
        }
        
        # CNAE principal
        activities['cnae_principal'] = str(data.get('cnae_fiscal', ''))
        activities['cnae_principal_desc'] = data.get('cnae_fiscal_descricao', '')
        
        # CNAEs secundários
        cnaes_secundarios = data.get('cnaes_secundarios', [])
        for cnae in cnaes_secundarios:
            activities['cnaes_secundarios'].append({
                'codigo': str(cnae.get('codigo', '')),
                'descricao': cnae.get('descricao', '')
            })
        
        # Verifica se tem CNAE permitido
        all_cnaes = []
        if activities['cnae_principal']:
            all_cnaes.append(activities['cnae_principal'])
        
        for cnae_sec in activities['cnaes_secundarios']:
            if cnae_sec['codigo']:
                all_cnaes.append(cnae_sec['codigo'])
        
        activities['allowed_cnae'] = any(
            str(cnae).replace('.', '').replace('/', '').replace('-', '') in 
            [str(allowed) for allowed in self.allowed_cnaes] 
            for cnae in all_cnaes
        )
        
        return activities
    
    def _process_partners(self, qsa_data: List) -> List[Dict[str, str]]:
        """Processa quadro societário"""
        partners = []
        
        for socio in qsa_data:
            partners.append({
                'nome': socio.get('nome_socio', ''),
                'qualificacao': socio.get('qualificacao_socio', ''),
                'data_entrada': socio.get('data_entrada_sociedade', ''),
                'cpf_cnpj': socio.get('cnpj_cpf_do_socio', '')
            })
        
        return partners
    
    def _calculate_derived_metrics(self, data: Dict) -> Dict[str, Any]:
        """Calcula métricas derivadas dos dados"""
        metrics = {
            'days_since_opening': 0,
            'years_since_opening': 0,
            'is_active': False,
            'has_fantasia': False,
            'capital_social_range': 'BAIXO',
            'partner_count': 0,
            'risk_indicators': []
        }
        
        # Calcula idade da empresa
        if data.get('data_abertura'):
            try:
                # Tenta diferentes formatos de data
                date_formats = ['%d/%m/%Y', '%Y-%m-%d', '%d-%m-%Y']
                opening_date = None
                
                for fmt in date_formats:
                    try:
                        opening_date = datetime.strptime(data['data_abertura'], fmt)
                        break
                    except:
                        continue
                
                if opening_date:
                    delta = datetime.now() - opening_date
                    metrics['days_since_opening'] = delta.days
                    metrics['years_since_opening'] = round(delta.days / 365.25, 2)
            except Exception as e:
                pass
        
        # Status ativo
        situacao = str(data.get('situacao_cadastral', '')).upper()
        metrics['is_active'] = any(active in situacao for active in self.active_situations)
        
        # Tem nome fantasia
        metrics['has_fantasia'] = bool(data.get('nome_fantasia', '').strip())
        
        # Faixa de capital social
        capital = data.get('capital_social', 0)
        try:
            capital_float = float(str(capital).replace(',', '.'))
            if capital_float < 10000:
                metrics['capital_social_range'] = 'BAIXO'
            elif capital_float < 100000:
                metrics['capital_social_range'] = 'MÉDIO'
            elif capital_float < 1000000:
                metrics['capital_social_range'] = 'ALTO'
            else:
                metrics['capital_social_range'] = 'MUITO_ALTO'
        except:
            metrics['capital_social_range'] = 'INDEFINIDO'
        
        # Número de sócios
        metrics['partner_count'] = len(data.get('socios', []))
        
        # Indicadores de risco
        risk_indicators = []
        
        if not metrics['is_active']:
            risk_indicators.append('Situação cadastral inativa')
        
        if metrics['days_since_opening'] < 180:
            risk_indicators.append('Empresa muito recente (menos de 6 meses)')
        
        if not data.get('allowed_cnae', False):
            risk_indicators.append('CNAE não relacionado ao setor automotivo')
        
        if capital_float < 1000:
            risk_indicators.append('Capital social muito baixo')
        
        if metrics['partner_count'] == 0:
            risk_indicators.append('Sem informações de sócios')
        
        if not data.get('endereco_completo', '').strip():
            risk_indicators.append('Endereço incompleto')
        
        metrics['risk_indicators'] = risk_indicators
        
        return metrics
    
    def add_cnpj_info_to_dataframe(self, df: pd.DataFrame, 
                                  cnpj_col: str = 'cnpj') -> pd.DataFrame:
        """
        Adiciona informações da RF a um DataFrame
        
        Args:
            df: DataFrame com CNPJs
            cnpj_col: Nome da coluna com CNPJs
            
        Returns:
            DataFrame enriquecido
        """
        if cnpj_col not in df.columns:
            print(f"Coluna '{cnpj_col}' não encontrada")
            return df
        
        cnpj_data = []
        unique_cnpjs = df[cnpj_col].unique()
        
        for cnpj in unique_cnpjs:
            rf_data = self.fetch_cnpj_data(str(cnpj))
            cnpj_data.append(rf_data)
        
        # Cria DataFrame com dados da RF
        rf_df = pd.DataFrame(cnpj_data)
        
        # Merge com DataFrame original
        enriched_df = df.merge(
            rf_df, 
            left_on=cnpj_col, 
            right_on='cnpj', 
            how='left',
            suffixes=('', '_rf')
        )
        
        return enriched_df
    
    def get_cache_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        total_entries = len(self.cnpj_cache)
        error_entries = len([k for k, v in self.cnpj_cache.items() if 'error' in v])
        success_entries = total_entries - error_entries
        
        # CNPJs com CNAE permitido
        allowed_cnae_count = len([
            k for k, v in self.cnpj_cache.items() 
            if v.get('allowed_cnae', False) and 'error' not in v
        ])
        
        # CNPJs ativos
        active_count = len([
            k for k, v in self.cnpj_cache.items()
            if v.get('is_active', False) and 'error' not in v
        ])
        
        return {
            'total_cnpjs': total_entries,
            'successful_queries': success_entries,
            'failed_queries': error_entries,
            'success_rate': round(success_entries / total_entries * 100, 2) if total_entries > 0 else 0,
            'allowed_cnae_count': allowed_cnae_count,
            'active_companies': active_count,
            'cache_file_size_mb': round(
                os.path.getsize(self.cache_file) / (1024 * 1024), 2
            ) if os.path.exists(self.cache_file) else 0
        }
    
    def analyze_cnpj_risk(self, cnpj: str) -> Dict[str, Any]:
        """
        Analisa risco de um CNPJ baseado nos dados da RF
        
        Args:
            cnpj: CNPJ para análise
            
        Returns:
            Análise de risco detalhada
        """
        rf_data = self.fetch_cnpj_data(cnpj)
        
        if 'error' in rf_data:
            return {
                'cnpj': cnpj,
                'risk_score': 100,  # Máximo risco se não conseguir consultar
                'risk_level': 'CRÍTICO',
                'risk_factors': [rf_data['error']],
                'recommendation': 'Não foi possível verificar dados na Receita Federal'
            }
        
        # Calcula score de risco (0-100)
        risk_score = 0
        risk_factors = rf_data.get('risk_indicators', [])
        
        # Penalizações
        if not rf_data.get('is_active', False):
            risk_score += 40
        
        if rf_data.get('days_since_opening', 0) < 180:
            risk_score += 25
        
        if not rf_data.get('allowed_cnae', False):
            risk_score += 20
        
        if rf_data.get('capital_social_range') == 'BAIXO':
            risk_score += 10
        
        if rf_data.get('partner_count', 0) == 0:
            risk_score += 5
        
        # Limitação
        risk_score = min(risk_score, 100)
        
        # Categorização
        if risk_score <= 20:
            risk_level = 'BAIXO'
            recommendation = 'CNPJ aprovado para operações normais'
        elif risk_score <= 40:
            risk_level = 'MÉDIO'
            recommendation = 'CNPJ aprovado com monitoramento'
        elif risk_score <= 70:
            risk_level = 'ALTO'
            recommendation = 'CNPJ requer verificação adicional'
        else:
            risk_level = 'CRÍTICO'
            recommendation = 'CNPJ não recomendado para operações'
        
        return {
            'cnpj': cnpj,
            'risk_score': risk_score,
            'risk_level': risk_level,
            'risk_factors': risk_factors,
            'recommendation': recommendation,
            'company_data': rf_data
        }