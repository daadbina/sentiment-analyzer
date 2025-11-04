"""Embedding computation engine."""

import logging
from typing import List, Tuple
import numpy as np

from src.models.model_pool import ModelPool
from src.models.model_router import ModelRouter
from src.preprocessing.text_preprocessor import TextPreprocessor
from src.batching.dynamic_batcher import DynamicBatcher
from src.embedding.normalization import normalize_embeddings
from src.exceptions import EmbeddingComputationError
from src.metrics import embedding_computed_total

logger = logging.getLogger(__name__)


class EmbeddingEngine:
    """Main engine for computing embeddings."""

    def __init__(
        self,
        model_pool: ModelPool,
        model_router: ModelRouter,
        text_preprocessor: TextPreprocessor,
        dynamic_batcher: DynamicBatcher,
    ):
        """
        Initialize embedding engine.

        Args:
            model_pool: Model pool for model management
            model_router: Router for model selection
            text_preprocessor: Text preprocessor
            dynamic_batcher: Dynamic batcher for batch management
        """
        self.model_pool = model_pool
        self.model_router = model_router
        self.text_preprocessor = text_preprocessor
        self.dynamic_batcher = dynamic_batcher

    def compute_embeddings(
        self,
        texts: List[str],
        article_ids: List[str],
        language: str = "en",
        domain: str = None,
        normalize: bool = True,
    ) -> Tuple[np.ndarray, List[str]]:
        """
        Compute embeddings for texts.

        Args:
            texts: List of texts to embed
            article_ids: List of article IDs
            language: Language code
            domain: Optional domain
            normalize: Whether to L2-normalize embeddings

        Returns:
            Tuple of (embeddings array, article_ids)

        Raises:
            EmbeddingComputationError: If computation fails
        """
        if not texts:
            return np.array([]), []

        try:
            logger.info(
                f"Computing embeddings for {len(texts)} texts "
                f"(language={language}, domain={domain})"
            )

            # Select model
            model_name = self.model_router.select_model(language, domain)
            logger.debug(f"Selected model: {model_name}")

            # Get model from pool
            model = self.model_pool.get_model(model_name, self.dynamic_batcher.device)

            # Preprocess texts
            preprocessed_texts = self.text_preprocessor.preprocess_batch(texts)

            # Create dynamic batches
            batches = self.dynamic_batcher.create_dynamic_batches(
                preprocessed_texts,
                article_ids,
                sequence_length=model.get_max_sequence_length(),
            )

            # Compute embeddings for each batch
            all_embeddings = []
            for batch in batches:
                batch_embeddings = model.encode(
                    batch.texts,
                    batch_size=len(batch),
                    normalize=normalize,
                )
                all_embeddings.append(batch_embeddings)

            # Concatenate all embeddings
            embeddings = np.vstack(all_embeddings) if all_embeddings else np.array([])

            # Record metrics
            embedding_computed_total.labels(
                model_name=model_name,
                language=language,
            ).inc(len(texts))

            logger.info(
                f"Computed {len(texts)} embeddings "
                f"(shape={embeddings.shape}, model={model_name})"
            )

            return embeddings, article_ids

        except Exception as e:
            logger.error(f"Embedding computation failed: {e}")
            raise EmbeddingComputationError(f"Embedding computation failed: {e}")

    def get_embedding_dimension(self, model_name: str = None) -> int:
        """Get embedding dimension for a model."""
        if model_name is None:
            model_name = self.model_router.select_model("en")

        model = self.model_pool.get_model(model_name)
        return model.get_embedding_dimension()

