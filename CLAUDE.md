# CLAUDE.md

## Project Overview

MVP MCP server for vehicle dealer fraud verification in Brazil. Single file (`mvp_dealer_fraud_mcp.py`) with OpenAI API integration for CNPJ validation, reputation checks, and legal issue searches.

## Essential Commands

```bash
# Install and run
pip install -r requirements.txt
python mvp_dealer_fraud_mcp.py

# CLI testing (edit test_cli.py to add OpenAI API key)
python test_cli.py validate 11.222.333/0001-81
python test_cli.py complete 11.222.333/0001-81 --empresa "Nome da Empresa"
```

## Core Architecture

**MCP Tools:**
- `validate_cnpj`: CNPJ format validation (Brazilian algorithm)
- `verify_cnpj_status`: Company status check
- `check_dealer_reputation`: Online reputation analysis  
- `check_legal_issues`: Legal problems and fraud indicators
- `comprehensive_dealer_check`: Complete risk assessment

**Key Implementation:**
- Uses `gpt-4o` model (no real-time web search)
- JSON response parsing with `_extract_json_from_response()`
- Risk scores 0-100 based on multiple data sources
- Brazilian CNPJ validation with check digits

## Current Limitations

- OpenAI API key hardcoded (MVP only)
- Model knowledge instead of real-time web search
- No caching or rate limiting implemented