#!/usr/bin/env python3
"""
Teste da funcionalidade de relatório JSON para veículos
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from vehicle_owner_service import VehicleOwnerService
from datetime import datetime
import json

def generate_vehicle_report(plate_input: str, result: dict) -> dict:
    """Gera um relatório estruturado para consulta de veículo"""
    report = {
        "metadata": {
            "report_type": "vehicle_owner_consultation",
            "version": "2.2",
            "generated_at": datetime.now().isoformat(),
            "generated_by": "BV - Sistema de Verificação de Fraude",
            "plate": plate_input.upper(),
            "consultation_status": "success" if result["success"] else "error"
        },
        "consultation_info": {
            "data_source": result.get("source", "unknown"),
            "cached_at": result.get("cached_at", None),
            "consulted_at": result.get("consulted_at", None),
            "timeout_used": result.get("timeout_used", None),
            "error_message": result.get("error", None)
        },
        "vehicle_data": {},
        "owner_data": {},
        "restrictions_data": {},
        "registration_data": {},
        "raw_api_response": {}
    }

    if result["success"] and result.get("data"):
        data = result["data"]

        # Dados do veículo
        if data.get("vehicle_info"):
            vehicle = data["vehicle_info"]
            report["vehicle_data"] = {
                "identification": {
                    "plate": vehicle.get("plate", ""),
                    "renavam": vehicle.get("renavam", ""),
                    "chassis": vehicle.get("chassis", "")
                },
                "specifications": {
                    "brand": vehicle.get("brand", ""),
                    "model": vehicle.get("model", ""),
                    "year_manufacture": vehicle.get("year_manufacture", ""),
                    "year_model": vehicle.get("year_model", ""),
                    "color": vehicle.get("color", ""),
                    "fuel_type": vehicle.get("fuel_type", ""),
                    "category": vehicle.get("category", "")
                }
            }

        # Dados do proprietário
        if data.get("owner_info"):
            owner = data["owner_info"]
            report["owner_data"] = {
                "personal_info": {
                    "name": owner.get("name", ""),
                    "document": owner.get("document", ""),
                    "document_type": owner.get("document_type", "")
                },
                "address": owner.get("address", {})
            }

        # Restrições
        if data.get("restrictions"):
            restrictions = data["restrictions"]
            report["restrictions_data"] = {
                "has_restrictions": restrictions.get("has_restrictions", False),
                "general_restrictions": restrictions.get("restriction_list", []),
                "judicial_restrictions": restrictions.get("judicial_restrictions", []),
                "administrative_restrictions": restrictions.get("administrative_restrictions", [])
            }

        # Dados de registro
        if data.get("registration_info"):
            registration = data["registration_info"]
            report["registration_data"] = {
                "registration_date": registration.get("registration_date", ""),
                "last_transfer": registration.get("last_transfer", ""),
                "municipal_registration": registration.get("municipal_registration", ""),
                "origin_state": registration.get("origin_state", "")
            }

        # Resposta bruta da API
        if data.get("raw_data"):
            report["raw_api_response"] = data["raw_data"]

    return report

def test_json_report():
    """Testa a geração de relatório JSON"""
    print("🔍 Testando geração de relatório JSON para veículos...")

    service = VehicleOwnerService()

    # Testa com placa que vai dar erro (limite excedido)
    test_plate = "RAT9J67"
    print(f"\n📋 Testando relatório para placa: {test_plate}")

    try:
        # Consulta o veículo
        result = service.lookup_vehicle_owner(test_plate)

        # Gera o relatório
        report = generate_vehicle_report(test_plate, result)

        print(f"✅ Relatório gerado com sucesso!")
        print(f"📊 Status da consulta: {report['metadata']['consultation_status']}")
        print(f"📄 Tipo do relatório: {report['metadata']['report_type']}")
        print(f"🕒 Gerado em: {report['metadata']['generated_at']}")

        # Salva o relatório em arquivo para teste
        filename = f"teste_relatorio_{test_plate}_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(report, f, indent=2, ensure_ascii=False)

        print(f"💾 Relatório salvo em: {filename}")

        # Mostra estrutura do relatório
        print(f"\n📋 Estrutura do relatório:")
        for section, content in report.items():
            if isinstance(content, dict):
                print(f"  📁 {section}: {len(content)} campos")
            else:
                print(f"  📄 {section}: {type(content).__name__}")

        # Verifica se é um erro
        if not result["success"]:
            print(f"\n❌ Erro detectado: {result.get('error')}")
            print(f"📊 Relatório de erro gerado corretamente")

    except Exception as e:
        print(f"❌ Erro no teste: {e}")
        import traceback
        traceback.print_exc()

    finally:
        service.close()

if __name__ == "__main__":
    test_json_report()