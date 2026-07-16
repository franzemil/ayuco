from __future__ import annotations

import json
import uuid
from datetime import datetime

import aiosqlite
import structlog

from ayuco.domain.entities.message import Message, Role, ToolCall, ToolResult

log = structlog.get_logger()

SCHEMA = """
CREATE TABLE IF NOT EXISTS messages (
    id TEXT PRIMARY KEY,
    chat_id TEXT NOT NULL,
    role TEXT NOT NULL,
    content TEXT NOT NULL DEFAULT '',
    tool_calls TEXT NOT NULL DEFAULT '[]',
    tool_result TEXT,
    timestamp TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_messages_chat_id ON messages(chat_id);

CREATE TABLE IF NOT EXISTS summaries (
    chat_id TEXT PRIMARY KEY,
    summary TEXT NOT NULL
);
"""


class SQLiteMessageRepository:
    def __init__(self, db_path: str) -> None:
        self._db_path = db_path
        self._db: aiosqlite.Connection | None = None

    async def connect(self) -> None:
        self._db = await aiosqlite.connect(self._db_path)
        self._db.row_factory = aiosqlite.Row
        await self._db.executescript(SCHEMA)
        await self._db.execute("PRAGMA journal_mode=WAL")
        await self._db.commit()
        log.info("sqlite_connected", path=self._db_path)

    async def close(self) -> None:
        if self._db:
            await self._db.close()

    async def add(self, message: Message) -> None:
        assert self._db is not None
        tool_calls_json = json.dumps(
            [{"id": tc.id, "name": tc.name, "arguments": tc.arguments} for tc in message.tool_calls]
        )
        tool_result_json = None
        if message.tool_result:
            tool_result_json = json.dumps(
                {
                    "call_id": message.tool_result.call_id,
                    "content": message.tool_result.content,
                    "is_error": message.tool_result.is_error,
                }
            )
        await self._db.execute(
            "INSERT INTO messages "
            "(id, chat_id, role, content, tool_calls, tool_result, timestamp) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                str(message.id),
                message.chat_id,
                message.role.value,
                message.content,
                tool_calls_json,
                tool_result_json,
                message.timestamp.isoformat(),
            ),
        )
        await self._db.commit()

    async def get_history(self, chat_id: str, limit: int) -> list[Message]:
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT * FROM messages WHERE chat_id = ? ORDER BY timestamp DESC LIMIT ?",
            (chat_id, limit),
        )
        rows = await cursor.fetchall()
        messages = [self._row_to_message(row) for row in reversed(rows)]
        return messages

    async def get_summarized(self, chat_id: str) -> str | None:
        assert self._db is not None
        cursor = await self._db.execute(
            "SELECT summary FROM summaries WHERE chat_id = ?", (chat_id,)
        )
        row = await cursor.fetchone()
        return row["summary"] if row else None

    async def set_summary(self, chat_id: str, summary: str) -> None:
        assert self._db is not None
        await self._db.execute(
            "INSERT OR REPLACE INTO summaries (chat_id, summary) VALUES (?, ?)",
            (chat_id, summary),
        )
        await self._db.commit()

    async def clear(self, chat_id: str) -> None:
        assert self._db is not None
        await self._db.execute("DELETE FROM messages WHERE chat_id = ?", (chat_id,))
        await self._db.execute("DELETE FROM summaries WHERE chat_id = ?", (chat_id,))
        await self._db.commit()

    @staticmethod
    def _row_to_message(row: aiosqlite.Row) -> Message:
        tool_calls_raw = json.loads(row["tool_calls"])
        tool_calls = tuple(
            ToolCall(id=tc["id"], name=tc["name"], arguments=tc["arguments"])
            for tc in tool_calls_raw
        )
        tool_result = None
        if row["tool_result"]:
            tr = json.loads(row["tool_result"])
            tool_result = ToolResult(
                call_id=tr["call_id"],
                content=tr["content"],
                is_error=tr["is_error"],
            )
        return Message(
            id=uuid.UUID(row["id"]),
            chat_id=row["chat_id"],
            role=Role(row["role"]),
            content=row["content"],
            tool_calls=tool_calls,
            tool_result=tool_result,
            timestamp=datetime.fromisoformat(row["timestamp"]),
        )
