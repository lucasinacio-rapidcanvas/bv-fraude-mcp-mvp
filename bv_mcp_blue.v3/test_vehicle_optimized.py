#!/usr/bin/env python3
"""
Teste do serviço otimizado de veículos
"""

from vehicle_owner_service import VehicleOwnerService
import json

def test_optimized_service():
    """Testa o serviço otimizado"""
    print("🚀 Testando serviço otimizado de veículos...")

    service = VehicleOwnerService()

    # Teste com placa
    test_plate = "ABC1234"

    try:
        result = service.lookup_vehicle_owner(test_plate)

        print(f"✅ Resultado: {result['success']}")
        if result['success']:
            print(f"📊 Fonte: {result['source']}")
            if 'timeout_used' in result:
                print(f"⏱️ Timeout usado: {result['timeout_used']}s")
        else:
            print(f"❌ Erro: {result['error']}")

    except Exception as e:
        print(f"❌ Exceção: {e}")

    finally:
        service.close()

if __name__ == "__main__":
    test_optimized_service()