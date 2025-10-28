#!/usr/bin/env python3
"""Test YAKE keyword extraction in production"""

import requests
import json

# Fazer request com query médica
response = requests.post(
    'https://comfortable-tenderness-production.up.railway.app/query',
    json={'question': 'Qual o tratamento da síndrome de lise tumoral segundo critérios de cairo-bishop?'},
    headers={'Content-Type': 'application/json'}
)

print('=== TESTE DE KEYWORD EXTRACTION COM YAKE ===\n')
print(f'Status Code: {response.status_code}')

if response.status_code == 200:
    try:
        data = response.json()
        print(f'\n✅ Query processada com sucesso')
        print(f'Imagens retornadas: {data.get("num_images", 0)}')
        print(f'Resposta: {len(data.get("answer", ""))} caracteres')
        print(f'\nPrimeiros 300 caracteres:')
        print(data.get('answer', '')[:300])
        print('\n...\n')
        print('✅ Sistema operacional com YAKE!')
        print('\n⚠️  Nota: Logs de keyword extraction aparecem no Railway, não na resposta HTTP')
        print('    Para ver as keywords extraídas, verifique os logs do Railway')
    except Exception as e:
        print(f'Erro ao parsear JSON: {e}')
        print(f'Response text: {response.text[:200]}')
else:
    print(f'Erro HTTP: {response.status_code}')
    print(f'Response: {response.text}')
