from pydantic_ai import Agent
from pydantic_ai.models.openai import OpenAIChatModel
from pydantic_ai.providers.openai import OpenAIProvider
from pydantic_ai.messages import (
    AgentStreamEvent,
    FinalResultEvent,
    FunctionToolCallEvent,
    FunctionToolResultEvent,
    PartDeltaEvent,
    PartStartEvent,
    TextPartDelta,
    ThinkingPartDelta,
    ToolCallPartDelta,
)
import os
import asyncio
from dotenv import load_dotenv
import logfire
import glob
import difflib

load_dotenv()

logfire.configure()
logfire.instrument_pydantic_ai()

model = OpenAIChatModel(
    os.environ.get('MODEL', 'deepseek-ai/DeepSeek-V3.2-Exp'),
    provider=OpenAIProvider(
        base_url=os.environ.get('BASE_URL', 'https://api.siliconflow.cn/v1'),
        api_key=os.environ['API_KEY']
    ),
)

filter_agent = Agent(
    model,
    instructions=(
        "You are a Wireshark filter generation expert. Your role is to create precise, effective filter strings "
        "for Wireshark/tshark based on user requirements, NOT to analyze packets directly. "
        "Always provide the filter string and explain what it does. "
        "Use fetch_tshark_help and fetch_wireshark_docs to understand filter syntax when needed. "
        "Focus on creating filters for: "
        "- Protocol-specific traffic (HTTP, DNS, TCP, UDP, etc.) "
        "- IP addresses, ports, and network ranges "
        "- Time-based filtering "
        "- Content-based filtering (strings, patterns) "
        "- Security-related patterns (malware, exploits, etc.) "
        "Provide both capture filters (-f) and display filters (-Y) when appropriate. "
        "Explain the difference between capture and display filters. "
        "Always validate your filters make sense for the user's analysis goals."
    )
)

@filter_agent.tool_plain
async def fetch_wireshark_docs(ctx, query: str) -> str:
    """Fetch documentation from the local wireshark_docs folder. Supports exact filename match, full-text search with context and line numbers, and fuzzy matching."""
    docs_dir = os.path.join(os.path.dirname(__file__), 'wireshark_docs')
    if not os.path.exists(docs_dir):
        return "wireshark_docs folder not found."

    if not hasattr(fetch_wireshark_docs, 'docs'):
        fetch_wireshark_docs.docs = {}
        for file_path in glob.glob(os.path.join(docs_dir, '*.html')):
            filename = os.path.basename(file_path)[:-5]  # remove .html
            try:
                with open(file_path, 'r', encoding='utf-8') as f:
                    fetch_wireshark_docs.docs[filename] = f.read()
            except Exception as e:
                continue  # Skip files that can't be read

    docs = fetch_wireshark_docs.docs

    # Exact match
    if query in docs:
        return docs[query][:3000]  # Limit full document return

    # Full-text search with context
    matches = []
    query_lower = query.lower()
    for filename, content in docs.items():
        lines = content.split('\n')
        file_matches = []

        for i, line in enumerate(lines):
            if query_lower in line.lower():
                # Get context around the match
                start_line = max(0, i - 2)  # 2 lines before
                end_line = min(len(lines), i + 3)  # 2 lines after

                context = []
                for j in range(start_line, end_line):
                    marker = "***" if j == i else "   "
                    context.append(f"{marker} {j + 1:4d}: {lines[j]}")

                file_matches.append(f"Match at line {i + 1}:\n" + "\n".join(context))

        if file_matches:
            matches.append(f"From {filename}:\n" + "\n\n".join(file_matches[:2]))  # Limit to 2 matches per file

    if matches:
        result = f"Found matches for '{query}':\n\n"
        result += "\n\n".join(matches[:3])  # Limit to 3 files
        if len(matches) > 3:
            result += f"\n\n... and matches in {len(matches) - 3} more files."
        return result

    # Fuzzy matching on filenames
    close_matches = difflib.get_close_matches(query, docs.keys(), n=3, cutoff=0.6)
    if close_matches:
        result = f"No exact match found. Did you mean one of these?\n"
        for match in close_matches:
            result += f"- {match}\n"
        return result

    return f"No documentation found for query '{query}'."

@filter_agent.tool_plain
async def fetch_tshark_help(ctx, query: str) -> str:
    """Fetch tshark command help from the local tshark manual. Supports full-text search with context, line numbers, and direct line access."""
    docs_dir = os.path.join(os.path.dirname(__file__), 'wireshark_docs')
    tshark_file = os.path.join(docs_dir, 'tshark.html')
    if not os.path.exists(tshark_file):
        return "tshark.html not found in wireshark_docs folder. Please download the tshark manual first."

    try:
        with open(tshark_file, 'r', encoding='utf-8') as f:
            content = f.read()
    except Exception as e:
        return f"Failed to read tshark.html: {str(e)}"

    lines = content.split('\n')

    # Check if query is a line number (integer)
    try:
        line_num = int(query)
        if 1 <= line_num <= len(lines):
            start_line = max(1, line_num - 3)  # Show 3 lines before
            end_line = min(len(lines), line_num + 3)  # Show 3 lines after
            result = f"Lines {start_line}-{end_line} (requested line {line_num}):\n"
            result += "-" * 50 + "\n"
            for i in range(start_line - 1, end_line):
                marker = ">>> " if i + 1 == line_num else "    "
                result += f"{marker}{i + 1:4d}: {lines[i]}\n"
            return result
        else:
            return f"Line number {line_num} is out of range (1-{len(lines)})."
    except ValueError:
        pass  # Not a line number, continue with text search

    # Full-text search with context
    query_lower = query.lower()
    matches = []

    for i, line in enumerate(lines):
        if query_lower in line.lower():
            # Get context around the match
            start_line = max(0, i - 2)  # 2 lines before
            end_line = min(len(lines), i + 3)  # 2 lines after

            context = []
            for j in range(start_line, end_line):
                marker = "***" if j == i else "   "
                context.append(f"{marker} {j + 1:4d}: {lines[j]}")

            matches.append(f"Match at line {i + 1}:\n" + "\n".join(context))

    if matches:
        # Limit to top 3 matches to avoid overwhelming output
        result = f"Found {len(matches)} matches for '{query}':\n\n"
        result += "\n\n".join(matches[:3])
        if len(matches) > 3:
            result += f"\n\n... and {len(matches) - 3} more matches."
        return result[:2000]  # Limit total response length

    # Fuzzy matching on option names (assuming options start with -)
    if query.startswith('-'):
        options = [line.strip() for line in lines if line.strip().startswith('-') and len(line.strip()) > 1]
        close_matches = difflib.get_close_matches(query, options, n=3, cutoff=0.6)
        if close_matches:
            result = f"No exact match for '{query}'. Similar options:\n"
            for match in close_matches:
                result += f"- {match}\n"
            return result

    return f"No help found for '{query}' in tshark manual."

@filter_agent.tool_plain
async def generate_filter(ctx, requirement: str) -> str:
    """Generate appropriate Wireshark/tshark filter strings based on user requirements.

    This tool creates filters for various analysis scenarios:
    - Protocol filtering (HTTP, DNS, TCP, UDP, etc.)
    - IP/Port filtering
    - Time-based filtering
    - Content/pattern matching
    - Security analysis filters

    Returns both capture filters (-f) and display filters (-Y) with explanations.
    """
    # This is a knowledge-based tool that generates filters based on common patterns
    # The agent will use this tool when it needs to create specific filter strings

    requirement_lower = requirement.lower()

    filters = {
        "http": {
            "display": "http",
            "capture": "tcp port 80 or tcp port 443",
            "description": "Filter for HTTP traffic (both HTTP and HTTPS)"
        },
        "https": {
            "display": "tls",
            "capture": "tcp port 443",
            "description": "Filter for HTTPS/TLS traffic"
        },
        "dns": {
            "display": "dns",
            "capture": "udp port 53",
            "description": "Filter for DNS queries and responses"
        },
        "tcp": {
            "display": "tcp",
            "capture": "tcp",
            "description": "Filter for TCP traffic only"
        },
        "udp": {
            "display": "udp",
            "capture": "udp",
            "description": "Filter for UDP traffic only"
        },
        "malware": {
            "display": "http contains \"exe\" or http contains \"dll\" or tcp contains \"MZ\"",
            "capture": "tcp port 80 or tcp port 443",
            "description": "Filter for potential malware downloads (EXE/DLL files)"
        },
        "suspicious": {
            "display": "tcp.flags.reset == 1 or udp or icmp",
            "capture": "tcp or udp or icmp",
            "description": "Filter for potentially suspicious traffic patterns"
        }
    }

    # Try to match the requirement to known patterns
    for key, filter_info in filters.items():
        if key in requirement_lower:
            result = f"**Recommended Filter for: {requirement}**\n\n"
            result += f"**Display Filter (-Y):** `{filter_info['display']}`\n"
            result += f"**Capture Filter (-f):** `{filter_info['capture']}`\n\n"
            result += f"**Description:** {filter_info['description']}\n\n"
            result += "**Usage Examples:**\n"
            result += f"- tshark -r file.pcapng -Y \"{filter_info['display']}\"\n"
            result += f"- tshark -i interface -f \"{filter_info['capture']}\" -w output.pcapng\n"
            return result

    # For custom requirements, provide a template
    result = f"**Custom Filter Generation for: {requirement}**\n\n"
    result += "Based on your requirement, here's a suggested approach:\n\n"

    # Basic template for custom filters
    if "ip" in requirement_lower and ("source" in requirement_lower or "src" in requirement_lower):
        result += "**IP Source Filtering:**\n"
        result += "- Display: `ip.src == 192.168.1.100`\n"
        result += "- Capture: `src host 192.168.1.100`\n\n"
    elif "ip" in requirement_lower and ("destination" in requirement_lower or "dst" in requirement_lower):
        result += "**IP Destination Filtering:**\n"
        result += "- Display: `ip.dst == 192.168.1.100`\n"
        result += "- Capture: `dst host 192.168.1.100`\n\n"
    elif "port" in requirement_lower:
        result += "**Port Filtering:**\n"
        result += "- Display: `tcp.port == 80 or udp.port == 53`\n"
        result += "- Capture: `port 80 or port 443`\n\n"
    elif "time" in requirement_lower or "timestamp" in requirement_lower:
        result += "**Time-based Filtering:**\n"
        result += "- Display: `frame.time >= \"2024-01-01 00:00:00\"`\n"
        result += "- Note: Time filters work best as display filters\n\n"
    else:
        result += "**General Filtering Template:**\n"
        result += "- Display Filter (-Y): `[protocol/field] [operator] [value]`\n"
        result += "- Capture Filter (-f): `[protocol] [host/port/net] [value]`\n\n"

    result += "**Common Operators:**\n"
    result += "- `==` or `eq`: equals\n"
    result += "- `!=` or `ne`: not equals\n"
    result += "- `>` or `gt`: greater than\n"
    result += "- `<` or `lt`: less than\n"
    result += "- `&&` or `and`: logical AND\n"
    result += "- `||` or `or`: logical OR\n"
    result += "- `!` or `not`: logical NOT\n\n"

    result += "**Example Usage:**\n"
    result += "```bash\n"
    result += "# Apply display filter to existing capture\n"
    result += "tshark -r capture.pcapng -Y \"http and ip.src == 192.168.1.100\"\n\n"
    result += "# Use capture filter during live capture\n"
    result += "tshark -i eth0 -f \"tcp port 80\" -w filtered.pcapng\n"
    result += "```"

    return result


if __name__ == '__main__':
    async def event_stream_handler(ctx, event_stream):
        """Handle streaming events to output text in real-time."""
        async for event in event_stream:
            if isinstance(event, PartStartEvent):
                pass  # Part started
            elif isinstance(event, PartDeltaEvent):
                if isinstance(event.delta, TextPartDelta):
                    print(event.delta.content_delta, end='', flush=True)
            elif isinstance(event, FunctionToolCallEvent):
                print(f"\n[Tool Call: {event.part.tool_name}] ", end='', flush=True)
            elif isinstance(event, FunctionToolResultEvent):
                print(f"[Tool Result] ", end='', flush=True)
            elif isinstance(event, FinalResultEvent):
                print()  # New line after final result

    async def main():
        message_history = []
        MAX_HISTORY_LENGTH = 10  # Limit to last 10 messages to save tokens

        print("Welcome to the Wireshark Filter Generator! Type 'quit' or 'exit' to end the conversation.")
        print("I will help you create precise filter strings for Wireshark/tshark analysis.")

        while True:
            try:
                user_input = input("You: ").strip()
                if user_input.lower() in ['quit', 'exit']:
                    print("Goodbye!")
                    break

                print("Filter Agent: ", end='', flush=True)
                result = await filter_agent.run(
                    user_input,
                    message_history=message_history[-MAX_HISTORY_LENGTH:],  # Only use recent history
                    event_stream_handler=event_stream_handler
                )

                # Update message history with new messages from this run
                message_history.extend(result.new_messages())

                # Keep only the most recent messages to prevent token explosion
                if len(message_history) > MAX_HISTORY_LENGTH:
                    message_history = message_history[-MAX_HISTORY_LENGTH:]

            except KeyboardInterrupt:
                print("\nGoodbye!")
                break
            except Exception as e:
                print(f"Error: {e}")
                break

    asyncio.run(main())