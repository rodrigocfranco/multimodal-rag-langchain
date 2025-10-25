#!/usr/bin/env python3
"""
Suite de Testes Automatizados - Multimodal RAG
Testa qualidade de retrieval, imagens e tabelas
"""

import requests
import json
import time
from datetime import datetime

# Configuração
BASE_URL = "https://comfortable-tenderness-production.up.railway.app"
TIMEOUT = 60  # 60 segundos por query

# Cores para output
class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name):
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BLUE}TEST: {name}{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}")

def print_success(msg):
    print(f"{Colors.GREEN}✓ {msg}{Colors.END}")

def print_error(msg):
    print(f"{Colors.RED}✗ {msg}{Colors.END}")

def print_warning(msg):
    print(f"{Colors.YELLOW}⚠ {msg}{Colors.END}")

def query_chat(question):
    """Faz query no endpoint /query"""
    url = f"{BASE_URL}/query"

    try:
        start_time = time.time()
        response = requests.post(
            url,
            json={"question": question},
            timeout=TIMEOUT
        )
        elapsed = time.time() - start_time

        if response.status_code == 200:
            data = response.json()
            return {
                "success": True,
                "answer": data.get("answer", ""),
                "images": data.get("images", []),
                "has_images": data.get("has_images", False),
                "num_images": data.get("num_images", 0),
                "elapsed": elapsed
            }
        else:
            return {
                "success": False,
                "error": f"Status {response.status_code}: {response.text[:200]}",
                "elapsed": elapsed
            }
    except requests.Timeout:
        return {
            "success": False,
            "error": f"Timeout após {TIMEOUT}s",
            "elapsed": TIMEOUT
        }
    except Exception as e:
        return {
            "success": False,
            "error": str(e),
            "elapsed": time.time() - start_time
        }

# ============================================================================
# SUITE DE TESTES
# ============================================================================

def test_text_retrieval():
    """Teste 1: Retrieval de informações textuais"""
    print_test("Retrieval de Textos")

    queries = [
        {
            "q": "Quais os critérios diagnósticos laboratoriais da síndrome de lise tumoral?",
            "expected_keywords": ["ácido úrico", "potássio", "fósforo", "cálcio"]
        },
        {
            "q": "Qual a dose de rasburicase recomendada?",
            "expected_keywords": ["mg/kg", "dose"]
        },
        {
            "q": "Quando a hemodiálise é indicada na síndrome de lise tumoral?",
            "expected_keywords": ["hemodiálise", "indicação"]
        }
    ]

    results = []
    for i, test in enumerate(queries, 1):
        print(f"\n  Query {i}: {test['q'][:60]}...")
        result = query_chat(test['q'])

        if result["success"]:
            answer = result["answer"].lower()

            # Verificar keywords esperadas
            found_keywords = [kw for kw in test["expected_keywords"] if kw.lower() in answer]

            if len(found_keywords) >= len(test["expected_keywords"]) // 2:
                print_success(f"Encontrou {len(found_keywords)}/{len(test['expected_keywords'])} keywords esperadas")
                print_success(f"Tempo: {result['elapsed']:.2f}s")
                results.append("PASS")
            else:
                print_warning(f"Apenas {len(found_keywords)}/{len(test['expected_keywords'])} keywords encontradas")
                print(f"    Esperava: {test['expected_keywords']}")
                print(f"    Encontrou: {found_keywords}")
                results.append("PARTIAL")
        else:
            print_error(f"Erro: {result['error']}")
            results.append("FAIL")

    # Resumo
    print(f"\n  Resumo: {results.count('PASS')}/{len(queries)} queries passaram")
    return results

def test_image_retrieval():
    """Teste 2: Retrieval de imagens"""
    print_test("Retrieval de Imagens")

    queries = [
        {
            "q": "Explique a fisiopatologia da síndrome de lise tumoral",
            "expect_images": True
        },
        {
            "q": "Mostre o diagrama do metabolismo do ácido úrico",
            "expect_images": True
        },
        {
            "q": "Como funciona o mecanismo da síndrome de lise tumoral?",
            "expect_images": True
        }
    ]

    results = []
    for i, test in enumerate(queries, 1):
        print(f"\n  Query {i}: {test['q'][:60]}...")
        result = query_chat(test['q'])

        if result["success"]:
            has_images = result["has_images"]
            num_images = result["num_images"]

            if test["expect_images"]:
                if has_images and num_images > 0:
                    print_success(f"Retornou {num_images} imagem(ns)")
                    print_success(f"Tempo: {result['elapsed']:.2f}s")
                    results.append("PASS")
                else:
                    print_error(f"Esperava imagens mas retornou {num_images}")
                    results.append("FAIL")
            else:
                if not has_images:
                    print_success("Corretamente não retornou imagens")
                    results.append("PASS")
                else:
                    print_warning(f"Retornou {num_images} imagem(ns) inesperada(s)")
                    results.append("PARTIAL")
        else:
            print_error(f"Erro: {result['error']}")
            results.append("FAIL")

    # Resumo
    print(f"\n  Resumo: {results.count('PASS')}/{len(queries)} queries passaram")
    return results

def test_table_retrieval():
    """Teste 3: Retrieval de dados de tabelas"""
    print_test("Retrieval de Tabelas")

    queries = [
        {
            "q": "Quais os valores de referência para ácido úrico?",
            "expected_keywords": ["ácido úrico", "mg/dL"]
        },
        {
            "q": "Liste os critérios de Cairo-Bishop",
            "expected_keywords": ["cairo", "bishop", "critério"]
        }
    ]

    results = []
    for i, test in enumerate(queries, 1):
        print(f"\n  Query {i}: {test['q'][:60]}...")
        result = query_chat(test['q'])

        if result["success"]:
            answer = result["answer"].lower()

            # Verificar keywords esperadas
            found_keywords = [kw for kw in test["expected_keywords"] if kw.lower() in answer]

            if len(found_keywords) >= len(test["expected_keywords"]) // 2:
                print_success(f"Encontrou {len(found_keywords)}/{len(test['expected_keywords'])} keywords esperadas")
                print_success(f"Tempo: {result['elapsed']:.2f}s")
                results.append("PASS")
            else:
                print_warning(f"Apenas {len(found_keywords)}/{len(test['expected_keywords'])} keywords encontradas")
                results.append("PARTIAL")
        else:
            print_error(f"Erro: {result['error']}")
            results.append("FAIL")

    # Resumo
    print(f"\n  Resumo: {results.count('PASS')}/{len(queries)} queries passaram")
    return results

def test_edge_cases():
    """Teste 4: Edge cases e correção de premissas"""
    print_test("Edge Cases")

    queries = [
        {
            "q": "Qual o tratamento para diabetes tipo 2?",
            "expected_behavior": "OUT_OF_SCOPE",
            "expected_keywords": ["não está presente", "não consta", "não foi encontrada"]
        },
        {
            "q": "O que causa a síndrome?",
            "expected_behavior": "CLARIFICATION",
            "expected_keywords": ["lise tumoral", "tratamento"]
        }
    ]

    results = []
    for i, test in enumerate(queries, 1):
        print(f"\n  Query {i}: {test['q'][:60]}...")
        result = query_chat(test['q'])

        if result["success"]:
            answer = result["answer"].lower()

            if test["expected_behavior"] == "OUT_OF_SCOPE":
                # Deve dizer que não encontrou
                if any(kw in answer for kw in test["expected_keywords"]):
                    print_success("Corretamente indicou que informação não está disponível")
                    results.append("PASS")
                else:
                    print_warning("Respondeu mas deveria dizer que não tem a informação")
                    results.append("PARTIAL")
            elif test["expected_behavior"] == "CLARIFICATION":
                # Deve responder sobre lise tumoral
                if any(kw in answer for kw in test["expected_keywords"]):
                    print_success("Respondeu sobre síndrome de lise tumoral")
                    results.append("PASS")
                else:
                    print_warning("Resposta não menciona lise tumoral")
                    results.append("PARTIAL")
        else:
            print_error(f"Erro: {result['error']}")
            results.append("FAIL")

    # Resumo
    print(f"\n  Resumo: {results.count('PASS')}/{len(queries)} queries passaram")
    return results

def test_performance():
    """Teste 5: Performance e latência"""
    print_test("Performance")

    query = "Quais os critérios diagnósticos da síndrome de lise tumoral?"

    print(f"\n  Query: {query}")
    print(f"  Executando 3 vezes para medir latência...")

    times = []
    for i in range(3):
        result = query_chat(query)
        if result["success"]:
            times.append(result["elapsed"])
            print(f"    Tentativa {i+1}: {result['elapsed']:.2f}s")
        else:
            print_error(f"Tentativa {i+1} falhou: {result['error']}")

    if times:
        avg_time = sum(times) / len(times)
        min_time = min(times)
        max_time = max(times)

        print(f"\n  Latência Média: {avg_time:.2f}s")
        print(f"  Mín: {min_time:.2f}s | Máx: {max_time:.2f}s")

        if avg_time < 10:
            print_success("Performance excelente (<10s)")
            return ["PASS"]
        elif avg_time < 20:
            print_success("Performance boa (<20s)")
            return ["PASS"]
        else:
            print_warning(f"Performance aceitável ({avg_time:.2f}s)")
            return ["PARTIAL"]
    else:
        print_error("Nenhuma query bem sucedida")
        return ["FAIL"]

# ============================================================================
# MAIN
# ============================================================================

def main():
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BLUE}SUITE DE TESTES AUTOMATIZADOS - Multimodal RAG{Colors.END}")
    print(f"{Colors.BLUE}Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}{Colors.END}")
    print(f"{Colors.BLUE}Endpoint: {BASE_URL}{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}")

    all_results = []

    # Rodar todos os testes
    all_results.extend(test_text_retrieval())
    all_results.extend(test_image_retrieval())
    all_results.extend(test_table_retrieval())
    all_results.extend(test_edge_cases())
    all_results.extend(test_performance())

    # Resumo final
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BLUE}RESUMO FINAL{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}")

    total = len(all_results)
    passed = all_results.count("PASS")
    partial = all_results.count("PARTIAL")
    failed = all_results.count("FAIL")

    print(f"\n  Total de testes: {total}")
    print_success(f"Passou: {passed} ({100*passed//total if total > 0 else 0}%)")
    print_warning(f"Parcial: {partial} ({100*partial//total if total > 0 else 0}%)")
    print_error(f"Falhou: {failed} ({100*failed//total if total > 0 else 0}%)")

    # Score final
    score = (passed + 0.5 * partial) / total * 100 if total > 0 else 0
    print(f"\n  {Colors.BLUE}Score Final: {score:.1f}%{Colors.END}")

    if score >= 80:
        print_success("\n  Sistema funcionando MUITO BEM! 🎉")
    elif score >= 60:
        print_success("\n  Sistema funcionando BEM ✓")
    elif score >= 40:
        print_warning("\n  Sistema precisa de melhorias ⚠️")
    else:
        print_error("\n  Sistema precisa de ajustes significativos ✗")

    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}\n")

if __name__ == "__main__":
    main()
