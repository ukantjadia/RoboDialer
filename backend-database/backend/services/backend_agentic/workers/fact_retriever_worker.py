# Fact retriever worker entrypoint
import asyncio
import os
import logging
import sys
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path


# Add path to access models
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../../'))
sys.path.append(os.path.join(os.path.dirname(__file__), '../../../'))


# Import semantic detection components
try:
    from services.semantic_detection.entity_extractor import SemanticEntityExtractor
    from services.semantic_detection.embedding_manager import Word2VecEmbeddingManager
    from services.semantic_detection.models import EntityMatch
    SEMANTIC_DETECTION_AVAILABLE = True
except ImportError:
    SEMANTIC_DETECTION_AVAILABLE = False
    logging.warning("Semantic detection not available. Using pattern-based entity extraction only.")

# Import agentic logging
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from agentic_logging import get_agentic_logger

logger = get_agentic_logger('workers.fact_retriever')

class FactRetrieverWorker:
    """
    Enhanced fact retriever worker for querying structured data from database
    with semantic entity extraction capabilities.
    """

    def __init__(self,
                 enable_semantic_extraction: bool = True,
                 embedding_model_path: Optional[str] = None):
        self.facts_cache = {}
        self.lead_id_index = {}
        self.loaded = False
        self.enable_semantic_extraction = enable_semantic_extraction and SEMANTIC_DETECTION_AVAILABLE

        # Initialize semantic components if available
        self.embedding_manager = None
        self.entity_extractor = None
        self.semantic_initialized = False

        if self.enable_semantic_extraction:
            self._initialize_semantic_components(embedding_model_path)

    def _initialize_semantic_components(self, embedding_model_path: Optional[str] = None):
        """Initialize semantic detection components."""
        try:
            if not SEMANTIC_DETECTION_AVAILABLE:
                logger.warning("Semantic detection components not available")
                return

            # Initialize embedding manager
            self.embedding_manager = Word2VecEmbeddingManager(
                model_path=embedding_model_path,
                model_type="word2vec",  # Default to word2vec
                cache_size=1000,
                vector_size=300
            )

            # Initialize entity extractor
            self.entity_extractor = SemanticEntityExtractor(self.embedding_manager)

            logger.info("Semantic components initialized successfully")

        except Exception as e:
            logger.error(f"Failed to initialize semantic components: {e}")
            self.enable_semantic_extraction = False

    async def initialize_semantic_detection(self) -> bool:
        """Initialize semantic detection asynchronously."""
        if not self.enable_semantic_extraction or not self.embedding_manager:
            return False

        try:
            success = await self.embedding_manager.initialize()
            if success:
                self.semantic_initialized = True
                logger.info("Semantic detection initialized successfully")
            else:
                logger.warning("Failed to initialize semantic detection, falling back to pattern-based extraction")
                self.enable_semantic_extraction = False

            return success

        except Exception as e:
            logger.error(f"Error initializing semantic detection: {e}")
            self.enable_semantic_extraction = False
            return False
    def load_facts_sync(self, user_id: str = None) -> bool:
        """
        Synchronous version of load_facts to avoid hanging issues
        """
        try:
            from ..main import get_user_drafts_data

            # Get the response from the route function
            response = get_user_drafts_data()
            logger.info(f"...............{response}======={response}")
            # Extract JSON data from Flask Response object
            if hasattr(response, 'get_json'):
                drafts_data = response.get_json()
            elif hasattr(response, 'json'):
                drafts_data = response.json
            else:
                # If it's already a dict, use it directly
                drafts_data = response
            logger.info(f"Extracted drafts data: {drafts_data}")
            # Handle the case where drafts_data is a dict with lead_id as keys
            if isinstance(drafts_data, dict):
                # This is the expected format: {lead_id: data}
                drafts_iterator = drafts_data.items()
            elif isinstance(drafts_data, list):
                # Handle cases where it might be a list of dicts with lead_id inside
                logger.warning("Draft data is a list, not a dict. Attempting to process.")
                drafts_iterator = (
                    (item.get('lead_id'), item) 
                    for item in drafts_data 
                    if 'lead_id' in item
                )
            else:
                logger.error(f"Unexpected data type for drafts_data: {type(drafts_data)}")
                self.loaded = True
                return False

            record_counter = 0
            # The loop now correctly iterates over (lead_id, draft_data) pairs
            for lead_id, draft_data in drafts_iterator:
                if draft_data and lead_id:
                    company_name = (
                        draft_data.get('company', '') or draft_data.get('Company Name', '') or
                        draft_data.get('Company', '') or draft_data.get('name', '') or
                        draft_data.get('Name', '')
                    ).strip()
                    if company_name:
                        unique_key = f"{company_name}_{record_counter}"
                        self.facts_cache[unique_key] = {
                            **draft_data,
                            'original_company_name': company_name,
                            'unique_id': unique_key,
                            'lead_id': lead_id 
                        }
                        self.lead_id_index[str(lead_id)] = unique_key
                        record_counter += 1

            self.loaded = True
            logger.info(f"Loaded {len(self.facts_cache)} companies and indexed {len(self.lead_id_index)} lead_ids.")
            return True
        except Exception as e:
            logger.error(f"Error loading facts from database: {e}", exc_info=True)
            return False
    async def load_facts(self, user_id: str = None) -> bool:
        """
        Load facts from database into memory and initialize semantic detection
        """
        try:
            # Use the synchronous version to avoid hanging
            success = self.load_facts_sync(user_id)
            if not success:
                return False

            # Initialize semantic detection if enabled
            if self.enable_semantic_extraction and not self.semantic_initialized:
                await self.initialize_semantic_detection()

            return True

        except Exception as e:
            logger.error(f"Error loading facts from database: {str(e)}")
            return False
    async def get_facts_by_lead_id(self, lead_id: str, fields: Optional[List[str]] = None) -> Optional[Dict[str, Any]]:
        """
        Retrieves facts for a specific lead_id using the efficient index.
        """
        if not self.loaded:
            await self.load_facts()

        unique_key = self.lead_id_index.get(str(lead_id))
        if not unique_key:
            logger.warning(f"Lead ID '{lead_id}' not found in index.")
            return None

        company_data = self.facts_cache.get(unique_key)
        if not company_data:
            logger.error(f"Data integrity error: unique_key '{unique_key}' found in index but not in cache.")
            return None

        result = {"entity": company_data.get('original_company_name'), "lead_id": lead_id}
        if fields:
            for field in fields:
                if field in company_data:
                    result[field] = company_data[field]
        else:
            result.update(company_data)

        return result
    async def get_facts(self, entity: str, fields: Optional[List[str]] = None) -> Dict[str, Any]:
        """
        Get facts for a specific entity (company name) with strict database gating.
        Normalizes natural-language queries (e.g., "tell me about <company>").
        Returns not_found if no confident match.
        """
        try:
            if not self.loaded:
                await self.load_facts()

            import os
            import re

            # Helper: normalize a string for exact comparison
            def _normalize_for_exact(s: str) -> str:
                s = s.strip().lower()
                # remove leading conversational phrases
                s = re.sub(r"^(tell me about|about|who is|what is|info on|information on|details about)\s+", "", s)
                # strip quotes and trailing punctuation
                s = s.strip(" \t\n\r\"'.,:;!")
                # collapse whitespace
                s = re.sub(r"\s+", " ", s)
                return s

            # Configurable fuzzy threshold via env; default 0.90 (more forgiving for NL queries)
            fuzzy_accept_threshold = float(os.getenv("FUZZY_ACCEPT_THRESHOLD", "0.90"))
            exact_required = os.getenv("EXACT_MATCH_REQUIRED", "false").lower() == "true"

            original_query = entity
            norm_query = _normalize_for_exact(entity)

            # 1) Exact-style match by normalized comparison over cached keys
            matched_entity = None
            company_data = None
            for unique_key, row in self.facts_cache.items():
                original_company_name = row.get('original_company_name', unique_key.split('_')[0])
                if _normalize_for_exact(original_company_name) == norm_query:
                    matched_entity = original_company_name
                    company_data = row
                    break

            # 2) Exact key match as stored (fast path) - check original company names
            if not matched_entity:
                for unique_key, row in self.facts_cache.items():
                    original_company_name = row.get('original_company_name', unique_key.split('_')[0])
                    if original_company_name == entity:
                        matched_entity = original_company_name
                        company_data = row
                        break

            # 3) Semantic/pattern/fuzzy match if allowed
            if not matched_entity and not exact_required:
                # Try semantic/pattern first to extract a cleaner candidate
                candidate = await self._find_best_entity_match(norm_query)
                if candidate:
                    # Find the candidate in our cache
                    for unique_key, row in self.facts_cache.items():
                        original_company_name = row.get('original_company_name', unique_key.split('_')[0])
                        if original_company_name == candidate:
                            # Verify confidence using internal fuzzy scorer against normalized strings
                            score = self._calculate_string_similarity(norm_query, _normalize_for_exact(candidate))
                            if score >= fuzzy_accept_threshold:
                                matched_entity = candidate
                                company_data = row
                                break

                # 4) Substring containment heuristic as a last resort
                if not matched_entity:
                    for unique_key, row in self.facts_cache.items():
                        original_company_name = row.get('original_company_name', unique_key.split('_')[0])
                        cn_norm = _normalize_for_exact(original_company_name)
                        if cn_norm and cn_norm in norm_query:
                            # score based on length ratio
                            shorter = len(cn_norm)
                            longer = max(len(norm_query), 1)
                            score = 0.7 + (0.3 * shorter / longer)
                            if score >= fuzzy_accept_threshold:
                                matched_entity = original_company_name
                                company_data = row
                                break

            if not matched_entity:
                logger.warning(f"Company not found in database (strict gating): {original_query}")
                return {"entity": original_query, "error": "Company not found", "extraction_method": "database_gated"}

            # Prepare result
            result = {"entity": matched_entity, "original_query": original_query if matched_entity != original_query else None}

            if fields:
                for field in fields:
                    # Try exact match first
                    if field in company_data:
                        result[field] = company_data[field]
                    else:
                        # Try case-insensitive match for common field variations
                        field_lower = field.lower().strip()
                        for data_key, data_value in company_data.items():
                            if data_key.lower().strip() == field_lower:
                                result[field] = data_value
                                break
            else:
                result.update(company_data)

            return result
        except Exception as e:
            logger.error(f"Error retrieving facts for {entity}: {str(e)}")
            return {"entity": entity, "error": str(e)}

    async def _find_best_entity_match(self, entity: str) -> Optional[str]:
        """
        Find the best matching entity using multiple extraction methods.

        Args:
            entity: Entity string to match

        Returns:
            Best matching company name or None
        """
        try:
            # Method 1: Semantic entity extraction (if available)
            if self.enable_semantic_extraction and self.semantic_initialized and self.entity_extractor:
                # Get original company names for semantic matching
                known_entities = [row.get('original_company_name', unique_key.split('_')[0])
                                for unique_key, row in self.facts_cache.items()]
                entity_matches = await self.entity_extractor.extract_entities(
                    query=entity,
                    known_entities=known_entities,
                    entity_type="company"
                )

                if entity_matches:
                    # Return the highest confidence match
                    best_match = max(entity_matches, key=lambda x: x.confidence)
                    logger.info(f"Semantic extraction found '{best_match.entity}' for '{entity}' "
                              f"with confidence {best_match.confidence:.3f}")
                    return best_match.entity

            # Method 2: Pattern-based extraction (fallback)
            pattern_match = self._extract_company_name(entity)
            if pattern_match:
                logger.info(f"Pattern extraction found '{pattern_match}' for '{entity}'")
                return pattern_match

            # Method 3: Fuzzy string matching against known entities
            fuzzy_match = self._fuzzy_match_entity(entity)
            if fuzzy_match:
                logger.info(f"Fuzzy matching found '{fuzzy_match}' for '{entity}'")
                return fuzzy_match

            return None

        except Exception as e:
            logger.error(f"Error finding best entity match for '{entity}': {e}")
            # Fallback to pattern-based extraction
            return self._extract_company_name(entity)

    def _fuzzy_match_entity(self, entity: str) -> Optional[str]:
        """
        Perform fuzzy string matching against known entities.

        Args:
            entity: Entity string to match

        Returns:
            Best fuzzy match or None
        """
        try:
            entity_lower = entity.lower().strip()
            best_match = None
            best_score = 0.0
            min_score_threshold = 0.6

            for unique_key, row in self.facts_cache.items():
                original_company_name = row.get('original_company_name', unique_key.split('_')[0])
                company_lower = original_company_name.lower().strip()

                # Calculate similarity score
                score = self._calculate_string_similarity(entity_lower, company_lower)

                if score > best_score and score >= min_score_threshold:
                    best_score = score
                    best_match = original_company_name

            if best_match:
                logger.debug(f"Fuzzy match: '{entity}' -> '{best_match}' (score: {best_score:.3f})")

            return best_match

        except Exception as e:
            logger.error(f"Error in fuzzy matching for '{entity}': {e}")
            return None

    def _calculate_string_similarity(self, str1: str, str2: str) -> float:
        """
        Calculate string similarity using multiple methods.

        Args:
            str1: First string
            str2: Second string

        Returns:
            Similarity score (0.0 to 1.0)
        """
        # Exact match
        if str1 == str2:
            return 1.0

        # Substring match
        if str1 in str2 or str2 in str1:
            shorter = min(len(str1), len(str2))
            longer = max(len(str1), len(str2))
            return 0.7 + (0.3 * shorter / longer)

        # Word-level matching
        words1 = set(str1.split())
        words2 = set(str2.split())

        if words1 & words2:  # Common words
            overlap = len(words1 & words2)
            total = len(words1 | words2)
            return 0.5 + (0.3 * overlap / total) if total > 0 else 0.5

        # Character-level similarity (Jaccard)
        chars1 = set(str1)
        chars2 = set(str2)

        if chars1 & chars2:
            overlap = len(chars1 & chars2)
            total = len(chars1 | chars2)
            return 0.2 + (0.3 * overlap / total) if total > 0 else 0.2

        return 0.0

    def _extract_company_name(self, entity: str) -> Optional[str]:
        """
        Extract clean company name from entity string
        """
        try:
            # Remove common prefixes and suffixes
            entity_clean = entity.strip()

            # Remove common phrases
            phrases_to_remove = [
                "the financial health of",
                "financial performance of",
                "revenue of",
                "data on",
                "information about",
                "details about",
                "analysis of",
                "compare",
                "comparison of"
            ]

            entity_lower = entity_clean.lower()
            for phrase in phrases_to_remove:
                if phrase in entity_lower:
                    # Find the phrase and remove it
                    start_idx = entity_lower.find(phrase)
                    if start_idx != -1:
                        # Remove the phrase and everything before it
                        entity_clean = entity_clean[start_idx + len(phrase):].strip()
                        break

            # Check if the cleaned entity matches any company name
            for unique_key, row in self.facts_cache.items():
                original_company_name = row.get('original_company_name', unique_key.split('_')[0])
                if original_company_name.lower() in entity_clean.lower() or entity_clean.lower() in original_company_name.lower():
                    return original_company_name

            # If no match found, return the cleaned entity
            return entity_clean if entity_clean != entity else None

        except Exception as e:
            logger.error(f"Error extracting company name from {entity}: {str(e)}")
            return None

    async def search_companies(self, query: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Search companies based on query
        """
        try:
            if not self.loaded:
                await self.load_facts()

            results = []
            query_lower = query.lower()

            for unique_key, data in self.facts_cache.items():
                original_company_name = data.get('original_company_name', unique_key.split('_')[0])
                # Search in company name, industry, city, state, and product/service category
                searchable_fields = [
                    original_company_name,
                    data.get('Industry', '') or data.get('Industry ', ''),  # Handle trailing space
                    data.get('City', ''),
                    data.get('State', ''),
                    data.get('Product/Service Category', '')
                ]

                for field in searchable_fields:
                    if query_lower in str(field).lower():
                        results.append({"entity": original_company_name, **data})
                        break

                if len(results) >= limit:
                    break

            return results

        except Exception as e:
            logger.error(f"Error searching companies: {str(e)}")
            return []

    async def get_companies_by_industry(self, industry: str, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get companies by industry with sorting by revenue (desc) and robust field handling
        """
        try:
            if not self.loaded:
                await self.load_facts()

            industry_lower = (industry or "").lower().strip()
            exact_matches: List[Dict[str, Any]] = []
            partial_matches: List[Dict[str, Any]] = []

            def parse_revenue(revenue_str: str) -> float:
                if not revenue_str:
                    return 0.0
                try:
                    s = str(revenue_str).replace("$", "").replace(",", "").strip()
                    if s.endswith("M") or s.endswith("m"):
                        return float(s[:-1]) * 1_000_000
                    if s.endswith("K") or s.endswith("k"):
                        return float(s[:-1]) * 1_000
                    return float(s)
                except Exception:
                    return 0.0

            for unique_key, data in self.facts_cache.items():
                original_company_name = data.get('original_company_name', unique_key.split('_')[0])
                ind_field = data.get('Industry', '') or data.get('Industry ', '')
                ind_val = str(ind_field).lower().strip()
                entry = {"entity": original_company_name, **data}
                if ind_val == industry_lower:
                    exact_matches.append(entry)
                elif industry_lower and industry_lower in ind_val:
                    partial_matches.append(entry)

            # Sort by revenue desc
            exact_matches.sort(key=lambda d: parse_revenue(d.get('Revenue', '')), reverse=True)
            partial_matches.sort(key=lambda d: parse_revenue(d.get('Revenue', '')), reverse=True)

            results = exact_matches[:limit]
            if len(results) < limit:
                # Fill remaining slots from partials (avoid duplicates)
                seen = set(r["entity"] for r in results)
                for r in partial_matches:
                    if r["entity"] not in seen:
                        results.append(r)
                        seen.add(r["entity"])
                    if len(results) >= limit:
                        break

            return results

        except Exception as e:
            logger.error(f"Error getting companies by industry: {str(e)}")
            return []

    async def get_companies_by_revenue_range(self, min_revenue: float, max_revenue: float) -> List[Dict[str, Any]]:
        """
        Get companies by revenue range
        """
        try:
            if not self.loaded:
                await self.load_facts()

            results = []

            for unique_key, data in self.facts_cache.items():
                original_company_name = data.get('original_company_name', unique_key.split('_')[0])
                revenue_str = data.get('Revenue', '')
                if revenue_str:
                    # Parse revenue (handle formats like "10M", "$12M", "17.8M")
                    try:
                        revenue_clean = revenue_str.replace('$', '').replace(',', '')
                        if 'M' in revenue_clean:
                            revenue_value = float(revenue_clean.replace('M', '')) * 1000000
                        elif 'K' in revenue_clean:
                            revenue_value = float(revenue_clean.replace('K', '')) * 1000
                        else:
                            revenue_value = float(revenue_clean)

                        if min_revenue <= revenue_value <= max_revenue:
                            results.append({"entity": original_company_name, **data})
                    except:
                        continue

            return results

        except Exception as e:
            logger.error(f"Error getting companies by revenue range: {str(e)}")
            return []

    async def get_companies_by_employee_count(self, min_employees: int, max_employees: int) -> List[Dict[str, Any]]:
        """
        Get companies by employee count range
        """
        try:
            if not self.loaded:
                await self.load_facts()

            results = []

            for unique_key, data in self.facts_cache.items():
                original_company_name = data.get('original_company_name', unique_key.split('_')[0])
                employees_str = data.get('Employees', '')
                if employees_str:
                    try:
                        # Handle ranges like "2 to 25"
                        if 'to' in str(employees_str):
                            employee_parts = str(employees_str).split('to')
                            employee_count = int(employee_parts[0].strip())
                        else:
                            employee_count = int(employees_str)

                        if min_employees <= employee_count <= max_employees:
                            results.append({"entity": original_company_name, **data})
                    except:
                        continue

            return results

        except Exception as e:
            logger.error(f"Error getting companies by employee count: {str(e)}")
            return []

    async def get_available_fields(self) -> List[str]:
        """
        Get list of available fields in the database
        """
        try:
            if not self.loaded:
                await self.load_facts()

            if not self.facts_cache:
                return []

            # Get fields from first company
            first_company = next(iter(self.facts_cache.values()))
            return list(first_company.keys())

        except Exception as e:
            logger.error(f"Error getting available fields: {str(e)}")
            return []

    async def get_available_companies(self) -> List[str]:
        """
        Get list of available companies
        """
        try:
            if not self.loaded:
                await self.load_facts()

            return [row.get('original_company_name', unique_key.split('_')[0])
                    for unique_key, row in self.facts_cache.items()]

        except Exception as e:
            logger.error(f"Error getting available companies: {str(e)}")
            return []

    async def get_company_summary(self, company_name: str) -> Dict[str, Any]:
        """
        Get a summary of company information
        """
        try:
            if not self.loaded:
                await self.load_facts()

            # Find company in cache by original company name
            data = None
            for unique_key, row in self.facts_cache.items():
                original_company_name = row.get('original_company_name', unique_key.split('_')[0])
                if original_company_name == company_name:
                    data = row
                    break

            if not data:
                return {"error": "Company not found"}

            summary = {
                "company_name": company_name,
                "industry": data.get('Industry', ''),
                "revenue": data.get('Revenue', ''),
                "employees": data.get('Employees', ''),
                "location": f"{data.get('City', '')}, {data.get('State', '')}",
                "year_founded": data.get('Year Founded', ''),
                "business_type": data.get('Business Type (B2B, B2B2C) ', ''),
                "product_service": data.get('Product/Service Category', ''),
                "website": data.get('Website', ''),
                "linkedin": data.get('LinkedIn URL', '')
            }

            return summary

        except Exception as e:
            logger.error(f"Error getting company summary: {str(e)}")
            return {"error": str(e)}

    async def extract_entities_from_query(self, query: str) -> List[Dict[str, Any]]:
        """
        Extract all entities from a query using semantic detection.

        Args:
            query: Input query text

        Returns:
            List of extracted entities with metadata
        """
        try:
            if not self.loaded:
                await self.load_facts()

            entities = []

            # Use semantic extraction if available
            if self.enable_semantic_extraction and self.semantic_initialized and self.entity_extractor:
                # Get original company names for semantic matching
                known_entities = [row.get('original_company_name', unique_key.split('_')[0])
                                for unique_key, row in self.facts_cache.items()]
                entity_matches = await self.entity_extractor.extract_entities(
                    query=query,
                    known_entities=known_entities,
                    entity_type="company"
                )

                for match in entity_matches:
                    # Check if entity is available in database
                    available_in_db = any(row.get('original_company_name', unique_key.split('_')[0]) == match.entity
                                        for unique_key, row in self.facts_cache.items())
                    entities.append({
                        "entity": match.entity,
                        "matched_text": match.matched_text,
                        "confidence": match.confidence,
                        "method": match.method,
                        "position": match.position,
                        "available_in_database": available_in_db
                    })

            # Fallback to pattern-based extraction
            if not entities:
                pattern_entity = self._extract_company_name(query)
                if pattern_entity:
                    entities.append({
                        "entity": pattern_entity,
                        "matched_text": pattern_entity,
                        "confidence": 0.7,
                        "method": "pattern",
                        "position": (0, len(pattern_entity)),
                        "available_in_database": any(row.get('original_company_name', unique_key.split('_')[0]) == pattern_entity
                                                   for unique_key, row in self.facts_cache.items())
                    })

            return entities

        except Exception as e:
            logger.error(f"Error extracting entities from query '{query}': {e}")
            return []

    async def validate_entity(self, entity: str) -> Dict[str, Any]:
        """
        Validate if an entity exists in the database and get match information.

        Args:
            entity: Entity to validate

        Returns:
            Validation result with match information
        """
        try:
            if not self.loaded:
                await self.load_facts()

            result = {
                "entity": entity,
                "exists": False,
                "exact_match": False,
                "best_match": None,
                "confidence": 0.0,
                "method": None
            }

            # Check exact match
            if entity in self.facts_cache:
                result.update({
                    "exists": True,
                    "exact_match": True,
                    "best_match": entity,
                    "confidence": 1.0,
                    "method": "exact"
                })
                return result

            # Find best match using multiple methods
            best_match = await self._find_best_entity_match(entity)

            if best_match:
                # Calculate confidence based on matching method
                if self.enable_semantic_extraction and self.semantic_initialized:
                    # Use semantic extraction to get confidence
                    entity_matches = await self.entity_extractor.extract_entities(
                        query=entity,
                        known_entities=[best_match],
                        entity_type="company"
                    )

                    if entity_matches:
                        confidence = entity_matches[0].confidence
                        method = entity_matches[0].method
                    else:
                        confidence = 0.7
                        method = "pattern"
                else:
                    confidence = 0.7
                    method = "pattern"

                result.update({
                    "exists": True,
                    "exact_match": False,
                    "best_match": best_match,
                    "confidence": confidence,
                    "method": method
                })

            return result

        except Exception as e:
            logger.error(f"Error validating entity '{entity}': {e}")
            return {
                "entity": entity,
                "exists": False,
                "error": str(e)
            }

    def get_extraction_capabilities(self) -> Dict[str, Any]:
        """
        Get information about available extraction capabilities.

        Returns:
            Dictionary with capability information
        """
        capabilities = {
            "semantic_extraction_available": SEMANTIC_DETECTION_AVAILABLE,
            "semantic_extraction_enabled": self.enable_semantic_extraction,
            "semantic_initialized": self.semantic_initialized,
            "pattern_extraction_available": True,
            "fuzzy_matching_available": True,
            "total_entities": len(self.facts_cache) if self.loaded else 0,
            "extraction_methods": ["exact", "pattern", "fuzzy"]
        }

        if self.enable_semantic_extraction:
            capabilities["extraction_methods"].insert(0, "semantic")

        if self.entity_extractor:
            capabilities["entity_extractor_stats"] = self.entity_extractor.get_extraction_stats()

        if self.embedding_manager:
            capabilities["embedding_manager_info"] = self.embedding_manager.get_model_info()

        return capabilities

# Standalone execution
async def main():
    """
    Standalone execution for testing enhanced fact retriever with semantic extraction
    """
    # Test with semantic extraction enabled
    worker = FactRetrieverWorker(enable_semantic_extraction=True)

    # Test loading facts
    loaded = await worker.load_facts()
    print(f"Facts loaded: {loaded}")

    # Show extraction capabilities
    capabilities = worker.get_extraction_capabilities()
    print(f"Extraction capabilities: {capabilities}")

    # Test getting company facts with exact match
    facts = await worker.get_facts("Lumious", ["Revenue", "Employees", "Industry"])
    print(f"Facts for Lumious: {facts}")

    # Test semantic entity extraction with natural language
    semantic_query = "the financial health of Lumious"
    facts_semantic = await worker.get_facts(semantic_query, ["Revenue", "Employees", "Industry"])
    print(f"Facts for '{semantic_query}': {facts_semantic}")

    # Test entity extraction from complex query
    complex_query = "compare the performance of Microsoft and Apple"
    entities = await worker.extract_entities_from_query(complex_query)
    print(f"Entities extracted from '{complex_query}': {entities}")

    # Test entity validation
    validation = await worker.validate_entity("Lumious")
    print(f"Validation for 'Lumious': {validation}")

    validation_fuzzy = await worker.validate_entity("financial health of Lumious")
    print(f"Validation for 'financial health of Lumious': {validation_fuzzy}")

    # Test search
    search_results = await worker.search_companies("education", limit=5)
    print(f"Search results for 'education': {len(search_results)} companies")

    # Test industry filter
    industry_results = await worker.get_companies_by_industry("Education", limit=3)
    print(f"Education companies: {len(industry_results)}")

if __name__ == "__main__":
    asyncio.run(main())