#!/usr/bin/env python3
"""
Debug do problema com a placa RAT9J67
"""

from vehicle_owner_service import VehicleOwnerService
import json

def debug_plate():
    """Debug da consulta específica"""
    service = VehicleOwnerService()

    test_plate = "RAT9J67"
    print(f"🔍 Debugando placa: {test_plate}")

    try:
        result = service.lookup_vehicle_owner(test_plate)

        print(f"📊 Resultado completo:")
        print(json.dumps(result, indent=2, ensure_ascii=False))

        print(f"\n✅ Success: {result.get('success')}")
        print(f"📄 Source: {result.get('source')}")
        print(f"❌ Error: {result.get('error')}")

        if result.get('data'):
            data = result['data']
            print(f"\n📋 Estrutura dos dados:")
            for key, value in data.items():
                print(f"  {key}: {type(value)} - {len(str(value))} chars")

    except Exception as e:
        print(f"❌ Exceção: {e}")
        import traceback
        traceback.print_exc()

    finally:
        service.close()

if __name__ == "__main__":
    debug_plate()