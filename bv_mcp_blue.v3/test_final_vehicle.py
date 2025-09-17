#!/usr/bin/env python3
"""
Teste final do sistema de veículos
"""

from vehicle_owner_service import VehicleOwnerService
import json

def test_different_scenarios():
    """Testa diferentes cenários"""
    service = VehicleOwnerService()

    test_cases = [
        ("ABC1234", "Placa válida padrão"),
        ("RAT9J67", "Placa com limite excedido"),
        ("INVALID", "Placa inválida"),
        ("ABC12345", "Formato incorreto")
    ]

    for plate, description in test_cases:
        print(f"\n🔍 Testando: {plate} ({description})")
        print("-" * 40)

        try:
            result = service.lookup_vehicle_owner(plate)
            print(f"✅ Success: {result['success']}")
            print(f"📄 Source: {result['source']}")

            if result['success']:
                print("✅ Consulta bem-sucedida!")
            else:
                print(f"❌ Erro: {result['error']}")

        except Exception as e:
            print(f"❌ Exceção: {e}")

    service.close()

if __name__ == "__main__":
    test_different_scenarios()