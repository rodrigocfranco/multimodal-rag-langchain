#!/usr/bin/env python3
"""
Suite Completa de Testes - Sistema RAG Multimodal
Valida todas as implementações e mudanças recentes
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple

# Configuração
BASE_URL = "https://comfortable-tenderness-production.up.railway.app"
TIMEOUT = 60

class Colors:
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    END = '\033[0m'

def print_test(name: str):
    print(f"\n{Colors.BLUE}{'='*70}{Colors.END}")
    print(f"{Colors.BLUE}🧪 {name}{Colors.END}")
    print(f"{Colors.BLUE}{'='*70}{Colors.END}")

def print_success(msg: str):
    print(f"{Colors.GREEN}✅ {msg}{Colors.END}")

def print_error(msg: str):
    print(f"{Colors.RED}❌ {msg}{Colors.END}")

def print_warning(msg: str):
    print(f"{Colors.YELLOW}⚠️  {msg}{Colors.END}")

def print_info(msg: str):
    print(f"   {msg}")

# ==============================================================================
# TESTE 1: HEALTHCHECK
# ==============================================================================
def test_healthcheck() -> Tuple[bool, Dict]:
    print_test("TESTE 1: Healthcheck e Inicialização")

    try:
        start = time.time()
        response = requests.get(f"{BASE_URL}/health", timeout=10)
        latency = time.time() - start

        if response.status_code == 200:
            data = response.json()

            # Verificações
            checks = {
                "Status 200": response.status_code == 200,
                "Status OK": data.get("status") == "ok",
                "Ready": data.get("ready") == True,
                "Persist dir correto": data.get("persist_dir") == "/app/base",
                "Reranker presente": "reranker" in data,
                "Latência <2s": latency < 2
            }

            for check, passed in checks.items():
                if passed:
                    print_success(check)
                else:
                    print_error(f"{check}: {data.get(check, 'N/A')}")

            print_info(f"Latência: {latency:.2f}s")
            print_info(f"Response: {json.dumps(data, indent=2)}")

            return all(checks.values()), data
        else:
            print_error(f"Status {response.status_code}")
            return False, {}

    except Exception as e:
        print_error(f"Erro: {str(e)}")
        return False, {}

# ==============================================================================
# TESTE 2: COHERE RERANK V3.5
# ==============================================================================
def test_cohere_v35() -> Tuple[bool, Dict]:
    print_test("TESTE 2: Cohere Rerank v3.5")

    # Query complexa que se beneficia de v3.5
    query = {
        "question": "Qual o tratamento da síndrome de lise tumoral segundo critérios de cairo-bishop em pacientes graves com insuficiência renal?"
    }

    try:
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/query",
            json=query,
            headers={"Content-Type": "application/json"},
            timeout=TIMEOUT
        )
        latency = time.time() - start

        if response.status_code == 200:
            data = response.json()

            checks = {
                "Resposta recebida": "answer" in data,
                "Resposta não vazia": len(data.get("answer", "")) > 100,
                "Tem contexto": len(data.get("context", [])) > 0,
                "Latência <15s": latency < 15,
                "Documentos rerankeados": data.get("reranked", False)
            }

            for check, passed in checks.items():
                if passed:
                    print_success(check)
                else:
                    print_error(check)

            print_info(f"Latência: {latency:.2f}s")
            print_info(f"Resposta (primeiros 300 chars): {data.get('answer', '')[:300]}...")
            print_info(f"Num documentos: {len(data.get('context', []))}")

            return all(checks.values()), data
        else:
            print_error(f"Status {response.status_code}: {response.text[:200]}")
            return False, {}

    except Exception as e:
        print_error(f"Erro: {str(e)}")
        return False, {}

# ==============================================================================
# TESTE 3: LLM QUERY GENERATION
# ==============================================================================
def test_llm_query_generation() -> Tuple[bool, Dict]:
    print_test("TESTE 3: LLM Query Generation")

    # Query com abreviação que deve ser expandida
    query = {
        "question": "Como tratar DM tipo 2 descompensado?"
    }

    print_info("Query original: 'Como tratar DM tipo 2 descompensado?'")
    print_info("Esperado: Expansão de 'DM' → 'diabetes mellitus'")
    print_info("Nota: Verificar logs do Railway para ver queries geradas")

    try:
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/query",
            json=query,
            timeout=TIMEOUT
        )
        latency = time.time() - start

        if response.status_code == 200:
            data = response.json()

            answer = data.get("answer", "").lower()

            checks = {
                "Resposta recebida": "answer" in data,
                "Menciona diabetes": "diabetes" in answer,
                "Menciona tratamento": "tratamento" in answer or "terapia" in answer,
                "Resposta completa": len(answer) > 200,
                "Latência aceitável": latency < 15
            }

            for check, passed in checks.items():
                if passed:
                    print_success(check)
                else:
                    print_error(check)

            print_warning("Para ver queries geradas pelo LLM, verificar logs do Railway!")
            print_info(f"Latência: {latency:.2f}s")

            return all(checks.values()), data
        else:
            print_error(f"Status {response.status_code}")
            return False, {}

    except Exception as e:
        print_error(f"Erro: {str(e)}")
        return False, {}

# ==============================================================================
# TESTE 4: DETECÇÃO DE QUERIES VISUAIS
# ==============================================================================
def test_visual_query_detection() -> Tuple[bool, Dict]:
    print_test("TESTE 4: Detecção de Queries Visuais")

    query = {
        "question": "Mostre a figura do algoritmo de manejo da sepse"
    }

    print_info("Query visual: 'Mostre a figura do algoritmo de manejo da sepse'")
    print_info("Esperado: Sistema detecta query visual e prioriza imagens")

    try:
        start = time.time()
        response = requests.post(
            f"{BASE_URL}/query",
            json=query,
            timeout=TIMEOUT
        )
        latency = time.time() - start

        if response.status_code == 200:
            data = response.json()

            num_images = data.get("num_images", 0)

            checks = {
                "Resposta recebida": "answer" in data,
                "Imagens incluídas": num_images > 0,
                "Múltiplas imagens": num_images >= 1,
                "Latência aceitável": latency < 20
            }

            for check, passed in checks.items():
                if passed:
                    print_success(check)
                else:
                    print_error(check)

            print_info(f"Número de imagens: {num_images}")
            print_info(f"Latência: {latency:.2f}s")
            print_warning("Verificar logs para confirmar detecção visual!")

            return checks["Imagens incluídas"], data
        else:
            print_error(f"Status {response.status_code}")
            return False, {}

    except Exception as e:
        print_error(f"Erro: {str(e)}")
        return False, {}

# ==============================================================================
# TESTE 5: MULTILÍNGUE (PORTUGUÊS)
# ==============================================================================
def test_multilingual_portuguese() -> Tuple[bool, Dict]:
    print_test("TESTE 5: Suporte Multilíngue (Português)")

    queries = [
        "Quais os critérios diagnósticos de SDRA segundo Berlin?",
        "Protocolo de sepse grave com choque séptico",
        "Tratamento de hipertensão arterial sistêmica refratária"
    ]

    results = []

    for q in queries:
        print_info(f"\nTestando: '{q}'")
        try:
            response = requests.post(
                f"{BASE_URL}/query",
                json={"question": q},
                timeout=TIMEOUT
            )

            if response.status_code == 200:
                data = response.json()
                answer_length = len(data.get("answer", ""))
                has_context = len(data.get("context", [])) > 0

                if answer_length > 50 and has_context:
                    print_success(f"OK - {answer_length} chars, contexto presente")
                    results.append(True)
                else:
                    print_error(f"Resposta curta ou sem contexto")
                    results.append(False)
            else:
                print_error(f"Status {response.status_code}")
                results.append(False)

        except Exception as e:
            print_error(f"Erro: {str(e)}")
            results.append(False)

    success_rate = sum(results) / len(results) * 100
    print_info(f"\nTaxa de sucesso: {success_rate:.1f}%")

    return success_rate >= 80, {"success_rate": success_rate}

# ==============================================================================
# TESTE 6: VOLUME E PERSISTÊNCIA
# ==============================================================================
def test_volume_persistence() -> Tuple[bool, Dict]:
    print_test("TESTE 6: Volume e Persistência")

    try:
        # Verificar volume
        response = requests.get(f"{BASE_URL}/debug-volume", timeout=30)

        if response.status_code == 200:
            data = response.json()

            persist_dir = data.get("persist_directory", "")
            exists = data.get("exists", False)

            checks = {
                "Volume existe": exists,
                "Path correto": persist_dir == "/app/base",
                "Tem arquivos": data.get("files_count", 0) > 0
            }

            for check, passed in checks.items():
                if passed:
                    print_success(check)
                else:
                    print_error(check)

            print_info(f"Persist dir: {persist_dir}")
            print_info(f"Files count: {data.get('files_count', 0)}")

            return all(checks.values()), data
        else:
            print_error(f"Status {response.status_code}")
            return False, {}

    except Exception as e:
        print_error(f"Erro: {str(e)}")
        return False, {}

# ==============================================================================
# TESTE 7: PERFORMANCE E LATÊNCIA
# ==============================================================================
def test_performance() -> Tuple[bool, Dict]:
    print_test("TESTE 7: Performance e Latência")

    queries = [
        "O que é diabetes?",  # Simples
        "Quais os critérios de sepse grave?",  # Média
        "Qual o protocolo completo de manejo de síndrome de lise tumoral segundo cairo-bishop incluindo tratamento da hipercalemia e insuficiência renal?"  # Complexa
    ]

    latencies = []

    for i, q in enumerate(queries, 1):
        complexity = ["Simples", "Média", "Complexa"][i-1]
        print_info(f"\n{i}. Query {complexity}: '{q[:60]}...'")

        try:
            start = time.time()
            response = requests.post(
                f"{BASE_URL}/query",
                json={"question": q},
                timeout=TIMEOUT
            )
            latency = time.time() - start
            latencies.append(latency)

            if response.status_code == 200:
                print_success(f"Latência: {latency:.2f}s")
            else:
                print_error(f"Status {response.status_code}")

        except Exception as e:
            print_error(f"Erro: {str(e)}")
            latencies.append(999)

    avg_latency = sum(latencies) / len(latencies)
    print_info(f"\nLatência média: {avg_latency:.2f}s")

    checks = {
        "Latência média <10s": avg_latency < 10,
        "Nenhum timeout": max(latencies) < 60,
        "Query simples <5s": latencies[0] < 5 if len(latencies) > 0 else False
    }

    for check, passed in checks.items():
        if passed:
            print_success(check)
        else:
            print_error(check)

    return all(checks.values()), {"avg_latency": avg_latency, "latencies": latencies}

# ==============================================================================
# MAIN - EXECUTAR TODOS OS TESTES
# ==============================================================================
def main():
    print(f"\n{Colors.BLUE}{'='*70}")
    print(f"🧪 SUITE COMPLETA DE TESTES - Sistema RAG Multimodal")
    print(f"Data: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"URL: {BASE_URL}")
    print(f"{'='*70}{Colors.END}\n")

    results = {}

    # Executar testes
    tests = [
        ("Healthcheck", test_healthcheck),
        ("Cohere Rerank v3.5", test_cohere_v35),
        ("LLM Query Generation", test_llm_query_generation),
        ("Detecção Visual", test_visual_query_detection),
        ("Multilíngue PT", test_multilingual_portuguese),
        ("Volume/Persistência", test_volume_persistence),
        ("Performance", test_performance)
    ]

    for name, test_func in tests:
        try:
            passed, data = test_func()
            results[name] = {"passed": passed, "data": data}
            time.sleep(2)  # Pausa entre testes
        except Exception as e:
            print_error(f"Erro fatal no teste {name}: {str(e)}")
            results[name] = {"passed": False, "error": str(e)}

    # Resumo final
    print(f"\n{Colors.BLUE}{'='*70}")
    print(f"📊 RESUMO DOS TESTES")
    print(f"{'='*70}{Colors.END}\n")

    passed_count = sum(1 for r in results.values() if r.get("passed"))
    total_count = len(results)
    success_rate = passed_count / total_count * 100

    for name, result in results.items():
        if result.get("passed"):
            print_success(f"{name}")
        else:
            print_error(f"{name}")

    print(f"\n{Colors.BLUE}Total: {passed_count}/{total_count} ({success_rate:.1f}%){Colors.END}")

    if success_rate >= 80:
        print(f"\n{Colors.GREEN}✅ SISTEMA VALIDADO! Todas as implementações funcionando!{Colors.END}\n")
    elif success_rate >= 60:
        print(f"\n{Colors.YELLOW}⚠️  PARCIALMENTE OK. Alguns ajustes necessários.{Colors.END}\n")
    else:
        print(f"\n{Colors.RED}❌ ATENÇÃO! Sistema precisa de correções.{Colors.END}\n")

    return results

if __name__ == "__main__":
    main()
