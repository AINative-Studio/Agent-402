"""
Test suite for timestamp validation.

GitHub Issue #39: As a developer, invalid timestamps return clear errors.
Epic 8 Story 3: Invalid timestamps return clear errors.

Requirements:
- Validate timestamp format (ISO8601)
- Invalid timestamps must return HTTP 422
- Error response must include error_code: "INVALID_TIMESTAMP"
- Error response must include "detail" field with clear message
- Follow PRD §10 for determinism
- Show expected format in error message (ISO8601)
- Provide examples of valid timestamps

Test Coverage:
1. Valid ISO8601 timestamp formats
2. Invalid timestamp formats
3. Missing timestamps
4. Empty/whitespace timestamps
5. Non-string timestamps
6. Edge cases (malformed dates, times, timezones)
7. Error response format validation
8. DX Contract compliance
"""
import pytest
from datetime import datetime
from app.core.timestamp_validator import (
    is_valid_iso8601,
    validate_timestamp,
    parse_timestamp,
    get_current_timestamp_iso8601,
    get_timestamp_error_message,
    TIMESTAMP_EXAMPLES
)
from app.core.errors import InvalidTimestampError


class TestValidISO8601Formats:
    """Test valid ISO8601 timestamp formats are accepted."""

    def test_valid_utc_with_z_suffix(self):
        """Test UTC timestamp with Z suffix."""
        timestamp = "2026-01-10T12:34:56Z"
        assert is_valid_iso8601(timestamp) is True
        assert validate_timestamp(timestamp) == timestamp

    def test_valid_utc_with_milliseconds(self):
        """Test UTC timestamp with milliseconds."""
        timestamp = "2026-01-10T12:34:56.789Z"
        assert is_valid_iso8601(timestamp) is True
        assert validate_timestamp(timestamp) == timestamp

    def test_valid_utc_with_microseconds(self):
        """Test UTC timestamp with microseconds."""
        timestamp = "2026-01-10T12:34:56.123456Z"
        assert is_valid_iso8601(timestamp) is True
        assert validate_timestamp(timestamp) == timestamp

    def test_valid_positive_timezone_offset(self):
        """Test timestamp with positive timezone offset."""
        timestamp = "2026-01-10T12:34:56+05:30"
        assert is_valid_iso8601(timestamp) is True
        assert validate_timestamp(timestamp) == timestamp

    def test_valid_negative_timezone_offset(self):
        """Test timestamp with negative timezone offset."""
        timestamp = "2026-01-10T12:34:56-08:00"
        assert is_valid_iso8601(timestamp) is True
        assert validate_timestamp(timestamp) == timestamp

    def test_valid_utc_zero_offset(self):
        """Test timestamp with +00:00 timezone."""
        timestamp = "2026-01-10T12:34:56+00:00"
        assert is_valid_iso8601(timestamp) is True
        assert validate_timestamp(timestamp) == timestamp

    def test_valid_with_milliseconds_and_offset(self):
        """Test timestamp with milliseconds and timezone offset."""
        timestamp = "2026-01-10T12:34:56.789+00:00"
        assert is_valid_iso8601(timestamp) is True
        assert validate_timestamp(timestamp) == timestamp

    def test_parse_valid_timestamps(self):
        """Test parsing valid timestamps to datetime objects."""
        timestamp = "2026-01-10T12:34:56Z"
        dt = parse_timestamp(timestamp)
        assert isinstance(dt, datetime)
        assert dt.year == 2026
        assert dt.month == 1
        assert dt.day == 10
        assert dt.hour == 12
        assert dt.minute == 34
        assert dt.second == 56


class TestInvalidTimestampFormats:
    """Test invalid timestamp formats are rejected."""

    def test_invalid_missing_timezone(self):
        """Test timestamp without timezone is rejected."""
        timestamp = "2026-01-10T12:34:56"
        assert is_valid_iso8601(timestamp) is False
        with pytest.raises(ValueError) as exc_info:
            validate_timestamp(timestamp)
        assert "Invalid timestamp format" in str(exc_info.value)
        assert "ISO8601" in str(exc_info.value)

    def test_invalid_date_only(self):
        """Test date-only format is rejected."""
        timestamp = "2026-01-10"
        assert is_valid_iso8601(timestamp) is False
        with pytest.raises(ValueError) as exc_info:
            validate_timestamp(timestamp)
        assert "Invalid timestamp format" in str(exc_info.value)

    def test_invalid_time_only(self):
        """Test time-only format is rejected."""
        timestamp = "12:34:56Z"
        assert is_valid_iso8601(timestamp) is False
        with pytest.raises(ValueError) as exc_info:
            validate_timestamp(timestamp)
        assert "Invalid timestamp format" in str(exc_info.value)

    def test_invalid_malformed_date(self):
        """Test malformed date is rejected."""
        timestamp = "2026-13-40T12:34:56Z"  # Invalid month and day
        assert is_valid_iso8601(timestamp) is False
        with pytest.raises(ValueError) as exc_info:
            validate_timestamp(timestamp)
        assert "Invalid timestamp format" in str(exc_info.value)

    def test_invalid_malformed_time(self):
        """Test malformed time is rejected."""
        timestamp = "2026-01-10T25:70:90Z"  # Invalid hour, minute, second
        assert is_valid_iso8601(timestamp) is False
        with pytest.raises(ValueError) as exc_info:
            validate_timestamp(timestamp)
        assert "Invalid timestamp format" in str(exc_info.value)

    def test_invalid_wrong_separator(self):
        """Test wrong date-time separator is rejected."""
        timestamp = "2026-01-10 12:34:56Z"  # Space instead of T
        assert is_valid_iso8601(timestamp) is False
        with pytest.raises(ValueError) as exc_info:
            validate_timestamp(timestamp)
        assert "Invalid timestamp format" in str(exc_info.value)

    def test_invalid_unix_timestamp(self):
        """Test Unix timestamp format is rejected."""
        timestamp = "1704891296"
        assert is_valid_iso8601(timestamp) is False
        with pytest.raises(ValueError) as exc_info:
            validate_timestamp(timestamp)
        assert "Invalid timestamp format" in str(exc_info.value)

    def test_invalid_human_readable(self):
        """Test human-readable format is rejected."""
        timestamp = "January 10, 2026 12:34:56"
        assert is_valid_iso8601(timestamp) is False
        with pytest.raises(ValueError) as exc_info:
            validate_timestamp(timestamp)
        assert "Invalid timestamp format" in str(exc_info.value)

    def test_invalid_random_string(self):
        """Test random string is rejected."""
        timestamp = "not-a-timestamp"
        assert is_valid_iso8601(timestamp) is False
        with pytest.raises(ValueError) as exc_info:
            validate_timestamp(timestamp)
        assert "Invalid timestamp format" in str(exc_info.value)


class TestTimestampEdgeCases:
    """Test edge cases for timestamp validation."""

    def test_missing_timestamp_none(self):
        """Test None timestamp is rejected with clear message."""
        with pytest.raises(ValueError) as exc_info:
            validate_timestamp(None)
        error_msg = str(exc_info.value)
        assert "Missing required field" in error_msg
        assert "ISO8601" in error_msg
        assert "Examples:" in error_msg

    def test_empty_string_timestamp(self):
        """Test empty string timestamp is rejected."""
        with pytest.raises(ValueError) as exc_info:
            validate_timestamp("")
        error_msg = str(exc_info.value)
        assert "Empty timestamp" in error_msg
        assert "ISO8601" in error_msg

    def test_whitespace_only_timestamp(self):
        """Test whitespace-only timestamp is rejected."""
        with pytest.raises(ValueError) as exc_info:
            validate_timestamp("   ")
        error_msg = str(exc_info.value)
        assert "Empty timestamp" in error_msg
        assert "ISO8601" in error_msg

    def test_non_string_timestamp_integer(self):
        """Test integer timestamp is rejected."""
        with pytest.raises(ValueError) as exc_info:
            validate_timestamp(1704891296)
        error_msg = str(exc_info.value)
        assert "Invalid timestamp type" in error_msg
        assert "expected string" in error_msg
        assert "got int" in error_msg

    def test_non_string_timestamp_datetime(self):
        """Test datetime object is rejected (must be string)."""
        with pytest.raises(ValueError) as exc_info:
            validate_timestamp(datetime.now())
        error_msg = str(exc_info.value)
        assert "Invalid timestamp type" in error_msg
        assert "expected string" in error_msg

    def test_timestamp_with_leading_whitespace(self):
        """Test timestamp with leading whitespace is accepted after strip."""
        timestamp = "  2026-01-10T12:34:56Z"
        result = validate_timestamp(timestamp)
        assert result == "2026-01-10T12:34:56Z"

    def test_timestamp_with_trailing_whitespace(self):
        """Test timestamp with trailing whitespace is accepted after strip."""
        timestamp = "2026-01-10T12:34:56Z  "
        result = validate_timestamp(timestamp)
        assert result == "2026-01-10T12:34:56Z"

    def test_custom_field_name_in_error(self):
        """Test custom field name appears in error message."""
        with pytest.raises(ValueError) as exc_info:
            validate_timestamp("invalid", field_name="created_at")
        error_msg = str(exc_info.value)
        assert "created_at" in error_msg


class TestErrorMessageFormat:
    """Test error message format and content."""

    def test_error_message_includes_examples(self):
        """Test error messages include valid timestamp examples."""
        with pytest.raises(ValueError) as exc_info:
            validate_timestamp("invalid")
        error_msg = str(exc_info.value)
        # Should include examples from TIMESTAMP_EXAMPLES
        assert "2026-01-10T12:34:56Z" in error_msg or "Examples:" in error_msg

    def test_error_message_includes_iso8601(self):
        """Test error messages mention ISO8601."""
        with pytest.raises(ValueError) as exc_info:
            validate_timestamp("invalid")
        error_msg = str(exc_info.value)
        assert "ISO8601" in error_msg

    def test_error_message_includes_invalid_value(self):
        """Test error message includes the invalid value provided."""
        invalid_timestamp = "2026-99-99T99:99:99Z"
        with pytest.raises(ValueError) as exc_info:
            validate_timestamp(invalid_timestamp)
        error_msg = str(exc_info.value)
        assert invalid_timestamp in error_msg

    def test_get_timestamp_error_message_helper(self):
        """Test timestamp error message helper function."""
        msg = get_timestamp_error_message("my_field", "bad_value")
        assert "my_field" in msg
        assert "bad_value" in msg
        assert "ISO8601" in msg
        assert any(example in msg for example in TIMESTAMP_EXAMPLES)


class TestInvalidTimestampError:
    """Test InvalidTimestampError exception class."""

    def test_invalid_timestamp_error_default_message(self):
        """Test InvalidTimestampError with default message."""
        error = InvalidTimestampError()
        assert error.status_code == 422
        assert error.error_code == "INVALID_TIMESTAMP"
        assert "ISO8601" in error.detail
        assert "Examples:" in error.detail or "2026-01-10T12:34:56Z" in error.detail

    def test_invalid_timestamp_error_custom_message(self):
        """Test InvalidTimestampError with custom message."""
        custom_msg = "Custom timestamp error message"
        error = InvalidTimestampError(detail=custom_msg)
        assert error.status_code == 422
        assert error.error_code == "INVALID_TIMESTAMP"
        assert error.detail == custom_msg

    def test_invalid_timestamp_error_format(self):
        """Test error follows DX Contract format."""
        error = InvalidTimestampError()
        # Error should have error_code attribute
        assert hasattr(error, 'error_code')
        assert error.error_code == "INVALID_TIMESTAMP"
        # Error should have detail attribute
        assert hasattr(error, 'detail')
        assert isinstance(error.detail, str)
        assert len(error.detail) > 0


class TestTimestampUtilities:
    """Test timestamp utility functions."""

    def test_get_current_timestamp_format(self):
        """Test current timestamp is in correct ISO8601 format."""
        timestamp = get_current_timestamp_iso8601()
        assert isinstance(timestamp, str)
        assert timestamp.endswith('Z')
        assert is_valid_iso8601(timestamp) is True

    def test_get_current_timestamp_parseable(self):
        """Test current timestamp can be parsed."""
        timestamp = get_current_timestamp_iso8601()
        dt = parse_timestamp(timestamp)
        assert isinstance(dt, datetime)

    def test_timestamp_examples_are_valid(self):
        """Test all example timestamps are valid."""
        for example in TIMESTAMP_EXAMPLES:
            assert is_valid_iso8601(example) is True, f"Example {example} should be valid"


class TestDeterminism:
    """Test deterministic behavior per PRD §10."""

    def test_same_valid_input_same_output(self):
        """Test same valid input always produces same output."""
        timestamp = "2026-01-10T12:34:56Z"
        result1 = validate_timestamp(timestamp)
        result2 = validate_timestamp(timestamp)
        result3 = validate_timestamp(timestamp)
        assert result1 == result2 == result3

    def test_same_invalid_input_same_error(self):
        """Test same invalid input always produces same error."""
        invalid = "not-a-timestamp"
        errors = []
        for _ in range(3):
            try:
                validate_timestamp(invalid)
            except ValueError as e:
                errors.append(str(e))

        assert len(errors) == 3
        assert errors[0] == errors[1] == errors[2]

    def test_validation_is_repeatable(self):
        """Test validation is repeatable and deterministic."""
        test_cases = [
            ("2026-01-10T12:34:56Z", True),
            ("2026-01-10T12:34:56.789Z", True),
            ("invalid", False),
            ("2026-01-10", False),
            ("", False)
        ]

        for timestamp, should_be_valid in test_cases:
            # Run same validation multiple times
            for _ in range(5):
                if should_be_valid:
                    result = is_valid_iso8601(timestamp)
                    assert result is True
                else:
                    result = is_valid_iso8601(timestamp)
                    assert result is False
