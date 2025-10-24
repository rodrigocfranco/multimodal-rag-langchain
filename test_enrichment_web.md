# 🧪 TESTES DE VALIDAÇÃO DO METADATA ENRICHMENT

Teste manualmente via web UI para validar que os metadados enriquecidos estão funcionando.

Data: 2025-10-22

---

## 📋 CHECKLIST DE TESTES

### ✅ TESTE 1: Verificar se documento foi processado com enrichment

1. Acesse: `https://comfortable-tenderness-production.up.railway.app/manage`
2. Encontre o documento: **"Hiperglicemia hospitalar no paciente crítico"**
3. Clique em **"Detalhes"**
4. Verifique:
   - [ ] Status: **processed**
   - [ ] Chunks: **16** (13 textos + 2 tabelas + 1 imagem)
   - [ ] Processado em: **2025-10-22**

**Resultado esperado:** ✅ Documento aparece com status "processed" e 16 chunks

---

### ✅ TESTE 2: Query simples - Baseline

1. Acesse: `https://comfortable-tenderness-production.up.railway.app/chat`
2. Faça a pergunta:
   ```
   Como tratar hiperglicemia hospitalar em pacientes críticos?
   ```
3. Aguarde a resposta

**Resultado esperado:**
- ✅ Resposta baseada na diretriz de diabetes de 2025
- ✅ Menciona protocolo de infusão de insulina
- ✅ Cita alvos glicêmicos específicos (140-180 mg/dL típico)

---

### ✅ TESTE 3: Query com termo médico específico (testa NER)

1. No `/chat`, pergunte:
   ```
   Quais são os protocolos de insulina recomendados?
   ```
2. Observe se a resposta menciona:
   - [ ] Infusão endovenosa de insulina
   - [ ] Protocolos padronizados
   - [ ] Ajustes de dose

**Resultado esperado:** ✅ Resposta específica sobre insulina (indica que NER identificou "insulina" nos metadados)

---

### ✅ TESTE 4: Query sobre valores numéricos (testa Numerical Extraction)

1. No `/chat`, pergunte:
   ```
   Qual o alvo de glicemia recomendado para pacientes em UTI?
   ```
2. Observe se a resposta menciona valores específicos:
   - [ ] 140-180 mg/dL (alvo comum)
   - [ ] Valores de HbA1c
   - [ ] Ranges específicos

**Resultado esperado:** ✅ Resposta com valores numéricos precisos (indica que numerical extraction funcionou)

---

### ✅ TESTE 5: Query sobre seção específica (testa Metadata Filtering)

1. No `/chat`, pergunte:
   ```
   Mostre as recomendações da tabela sobre critérios de hiperglicemia
   ```
2. Observe se a resposta:
   - [ ] Menciona especificamente conteúdo de tabela
   - [ ] Cita critérios objetivos
   - [ ] Usa formato estruturado

**Resultado esperado:** ✅ Resposta focada em tabelas (indica que metadata "type: table" está funcionando)

---

### ✅ TESTE 6: Query comparativa (testa Keywords)

1. No `/chat`, pergunte:
   ```
   Compare o controle glicêmico em pacientes clínicos vs cirúrgicos
   ```
2. Observe se a resposta:
   - [ ] Distingue entre tipos de pacientes
   - [ ] Usa keywords relevantes (clínico, cirúrgico, controle glicêmico)
   - [ ] Resposta coerente e específica

**Resultado esperado:** ✅ Resposta diferenciada (indica que keywords extraídas ajudam no retrieval)

---

### ✅ TESTE 7: Query sobre figura/imagem (testa Image Contextual Retrieval)

1. No `/chat`, pergunte:
   ```
   Existe algum fluxograma ou algoritmo sobre manejo de hiperglicemia?
   ```
2. Observe se a resposta:
   - [ ] Menciona a imagem/figura do PDF
   - [ ] Descreve o conteúdo visual
   - [ ] Usa descrição do GPT-4o Vision

**Resultado esperado:** ✅ Resposta sobre conteúdo visual (indica que imagens foram processadas e contextualizadas)

---

## 📊 INTERPRETAÇÃO DOS RESULTADOS

### ✅ TODOS OS TESTES PASSARAM (7/7)
**Diagnóstico:** Metadata enrichment funcionando **PERFEITAMENTE**!
- Keywords sendo usadas no retrieval
- Entidades médicas identificadas
- Valores numéricos capturados
- Filtros de metadata funcionando
- Contextual retrieval ativo

**Ação:** Nenhuma! Sistema em produção ✅

---

### ✓ MAIORIA PASSOU (5-6/7)
**Diagnóstico:** Metadata enrichment funcionando **BEM**
- Alguns aspectos podem ter cobertura parcial
- KeyBERT pode ter feito fallback para regex em alguns textos
- Ainda assim, sistema está funcional

**Ação:** Monitorar próximos uploads

---

### ⚠️ METADE PASSOU (3-4/7)
**Diagnóstico:** Metadata enrichment **PARCIALMENTE FUNCIONAL**
- Pode haver problemas de timeout
- KeyBERT pode estar falhando frequentemente
- Numerical extraction pode não estar capturando valores

**Ação:**
1. Revisar logs do último upload
2. Verificar se KeyBERT timeout está funcionando
3. Considerar reduzir max_chars ainda mais

---

### ❌ POUCOS PASSARAM (0-2/7)
**Diagnóstico:** Metadata enrichment **NÃO ESTÁ FUNCIONANDO**
- Metadados não estão sendo salvos
- Ou não estão sendo usados no retrieval

**Ação:**
1. Deletar documento e reprocessar
2. Verificar logs de erro
3. Checar se commit foi deployado no Railway

---

## 🎯 TESTES ADICIONAIS (OPCIONAL)

### TESTE 8: Verificar keywords específicas

No `/chat`, pergunte:
```
Liste as principais recomendações sobre diabetes
```

Verifique se a resposta usa termos que SABEMOS que estão no PDF:
- [ ] "hiperglicemia hospitalar"
- [ ] "paciente crítico"
- [ ] "infusão de insulina"
- [ ] "controle glicêmico"

---

### TESTE 9: Query com filtro implícito

No `/chat`, pergunte:
```
Qual o nível de evidência das recomendações sobre hiperglicemia?
```

Verifique se:
- [ ] Menciona "Classe I", "Nível A", etc (estrutura de guidelines)
- [ ] Cita especificamente a diretriz de 2025
- [ ] Usa terminologia de medicina baseada em evidências

---

### TESTE 10: Stress test - Query complexa

No `/chat`, pergunte:
```
Em um paciente diabético tipo 2 internado em UTI pós-cirurgia cardíaca,
com glicemia de 250 mg/dL, qual o protocolo de insulina recomendado e
qual o alvo glicêmico ideal? Cite as recomendações da diretriz.
```

Verifique se a resposta:
- [ ] É específica e detalhada
- [ ] Cita valores numéricos corretos
- [ ] Usa informações de TABELAS
- [ ] Menciona recomendações com classes/níveis de evidência

**Este é o teste definitivo!** Se passar, o enrichment está funcionando perfeitamente.

---

## 📝 REGISTRO DE RESULTADOS

Preencha após executar os testes:

| Teste | Passou? | Observações |
|-------|---------|-------------|
| 1. Documento processado | ☐ Sim ☐ Não | |
| 2. Query baseline | ☐ Sim ☐ Não | |
| 3. Termos médicos (NER) | ☐ Sim ☐ Não | |
| 4. Valores numéricos | ☐ Sim ☐ Não | |
| 5. Seção específica | ☐ Sim ☐ Não | |
| 6. Keywords comparativas | ☐ Sim ☐ Não | |
| 7. Imagens | ☐ Sim ☐ Não | |
| **TOTAL** | __/7 | |

**Data do teste:** ___________
**Testado por:** ___________
**Veredicto:** ___________

---

## ✅ CONCLUSÃO

Este teste manual valida que:
1. ✅ Metadata enrichment está sendo executado
2. ✅ Metadados estão sendo salvos corretamente
3. ✅ Retrieval está usando os metadados
4. ✅ Qualidade das respostas melhorou

Se você passar em 5+ testes, o sistema está funcionando **excelentemente**! 🎉
