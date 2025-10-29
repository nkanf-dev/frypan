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
import subprocess
import asyncio
import os
from dotenv import load_dotenv
import logfire
import glob
import difflib
import shlex

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
agent = Agent(
    model,
    instructions=(
        "注意路径可能是Windows的反斜杠，这时候不要加双引号"
        'MANDATORY WORKFLOW: For ANY tshark command you want to run:'
        'STEP 1: ALWAYS call fetch_tshark_help FIRST to check syntax and options'
        'STEP 2: ONLY THEN call run_tshark with proper arguments (without "tshark" prefix)'
        'FOR LARGE PCAP FILES: Use analyze_large_pcap instead of run_tshark to prevent token overflow'
        'NEVER call run_tshark without first consulting fetch_tshark_help'
        'CRITICAL TSHARK SYNTAX RULES:'
        '- Use -Y for display filters (packet filtering), put the ENTIRE filter expression as ONE quoted argument after -Y'
        '- Use -f for capture filters (interface filtering), put the ENTIRE filter expression as ONE quoted argument after -f'  
        '- NEVER specify display filters both with -Y AND as additional command-line arguments at the end'
        '- Display filter syntax is different from capture filter syntax - display filters use Wireshark syntax'
        '- When reading from file (-r), display filters go with -Y, capture filters go with -f'
        '- Command structure: tshark [options] [filter]'
        '- Options like -T fields -e field1 -e field2 come BEFORE any final filter argument'
        'You are a brilliant pcapng analyser master with deep expertise in network forensics and packet analysis. '
        'You excel at dissecting network packet captures to uncover protocols, traffic patterns, anomalies, and security issues. '
        'When analyzing pcapng files, ALWAYS start by using fetch_tshark_help to understand available options, then use run_tshark for execution. '
        'Provide clear, technical explanations of your findings, including packet details, protocol breakdowns, and actionable insights. '
        'Always prioritize accuracy and thoroughness in your analysis.'
        'REMEMBER: fetch_tshark_help FIRST, THEN run_tshark with arguments only (no "tshark" prefix).'
"""tshark(1) Manual Page
NAME
tshark - Dump and analyze network traffic

SYNOPSIS
tshark [ -i <capture interface>|- ] [ -f <capture filter> ] [ -2 ] [ -r <infile> ] [ -w <outfile>|- ] [ options ] [ <filter> ]

tshark -h|--help

tshark -v|--version
"""
    )
)

@agent.tool_plain
async def run_tshark(ctx, command: str) -> str:
    """Run tshark with the given arguments to analyze network packets. Pass ONLY the tshark arguments (without 'tshark' command itself). Example: '-r file.pcapng -Y http'"""
    tshark_path = os.environ.get('TSHARK_PATH', 'tshark')
    
    # Clean up the command - remove 'tshark' if present at the beginning
    command = command.strip()
    if command.startswith('tshark '):
        command = command[7:].strip()
    elif command.startswith('tshark'):
        command = command[6:].strip()
    
    # Validate that command starts with a proper tshark option
    if not command.startswith(('-r', '-i', '-h', '-v', '--help', '--version')):
        return f"ERROR: Invalid tshark command format. Command must start with a valid tshark option like -r, -i, -h, etc. Got: {command[:50]}..."
    
    try:
        # Use shlex to properly parse the command with quotes
        import shlex
        args = shlex.split(command)
        
        result = await asyncio.create_subprocess_exec(
            tshark_path, *args,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await result.communicate()
        if result.returncode == 0:
            output = stdout.decode()
            
            # Limit output length to prevent token explosion
            MAX_OUTPUT_LENGTH = 4000  # Characters, not tokens
            lines = output.split('\n')
            
            if len(output) > MAX_OUTPUT_LENGTH:
                # Truncate and show summary
                truncated_lines = lines[:50]  # First 50 lines
                summary = f"\n[OUTPUT TRUNCATED - {len(lines)} total lines, showing first 50]\n"
                summary += f"Total output size: {len(output)} characters\n"
                result = '\n'.join(truncated_lines) + summary
            else:
                result = output
            
            print(result)
            return result
        else:
            error_msg = stderr.decode()
            print(error_msg)
            return f"Error: {error_msg}"
    except Exception as e:
        return f"Failed to run tshark: {str(e)}"

@agent.tool_plain
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

@agent.tool_plain
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

@agent.tool_plain
async def analyze_large_pcap(ctx, file_path: str, analysis_type: str = "summary") -> str:
    """Analyze large pcap files efficiently with different analysis modes.
    
    analysis_type options:
    - summary: Basic packet count and protocols
    - http: HTTP traffic analysis
    - dns: DNS queries/responses
    - connections: Network connections summary
    - anomalies: Look for suspicious patterns
    """
    if not os.path.exists(file_path):
        return f"File not found: {file_path}"
    
    tshark_path = os.environ.get('TSHARK_PATH', 'tshark')
    
    commands = {
        "summary": [tshark_path, "-r", file_path, "-q", "-z", "io,phs"],
        "http": [tshark_path, "-r", file_path, "-Y", "http", "-T", "fields", "-e", "frame.number", "-e", "ip.src", "-e", "ip.dst", "-e", "http.request.method", "-e", "http.request.uri", "-e", "http.host"],
        "dns": [tshark_path, "-r", file_path, "-Y", "dns", "-T", "fields", "-e", "frame.number", "-e", "ip.src", "-e", "ip.dst", "-e", "dns.qry.name", "-e", "dns.a"],
        "connections": [tshark_path, "-r", file_path, "-q", "-z", "conv,ip"],
        "anomalies": [tshark_path, "-r", file_path, "-Y", "tcp.flags.reset==1 or udp", "-T", "fields", "-e", "frame.number", "-e", "ip.src", "-e", "ip.dst", "-e", "tcp.flags", "-e", "_ws.col.info"]
    }
    
    if analysis_type not in commands:
        return f"Unknown analysis type: {analysis_type}. Available: {', '.join(commands.keys())}"
    
    try:
        result = await asyncio.create_subprocess_exec(
            *commands[analysis_type],
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )
        stdout, stderr = await result.communicate()
        
        if result.returncode == 0:
            output = stdout.decode()
            
            # For large outputs, provide summary
            lines = output.split('\n')
            if len(lines) > 100:
                summary = f"=== {analysis_type.upper()} ANALYSIS SUMMARY ===\n"
                summary += f"Total lines: {len(lines)}\n"
                summary += f"Output size: {len(output)} characters\n\n"
                summary += "FIRST 20 LINES:\n" + '\n'.join(lines[:20]) + "\n\n"
                summary += "LAST 10 LINES:\n" + '\n'.join(lines[-10:]) + "\n\n"
                summary += "[Use specific queries for detailed analysis of sections]"
                return summary
            else:
                return output
        else:
            error_msg = stderr.decode()
            return f"Error: {error_msg}"
    except Exception as e:
        return f"Failed to analyze pcap: {str(e)}"


if __name__ == '__main__':
    async def event_stream_handler(ctx, event_stream):
        """Handle streaming events to output text in real-time."""
        async for event in event_stream:
            if isinstance(event, PartStartEvent):
                pass  # Part started
            elif isinstance(event, PartDeltaEvent):
                if isinstance(event.delta, TextPartDelta):
                    print(event.delta.content_delta, end='', flush=True)
            elif isinstance(event, FunctionToolCallEvent):32
                print(f"\n[Tool Call: {event.part.tool_name}] ", end='', flush=True)
            elif isinstance(event, FunctionToolResultEvent):
                print(f"[Tool Result] ", end='', flush=True)
            elif isinstance(event, FinalResultEvent):
                print()  # New line after final result

    async def main():
        message_history = []
        MAX_HISTORY_LENGTH = 10  # Limit to last 10 messages to save tokens
        
        print("Welcome to the Pcapng Analyser Chat! Type 'quit' or 'exit' to end the conversation.")
        
        while True:
            try:
                user_input = input("You: ").strip()
                if user_input.lower() in ['quit', 'exit']:
                    print("Goodbye!")
                    break
                
                print("Agent: ", end='', flush=True)
                result = await agent.run(
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