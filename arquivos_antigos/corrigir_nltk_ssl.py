#!/usr/bin/env python3
"""
Script para corrigir problemas de SSL do NLTK
"""

import ssl
import nltk

print("=" * 80)
print("🔧 CORRIGINDO PROBLEMAS DE SSL DO NLTK")
print("=" * 80)
print()

# Desabilitar verificação SSL temporariamente para download
try:
    _create_unverified_https_context = ssl._create_unverified_context
except AttributeError:
    pass
else:
    ssl._create_default_https_context = _create_unverified_https_context

print("Baixando dados do NLTK necessários...")
print()

# Baixar dados necessários
packages = [
    'averaged_perceptron_tagger',
    'averaged_perceptron_tagger_eng',
    'punkt',
    'punkt_tab',
]

for package in packages:
    try:
        print(f"Baixando {package}...", end=" ")
        nltk.download(package, quiet=True)
        print("✅")
    except Exception as e:
        print(f"⚠️  ({str(e)[:50]})")

print()
print("=" * 80)
print("✅ Processo concluído!")
print("=" * 80)
print()
print("Os warnings de SSL não devem mais aparecer.")
print("Execute seu script normalmente agora.")

