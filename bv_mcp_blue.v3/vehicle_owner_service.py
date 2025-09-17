#!/usr/bin/env python3
"""
Serviço de Consulta de Proprietários de Veículos
Sistema com cache de 6 meses para otimizar consultas
"""

import requests
import json
import os
from datetime import datetime, timedelta
from typing import Dict, Any, Optional
import logging
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

class VehicleOwnerService:
    def __init__(self):
        self.api_url = "https://api.credify.com.br/veiculoproprietarioplaca"
        self.headers = {
            "accept": "application/json",
            "content-type": "application/json",
            "Authorization": "eyJhbGciOiAiSFMyNTYiLCJ0eXAiOiAiSldUIn0.eyAicm9sZSIgOiAidXNlciIsImxvZ2luIiA6ICIzOTgzNyIsIm5iZiI6MTc1ODEwOTA3MiwiZXhwIjoxNzU4MTk1NDcyLCJpYXQiOjE3NTgxMDkwNzIgfQ.Y6kyuYpzxvKa9WFpWFp6vRLPZuZrPvBRUbvqpWgx0Hg"
        }
        self.cache_file = "vehicle_owner_cache.json"
        self.cache_duration_months = 6
        self.logger = self._setup_logger()
        self.session = self._setup_session()

    def _setup_logger(self) -> logging.Logger:
        """Configura o logger para o serviço"""
        logger = logging.getLogger(__name__)
        logger.setLevel(logging.INFO)

        if not logger.handlers:
            handler = logging.StreamHandler()
            formatter = logging.Formatter('%(asctime)s - %(name)s - %(levelname)s - %(message)s')
            handler.setFormatter(formatter)
            logger.addHandler(handler)

        return logger

    def _setup_session(self) -> requests.Session:
        """Configura uma sessão HTTP otimizada com retry e timeout"""
        session = requests.Session()

        # Configuração de retry strategy
        retry_strategy = Retry(
            total=3,
            backoff_factor=1,
            status_forcelist=[429, 500, 502, 503, 504],
            allowed_methods=["HEAD", "GET", "POST"]
        )

        # Adaptador HTTP com retry
        adapter = HTTPAdapter(max_retries=retry_strategy)
        session.mount("http://", adapter)
        session.mount("https://", adapter)

        # Headers padrão
        session.headers.update(self.headers)

        return session

    def _check_api_error(self, api_data: Dict[str, Any]) -> Optional[str]:
        """Verifica se a API retornou erro no conteúdo da resposta"""
        try:
            # Verifica resposta da API na estrutura CONSULTA/RESPOSTA
            if isinstance(api_data, dict):
                # Verifica campo CONSULTA
                if "CONSULTA" in api_data:
                    consulta = api_data["CONSULTA"]
                    if "CODIGORESPOSTA" in consulta:
                        codigo_resposta = consulta["CODIGORESPOSTA"]
                        # Se não for "SUCESSO", é um erro
                        if codigo_resposta and codigo_resposta.upper() != "SUCESSO":
                            return f"API Error: {codigo_resposta}"

                # Verifica campo RESPOSTA
                if "RESPOSTA" in api_data:
                    resposta = api_data["RESPOSTA"]
                    if isinstance(resposta, dict):
                        codigo = resposta.get("CODIGO", "")
                        msg = resposta.get("MSG", "")

                        # Códigos de erro conhecidos
                        if codigo and codigo != "0":  # 0 geralmente é sucesso
                            return f"Código {codigo}: {msg}" if msg else f"Código de erro: {codigo}"

            return None  # Sem erro detectado

        except Exception as e:
            self.logger.warning(f"Erro ao verificar resposta da API: {e}")
            return None

    def _load_cache(self) -> Dict[str, Any]:
        """Carrega o cache do arquivo JSON"""
        try:
            if os.path.exists(self.cache_file):
                with open(self.cache_file, 'r', encoding='utf-8') as f:
                    return json.load(f)
        except Exception as e:
            self.logger.error(f"Erro ao carregar cache: {e}")
        return {}

    def _save_cache(self, cache_data: Dict[str, Any]) -> None:
        """Salva o cache no arquivo JSON"""
        try:
            with open(self.cache_file, 'w', encoding='utf-8') as f:
                json.dump(cache_data, f, indent=2, ensure_ascii=False)
        except Exception as e:
            self.logger.error(f"Erro ao salvar cache: {e}")

    def _is_cache_valid(self, cache_timestamp: str) -> bool:
        """Verifica se o cache ainda é válido (menos de 6 meses)"""
        try:
            cache_date = datetime.fromisoformat(cache_timestamp)
            expiry_date = cache_date + timedelta(days=30 * self.cache_duration_months)
            return datetime.now() < expiry_date
        except Exception:
            return False

    def _normalize_plate(self, plate: str) -> str:
        """Normaliza a placa removendo espaços e convertendo para maiúscula"""
        return plate.replace(" ", "").replace("-", "").upper().strip()

    def _validate_plate(self, plate: str) -> bool:
        """Valida o formato da placa brasileira (AAA0000 ou AAA0A00)"""
        plate = self._normalize_plate(plate)

        # Formato antigo: 3 letras + 4 números (AAA0000)
        old_format = len(plate) == 7 and plate[:3].isalpha() and plate[3:].isdigit()

        # Formato Mercosul: 3 letras + 1 número + 1 letra + 2 números (AAA0A00)
        mercosul_format = (len(plate) == 7 and
                          plate[:3].isalpha() and
                          plate[3].isdigit() and
                          plate[4].isalpha() and
                          plate[5:].isdigit())

        return old_format or mercosul_format

    def lookup_vehicle_owner(self, plate: str) -> Dict[str, Any]:
        """
        Consulta dados do proprietário do veículo pela placa
        Utiliza cache com validade de 6 meses
        """
        # Normaliza e valida a placa
        normalized_plate = self._normalize_plate(plate)

        if not self._validate_plate(normalized_plate):
            return {
                "success": False,
                "error": "Formato de placa inválido",
                "data": None,
                "source": "validation"
            }

        # Verifica cache primeiro
        cache_data = self._load_cache()
        cache_key = f"plate_{normalized_plate}"

        if cache_key in cache_data:
            cache_entry = cache_data[cache_key]
            if self._is_cache_valid(cache_entry.get("timestamp", "")):
                # Verifica se o cache contém erro da API
                cached_data = cache_entry["data"]
                if cached_data and cached_data.get("raw_data"):
                    api_error = self._check_api_error(cached_data["raw_data"])
                    if api_error:
                        self.logger.warning(f"Cache contém erro da API para placa {normalized_plate}: {api_error}")
                        # Remove da cache e consulta novamente
                        del cache_data[cache_key]
                        self._save_cache(cache_data)
                    else:
                        self.logger.info(f"Dados encontrados no cache para placa: {normalized_plate}")
                        return {
                            "success": True,
                            "data": cached_data,
                            "source": "cache",
                            "cached_at": cache_entry["timestamp"]
                        }

        # Cache inválido ou inexistente, consulta API
        return self._call_api_with_fallback(normalized_plate)

    def _call_api_with_fallback(self, normalized_plate: str) -> Dict[str, Any]:
        """Chama a API com estratégia de fallback para diferentes timeouts"""
        self.logger.info(f"Consultando API para placa: {normalized_plate}")

        payload = {
            "Consulta": {
                "IdConsulta": "514",
                "Placa": normalized_plate
            }
        }

        # Lista de timeouts para tentar em ordem
        timeouts = [60, 90, 120]  # Aumentei os timeouts baseado no teste
        last_error = None

        for timeout_val in timeouts:
            try:
                self.logger.info(f"Tentativa com timeout de {timeout_val}s")

                # Usar sessão otimizada
                response = self.session.post(
                    self.api_url,
                    json=payload,
                    timeout=(30, timeout_val)  # (connection_timeout, read_timeout)
                )
                response.raise_for_status()

                api_data = response.json()

                # Verifica se a API retornou um erro no conteúdo
                api_error = self._check_api_error(api_data)
                if api_error:
                    self.logger.error(f"Erro da API: {api_error}")
                    return {
                        "success": False,
                        "error": api_error,
                        "data": None,
                        "source": "api_business_error"
                    }

                self.logger.info(f"Sucesso com timeout de {timeout_val}s")

                # Organiza os dados da resposta
                organized_data = self._organize_api_response(api_data)

                # Salva no cache
                cache_data = self._load_cache()
                cache_key = f"plate_{normalized_plate}"
                cache_data[cache_key] = {
                    "data": organized_data,
                    "timestamp": datetime.now().isoformat(),
                    "plate": normalized_plate
                }
                self._save_cache(cache_data)

                return {
                    "success": True,
                    "data": organized_data,
                    "source": "api",
                    "consulted_at": datetime.now().isoformat(),
                    "timeout_used": timeout_val
                }

            except requests.exceptions.Timeout as e:
                last_error = f"Timeout após {timeout_val}s: {str(e)}"
                self.logger.warning(f"Timeout com {timeout_val}s, tentando próximo...")
                continue

            except requests.exceptions.RequestException as e:
                last_error = f"Erro de requisição: {str(e)}"
                self.logger.error(f"Erro de requisição com timeout {timeout_val}s: {e}")
                # Para erros não-timeout, não tenta outros timeouts
                break

            except Exception as e:
                last_error = f"Erro inesperado: {str(e)}"
                self.logger.error(f"Erro inesperado com timeout {timeout_val}s: {e}")
                break

        # Se chegou aqui, todas as tentativas falharam
        self.logger.error(f"Todas as tentativas falharam. Último erro: {last_error}")
        return {
            "success": False,
            "error": last_error,
            "data": None,
            "source": "api_error"
        }

    def _organize_api_response(self, api_data: Dict[str, Any]) -> Dict[str, Any]:
        """Organiza a resposta da API em categorias lógicas"""
        try:
            # Estrutura organizada dos dados
            organized = {
                "vehicle_info": {},
                "owner_info": {},
                "registration_info": {},
                "restrictions": {},
                "technical_data": {},
                "raw_data": api_data  # Mantém dados originais para debug
            }

            # Extrai informações do veículo se disponíveis
            if "VeiculoInfo" in api_data:
                vehicle = api_data["VeiculoInfo"]
                organized["vehicle_info"] = {
                    "plate": vehicle.get("Placa", ""),
                    "brand": vehicle.get("Marca", ""),
                    "model": vehicle.get("Modelo", ""),
                    "year_manufacture": vehicle.get("AnoFabricacao", ""),
                    "year_model": vehicle.get("AnoModelo", ""),
                    "color": vehicle.get("Cor", ""),
                    "fuel_type": vehicle.get("Combustivel", ""),
                    "category": vehicle.get("Categoria", ""),
                    "chassis": vehicle.get("Chassi", ""),
                    "renavam": vehicle.get("Renavam", "")
                }

            # Extrai informações do proprietário se disponíveis
            if "ProprietarioInfo" in api_data:
                owner = api_data["ProprietarioInfo"]
                organized["owner_info"] = {
                    "name": owner.get("Nome", ""),
                    "document": owner.get("Documento", ""),
                    "document_type": owner.get("TipoDocumento", ""),
                    "address": {
                        "street": owner.get("Endereco", {}).get("Logradouro", ""),
                        "number": owner.get("Endereco", {}).get("Numero", ""),
                        "neighborhood": owner.get("Endereco", {}).get("Bairro", ""),
                        "city": owner.get("Endereco", {}).get("Cidade", ""),
                        "state": owner.get("Endereco", {}).get("Estado", ""),
                        "zip_code": owner.get("Endereco", {}).get("CEP", "")
                    }
                }

            # Extrai informações de registro
            if "RegistroInfo" in api_data:
                registration = api_data["RegistroInfo"]
                organized["registration_info"] = {
                    "registration_date": registration.get("DataRegistro", ""),
                    "last_transfer": registration.get("UltimaTransferencia", ""),
                    "municipal_registration": registration.get("RegistroMunicipal", ""),
                    "origin_state": registration.get("EstadoOrigem", "")
                }

            # Extrai restrições e impedimentos
            if "Restricoes" in api_data:
                restrictions = api_data["Restricoes"]
                organized["restrictions"] = {
                    "has_restrictions": restrictions.get("PossuiRestricoes", False),
                    "restriction_list": restrictions.get("ListaRestricoes", []),
                    "judicial_restrictions": restrictions.get("RestricaoJudicial", []),
                    "administrative_restrictions": restrictions.get("RestricaoAdministrativa", [])
                }

            return organized

        except Exception as e:
            self.logger.error(f"Erro ao organizar resposta da API: {e}")
            return {
                "vehicle_info": {},
                "owner_info": {},
                "registration_info": {},
                "restrictions": {},
                "technical_data": {},
                "raw_data": api_data,
                "organization_error": str(e)
            }

    def get_cache_stats(self) -> Dict[str, Any]:
        """Retorna estatísticas do cache"""
        cache_data = self._load_cache()

        total_entries = len(cache_data)
        valid_entries = 0
        expired_entries = 0

        for key, entry in cache_data.items():
            if self._is_cache_valid(entry.get("timestamp", "")):
                valid_entries += 1
            else:
                expired_entries += 1

        return {
            "total_entries": total_entries,
            "valid_entries": valid_entries,
            "expired_entries": expired_entries,
            "cache_file": self.cache_file
        }

    def clear_expired_cache(self) -> int:
        """Remove entradas expiradas do cache"""
        cache_data = self._load_cache()
        original_count = len(cache_data)

        # Filtra apenas entradas válidas
        valid_cache = {
            key: entry for key, entry in cache_data.items()
            if self._is_cache_valid(entry.get("timestamp", ""))
        }

        self._save_cache(valid_cache)
        removed_count = original_count - len(valid_cache)

        self.logger.info(f"Removidas {removed_count} entradas expiradas do cache")
        return removed_count

    def close(self):
        """Fecha a sessão HTTP adequadamente"""
        if hasattr(self, 'session'):
            self.session.close()

    def __del__(self):
        """Destrutor para garantir que a sessão seja fechada"""
        self.close()


# Função de teste
if __name__ == "__main__":
    service = VehicleOwnerService()

    # Exemplo de uso
    test_plate = "ABC1234"
    result = service.lookup_vehicle_owner(test_plate)

    print(f"Resultado da consulta para placa {test_plate}:")
    print(json.dumps(result, indent=2, ensure_ascii=False))

    # Estatísticas do cache
    stats = service.get_cache_stats()
    print(f"\nEstatísticas do cache:")
    print(json.dumps(stats, indent=2, ensure_ascii=False))