import { useSession, ThoughtEntry } from '../contexts/SessionContext'

function ThoughtItem({ thought }: { thought: ThoughtEntry }) {
  const timeStr = thought.timestamp.toLocaleTimeString()

  if (thought.type === 'tool_start') {
    return (
      <div className="flex items-start gap-2 text-yellow-400">
        <span className="text-xs text-muted-foreground">{timeStr}</span>
        <span className="font-mono text-sm">
          Running {thought.toolName}...
        </span>
      </div>
    )
  }

  if (thought.type === 'tool_end') {
    return (
      <div className="flex items-start gap-2 text-green-400">
        <span className="text-xs text-muted-foreground">{timeStr}</span>
        <span className="font-mono text-sm truncate" title={thought.content}>
          {thought.toolName} completed
        </span>
      </div>
    )
  }

  return (
    <div className="flex items-start gap-2">
      <span className="text-xs text-muted-foreground">{timeStr}</span>
      <span className="text-sm text-foreground">{thought.content}</span>
    </div>
  )
}

export function ThoughtsLog() {
  const { thoughts } = useSession()

  if (thoughts.length === 0) {
    return (
      <div className="p-4 bg-muted/50 rounded-lg text-center text-muted-foreground text-sm">
        Tool activity will appear here...
      </div>
    )
  }

  return (
    <div className="p-4 bg-muted/50 rounded-lg max-h-48 overflow-y-auto">
      <h3 className="text-xs font-semibold text-muted-foreground mb-2 uppercase tracking-wider">
        Thoughts
      </h3>
      <div className="space-y-1 flex flex-col-reverse">
        {[...thoughts]
          .sort((a, b) => b.timestamp.getTime() - a.timestamp.getTime())
          .slice(0, 10)
          .map((thought) => (
            <ThoughtItem key={thought.id} thought={thought} />
          ))}
      </div>
    </div>
  )
}
