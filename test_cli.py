#!/usr/bin/env python3
"""
Interface CLI para testar o sistema de verificação de fraude em lojistas
"""

import asyncio
import argparse
import json
import sys
from typing import Dict, Any

# Importa a classe principal do MCP server
from mvp_dealer_fraud_mcp import DealerFraudChecker

class DealerFraudCLI:
    """Interface de linha de comando para testes do sistema de fraude."""
    
    def __init__(self):
        # Por enquanto, vamos usar uma API key de exemplo - você precisará configurar a sua
        self.checker = DealerFraudChecker("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")
    
    async def validate_cnpj(self, cnpj: str) -> None:
        """Valida um CNPJ."""
        print(f"🔍 Validando CNPJ: {cnpj}")
        print("-" * 50)
        
        is_valid = self.checker._validate_cnpj(cnpj)
        formatted = self.checker._format_cnpj(cnpj)
        
        if is_valid:
            print(f"✅ CNPJ VÁLIDO: {formatted}")
        else:
            print(f"❌ CNPJ INVÁLIDO: {cnpj}")
    
    async def check_status(self, cnpj: str) -> None:
        """Verifica status do CNPJ na Receita Federal."""
        print(f"🏢 Verificando status oficial do CNPJ: {cnpj}")
        print("-" * 50)
        
        try:
            result = await self.checker.verify_cnpj_status(cnpj)
            self._print_json_result(result)
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    async def check_reputation(self, cnpj: str, company_name: str = None) -> None:
        """Verifica reputação online."""
        print(f"⭐ Verificando reputação do CNPJ: {cnpj}")
        if company_name:
            print(f"📝 Nome da empresa: {company_name}")
        print("-" * 50)
        
        try:
            result = await self.checker.check_dealer_reputation(cnpj, company_name)
            self._print_json_result(result)
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    async def check_legal(self, cnpj: str, company_name: str = None) -> None:
        """Verifica questões legais."""
        print(f"⚖️  Verificando questões legais do CNPJ: {cnpj}")
        if company_name:
            print(f"📝 Nome da empresa: {company_name}")
        print("-" * 50)
        
        try:
            result = await self.checker.check_legal_issues(cnpj, company_name)
            self._print_json_result(result)
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    async def comprehensive_check(self, cnpj: str, company_name: str = None) -> None:
        """Executa verificação completa."""
        print(f"🔍 ANÁLISE COMPLETA DO CNPJ: {cnpj}")
        if company_name:
            print(f"📝 Nome da empresa: {company_name}")
        print("=" * 60)
        
        try:
            result = await self.checker.comprehensive_check(cnpj, company_name)
            self._print_json_result(result)
        except Exception as e:
            print(f"❌ Erro: {e}")
    
    def _print_json_result(self, result: Dict[str, Any]) -> None:
        """Imprime resultado JSON de forma formatada."""
        try:
            print(json.dumps(result, indent=2, ensure_ascii=False))
        except Exception:
            print(result)
        print("-" * 50)

async def main():
    """Função principal da CLI."""
    parser = argparse.ArgumentParser(
        description="Sistema CLI para verificação de fraude em lojistas de veículos"
    )
    
    parser.add_argument("comando", 
                       choices=["validate", "status", "reputation", "legal", "complete"],
                       help="Tipo de verificação a realizar")
    
    parser.add_argument("cnpj", 
                       help="CNPJ do lojista (com ou sem formatação)")
    
    parser.add_argument("--empresa", "-e",
                       help="Nome da empresa (opcional)")
    
    args = parser.parse_args()
    
    cli = DealerFraudCLI()
    
    try:
        if args.comando == "validate":
            await cli.validate_cnpj(args.cnpj)
        elif args.comando == "status":
            await cli.check_status(args.cnpj)
        elif args.comando == "reputation":
            await cli.check_reputation(args.cnpj, args.empresa)
        elif args.comando == "legal":
            await cli.check_legal(args.cnpj, args.empresa)
        elif args.comando == "complete":
            await cli.comprehensive_check(args.cnpj, args.empresa)
    
    except KeyboardInterrupt:
        print("\n⏹️  Operação cancelada pelo usuário")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Erro inesperado: {e}")
        sys.exit(1)

if __name__ == "__main__":
    print("🚗 Sistema de Verificação de Fraude em Lojistas - CLI")
    print("=" * 60)
    
    try:
        asyncio.run(main())
    except Exception as e:
        print(f"❌ Erro fatal: {e}")
        sys.exit(1)