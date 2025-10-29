# Gerenciamento de Dependências

Este documento explica como gerenciar atualizações de dependências neste projeto.

## 📌 Estratégia Atual

Usamos **versões compatíveis** que permitem atualizações de bugfix mas bloqueiam breaking changes:

```python
# ✅ CORRETO - Permite 1.0.x, bloqueia 2.0.0
chromadb>=1.0.21,<2.0.0

# ❌ EVITAR - Muito restritivo
chromadb==1.0.21

# ❌ NUNCA - Muito arriscado para produção
chromadb
```

### Vantagens desta Abordagem:

- ✅ Recebe **bugfixes e security patches** automaticamente
- ✅ **Bloqueia breaking changes** (major versions)
- ✅ Equilíbrio entre estabilidade e atualização
- ✅ Railway sempre instala versão compatível mais recente

## 🤖 Monitoramento Automático

### Opção 1: Dependabot (GitHub Native - Recomendado)

O Dependabot já está configurado em `.github/dependabot.yml` e vai:

1. ✅ Verificar atualizações **toda segunda-feira**
2. ✅ Criar **Pull Requests** automaticamente
3. ✅ Agrupar patches e minor updates
4. ✅ **Ignorar major versions** (você decide quando atualizar)

**Como ativar:**
1. Vá em `Settings` → `Security` → `Code security and analysis`
2. Ative `Dependabot alerts` e `Dependabot security updates`
3. Pronto! PRs serão criados automaticamente

### Opção 2: Renovate (Alternativa Mais Poderosa)

Configuração está em `renovate.json`. Para ativar:

1. Instale o [Renovate App](https://github.com/apps/renovate) no seu repositório
2. Renovate começará a criar PRs automaticamente

## 🔍 Verificação Manual

Use o script fornecido:

```bash
./check_updates.sh
```

Isso mostra quais pacotes têm atualizações disponíveis.

## 🚀 Como Atualizar Dependências

### 1. Atualizações Patch/Minor (Seguras)

```bash
# Ver o que está desatualizado
pip list --outdated

# Atualizar tudo dentro das restrições
pip install --upgrade -r requirements.txt

# Testar localmente
python consultar_com_rerank.py --api

# Se tudo funcionar, fazer commit
pip freeze > requirements.txt.new
# Revisar mudanças e atualizar requirements.txt
```

### 2. Atualizações Major (Breaking Changes)

**⚠️ CUIDADO:** Major versions podem quebrar o código!

**Processo:**

1. **Ler o CHANGELOG** do pacote
2. **Criar branch de teste:**
   ```bash
   git checkout -b update-chromadb-2.0
   ```

3. **Atualizar versão:**
   ```python
   # requirements.txt
   chromadb>=2.0.0,<3.0.0  # Nova major version
   ```

4. **Instalar e testar extensivamente:**
   ```bash
   pip install -r requirements.txt
   python test_queries.py
   python test_validation_suite.py
   ```

5. **Verificar documentação de migração:**
   - Mudanças de API
   - Breaking changes
   - Formato de dados

6. **Fazer merge apenas se tudo funcionar**

## 📊 Dependências Críticas

Preste atenção especial a estas dependências:

| Pacote | Impacto | Frequência de Breaking Changes |
|--------|---------|-------------------------------|
| `chromadb` | 🔴 ALTO | Médio (mudou formato 0.5→1.0) |
| `langchain-*` | 🔴 ALTO | Baixo (estável) |
| `unstructured` | 🟡 MÉDIO | Médio |
| `flask` | 🟢 BAIXO | Muito baixo |

## 🔐 Atualizações de Segurança

Atualizações de segurança devem ser aplicadas **imediatamente**:

1. Dependabot/Renovate criarão PR com label `security`
2. Revisar o CVE mencionado
3. Testar rapidamente
4. Fazer merge e deploy

## 📝 Checklist de Atualização

Antes de atualizar dependências:

- [ ] Ler CHANGELOG do pacote
- [ ] Verificar breaking changes
- [ ] Testar localmente
- [ ] Rodar suite de testes
- [ ] Verificar se Railway precisa de ações (ex: limpar volume)
- [ ] Atualizar documentação se necessário
- [ ] Fazer backup do volume do Railway (se aplicável)

## ⚠️ Casos Especiais

### ChromaDB

- **0.5.x → 1.0.x**: Formato de DB mudou, precisa limpar volume
- **1.0.x → 2.0.x**: Verificar se formato mudou novamente
- **Sempre testar com dados de produção** antes de fazer upgrade

### LangChain

- Verificar compatibilidade entre `langchain`, `langchain-core`, `langchain-community`
- Manter versões alinhadas (todas 0.3.x ou todas 0.4.x)

### Unstructured

- Pode afetar qualidade da extração de PDFs
- Sempre testar com PDFs reais após atualizar

## 🎯 Recomendação Final

1. **Use Dependabot** para monitoramento automático
2. **Aceite patches/minor** após teste rápido
3. **Avalie major versions** com muito cuidado
4. **Rode `./check_updates.sh`** mensalmente
5. **Mantenha registro** de por que certas versões foram fixadas

---

**Última atualização:** 2025-10-29
