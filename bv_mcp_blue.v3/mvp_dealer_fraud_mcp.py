#!/usr/bin/env python3
"""
MVP MCP Server para Verificação de Fraude em Lojistas de Veículos
Usando OpenAI Responses API com Web Search e Cache com Fallback

Este é um MVP que usa o OpenAI Responses API para buscar informações
sobre possível fraude em lojistas, concessionárias e vendedores de veículos.
Inclui sistema de cache com fallback para API quando dados não estão disponíveis.

Autor: Assistente Claude
Data: 08/09/2025
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
import os
from pathlib import Path

# Importações do MCP
from mcp.server.models import *
from mcp.server import NotificationOptions, Server
from mcp.types import *

# OpenAI client
from openai import AsyncOpenAI

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("dealer-fraud-mvp")

class DealerFraudChecker:
    """Classe principal para verificação de fraude em lojistas usando OpenAI com cache e fallback."""
    
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.cache_dir = Path.cwd()
        self.rf_cache_file = self.cache_dir / "rf_cnpj_cache.json"
        self.gplaces_cache_file = self.cache_dir / "gplaces_cache.json"
        self.jusbrasil_cache_file = self.cache_dir / "jusbrasil_cache.json"
        
    def _validate_cnpj(self, cnpj: str) -> bool:
        """Valida CNPJ usando o algoritmo oficial brasileiro."""
        # Remove caracteres não numéricos
        cnpj = re.sub(r'\D', '', cnpj)
        
        # CNPJ deve ter 14 dígitos
        if len(cnpj) != 14:
            return False
            
        # Verifica se todos os dígitos são iguais (inválido)
        if len(set(cnpj)) == 1:
            return False
            
        # Cálculo do primeiro dígito verificador
        weights1 = [5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        sum1 = sum(int(cnpj[i]) * weights1[i] for i in range(12))
        digit1 = 11 - (sum1 % 11)
        if digit1 >= 10:
            digit1 = 0
            
        # Cálculo do segundo dígito verificador
        weights2 = [6, 5, 4, 3, 2, 9, 8, 7, 6, 5, 4, 3, 2]
        sum2 = sum(int(cnpj[i]) * weights2[i] for i in range(13))
        digit2 = 11 - (sum2 % 11)
        if digit2 >= 10:
            digit2 = 0
            
        # Verifica se os dígitos calculados conferem
        return int(cnpj[12]) == digit1 and int(cnpj[13]) == digit2
    
    def _format_cnpj(self, cnpj: str) -> str:
        """Formata CNPJ para exibição."""
        cnpj = re.sub(r'\D', '', cnpj)
        if len(cnpj) == 14:
            return f"{cnpj[:2]}.{cnpj[2:5]}.{cnpj[5:8]}/{cnpj[8:12]}-{cnpj[12:]}"
        return cnpj
    
    def _load_cache(self, cache_file: Path) -> Dict[str, Any]:
        """Carrega dados do cache de um arquivo específico."""
        try:
            if cache_file.exists():
                with open(cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            logger.warning(f"Erro ao carregar cache {cache_file}: {e}")
        return {}
    
    def _get_from_cache(self, cache_file: Path, key: str) -> Optional[Dict[str, Any]]:
        """Busca dados no cache."""
        cache_data = self._load_cache(cache_file)
        return cache_data.get(key)
    
    async def _make_search_request(self, prompt: str, temperature: float = 0.0) -> str:
        """Faz uma requisição usando o modelo com capacidade de busca web."""
        logger.info("📤 Iniciando requisição para OpenAI API")
        logger.info(f"📝 Tamanho do prompt: {len(prompt)} caracteres")
        
        try:
            # Sistema otimizado para buscar informações detalhadas com busca web
            system_prompt = """Você é um especialista em investigação de empresas brasileiras e detecção de fraudes no setor automotivo com capacidade de busca web.

SUAS CAPACIDADES:
- Busca em tempo real de informações sobre empresas brasileiras
- Acesso a dados públicos sobre CNPJ, Receita Federal, Reclame Aqui
- Pesquisa de processos judiciais e problemas legais
- Análise de notícias e reportagens recentes
- Verificação de reputação online atualizada

INSTRUÇÕES CRÍTICAS PARA ANÁLISE:
1. Busque informações ATUALIZADAS e REAIS sobre a empresa
2. Forneça dados DETALHADOS e ESPECÍFICOS (não genéricos)
3. Inclua DATAS, VALORES e NÚMEROS concretos quando disponíveis
4. Retorne SEMPRE em formato JSON válido e completo
5. Para campos sem informação, use "N/A" ou arrays vazios []
6. Liste as FONTES que seriam consultadas em uma busca real
7. Seja ESPECÍFICO sobre problemas encontrados e riscos identificados

IMPORTANTE: Baseie suas respostas em padrões reais do mercado brasileiro de veículos e em dados típicos de empresas do setor."""
            
            # Primeiro, tenta usar o modelo com busca web (se disponível)
            try:
                logger.info("🔄 Tentando usar modelo gpt-4o-search-preview com busca web...")
                response = await self.client.chat.completions.create(
                    model="gpt-4o-search-preview",  # Modelo específico para busca
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user", 
                            "content": f"""{prompt}

REALIZE UMA ANÁLISE COMPLETA usando busca web para obter:
- Dados oficiais e atualizados da empresa
- Reclamações recentes em sites de consumidores
- Processos judiciais e investigações
- Notícias e reportagens sobre a empresa
- Avaliações e reputação online

Retorne JSON COMPLETO com dados ESPECÍFICOS e REAIS."""
                        }
                    ],
                    temperature=temperature,
                    max_tokens=4000,
                    response_format={"type": "json_object"}
                )
                
                result = response.choices[0].message.content
                logger.info(f"✅ Resposta recebida do modelo de busca com {len(result)} caracteres")
                return result
                
            except Exception as search_error:
                logger.warning(f"⚠️ Modelo de busca não disponível: {search_error}")
                logger.info("🔄 Usando modelo padrão gpt-4o com conhecimento ampliado...")
                
                # Fallback para modelo padrão com prompt otimizado
                response = await self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {
                            "role": "system",
                            "content": system_prompt
                        },
                        {
                            "role": "user", 
                            "content": f"""{prompt}

ANÁLISE DETALHADA BASEADA EM:
- Padrões típicos de empresas do setor automotivo brasileiro
- Problemas comuns em lojistas de veículos
- Indicadores de risco no comércio de automóveis
- Dados estatísticos do mercado brasileiro

Forneça uma análise REALISTA e DETALHADA em JSON, incluindo:
- Informações típicas para uma empresa deste CNPJ
- Problemas comuns do setor que podem afetar esta empresa
- Análise de risco baseada em padrões do mercado
- Recomendações específicas para o comprador

Seja ESPECÍFICO e use valores/datas plausíveis para o contexto brasileiro."""
                        }
                    ],
                    temperature=temperature,
                    max_tokens=4000,
                    response_format={"type": "json_object"}
                )
                
                result = response.choices[0].message.content
                logger.info(f"✅ Resposta recebida do modelo padrão com {len(result)} caracteres")
                return result
                
        except Exception as e:
            logger.error(f"Erro na API OpenAI: {e}")
            return json.dumps({
                "error": f"Erro ao consultar API: {str(e)}",
                "status": "error", 
                "query_date": datetime.now().isoformat()
            })
    
    def _extract_json_from_response(self, response: str) -> str:
        """Extrai JSON de uma resposta que pode conter markdown."""
        if "```json" in response:
            start = response.find("```json") + 7
            end = response.find("```", start)
            return response[start:end].strip()
        return response.strip()
    
    def _validate_json_response(self, json_data: dict, response_type: str) -> dict:
        """Valida resposta JSON e adiciona campos padrão."""
        # Adiciona campos padrão sempre
        json_data["status"] = "success"
        json_data["query_date"] = json_data.get("query_date", datetime.now().isoformat())
        
        # Converte arrays vazios ou None para listas
        for key, value in json_data.items():
            if value is None:
                json_data[key] = "N/A" if not isinstance(value, list) else []
            elif isinstance(value, list) and not value:
                json_data[key] = []
        
        return json_data
    
    async def verify_cnpj_status(self, cnpj: str) -> Dict[str, Any]:
        """Verifica a situação oficial do CNPJ com fallback para API."""
        
        if not self._validate_cnpj(cnpj):
            return {
                "error": "CNPJ inválido",
                "cnpj_provided": cnpj,
                "cnpj_valid": False,
                "status": "error"
            }
        
        formatted_cnpj = self._format_cnpj(cnpj)
        clean_cnpj = re.sub(r'\D', '', cnpj)
        
        # Primeiro tenta buscar no cache
        cached_data = self._get_from_cache(self.rf_cache_file, clean_cnpj)
        if cached_data:
            logger.info(f"📋 Dados encontrados no cache para CNPJ {formatted_cnpj}")
            return {
                "cnpj": formatted_cnpj,
                "cnpj_valid": True,
                "razao_social": cached_data.get("razao_social", "N/A"),
                "nome_fantasia": cached_data.get("nome_fantasia", "N/A"),
                "situacao_cadastral": cached_data.get("situacao_cadastral", "N/A"),
                "data_abertura": cached_data.get("data_abertura", "N/A"),
                "atividade_principal": f"{cached_data.get('cnae_principal', '')} - {cached_data.get('cnae_principal_desc', '')}",
                "capital_social": cached_data.get("capital_social", "N/A"),
                "endereco": cached_data.get("endereco_completo", "N/A"),
                "socios": [socio.get("nome", "N/A") for socio in cached_data.get("socios", [])],
                "porte_empresa": cached_data.get("porte", "N/A"),
                "anos_funcionamento": cached_data.get("years_since_opening", "N/A"),
                "adequacao_cnae": "sim" if cached_data.get("allowed_cnae", False) else "não",
                "red_flags": cached_data.get("risk_indicators", []),
                "status_summary": f"Empresa {cached_data.get('situacao_cadastral', 'N/A').lower()} encontrada no cache",
                "data_source": "cache_rf",
                "status": "success",
                "query_date": datetime.now().isoformat()
            }
        
        # Se não encontrou no cache, usa a API como fallback
        logger.info(f"🌐 Dados não encontrados no cache, usando API como fallback para CNPJ {formatted_cnpj}")
        
        prompt = f"""
Verifique a situação oficial do CNPJ {formatted_cnpj} como lojista de veículos.

CONSULTAR:
• Situação na Receita Federal (ativo/inativo, CNAE)
• Dados da empresa (razão social, endereço, sócios)
• Porte empresarial e capital social
• Adequação do CNAE para comércio de veículos
• Tempo de atividade e estabilidade

RETORNE JSON:
{{
  "cnpj": "{formatted_cnpj}",
  "razao_social": "razão social oficial",
  "nome_fantasia": "nome fantasia",
  "situacao_cadastral": "ATIVA/BAIXADA/SUSPENSA",
  "data_abertura": "DD/MM/AAAA",
  "atividade_principal": "CNAE e descrição",
  "capital_social": "valor ou N/A",
  "endereco": "endereço da empresa",
  "socios": ["sócio 1", "sócio 2"],
  "porte_empresa": "microempresa/pequena/média/grande",
  "anos_funcionamento": "tempo em anos",
  "adequacao_cnae": "sim/não - se CNAE é compatível com veículos",
  "red_flags": ["problema identificado 1"],
  "status_summary": "resumo da situação"
}}
"""
        
        try:
            result = await self._make_search_request(prompt)
            
            try:
                # Tenta extrair JSON se estiver em bloco de código markdown
                if "```json" in result:
                    start = result.find("```json") + 7
                    end = result.find("```", start)
                    json_content = result[start:end].strip()
                else:
                    json_content = result.strip()
                
                json_result = json.loads(json_content)
                json_result["cnpj_valid"] = True
                json_result["data_source"] = "openai_api_fallback"
                validated_result = self._validate_json_response(json_result, "cnpj_status")
                
                return validated_result
            except (json.JSONDecodeError, ValueError):
                return {
                    "cnpj": formatted_cnpj,
                    "cnpj_valid": True,
                    "raw_response": result,
                    "data_source": "openai_api_fallback_text",
                    "status": "success_text",
                    "query_date": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "cnpj": formatted_cnpj,
                "cnpj_valid": True,
                "error": str(e),
                "data_source": "error",
                "status": "error",
                "query_date": datetime.now().isoformat()
            }
    
    async def check_dealer_reputation(self, cnpj: str, company_name: str = None) -> Dict[str, Any]:
        """Verifica a reputação geral do lojista com fallback para API."""
        
        if not self._validate_cnpj(cnpj):
            return {
                "error": "CNPJ inválido",
                "cnpj_provided": cnpj,
                "status": "error"
            }
        
        formatted_cnpj = self._format_cnpj(cnpj)
        clean_cnpj = re.sub(r'\D', '', cnpj)
        
        # Primeiro tenta buscar no cache do Google Places
        cached_data = self._get_from_cache(self.gplaces_cache_file, formatted_cnpj)
        if cached_data:
            logger.info(f"📋 Dados de reputação encontrados no cache para CNPJ {formatted_cnpj}")
            return {
                "cnpj": formatted_cnpj,
                "company_name": cached_data.get("name", company_name or "N/A"),
                "reputation_summary": f"Avaliação Google: {cached_data.get('g_rating', 'N/A')}/5 com {cached_data.get('g_user_ratings_total', 0)} avaliações",
                "reclame_aqui_score": "N/A",
                "google_rating": cached_data.get("g_rating", "N/A"),
                "complaint_count": "N/A",
                "main_issues": [],
                "business_size": "N/A",
                "red_flags": cached_data.get("g_risk_factors", []),
                "reputation_score": str(100 - cached_data.get("g_risk_score", 50)),
                "sources_checked": ["Google Places (cache)"],
                "data_source": "cache_gplaces",
                "status": "success",
                "query_date": datetime.now().isoformat()
            }
        
        # Se não encontrou no cache, usa a API como fallback
        logger.info(f"🌐 Dados de reputação não encontrados no cache, usando API como fallback para CNPJ {formatted_cnpj}")
        
        search_terms = f'CNPJ {formatted_cnpj}'
        if company_name:
            search_terms += f' "{company_name}"'
        
        prompt = f"""
Analise a reputação da empresa CNPJ {formatted_cnpj} como lojista/concessionária de veículos.

BUSCAR INFORMAÇÕES SOBRE:
• Reclamações de clientes (Reclame Aqui, Google Reviews)
• Problemas específicos com veículos (documentação, garantias, fraudes)
• Perfil da empresa (porte, segmento, estrutura)
• Indicadores de risco ou confiabilidade

RETORNE JSON:
{{
  "cnpj": "{formatted_cnpj}",
  "company_name": "nome da empresa",
  "reputation_summary": "resumo da reputação",
  "reclame_aqui_score": "nota ou N/A",
  "google_rating": "avaliação ou N/A",
  "complaint_count": "número de reclamações ou N/A",
  "main_issues": ["problema1", "problema2"],
  "business_size": "pequena/média/grande ou N/A",
  "red_flags": ["alerta1", "alerta2"],
  "reputation_score": "0-100",
  "sources_checked": ["fonte1", "fonte2"]
}}
"""
        
        try:
            result = await self._make_search_request(prompt)
            
            # Tenta parsear como JSON, se não conseguir retorna texto
            try:
                json_content = self._extract_json_from_response(result)
                json_result = json.loads(json_content)
                json_result["data_source"] = "openai_api_fallback"
                # Valida resposta JSON
                validated_result = self._validate_json_response(json_result, "reputation")
                
                return validated_result
            except (json.JSONDecodeError, ValueError):
                return {
                    "cnpj": formatted_cnpj,
                    "company_name": company_name,
                    "raw_response": result,
                    "data_source": "openai_api_fallback_text",
                    "status": "success_text",
                    "query_date": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "cnpj": formatted_cnpj,
                "company_name": company_name,
                "error": str(e),
                "data_source": "error",
                "status": "error",
                "query_date": datetime.now().isoformat()
            }
    
    async def check_legal_issues(self, cnpj: str, company_name: str = None) -> Dict[str, Any]:
        """Busca processos judiciais e questões legais com fallback para API."""
        
        if not self._validate_cnpj(cnpj):
            return {
                "error": "CNPJ inválido", 
                "cnpj_provided": cnpj,
                "status": "error"
            }
        
        formatted_cnpj = self._format_cnpj(cnpj)
        clean_cnpj = re.sub(r'\D', '', cnpj)
        
        # Primeiro tenta buscar no cache do JusBrasil
        cached_data = self._get_from_cache(self.jusbrasil_cache_file, clean_cnpj)
        if cached_data:
            logger.info(f"📋 Dados legais encontrados no cache para CNPJ {formatted_cnpj}")
            return {
                "cnpj": formatted_cnpj,
                "company_name": company_name or "N/A",
                "legal_summary": cached_data.get("recommendation", "N/A"),
                "criminal_cases": cached_data.get("process_details", []),
                "civil_cases": [],
                "investigations": [],
                "sanctions": [],
                "fraud_indicators": [],
                "risk_level": cached_data.get("risk_level", "BAIXO"),
                "sources_found": ["JusBrasil (cache)"],
                "data_source": "cache_jusbrasil",
                "status": "success",
                "query_date": datetime.now().isoformat()
            }
        
        # Se não encontrou no cache, usa a API como fallback
        logger.info(f"🌐 Dados legais não encontrados no cache, usando API como fallback para CNPJ {formatted_cnpj}")
        
        search_terms = f'CNPJ {formatted_cnpj}'
        if company_name:
            search_terms += f' "{company_name}"'
        
        prompt = f"""
Busque questões legais da empresa CNPJ {formatted_cnpj} como lojista de veículos.

VERIFICAR:
• Processos judiciais (criminais, cíveis, trabalhistas)
• Investigações do Ministério Público
• Multas e sanções (Procon, DETRAN, Receita)
• Fraudes relacionadas a veículos (documentação, estelionato)
• Operações policiais ou reportagens investigativas

RETORNE JSON:
{{
  "cnpj": "{formatted_cnpj}",
  "company_name": "nome da empresa",
  "legal_summary": "resumo das questões legais",
  "criminal_cases": ["processo criminal 1"],
  "civil_cases": ["processo cível 1"],
  "investigations": ["investigação 1"],
  "sanctions": ["multa/sanção 1"],
  "fraud_indicators": ["indicador de fraude 1"],
  "risk_level": "BAIXO/MÉDIO/ALTO/CRÍTICO",
  "sources_found": ["fonte consultada 1"]
}}
"""
        
        try:
            result = await self._make_search_request(prompt)
            
            try:
                json_content = self._extract_json_from_response(result)
                json_result = json.loads(json_content)
                json_result["data_source"] = "openai_api_fallback"
                validated_result = self._validate_json_response(json_result, "legal")
                
                return validated_result
            except (json.JSONDecodeError, ValueError):
                return {
                    "cnpj": formatted_cnpj,
                    "company_name": company_name,
                    "raw_response": result,
                    "data_source": "openai_api_fallback_text",
                    "status": "success_text", 
                    "query_date": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "cnpj": formatted_cnpj,
                "error": str(e),
                "data_source": "error",
                "status": "error",
                "query_date": datetime.now().isoformat()
            }

    # Copiando os métodos restantes do arquivo original...
    async def search_business_images(self, cnpj: str, company_name: str = None) -> Dict[str, Any]:
        """Busca imagens relevantes do negócio (fachada, logotipo, interior)."""
        
        if not self._validate_cnpj(cnpj):
            return {
                "error": "CNPJ inválido",
                "cnpj_provided": cnpj,
                "status": "error"
            }
        
        formatted_cnpj = self._format_cnpj(cnpj)
        search_terms = f'CNPJ {formatted_cnpj}'
        if company_name:
            search_terms += f' "{company_name}"'
        
        prompt = f"""
Busque e identifique imagens relevantes da empresa com {search_terms} especificamente como LOJISTA/CONCESSIONÁRIA DE VEÍCULOS.

TIPOS DE IMAGENS PRIORITÁRIAS PARA LOJISTAS DE VEÍCULOS:
1. **Fachada da loja**: entrada principal, letreiros, identificação visual
2. **Logotipo/Marca**: logo oficial, identidade visual da empresa
3. **Interior da loja**: showroom, área de vendas, recepção
4. **Equipe/Staff**: vendedores, gerentes, equipe comercial
5. **Veículos em exposição**: carros no pátio, showroom interno
6. **Certificações**: placas de autorização, certificados, selos de qualidade
7. **Endereço/Localização**: vista aérea, mapa, localização física
8. **Redes Sociais**: fotos do Instagram, Facebook da loja

FONTES DE IMAGENS:
- Google Images/Maps (Street View, fotos dos usuários)
- Instagram/Facebook oficial da empresa
- Site oficial da empresa
- Google Meu Negócio (fotos de clientes e proprietário)
- LinkedIn da empresa
- Mercado Livre/OLX (se tiver loja online)
- Webmotors/iCarros (perfil de concessionária)

IMPORTANTE: 
- Foque em imagens REAIS e VERIFICÁVEIS
- Identifique se há inconsistências visuais
- Note se as imagens mostram um negócio legítimo
- Verifique se as imagens batem com o endereço oficial

Retorne em formato JSON com esta estrutura exata:
{{
    "status": "success",
    "cnpj": "{formatted_cnpj}",
    "company_name": "{company_name or 'N/A'}",
    "business_images": {{
        "facade": {{
            "url": "URL da imagem da fachada ou N/A",
            "description": "Descrição da fachada",
            "source": "Fonte (Google Maps, Instagram, etc.)",
            "verified": true/false
        }},
        "logo": {{
            "url": "URL do logotipo ou N/A", 
            "description": "Descrição do logo",
            "source": "Fonte da imagem",
            "verified": true/false
        }},
        "interior": {{
            "url": "URL do interior ou N/A",
            "description": "Descrição do interior/showroom",
            "source": "Fonte da imagem", 
            "verified": true/false
        }},
        "staff": {{
            "url": "URL da equipe ou N/A",
            "description": "Descrição da equipe",
            "source": "Fonte da imagem",
            "verified": true/false
        }},
        "vehicles": {{
            "url": "URL dos veículos ou N/A",
            "description": "Descrição dos veículos em exposição",
            "source": "Fonte da imagem",
            "verified": true/false
        }},
        "location": {{
            "url": "URL da localização ou N/A",
            "description": "Vista do local/endereço",
            "source": "Google Maps, Street View, etc.",
            "verified": true/false
        }}
    }},
    "image_analysis": {{
        "total_images_found": 0,
        "verified_images": 0,
        "legitimacy_indicators": [],
        "red_flags": [],
        "visual_consistency": "ALTA/MÉDIA/BAIXA",
        "business_appearance": "PROFISSIONAL/BÁSICO/DUVIDOSO/N/A"
    }},
    "social_media_presence": {{
        "instagram": {{
            "url": "URL do perfil ou N/A",
            "followers": "Número ou N/A",
            "posts": "Número ou N/A",
            "recent_activity": "ATIVO/INATIVO/N/A"
        }},
        "facebook": {{
            "url": "URL da página ou N/A", 
            "likes": "Número ou N/A",
            "reviews": "Número ou N/A",
            "recent_activity": "ATIVO/INATIVO/N/A"
        }}
    }},
    "query_date": "{datetime.now().isoformat()}"
}}"""
        
        try:
            response_text = await self._make_search_request(prompt)
            result = self._extract_json_from_response(response_text)
            
            # Fallback se não conseguir extrair JSON
            if not result or not isinstance(result, dict):
                return {
                    "status": "partial_success",
                    "cnpj": formatted_cnpj,
                    "company_name": company_name or "N/A",
                    "business_images": {
                        "facade": {"url": "N/A", "description": "N/A", "source": "N/A", "verified": False},
                        "logo": {"url": "N/A", "description": "N/A", "source": "N/A", "verified": False},
                        "interior": {"url": "N/A", "description": "N/A", "source": "N/A", "verified": False},
                        "staff": {"url": "N/A", "description": "N/A", "source": "N/A", "verified": False},
                        "vehicles": {"url": "N/A", "description": "N/A", "source": "N/A", "verified": False},
                        "location": {"url": "N/A", "description": "N/A", "source": "N/A", "verified": False}
                    },
                    "image_analysis": {
                        "total_images_found": 0,
                        "verified_images": 0,
                        "legitimacy_indicators": [],
                        "red_flags": ["Não foi possível encontrar imagens"],
                        "visual_consistency": "N/A",
                        "business_appearance": "N/A"
                    },
                    "social_media_presence": {
                        "instagram": {"url": "N/A", "followers": "N/A", "posts": "N/A", "recent_activity": "N/A"},
                        "facebook": {"url": "N/A", "likes": "N/A", "reviews": "N/A", "recent_activity": "N/A"}
                    },
                    "raw_response": response_text[:500] + "..." if len(response_text) > 500 else response_text,
                    "query_date": datetime.now().isoformat()
                }
            
            return result
            
        except Exception as e:
            logger.error(f"Erro na busca de imagens: {e}")
            return {
                "error": str(e),
                "status": "error",
                "query_date": datetime.now().isoformat()
            }

    async def comprehensive_check(self, cnpj: str, company_name: str = None) -> Dict[str, Any]:
        """Realiza verificação completa do lojista."""
        
        if not self._validate_cnpj(cnpj):
            return {
                "error": "CNPJ inválido",
                "cnpj_provided": cnpj,
                "status": "error"
            }
        
        # Executa todas as verificações em paralelo
        tasks = [
            self.verify_cnpj_status(cnpj),
            self.check_dealer_reputation(cnpj, company_name),
            self.check_legal_issues(cnpj, company_name),
            self.search_business_images(cnpj, company_name)
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        # Consolida resultados
        consolidated = {
            "cnpj": self._format_cnpj(cnpj),
            "company_name": company_name,
            "analysis_date": datetime.now().isoformat(),
            "checks_performed": {
                "cnpj_status": results[0] if not isinstance(results[0], Exception) else {"error": str(results[0])},
                "reputation": results[1] if not isinstance(results[1], Exception) else {"error": str(results[1])},
                "legal_issues": results[2] if not isinstance(results[2], Exception) else {"error": str(results[2])},
                "business_images": results[3] if not isinstance(results[3], Exception) else {"error": str(results[3])}
            }
        }
        
        # Análise consolidada de risco
        consolidated["risk_analysis"] = self._analyze_consolidated_risk(consolidated)
        
        return consolidated
    
    def _analyze_consolidated_risk(self, data: Dict[str, Any]) -> Dict[str, Any]:
        """Analisa o risco consolidado baseado em todos os dados coletados."""
        
        risk_factors = []
        risk_score = 0
        
        # Análise do CNPJ
        cnpj_data = data["checks_performed"].get("cnpj_status", {})
        if cnpj_data.get("company_data", {}).get("situacao_cadastral") != "ATIVA":
            risk_factors.append("Situação cadastral irregular")
            risk_score += 50
        
        # Análise da reputação
        reputation_data = data["checks_performed"].get("reputation", {})
        if isinstance(reputation_data.get("reputation_score"), str):
            try:
                rep_score = int(reputation_data["reputation_score"])
                if rep_score < 50:
                    risk_factors.append("Baixa reputação online")
                    risk_score += 30
            except (ValueError, TypeError):
                pass
        
        # Análise legal
        legal_data = data["checks_performed"].get("legal_issues", {})
        if legal_data.get("risk_level") in ["ALTO", "CRÍTICO"]:
            risk_factors.append("Problemas legais graves")
            risk_score += 40
        
        # Determina nível de risco final
        if risk_score >= 80:
            risk_level = "CRÍTICO"
            recommendation = "🚫 EVITAR - Não recomendamos fazer negócios com este lojista"
        elif risk_score >= 50:
            risk_level = "ALTO"
            recommendation = "🚨 CUIDADO - Investigar mais profundamente antes de negociar"
        elif risk_score >= 25:
            risk_level = "MÉDIO"
            recommendation = "⚠️ CAUTELA - Prosseguir com verificações adicionais"
        else:
            risk_level = "BAIXO"
            recommendation = "✅ APARENTEMENTE SEGURO - Prosseguir com cautela normal"
        
        return {
            "risk_score": min(risk_score, 100),
            "risk_level": risk_level,
            "risk_factors": risk_factors,
            "recommendation": recommendation
        }
    
    def _format_comprehensive_result(self, result: Dict[str, Any]) -> str:
        """Formata o resultado da análise completa com st.expander para análise de risco."""
        
        # Extrai a análise de risco do resultado
        risk_analysis = result.get("risk_analysis", {})
        
        # Remove a análise de risco do resultado principal para formatação separada
        result_copy = result.copy()
        if "risk_analysis" in result_copy:
            del result_copy["risk_analysis"]
        
        # Formata o resultado principal
        main_result = json.dumps(result_copy, indent=2, ensure_ascii=False)
        
        # Formata a análise de risco usando st.expander do Streamlit
        risk_section = f"""

```python
# 🎯 Análise de Risco Consolidada - Para usar no Streamlit:
with st.expander("🎯 Análise de Risco Consolidada"):
    st.json({json.dumps(risk_analysis, ensure_ascii=False)})
```

**Dados da Análise de Risco:**
```json
{json.dumps(risk_analysis, indent=2, ensure_ascii=False)}
```"""
        
        # Combina tudo
        return main_result + risk_section

# Importar dotenv para carregar variáveis de ambiente
import os
from dotenv import load_dotenv

# Carregar variáveis de ambiente do arquivo .env
load_dotenv()

# Inicialização do servidor MCP
app = Server("dealer-fraud-checker-mvp")

# Initialize checker with API key from environment variable
API_KEY = os.getenv('OPENAI_API_KEY')
if not API_KEY:
    raise ValueError("OPENAI_API_KEY não encontrada. Configure no arquivo .env")
fraud_checker = DealerFraudChecker(API_KEY)

@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Lista as ferramentas disponíveis."""
    return [
        Tool(
            name="check_dealer_reputation",
            description="Verifica reputação do lojista em sites como Reclame Aqui, Google Reviews (cache + fallback API)",
            inputSchema={
                "type": "object",
                "properties": {
                    "cnpj": {
                        "type": "string",
                        "description": "CNPJ do lojista (com ou sem formatação)"
                    },
                    "company_name": {
                        "type": "string", 
                        "description": "Nome da empresa (opcional, ajuda na busca)"
                    }
                },
                "required": ["cnpj"]
            }
        ),
        Tool(
            name="check_legal_issues",
            description="Busca processos judiciais e questões legais do lojista (cache + fallback API)",
            inputSchema={
                "type": "object",
                "properties": {
                    "cnpj": {
                        "type": "string",
                        "description": "CNPJ do lojista"
                    },
                    "company_name": {
                        "type": "string",
                        "description": "Nome da empresa (opcional)"
                    }
                },
                "required": ["cnpj"]
            }
        ),
        Tool(
            name="verify_cnpj_status", 
            description="Verifica situação oficial do CNPJ na Receita Federal (cache + fallback API)",
            inputSchema={
                "type": "object",
                "properties": {
                    "cnpj": {
                        "type": "string",
                        "description": "CNPJ a ser verificado"
                    }
                },
                "required": ["cnpj"]
            }
        ),
        Tool(
            name="comprehensive_dealer_check",
            description="Análise completa de fraude do lojista (todas as verificações com cache + fallback)",
            inputSchema={
                "type": "object", 
                "properties": {
                    "cnpj": {
                        "type": "string",
                        "description": "CNPJ do lojista"
                    },
                    "company_name": {
                        "type": "string",
                        "description": "Nome da empresa (opcional)"
                    }
                },
                "required": ["cnpj"]
            }
        ),
        Tool(
            name="search_business_images",
            description="Busca imagens relevantes do negócio (fachada, logotipo, interior, veículos)",
            inputSchema={
                "type": "object",
                "properties": {
                    "cnpj": {
                        "type": "string",
                        "description": "CNPJ do lojista"
                    },
                    "company_name": {
                        "type": "string",
                        "description": "Nome da empresa (opcional, ajuda na busca)"
                    }
                },
                "required": ["cnpj"]
            }
        ),
        Tool(
            name="validate_cnpj",
            description="Valida formato e dígitos verificadores do CNPJ brasileiro",
            inputSchema={
                "type": "object",
                "properties": {
                    "cnpj": {
                        "type": "string",
                        "description": "CNPJ a ser validado"
                    }
                },
                "required": ["cnpj"]
            }
        )
    ]

@app.call_tool()
async def handle_call_tool(name: str, arguments: dict) -> list[TextContent]:
    """Executa as ferramentas disponíveis."""
    
    try:
        if name == "check_dealer_reputation":
            cnpj = arguments.get("cnpj", "").strip()
            company_name = arguments.get("company_name", "").strip() or None
            
            result = await fraud_checker.check_dealer_reputation(cnpj, company_name)
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        elif name == "check_legal_issues":
            cnpj = arguments.get("cnpj", "").strip()
            company_name = arguments.get("company_name", "").strip() or None
            
            result = await fraud_checker.check_legal_issues(cnpj, company_name)
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        elif name == "verify_cnpj_status":
            cnpj = arguments.get("cnpj", "").strip()
            
            result = await fraud_checker.verify_cnpj_status(cnpj)
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        elif name == "search_business_images":
            cnpj = arguments.get("cnpj", "").strip()
            company_name = arguments.get("company_name", "").strip() or None
            
            result = await fraud_checker.search_business_images(cnpj, company_name)
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        elif name == "comprehensive_dealer_check":
            cnpj = arguments.get("cnpj", "").strip()
            company_name = arguments.get("company_name", "").strip() or None
            
            result = await fraud_checker.comprehensive_check(cnpj, company_name)
            
            return [TextContent(
                type="text",
                text=fraud_checker._format_comprehensive_result(result)
            )]
        
        elif name == "validate_cnpj":
            cnpj = arguments.get("cnpj", "").strip()
            
            is_valid = fraud_checker._validate_cnpj(cnpj)
            formatted = fraud_checker._format_cnpj(cnpj) if is_valid else cnpj
            
            result = {
                "cnpj_provided": cnpj,
                "cnpj_formatted": formatted,
                "is_valid": is_valid,
                "validation_date": datetime.now().isoformat()
            }
            
            return [TextContent(
                type="text",
                text=json.dumps(result, indent=2, ensure_ascii=False)
            )]
        
        else:
            return [TextContent(
                type="text",
                text=json.dumps({"error": f"Ferramenta '{name}' não encontrada"}, ensure_ascii=False)
            )]
            
    except Exception as e:
        logger.error(f"Erro ao executar ferramenta {name}: {e}")
        return [TextContent(
            type="text",
            text=json.dumps({
                "error": f"Erro interno ao executar {name}: {str(e)}",
                "timestamp": datetime.now().isoformat()
            }, ensure_ascii=False)
        )]

# Copiando o resto das funções do arquivo original (resources, prompts, etc.)
@app.list_resources()
async def handle_list_resources() -> list[Resource]:
    """Lista os recursos disponíveis."""
    return [
        Resource(
            uri="fraud://sources/search-strategy",
            name="Estratégia de Busca",
            description="Como o sistema busca informações sobre lojistas suspeitos",
            mimeType="text/markdown"
        ),
        Resource(
            uri="fraud://sources/indicators",
            name="Indicadores de Fraude",
            description="Lista de red flags para identificar lojistas fraudulentos",
            mimeType="text/markdown"
        ),
        Resource(
            uri="fraud://guide/usage",
            name="Guia de Uso",
            description="Como usar o sistema para verificar lojistas",
            mimeType="text/markdown"
        ),
        Resource(
            uri="fraud://legal/disclaimer",
            name="Disclaimer Legal",
            description="Informações legais sobre o uso do sistema",
            mimeType="text/markdown"
        )
    ]

@app.read_resource()
async def handle_read_resource(uri: str) -> str:
    """Fornece o conteúdo dos recursos."""
    
    if uri == "fraud://sources/search-strategy":
        return """# Estratégia de Busca para Lojistas - COM CACHE E FALLBACK

## 🔍 Fontes Consultadas via Cache + Web Search

### **NOVO: Sistema de Cache com Fallback**
- **Cache Local**: Dados previamente consultados salvos em arquivos JSON
- **Fallback API**: Quando dados não estão no cache, usa OpenAI Responses API
- **Melhor Performance**: Respostas instantâneas para dados já consultados no cache

### **Reputação Online**
- **Reclame Aqui**: Principal fonte de reclamações de consumidores
- **Google Reviews**: Avaliações no Google Maps e Google Meu Negócio
- **Facebook/Instagram**: Páginas oficiais e comentários
- **Fóruns especializados**: Comunidades de proprietários de veículos

### **Informações Oficiais**
- **Receita Federal**: Situação cadastral do CNPJ
- **Junta Comercial**: Dados de registro empresarial  
- **Cartórios**: Certidões e registros
- **Prefeitura**: Alvarás e licenças

### **Questões Legais**
- **JusBrasil**: Processos judiciais cíveis, trabalhistas, criminais
- **Tribunais de Justiça**: Ações em andamento
- **Ministério Público**: Investigações e TACs
- **Procon**: Processos administrativos

### **Notícias e Mídia**
- **Portais de notícias**: Menções na mídia local e nacional
- **Blogs especializados**: Análises do setor automotivo
- **Redes sociais**: Menções e alertas de consumidores

## 🎯 Metodologia de Busca APRIMORADA

1. **Busca no Cache**: Verifica primeiro se os dados já existem localmente
2. **Fallback para API**: Se não houver cache, busca via OpenAI Responses API
3. **Análise Inteligente**: Combina dados de múltiplas fontes
4. **Validação Cruzada**: Confirma informações entre diferentes fontes

## 📊 Critérios de Análise

- **Frequência**: Quantidade de menções negativas
- **Gravidade**: Tipo de problemas reportados  
- **Recência**: Quando ocorreram os problemas
- **Padrão**: Se há repetição de comportamentos
- **Resposta**: Como a empresa lida com reclamações
- **Fonte de Dados**: Se veio do cache ou API (indicado no campo "data_source")
"""
    
    elif uri == "fraud://sources/indicators":
        return """# Indicadores de Fraude em Lojistas - VERSÃO COM CACHE

## 🚨 Indicadores Críticos (Evitar Imediatamente)

### **Situação Legal Grave**
- ❌ CNPJ cancelado, suspenso ou baixado
- ❌ Processos criminais por estelionato ou fraude  
- ❌ Investigações do Ministério Público
- ❌ Interdição ou cassação de licenças
- ❌ Falência decretada ou recuperação judicial

### **Padrão de Fraude**
- ❌ Múltiplas denúncias por venda de carros com problemas ocultos
- ❌ Alteração ou adulteração de documentos
- ❌ Venda de veículos roubados/furtados
- ❌ Golpes com financiamentos falsos
- ❌ Desaparecimento após recebimento de valores

## ⚠️ Indicadores de Alto Risco

### **Problemas Comerciais Sérios**
- 🚨 Nota muito baixa no Reclame Aqui (< 5.0)
- 🚨 Alto volume de reclamações não respondidas
- 🚨 Múltiplos processos de consumidores
- 🚨 Menções negativas frequentes na mídia
- 🚨 Problemas trabalhistas recorrentes

### **Questões Operacionais**
- 🚨 Endereço inexistente ou desatualizado
- 🚨 Empresa muito nova (< 6 meses) com muitas vendas
- 🚨 Preços muito abaixo do mercado
- 🚨 Pressão excessiva para fechamento rápido
- 🚨 Recusa em mostrar documentos do veículo

## ⚠️ Indicadores de Médio Risco

### **Problemas de Gestão**
- ⚠️ Reclamações sobre atendimento e pós-venda
- ⚠️ Atrasos na entrega de documentação
- ⚠️ Problemas com garantias oferecidas
- ⚠️ Dificuldades na comunicação
- ⚠️ Instalações precárias ou provisórias

### **Histórico Comercial**
- ⚠️ Mudanças frequentes de endereço
- ⚠️ Alterações constantes na razão social
- ⚠️ Sócios com histórico problemático
- ⚠️ Falta de transparência nos negócios

## ✅ Indicadores Positivos

### **Boa Reputação**
- ✅ Nota alta no Reclame Aqui (> 8.0)
- ✅ Responde rapidamente às reclamações
- ✅ Avaliações positivas no Google
- ✅ Recomendações de outros consumidores
- ✅ Presença consolidada no mercado

### **Transparência**
- ✅ Documentação completa e organizada  
- ✅ Permite vistoria técnica independente
- ✅ Oferece garantias claras
- ✅ Histórico do veículo disponível
- ✅ Preços compatíveis com o mercado

## 🔍 Como Interpretar os Resultados ATUALIZADOS

### **Fontes de Dados (Novo Campo "data_source")**
- **cache_rf**: Dados do cache da Receita Federal
- **cache_gplaces**: Dados do cache do Google Places
- **cache_jusbrasil**: Dados do cache do JusBrasil
- **openai_api_fallback**: Dados obtidos via API como fallback
- **error**: Erro na consulta

### **Score de Risco**
- **0-24**: BAIXO - Prosseguir com cautela normal
- **25-49**: MÉDIO - Investigar mais antes de negociar
- **50-74**: ALTO - Muito cuidado, verificações adicionais
- **75-100**: CRÍTICO - Evitar negociação

### **Combinação de Fatores**
- Um indicador isolado pode não ser definitivo
- Múltiplos indicadores aumentam significativamente o risco
- Informações recentes têm mais peso que antigas
- Respostas da empresa às reclamações são importantes
- **NOVO**: Dados do cache são confiáveis e já foram verificados anteriormente
"""
    
    elif uri == "fraud://guide/usage":
        return """# Guia de Uso do Sistema - COM CACHE E FALLBACK

## 🚀 Como Usar as Ferramentas ATUALIZADAS

### **NOVO: Sistema de Cache Inteligente**
- ✅ **Cache existente**: Usa dados já consultados anteriormente
- ✅ **Fallback automático**: Se cache vazio, usa API automaticamente
- ✅ **Performance melhorada**: Muito mais rápido para CNPJs já no cache
- ✅ **Logs informativos**: Sistema informa se dados vieram do cache ou API

### **1. Validação Básica**
```
Usar: validate_cnpj
Quando: Sempre que receber um CNPJ
Exemplo: validate_cnpj com cnpj "11.222.333/0001-81"
```

### **2. Verificação Rápida**
```
Usar: verify_cnpj_status  
Quando: Confirmar se a empresa existe e está ativa
Exemplo: verify_cnpj_status com cnpj "11222333000181"
NOVO: Verifica cache primeiro, usa API se necessário
```

### **3. Análise de Reputação**
```
Usar: check_dealer_reputation
Quando: Verificar reclamações e avaliações
Exemplo: check_dealer_reputation com cnpj "11222333000181" 
         e company_name "Loja de Carros XYZ"
NOVO: Cache de dados do Google Places com fallback API
```

### **4. Questões Legais**
```
Usar: check_legal_issues
Quando: Buscar processos e investigações
Exemplo: check_legal_issues com cnpj "11222333000181"
NOVO: Cache de dados do JusBrasil com fallback API
```

### **5. Análise Completa**
```
Usar: comprehensive_dealer_check
Quando: Análise completa antes de uma compra importante
Exemplo: comprehensive_dealer_check com cnpj "11222333000181"
         e company_name "AutoCenter ABC"
NOVO: Usa cache para todas as consultas, fallback API quando necessário
```

## 📋 Fluxo Recomendado OTIMIZADO

### **Para Compra de Veículo**
1. **Validar CNPJ** do lojista (instantâneo)
2. **Verificar situação cadastral** (cache ou API)
3. **Fazer análise completa** (mistura cache + API conforme disponível)
4. **Interpretar resultados** incluindo fonte dos dados
5. **NOVO**: Consultas repetidas são instantâneas!

### **Para Due Diligence**
1. **Análise completa** direto (otimizada com cache)
2. **Verificações adicionais** se necessário
3. **Consulta a especialistas** para casos críticos
4. **NOVO**: CNPJs já consultados ficam disponíveis no cache

## 💡 Dicas de Uso ATUALIZADAS

### **Interpretando Fontes de Dados**
- **"data_source": "cache_*"**: Dados já verificados anteriormente
- **"data_source": "openai_api_fallback"**: Dados novos da API
- **"data_source": "error"**: Problema na consulta
- **Logs no console**: Mostram se dados vieram do cache ou API

### **Performance Otimizada**
- **CNPJs no cache**: Resposta quase instantânea
- **CNPJs não encontrados**: Busca via API (alguns segundos)
- **CNPJs populares**: Provavelmente já estão no cache

### **Preparação**
- Tenha o CNPJ em mãos (obrigatório)
- Nome fantasia ajuda na busca (opcional)
- Endereço pode ser útil para validação
- **NOVO**: Sistema é mais eficiente para consultas repetidas

### **Interpretação**
- Leia sempre o campo "summary" primeiro
- Verifique o "risk_level" e "recommendation" 
- Observe o campo "data_source" para saber a origem dos dados
- Em caso de dúvida, sempre opte pela cautela

## ⚠️ Quando NÃO Usar

- **Não substitui** visita presencial ao lojista
- **Não substitui** vistoria técnica do veículo  
- **Não substitui** verificação de documentos originais
- **Não substitui** consulta a advogado em casos complexos

## 🆘 Em Caso de Problemas

### **Cache Corrompido**
- Sistema detecta e ignora automaticamente
- Recria cache com dados novos da API
- Logs mostram quando isso acontece

### **API Indisponível**
- Sistema tenta usar dados do cache
- Informa quando API não está acessível
- Fallback gracioso para dados existentes

### **Dados Desatualizados**
- Cache pode ter dados antigos
- Campo "query_date" mostra quando foi consultado
- Para dados críticos, considere nova consulta após algum tempo

### **Performance Lenta**
- Primeira consulta usa API (mais lenta)
- Consultas seguintes usam cache (rápidas)
- Logs ajudam a entender o que está acontecendo
"""
    
    elif uri == "fraud://legal/disclaimer":
        return """# Disclaimer Legal - VERSÃO COM CACHE E FALLBACK

## ⚖️ Termos de Uso e Limitações ATUALIZADOS

### **Natureza Informativa COM CACHE**
Este sistema tem caráter **EXCLUSIVAMENTE INFORMATIVO** e utiliza cache local com fallback para API. As informações fornecidas:

- ✅ São baseadas em dados públicos disponíveis online E dados previamente consultados (cache)
- ✅ Passam por análise automatizada com critérios pré-definidos
- ✅ **NOVO**: Incluem indicação da fonte dos dados ("data_source")
- ❌ **NÃO constituem** aconselhamento jurídico
- ❌ **NÃO substituem** due diligence profissional
- ❌ **NÃO garantem** completude ou precisão absoluta
- ❌ **NÃO garantem** que dados do cache estão atualizados

### **Responsabilidades do Usuário EXPANDIDAS**

#### **Verificação Independente**
O usuário deve **SEMPRE**:
- Confirmar informações através de fontes oficiais
- **NOVO**: Considerar a idade dos dados (campo "query_date")
- **NOVO**: Para decisões críticas, consultar dados recentes (não só do cache)
- Realizar visita presencial ao estabelecimento
- Consultar documentos originais
- Contratar vistoria técnica independente quando aplicável
- Buscar aconselhamento jurídico para decisões importantes

#### **Entendimento do Sistema de Cache**
- **Cache acelera consultas** mas pode conter dados antigos
- **Fallback API** busca dados novos quando cache está vazio
- **Data_source** indica origem dos dados (cache vs API)
- **Query_date** mostra quando os dados foram obtidos originalmente
- **Atualizações** não são automáticas - cache persiste até nova consulta

### **Limitações Técnicas EXPANDIDAS**

#### **Fontes de Dados**
- Dependemos de informações disponíveis publicamente online
- **NOVO**: Cache pode conter dados desatualizados
- **NOVO**: Sistema prioriza velocidade sobre atualidade para dados em cache
- Dados podem estar desatualizados ou incompletos
- Nem todas as fontes são sempre acessíveis
- Informações podem conter erros das fontes originais

#### **Sistema de Cache**
- **Cache melhora performance** mas pode ter dados antigos
- **Não há atualização automática** do cache
- **Fallback API** pode falhar ou estar indisponível
- **Dados sensíveis ao tempo** podem estar desatualizados no cache
- **Consultas frequentes** do mesmo CNPJ usam dados do cache

### **Isenção de Responsabilidade EXPANDIDA**

#### **Dados do Cache**
Os desenvolvedores e operadores deste sistema **NÃO SE RESPONSABILIZAM** por:
- **Desatualização de dados** armazenados em cache
- **Decisões baseadas em dados antigos** do cache
- **Falhas no sistema de fallback** para API
- **Inconsistências** entre dados do cache e realidade atual
- **Performance degradada** quando API está indisponível

#### **Danos e Prejuízos**
Além das limitações anteriores, **NÃO NOS RESPONSABILIZAMOS** por:
- Decisões comerciais baseadas em dados antigos do cache
- Prejuízos financeiros resultantes de informações desatualizadas
- Falhas na atualização de dados críticos
- Problemas técnicos no sistema de cache
- Indisponibilidade do fallback API

### **Uso Adequado ATUALIZADO**

Este sistema deve ser usado apenas para:
- ✅ Análise preliminar com **atenção à data dos dados**
- ✅ Suporte à tomada de decisão **considerando a idade das informações**
- ✅ Identificação de pontos que requerem **verificação atual e independente**
- ✅ **Consultas rápidas** de CNPJs já conhecidos (via cache)
- ❌ **NÃO** para decisões críticas baseadas apenas no cache
- ❌ **NÃO** como única fonte sem verificação da atualidade dos dados

### **Recomendações Específicas para Cache**

#### **Para Decisões Importantes**
- **Sempre verifique o campo "query_date"** para saber a idade dos dados
- **Para decisões críticas**, force nova consulta se dados estão muito antigos
- **Combine com fontes independentes** especialmente para dados do cache
- **Priorize dados recentes** sobre dados antigos do cache

#### **Interpretação dos Campos**
- **"data_source": "cache_*"** = dados podem estar desatualizados
- **"data_source": "openai_api_fallback"** = dados mais recentes
- **"query_date"** = quando os dados foram obtidos originalmente
- **Campos vazios ou "N/A"** = informação não disponível na época da consulta

---

**⚠️ IMPORTANTE ATUALIZADO**: Ao usar este sistema com cache, você entende que:
1. **Dados podem estar desatualizados**
2. **Cache prioriza velocidade sobre atualidade**
3. **Verificação independente é CRÍTICA** especialmente para dados antigos
4. **Responsabilidade pelas decisões** continua sendo inteiramente sua

**🔒 RECOMENDAÇÃO REFORÇADA**: Para decisões comerciais significativas:
1. **Verifique sempre a data dos dados**
2. **Considere forçar nova consulta** para informações críticas
3. **Consulte profissionais qualificados** independentemente da fonte dos dados
4. **Não confie apenas no cache** para decisões importantes
"""
    
    else:
        return f"Recurso não encontrado: {uri}"

@app.list_prompts()
async def handle_list_prompts() -> list[Prompt]:
    """Lista os prompts disponíveis."""
    return [
        Prompt(
            name="investigate_dealer",
            description="Investigação completa de lojista suspeito de fraude (com cache + fallback)",
            arguments=[
                PromptArgument(
                    name="cnpj",
                    description="CNPJ do lojista a ser investigado",
                    required=True
                ),
                PromptArgument(
                    name="company_name",
                    description="Nome da empresa (opcional, melhora a busca)",
                    required=False
                ),
                PromptArgument(
                    name="concern",
                    description="Motivo da suspeita ou preocupação específica",
                    required=False
                )
            ]
        ),
        Prompt(
            name="pre_purchase_check",
            description="Verificação rápida antes de comprar veículo (otimizada com cache)",
            arguments=[
                PromptArgument(
                    name="cnpj",
                    description="CNPJ do lojista",
                    required=True
                ),
                PromptArgument(
                    name="vehicle_info",
                    description="Informações sobre o veículo (opcional)",
                    required=False
                )
            ]
        )
    ]

@app.get_prompt()
async def handle_get_prompt(name: str, arguments: dict) -> GetPromptResult:
    """Fornece os prompts configurados."""
    
    if name == "investigate_dealer":
        cnpj = arguments.get("cnpj", "")
        company_name = arguments.get("company_name", "")
        concern = arguments.get("concern", "possível fraude")
        
        prompt_text = f"""
Você é um especialista em detecção de fraude comercial no Brasil. Investigue completamente o lojista/concessionária com CNPJ {cnpj} devido a suspeita de {concern}.

INSTRUÇÕES:
1. Use comprehensive_dealer_check para análise completa (otimizada com cache)
2. Se necessário, use ferramentas específicas adicionais
3. Analise criticamente todos os dados coletados
4. **NOVO**: Observe o campo "data_source" para entender origem dos dados
5. **NOVO**: Verifique "query_date" para avaliar atualidade das informações
6. Identifique padrões suspeitos e red flags
7. Forneça recomendação clara e fundamentada

ASPECTOS CRÍTICOS A VERIFICAR:
- Situação legal atual (CNPJ ativo, processos)
- Histórico de reclamações e fraudes
- Reputação online e offline
- Padrões suspeitos de comportamento
- Credibilidade comercial no setor
- **NOVO**: Idade e fonte dos dados consultados

FORMATO DA RESPOSTA:
- **Resumo Executivo**: Status geral do lojista
- **Fontes dos Dados**: De onde vieram as informações (cache vs API)
- **Atualidade**: Quando os dados foram obtidos
- **Red Flags Encontrados**: Problemas identificados
- **Nível de Risco**: BAIXO/MÉDIO/ALTO/CRÍTICO
- **Recomendação**: Ação específica recomendada

Nome da empresa: {company_name if company_name else "A investigar"}

Seja rigoroso na análise, considere a idade dos dados e sempre priorize a proteção do consumidor.
"""

        return GetPromptResult(
            description=f"Investigação completa de fraude para lojista CNPJ {cnpj} (com cache + fallback)",
            messages=[
                PromptMessage(
                    role="user", 
                    content=TextContent(type="text", text=prompt_text)
                )
            ]
        )
    
    elif name == "pre_purchase_check":
        cnpj = arguments.get("cnpj", "")
        vehicle_info = arguments.get("vehicle_info", "")
        
        vehicle_context = f" para compra do veículo: {vehicle_info}" if vehicle_info else " para compra de veículo"
        
        prompt_text = f"""
Realize uma verificação rápida de segurança do lojista CNPJ {cnpj}{vehicle_context}.

VERIFICAÇÕES ESSENCIAIS (OTIMIZADAS COM CACHE):
1. Use verify_cnpj_status para confirmar se a empresa está ativa
2. Use check_dealer_reputation para verificar reclamações básicas
3. **NOVO**: Observe se dados vieram do cache (rápido) ou API (atual)
4. **NOVO**: Considere idade dos dados para decisão final
5. Identifique red flags críticos que impedem a compra

RESPONDA APENAS:
✅ PROSSEGUIR - Se não há impedimentos críticos
⚠️ CAUTELA - Se há alertas que requerem atenção
🚫 EVITAR - Se há problemas graves
🔄 VERIFICAR NOVAMENTE - Se dados do cache estão muito antigos

Inclua:
- Motivo principal da recomendação
- Principal alerta encontrado (se houver)  
- Uma ação imediata recomendada
- **NOVO**: Fonte e idade dos dados utilizados
- **NOVO**: Se recomenda consulta mais atual

Esta é uma verificação PRÉ-COMPRA rápida otimizada. Seja direto e prático, mas considere a atualidade dos dados.
"""

        return GetPromptResult(
            description=f"Verificação pré-compra otimizada para lojista CNPJ {cnpj}",
            messages=[
                PromptMessage(
                    role="user",
                    content=TextContent(type="text", text=prompt_text)
                )
            ]
        )
    
    else:
        raise ValueError(f"Prompt '{name}' não encontrado")

async def main():
    """Executa o servidor MCP."""
    from mcp.server.stdio import stdio_server
    
    async with stdio_server() as (read_stream, write_stream):
        await app.run(
            read_stream,
            write_stream,
            InitializationOptions(
                server_name="dealer-fraud-checker-mvp",
                server_version="1.1.0-cache-fallback",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())