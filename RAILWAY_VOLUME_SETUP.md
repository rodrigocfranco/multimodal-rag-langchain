# 🚨 PROBLEMA CRÍTICO: Dados Perdidos a Cada Deploy

## O Que Está Acontecendo

O Railway usa **containers efêmeros**:
- A cada deploy, o container antigo é DESTRUÍDO
- Um novo container é criado do zero
- **TODOS os dados em `/app/knowledge_base/` são PERDIDOS**

Por isso o documento que você viu no `/manage` DESAPARECEU após o último deploy!

---

## ✅ SOLUÇÃO: Railway Volume (Persistência)

Você precisa criar um **Volume** no Railway para persistir os dados entre deploys.

### Passo 1: Criar Volume no Dashboard Railway

1. Acesse: https://railway.app/project/[SEU_PROJECT_ID]

2. Clique no seu serviço (o app)

3. Vá em **Settings** (engrenagem)

4. Role até **Volumes**

5. Click em **+ New Volume**

6. Configure:
   ```
   Mount Path: /app/knowledge_base
   ```

7. Click **Add**

8. O Railway vai criar um volume chamado automaticamente (ex: `data`)

---

### Passo 2: Atualizar railway.json (JÁ FEITO)

Já atualizei o `railway.json` para referenciar o volume:

```json
{
  "deploy": {
    "volumeMounts": [
      {
        "mountPath": "/app/knowledge_base",
        "name": "knowledge_base_volume"
      }
    ]
  }
}
```

**IMPORTANTE**: O `"name"` precisa corresponder ao nome do volume que você criou no dashboard.

Se o Railway criou com nome diferente (ex: `data`), você precisa ajustar:

```json
"name": "data"  // Use o nome exato do volume criado
```

---

### Passo 3: Fazer Redeploy

Depois de criar o volume e fazer commit do railway.json:

```bash
git add railway.json RAILWAY_VOLUME_SETUP.md
git commit -m "Add Railway volume for persistent knowledge base"
git push
```

O Railway vai:
1. Detectar o volume configurado
2. Montar `/app/knowledge_base` no volume persistente
3. **Manter os dados entre deploys**

---

## 🧪 Como Validar

Depois do setup:

1. **Faça upload de um PDF** via `/ui`
2. **Verifique em `/manage`** que está lá
3. **Faça um novo deploy** (qualquer mudança no código)
4. **Verifique em `/manage` novamente** - o PDF deve CONTINUAR lá! ✅

---

## 📊 Estrutura Esperada no Volume

Depois de processar PDFs, o volume terá:

```
/app/knowledge_base/
├── chroma.sqlite3           # Banco vetorial do ChromaDB
├── docstore.pkl             # Documentos completos
├── metadata.pkl             # Metadados dos PDFs
└── [outros arquivos do ChromaDB]
```

**TUDO isso será preservado entre deploys** uma vez que o volume esteja configurado.

---

## ⚠️ IMPORTANTE: Custo do Volume

Railway cobra por:
- **Storage**: ~$0.25/GB/mês
- **Egress**: Se você transferir dados para fora do Railway

Estime o tamanho dos PDFs:
- 10 PDFs médicos (~50 MB cada) = 500 MB de PDFs
- + Embeddings e ChromaDB = ~1-2 GB total
- **Custo estimado: $0.25-0.50/mês**

---

## 🔧 Troubleshooting

### Volume não está montando

Verifique:
1. Nome do volume em `railway.json` corresponde ao nome criado
2. Restart o serviço no Railway
3. Veja logs para erros de mount

### Dados ainda somem

Se após configurar o volume os dados ainda somem:
1. Verifique que o volume está **attached** no dashboard
2. Confirme que `mountPath` é exatamente `/app/knowledge_base`
3. Não há espaços ou caracteres estranhos

### Como migrar dados existentes

Se você já processou PDFs antes do volume:
1. Eles foram perdidos (container antigo)
2. Você precisa **reprocessar** via `/ui`
3. Agora com volume, vão persistir! ✅

---

## ✅ Checklist Final

- [ ] Volume criado no Railway dashboard
- [ ] Mount path = `/app/knowledge_base`
- [ ] `railway.json` atualizado com nome correto do volume
- [ ] Commit + push feito
- [ ] Deploy concluído
- [ ] PDF de teste processado
- [ ] Verificado em `/manage` que está lá
- [ ] Novo deploy feito (teste de persistência)
- [ ] PDF ainda está em `/manage` ✅

---

**Com isso configurado, seus documentos vão PERSISTIR entre todos os deploys futuros!** 🎉
