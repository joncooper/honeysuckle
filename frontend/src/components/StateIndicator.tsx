import { useSession } from '../contexts/SessionContext'

const stateLabels: Record<string, string> = {
  idle: 'Ready',
  listening: 'Listening...',
  receptionist_speaking: 'Speaking',
  professor_thinking: 'Thinking...',
  awaiting_approval: 'Awaiting Approval',
}

const stateColors: Record<string, string> = {
  idle: 'bg-muted text-muted-foreground',
  listening: 'bg-green-500/20 text-green-400',
  receptionist_speaking: 'bg-blue-500/20 text-blue-400',
  professor_thinking: 'bg-yellow-500/20 text-yellow-400',
  awaiting_approval: 'bg-red-500/20 text-red-400',
}

export function StateIndicator() {
  const {
    state,
    isConnected,
    isRecording,
    connect,
    disconnect,
    startRecording,
    stopRecording,
    sendApproval,
  } = useSession()

  return (
    <div className="flex flex-col items-center gap-4">
      {/* Connection and Recording buttons */}
      <div className="flex gap-3">
        <button
          onClick={isConnected ? disconnect : connect}
          className={`px-6 py-2 rounded-full font-medium transition-colors ${
            isConnected
              ? 'bg-red-500/20 text-red-400 hover:bg-red-500/30'
              : 'bg-green-500/20 text-green-400 hover:bg-green-500/30'
          }`}
        >
          {isConnected ? 'Disconnect' : 'Connect'}
        </button>

        {isConnected && (
          <button
            onClick={isRecording ? stopRecording : startRecording}
            className={`px-6 py-2 rounded-full font-medium transition-colors ${
              isRecording
                ? 'bg-red-500 text-white hover:bg-red-600 animate-pulse'
                : 'bg-blue-500/20 text-blue-400 hover:bg-blue-500/30'
            }`}
          >
            {isRecording ? 'Stop Mic' : 'Start Mic'}
          </button>
        )}
      </div>

      {/* State indicator */}
      <div
        className={`px-4 py-2 rounded-full text-sm font-medium ${
          stateColors[state.phase] || stateColors.idle
        }`}
      >
        {stateLabels[state.phase] || 'Unknown'}
      </div>

      {/* Approval UI */}
      {state.pendingApproval && (
        <div className="mt-4 p-4 bg-muted rounded-lg text-center">
          <p className="mb-3 text-foreground">
            {state.pendingApproval.description}
          </p>
          <div className="flex gap-3 justify-center">
            <button
              onClick={() => sendApproval(true)}
              className="px-4 py-2 bg-green-500 text-white rounded-lg hover:bg-green-600"
            >
              Approve
            </button>
            <button
              onClick={() => sendApproval(false)}
              className="px-4 py-2 bg-red-500 text-white rounded-lg hover:bg-red-600"
            >
              Deny
            </button>
          </div>
        </div>
      )}
    </div>
  )
}
