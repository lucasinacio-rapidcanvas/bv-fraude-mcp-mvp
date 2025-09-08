#!/usr/bin/env python3
"""
Simple test script to show OpenAI API response structure
"""

import asyncio
import json
import logging
from datetime import datetime
from openai import AsyncOpenAI

# Configuração de logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("test-api")

class SimpleAPITest:
    def __init__(self, api_key: str):
        self.client = AsyncOpenAI(api_key=api_key)
        
    async def test_responses_api(self):
        """Testa a Responses API e mostra a estrutura completa da resposta."""
        
        prompt = """
        Pesquise informações sobre uma empresa brasileira fictícia com CNPJ 11.222.333/0001-81.
        
        Retorne em formato JSON:
        {
          "cnpj": "11.222.333/0001-81",
          "company_name": "Empresa Teste Ltda",
          "status": "ativa",
          "teste": "informação de teste"
        }
        """
        
        logger.info("🔄 Testando OpenAI Responses API...")
        
        try:
            # Testa Responses API primeiro
            response = await self.client.responses.create(
                model="gpt-4o",
                input=prompt,
                tools=[{"type": "web_search"}]
            )
            
            logger.info("✅ Resposta recebida da Responses API")
            logger.info(f"📊 Tipo da resposta: {type(response)}")
            logger.info(f"📊 Atributos disponíveis: {[attr for attr in dir(response) if not attr.startswith('_')]}")
            
            # Mostra a estrutura completa
            if hasattr(response, 'model_dump'):
                logger.info("📊 Resposta completa (model_dump):")
                response_dict = response.model_dump()
                logger.info(json.dumps(response_dict, indent=2, ensure_ascii=False))
            else:
                logger.info(f"📊 Resposta completa (str): {response}")
            
            # Tenta extrair o texto
            if hasattr(response, 'output') and response.output:
                logger.info(f"📊 Output disponível: {len(response.output)} items")
                
                for idx, item in enumerate(response.output):
                    logger.info(f"  Item {idx}: tipo={getattr(item, 'type', 'unknown')}")
                    if hasattr(item, 'model_dump'):
                        logger.info(f"  Conteúdo do item {idx}: {json.dumps(item.model_dump(), indent=2, ensure_ascii=False)}")
                    
                    if hasattr(item, 'type') and item.type == 'message':
                        if hasattr(item, 'content') and item.content:
                            for content_idx, content_item in enumerate(item.content):
                                if hasattr(content_item, 'text'):
                                    text_content = content_item.text
                                    logger.info(f"✅ Texto extraído: {len(text_content)} caracteres")
                                    logger.info(f"📝 Conteúdo: {text_content[:500]}...")
                                    return text_content
            
            return "Nenhum texto encontrado"
            
        except Exception as e:
            logger.error(f"❌ Erro na Responses API: {e}")
            logger.error(f"   Tipo do erro: {type(e).__name__}")
            
            # Fallback para Chat Completions
            try:
                logger.info("🔄 Tentando fallback para Chat Completions API...")
                response = await self.client.chat.completions.create(
                    model="gpt-4o",
                    messages=[
                        {"role": "system", "content": "Você é um assistente que responde em JSON."},
                        {"role": "user", "content": prompt}
                    ],
                    temperature=0.0,
                    max_tokens=1000
                )
                
                logger.info("✅ Resposta recebida da Chat Completions API")
                logger.info(f"📊 Uso de tokens: {response.usage}")
                
                content = response.choices[0].message.content
                logger.info(f"📝 Conteúdo: {content}")
                return content
                
            except Exception as e2:
                logger.error(f"❌ Erro também no fallback: {e2}")
                return f"Erro: {str(e)} | Fallback: {str(e2)}"

async def main():
    # API key das variáveis de ambiente
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    API_KEY = os.getenv("OPENAI_API_KEY")
    if not API_KEY:
        print("❌ OPENAI_API_KEY não encontrada nas variáveis de ambiente")
        return
    
    tester = SimpleAPITest(API_KEY)
    result = await tester.test_responses_api()
    
    print("\n" + "="*50)
    print("RESULTADO FINAL:")
    print("="*50)
    print(result)

if __name__ == "__main__":
    asyncio.run(main())