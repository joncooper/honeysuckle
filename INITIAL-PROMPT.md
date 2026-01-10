# Project: Honeysuckle - Voice-First Email & Calendar Assistant

**Role:** You are a Principal Systems Engineer and AI Architect specializing in high-concurrency real-time systems, Agentic AI, and Human-in-the-Loop UX.

**Objective:** Scaffold a production-ready voice-first email and calendar assistant using a "Split-Brain" architecture: **OpenAI Realtime API** as the continuous "Receptionist" (low-latency voice interface) and **Claude Agent SDK** as the on-demand "Professor" (deep reasoning and action execution).

---

## 1. Product Vision

Honeysuckle is a voice-first assistant for managing email and calendar. Users interact primarily through natural conversation, with visual UI as a companion that adapts to context.

**Core Capabilities:**
- Triage inbox by voice ("What's important today?")
- Search and read emails ("Find the invoice from Acme")
- Compose and send emails ("Send a quick reply saying I'll be there")
- Check calendar ("What's my afternoon look like?")
- Schedule meetings ("Set up 30 minutes with Sarah tomorrow")
- Smart deferral of complex/risky actions to high-bandwidth contexts

**Example Voice Interactions:**
```
User: "What came in overnight?"
Assistant: "You have 12 new emails. 3 look important: a contract from
           Acme Corp needing review, a meeting reschedule from Sarah,
           and a flight confirmation. Want me to read any of these?"

User: "Read the one from Sarah"
Assistant: "Sarah says: 'Can we move our Thursday sync to Friday 2pm?
           I have a conflict.' Want me to check your Friday and reply?"

User: "Yeah, check Friday and if I'm free, confirm it"
Assistant: "You're free Friday 2-3pm. I'll draft a reply confirming
           the reschedule. I'll send it when you're at your desk so
           you can review first."
```

---

## 2. Multi-Context UX

The system adapts to how and where the user is interacting:

| Context | Visual Output | Audio Output | Input | Considerations |
|---------|---------------|--------------|-------|----------------|
| **AirPods, phone in pocket** | None | Full (primary) | Voice only | Fully audio-navigable. Quick triage, simple replies. Defer complex approvals. |
| **CarPlay** | Minimal (glanceable) | Full (primary) | Voice + preset buttons | Legal/safety constraints. Eyes-on-road. Defer detailed review. |
| **Bluetooth car** | None | Full (primary) | Voice only | Good mic quality. Quick triage. Queue risky operations for desktop. |
| **Desktop** | Full | Optional | Voice + keyboard + mouse | High-throughput. Detailed review, complex composition, risky approvals. |
| **Phone in hand** | Full (mobile) | Full | Voice + touch + gesture | High-throughput. Hybrid voice/touch. Can handle approvals. |

### Context-Aware Delegation Pattern

```
Low-bandwidth contexts              High-bandwidth contexts
(AirPods, CarPlay, BT car)    →     (Desktop, Phone in hand)

• Triage                            • Detailed review
• Quick replies                     • Complex composition
• Simple searches                   • Risky approvals (delete, send-all)
• "Star for later"                  • Bulk operations
• Queue tasks                       • Process queued tasks
```

The system recognizes action risk/complexity and defers appropriately:
- "I'll draft that reply, but let's review it when you're at your desk"
- "That's 47 emails to archive. Want me to queue that for when you can review the list?"

### Implementation Phases

**Phase 1:** Voice-only core (works in all contexts)
**Phase 2:** Desktop companion UI (full inbox, calendar, compose)
**Phase 3:** Mobile adaptive UI + CarPlay integration
**Phase 4:** Cross-device handoff and queue management

---

## 3. Architecture: Split-Brain Pattern

```
┌─────────────────────────────────────────────────────────────────────┐
│                         FastAPI Backend                             │
│                                                                     │
│  ┌──────────────────────┐      ┌──────────────────────────────┐    │
│  │     Receptionist     │      │          Professor           │    │
│  │   (OpenAI Realtime)  │─────▶│    (Claude Agent SDK)        │    │
│  │                      │      │                              │    │
│  │  • Speech-to-speech  │      │  • ClaudeSDKClient           │    │
│  │  • VAD (barge-in)    │      │  • gday CLI (email/calendar) │    │
│  │  • Prosody awareness │      │  • Multi-turn reasoning      │    │
│  │  • Function routing  │      │  • Tool execution            │    │
│  └──────────────────────┘      └──────────────────────────────┘    │
│             │                              │                        │
│             └──────────────┬───────────────┘                        │
│                            ▼                                        │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │                  SessionManager (Supervisor)                  │  │
│  │                                                               │  │
│  │  • Orchestrates Receptionist ↔ Professor handoff              │  │
│  │  • Injects ambient audio during thinking                      │  │
│  │  • Manages voice-based approval flow                          │  │
│  │  • Handles barge-in cancellation                              │  │
│  │  • Maintains conversation state and task queue                │  │
│  └──────────────────────────────────────────────────────────────┘  │
└─────────────────────────────────────────────────────────────────────┘
                                   │
                    WebSocket /ws/audio (bidirectional)
                                   │
┌─────────────────────────────────────────────────────────────────────┐
│                        React Frontend                               │
│                                                                     │
│  Desktop Mode:           │  Mobile Mode:      │  Voice-Only Mode:  │
│  • Full inbox view       │  • Compact inbox   │  • Audio viz only  │
│  • Calendar widget       │  • Touch actions   │  • State indicator │
│  • Compose panel         │  • Swipe gestures  │  • (AirPods/Car)   │
│  • Thoughts log          │                    │                    │
│  • Approval UI           │                    │                    │
└─────────────────────────────────────────────────────────────────────┘
```

### A. The Receptionist (Fast Loop)

**Role:** Low-latency voice interface with prosody and tone awareness.

**Implementation:**
- Persistent WebSocket to OpenAI Realtime API
- Bidirectional audio streaming
- Handles conversational turns, VAD, barge-in detection
- Routes to Professor via function call: `ask_professor(query: str)`

**Why OpenAI Realtime:**
- True speech-to-speech (not STT→LLM→TTS pipeline)
- Prosody and tone awareness
- Native barge-in handling
- Sub-200ms response latency for conversational flow

### B. The Professor (Slow Loop)

**Role:** Deep reasoning, tool execution, and action planning.

**Implementation:**
```python
from claude_agent_sdk import ClaudeSDKClient, ClaudeAgentOptions, HookMatcher

options = ClaudeAgentOptions(
    system_prompt=PROFESSOR_SYSTEM_PROMPT,
    allowed_tools=["Bash"],  # gday CLI access
    hooks={
        "PreToolUse": [
            HookMatcher(matcher="Bash", hooks=[voice_approval_hook])
        ]
    },
    max_turns=10,
)

async with ClaudeSDKClient(options=options) as client:
    await client.query(user_request)
    async for message in client.receive_response():
        # Stream tool use events to frontend
        # Inject ambient audio while processing
        pass
```

**gday Integration:**
The Professor executes email/calendar operations via the `gday` CLI:
```bash
gday mail list --unread --json      # List unread emails
gday mail read <id> --json          # Read specific email
gday mail send --to X --subject Y   # Send email
gday cal today --json               # Today's calendar
gday cal create --quick "..."       # Create event
```

### C. The Supervisor (SessionManager)

**Responsibilities:**

1. **Handoff Orchestration:**
   - Receptionist says "ask_professor" → pause Receptionist output
   - Spin up Professor task
   - Stream Professor results back through Receptionist voice

2. **Ambient Audio Injection:**
   - While Professor is thinking, inject subtle audio feedback
   - Options: soft acknowledgment ("mm-hmm"), gentle tone, or brief verbal status
   - Prevents "dead air" that makes users think connection dropped

3. **Voice-Based Approval Flow:**
   ```python
   async def voice_approval_hook(input_data, tool_use_id, context):
       tool_name = input_data["tool_name"]
       tool_input = input_data["tool_input"]

       # Determine if approval needed based on action risk
       if requires_approval(tool_name, tool_input):
           description = describe_action(tool_name, tool_input)

           # Pause Professor, ask via Receptionist
           approved = await session.request_voice_approval(
               f"I need to {description}. Is that okay?"
           )

           if not approved:
               return {
                   "hookSpecificOutput": {
                       "permissionDecision": "deny",
                       "permissionDecisionReason": "User denied via voice"
                   }
               }
       return {}
   ```

4. **Barge-In Handling:**
   - Frontend sends `vad_start` when user begins speaking
   - If Professor is thinking: cancel task, clear buffers
   - If waiting for approval: interpret as "no" or new command
   - Send `response.cancel` to OpenAI Realtime

5. **Task Queue Management:**
   - Track deferred tasks for high-bandwidth contexts
   - "Review draft on desktop" → queue with context
   - Sync queue state across devices

---

## 4. Tech Stack

### Backend (Python 3.11+)
```toml
# pyproject.toml
[project]
name = "honeysuckle"
version = "0.1.0"
requires-python = ">=3.11"
dependencies = [
    "fastapi>=0.109.0",
    "uvicorn[standard]>=0.27.0",
    "websockets>=12.0",
    "claude-agent-sdk>=0.1.0",
    "openai>=1.12.0",
    "arize-phoenix>=0.0.50",
    "opentelemetry-sdk>=1.22.0",
    "opentelemetry-instrumentation-fastapi>=0.43b0",
    "pydantic>=2.5.0",
    "pydantic-settings>=2.1.0",
]

[build-system]
requires = ["hatchling"]
build-backend = "hatchling.build"

[tool.uv]
dev-dependencies = [
    "pytest>=8.0.0",
    "pytest-asyncio>=0.23.0",
    "ruff>=0.2.0",
]
```

### Frontend (React + Vite + TypeScript)
```json
{
  "name": "honeysuckle-ui",
  "type": "module",
  "dependencies": {
    "react": "^18.2.0",
    "react-dom": "^18.2.0",
    "@radix-ui/react-*": "latest",
    "tailwindcss": "^3.4.0",
    "class-variance-authority": "^0.7.0",
    "clsx": "^2.1.0",
    "tailwind-merge": "^2.2.0"
  },
  "devDependencies": {
    "@types/react": "^18.2.0",
    "@vitejs/plugin-react": "^4.2.0",
    "typescript": "^5.3.0",
    "vite": "^5.0.0"
  }
}
```

### External Dependencies
- `gday` CLI at `~/.local/bin/gday` (Gmail/Calendar operations)
- OpenAI API key (Realtime API access)
- Anthropic API key (Claude Agent SDK)

---

## 5. Directory Structure

```
honeysuckle/
├── backend/
│   ├── pyproject.toml
│   ├── src/
│   │   └── honeysuckle/
│   │       ├── __init__.py
│   │       ├── main.py              # FastAPI app, /ws/audio endpoint
│   │       ├── config.py            # Settings via pydantic-settings
│   │       ├── session/
│   │       │   ├── __init__.py
│   │       │   ├── manager.py       # SessionManager (supervisor)
│   │       │   ├── state.py         # Conversation state, task queue
│   │       │   └── context.py       # UX context detection/management
│   │       ├── receptionist/
│   │       │   ├── __init__.py
│   │       │   ├── client.py        # OpenAI Realtime WebSocket client
│   │       │   ├── audio.py         # Audio buffer management
│   │       │   └── functions.py     # Function definitions (ask_professor)
│   │       ├── professor/
│   │       │   ├── __init__.py
│   │       │   ├── client.py        # Claude Agent SDK wrapper
│   │       │   ├── hooks.py         # Approval hooks, tool interceptors
│   │       │   ├── prompts.py       # System prompts
│   │       │   └── tools.py         # gday tool definitions (future MCP)
│   │       ├── approval/
│   │       │   ├── __init__.py
│   │       │   ├── flow.py          # Voice approval flow
│   │       │   └── risk.py          # Action risk assessment
│   │       └── observability/
│   │           ├── __init__.py
│   │           ├── tracing.py       # OTel spans
│   │           └── phoenix.py       # Arize Phoenix setup
│   └── tests/
│       └── ...
├── frontend/
│   ├── package.json
│   ├── vite.config.ts
│   ├── tailwind.config.js
│   ├── tsconfig.json
│   ├── index.html
│   └── src/
│       ├── main.tsx
│       ├── App.tsx
│       ├── hooks/
│       │   ├── useAudioStream.ts    # WebSocket audio handling
│       │   ├── useVAD.ts            # Voice activity detection
│       │   └── useSession.ts        # Session state
│       ├── components/
│       │   ├── ui/                  # shadcn/ui components
│       │   ├── AudioVisualizer.tsx  # Real-time waveform
│       │   ├── ThoughtsLog.tsx      # Professor's tool use stream
│       │   ├── StateIndicator.tsx   # Listening/Thinking/Approval states
│       │   ├── ApprovalModal.tsx    # Visual approval UI (desktop)
│       │   ├── InboxView.tsx        # Email list (desktop)
│       │   ├── EmailReader.tsx      # Email content (desktop)
│       │   ├── ComposePanel.tsx     # Email composition (desktop)
│       │   └── CalendarWidget.tsx   # Calendar view (desktop)
│       ├── contexts/
│       │   └── SessionContext.tsx
│       └── lib/
│           ├── audio.ts             # Audio utilities
│           └── api.ts               # API client
└── README.md
```

---

## 6. Core Logic: SessionManager

```python
# backend/src/honeysuckle/session/manager.py

import asyncio
from enum import Enum
from dataclasses import dataclass
from typing import AsyncIterator

class SessionState(Enum):
    IDLE = "idle"
    LISTENING = "listening"
    RECEPTIONIST_SPEAKING = "receptionist_speaking"
    PROFESSOR_THINKING = "professor_thinking"
    AWAITING_APPROVAL = "awaiting_approval"

@dataclass
class ApprovalRequest:
    tool_name: str
    tool_input: dict
    description: str
    future: asyncio.Future

class SessionManager:
    """
    Orchestrates the Split-Brain architecture.

    Manages handoff between Receptionist (OpenAI Realtime) and
    Professor (Claude Agent SDK), handles ambient audio, approval
    flows, and barge-in cancellation.
    """

    def __init__(
        self,
        receptionist: ReceptionistClient,
        professor: ProfessorClient,
        audio_sink: AudioSink,
    ):
        self.receptionist = receptionist
        self.professor = professor
        self.audio_sink = audio_sink
        self.state = SessionState.IDLE
        self.professor_task: asyncio.Task | None = None
        self.pending_approval: ApprovalRequest | None = None
        self.task_queue: list[QueuedTask] = []

    async def run(self) -> AsyncIterator[SessionEvent]:
        """Main session loop."""
        async with asyncio.TaskGroup() as tg:
            tg.create_task(self._receptionist_loop())
            tg.create_task(self._vad_monitor())

    async def _receptionist_loop(self):
        """Handle Receptionist events."""
        async for event in self.receptionist.events():
            match event:
                case FunctionCall(name="ask_professor", args=args):
                    await self._invoke_professor(args["query"])

                case TranscriptDelta(text=text):
                    # User speech transcript
                    pass

                case AudioDelta(data=data):
                    # Receptionist audio output
                    await self.audio_sink.write(data)

    async def _invoke_professor(self, query: str):
        """Hand off to Professor for deep reasoning."""
        self.state = SessionState.PROFESSOR_THINKING

        # Start ambient audio
        ambient_task = asyncio.create_task(
            self._ambient_audio_loop()
        )

        try:
            self.professor_task = asyncio.create_task(
                self._run_professor(query)
            )
            result = await self.professor_task

            # Speak result via Receptionist
            await self.receptionist.speak(result)

        except asyncio.CancelledError:
            # Barge-in occurred
            await self.receptionist.speak(
                "Sure, go ahead."
            )
        finally:
            ambient_task.cancel()
            self.professor_task = None
            self.state = SessionState.IDLE

    async def _run_professor(self, query: str) -> str:
        """Execute Professor task with approval hooks."""
        async for event in self.professor.run(query):
            match event:
                case ToolStart(name=name, input=input):
                    # Emit to frontend for Thoughts Log
                    await self._emit_event(event)

                case ApprovalNeeded(tool=tool, input=input, desc=desc):
                    approved = await self._request_approval(
                        tool, input, desc
                    )
                    if not approved:
                        raise PermissionDenied(tool)

                case Result(text=text):
                    return text

    async def _request_approval(
        self,
        tool: str,
        input: dict,
        description: str
    ) -> bool:
        """Request approval via voice."""
        self.state = SessionState.AWAITING_APPROVAL

        # Create future for approval response
        future = asyncio.Future()
        self.pending_approval = ApprovalRequest(
            tool_name=tool,
            tool_input=input,
            description=description,
            future=future,
        )

        # Ask via Receptionist
        await self.receptionist.speak(
            f"I need to {description}. Is that okay?"
        )

        # Wait for voice response
        try:
            return await asyncio.wait_for(future, timeout=30.0)
        except asyncio.TimeoutError:
            return False
        finally:
            self.pending_approval = None
            self.state = SessionState.PROFESSOR_THINKING

    async def _ambient_audio_loop(self):
        """Inject subtle audio feedback during Professor thinking."""
        while True:
            # Option 1: Brief verbal acknowledgment
            # await self.receptionist.speak("mm-hmm", interrupt=False)

            # Option 2: Soft audio cue
            # await self.audio_sink.write(SOFT_CHIME)

            # Option 3: Status update on long operations
            # await self.receptionist.speak("still working on that...")

            await asyncio.sleep(3.0)

    async def handle_vad_start(self):
        """User started speaking - handle barge-in."""
        if self.state == SessionState.PROFESSOR_THINKING:
            # Cancel Professor task
            if self.professor_task:
                self.professor_task.cancel()

        elif self.state == SessionState.AWAITING_APPROVAL:
            # Interpret as response to approval request
            # (actual yes/no determined by Receptionist transcript)
            pass

        # Clear audio buffers
        await self.receptionist.cancel_response()
        await self.audio_sink.clear()

    async def handle_approval_response(self, approved: bool):
        """User responded to approval request."""
        if self.pending_approval:
            self.pending_approval.future.set_result(approved)
```

---

## 7. Observability

Instrument with OpenTelemetry spans for key operations:

```python
# backend/src/honeysuckle/observability/tracing.py

from opentelemetry import trace

tracer = trace.get_tracer("honeysuckle")

# Spans to create:
# - voice_turn: VAD start → VAD end (user speaking)
# - receptionist_response: Query → audio complete
# - professor_invocation: Start → result
# - tool_execution: Tool start → tool end
# - approval_flow: Request → user response
# - approval_latency: Time waiting for user
```

Phoenix integration for development visibility into traces.

---

## 8. Implementation Plan

### Milestone 1: Voice Core (MVP)
**Goal:** Voice conversation that can read emails

Tasks:
- FastAPI WebSocket endpoint (`/ws/audio`)
- OpenAI Realtime client (bidirectional audio streaming)
- Claude Agent SDK integration with gday CLI
- Basic SessionManager (Receptionist → Professor handoff)
- Minimal frontend (audio visualizer + state indicator)

**Done when:** User can ask "What emails do I have?" and hear the response.

### Milestone 2: Safety & Polish
**Goal:** Safe tool execution with voice approval

Tasks:
- Voice-based approval flow via Agent SDK hooks
- Action risk assessment (classify operations by risk level)
- Barge-in handling (cancel Professor on VAD)
- Ambient audio feedback during thinking
- Thoughts Log UI (stream tool use to frontend)

**Done when:** Sending an email requires voice confirmation.

### Milestone 3: Desktop UI
**Goal:** Full desktop companion experience

Tasks:
- Inbox view component
- Email reader component
- Compose panel (with draft preview)
- Calendar widget
- Visual approval modal (for desktop context)

**Done when:** Desktop users have full visual + voice experience.

### Milestone 4: Context & Handoff
**Goal:** Seamless multi-context experience

Tasks:
- UX context detection (how does system know current mode?)
- Task queue (defer actions to high-bandwidth contexts)
- Cross-device state sync
- Mobile-responsive UI

**Done when:** User can start task in car, complete on desktop.

### Milestone 5: CarPlay & Mobile
**Goal:** Full multi-platform support

Tasks:
- CarPlay integration
- iOS app wrapper
- Optimized mobile UI
- Voice-only mode polish

**Done when:** Works seamlessly across all 5 contexts.

---

## 9. Beans Roadmap Setup

After scaffolding the project, populate beans with the roadmap:

```bash
# Create milestones
beans create "Voice Core (MVP)" -t milestone -d "Voice conversation that can read emails"
beans create "Safety & Polish" -t milestone -d "Safe tool execution with voice approval"
beans create "Desktop UI" -t milestone -d "Full desktop companion experience"
beans create "Context & Handoff" -t milestone -d "Seamless multi-context experience"
beans create "CarPlay & Mobile" -t milestone -d "Full multi-platform support"

# Create initial tasks under Milestone 1 (use actual milestone ID)
beans create "FastAPI WebSocket endpoint" -t task --parent <milestone-1-id>
beans create "OpenAI Realtime client" -t task --parent <milestone-1-id>
beans create "Claude Agent SDK integration with gday" -t task --parent <milestone-1-id>
beans create "Basic SessionManager" -t task --parent <milestone-1-id>
beans create "Minimal frontend (audio viz + state)" -t task --parent <milestone-1-id>
```

Run `beans roadmap` to view the project roadmap.
Run `beans tui` for interactive task management.

---

## 10. Open Questions

1. **Ambient audio approach:** Verbal acknowledgments vs. audio cues vs. silence with visual indicator?

2. **Context detection:** Manual toggle? Bluetooth/CarPlay detection? Screen state?

3. **Authentication flow:** How does initial Gmail OAuth happen? Desktop-only setup?

4. **Offline handling:** What happens when network drops mid-conversation?

5. **Wake word:** Always-listening with wake word, or push-to-talk?

---

## 11. Next Steps

Generate the initial scaffolding in this order:

1. **Backend setup:**
   - Create `backend/pyproject.toml` with dependencies
   - Create directory structure per Section 5
   - Stub out `main.py` with FastAPI app and WebSocket endpoint
   - Create `config.py` with pydantic-settings

2. **Frontend setup:**
   - Create `frontend/package.json`
   - Set up Vite + React + TypeScript
   - Configure Tailwind + shadcn/ui
   - Create minimal App with audio visualizer placeholder

3. **Beans roadmap:**
   - Create milestones per Section 9
   - Create initial tasks for Milestone 1
   - Run `beans roadmap` to verify

4. **Core implementation (Milestone 1):**
   - OpenAI Realtime client
   - Claude Agent SDK integration
   - SessionManager skeleton
   - Wire it all together

5. **Update WORKLOG.md** with progress
