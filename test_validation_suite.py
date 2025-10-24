#!/usr/bin/env python3
"""
🧪 SUITE DE VALIDAÇÃO - RAG Multimodal
Testa o sistema com perguntas difíceis e variadas baseadas nos documentos indexados

Documentos disponíveis:
1. Artigo de Revisão - Nature Review Disease Primers - Nefrite Lúpica.pdf
2. Artigo de Revisão - NEJM - Gamopatia Monoclonal de Significado Indeterminado.pdf
3. Artigo de Revisão - NEJM - Síndrome de Lise Tumoral.pdf
4. Artigo de Revisão - Prostatite - JAMA.pdf
5. Diretriz Brasileira de Diabetes 2025 - Manejo da terapia antidiabética no DM2.pdf
"""

import requests
import json
from datetime import datetime
from typing import List, Dict
import time

# ==============================================================================
# CONFIGURAÇÃO
# ==============================================================================

# URL da API (Railway ou local)
API_URL = "https://multimodal-rag-langchain-production.up.railway.app/query"
# API_URL = "http://localhost:5001/query"  # Descomente para testar local

# ==============================================================================
# DATASET DE TESTES - 30 PERGUNTAS ESTRATÉGICAS
# ==============================================================================

TEST_QUERIES: List[Dict] = [
    # =========================================================================
    # CATEGORIA 1: DIABETES (Diretriz Brasileira) - 8 perguntas
    # =========================================================================
    {
        "id": "D1",
        "category": "Diabetes - Retrieval Direto",
        "question": "Quais são os critérios de muito alto risco cardiovascular segundo a diretriz brasileira de diabetes 2025?",
        "expected_topics": ["3 ou mais fatores", "Hipercolesterolemia Familiar", "albuminúria >300", "TFG <30"],
        "difficulty": "Fácil",
        "document": "Diretriz Brasileira de Diabetes 2025"
    },
    {
        "id": "D2",
        "category": "Diabetes - Valores Numéricos",
        "question": "Qual o valor de HbA1c que define controle glicêmico inadequado e indica necessidade de intensificação terapêutica?",
        "expected_topics": ["HbA1c", ">7%", "intensificação"],
        "difficulty": "Médio",
        "document": "Diretriz Brasileira de Diabetes 2025"
    },
    {
        "id": "D3",
        "category": "Diabetes - Contraindicações",
        "question": "Em quais valores de TFG a Metformina é contraindicada ou requer ajuste de dose?",
        "expected_topics": ["TFG <30", "contraindicada", "TFG 30-45", "ajuste"],
        "difficulty": "Médio",
        "document": "Diretriz Brasileira de Diabetes 2025"
    },
    {
        "id": "D4",
        "category": "Diabetes - Tratamento Complexo",
        "question": "Para pacientes com diabetes tipo 2 e risco cardiovascular muito alto, quais classes de antidiabéticos são preferenciais além da metformina?",
        "expected_topics": ["iSGLT2", "AR GLP-1", "benefício cardiovascular"],
        "difficulty": "Médio",
        "document": "Diretriz Brasileira de Diabetes 2025"
    },
    {
        "id": "D5",
        "category": "Diabetes - Multi-hop",
        "question": "Se um paciente tem albuminúria de 350 mg/g e TFG de 42 ml/min, qual sua estratificação de risco e qual medicamento pode estar contraindicado?",
        "expected_topics": ["muito alto risco", "albuminúria >300", "TFG <45", "metformina"],
        "difficulty": "Difícil",
        "document": "Diretriz Brasileira de Diabetes 2025"
    },
    {
        "id": "D6",
        "category": "Diabetes - Negação",
        "question": "Quando NÃO usar insulina como primeira linha no diabetes tipo 2?",
        "expected_topics": ["primeira linha", "metformina", "HbA1c <9%"],
        "difficulty": "Difícil",
        "document": "Diretriz Brasileira de Diabetes 2025"
    },
    {
        "id": "D7",
        "category": "Diabetes - Interpretação Coloquial",
        "question": "Qual remédio é melhor para quem é gordo e tem diabetes?",
        "expected_topics": ["obesidade", "IMC", "iSGLT2", "AR GLP-1", "perda de peso"],
        "difficulty": "Difícil",
        "document": "Diretriz Brasileira de Diabetes 2025"
    },
    {
        "id": "D8",
        "category": "Diabetes - Relação Entre Conceitos",
        "question": "Qual a relação entre albuminúria e risco cardiovascular em pacientes com diabetes?",
        "expected_topics": ["marcador", "lesão endotelial", "risco cardiovascular", "muito alto"],
        "difficulty": "Difícil",
        "document": "Diretriz Brasileira de Diabetes 2025"
    },

    # =========================================================================
    # CATEGORIA 2: NEFRITE LÚPICA (Nature) - 6 perguntas
    # =========================================================================
    {
        "id": "NL1",
        "category": "Nefrite Lúpica - Classificação",
        "question": "Qual a classificação simplificada de nefrite lúpica segundo a ISN/RPS?",
        "expected_topics": ["classe I", "classe II", "classe III", "classe IV", "classe V", "ISN/RPS"],
        "difficulty": "Fácil",
        "document": "Nefrite Lúpica"
    },
    {
        "id": "NL2",
        "category": "Nefrite Lúpica - Diagnóstico",
        "question": "Quais os achados histopatológicos que definem nefrite lúpica classe IV?",
        "expected_topics": ["glomerulonefrite proliferativa difusa", "50%", "glomérulos"],
        "difficulty": "Médio",
        "document": "Nefrite Lúpica"
    },
    {
        "id": "NL3",
        "category": "Nefrite Lúpica - Tratamento",
        "question": "Qual o tratamento de indução padrão para nefrite lúpica proliferativa?",
        "expected_topics": ["micofenolato", "ciclofosfamida", "corticoides"],
        "difficulty": "Médio",
        "document": "Nefrite Lúpica"
    },
    {
        "id": "NL4",
        "category": "Nefrite Lúpica - Prognóstico",
        "question": "Quais fatores prognósticos indicam pior evolução na nefrite lúpica?",
        "expected_topics": ["creatinina elevada", "hipertensão", "fibrose intersticial", "raça negra"],
        "difficulty": "Médio",
        "document": "Nefrite Lúpica"
    },
    {
        "id": "NL5",
        "category": "Nefrite Lúpica - Diferenciação",
        "question": "Qual a diferença entre nefrite lúpica classe III e classe IV?",
        "expected_topics": ["focal", "difusa", "<50%", ">50%", "glomérulos"],
        "difficulty": "Difícil",
        "document": "Nefrite Lúpica"
    },
    {
        "id": "NL6",
        "category": "Nefrite Lúpica - Multi-hop",
        "question": "Por que pacientes com nefrite lúpica classe V têm proteinúria maciça mas preservam melhor a função renal inicialmente?",
        "expected_topics": ["membranosa", "podócitos", "não proliferativa", "síndrome nefrótica"],
        "difficulty": "Muito Difícil",
        "document": "Nefrite Lúpica"
    },

    # =========================================================================
    # CATEGORIA 3: MGUS (NEJM) - 5 perguntas
    # =========================================================================
    {
        "id": "MGUS1",
        "category": "MGUS - Diagnóstico",
        "question": "Quais os critérios diagnósticos para MGUS?",
        "expected_topics": ["proteína M", "<3 g/dL", "plasmócitos <10%", "ausência de dano orgânico"],
        "difficulty": "Fácil",
        "document": "MGUS"
    },
    {
        "id": "MGUS2",
        "category": "MGUS - Risco de Progressão",
        "question": "Qual o risco de progressão de MGUS para mieloma múltiplo?",
        "expected_topics": ["1% ao ano", "25 anos", "risco cumulativo"],
        "difficulty": "Médio",
        "document": "MGUS"
    },
    {
        "id": "MGUS3",
        "category": "MGUS - Fatores de Risco",
        "question": "Quais fatores de risco indicam maior probabilidade de progressão de MGUS?",
        "expected_topics": ["proteína M >1.5", "IgA ou IgM", "relação kappa/lambda alterada"],
        "difficulty": "Médio",
        "document": "MGUS"
    },
    {
        "id": "MGUS4",
        "category": "MGUS - Seguimento",
        "question": "Como deve ser o seguimento de pacientes com MGUS de baixo risco?",
        "expected_topics": ["6 meses", "anual", "eletroforese", "sem tratamento"],
        "difficulty": "Médio",
        "document": "MGUS"
    },
    {
        "id": "MGUS5",
        "category": "MGUS - Diferenciação",
        "question": "Qual a diferença entre MGUS e mieloma múltiplo smoldering?",
        "expected_topics": ["proteína M", "plasmócitos", "10%", "dano orgânico", "CRAB"],
        "difficulty": "Difícil",
        "document": "MGUS"
    },

    # =========================================================================
    # CATEGORIA 4: SÍNDROME DE LISE TUMORAL (NEJM) - 5 perguntas
    # =========================================================================
    {
        "id": "SLT1",
        "category": "SLT - Definição",
        "question": "O que caracteriza a síndrome de lise tumoral?",
        "expected_topics": ["hiperuricemia", "hipercalemia", "hiperfosfatemia", "hipocalcemia", "quimioterapia"],
        "difficulty": "Fácil",
        "document": "Síndrome de Lise Tumoral"
    },
    {
        "id": "SLT2",
        "category": "SLT - Fisiopatologia",
        "question": "Qual o mecanismo fisiopatológico da hipocalcemia na síndrome de lise tumoral?",
        "expected_topics": ["hiperfosfatemia", "precipitação", "cálcio-fosfato", "quelação"],
        "difficulty": "Médio",
        "document": "Síndrome de Lise Tumoral"
    },
    {
        "id": "SLT3",
        "category": "SLT - Prevenção",
        "question": "Como prevenir síndrome de lise tumoral em pacientes de alto risco?",
        "expected_topics": ["hidratação", "alopurinol", "rasburicase", "monitorização"],
        "difficulty": "Médio",
        "document": "Síndrome de Lise Tumoral"
    },
    {
        "id": "SLT4",
        "category": "SLT - Complicações",
        "question": "Qual a complicação mais grave da síndrome de lise tumoral e como preveni-la?",
        "expected_topics": ["insuficiência renal aguda", "precipitação", "hidratação", "diurese"],
        "difficulty": "Médio",
        "document": "Síndrome de Lise Tumoral"
    },
    {
        "id": "SLT5",
        "category": "SLT - Tratamento Específico",
        "question": "Quando usar rasburicase em vez de alopurinol na síndrome de lise tumoral?",
        "expected_topics": ["alto risco", "hiperuricemia grave", "deficiência G6PD", "contraindicação"],
        "difficulty": "Difícil",
        "document": "Síndrome de Lise Tumoral"
    },

    # =========================================================================
    # CATEGORIA 5: PROSTATITE (JAMA) - 4 perguntas
    # =========================================================================
    {
        "id": "PROST1",
        "category": "Prostatite - Classificação",
        "question": "Quais os tipos de prostatite segundo a classificação NIH?",
        "expected_topics": ["tipo I", "tipo II", "tipo III", "tipo IV", "aguda", "crônica"],
        "difficulty": "Fácil",
        "document": "Prostatite"
    },
    {
        "id": "PROST2",
        "category": "Prostatite - Diagnóstico",
        "question": "Como diferenciar prostatite bacteriana de síndrome de dor pélvica crônica?",
        "expected_topics": ["cultura", "leucócitos", "EPS", "VB3", "Meares-Stamey"],
        "difficulty": "Médio",
        "document": "Prostatite"
    },
    {
        "id": "PROST3",
        "category": "Prostatite - Tratamento",
        "question": "Qual o tratamento de escolha para prostatite bacteriana aguda?",
        "expected_topics": ["fluoroquinolona", "trimetoprim-sulfametoxazol", "4-6 semanas"],
        "difficulty": "Médio",
        "document": "Prostatite"
    },
    {
        "id": "PROST4",
        "category": "Prostatite - Crônica",
        "question": "Por que a prostatite crônica é difícil de tratar e qual a duração recomendada de antibiótico?",
        "expected_topics": ["penetração prostática", "barreira hematoprostática", "6-12 semanas"],
        "difficulty": "Difícil",
        "document": "Prostatite"
    },

    # =========================================================================
    # CATEGORIA 6: QUERIES CROSS-DOCUMENT (Muito Difícil!) - 2 perguntas
    # =========================================================================
    {
        "id": "CROSS1",
        "category": "Cross-Document - Comparação",
        "question": "Quais condições médicas nos documentos estão associadas a risco de insuficiência renal aguda?",
        "expected_topics": ["síndrome de lise tumoral", "nefrite lúpica", "diabetes com TFG baixa"],
        "difficulty": "Muito Difícil",
        "document": "Múltiplos"
    },
    {
        "id": "CROSS2",
        "category": "Cross-Document - Síntese",
        "question": "Compare as estratégias de monitoramento de risco entre diabetes (risco cardiovascular) e MGUS (risco de progressão para mieloma)?",
        "expected_topics": ["estratificação", "seguimento", "fatores de risco", "periodicidade"],
        "difficulty": "Muito Difícil",
        "document": "Múltiplos"
    },
]

# ==============================================================================
# FUNÇÕES DE TESTE
# ==============================================================================

def query_api(question: str, api_url: str = API_URL) -> Dict:
    """Faz query na API e retorna resultado"""
    try:
        response = requests.post(
            api_url,
            json={"question": question},
            timeout=60
        )
        response.raise_for_status()
        return response.json()
    except Exception as e:
        return {"error": str(e), "answer": None}


def evaluate_answer(answer: str, expected_topics: List[str]) -> Dict:
    """
    Avalia resposta baseado em topics esperados
    Retorna score de 0-100 e topics encontrados
    """
    if not answer or "informação solicitada não está presente" in answer.lower():
        return {
            "score": 0,
            "found_topics": [],
            "missing_topics": expected_topics,
            "status": "❌ NÃO RESPONDEU"
        }

    answer_lower = answer.lower()
    found_topics = []
    missing_topics = []

    for topic in expected_topics:
        # Verificar se topic está presente (case insensitive)
        if topic.lower() in answer_lower:
            found_topics.append(topic)
        else:
            missing_topics.append(topic)

    # Score baseado em % de topics encontrados
    score = int((len(found_topics) / len(expected_topics)) * 100) if expected_topics else 0

    # Determinar status
    if score >= 80:
        status = "✅ EXCELENTE"
    elif score >= 60:
        status = "⚠️ BOM"
    elif score >= 40:
        status = "⚠️ PARCIAL"
    elif score > 0:
        status = "❌ INCOMPLETO"
    else:
        status = "❌ FALHOU"

    return {
        "score": score,
        "found_topics": found_topics,
        "missing_topics": missing_topics,
        "status": status
    }


def run_validation_suite(queries: List[Dict], api_url: str = API_URL):
    """Executa suite completa de validação"""

    print("=" * 80)
    print("🧪 INICIANDO SUITE DE VALIDAÇÃO - RAG MULTIMODAL")
    print("=" * 80)
    print(f"\n📅 Data/Hora: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"🌐 API URL: {api_url}")
    print(f"📊 Total de queries: {len(queries)}")
    print("\n" + "=" * 80 + "\n")

    results = []

    for i, test in enumerate(queries, 1):
        print(f"[{i}/{len(queries)}] {test['category']}")
        print(f"❓ {test['question']}")
        print(f"📄 Documento: {test['document']}")
        print(f"🎯 Dificuldade: {test['difficulty']}")

        # Fazer query
        start_time = time.time()
        response = query_api(test['question'], api_url)
        latency = time.time() - start_time

        # Avaliar resposta
        answer = response.get('answer', '')
        evaluation = evaluate_answer(answer, test['expected_topics'])

        # Armazenar resultado
        result = {
            **test,
            "answer": answer,
            "sources": response.get('sources', []),
            "chunks_used": response.get('chunks_used', 0),
            "latency": round(latency, 2),
            "evaluation": evaluation,
            "error": response.get('error')
        }
        results.append(result)

        # Mostrar resultado
        print(f"{evaluation['status']} (Score: {evaluation['score']}%)")
        print(f"⏱️  Latency: {latency:.2f}s")
        print(f"📚 Chunks: {result['chunks_used']}")

        if evaluation['found_topics']:
            print(f"✅ Topics encontrados: {', '.join(evaluation['found_topics'])}")
        if evaluation['missing_topics']:
            print(f"❌ Topics faltando: {', '.join(evaluation['missing_topics'])}")

        if answer:
            print(f"💬 Resposta (preview): {answer[:150]}...")
        else:
            print(f"💬 Resposta: [ERRO ou SEM RESPOSTA]")
        print(f"📖 Fontes: {', '.join(response.get('sources', []))}")
        print("\n" + "-" * 80 + "\n")

        # Pequena pausa entre queries
        time.sleep(0.5)

    # ===========================================================================
    # RELATÓRIO FINAL
    # ===========================================================================

    print("\n" + "=" * 80)
    print("📊 RELATÓRIO FINAL DE VALIDAÇÃO")
    print("=" * 80 + "\n")

    # Estatísticas gerais
    total_queries = len(results)
    avg_score = sum(r['evaluation']['score'] for r in results) / total_queries
    avg_latency = sum(r['latency'] for r in results) / total_queries

    # Contar por status
    excelente = len([r for r in results if r['evaluation']['status'] == "✅ EXCELENTE"])
    bom = len([r for r in results if r['evaluation']['status'] == "⚠️ BOM"])
    parcial = len([r for r in results if r['evaluation']['status'] == "⚠️ PARCIAL"])
    incompleto = len([r for r in results if r['evaluation']['status'] == "❌ INCOMPLETO"])
    falhou = len([r for r in results if r['evaluation']['status'] == "❌ FALHOU"])
    nao_respondeu = len([r for r in results if r['evaluation']['status'] == "❌ NÃO RESPONDEU"])

    print(f"📈 ACCURACY GERAL: {avg_score:.1f}%")
    print(f"⏱️  LATENCY MÉDIA: {avg_latency:.2f}s")
    print(f"\n📊 DISTRIBUIÇÃO DE RESULTADOS:")
    print(f"   ✅ EXCELENTE (80-100%):  {excelente:2d} ({excelente/total_queries*100:.1f}%)")
    print(f"   ⚠️  BOM (60-79%):        {bom:2d} ({bom/total_queries*100:.1f}%)")
    print(f"   ⚠️  PARCIAL (40-59%):    {parcial:2d} ({parcial/total_queries*100:.1f}%)")
    print(f"   ❌ INCOMPLETO (1-39%):   {incompleto:2d} ({incompleto/total_queries*100:.1f}%)")
    print(f"   ❌ FALHOU (0%):          {falhou:2d} ({falhou/total_queries*100:.1f}%)")
    print(f"   ❌ NÃO RESPONDEU:        {nao_respondeu:2d} ({nao_respondeu/total_queries*100:.1f}%)")

    # Por categoria
    print(f"\n📚 PERFORMANCE POR CATEGORIA:")
    categories = {}
    for r in results:
        cat = r['category'].split(' - ')[0]  # Ex: "Diabetes" de "Diabetes - Retrieval"
        if cat not in categories:
            categories[cat] = []
        categories[cat].append(r['evaluation']['score'])

    for cat, scores in sorted(categories.items()):
        avg = sum(scores) / len(scores)
        print(f"   {cat:20s}: {avg:5.1f}% ({len(scores)} queries)")

    # Por dificuldade
    print(f"\n🎯 PERFORMANCE POR DIFICULDADE:")
    difficulties = {}
    for r in results:
        diff = r['difficulty']
        if diff not in difficulties:
            difficulties[diff] = []
        difficulties[diff].append(r['evaluation']['score'])

    for diff in ["Fácil", "Médio", "Difícil", "Muito Difícil"]:
        if diff in difficulties:
            scores = difficulties[diff]
            avg = sum(scores) / len(scores)
            print(f"   {diff:15s}: {avg:5.1f}% ({len(scores)} queries)")

    # Top 5 melhores
    print(f"\n🏆 TOP 5 MELHORES RESPOSTAS:")
    top_results = sorted(results, key=lambda x: x['evaluation']['score'], reverse=True)[:5]
    for i, r in enumerate(top_results, 1):
        print(f"   {i}. [{r['id']}] {r['question'][:60]}... ({r['evaluation']['score']}%)")

    # Top 5 piores
    print(f"\n⚠️  TOP 5 PIORES RESPOSTAS:")
    worst_results = sorted(results, key=lambda x: x['evaluation']['score'])[:5]
    for i, r in enumerate(worst_results, 1):
        print(f"   {i}. [{r['id']}] {r['question'][:60]}... ({r['evaluation']['score']}%)")

    # Salvar resultados em JSON
    output_file = f"validation_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump({
            "summary": {
                "total_queries": total_queries,
                "avg_score": round(avg_score, 2),
                "avg_latency": round(avg_latency, 2),
                "distribution": {
                    "excelente": excelente,
                    "bom": bom,
                    "parcial": parcial,
                    "incompleto": incompleto,
                    "falhou": falhou,
                    "nao_respondeu": nao_respondeu
                },
                "by_category": {cat: round(sum(scores)/len(scores), 2) for cat, scores in categories.items()},
                "by_difficulty": {diff: round(sum(scores)/len(scores), 2) for diff, scores in difficulties.items()}
            },
            "results": results
        }, f, ensure_ascii=False, indent=2)

    print(f"\n💾 Resultados salvos em: {output_file}")
    print("\n" + "=" * 80)

    # Interpretação final
    print("\n🎯 INTERPRETAÇÃO:")
    if avg_score >= 85:
        print("   ✅ EXCELENTE! Sistema production-ready com alta precisão.")
    elif avg_score >= 75:
        print("   ⚠️  BOM! Sistema funcional, mas pode melhorar com Contextual Retrieval.")
    elif avg_score >= 65:
        print("   ⚠️  ACEITÁVEL! Considere implementar HyDE e Contextual Retrieval.")
    else:
        print("   ❌ NECESSITA MELHORIAS! Priorize Contextual Retrieval urgentemente.")

    print("\n" + "=" * 80 + "\n")

    return results


# ==============================================================================
# MAIN
# ==============================================================================

if __name__ == "__main__":
    import sys

    # Permitir passar URL via argumento
    api_url = sys.argv[1] if len(sys.argv) > 1 else API_URL

    print("\n🚀 Iniciando validação em 3 segundos...")
    time.sleep(3)

    results = run_validation_suite(TEST_QUERIES, api_url)

    print("\n✅ Validação concluída!")
    print(f"📊 Verifique o arquivo JSON gerado para detalhes completos.")
