#!/usr/bin/env python3
"""
Script de teste para a API de consulta de veículos
Diagnóstica problemas de conectividade e timeout
"""

import requests
import json
import time
from datetime import datetime

def test_vehicle_api():
    """Testa a API de consulta de veículos com diferentes configurações"""

    url = "https://api.credify.com.br/veiculoproprietarioplaca"

    headers = {
        "accept": "application/json",
        "content-type": "application/json",
        "Authorization": "eyJhbGciOiAiSFMyNTYiLCJ0eXAiOiAiSldUIn0.eyAicm9sZSIgOiAidXNlciIsImxvZ2luIiA6ICIzOTgzNyIsIm5iZiI6MTc1ODEwOTA3MiwiZXhwIjoxNzU4MTk1NDcyLCJpYXQiOjE3NTgxMDkwNzIgfQ.Y6kyuYpzxvKa9WFpWFp6vRLPZuZrPvBRUbvqpWgx0Hg"
    }

    # Placa de teste (use uma placa real para teste)
    test_plate = "ABC1234"

    payload = {
        "Consulta": {
            "IdConsulta": "514",
            "Placa": test_plate
        }
    }

    print(f"🔍 Testando API de Veículos - {datetime.now()}")
    print(f"URL: {url}")
    print(f"Placa de teste: {test_plate}")
    print("-" * 50)

    # Teste 1: Verificar conectividade básica
    print("1️⃣ Testando conectividade básica...")
    try:
        response = requests.get("https://api.credify.com.br", timeout=10)
        print(f"✅ Conectividade básica OK - Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Problema de conectividade básica: {e}")
        return

    # Teste 2: Teste com timeout mais longo
    print("\n2️⃣ Testando com timeout de 60 segundos...")
    try:
        start_time = time.time()
        response = requests.post(url, json=payload, headers=headers, timeout=60)
        end_time = time.time()

        print(f"✅ Sucesso! Tempo de resposta: {end_time - start_time:.2f}s")
        print(f"Status Code: {response.status_code}")
        print(f"Tamanho da resposta: {len(response.text)} caracteres")

        if response.status_code == 200:
            data = response.json()
            print("✅ Resposta JSON válida recebida")
            print(f"Estrutura da resposta: {list(data.keys()) if isinstance(data, dict) else 'Lista ou outro tipo'}")

    except requests.exceptions.Timeout:
        print("❌ Timeout após 60 segundos")
        return
    except requests.exceptions.ConnectionError as e:
        print(f"❌ Erro de conexão: {e}")
        return
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        return

    # Teste 3: Teste com diferentes timeouts
    print("\n3️⃣ Testando diferentes configurações de timeout...")
    timeouts = [10, 20, 30, 45]

    for timeout_val in timeouts:
        try:
            print(f"   Testando timeout de {timeout_val}s...")
            start_time = time.time()
            response = requests.post(url, json=payload, headers=headers, timeout=timeout_val)
            end_time = time.time()
            print(f"   ✅ Sucesso com {timeout_val}s - Tempo real: {end_time - start_time:.2f}s")
            break
        except requests.exceptions.Timeout:
            print(f"   ❌ Timeout com {timeout_val}s")
        except Exception as e:
            print(f"   ❌ Erro com {timeout_val}s: {e}")

    # Teste 4: Verificar headers e payload
    print("\n4️⃣ Verificando configuração da requisição...")
    print("Headers:")
    for key, value in headers.items():
        if key == "Authorization":
            print(f"  {key}: {value[:50]}...")
        else:
            print(f"  {key}: {value}")

    print(f"\nPayload:")
    print(json.dumps(payload, indent=2, ensure_ascii=False))

    # Teste 5: Teste com requests session (pode melhorar performance)
    print("\n5️⃣ Testando com requests Session...")
    try:
        with requests.Session() as session:
            session.headers.update(headers)
            start_time = time.time()
            response = session.post(url, json=payload, timeout=30)
            end_time = time.time()
            print(f"✅ Sucesso com Session! Tempo: {end_time - start_time:.2f}s")
            print(f"Status: {response.status_code}")
    except Exception as e:
        print(f"❌ Erro com Session: {e}")

if __name__ == "__main__":
    test_vehicle_api()