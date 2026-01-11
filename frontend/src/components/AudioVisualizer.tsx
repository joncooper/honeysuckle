import { useEffect, useRef } from 'react'
import { useSession } from '../contexts/SessionContext'

export function AudioVisualizer() {
  const { state, isConnected } = useSession()
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const animationRef = useRef<number>()

  useEffect(() => {
    const canvas = canvasRef.current
    if (!canvas) return

    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const resize = () => {
      canvas.width = canvas.offsetWidth * window.devicePixelRatio
      canvas.height = canvas.offsetHeight * window.devicePixelRatio
    }
    resize()
    window.addEventListener('resize', resize)

    const draw = () => {
      const width = canvas.width
      const height = canvas.height

      // Clear canvas
      ctx.fillStyle = 'hsl(222.2, 84%, 4.9%)'
      ctx.fillRect(0, 0, width, height)

      // Draw visualization based on state
      const centerY = height / 2
      const barCount = 32
      const barWidth = (width / barCount) * 0.8
      const barGap = (width / barCount) * 0.2

      for (let i = 0; i < barCount; i++) {
        const x = i * (barWidth + barGap) + barGap / 2

        // Generate height based on state
        let barHeight: number
        let color: string

        if (!isConnected) {
          // Disconnected - flat line
          barHeight = 4
          color = 'hsl(215, 20.2%, 35%)'
        } else if (state.phase === 'idle') {
          // Idle - subtle ambient motion
          barHeight = 10 + Math.sin(Date.now() / 500 + i * 0.3) * 5
          color = 'hsl(215, 20.2%, 45%)'
        } else if (state.phase === 'listening') {
          // Listening - active waveform
          barHeight = 20 + Math.sin(Date.now() / 100 + i * 0.5) * 30 + Math.random() * 20
          color = 'hsl(142, 71%, 45%)'
        } else if (state.phase === 'sam_speaking') {
          // Sam speaking - smooth wave
          barHeight = 30 + Math.sin(Date.now() / 150 + i * 0.4) * 40
          color = 'hsl(210, 40%, 60%)'
        } else if (state.phase === 'foyle_thinking') {
          // Foyle thinking - pulsing
          const pulse = Math.sin(Date.now() / 300) * 0.3 + 0.7
          barHeight = 25 * pulse + Math.sin(i * 0.5) * 10
          color = 'hsl(45, 93%, 47%)'
        } else if (state.phase === 'awaiting_approval') {
          // Awaiting - steady pulse
          const pulse = Math.sin(Date.now() / 500) * 0.2 + 0.8
          barHeight = 35 * pulse
          color = 'hsl(0, 84%, 60%)'
        } else {
          barHeight = 10
          color = 'hsl(215, 20.2%, 45%)'
        }

        ctx.fillStyle = color
        ctx.fillRect(x, centerY - barHeight / 2, barWidth, barHeight)
      }

      animationRef.current = requestAnimationFrame(draw)
    }

    draw()

    return () => {
      window.removeEventListener('resize', resize)
      if (animationRef.current) {
        cancelAnimationFrame(animationRef.current)
      }
    }
  }, [state.phase, isConnected])

  return (
    <canvas
      ref={canvasRef}
      className="w-full h-full rounded-lg"
      style={{ imageRendering: 'pixelated' }}
    />
  )
}
