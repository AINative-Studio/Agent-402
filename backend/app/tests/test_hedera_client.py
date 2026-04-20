"""
Tests for HederaClient HCS topic message submission.

Issues #322 (submit_hcs_message) and #327 (submit_topic_message).

TDD Approach: Tests written FIRST, then implementation.
BDD-style: class Describe* / def it_* naming.

Coverage:
- submit_hcs_message returns the full receipt contract
- submit_topic_message is an alias of submit_hcs_message
- dict messages are JSON-encoded; str messages are passed through
- consensus_timestamp uses Hedera "{seconds}.{nanoseconds:09d}" format
- sequence_number is a positive integer

Built by AINative Dev Team
Refs #322, #327
"""
from __future__ import annotations

import json
import re

import pytest


HEDERA_TIMESTAMP_RE = re.compile(r"^\d+\.\d{9}$")
HEDERA_TX_ID_RE = re.compile(r"^\d+\.\d+\.\d+@\d+\.\d{9}$")


class DescribeSubmitHcsMessage:
    """Tests for HederaClient.submit_hcs_message — Issue #322."""

    @pytest.mark.asyncio
    async def it_returns_receipt_with_required_fields(self):
        """Receipt must include all five contract fields."""
        from app.services.hedera_client import HederaClient

        client = HederaClient(operator_id="0.0.12345")
        receipt = await client.submit_hcs_message(
            topic_id="0.0.99999",
            message={"type": "feedback", "rating": 5},
        )

        assert "transaction_id" in receipt
        assert "status" in receipt
        assert "topic_id" in receipt
        assert "sequence_number" in receipt
        assert "consensus_timestamp" in receipt

    @pytest.mark.asyncio
    async def it_echoes_topic_id_in_receipt(self):
        from app.services.hedera_client import HederaClient

        client = HederaClient(operator_id="0.0.12345")
        receipt = await client.submit_hcs_message(
            topic_id="0.0.7777777",
            message={"hello": "world"},
        )
        assert receipt["topic_id"] == "0.0.7777777"

    @pytest.mark.asyncio
    async def it_returns_success_status(self):
        from app.services.hedera_client import HederaClient

        client = HederaClient(operator_id="0.0.12345")
        receipt = await client.submit_hcs_message(
            topic_id="0.0.99999",
            message="hello",
        )
        assert receipt["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def it_returns_positive_sequence_number(self):
        from app.services.hedera_client import HederaClient

        client = HederaClient(operator_id="0.0.12345")
        receipt = await client.submit_hcs_message(
            topic_id="0.0.99999",
            message={"a": 1},
        )
        assert isinstance(receipt["sequence_number"], int)
        assert receipt["sequence_number"] > 0

    @pytest.mark.asyncio
    async def it_returns_hedera_format_consensus_timestamp(self):
        """consensus_timestamp must be a string in '{seconds}.{nanoseconds:09d}' form."""
        from app.services.hedera_client import HederaClient

        client = HederaClient(operator_id="0.0.12345")
        receipt = await client.submit_hcs_message(
            topic_id="0.0.99999",
            message={"a": 1},
        )
        ts = receipt["consensus_timestamp"]
        assert isinstance(ts, str)
        assert HEDERA_TIMESTAMP_RE.match(ts), (
            f"consensus_timestamp must match '{{seconds}}.{{nanoseconds:09d}}', got: {ts!r}"
        )

    @pytest.mark.asyncio
    async def it_returns_hedera_format_transaction_id(self):
        from app.services.hedera_client import HederaClient

        client = HederaClient(operator_id="0.0.12345")
        receipt = await client.submit_hcs_message(
            topic_id="0.0.99999",
            message={"a": 1},
        )
        assert HEDERA_TX_ID_RE.match(receipt["transaction_id"]), (
            f"transaction_id format unexpected: {receipt['transaction_id']!r}"
        )

    @pytest.mark.asyncio
    async def it_accepts_dict_messages(self):
        """dict messages should be JSON-encoded and accepted without error."""
        from app.services.hedera_client import HederaClient

        client = HederaClient(operator_id="0.0.12345")
        receipt = await client.submit_hcs_message(
            topic_id="0.0.99999",
            message={"nested": {"value": 42}, "list": [1, 2, 3]},
        )
        assert receipt["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def it_accepts_string_messages(self):
        from app.services.hedera_client import HederaClient

        client = HederaClient(operator_id="0.0.12345")
        receipt = await client.submit_hcs_message(
            topic_id="0.0.99999",
            message=json.dumps({"already": "encoded"}),
        )
        assert receipt["status"] == "SUCCESS"

    @pytest.mark.asyncio
    async def it_produces_monotonically_increasing_sequence_numbers(self):
        """Repeated submissions to the same topic should advance sequence_number."""
        from app.services.hedera_client import HederaClient

        client = HederaClient(operator_id="0.0.12345")
        first = await client.submit_hcs_message(
            topic_id="0.0.555", message={"i": 1}
        )
        second = await client.submit_hcs_message(
            topic_id="0.0.555", message={"i": 2}
        )
        assert second["sequence_number"] > first["sequence_number"]


class DescribeSubmitTopicMessage:
    """Tests for HederaClient.submit_topic_message — Issue #327.

    submit_topic_message is the OpenConvAI/HCS-10 caller name for the same
    underlying HCS topic submission operation.
    """

    @pytest.mark.asyncio
    async def it_exists_on_hedera_client(self):
        from app.services.hedera_client import HederaClient

        client = HederaClient(operator_id="0.0.12345")
        assert hasattr(client, "submit_topic_message")
        assert callable(client.submit_topic_message)

    @pytest.mark.asyncio
    async def it_returns_same_receipt_shape_as_submit_hcs_message(self):
        from app.services.hedera_client import HederaClient

        client = HederaClient(operator_id="0.0.12345")
        receipt = await client.submit_topic_message(
            topic_id="0.0.5000000",
            message=json.dumps({"protocol": "hcs-10"}),
        )
        for field in (
            "transaction_id",
            "status",
            "topic_id",
            "sequence_number",
            "consensus_timestamp",
        ):
            assert field in receipt, f"missing field: {field}"

    @pytest.mark.asyncio
    async def it_is_an_alias_for_submit_hcs_message(self):
        """submit_topic_message must delegate to submit_hcs_message."""
        from unittest.mock import AsyncMock

        from app.services.hedera_client import HederaClient

        client = HederaClient(operator_id="0.0.12345")
        sentinel = {
            "transaction_id": "0.0.12345@1.000000000",
            "status": "SUCCESS",
            "topic_id": "0.0.5000000",
            "sequence_number": 7,
            "consensus_timestamp": "1.000000000",
        }
        client.submit_hcs_message = AsyncMock(return_value=sentinel)

        result = await client.submit_topic_message(
            topic_id="0.0.5000000", message="hi"
        )

        client.submit_hcs_message.assert_awaited_once_with(
            topic_id="0.0.5000000", message="hi"
        )
        assert result is sentinel


class DescribeGetTopicMessages:
    """Tests for HederaClient.get_topic_messages — required by HCS-10 receive flows.

    Consumed by ``openconvai_messaging_service.receive_messages`` and
    ``openconvai_discovery_service`` — returns submitted HCS messages so
    e2e Tutorial 03 Step 4 (messages retrievable) succeeds.
    """

    @pytest.mark.asyncio
    async def it_exists_on_hedera_client(self):
        from app.services.hedera_client import HederaClient

        client = HederaClient(operator_id="0.0.12345")
        assert hasattr(client, "get_topic_messages")
        assert callable(client.get_topic_messages)

    @pytest.mark.asyncio
    async def it_returns_messages_dict_with_list(self):
        from app.services.hedera_client import HederaClient

        client = HederaClient(operator_id="0.0.12345")
        result = await client.get_topic_messages(topic_id="0.0.empty")
        assert isinstance(result, dict)
        assert "messages" in result
        assert isinstance(result["messages"], list)

    @pytest.mark.asyncio
    async def it_returns_previously_submitted_messages_for_same_topic(self):
        """Submissions to a topic should be retrievable from the same client."""
        import json as _json

        from app.services.hedera_client import HederaClient

        client = HederaClient(operator_id="0.0.12345")
        await client.submit_hcs_message(
            topic_id="0.0.4242", message={"hello": "alice"}
        )
        await client.submit_hcs_message(
            topic_id="0.0.4242", message={"hello": "bob"}
        )

        result = await client.get_topic_messages(topic_id="0.0.4242")
        msgs = result["messages"]
        assert len(msgs) == 2
        for item in msgs:
            assert "message" in item
            assert "sequence_number" in item
            assert "consensus_timestamp" in item
        # Each item["message"] must be JSON-decodable (the format consumers expect).
        decoded = [_json.loads(m["message"]) for m in msgs]
        assert decoded[0] == {"hello": "alice"}
        assert decoded[1] == {"hello": "bob"}

    @pytest.mark.asyncio
    async def it_filters_by_since_sequence(self):
        from app.services.hedera_client import HederaClient

        client = HederaClient(operator_id="0.0.12345")
        for i in range(5):
            await client.submit_hcs_message(
                topic_id="0.0.55", message={"i": i}
            )

        result = await client.get_topic_messages(
            topic_id="0.0.55", since_sequence=2
        )
        seqs = [m["sequence_number"] for m in result["messages"]]
        assert all(s > 2 for s in seqs)
        assert seqs == sorted(seqs)

    @pytest.mark.asyncio
    async def it_respects_limit(self):
        from app.services.hedera_client import HederaClient

        client = HederaClient(operator_id="0.0.12345")
        for i in range(10):
            await client.submit_hcs_message(
                topic_id="0.0.lim", message={"i": i}
            )

        result = await client.get_topic_messages(
            topic_id="0.0.lim", limit=3
        )
        assert len(result["messages"]) == 3

    @pytest.mark.asyncio
    async def it_returns_empty_list_for_unknown_topic(self):
        from app.services.hedera_client import HederaClient

        client = HederaClient(operator_id="0.0.12345")
        result = await client.get_topic_messages(topic_id="0.0.never_used")
        assert result == {"messages": []}
