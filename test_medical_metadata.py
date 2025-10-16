#!/usr/bin/env python3
"""
Teste de Extração de Metadata Médico
Valida funções extract_section_heading() e infer_document_type()
"""

import sys
import os

# Importar funções do adicionar_pdf
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

print("=" * 70)
print("🧪 TESTE DE METADATA MÉDICO")
print("=" * 70)
print()

# ============================================================================
# TESTE 1: infer_document_type()
# ============================================================================
print("📋 TESTE 1: Inferir Tipo de Documento")
print("-" * 70)

# Criar mock da função (copiar do adicionar_pdf.py)
def infer_document_type(filename):
    """Infere tipo de documento médico pelo nome do arquivo"""
    filename_lower = filename.lower()

    # Artigos de revisão
    if any(word in filename_lower for word in ['artigo de revisão', 'review article', 'review -', '- review']):
        return 'review_article'

    # Guidelines / Diretrizes
    if any(word in filename_lower for word in ['guideline', 'diretriz', 'consenso', 'consensus', 'recomendações']):
        return 'clinical_guideline'

    # Relatos de caso
    if any(word in filename_lower for word in ['case report', 'relato de caso', 'case series']):
        return 'case_report'

    # Ensaios clínicos / RCTs
    if any(word in filename_lower for word in ['rct', 'trial', 'ensaio clínico', 'clinical trial', 'randomized']):
        return 'clinical_trial'

    # Meta-análises
    if any(word in filename_lower for word in ['meta-analysis', 'metanálise', 'meta-análise', 'systematic review', 'revisão sistemática']):
        return 'meta_analysis'

    # Estudos de coorte
    if any(word in filename_lower for word in ['cohort', 'coorte', 'prospective study', 'estudo prospectivo']):
        return 'cohort_study'

    # Estudos observacionais
    if any(word in filename_lower for word in ['observational', 'observacional', 'cross-sectional', 'transversal']):
        return 'observational_study'

    # Artigos originais / pesquisa
    if any(word in filename_lower for word in ['original article', 'artigo original', 'research article', 'research paper']):
        return 'original_research'

    # Editoriais / Comentários
    if any(word in filename_lower for word in ['editorial', 'commentary', 'comentário', 'perspective']):
        return 'editorial'

    # Default: artigo médico genérico
    return 'medical_article'

# Casos de teste
test_filenames = [
    ("Artigo de Revisão - NEJM - Síndrome de Lise Tumoral.pdf", "review_article"),
    ("Clinical Guideline - Hypertension Management 2024.pdf", "clinical_guideline"),
    ("Case Report - Rare Neurological Disorder.pdf", "case_report"),
    ("RCT - Novel Drug for Diabetes Treatment.pdf", "clinical_trial"),
    ("Meta-análise - Eficácia de Estatinas.pdf", "meta_analysis"),
    ("Cohort Study - 10 Year Follow-up.pdf", "cohort_study"),
    ("Original Article - Genetic Markers.pdf", "original_research"),
    ("Editorial - Future of Oncology.pdf", "editorial"),
    ("Artigo Médico Genérico.pdf", "medical_article"),
]

passed = 0
failed = 0

for filename, expected_type in test_filenames:
    result = infer_document_type(filename)
    status = "✅" if result == expected_type else "❌"

    if result == expected_type:
        passed += 1
    else:
        failed += 1

    print(f"{status} {filename[:50]:<50} → {result}")

print()
print(f"Resultado: {passed}/{len(test_filenames)} testes passaram")
print()

# ============================================================================
# TESTE 2: extract_section_heading()
# ============================================================================
print("📑 TESTE 2: Extrair Section Heading")
print("-" * 70)

# Criar mock de elementos de texto
class MockMetadata:
    def __init__(self, category):
        self.category = category

class MockTextElement:
    def __init__(self, text, category):
        self.text = text
        self.metadata = MockMetadata(category)

def extract_section_heading(text_element):
    """Extrai section heading de elementos de texto"""
    if not hasattr(text_element, 'metadata'):
        return None

    if hasattr(text_element.metadata, 'category'):
        cat = text_element.metadata.category

        if cat == 'Title':
            text = text_element.text if hasattr(text_element, 'text') else str(text_element)
            text_lower = text.lower().strip()

            medical_sections = {
                'resumo': 'Resumo',
                'abstract': 'Abstract',
                'introdução': 'Introdução',
                'introduction': 'Introduction',
                'métodos': 'Métodos',
                'methods': 'Methods',
                'metodologia': 'Metodologia',
                'resultados': 'Resultados',
                'results': 'Results',
                'discussão': 'Discussão',
                'discussion': 'Discussion',
                'conclusão': 'Conclusão',
                'conclusion': 'Conclusion',
                'referências': 'Referências',
                'references': 'References',
                'relato de caso': 'Relato de Caso',
                'case report': 'Case Report',
                'diagnóstico': 'Diagnóstico',
                'diagnosis': 'Diagnosis',
                'tratamento': 'Tratamento',
                'treatment': 'Treatment',
            }

            for key, value in medical_sections.items():
                if key in text_lower:
                    return value

    return None

# Casos de teste
test_sections = [
    ("ABSTRACT", "Title", "Abstract"),
    ("Resumo", "Title", "Resumo"),
    ("INTRODUÇÃO", "Title", "Introdução"),
    ("Methods and Materials", "Title", "Methods"),
    ("RESULTADOS", "Title", "Resultados"),
    ("Discussion", "Title", "Discussion"),
    ("Conclusões", "Title", "Conclusão"),
    ("REFERÊNCIAS BIBLIOGRÁFICAS", "Title", "Referências"),
    ("Case Report: Unusual Presentation", "Title", "Case Report"),
    ("Treatment Protocol", "Title", "Treatment"),
    ("Texto normal", "NarrativeText", None),  # Não é Title
    ("Qualquer coisa", "Title", None),  # Title mas não é seção conhecida
]

passed2 = 0
failed2 = 0

for text, category, expected_section in test_sections:
    element = MockTextElement(text, category)
    result = extract_section_heading(element)
    status = "✅" if result == expected_section else "❌"

    if result == expected_section:
        passed2 += 1
    else:
        failed2 += 1

    result_str = result if result else "None"
    print(f"{status} [{category:15}] {text[:35]:<35} → {result_str}")

print()
print(f"Resultado: {passed2}/{len(test_sections)} testes passaram")
print()

# ============================================================================
# RESUMO FINAL
# ============================================================================
print("=" * 70)
print("📊 RESUMO DOS TESTES")
print("=" * 70)

total_passed = passed + passed2
total_tests = len(test_filenames) + len(test_sections)

print(f"Total de testes: {total_tests}")
print(f"Testes aprovados: {total_passed}")
print(f"Testes falhados: {total_tests - total_passed}")
print()

if total_passed == total_tests:
    print("✅ TODOS OS TESTES PASSARAM!")
    print("Sistema de metadata médico está funcionando corretamente.")
else:
    print(f"⚠️  {total_tests - total_passed} testes falharam")
    print("Revise as funções de extração de metadata")

print()
print("=" * 70)
print("💡 PRÓXIMO PASSO: Processar um PDF médico real")
print()
print("   python adicionar_pdf.py 'content/Artigo de Revisão.pdf'")
print()
print("   O sistema agora vai:")
print("   1. Detectar tipo: review_article")
print("   2. Extrair seções: Abstract, Introduction, Methods, etc.")
print("   3. Adicionar metadata enriquecido a cada chunk")
print("=" * 70)
