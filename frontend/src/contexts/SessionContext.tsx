import {
  createContext,
  useContext,
  useEffect,
  useState,
  useRef,
  useCallback,
  ReactNode,
} from 'react'
import { createAudioPlayer } from '../lib/audio'

export type SessionPhase =
  | 'idle'
  | 'listening'
  | 'receptionist_speaking'
  | 'professor_thinking'
  | 'awaiting_approval'

export interface SessionState {
  phase: SessionPhase
  pendingApproval: {
    toolName: string
    description: string
  } | null
  queuedTasksCount: number
}

export interface ThoughtEntry {
  id: string
  type: 'tool_start' | 'tool_end' | 'text' | 'transcript'
  toolName?: string
  content: string
  timestamp: Date
}

interface SessionContextValue {
  state: SessionState
  thoughts: ThoughtEntry[]
  isConnected: boolean
  isRecording: boolean
  connect: () => void
  disconnect: () => void
  startRecording: () => Promise<void>
  stopRecording: () => void
  sendApproval: (approved: boolean) => void
}

const defaultState: SessionState = {
  phase: 'idle',
  pendingApproval: null,
  queuedTasksCount: 0,
}

const SessionContext = createContext<SessionContextValue | null>(null)

export function useSession() {
  const context = useContext(SessionContext)
  if (!context) {
    throw new Error('useSession must be used within a SessionProvider')
  }
  return context
}

interface SessionProviderProps {
  children: ReactNode
}

export function SessionProvider({ children }: SessionProviderProps) {
  const [state, setState] = useState<SessionState>(defaultState)
  const [thoughts, setThoughts] = useState<ThoughtEntry[]>([])
  const [isConnected, setIsConnected] = useState(false)
  const [isRecording, setIsRecording] = useState(false)

  const wsRef = useRef<WebSocket | null>(null)
  const audioContextRef = useRef<AudioContext | null>(null)
  const streamRef = useRef<MediaStream | null>(null)
  const processorRef = useRef<ScriptProcessorNode | null>(null)
  const audioPlayerRef = useRef<ReturnType<typeof createAudioPlayer> | null>(null)

  const connect = useCallback(() => {
    if (wsRef.current) return

    const protocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
    const socket = new WebSocket(`${protocol}//${window.location.host}/ws/audio`)

    socket.binaryType = 'arraybuffer'

    socket.onopen = () => {
      setIsConnected(true)
      audioPlayerRef.current = createAudioPlayer(24000)
      console.log('WebSocket connected')
    }

    socket.onclose = () => {
      setIsConnected(false)
      wsRef.current = null
      audioPlayerRef.current?.close()
      audioPlayerRef.current = null
      console.log('WebSocket disconnected')
    }

    socket.onerror = (error) => {
      console.error('WebSocket error:', error)
    }

    socket.onmessage = (event) => {
      if (event.data instanceof ArrayBuffer) {
        // Audio data from server - play it
        const pcm16 = new Int16Array(event.data)
        audioPlayerRef.current?.play(pcm16)
      } else if (typeof event.data === 'string') {
        const message = JSON.parse(event.data)
        handleMessage(message)
      }
    }

    wsRef.current = socket
  }, [])

  const disconnect = useCallback(() => {
    stopRecording()
    wsRef.current?.close()
    wsRef.current = null
  }, [])

  const handleMessage = (message: Record<string, unknown>) => {
    switch (message.type) {
      case 'state':
        setState({
          phase: (message.state as Record<string, unknown>)?.phase as SessionPhase ?? 'idle',
          pendingApproval: (message.state as Record<string, unknown>)?.pending_approval
            ? {
                toolName: ((message.state as Record<string, unknown>).pending_approval as Record<string, string>).tool_name,
                description: ((message.state as Record<string, unknown>).pending_approval as Record<string, string>).description,
              }
            : null,
          queuedTasksCount: (message.state as Record<string, unknown>)?.queued_tasks_count as number ?? 0,
        })
        break

      case 'tool_start':
        setThoughts((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            type: 'tool_start',
            toolName: message.tool as string,
            content: `Running ${message.tool}...`,
            timestamp: new Date(),
          },
        ])
        break

      case 'tool_end':
        setThoughts((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            type: 'tool_end',
            toolName: message.tool as string,
            content: message.output as string,
            timestamp: new Date(),
          },
        ])
        break

      case 'text':
        setThoughts((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            type: 'text',
            content: message.content as string,
            timestamp: new Date(),
          },
        ])
        break

      case 'transcript':
        setThoughts((prev) => [
          ...prev,
          {
            id: crypto.randomUUID(),
            type: 'transcript',
            content: `[${message.role}] ${message.text}`,
            timestamp: new Date(),
          },
        ])
        break

      case 'barge_in':
        // User interrupted - clear audio buffer immediately
        audioPlayerRef.current?.clear()
        break

      case 'error':
        console.error('Server error:', message.message)
        break
    }
  }

  const startRecording = useCallback(async () => {
    if (!wsRef.current || isRecording) return

    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: {
          channelCount: 1,
          sampleRate: 24000,
          echoCancellation: true,
          noiseSuppression: true,
        },
      })
      streamRef.current = stream

      const audioContext = new AudioContext({ sampleRate: 24000 })
      audioContextRef.current = audioContext

      const source = audioContext.createMediaStreamSource(stream)
      const processor = audioContext.createScriptProcessor(4096, 1, 1)
      processorRef.current = processor

      processor.onaudioprocess = (event) => {
        if (!wsRef.current || wsRef.current.readyState !== WebSocket.OPEN) return

        const float32 = event.inputBuffer.getChannelData(0)
        // Convert Float32 to PCM16
        const pcm16 = new Int16Array(float32.length)
        for (let i = 0; i < float32.length; i++) {
          const s = Math.max(-1, Math.min(1, float32[i]))
          pcm16[i] = s < 0 ? s * 0x8000 : s * 0x7fff
        }
        wsRef.current.send(pcm16.buffer)
      }

      source.connect(processor)
      processor.connect(audioContext.destination)

      setIsRecording(true)
    } catch (error) {
      console.error('Failed to start recording:', error)
    }
  }, [isRecording])

  const stopRecording = useCallback(() => {
    if (processorRef.current) {
      processorRef.current.disconnect()
      processorRef.current = null
    }

    if (streamRef.current) {
      streamRef.current.getTracks().forEach((track) => track.stop())
      streamRef.current = null
    }

    if (audioContextRef.current) {
      audioContextRef.current.close()
      audioContextRef.current = null
    }

    setIsRecording(false)
  }, [])

  const sendApproval = useCallback((approved: boolean) => {
    wsRef.current?.send(
      JSON.stringify({
        type: 'approval_response',
        approved,
      })
    )
  }, [])

  // Clean up on unmount
  useEffect(() => {
    return () => {
      stopRecording()
      wsRef.current?.close()
    }
  }, [stopRecording])

  const value: SessionContextValue = {
    state,
    thoughts,
    isConnected,
    isRecording,
    connect,
    disconnect,
    startRecording,
    stopRecording,
    sendApproval,
  }

  return (
    <SessionContext.Provider value={value}>{children}</SessionContext.Provider>
  )
}
