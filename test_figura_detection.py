#!/usr/bin/env python3
"""Testar se queries sobre figura estão sendo detectadas"""

import re

def detect_image_query(question):
    """Mesma função do código"""
    image_patterns = [
        r'\bfigura\s+\d+\b',  # "figura 1", "figura 2"
        r'\bfig\.?\s*\d+\b',   # "fig. 1", "fig 2"
        r'\btabela\s+\d+\b',   # "tabela 1"
        r'\bfluxograma\b',
        r'\balgorit?mo\b',
        r'\bdiagrama\b',
        r'\bgr[aá]fico\b',
        r'\bimagem\b',
        r'\bilustra[çc][ãa]o\b',
        r'\bexplique\s+(a|o)\s+(figura|imagem|fluxograma|algoritmo|diagrama)\b',
        r'\bdescreva\s+(a|o)\s+(figura|imagem|fluxograma)\b',
        r'\bo\s+que\s+(mostra|diz|apresenta)\s+(a|o)\s+(figura|imagem)\b',
    ]

    keywords_found = []
    for pattern in image_patterns:
        match = re.search(pattern, question.lower())
        if match:
            keywords_found.append(match.group(0))

    return len(keywords_found) > 0, keywords_found

# Testar queries que você usou
queries = [
    "Fale sobre o fluxograma 1 do documento de hiperglicemia no paciente internado não crítico",
    "Explique detalhadamente a figura 1 do documento de hiperglicemia no paciente internado não crítico",
    "quais figuras há no documento documento de hiperglicemia no paciente internado não crítico"
]

print("=" * 80)
print("🧪 TESTE DE DETECÇÃO DE QUERIES SOBRE IMAGENS")
print("=" * 80)

for query in queries:
    is_image, keywords = detect_image_query(query)
    print(f"\nQuery: {query}")
    print(f"Detectou? {'✅ SIM' if is_image else '❌ NÃO'}")
    if keywords:
        print(f"Keywords: {keywords}")
    print()

print("=" * 80)
