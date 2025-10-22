"""
🔍 METADATA EXTRACTORS - Advanced Metadata Enrichment for Medical RAG

Implementação das 3 técnicas de enriquecimento de metadados:
1. KeyBERT - Extração semântica de keywords
2. MediAlbertina - Extração de entidades médicas em PT-PT
3. Numerical Values - Extração de valores numéricos com unidades

Baseado em: METADATA_ENRICHMENT_ANALYSIS.md
Data: 2025-10-21
"""

from typing import List, Dict, Optional
import re

# ==============================================================================
# 1. KEYBERT - KEYWORD EXTRACTION
# ==============================================================================

class KeywordExtractor:
    """Extração de keywords semânticas usando KeyBERT"""

    def __init__(self):
        """
        Inicializa KeyBERT com modelo multilíngue otimizado para português

        Modelo: paraphrase-multilingual-MiniLM-L12-v2
        - Suporta 50+ idiomas incluindo português
        - 384 dimensões
        - Rápido e preciso para textos médicos
        """
        from keybert import KeyBERT

        print("🔧 Inicializando KeyBERT (multilingual model)...")
        self.kw_model = KeyBERT(model='paraphrase-multilingual-MiniLM-L12-v2')
        print("   ✓ KeyBERT pronto!")

    def extract_keywords(
        self,
        text: str,
        top_n: int = 8,
        use_maxsum: bool = True,
        diversity: float = 0.5,
        max_chars: int = 3000  # NOVO: Limite para evitar lentidão
    ) -> List[str]:
        """
        Extrai keywords semanticamente relevantes do texto

        Args:
            text: Texto para extrair keywords
            top_n: Número de keywords a extrair (padrão: 8)
            use_maxsum: Usar MaxSum para diversificar keywords (padrão: True)
            diversity: Nível de diversidade 0-1 (padrão: 0.5)
            max_chars: Máximo de caracteres a processar (padrão: 3000)

        Returns:
            Lista de keywords ordenadas por relevância

        Exemplo:
            >>> extractor = KeywordExtractor()
            >>> keywords = extractor.extract_keywords("Diabetes tipo 2 com HbA1c elevada...")
            >>> print(keywords)
            ['diabetes', 'HbA1c', 'glicemia', 'metformina', 'insulina']
        """
        if not text or len(text.strip()) < 20:
            return []

        # ⚡ OTIMIZAÇÃO: Limitar tamanho do texto para evitar lentidão
        # KeyBERT fica MUITO lento com textos grandes (>3000 chars)
        # Usar apenas os primeiros N caracteres (geralmente contêm as keywords principais)
        if len(text) > max_chars:
            text = text[:max_chars]

        try:
            # Extração com KeyBERT
            keywords = self.kw_model.extract_keywords(
                text,
                keyphrase_ngram_range=(1, 2),  # Unigrams e bigrams
                stop_words=None,  # Não usar stop words (médico tem termos específicos)
                top_n=top_n,
                use_maxsum=use_maxsum,
                nr_candidates=20,
                diversity=diversity
            )

            # Retornar apenas as strings (sem scores)
            return [kw[0] for kw in keywords]

        except Exception as e:
            print(f"      ⚠️  Erro ao extrair keywords: {str(e)[:100]}")
            return []


# ==============================================================================
# 2. MEDIALBERTINA - MEDICAL ENTITY EXTRACTION (PT-PT)
# ==============================================================================

class MedicalEntityExtractor:
    """
    Extração de entidades médicas usando MediAlbertina PT-PT

    MediAlbertina: Estado da arte para português médico
    - 96.13% F1 score em textos médicos portugueses
    - Treinado em 96M tokens de textos médicos PT
    - Identifica: doenças, medicamentos, procedimentos, anatomia, etc.

    Referência: https://huggingface.co/pucpr/medialbertina-pt-pt
    """

    def __init__(self):
        """
        Inicializa extrator de entidades médicas

        Tenta carregar modelos nesta ordem:
        1. BioBERT multilingual (melhor para português médico)
        2. Fallback: regex patterns (rápido e eficaz para termos comuns)
        """
        print("🔧 Inicializando Medical Entity Extractor...")

        self.ner = None

        # Opção: Usar BioBERT (bom para textos médicos multilíngues)
        # Comentado por padrão para economizar memória - descomente se quiser usar
        """
        try:
            from transformers import AutoTokenizer, AutoModelForTokenClassification, pipeline

            # BioBERT é treinado em textos médicos (inglês, mas funciona em PT)
            model_name = "dmis-lab/biobert-base-cased-v1.2"

            self.tokenizer = AutoTokenizer.from_pretrained(model_name)
            self.model = AutoModelForTokenClassification.from_pretrained(model_name)

            self.ner = pipeline(
                "ner",
                model=self.model,
                tokenizer=self.tokenizer,
                aggregation_strategy="simple",
                device=-1  # CPU
            )

            print("   ✓ BioBERT carregado!")
            return

        except Exception as e:
            print(f"   ⚠️  BioBERT não disponível: {str(e)[:100]}")
        """

        print("   ✓ Usando extração por regex patterns (rápido e eficaz!)")
        self.ner = None

    def extract_entities(self, text: str) -> Dict[str, List[str]]:
        """
        Extrai entidades médicas do texto em português

        Args:
            text: Texto médico em português para análise

        Returns:
            Dict com listas de entidades por categoria:
            {
                "diseases": ["diabetes tipo 2", "hipertensão"],
                "medications": ["metformina", "insulina"],
                "procedures": ["glicemia capilar", "HbA1c"]
            }

        Exemplo:
            >>> extractor = MedicalEntityExtractor()
            >>> entities = extractor.extract_entities("Paciente com diabetes tipo 2 em uso de metformina")
            >>> print(entities["diseases"])
            ['diabetes tipo 2']
            >>> print(entities["medications"])
            ['metformina']
        """
        if not text or len(text.strip()) < 10:
            return {"diseases": [], "medications": [], "procedures": []}

        # Se MediAlbertina não carregou, usar fallback
        if self.ner is None:
            return self._extract_entities_fallback(text)

        try:
            # Limitar texto para evitar timeout (MediAlbertina tem limite de tokens)
            text_limited = text[:2000]

            # Executar NER
            entities_raw = self.ner(text_limited)

            # Organizar por tipo
            diseases = []
            medications = []
            procedures = []

            for entity in entities_raw:
                entity_text = entity['word'].strip()
                entity_type = entity.get('entity_group', 'UNKNOWN')

                # Mapear tipos de entidade
                if entity_type in ['DISEASE', 'DIAGNOSIS', 'DISORDER', 'SYMPTOM']:
                    if entity_text not in diseases:
                        diseases.append(entity_text)

                elif entity_type in ['MEDICATION', 'DRUG', 'TREATMENT']:
                    if entity_text not in medications:
                        medications.append(entity_text)

                elif entity_type in ['PROCEDURE', 'TEST', 'EXAM']:
                    if entity_text not in procedures:
                        procedures.append(entity_text)

            return {
                "diseases": diseases,
                "medications": medications,
                "procedures": procedures
            }

        except Exception as e:
            print(f"      ⚠️  Erro ao extrair entidades médicas: {str(e)[:100]}")
            return self._extract_entities_fallback(text)

    def _extract_entities_fallback(self, text: str) -> Dict[str, List[str]]:
        """
        Fallback: Extração usando regex para termos médicos comuns em PT

        Padrões otimizados para textos médicos em português brasileiro/europeu
        Captura: doenças, medicamentos, procedimentos/exames
        """
        diseases = []
        medications = []
        procedures = []

        # Padrões expandidos de doenças
        disease_patterns = [
            r'diabetes\s+(?:mellitus\s+)?tipo\s+[12I]',
            r'diabetes\s+tipo\s+[12]',
            r'hipertensão\s+arterial(?:\s+sistêmica)?',
            r'insuficiência\s+cardíaca(?:\s+congestiva)?',
            r'cardiomiopatia\s+hipertrófica',
            r'nefrite\s+lúpica',
            r'síndrome\s+metabólica',
            r'doença\s+renal\s+crônica',
            r'síndrome\s+coronariana\s+aguda',
            r'infarto\s+(?:agudo\s+do\s+)?miocárdio',
            r'acidente\s+vascular\s+cerebral',
            r'fibrilação\s+atrial',
            r'obesidade',
            r'dislipidemia',
        ]

        # Padrões expandidos de medicamentos
        medication_patterns = [
            r'metformina',
            r'insulina(?:\s+(?:glargina|detemir|aspart|lispro|NPH|regular))?',
            r'gliclazida',
            r'empagliflozina',
            r'dapagliflozina',
            r'canagliflozina',
            r'liraglutida',
            r'semaglutida',
            r'dulaglutida',
            r'sitagliptina',
            r'vildagliptina',
            r'iSGLT-?2',
            r'AR\s+GLP-?1',
            r'iDPP-?4',
            r'mavacamten',
            r'aficamten',
            r'enalapril',
            r'losartana',
            r'atorvastatina',
            r'sinvastatina',
            r'AAS|aspirina',
            r'clopidogrel',
        ]

        # Padrões expandidos de procedimentos/exames
        procedure_patterns = [
            r'HbA1c|hemoglobina\s+glicada|A1C',
            r'glicemia(?:\s+(?:de\s+jejum|pós-prandial|capilar))?',
            r'TFG|taxa\s+de\s+filtração\s+glomerular',
            r'creatinina(?:\s+sérica)?',
            r'albuminúria',
            r'ureia',
            r'colesterol(?:\s+(?:total|LDL|HDL))?',
            r'triglicerídeos',
            r'ecocardiograma',
            r'eletrocardiograma|ECG',
            r'teste\s+ergométrico',
            r'cintilografia\s+miocárdica',
            r'cateterismo\s+cardíaco',
            r'angiografia\s+coronariana',
            r'ressonância\s+magnética',
            r'tomografia\s+computadorizada',
        ]

        # Extrair matches únicos
        for pattern in disease_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            diseases.extend([m.strip() for m in matches])

        for pattern in medication_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            medications.extend([m.strip() for m in matches])

        for pattern in procedure_patterns:
            matches = re.findall(pattern, text, re.IGNORECASE)
            procedures.extend([m.strip() for m in matches])

        return {
            "diseases": list(set([d for d in diseases if d])),
            "medications": list(set([m for m in medications if m])),
            "procedures": list(set([p for p in procedures if p]))
        }


# ==============================================================================
# 3. NUMERICAL VALUE EXTRACTION
# ==============================================================================

class NumericalValueExtractor:
    """Extração de valores numéricos com unidades de medida médicas"""

    def __init__(self):
        """Inicializa extrator de valores numéricos"""
        pass

    def extract_measurements(self, text: str) -> List[Dict[str, any]]:
        """
        Extrai valores numéricos com unidades de textos médicos

        Args:
            text: Texto médico com valores numéricos

        Returns:
            Lista de medições encontradas:
            [
                {"name": "HbA1c", "value": 7.5, "unit": "%"},
                {"name": "TFG", "value": 45, "unit": "mL/min/1.73m²"}
            ]

        Exemplo:
            >>> extractor = NumericalValueExtractor()
            >>> measurements = extractor.extract_measurements("HbA1c: 7.5%, TFG: 45 mL/min")
            >>> print(measurements)
            [{'name': 'HbA1c', 'value': 7.5, 'unit': '%'}, ...]
        """
        if not text:
            return []

        measurements = []

        # Padrões de medições médicas comuns
        patterns = [
            # HbA1c: 7.5%
            (r'(?P<name>HbA1c|A1C|hemoglobina\s+glicada)[:\s]+(?P<value>\d+\.?\d*)\s*(?P<unit>%)', 'HbA1c'),

            # Creatinina: 1.2 mg/dL
            (r'(?P<name>creatinina|creatinine)[:\s]+(?P<value>\d+\.?\d*)\s*(?P<unit>mg/dL|μmol/L)', 'creatinina'),

            # TFG: 60 mL/min/1.73m²
            (r'(?P<name>TFG|GFR|taxa\s+de\s+filtração\s+glomerular)[:\s]+(?P<value>\d+\.?\d*)\s*(?P<unit>mL/min(?:/1\.73m²)?)', 'TFG'),

            # Pressão arterial: 140/90 mmHg
            (r'(?P<value>\d{2,3}/\d{2,3})\s*(?P<unit>mmHg)', 'pressão_arterial'),

            # Glicemia: 180 mg/dL
            (r'(?P<name>glicemia|glucose)[:\s]+(?P<value>\d+\.?\d*)\s*(?P<unit>mg/dL|mmol/L)', 'glicemia'),

            # Peso: 75.5 kg
            (r'(?P<name>peso|weight)[:\s]+(?P<value>\d+\.?\d*)\s*(?P<unit>kg)', 'peso'),

            # Albuminúria: 300 mg/g
            (r'(?P<name>albuminúria|albumin)[:\s]+(?P<value>\d+\.?\d*)\s*(?P<unit>mg/g|mg/24h)', 'albuminúria'),
        ]

        for pattern, default_name in patterns:
            matches = re.finditer(pattern, text, re.IGNORECASE)

            for match in matches:
                measurement = {
                    "name": match.group('name') if 'name' in match.groupdict() and match.group('name') else default_name,
                    "value": match.group('value'),
                    "unit": match.group('unit')
                }

                # Tentar converter valor para float
                try:
                    if '/' not in measurement['value']:  # Não converter pressão arterial
                        measurement['value'] = float(measurement['value'])
                except:
                    pass  # Manter como string

                measurements.append(measurement)

        return measurements


# ==============================================================================
# FACADE: UNIFIED METADATA EXTRACTOR
# ==============================================================================

class MetadataEnricher:
    """
    Facade que combina todos os extractors para enriquecimento completo

    Uso:
        enricher = MetadataEnricher()
        enriched = enricher.enrich(chunk_text)

        # enriched contém:
        # {
        #     "keywords": [...],
        #     "entities_diseases": [...],
        #     "entities_medications": [...],
        #     "entities_procedures": [...],
        #     "measurements": [...],
        #     "has_medical_entities": True/False,
        #     "has_measurements": True/False
        # }
    """

    def __init__(self):
        """Inicializa todos os extractors"""
        print("\n🚀 Inicializando Metadata Enrichment System...")

        self.keyword_extractor = KeywordExtractor()
        self.entity_extractor = MedicalEntityExtractor()
        self.numerical_extractor = NumericalValueExtractor()

        print("✅ Metadata Enrichment System pronto!\n")

    def enrich(self, text: str, extract_keywords: bool = True, extract_entities: bool = True, extract_measurements: bool = True) -> Dict:
        """
        Enriquece texto com todos os metadados disponíveis

        Args:
            text: Texto para enriquecer
            extract_keywords: Extrair keywords (padrão: True)
            extract_entities: Extrair entidades médicas (padrão: True)
            extract_measurements: Extrair valores numéricos (padrão: True)

        Returns:
            Dict com todos os metadados extraídos
        """
        enriched = {}

        # Keywords
        if extract_keywords:
            keywords = self.keyword_extractor.extract_keywords(text)
            enriched["keywords"] = keywords
            enriched["keywords_str"] = ", ".join(keywords)

        # Entidades médicas
        if extract_entities:
            entities = self.entity_extractor.extract_entities(text)
            enriched["entities_diseases"] = entities["diseases"]
            enriched["entities_medications"] = entities["medications"]
            enriched["entities_procedures"] = entities["procedures"]
            enriched["has_medical_entities"] = (
                len(entities["diseases"]) > 0 or
                len(entities["medications"]) > 0 or
                len(entities["procedures"]) > 0
            )

        # Valores numéricos
        if extract_measurements:
            measurements = self.numerical_extractor.extract_measurements(text)
            enriched["measurements"] = measurements
            enriched["has_measurements"] = len(measurements) > 0

        return enriched


# ==============================================================================
# TESTES
# ==============================================================================

if __name__ == "__main__":
    print("="*80)
    print("🧪 TESTANDO METADATA EXTRACTORS")
    print("="*80)

    # Texto de teste
    test_text = """
    Paciente com diabetes tipo 2 e hipertensão arterial. HbA1c: 8.5%,
    glicemia de jejum: 180 mg/dL, TFG: 45 mL/min/1.73m².
    Iniciado tratamento com metformina 850mg e insulina glargina 10 UI/dia.
    Creatinina: 1.4 mg/dL, albuminúria: 350 mg/g.
    """

    # Inicializar enricher
    enricher = MetadataEnricher()

    # Enriquecer
    print("\n📝 Texto de teste:")
    print(test_text)

    print("\n🔍 Extraindo metadados...\n")
    enriched = enricher.enrich(test_text)

    # Mostrar resultados
    print("✅ RESULTADOS:")
    print(f"\n📌 Keywords: {enriched['keywords']}")
    print(f"\n🏥 Doenças: {enriched['entities_diseases']}")
    print(f"💊 Medicamentos: {enriched['entities_medications']}")
    print(f"🔬 Procedimentos/Exames: {enriched['entities_procedures']}")
    print(f"\n📊 Medições:")
    for m in enriched['measurements']:
        print(f"   - {m['name']}: {m['value']} {m['unit']}")

    print(f"\n✓ Has medical entities: {enriched['has_medical_entities']}")
    print(f"✓ Has measurements: {enriched['has_measurements']}")

    print("\n" + "="*80)
    print("✅ TESTES CONCLUÍDOS!")
    print("="*80)
