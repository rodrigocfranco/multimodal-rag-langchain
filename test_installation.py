#!/usr/bin/env python3
"""
Script de teste rápido para verificar se todas as dependências estão instaladas.
"""

import sys

def test_imports():
    """Testa se todas as bibliotecas principais podem ser importadas."""
    
    print("=" * 80)
    print("🧪 TESTANDO INSTALAÇÃO - Multi-modal RAG com LangChain")
    print("=" * 80)
    print()
    
    tests = [
        ("Python", lambda: sys.version_info >= (3, 8), f"Python {sys.version}"),
        ("LangChain", lambda: __import__("langchain"), None),
        ("LangChain Community", lambda: __import__("langchain_community"), None),
        ("LangChain Core", lambda: __import__("langchain_core"), None),
        ("LangChain OpenAI", lambda: __import__("langchain_openai"), None),
        ("LangChain Groq", lambda: __import__("langchain_groq"), None),
        ("ChromaDB", lambda: __import__("chromadb"), None),
        ("Unstructured", lambda: __import__("unstructured"), None),
        ("OpenAI", lambda: __import__("openai"), None),
        ("Tiktoken", lambda: __import__("tiktoken"), None),
        ("Jupyter", lambda: __import__("jupyter"), None),
        ("Pillow", lambda: __import__("PIL"), None),
        ("lxml", lambda: __import__("lxml"), None),
        ("python-dotenv", lambda: __import__("dotenv"), None),
    ]
    
    passed = 0
    failed = 0
    
    for name, test, version_info in tests:
        try:
            result = test()
            if result is False:
                print(f"❌ {name}: FALHOU")
                failed += 1
            else:
                version = version_info if version_info else ""
                print(f"✅ {name}: OK {version}")
                passed += 1
        except Exception as e:
            print(f"❌ {name}: ERRO - {str(e)[:50]}")
            failed += 1
    
    print()
    print("=" * 80)
    print(f"RESULTADO: {passed} passaram, {failed} falharam")
    print("=" * 80)
    print()
    
    return failed == 0


def test_environment():
    """Testa se as variáveis de ambiente estão configuradas."""
    
    print("🔑 TESTANDO VARIÁVEIS DE AMBIENTE")
    print("-" * 80)
    
    import os
    from dotenv import load_dotenv
    
    load_dotenv()
    
    env_vars = [
        ("OPENAI_API_KEY", True),
        ("GROQ_API_KEY", True),
        ("LANGCHAIN_API_KEY", False),  # Opcional
    ]
    
    passed = 0
    failed = 0
    
    for var_name, required in env_vars:
        value = os.getenv(var_name)
        if value and value != "sk-...":
            masked = value[:8] + "..." + value[-4:] if len(value) > 12 else "***"
            print(f"✅ {var_name}: {masked}")
            passed += 1
        elif required:
            print(f"❌ {var_name}: NÃO CONFIGURADA (obrigatória)")
            failed += 1
        else:
            print(f"⚠️  {var_name}: Não configurada (opcional)")
    
    print()
    return failed == 0


def test_files():
    """Testa se os arquivos necessários existem."""
    
    print("📁 TESTANDO ARQUIVOS DO PROJETO")
    print("-" * 80)
    
    import os
    
    files = [
        (".env", True),
        ("requirements.txt", True),
        ("multimodal_rag.py", True),
        ("README.md", True),
        ("content/attention.pdf", True),
    ]
    
    passed = 0
    failed = 0
    
    for file_path, required in files:
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            size_str = f"{size / 1024:.1f} KB" if size > 1024 else f"{size} bytes"
            print(f"✅ {file_path}: {size_str}")
            passed += 1
        elif required:
            print(f"❌ {file_path}: NÃO ENCONTRADO")
            failed += 1
        else:
            print(f"⚠️  {file_path}: Não encontrado (opcional)")
    
    print()
    return failed == 0


def test_system_dependencies():
    """Testa se as dependências do sistema estão instaladas."""
    
    print("🔧 TESTANDO DEPENDÊNCIAS DO SISTEMA")
    print("-" * 80)
    
    import subprocess
    
    commands = [
        ("poppler", ["pdfinfo", "-v"]),
        ("tesseract", ["tesseract", "--version"]),
    ]
    
    passed = 0
    failed = 0
    
    for name, cmd in commands:
        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 or "version" in result.stdout.lower() or "version" in result.stderr.lower():
                version_line = (result.stdout + result.stderr).split('\n')[0]
                print(f"✅ {name}: {version_line[:60]}")
                passed += 1
            else:
                print(f"❌ {name}: Comando executou mas retornou erro")
                failed += 1
        except FileNotFoundError:
            print(f"❌ {name}: NÃO INSTALADO")
            failed += 1
        except Exception as e:
            print(f"❌ {name}: ERRO - {str(e)[:50]}")
            failed += 1
    
    print()
    return failed == 0


def main():
    """Executa todos os testes."""
    
    all_passed = True
    
    all_passed &= test_imports()
    all_passed &= test_environment()
    all_passed &= test_files()
    all_passed &= test_system_dependencies()
    
    print("=" * 80)
    if all_passed:
        print("✅ TODOS OS TESTES PASSARAM!")
        print("=" * 80)
        print()
        print("🚀 Você está pronto para executar o projeto!")
        print()
        print("Para começar:")
        print("  python multimodal_rag.py")
        print()
        return 0
    else:
        print("❌ ALGUNS TESTES FALHARAM")
        print("=" * 80)
        print()
        print("Por favor, revise os erros acima e corrija antes de prosseguir.")
        print("Consulte INSTALACAO_COMPLETA.md para mais detalhes.")
        print()
        return 1


if __name__ == "__main__":
    sys.exit(main())

