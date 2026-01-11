# Honeysuckle Work Log

A running log of work sessions, achievements, architectural decisions, and next steps.

---

## [2025-01-10] Project Initialization

**Achieved:**
- Created `INITIAL-PROMPT.md` with full project specification
- Defined Split-Brain architecture (OpenAI Realtime as Receptionist, Claude Agent SDK as Professor)
- Documented multi-context UX matrix (AirPods, CarPlay, Bluetooth car, Desktop, Phone in hand)
- Established context-aware delegation pattern for low vs high bandwidth contexts
- Initialized beans for task management
- Set up project workflow with WORKLOG.md and CLAUDE.md

**Architectural Decisions:**
- DECISION: Split-Brain architecture with OpenAI Realtime + Claude Agent SDK
- REASON: OpenAI Realtime provides true speech-to-speech with prosody awareness and sub-200ms latency. Claude Agent SDK provides deep reasoning and tool execution. This separation allows each to do what it does best.

- DECISION: Use `gday` CLI for email/calendar operations (not direct API calls)
- REASON: gday already exists and works. Wrap it via Bash tool initially, migrate to MCP tools later if needed for finer control.

- DECISION: Voice-based approval flow using Agent SDK hooks (not `dangerously_skip_permissions`)
- REASON: Safety-critical for email operations. Voice approval maintains the voice-first UX while keeping humans in the loop.

- DECISION: Context-aware deferral of risky actions to high-bandwidth contexts
- REASON: Operations like bulk delete, complex composition, or detailed review should wait for desktop/phone-in-hand contexts where the user can properly review.

**Lessons Learned:**
- Claude Agent SDK is the right choice for embedding Claude in an app (not wrapping Claude Code CLI with PTY)
- The SDK uses hooks for permission control - perfect for voice-based approval flow
- OpenAI Realtime is true speech-to-speech with prosody awareness, not STT→LLM→TTS pipeline
- Bluetooth car mics are typically good quality (user clarification - don't over-engineer noise handling)
- High-risk/complex actions should defer to high-bandwidth contexts (desktop, phone in hand) rather than trying to handle them in voice-only contexts

**Next:**
- Run INITIAL-PROMPT.md to scaffold the project structure
- Set up backend with FastAPI and WebSocket endpoint
- Set up frontend with React/Vite
- Implement basic OpenAI Realtime client

---

## [2026-01-10] Project Scaffolding Complete

**Achieved:**
- Scaffolded complete backend structure per INITIAL-PROMPT.md Section 5
  - `backend/pyproject.toml` with all dependencies (FastAPI, Claude Code SDK, OpenAI, etc.)
  - `backend/src/honeysuckle/main.py` - FastAPI app with `/ws/audio` WebSocket endpoint
  - `backend/src/honeysuckle/config.py` - pydantic-settings configuration
  - `backend/src/honeysuckle/session/` - SessionManager, state, and context detection
  - `backend/src/honeysuckle/receptionist/` - OpenAI Realtime client, audio buffer, functions
  - `backend/src/honeysuckle/professor/` - Claude Agent SDK client, prompts, hooks, tools
  - `backend/src/honeysuckle/approval/` - Voice approval flow and risk assessment
  - `backend/src/honeysuckle/observability/` - OTel tracing and Phoenix setup
- Scaffolded complete frontend structure
  - `frontend/package.json` with React, Vite, Tailwind, Radix UI
  - `frontend/src/App.tsx` - Main app with audio viz, state indicator, thoughts log
  - `frontend/src/contexts/SessionContext.tsx` - Session state management
  - `frontend/src/components/` - AudioVisualizer, StateIndicator, ThoughtsLog
  - `frontend/src/hooks/` - useAudioStream, useVAD, useSession
  - `frontend/src/lib/` - Audio utilities, API client, cn helper
- Created beans milestones for full roadmap:
  - honeysuckle-lrb4: Voice Core (MVP) [todo]
  - honeysuckle-yf92: Safety & Polish [draft]
  - honeysuckle-1nkv: Desktop UI [draft]
  - honeysuckle-lcpy: Mobile UI [draft]
  - honeysuckle-rptc: Context & Handoff [draft]
  - honeysuckle-29s0: CarPlay [draft]
- Created Milestone 1 tasks under Voice Core:
  - honeysuckle-0i08: FastAPI WebSocket endpoint
  - honeysuckle-rch4: OpenAI Realtime client
  - honeysuckle-j7dk: Claude Agent SDK integration with gday
  - honeysuckle-8ku5: Basic SessionManager handoff
  - honeysuckle-ii3m: Minimal frontend with audio viz

**Lessons Learned:**
- The Python SDK is `claude-agent-sdk` from https://github.com/anthropics/claude-agent-sdk-python
- Frontend minimal scaffolding is already functional - AudioVisualizer, StateIndicator, ThoughtsLog all have working implementations
- Risk assessment categorizes gday commands by action type (send=HIGH, archive=MEDIUM, read=LOW)

**Next:**
- Install backend dependencies: `cd backend && uv sync`
- Install frontend dependencies: `cd frontend && bun install`
- Implement OpenAI Realtime client connection (honeysuckle-rch4)
- Wire up SessionManager to route ask_professor to Professor (honeysuckle-8ku5)
- Test end-to-end voice flow with "What emails do I have?"

---

## [2026-01-10] Milestone 1: Voice Core MVP Complete

**Achieved:**
- Implemented full OpenAI Realtime client with bidirectional audio streaming
  - `backend/src/honeysuckle/receptionist/client.py` - WebSocket connection, audio handling, function calls
  - Added system prompt (instructions) to configure Receptionist behavior
- Implemented Claude Agent SDK integration for Professor
  - `backend/src/honeysuckle/professor/client.py` - Uses `query()` function with streaming events
  - Configured with `bypassPermissions` mode (we handle approval ourselves)
  - System prompt guides Professor to use gday CLI for email/calendar
- Wired up SessionManager for full Receptionist → Professor handoff
  - `backend/src/honeysuckle/session/manager.py` - Orchestrates both clients
  - Handles audio forwarding, function call routing, state management
- Updated frontend with real audio streaming
  - `frontend/src/contexts/SessionContext.tsx` - Mic capture, audio playback, WebSocket handling
  - `frontend/src/components/StateIndicator.tsx` - Connect/Disconnect + Start/Stop Mic buttons
- Fixed configuration to find .env at project root
- Disabled Phoenix by default (was blocking startup)

**All Milestone 1 tasks completed:**
- honeysuckle-0i08: FastAPI WebSocket endpoint
- honeysuckle-rch4: OpenAI Realtime client
- honeysuckle-j7dk: Claude Agent SDK integration with gday
- honeysuckle-8ku5: Basic SessionManager handoff
- honeysuckle-ii3m: Minimal frontend with audio viz

**Lessons Learned:**
- Claude Agent SDK uses `query()` for one-shot queries, `ClaudeSDKClient` for interactive sessions
- SDK message types: `AssistantMessage` (with `TextBlock`, `ToolUseBlock`), `ResultMessage`
- OpenAI Realtime uses `instructions` field for system prompt (not `system_prompt`)
- Phoenix tracing can block startup if misconfigured - disabled by default for now

**Next:**
- Test end-to-end: "What emails do I have?" should trigger gday and return results
- Start Milestone 2: Safety & Polish (voice approval, barge-in, ambient feedback)
- Add error handling for OpenAI Realtime connection failures
- Consider adding reconnection logic for dropped connections

---

## [2026-01-10] Milestone 1 Complete - Voice Core Working

**Achieved:**
- End-to-end voice flow working: User can say "What emails do I have?" and hear the response
- Fixed critical concurrency bug: Professor now runs as background task
- Fixed greeting: Uses pattern from OpenAI community - inject user message with instruction
- Fixed audio playback: Resume AudioContext when suspended
- Fixed transcript display: Use complete transcripts not word-by-word deltas
- Added tmux workflow: Dev servers run in split panes, documented in CLAUDE.md

**Architectural Decisions:**
- DECISION: Professor invocation must be non-blocking (`asyncio.create_task`)
- REASON: Blocking the Receptionist event loop causes audio to queue up, resulting in out-of-order playback. Audio must continue flowing while Professor thinks.

- DECISION: Use tmux panes for dev servers instead of background processes
- REASON: Background shell processes create orphaned tasks and are hard to manage. Tmux panes keep output visible and are easy to kill.

**Lessons Learned:**
- **Critical:** Never `await` long operations in the Receptionist event loop - spawn as task
- OpenAI Realtime greeting pattern: Create user message with instruction, then `response.create`
- Browser AudioContext starts suspended - must call `resume()` after user interaction
- Use `response.audio_transcript.done` for complete transcripts, not `.delta` events
- Logging truncates in tmux - filter to relevant events for debugging

**Bugs Fixed:**
- honeysuckle-07i2: Receptionist event loop blocks during Professor invocation

**Known Issues:**
- honeysuckle-6toj: Claude Agent SDK cancel scope error (cosmetic, doesn't break flow)

**Next:**
- Commit this working state
- Start Milestone 2: Safety & Polish
- Enable Phoenix tracing for better observability
- Fix the SDK cancel scope error

---

## [2026-01-10] Phoenix Observability & Barge-in

**Achieved:**
- Phoenix tracing now fully operational with proper parent-child span hierarchy
  - `conversation_turn` parent spans contain nested children
  - `user_utterance`, `receptionist_routing`, `professor_invocation` as child spans
  - Tool executions nested under professor_invocation
- Fixed Phoenix data persistence across restarts (`use_temp_dir=False`, `batch=True`)
- Added Receptionist-tier tracing events: `SpeechStarted`, `SpeechStopped`, `ResponseStarted`, `ResponseDone`
- Implemented working barge-in: user can interrupt and audio stops immediately
  - Backend sends `barge_in` event via WebSocket
  - Frontend tracks active `AudioBufferSourceNode`s and stops them on clear
  - OpenAI response cancelled, Professor task cancelled if running

**Architectural Decisions:**
- DECISION: Model conversation "turns" starting from VAD speech detection
- REASON: In a voice-first app with barge-in, the natural unit of work is "user speaks → system responds". VAD detection (`input_audio_buffer.speech_started`) marks the beginning of a turn, and `response.done` marks the end.

- DECISION: Use OpenTelemetry context propagation for span hierarchy
- REASON: `set_span_in_context()` creates a context that child spans can reference, ensuring proper parent-child relationships in Phoenix UI. Without this, all spans appear flat and disconnected.

**Lessons Learned:**
- Phoenix `px.launch_app()` defaults to `use_temp_dir=True` which loses data on restart - use `use_temp_dir=False` for persistence
- `batch=True` in Phoenix register() uses BatchSpanProcessor for reliable persistence vs SimpleSpanProcessor
- OpenTelemetry span hierarchy requires explicit context passing - spans don't automatically nest
- `tracer.start_span(name, context=parent_context)` creates a child span under the parent
- Web Audio API queues audio buffers - barge-in must stop all active `AudioBufferSourceNode`s, not just stop sending new audio
- OpenAI Realtime `response.cancel` stops the LLM but doesn't clear already-sent audio chunks

**Next:**
- Commit current state
- Consider cleaning up verbose audio logging
- Remove test spans polluting Phoenix UI
- Start Safety & Polish milestone: voice approval flow, ambient feedback sounds
- Fix Claude Agent SDK cancel scope error (honeysuckle-6toj)

---

## [2026-01-10] Session-Level Tracing & Cleanup

**Achieved:**
- Restructured Phoenix tracing with session-level root spans
  - `session` span now encompasses entire WebSocket connection (connect → disconnect)
  - `conversation_turn` spans are children of session
  - `greeting` as session-level child span
  - Turn numbering added for easier debugging
- Added Playwright subagent pattern to CLAUDE.md
  - Playwright MCP tools consume excessive context with accessibility snapshots
  - Rule: always delegate to subagent for substantive browser operations
- Cleaned up repo
  - Deleted unused `useThinkingSound.ts` hook
  - Added `.mcp.json` to gitignore

**Architectural Decisions:**
- DECISION: Session is the root trace, not individual turns
- REASON: A session (mic on → mic off) is the meaningful unit for observability. You want to see everything that happened in one interaction as a single expandable tree, not disconnected turn traces.

- DECISION: Use subagents for Playwright operations
- REASON: Playwright accessibility snapshots are verbose and consume significant context. Delegating to a subagent isolates this, keeps main context clean, and lets the subagent iterate as needed.

**Lessons Learned:**
- Phoenix trace hierarchy must be explicit - spans don't auto-nest based on timing
- Session-level spans require careful lifecycle management (start in `run()`, end in `cleanup()`)
- MCP tools with verbose output (like Playwright) benefit from subagent isolation pattern

**Next:**
- Test session-level tracing with multi-turn conversation
- Clean up verbose audio logging
- Remove test spans polluting Phoenix UI
- Start Safety & Polish milestone: voice approval flow, ambient feedback sounds
- Fix Claude Agent SDK cancel scope error (honeysuckle-6toj)

---

## [2026-01-10] Comprehensive Test Suite for Orchestration

**Achieved:**
- Implemented complete mock-based testing strategy (38 tests, all passing)
- Created Protocol classes for dependency injection in SessionManager
  - `SamClientProtocol` and `FoyleClientProtocol` in `protocols.py`
  - SessionManager now accepts optional injected clients
- Built test infrastructure:
  - `tests/mocks.py` - MockSamClient, MockFoyleClient with event injection
  - `tests/fakes.py` - FakeWebSocket capturing all sent messages
  - `tests/conftest.py` - pytest fixtures composing the test dependencies
- Session Manager tests (`test_session/test_manager.py` - 25 tests):
  - State transitions (IDLE → LISTENING → SAM_SPEAKING → IDLE)
  - Sam → Foyle handoff (ask_foyle triggers Foyle, result sent back)
  - Barge-in handling (cancels Sam response, cancels Foyle task)
  - Event routing (audio, transcripts, tool starts forwarded to WebSocket)
  - Error handling (Sam connect failure, Foyle exceptions)
  - Edge cases (multiple rapid barge-ins, out-of-order events)
  - Status speak debouncing verification
- Tracing tests (`test_observability/test_tracing.py` - 13 tests):
  - Session/turn/foyle_invocation spans created with correct attributes
  - Span parent/child hierarchy verification (greeting→session, turn→session, foyle→turn)
  - Error and cancellation recording in spans
- Renamed "Receptionist" → "Sam" and "Professor" → "Foyle" throughout codebase
  - Based on Foyle's War TV series (Honeysuckle Weeks plays Sam Stewart)
  - Updated README with Foyle's War reference and image

**Architectural Decisions:**
- DECISION: Use Protocol classes for mock injection, not ABC inheritance
- REASON: Python's `typing.Protocol` with `@runtime_checkable` provides structural subtyping - the mock just needs matching methods, no explicit inheritance required. This is more Pythonic and less invasive.

- DECISION: Module-level TracerProvider setup in tracing tests
- REASON: OpenTelemetry's global TracerProvider can only be set once per process. Using per-test fixtures causes warnings and potential issues. Module-level setup with `exporter.clear()` between tests is the recommended pattern.

**Lessons Learned:**
- OpenTelemetry global state requires careful test setup - can't swap TracerProvider per test
- AsyncIterator mocks need explicit generator syntax (`async def ... yield`)
- Async generators that raise exceptions before yielding still need `yield` statement for type checking
- Barge-in during async cleanup can cause state to end up IDLE not LISTENING due to task completion order
- Sleep-based test synchronization works but is inherently flaky - consider `asyncio.Event` for future improvements

**Test Coverage Summary:**
| Category | Tests | Coverage |
|----------|-------|----------|
| State Transitions | 4 | Happy path state machine |
| Sam→Foyle Handoff | 3 | Function call routing, result return |
| Barge-in | 4 | Sam cancel, Foyle cancel, rapid barge-in |
| Event Routing | 4 | Audio, transcript, tool, state events |
| Error Handling | 3 | Connect failure, Foyle exceptions |
| Event Ordering | 3 | Out-of-order events don't crash |
| Debouncing | 1 | Status speak throttling |
| Session Lifecycle | 3 | Connect, greeting, cleanup |
| Span Hierarchy | 3 | Parent/child relationships |
| Tracing Attributes | 7 | Session ID, turn number, input/output |

**Next:**
- Consider parameterized tests to reduce duplication
- Add timeout markers to prevent hung tests
- Clean up verbose audio logging
- Start Safety & Polish milestone: voice approval flow
