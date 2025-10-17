#!/usr/bin/env python3
"""
Script de Teste de Stress para RAG System
Testa 48 perguntas progressivamente mais difíceis
"""

import requests
import json
import time
from datetime import datetime
from typing import Dict, List, Tuple
import sys

API_URL = "http://localhost:5001/query"
TIMEOUT = 30  # segundos

# Cores para terminal
class Colors:
    GREEN = '\033[92m'
    YELLOW = '\033[93m'
    RED = '\033[91m'
    BLUE = '\033[94m'
    BOLD = '\033[1m'
    END = '\033[0m'

# ========================================================================
# BANCO DE PERGUNTAS
# ========================================================================

PERGUNTAS = {
    "basicas": [
        "Qual o valor de TFG que define insuficiência renal crônica?",
        "Em qual porcentagem a metformina reduz o risco de IAM segundo o UKPDS?",
        "Qual o alvo de HbA1c recomendado pela diretriz?",
        "Liste todos os iSGLT2 mencionados no documento",
        "Quais são os critérios de muito alto risco cardiovascular?",
        "Enumere os efeitos adversos da metformina",
    ],
    "negacoes": [
        "Quando NÃO usar metformina?",
        "Quais medicamentos NÃO são recomendados em pacientes com TFG < 30?",
        "Em quais situações NÃO se deve fazer insulina como primeira linha?",
        "Existem casos onde HbA1c normal NÃO exclui o diagnóstico de diabetes?",
        "Há situações em que controle glicêmico rigoroso NÃO é recomendado?",
        "TFG acima de 60 NÃO garante ausência de risco cardiovascular. Verdadeiro ou falso?",
    ],
    "relacoes": [
        "Qual a relação entre HbA1c elevada e complicações microvasculares?",
        "Como a obesidade influencia a escolha do antidiabético?",
        "Qual a conexão entre TFG reduzida e dosagem de metformina?",
        "Compare a eficácia de iSGLT2 vs GLP-1 em pacientes com DRC",
        "Qual a diferença entre monoterapia e terapia dupla inicial?",
        "Compare os alvos de HbA1c para pacientes jovens vs idosos",
    ],
    "contextuais": [
        "Qual a sequência de escalonamento terapêutico se o paciente falha na monoterapia?",
        "Descreva o algoritmo de escolha do antidiabético em paciente com ICC",
        "Como ajustar a terapia se HbA1c permanecer > 7% após 3 meses?",
        "Paciente com DM2, obesidade e HbA1c 8,5%. Qual terapia inicial recomendada?",
        "Mulher com DM2, TFG 25 ml/min e DCV prévia. Posso usar metformina?",
        "Idoso frágil, HbA1c 9%, sem DCV. Qual meta glicêmica adequada?",
    ],
    "ambiguas": [
        "Quais os benefícios dos iSGLT2?",
        "Como tratar diabetes?",
        "O que diz sobre insulina?",
        "Qual a dose máxima de iSGLT2 em pacientes com TFG < 15?",
        "A metformina é recomendada em gestantes com DM2?",
        "HbA1c abaixo de 5% é o alvo ideal?",
    ],
    "armadilhas": [
        "Qual o custo médio do tratamento com iSGLT2 no Brasil?",
        "Quantos pacientes foram incluídos no estudo UKPDS?",
        "Qual a prevalência de DM2 no Brasil segundo a diretriz?",
        "Quais são os critérios da ADA para diagnóstico de diabetes?",
        "O que a diretriz europeia recomenda sobre metformina?",
        "Como a OMS define síndrome metabólica?",
    ],
    "extremas": [
        "Em um paciente de 65 anos, com DM2 há 10 anos, HbA1c 8,2%, IMC 32, TFG 45 ml/min, com histórico de IAM há 2 anos, atualmente em uso de metformina 2g/dia, qual seria a melhor opção de escalonamento terapêutico segundo a diretriz brasileira considerando o perfil de risco cardiovascular muito alto e a presença de doença renal crônica moderada?",
        "Quais são as contraindicações da metformina E dos iSGLT2 E quando cada um deve ser preferido?",
        "Liste os valores de TFG para cada estágio de DRC, as restrições medicamentosas correspondentes e os ajustes de dose necessários para metformina em cada caso.",
        "Qual a diferença entre clearance de creatinina e taxa de filtração glomerular estimada?",
        "O que é prontidão terapêutica e por que é importante no DM2?",
        "Explique a relação entre inércia clínica e controle glicêmico inadequado",
    ],
    "humanas": [
        "Meu paciente tá com açúcar de 8 e pouco na hemoglobina. O que faço?",
        "Posso dar metformina pra quem tem problema no rim?",
        "Qual remédio é melhor pra quem é gordo e tem diabetes?",
        "Sou diabético e minha HbA1c está em 7,5%. Preciso aumentar o remédio?",
        "Tenho um paciente com DM2 novo. Por onde começar o tratamento?",
        "Posso usar insulina logo de cara ou tem que tentar comprimido primeiro?",
    ],
}

# Smoke test: 10 perguntas críticas (uma de cada categoria + extras)
SMOKE_TEST = [
    ("basicas", 0),      # Q1: Valor TFG
    ("basicas", 3),      # Q4: Lista iSGLT2
    ("negacoes", 0),     # Q7: Quando NÃO metformina
    ("relacoes", 0),     # Q13: Relação HbA1c e complicações
    ("contextuais", 0),  # Q19: Escalonamento terapêutico
    ("contextuais", 3),  # Q22: Caso clínico obesidade
    ("ambiguas", 4),     # Q28: Metformina gestante (armadilha)
    ("armadilhas", 0),   # Q31: Custo iSGLT2 (não presente)
    ("humanas", 0),      # Q43: Linguagem coloquial
    ("negacoes", 3),     # Q10: Dupla negação HbA1c
]

# ========================================================================
# FUNÇÕES DE TESTE
# ========================================================================

def test_query(question: str, timeout: int = TIMEOUT) -> Tuple[bool, Dict]:
    """Testa uma query no endpoint"""
    try:
        response = requests.post(
            API_URL,
            json={"question": question},
            timeout=timeout
        )

        if response.status_code == 200:
            return True, response.json()
        else:
            return False, {"error": f"HTTP {response.status_code}", "detail": response.text}

    except requests.exceptions.ConnectionError:
        return False, {"error": "Servidor não está rodando"}
    except requests.exceptions.Timeout:
        return False, {"error": f"Timeout após {timeout}s"}
    except Exception as e:
        return False, {"error": str(e)}


def classify_response(question: str, response: Dict, category: str) -> Tuple[str, str]:
    """
    Classifica resposta como: sucesso_total, sucesso_parcial, falha, falha_critica
    Retorna: (status, justificativa)
    """
    answer = response.get("answer", "").lower()

    # Detectar "informação não presente"
    info_ausente = "informação" in answer and "não está presente" in answer

    # CATEGORIA: ARMADILHAS (deve SEMPRE dizer "não presente")
    if category == "armadilhas":
        if info_ausente:
            return "sucesso_total", "Corretamente identificou informação ausente"
        else:
            return "falha_critica", "🚨 ALUCINAÇÃO! Respondeu sobre informação não presente"

    # CATEGORIA: AMBÍGUAS (perguntas armadilha com premissa falsa)
    if category == "ambiguas" and any(word in question.lower() for word in ["gestante", "grávida", "abaixo de 5%", "tfg < 15"]):
        # Deve corrigir a premissa falsa
        if "não" in answer or "contraindicad" in answer:
            return "sucesso_total", "Corrigiu premissa falsa da pergunta"
        else:
            return "falha_critica", "🚨 Não corrigiu premissa falsa!"

    # OUTRAS CATEGORIAS: deve ter resposta substantiva
    if info_ausente:
        return "falha", "Disse que informação não está presente (pode estar nos docs)"

    if len(answer) < 50:
        return "sucesso_parcial", "Resposta muito curta"

    if "sources" in response and len(response["sources"]) > 0:
        return "sucesso_total", "Resposta substantiva com fontes"

    return "sucesso_parcial", "Resposta sem fontes citadas"


def print_result(qnum: int, category: str, question: str, status: str, justificativa: str, response: Dict):
    """Imprime resultado formatado"""

    # Cores por status
    status_colors = {
        "sucesso_total": Colors.GREEN,
        "sucesso_parcial": Colors.YELLOW,
        "falha": Colors.RED,
        "falha_critica": Colors.RED + Colors.BOLD,
    }

    status_symbols = {
        "sucesso_total": "✅",
        "sucesso_parcial": "⚠️",
        "falha": "❌",
        "falha_critica": "🚨",
    }

    color = status_colors.get(status, Colors.END)
    symbol = status_symbols.get(status, "?")

    print(f"\n{color}{symbol} Q{qnum} [{category}]{Colors.END}")
    print(f"   Pergunta: {question[:80]}...")
    print(f"   Status: {color}{status.upper()}{Colors.END} - {justificativa}")

    if "answer" in response:
        answer_preview = response["answer"][:150].replace("\n", " ")
        print(f"   Resposta: {answer_preview}...")

    if "error" in response:
        print(f"   {Colors.RED}Erro: {response['error']}{Colors.END}")


def run_smoke_test():
    """Executa smoke test (10 perguntas críticas)"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}")
    print("🧪 SMOKE TEST - 10 perguntas críticas")
    print(f"{'='*70}{Colors.END}\n")

    results = {"sucesso_total": 0, "sucesso_parcial": 0, "falha": 0, "falha_critica": 0}
    details = []

    for idx, (cat, q_idx) in enumerate(SMOKE_TEST, 1):
        question = PERGUNTAS[cat][q_idx]

        print(f"Testando Q{idx}/{len(SMOKE_TEST)}...", end="", flush=True)
        success, response = test_query(question)
        print(" OK" if success else " ERRO")

        if success:
            status, justificativa = classify_response(question, response, cat)
            results[status] += 1
        else:
            status = "falha"
            justificativa = response.get("error", "Erro desconhecido")
            results["falha"] += 1

        print_result(idx, cat, question, status, justificativa, response)
        details.append({
            "qnum": idx,
            "category": cat,
            "question": question,
            "status": status,
            "response": response
        })

        time.sleep(0.5)  # Rate limiting

    # Resumo
    total = len(SMOKE_TEST)
    success_rate = ((results["sucesso_total"] + results["sucesso_parcial"]) / total) * 100

    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}")
    print("📊 RESUMO DO SMOKE TEST")
    print(f"{'='*70}{Colors.END}")
    print(f"  ✅ Sucesso Total:   {results['sucesso_total']}/{total}")
    print(f"  ⚠️  Sucesso Parcial: {results['sucesso_parcial']}/{total}")
    print(f"  ❌ Falhas:          {results['falha']}/{total}")
    print(f"  🚨 Falhas Críticas: {results['falha_critica']}/{total}")
    print(f"\n  {Colors.BOLD}Taxa de Sucesso: {success_rate:.1f}%{Colors.END}")

    if results["falha_critica"] > 0:
        print(f"\n  {Colors.RED}{Colors.BOLD}⚠️  ATENÇÃO: {results['falha_critica']} falha(s) crítica(s) detectada(s)!{Colors.END}")

    # Meta: 8/10 (80%)
    if success_rate >= 80:
        print(f"\n  {Colors.GREEN}🎉 META ATINGIDA! (≥80%){Colors.END}")
    else:
        print(f"\n  {Colors.YELLOW}⚠️  Abaixo da meta de 80%{Colors.END}")

    return details, results


def run_full_test():
    """Executa teste completo (todas as 48 perguntas)"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}")
    print("🔬 TESTE COMPLETO - 48 perguntas")
    print(f"{'='*70}{Colors.END}\n")

    all_results = {}
    all_details = []
    qnum = 1

    for category, questions in PERGUNTAS.items():
        print(f"\n{Colors.BOLD}📁 Categoria: {category.upper()}{Colors.END}")
        cat_results = {"sucesso_total": 0, "sucesso_parcial": 0, "falha": 0, "falha_critica": 0}

        for question in questions:
            print(f"  Testando Q{qnum}...", end="", flush=True)
            success, response = test_query(question)
            print(" OK" if success else " ERRO")

            if success:
                status, justificativa = classify_response(question, response, category)
                cat_results[status] += 1
            else:
                status = "falha"
                justificativa = response.get("error", "Erro desconhecido")
                cat_results["falha"] += 1

            print_result(qnum, category, question, status, justificativa, response)
            all_details.append({
                "qnum": qnum,
                "category": category,
                "question": question,
                "status": status,
                "response": response
            })

            qnum += 1
            time.sleep(0.5)

        # Resumo da categoria
        total = len(questions)
        success = cat_results["sucesso_total"] + cat_results["sucesso_parcial"]
        rate = (success / total) * 100
        print(f"\n  Categoria {category}: {success}/{total} ({rate:.1f}%)")

        all_results[category] = cat_results

    # Resumo geral
    print_full_summary(all_results, all_details)

    return all_details, all_results


def print_full_summary(results: Dict, details: List):
    """Imprime resumo completo"""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'='*70}")
    print("📊 RESUMO GERAL")
    print(f"{'='*70}{Colors.END}\n")

    # Tabela por categoria
    print(f"{'Categoria':<15} {'✅ Total':<10} {'⚠️ Parcial':<10} {'❌ Falha':<10} {'Taxa':<10}")
    print("-" * 70)

    total_success_total = 0
    total_success_parcial = 0
    total_falha = 0
    total_falha_critica = 0
    total_questions = 0

    for cat, res in results.items():
        total = sum(res.values())
        success = res["sucesso_total"] + res["sucesso_parcial"]
        rate = (success / total) * 100 if total > 0 else 0

        total_success_total += res["sucesso_total"]
        total_success_parcial += res["sucesso_parcial"]
        total_falha += res["falha"]
        total_falha_critica += res["falha_critica"]
        total_questions += total

        print(f"{cat:<15} {res['sucesso_total']:<10} {res['sucesso_parcial']:<10} {res['falha'] + res['falha_critica']:<10} {rate:.1f}%")

    print("-" * 70)
    total_rate = ((total_success_total + total_success_parcial) / total_questions) * 100 if total_questions > 0 else 0
    print(f"{'TOTAL':<15} {total_success_total:<10} {total_success_parcial:<10} {total_falha + total_falha_critica:<10} {Colors.BOLD}{total_rate:.1f}%{Colors.END}")

    # Meta geral: ≥73%
    print(f"\n{Colors.BOLD}Meta Geral: ≥73%{Colors.END}")
    if total_rate >= 73:
        print(f"{Colors.GREEN}✅ META ATINGIDA!{Colors.END}")
    else:
        print(f"{Colors.YELLOW}⚠️  Abaixo da meta{Colors.END}")

    # Falhas críticas
    if total_falha_critica > 0:
        print(f"\n{Colors.RED}{Colors.BOLD}🚨 {total_falha_critica} FALHA(S) CRÍTICA(S):{Colors.END}")
        for d in details:
            if d["status"] == "falha_critica":
                print(f"  - Q{d['qnum']}: {d['question'][:60]}...")


def save_results(details: List, results: Dict, filename: str):
    """Salva resultados em JSON"""
    output = {
        "timestamp": datetime.now().isoformat(),
        "summary": results,
        "details": details
    }

    with open(filename, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)

    print(f"\n💾 Resultados salvos em: {filename}")


# ========================================================================
# MAIN
# ========================================================================

def main():
    # Verificar se servidor está online
    print(f"{Colors.BOLD}🔍 Verificando servidor...{Colors.END}")
    success, response = test_query("teste")

    if not success:
        print(f"{Colors.RED}❌ Servidor não está rodando em {API_URL}{Colors.END}")
        print(f"\nInicie o servidor primeiro:")
        print(f"  python consultar_com_rerank.py --api")
        sys.exit(1)

    print(f"{Colors.GREEN}✅ Servidor online{Colors.END}")

    # Menu
    print(f"\n{Colors.BOLD}Escolha o tipo de teste:{Colors.END}")
    print("  1. Smoke Test (10 perguntas - 5 min)")
    print("  2. Teste Completo (48 perguntas - 30 min)")
    print("  3. Apenas perguntas originais (6 perguntas)")

    choice = input("\nOpção (1/2/3): ").strip()

    if choice == "1":
        details, results = run_smoke_test()
        filename = f"smoke_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    elif choice == "2":
        details, results = run_full_test()
        filename = f"full_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    elif choice == "3":
        # Perguntas originais que falharam
        original = [
            "Qual a relação entre albuminúria e risco cardiovascular segundo a diretriz brasileira de diabetes 2025?",
            "Quais são as contraindicações absolutas e relativas da metformina mencionadas no documento?",
            "Em quais situações a diretriz recomenda NÃO usar insulina como primeira linha no DM2?",
            "Existem situações onde glicose em jejum normal NÃO descarta diabetes?",
            "Qual o valor EXATO de TFG que define risco cardiovascular muito alto segundo a diretriz?",
            "Liste TODOS os valores de HbA1c mencionados no documento e seus respectivos contextos de uso",
        ]

        print(f"\n{Colors.BOLD}🔄 Testando perguntas originais...{Colors.END}\n")
        details = []
        results = {"sucesso_total": 0, "sucesso_parcial": 0, "falha": 0, "falha_critica": 0}

        for idx, question in enumerate(original, 1):
            print(f"Q{idx}...", end="", flush=True)
            success, response = test_query(question)
            print(" OK" if success else " ERRO")

            status, justificativa = classify_response(question, response, "relacoes")
            results[status] += 1

            print_result(idx, "original", question, status, justificativa, response)
            details.append({"qnum": idx, "question": question, "status": status, "response": response})
            time.sleep(0.5)

        # Meta: 5-6/6
        success_count = results["sucesso_total"] + results["sucesso_parcial"]
        print(f"\n{Colors.BOLD}Resultado: {success_count}/6 ({success_count/6*100:.1f}%){Colors.END}")

        if success_count >= 5:
            print(f"{Colors.GREEN}✅ META ATINGIDA (≥5/6)!{Colors.END}")
        else:
            print(f"{Colors.YELLOW}⚠️  Abaixo da meta de 5/6{Colors.END}")

        filename = f"original_test_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    else:
        print("Opção inválida")
        sys.exit(1)

    # Salvar resultados
    save_results(details, results, filename)

    print(f"\n{Colors.BOLD}✅ Teste concluído!{Colors.END}\n")


if __name__ == "__main__":
    main()
