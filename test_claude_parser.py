from aidash.parsers.claude import ClaudeCodeParser

parser = ClaudeCodeParser()
sessions = parser.discover_sessions()

print(f"Total session files found: {len(sessions)}")
print(f"\nFirst 5 files:")
for f in sessions[:5]:
    print(f"  {f}")

if sessions:
    print(f"\nParsing most recent session...")
    session = parser.parse_session(sessions[0])
    print(f"  Session ID: {session.id}")
    print(f"  Project: {session.project}")
    print(f"  Agent: {session.agent}")
    print(f"  Messages: {len(session.messages)}")
    print(f"  Total input tokens: {session.total_input_tokens:,}")
    print(f"  Total output tokens: {session.total_output_tokens:,}")
    print(f"  Start: {session.start_time}")
    print(f"  End: {session.end_time}")

    print(f"\nFirst 3 messages:")
    for msg in session.messages[:3]:
        print(f"  [{msg.role}] {msg.content_preview}")
        if msg.tool_calls:
            for tc in msg.tool_calls:
                print(f"    -> Tool: {tc.name}")
