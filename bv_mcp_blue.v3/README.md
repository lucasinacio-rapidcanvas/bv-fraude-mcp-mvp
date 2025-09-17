# MVP - Verificação de Fraude em Lojistas de Veículos 🚗🔍

**Versão MVP** usando OpenAI Responses API com Web Search para verificação rápida de fraude em lojistas, concessionárias e vendedores de veículos no Brasil.

## 🎯 O que faz este MVP

Verifica rapidamente se um lojista de veículos é confiável através de:
- ✅ **Validação de CNPJ** (algoritmo oficial brasileiro)
- ✅ **Situação cadastral** na Receita Federal
- ✅ **Reputação online** (Reclame Aqui, Google Reviews)
- ✅ **Processos judiciais** (JusBrasil, Tribunais)
- ✅ **Score de risco** automático (0-100)
- ✅ **Recomendações** específicas

## 🚀 Instalação Rápida

### 1. Clone e instale
```bash
git clone <repo>
cd dealer-fraud-mvp
pip install -r requirements.txt
```

### 2. Configure a API Key
A API key do OpenAI já está configurada no código para este MVP.

### 3. Execute o servidor MCP
```bash
python mvp_dealer_fraud_mcp.py
```

### 4. OU use a Interface Web (Streamlit) 🎯 NOVA!
```bash
# Executar interface web completa
streamlit run app.py

# OU usar o script de inicialização
python run_streamlit.py
```
**Acesse:** http://localhost:8501

### 5. OU use a Interface CLI para Testes
```bash
# Validação básica de CNPJ (sem API key necessária)
python test_cli.py validate 11.222.333/0001-81

# Verificação completa (requer API key configurada)
python test_cli.py complete 11.222.333/0001-81 --empresa "Nome da Empresa"
```

### 6. Use com Claude Desktop

Adicione ao `claude_desktop_config.json`:
```json
{
  "mcpServers": {
    "dealer-fraud-mvp": {
      "command": "python",
      "args": ["/caminho/completo/para/mvp_dealer_fraud_mcp.py"]
    }
  }
}
```

## 💡 Como Usar

### Interface CLI (Nova!)
```bash
# Ver todas as opções disponíveis
python test_cli.py --help

# Validar CNPJ (offline, sem API key)
python test_cli.py validate 11.222.333/0001-81

# Verificar status oficial da empresa
python test_cli.py status 11.222.333/0001-81

# Verificar reputação online
python test_cli.py reputation 11.222.333/0001-81 --empresa "AutoCenter ABC"

# Verificar questões legais
python test_cli.py legal 11.222.333/0001-81

# Análise completa
python test_cli.py complete 11.222.333/0001-81 --empresa "AutoCenter ABC"
```

### Claude Desktop

#### Exemplo 1: Verificação Rápida
```
Verifique se o lojista com CNPJ 11.222.333/0001-81 é confiável.
```

#### Exemplo 2: Análise Completa  
```
Faça uma investigação completa do lojista "AutoCenter ABC" 
CNPJ 11222333000181 - suspeito de fraude na venda.
```

#### Exemplo 3: Pré-Compra
```
Vou comprar um Civic 2020 no lojista CNPJ 11.222.333/0001-81.
É seguro prosseguir?
```

## 🛠️ Ferramentas Disponíveis

| Ferramenta | Descrição | Quando Usar |
|------------|-----------|-------------|
| `validate_cnpj` | Valida formato do CNPJ | Sempre primeiro |
| `verify_cnpj_status` | Situação na Receita Federal | Verificação básica |
| `check_dealer_reputation` | Reclame Aqui, Google | Para reputação |
| `check_legal_issues` | Processos judiciais | Para questões legais |
| `comprehensive_dealer_check` | Análise completa | Para decisões importantes |

## 📊 Interpretando Resultados

### Score de Risco
- **0-24**: ✅ **BAIXO** - Aparentemente seguro
- **25-49**: ⚠️ **MÉDIO** - Prosseguir com cautela  
- **50-74**: 🚨 **ALTO** - Investigar mais
- **75-100**: 🚫 **CRÍTICO** - Evitar negociação

### Red Flags Críticos
- CNPJ cancelado/suspenso
- Processos por fraude/estelionato
- Múltiplas reclamações não respondidas
- Menções negativas na mídia
- Empresa muito nova com muitas vendas

## 🔧 Limitações do MVP

### O que NÃO faz ainda:
- ❌ Web search em tempo real (usa conhecimento do modelo)
- ❌ Cache de resultados (consulta sempre online)
- ❌ Rate limiting avançado
- ❌ Múltiplas APIs simultâneas
- ❌ Análise de padrões com ML
- ❌ Relatórios detalhados em PDF

### Dependências:
- ⚠️ Validação CNPJ funciona offline
- ⚠️ Outras funcionalidades requerem OpenAI API key
- ⚠️ Análises baseadas no conhecimento do modelo GPT-4o
- ⚠️ Para dados em tempo real, seria necessário integrar APIs específicas

## 🔄 Próxima Evolução

Após validar este MVP, a próxima versão incluirá:

1. **MCP Server Híbrido** com APIs específicas
2. **Cache inteligente** para reduzir custos
3. **Múltiplas fontes paralelas** 
4. **Machine Learning** para detecção de padrões
5. **Dashboard** para monitoramento
6. **APIs regionais** dos Detrans

## 📋 Exemplos de Uso

### Claude Prompt Examples

#### Verificação Básica
```
Claude, use a ferramenta validate_cnpj para verificar se o CNPJ 11.222.333/0001-81 é válido.
```

#### Investigação de Fraude
```
Use o prompt "investigate_dealer" com:
- cnpj: "11222333000181"  
- company_name: "AutoCenter São Paulo"
- concern: "cliente reportou problemas no carro após compra"
```

#### Pré-Compra
```
Use o prompt "pre_purchase_check" com:
- cnpj: "11222333000181"
- vehicle_info: "Honda Civic 2020, R$ 85.000"
```

## ⚠️ Disclaimer

Este é um **MVP para validação de conceito**. Para decisões comerciais importantes:

- ✅ **Use** como análise inicial
- ✅ **Confirme** informações independentemente  
- ✅ **Visite** o lojista pessoalmente
- ✅ **Consulte** advogado se necessário
- ❌ **NÃO** tome decisões baseado apenas neste sistema

## 🆘 Troubleshooting

### Problema: "CNPJ inválido"
**Solução**: Verifique se o CNPJ tem 14 dígitos e está correto

### Problema: "Poucos resultados encontrados"  
**Solução**: Empresa pode ser muito nova ou ter pouca presença online

### Problema: "Erro na requisição OpenAI"
**Solução**: Verifique sua API key da OpenAI em `test_cli.py` ou conexão de internet

### Problema: "Invalid value: 'web_search'"
**Solução**: ✅ **RESOLVIDO** - Removemos dependência de web search, agora funciona com GPT-4o base

### Problema: "Parsing JSON"
**Solução**: ✅ **RESOLVIDO** - Sistema agora extrai JSON corretamente de respostas markdown

## 📞 Suporte

Para problemas ou sugestões:
- 🐛 Abra uma issue no GitHub
- 💬 Use as discussões do repositório  
- 📖 Consulte a documentação completa nos recursos MCP

---

**🎯 Objetivo do MVP**: Validar rapidamente se o conceito funciona antes de investir na versão completa híbrida.

**⏱️ Tempo estimado de desenvolvimento**: 2-3 dias para este MVP vs 4-6 semanas para versão completa.