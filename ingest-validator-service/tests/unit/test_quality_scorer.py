"""Tests for quality scorer."""

from src.validation.quality import QualityScorer


class TestQualityScorer:
    """Test quality scorer."""

    def test_validate_title_valid(self):
        """Test title validation - valid."""
        title = "This is a valid title"
        is_valid, error = QualityScorer.validate_title(title)
        assert is_valid is True
        assert error is None

    def test_validate_title_empty(self):
        """Test title validation - empty."""
        is_valid, error = QualityScorer.validate_title("")
        assert is_valid is False
        assert error is not None

    def test_validate_title_too_short(self):
        """Test title validation - too short."""
        is_valid, error = QualityScorer.validate_title("Hi")
        assert is_valid is False
        assert error is not None

    def test_validate_title_too_long(self):
        """Test title validation - too long."""
        title = "x" * 300
        is_valid, error = QualityScorer.validate_title(title)
        assert is_valid is False
        assert error is not None

    def test_validate_body_valid(self):
        """Test body validation - valid."""
        body = "This is a valid body with enough content. It has multiple sentences. And it is long enough with more text to meet minimum length requirements."
        is_valid, error = QualityScorer.validate_body(body)
        assert is_valid is True
        assert error is None

    def test_validate_body_empty(self):
        """Test body validation - empty."""
        is_valid, error = QualityScorer.validate_body("")
        assert is_valid is False
        assert error is not None

    def test_validate_body_too_short(self):
        """Test body validation - too short."""
        is_valid, error = QualityScorer.validate_body("Short body")
        assert is_valid is False
        assert error is not None

    def test_validate_body_single_sentence(self):
        """Test body validation - single sentence."""
        body = "This is only one sentence"
        is_valid, error = QualityScorer.validate_body(body)
        assert is_valid is False
        assert error is not None

    def test_count_words(self):
        """Test word counting."""
        text = "Hello world this is a test"
        count = QualityScorer.count_words(text)
        assert count == 6

    def test_count_words_with_punctuation(self):
        """Test word counting with punctuation."""
        text = "Hello, world! This is a test."
        count = QualityScorer.count_words(text)
        assert count == 6

    def test_validate_word_count_valid(self):
        """Test word count validation - valid."""
        text = "word " * 30  # 30 words
        is_valid, error = QualityScorer.validate_word_count(text)
        assert is_valid is True
        assert error is None

    def test_validate_word_count_too_low(self):
        """Test word count validation - too low."""
        text = "word " * 5  # 5 words
        is_valid, error = QualityScorer.validate_word_count(text)
        assert is_valid is False
        assert error is not None

    def test_validate_url_valid(self):
        """Test URL validation - valid."""
        url = "https://example.com/article"
        is_valid, error = QualityScorer.validate_url(url)
        assert is_valid is True
        assert error is None

    def test_validate_url_invalid_scheme(self):
        """Test URL validation - invalid scheme."""
        url = "ftp://example.com/article"
        is_valid, error = QualityScorer.validate_url(url)
        assert is_valid is False
        assert error is not None

    def test_validate_url_missing_scheme(self):
        """Test URL validation - missing scheme."""
        url = "example.com/article"
        is_valid, error = QualityScorer.validate_url(url)
        assert is_valid is False
        assert error is not None

    def test_calculate_special_char_ratio(self):
        """Test special character ratio calculation."""
        text = "Hello World"
        ratio = QualityScorer.calculate_special_char_ratio(text)
        assert 0.0 <= ratio <= 1.0

    def test_calculate_special_char_ratio_high(self):
        """Test special character ratio - high."""
        text = "!!!@@@###$$$%%%"
        ratio = QualityScorer.calculate_special_char_ratio(text)
        assert ratio > 0.5

    def test_score_content_valid(self):
        """Test content scoring - valid."""
        title = "Valid Article Title"
        body = "This is a valid body. It has multiple sentences. And it is long enough with good content."
        url = "https://example.com/article"

        score, issues = QualityScorer.score_content(title, body, url)

        assert 0.0 <= score <= 1.0
        assert isinstance(issues, list)

    def test_score_content_invalid(self):
        """Test content scoring - invalid."""
        title = ""
        body = ""
        url = "invalid"

        score, issues = QualityScorer.score_content(title, body, url)

        assert score < 1.0
        assert len(issues) > 0

    def test_validate_body_no_sentences(self):
        """Test body validation - no sentences."""
        body = "   "  # Only whitespace, no sentences
        is_valid, error = QualityScorer.validate_body(body)
        assert is_valid is False
        assert error is not None

    def test_validate_url_exception(self):
        """Test URL validation with exception."""
        url = None
        is_valid, error = QualityScorer.validate_url(url)
        assert is_valid is False
        assert error is not None

    def test_validate_url_invalid_scheme(self):
        """Test URL validation - invalid scheme."""
        url = "ftp://example.com/article"
        is_valid, error = QualityScorer.validate_url(url)
        assert is_valid is False
        assert error is not None

    def test_score_content_high_special_chars(self):
        """Test content scoring - high special character ratio."""
        title = "Valid Article Title"
        body = "!@#$%^&*()!@#$%^&*()!@#$%^&*()!@#$%^&*()!@#$%^&*()!@#$%^&*()!@#$%^&*()"
        url = "https://example.com/article"

        score, issues = QualityScorer.score_content(title, body, url)

        # Should have issues about special characters
        assert any("special" in issue.lower() for issue in issues)

    def test_calculate_special_char_ratio_high(self):
        """Test special character ratio calculation - high."""
        text = "!@#$%^&*()!@#$%^&*()"
        ratio = QualityScorer.calculate_special_char_ratio(text)
        assert ratio > 0.5

    def test_calculate_special_char_ratio_low(self):
        """Test special character ratio calculation - low."""
        text = "This is normal text with no special characters"
        ratio = QualityScorer.calculate_special_char_ratio(text)
        assert ratio < 0.1

    def test_score_content_with_language_en(self):
        """Test content scoring with English language."""
        title = "Valid Article Title"
        body = "This is a valid body. It has multiple sentences. And it is long enough with good content."
        url = "https://example.com/article"

        score, issues = QualityScorer.score_content(title, body, url, language="en")

        assert 0.0 <= score <= 1.0

    def test_score_content_with_language_fa(self):
        """Test content scoring with Persian language."""
        title = "عنوان مقاله معتبر"
        body = "این یک متن معتبر است. این متن دارای جملات متعدد است. و این متن به اندازه کافی طولانی است."
        url = "https://example.com/article"

        score, issues = QualityScorer.score_content(title, body, url, language="fa")

        assert 0.0 <= score <= 1.0
