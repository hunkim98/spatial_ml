"""
Stage 1: Extractor (Token Classification)
Extracts candidate zone codes from ordinance text using a fine-tuned BERT model.
Uses BIO tagging scheme: B-ZONE (begin), I-ZONE (inside), O (outside).
"""

import re
from dataclasses import dataclass
from typing import List, Optional, Tuple
import torch
from transformers import (
    AutoTokenizer,
    AutoModelForTokenClassification,
    pipeline
)

# Import post-processing (will gracefully handle if not available)
try:
    import sys
    from pathlib import Path
    training_dir = Path(__file__).parent.parent / 'training'
    if training_dir.exists():
        sys.path.insert(0, str(training_dir))
    from post_processing import ZoneCodePostProcessor
    POST_PROCESSING_AVAILABLE = True
except ImportError:
    POST_PROCESSING_AVAILABLE = False


@dataclass
class ExtractedSpan:
    """A span of text identified as a potential zone code."""
    text: str
    start: int
    end: int
    score: float


class ZoneExtractor:
    """
    Extracts zone code mentions from ordinance text using token classification.

    Uses a fine-tuned BERT model to identify spans that represent zone codes.
    Handles chunking for long documents and aggregates predictions.
    """

    # Standard BIO tag labels
    TAG_LABELS = ['O', 'B-ZONE', 'I-ZONE']

    # Enhanced BIO tag labels (same as training)
    ENHANCED_TAG_LABELS = [
        'O',
        'B-ZONE',
        'I-ZONE-LETTER',
        'I-ZONE-DIGIT',
        'I-ZONE-HYPHEN',
        'I-ZONE-SUFFIX',
        'I-ZONE-DOT',
        'I-ZONE-SLASH',
    ]

    # Will be set during initialization based on model config
    TAG_TO_ID = {}
    ID_TO_TAG = {}

    def __init__(
        self,
        model_path: Optional[str] = None,
        tokenizer_name: str = "bert-base-uncased",
        max_length: int = 512,
        overlap: int = 128,
        min_score: float = 0.5,
        device: Optional[str] = None,
        enable_post_processing: bool = True,
        use_enhanced_tags: bool = False
    ):
        """
        Initialize the zone extractor.

        Args:
            model_path: Path to fine-tuned model (if None, will need to train first)
            tokenizer_name: Name of tokenizer to use
            max_length: Maximum sequence length for BERT
            overlap: Number of tokens to overlap between chunks
            min_score: Minimum confidence score to keep a prediction
            device: Device to run model on ('cuda', 'cpu', or None for auto)
            enable_post_processing: Whether to apply post-processing rules
            use_enhanced_tags: Whether model was trained with enhanced tags
        """
        self.max_length = max_length
        self.overlap = overlap
        self.min_score = min_score
        self.enable_post_processing = enable_post_processing and POST_PROCESSING_AVAILABLE
        self.use_enhanced_tags = use_enhanced_tags

        # Set tag mappings based on model type
        tag_labels = self.ENHANCED_TAG_LABELS if use_enhanced_tags else self.TAG_LABELS
        self.TAG_TO_ID = {tag: idx for idx, tag in enumerate(tag_labels)}
        self.ID_TO_TAG = {idx: tag for tag, idx in self.TAG_TO_ID.items()}

        # Set device
        if device is None:
            self.device = 'cuda' if torch.cuda.is_available() else 'cpu'
        else:
            self.device = device

        # Load tokenizer
        self.tokenizer = AutoTokenizer.from_pretrained(tokenizer_name)

        # Initialize post-processor
        self.post_processor = None
        if self.enable_post_processing:
            self.post_processor = ZoneCodePostProcessor()

        # Load model if path provided
        self.model = None
        self.ner_pipeline = None
        if model_path:
            self.load_model(model_path)

    def load_model(self, model_path: str):
        """Load a trained model from path."""
        self.model = AutoModelForTokenClassification.from_pretrained(model_path)
        self.model.to(self.device)
        self.model.eval()

        # Create NER pipeline for easier inference
        self.ner_pipeline = pipeline(
            "ner",
            model=self.model,
            tokenizer=self.tokenizer,
            device=0 if self.device == 'cuda' else -1,
            aggregation_strategy="simple"  # Aggregates B- and I- tags
        )

    def extract(self, text: str, return_raw_codes: bool = False) -> List[ExtractedSpan]:
        """
        Extract zone code mentions from text.

        Args:
            text: Input ordinance text
            return_raw_codes: If True, return raw codes without post-processing

        Returns:
            List of ExtractedSpan objects with zone code candidates
        """
        if self.ner_pipeline is None:
            raise ValueError("No model loaded. Call load_model() or train a model first.")

        # Split text into overlapping chunks
        chunks = self._chunk_text(text)

        # Extract from each chunk
        all_spans = []
        for chunk, offset in chunks:
            chunk_spans = self._extract_from_chunk(chunk, offset)
            all_spans.extend(chunk_spans)

        # Merge overlapping spans
        merged_spans = self._merge_spans(all_spans)

        # Apply post-processing if enabled
        if self.enable_post_processing and not return_raw_codes and self.post_processor:
            merged_spans = self._apply_post_processing(merged_spans, text)

        return merged_spans

    def extract_batch(self, texts: List[str]) -> List[List[ExtractedSpan]]:
        """Extract from multiple texts."""
        return [self.extract(text) for text in texts]

    def _chunk_text(self, text: str) -> List[Tuple[str, int]]:
        """
        Split text into overlapping chunks suitable for BERT.

        Args:
            text: Full text to chunk

        Returns:
            List of (chunk_text, start_offset) tuples
        """
        # Tokenize full text
        tokens = self.tokenizer.tokenize(text)

        if len(tokens) <= self.max_length:
            return [(text, 0)]

        chunks = []
        stride = self.max_length - self.overlap

        for i in range(0, len(tokens), stride):
            chunk_tokens = tokens[i:i + self.max_length]

            # Convert back to text
            chunk_text = self.tokenizer.convert_tokens_to_string(chunk_tokens)

            # Find actual character offset in original text
            # This is approximate but good enough for our purposes
            offset = text.find(chunk_text)
            if offset == -1:
                offset = 0

            chunks.append((chunk_text, offset))

            if i + self.max_length >= len(tokens):
                break

        return chunks

    def _extract_from_chunk(
        self,
        chunk: str,
        offset: int
    ) -> List[ExtractedSpan]:
        """Extract zone codes from a single chunk."""
        # Run NER pipeline
        predictions = self.ner_pipeline(
            chunk,
            truncation=True,
            max_length=self.max_length,
        )

        spans = []
        for pred in predictions:
            if pred['score'] >= self.min_score:
                # Adjust positions by offset
                span = ExtractedSpan(
                    text=pred['word'].strip(),
                    start=offset + pred['start'],
                    end=offset + pred['end'],
                    score=pred['score']
                )
                spans.append(span)

        return spans

    def _merge_spans(self, spans: List[ExtractedSpan]) -> List[ExtractedSpan]:
        """
        Merge overlapping or adjacent spans.

        Args:
            spans: List of potentially overlapping spans

        Returns:
            Merged list of spans
        """
        if not spans:
            return []

        # Sort by start position
        sorted_spans = sorted(spans, key=lambda x: x.start)

        merged = [sorted_spans[0]]
        for current in sorted_spans[1:]:
            previous = merged[-1]

            # Check if overlapping or adjacent
            if current.start <= previous.end + 1:
                # Merge spans
                merged[-1] = ExtractedSpan(
                    text=f"{previous.text} {current.text}".strip(),
                    start=previous.start,
                    end=max(previous.end, current.end),
                    score=(previous.score + current.score) / 2
                )
            else:
                merged.append(current)

        return merged

    def normalize_extracted_code(self, text: str) -> str:
        """
        Normalize extracted text to canonical zone code format.

        Args:
            text: Raw extracted text

        Returns:
            Normalized zone code
        """
        # Remove extra whitespace
        text = ' '.join(text.split())

        # Uppercase
        text = text.upper()

        # Try to extract just the zone code part
        # E.g., "THE R-1 ZONE" -> "R-1"
        patterns = [
            r'\b([A-Z]{1,3}-?\d{1,2})\b',           # R-1, C-2
            r'\b([A-Z]{2,4})\b',                     # AG, MU
            r'\b([A-Z]-[A-Z]{1,2})\b',              # R-SF
        ]

        for pattern in patterns:
            match = re.search(pattern, text)
            if match:
                return match.group(1)

        return text

    @classmethod
    def get_tag_id(cls, tag: str) -> int:
        """Convert tag to ID."""
        return cls.TAG_TO_ID.get(tag, 0)

    @classmethod
    def get_tag_label(cls, tag_id: int) -> str:
        """Convert ID to tag."""
        return cls.ID_TO_TAG.get(tag_id, 'O')

    def _apply_post_processing(
        self,
        spans: List[ExtractedSpan],
        original_text: str
    ) -> List[ExtractedSpan]:
        """
        Apply post-processing rules to complete fragmented codes.

        Args:
            spans: Extracted spans from model
            original_text: Original text for context

        Returns:
            Updated spans with completed codes
        """
        if not self.post_processor:
            return spans

        # Extract code texts
        raw_codes = [span.text for span in spans]

        # Apply post-processing
        completed = self.post_processor.post_process_extracted_codes(raw_codes, original_text)

        # Create new spans with completed codes
        updated_spans = []
        for i, span in enumerate(spans):
            if i < len(completed):
                comp = completed[i]
                # Update span with completed code
                updated_span = ExtractedSpan(
                    text=comp.completed,
                    start=span.start,
                    end=span.end,
                    score=span.score * comp.confidence  # Adjust score by completion confidence
                )
                updated_spans.append(updated_span)
            else:
                updated_spans.append(span)

        return updated_spans
