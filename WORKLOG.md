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
