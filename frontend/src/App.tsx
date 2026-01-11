import { SessionProvider, useSession } from './contexts/SessionContext'
import { AudioVisualizer } from './components/AudioVisualizer'
import { StateIndicator } from './components/StateIndicator'
import { ThoughtsLog } from './components/ThoughtsLog'
import { useThinkingSound } from './hooks/useThinkingSound'

// Component that handles ambient audio feedback
function AmbientFeedback() {
  const { state } = useSession()
  useThinkingSound(state.phase)
  return null
}

function App() {
  return (
    <SessionProvider>
      <AmbientFeedback />
      <div className="min-h-screen bg-background flex flex-col items-center justify-center p-8">
        <h1 className="text-4xl font-bold mb-8 text-foreground">Honeysuckle</h1>

        <div className="flex flex-col items-center gap-6 w-full max-w-2xl">
          {/* State Indicator */}
          <StateIndicator />

          {/* Audio Visualizer */}
          <div className="w-full h-32">
            <AudioVisualizer />
          </div>

          {/* Thoughts Log */}
          <div className="w-full">
            <ThoughtsLog />
          </div>
        </div>

        <p className="mt-8 text-sm text-muted-foreground">
          Voice-first email and calendar assistant
        </p>
      </div>
    </SessionProvider>
  )
}

export default App
