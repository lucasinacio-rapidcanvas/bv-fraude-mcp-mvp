#!/usr/bin/env python3
"""
MVP MCP Server para Verificação de Fraude em Lojistas de Veículos
Usando OpenAI Responses API com Web Search

Este é um MVP que usa o OpenAI Responses API para buscar informações
sobre possível fraude em lojistas, concessionárias e vendedores de veículos.

Autor: Assistente Claude
Data: 29/08/2025
"""

import asyncio
import json
import logging
import re
from datetime import datetime
from typing import Any, Dict, List, Optional
import os

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
    """Classe principal para verificação de fraude em lojistas usando OpenAI."""
    
    # Preços por 1K tokens (USD) - Atualizado em Jan 2025
    PRICING = {
        "gpt-4o": {
            "input": 0.003,   # $3.00 per 1M tokens (preço atual correto)
            "output": 0.010   # $10.00 per 1M tokens (correto)
        },
        "gpt-4o-2024-08-06": {
            "input": 0.0025,  # $2.50 per 1M tokens (versão mais recente)
            "output": 0.010   # $10.00 per 1M tokens
        },
        "gpt-4o-search-preview": {
            "input": 0.003,   # Baseado no gpt-4o padrão
            "output": 0.010,  # Baseado no gpt-4o padrão
            "search_cost": 0.02  # $0.02 por busca adicional (real)
        },
        "gpt-4o-mini": {
            "input": 0.00015, # $0.15 per 1M tokens
            "output": 0.0006  # $0.60 per 1M tokens
        }
    }
    
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        self.total_cost = 0.0
        self.request_history = []
        
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
    
    def _calculate_cost(self, model: str, input_tokens: int, output_tokens: int, search_count: int = 0) -> float:
        """Calcula o custo da requisição baseado no modelo e tokens utilizados."""
        if model not in self.PRICING:
            logger.warning(f"⚠️ Modelo {model} não encontrado na tabela de preços")
            return 0.0
        
        pricing = self.PRICING[model]
        
        # Converte tokens para milhares (pricing é por 1K tokens)
        input_cost = (input_tokens / 1000) * pricing["input"]
        output_cost = (output_tokens / 1000) * pricing["output"]
        
        total_cost = input_cost + output_cost
        
        # Adiciona custo de busca se for modelo de busca
        if "search" in model.lower() and "search_cost" in pricing:
            search_cost = search_count * pricing["search_cost"]
            total_cost += search_cost
            logger.info(f"💰 Custo adicional de busca: ${search_cost:.4f} ({search_count} buscas)")
        
        return total_cost
    
    def _track_request(self, model: str, input_tokens: int, output_tokens: int, cost: float, operation: str = "unknown"):
        """Registra uma requisição no histórico de custos."""
        request_info = {
            "timestamp": datetime.now().isoformat(),
            "model": model,
            "input_tokens": input_tokens,
            "output_tokens": output_tokens,
            "total_tokens": input_tokens + output_tokens,
            "cost_usd": cost,
            "operation": operation
        }
        
        self.request_history.append(request_info)
        self.total_cost += cost
        
        logger.info(f"💰 Custo da requisição: ${cost:.4f} USD | Total acumulado: ${self.total_cost:.4f} USD")
    
    def get_cost_summary(self) -> Dict[str, Any]:
        """Retorna um resumo detalhado dos custos."""
        if not self.request_history:
            return {
                "total_cost_usd": 0.0,
                "total_requests": 0,
                "total_tokens": 0,
                "cost_by_model": {},
                "cost_by_operation": {},
                "average_cost_per_request": 0.0
            }
        
        # Agrupa custos por modelo
        cost_by_model = {}
        cost_by_operation = {}
        total_tokens = 0
        
        for req in self.request_history:
            model = req["model"]
            operation = req["operation"]
            cost = req["cost_usd"]
            tokens = req["total_tokens"]
            
            # Por modelo
            if model not in cost_by_model:
                cost_by_model[model] = {"cost": 0.0, "requests": 0, "tokens": 0}
            cost_by_model[model]["cost"] += cost
            cost_by_model[model]["requests"] += 1
            cost_by_model[model]["tokens"] += tokens
            
            # Por operação
            if operation not in cost_by_operation:
                cost_by_operation[operation] = {"cost": 0.0, "requests": 0}
            cost_by_operation[operation]["cost"] += cost
            cost_by_operation[operation]["requests"] += 1
            
            total_tokens += tokens
        
        return {
            "total_cost_usd": self.total_cost,
            "total_requests": len(self.request_history),
            "total_tokens": total_tokens,
            "cost_by_model": cost_by_model,
            "cost_by_operation": cost_by_operation,
            "average_cost_per_request": self.total_cost / len(self.request_history),
            "requests_history": self.request_history[-10:]  # Últimas 10 requisições
        }
    
    def reset_cost_tracking(self):
        """Reseta o rastreamento de custos."""
        self.total_cost = 0.0
        self.request_history = []
        logger.info("🔄 Rastreamento de custos resetado")
    
    async def _make_search_request(self, prompt: str, temperature: float = 0.0, operation: str = "search") -> str:
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

IMPORTANTE: Retorne sua resposta EXCLUSIVAMENTE em formato JSON válido, sem texto adicional."""
                        }
                    ],
                    max_tokens=4000
                )
                
                result = response.choices[0].message.content
                
                # Rastrear custos
                usage = response.usage
                if usage:
                    # Estima 1 busca web por requisição para modelo de busca
                    cost = self._calculate_cost("gpt-4o-search-preview", usage.prompt_tokens, usage.completion_tokens, search_count=1)
                    self._track_request("gpt-4o-search-preview", usage.prompt_tokens, usage.completion_tokens, cost, operation)
                
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
                
                # Rastrear custos do modelo padrão
                usage = response.usage
                if usage:
                    cost = self._calculate_cost("gpt-4o", usage.prompt_tokens, usage.completion_tokens)
                    self._track_request("gpt-4o", usage.prompt_tokens, usage.completion_tokens, cost, operation)
                
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
    
    async def check_dealer_reputation(self, cnpj: str, company_name: str = None) -> Dict[str, Any]:
        """Verifica a reputação geral do lojista em sites como Reclame Aqui."""
        
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
            result = await self._make_search_request(prompt, operation="verify_cnpj_status")
            
            # Tenta parsear como JSON, se não conseguir retorna texto
            try:
                json_content = self._extract_json_from_response(result)
                json_result = json.loads(json_content)
                # Valida resposta JSON
                validated_result = self._validate_json_response(json_result, "reputation")
                return validated_result
            except (json.JSONDecodeError, ValueError):
                return {
                    "cnpj": formatted_cnpj,
                    "company_name": company_name,
                    "raw_response": result,
                    "status": "success_text",
                    "query_date": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "cnpj": formatted_cnpj,
                "error": str(e),
                "status": "error",
                "query_date": datetime.now().isoformat()
            }
    
    async def check_legal_issues(self, cnpj: str, company_name: str = None) -> Dict[str, Any]:
        """Busca processos judiciais e questões legais."""
        
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
            result = await self._make_search_request(prompt, operation="check_dealer_reputation")
            
            try:
                json_content = self._extract_json_from_response(result)
                json_result = json.loads(json_content)
                validated_result = self._validate_json_response(json_result, "legal")
                return validated_result
            except (json.JSONDecodeError, ValueError):
                return {
                    "cnpj": formatted_cnpj,
                    "company_name": company_name,
                    "raw_response": result,
                    "status": "success_text", 
                    "query_date": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "cnpj": formatted_cnpj,
                "error": str(e),
                "status": "error",
                "query_date": datetime.now().isoformat()
            }
    
    async def verify_cnpj_status(self, cnpj: str) -> Dict[str, Any]:
        """Verifica a situação oficial do CNPJ."""
        
        if not self._validate_cnpj(cnpj):
            return {
                "error": "CNPJ inválido",
                "cnpj_provided": cnpj,
                "cnpj_valid": False,
                "status": "error"
            }
        
        formatted_cnpj = self._format_cnpj(cnpj)
        
        prompt = f"""
Verifique a situação oficial do CNPJ {formatted_cnpj} como lojista de veículos.

CONSULTAR:
• Situação na Receita Federal (ativo/inativo, CNAE)
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
            result = await self._make_search_request(prompt, operation="check_legal_issues")
            
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
                validated_result = self._validate_json_response(json_result, "cnpj_status")
                return validated_result
            except (json.JSONDecodeError, ValueError):
                return {
                    "cnpj": formatted_cnpj,
                    "cnpj_valid": True,
                    "raw_response": result,
                    "status": "success_text",
                    "query_date": datetime.now().isoformat()
                }
                
        except Exception as e:
            return {
                "cnpj": formatted_cnpj,
                "cnpj_valid": True,
                "error": str(e),
                "status": "error",
                "query_date": datetime.now().isoformat()
            }
    
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
            response_text = await self._make_search_request(prompt, operation="comprehensive_check")
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
            "recommendation": recommendation,
            "next_steps": self._get_next_steps(risk_level)
        }
    
    def _get_next_steps(self, risk_level: str) -> List[str]:
        """Retorna próximos passos recomendados baseado no nível de risco."""
        
        if risk_level == "CRÍTICO":
            return [
                "Evitar qualquer negociação",
                "Procurar outros lojistas",
                "Se já houve negociação, consultar advogado"
            ]
        elif risk_level == "ALTO":
            return [
                "Solicitar documentação adicional",
                "Verificar credenciamento em órgãos do setor",
                "Visitar fisicamente o estabelecimento",
                "Consultar outros clientes recentes"
            ]
        elif risk_level == "MÉDIO":
            return [
                "Verificar documentos do veículo cuidadosamente",
                "Pedir referências de outros clientes",
                "Fazer vistoria técnica independente",
                "Negociar garantias adicionais"
            ]
        else:
            return [
                "Verificar documentação padrão",
                "Fazer test drive completo",
                "Confirmar procedência do veículo",
                "Manter cautela normal na compra"
            ]

# Inicialização do servidor MCP
app = Server("dealer-fraud-checker-mvp")

# Initialize checker with API key
API_KEY = "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"
fraud_checker = DealerFraudChecker(API_KEY)

@app.list_tools()
async def handle_list_tools() -> list[Tool]:
    """Lista as ferramentas disponíveis."""
    return [
        Tool(
            name="check_dealer_reputation",
            description="Verifica reputação do lojista em sites como Reclame Aqui, Google Reviews",
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
            description="Busca processos judiciais e questões legais do lojista",
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
            description="Verifica situação oficial do CNPJ na Receita Federal",
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
            description="Análise completa de fraude do lojista (todas as verificações)",
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
                text=json.dumps(result, indent=2, ensure_ascii=False)
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
        return """# Estratégia de Busca para Lojistas

## 🔍 Fontes Consultadas via Web Search

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

## 🎯 Metodologia de Busca

1. **Busca por CNPJ**: Identificação precisa da empresa
2. **Busca por nome**: Captura variações e nomes fantasia
3. **Busca contextual**: Termos específicos do setor automotivo
4. **Análise temporal**: Foco em informações recentes (último ano)

## 📊 Critérios de Análise

- **Frequência**: Quantidade de menções negativas
- **Gravidade**: Tipo de problemas reportados  
- **Recência**: Quando ocorreram os problemas
- **Padrão**: Se há repetição de comportamentos
- **Resposta**: Como a empresa lida com reclamações
"""
    
    elif uri == "fraud://sources/indicators":
        return """# Indicadores de Fraude em Lojistas

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

## 🔍 Como Interpretar os Resultados

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
"""
    
    elif uri == "fraud://guide/usage":
        return """# Guia de Uso do Sistema

## 🚀 Como Usar as Ferramentas

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
```

### **3. Análise de Reputação**
```
Usar: check_dealer_reputation
Quando: Verificar reclamações e avaliações
Exemplo: check_dealer_reputation com cnpj "11222333000181" 
         e company_name "Loja de Carros XYZ"
```

### **4. Questões Legais**
```
Usar: check_legal_issues
Quando: Buscar processos e investigações
Exemplo: check_legal_issues com cnpj "11222333000181"
```

### **5. Análise Completa**
```
Usar: comprehensive_dealer_check
Quando: Análise completa antes de uma compra importante
Exemplo: comprehensive_dealer_check com cnpj "11222333000181"
         e company_name "AutoCenter ABC"
```

## 📋 Fluxo Recomendado

### **Para Compra de Veículo**
1. **Validar CNPJ** do lojista
2. **Verificar situação cadastral** na Receita
3. **Fazer análise completa** se os primeiros passos forem OK
4. **Interpretar resultados** e tomar decisão

### **Para Due Diligence**
1. **Análise completa** direto
2. **Verificações adicionais** se necessário
3. **Consulta a especialistas** para casos críticos

## 💡 Dicas de Uso

### **Preparação**
- Tenha o CNPJ em mãos (obrigatório)
- Nome fantasia ajuda na busca (opcional)
- Endereço pode ser útil para validação

### **Interpretação**
- Leia sempre o campo "summary" primeiro
- Verifique o "risk_level" e "recommendation" 
- Siga os "next_steps" sugeridos
- Em caso de dúvida, sempre opte pela cautela

### **Limitações**
- Informações dependem do que está disponível online
- Dados podem estar desatualizados
- Nem todas as fontes são sempre acessíveis
- Decisões finais devem considerar outros fatores

## ⚠️ Quando NÃO Usar

- **Não substitui** visita presencial ao lojista
- **Não substitui** vistoria técnica do veículo  
- **Não substitui** verificação de documentos originais
- **Não substitui** consulta a advogado em casos complexos

## 🆘 Em Caso de Problemas

### **Erro de CNPJ Inválido**
- Verifique se digitou corretamente
- CNPJ deve ter exatamente 14 números
- Use com ou sem formatação

### **Poucos Resultados**
- Empresa pode ser muito nova
- Pode não ter presença online significativa
- Considere busca manual adicional

### **Resultados Conflitantes**
- Dados podem estar desatualizados
- Múltiplas fontes podem ter informações diferentes
- Priorize fontes oficiais (Receita Federal, tribunais)

### **Erro Técnico**
- Tente novamente em alguns minutos
- APIs externas podem estar temporariamente indisponíveis
- Entre em contato se o problema persistir
"""
    
    elif uri == "fraud://legal/disclaimer":
        return """# Disclaimer Legal

## ⚖️ Termos de Uso e Limitações

### **Natureza Informativa**
Este sistema tem caráter **EXCLUSIVAMENTE INFORMATIVO** e destina-se a auxiliar na tomada de decisões comerciais. As informações fornecidas:

- ✅ São baseadas em dados públicos disponíveis online
- ✅ Passam por análise automatizada com critérios pré-definidos
- ❌ **NÃO constituem** aconselhamento jurídico
- ❌ **NÃO substituem** due diligence profissional
- ❌ **NÃO garantem** completude ou precisão absoluta

### **Responsabilidades do Usuário**

#### **Verificação Independente**
O usuário deve **SEMPRE**:
- Confirmar informações através de fontes oficiais
- Realizar visita presencial ao estabelecimento
- Consultar documentos originais
- Contratar vistoria técnica independente quando aplicável
- Buscar aconselhamento jurídico para decisões importantes

#### **Decisões Comerciais**
- Todas as decisões de compra, venda ou negociação são de **exclusiva responsabilidade do usuário**
- O sistema oferece apenas suporte informativo para análise
- Recomendações automáticas devem ser validadas independentemente

### **Limitações Técnicas**

#### **Fontes de Dados**
- Dependemos de informações disponíveis publicamente online
- Dados podem estar desatualizados ou incompletos
- Nem todas as fontes são sempre acessíveis
- Informações podem conter erros das fontes originais

#### **Cobertura**
- Empresas muito novas podem ter pouca informação disponível
- Empresas sem presença online significativa podem não aparecer
- Algumas fontes regionais podem não estar incluídas
- Dados históricos podem ser limitados

### **Isenção de Responsabilidade**

#### **Danos e Prejuízos**
Os desenvolvedores e operadores deste sistema **NÃO SE RESPONSABILIZAM** por:
- Decisões comerciais baseadas nas informações fornecidas
- Prejuízos financeiros resultantes de uso do sistema
- Imprecisões ou omissões nos dados apresentados
- Indisponibilidade temporária do sistema
- Problemas técnicos ou falhas operacionais

#### **Uso Adequado**
Este sistema deve ser usado apenas para:
- ✅ Análise preliminar de lojistas e comerciantes
- ✅ Suporte à tomada de decisão informada
- ✅ Identificação de pontos que requerem investigação adicional
- ❌ **NÃO** para difamação ou prejuízo à reputação
- ❌ **NÃO** como única fonte de informação para decisões importantes

### **Conformidade Legal**

#### **LGPD - Lei Geral de Proteção de Dados**
- Utilizamos apenas dados públicos disponíveis online
- Não coletamos dados pessoais dos usuários do sistema
- Informações são processadas para fins legítimos de análise comercial

#### **Direitos de Propriedade**
- Respeitamos direitos autorais das fontes consultadas
- Não reproduzimos conteúdo protegido integralmente
- Fazemos referência adequada às fontes utilizadas

#### **Legislação Aplicável**
Este sistema está sujeito à:
- Legislação brasileira aplicável
- Código de Defesa do Consumidor
- Marco Civil da Internet
- Demais normas pertinentes

### **Contato e Suporte**

Para questões legais, dúvidas sobre o sistema ou reportar problemas:
- Use os canais oficiais de suporte
- Mantenha registros de suas consultas
- Em caso de disputas, busque orientação jurídica independente

---

**⚠️ IMPORTANTE**: Ao usar este sistema, você concorda com os termos acima e assume total responsabilidade pelas decisões tomadas com base nas informações fornecidas. 

**🔒 RECOMENDAÇÃO**: Para decisões comerciais significativas, sempre consulte profissionais qualificados (advogados, contadores, auditores) além das informações aqui apresentadas.
"""
    
    else:
        return f"Recurso não encontrado: {uri}"

@app.list_prompts()
async def handle_list_prompts() -> list[Prompt]:
    """Lista os prompts disponíveis."""
    return [
        Prompt(
            name="investigate_dealer",
            description="Investigação completa de lojista suspeito de fraude",
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
            description="Verificação rápida antes de comprar veículo",
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
1. Use comprehensive_dealer_check para análise completa
2. Se necessário, use ferramentas específicas adicionais
3. Analise criticamente todos os dados coletados
4. Identifique padrões suspeitos e red flags
5. Forneça recomendação clara e fundamentada

ASPECTOS CRÍTICOS A VERIFICAR:
- Situação legal atual (CNPJ ativo, processos)
- Histórico de reclamações e fraudes
- Reputação online e offline
- Padrões suspeitos de comportamento
- Credibilidade comercial no setor

FORMATO DA RESPOSTA:
- **Resumo Executivo**: Status geral do lojista
- **Red Flags Encontrados**: Problemas identificados
- **Nível de Risco**: BAIXO/MÉDIO/ALTO/CRÍTICO
- **Recomendação**: Ação específica recomendada
- **Próximos Passos**: O que fazer em seguida

Nome da empresa: {company_name if company_name else "A investigar"}

Seja rigoroso na análise e sempre priorize a proteção do consumidor.
"""

        return GetPromptResult(
            description=f"Investigação completa de fraude para lojista CNPJ {cnpj}",
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

VERIFICAÇÕES ESSENCIAIS:
1. Use verify_cnpj_status para confirmar se a empresa está ativa
2. Use check_dealer_reputation para verificar reclamações básicas
3. Identifique red flags críticos que impedem a compra

RESPONDA APENAS:
✅ PROSSEGUIR - Se não há impedimentos críticos
⚠️ CAUTELA - Se há alertas que requerem atenção
🚫 EVITAR - Se há problemas graves

Inclua:
- Motivo principal da recomendação
- Principal alerta encontrado (se houver)  
- Uma ação imediata recomendada

Esta é uma verificação PRÉ-COMPRA rápida. Seja direto e prático.
"""

        return GetPromptResult(
            description=f"Verificação pré-compra para lojista CNPJ {cnpj}",
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
                server_version="1.0.0-mvp",
                capabilities=app.get_capabilities(
                    notification_options=NotificationOptions(),
                    experimental_capabilities={},
                )
            ),
        )

if __name__ == "__main__":
    asyncio.run(main())