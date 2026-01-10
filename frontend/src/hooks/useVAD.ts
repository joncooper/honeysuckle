import { useRef, useCallback, useState } from 'react'

interface UseVADOptions {
  /**
   * Threshold for voice detection (0-1).
   * Higher values require louder speech to trigger.
   */
  threshold?: number

  /**
   * Duration in ms of silence before considering speech ended.
   */
  silenceDuration?: number

  /**
   * Callback when voice activity starts.
   */
  onVoiceStart?: () => void

  /**
   * Callback when voice activity ends.
   */
  onVoiceEnd?: () => void
}

export function useVAD(options: UseVADOptions = {}) {
  const {
    threshold = 0.01,
    silenceDuration = 500,
    onVoiceStart,
    onVoiceEnd,
  } = options

  const [isVoiceActive, setIsVoiceActive] = useState(false)
  const silenceTimerRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const wasActiveRef = useRef(false)

  const processAudioFrame = useCallback(
    (audioData: Float32Array) => {
      // Calculate RMS (root mean square) energy
      let sum = 0
      for (let i = 0; i < audioData.length; i++) {
        sum += audioData[i] * audioData[i]
      }
      const rms = Math.sqrt(sum / audioData.length)

      const isActive = rms > threshold

      if (isActive) {
        // Voice detected
        if (silenceTimerRef.current) {
          clearTimeout(silenceTimerRef.current)
          silenceTimerRef.current = null
        }

        if (!wasActiveRef.current) {
          wasActiveRef.current = true
          setIsVoiceActive(true)
          onVoiceStart?.()
        }
      } else {
        // Silence
        if (wasActiveRef.current && !silenceTimerRef.current) {
          silenceTimerRef.current = setTimeout(() => {
            wasActiveRef.current = false
            setIsVoiceActive(false)
            onVoiceEnd?.()
            silenceTimerRef.current = null
          }, silenceDuration)
        }
      }
    },
    [threshold, silenceDuration, onVoiceStart, onVoiceEnd]
  )

  const reset = useCallback(() => {
    if (silenceTimerRef.current) {
      clearTimeout(silenceTimerRef.current)
      silenceTimerRef.current = null
    }
    wasActiveRef.current = false
    setIsVoiceActive(false)
  }, [])

  return {
    isVoiceActive,
    processAudioFrame,
    reset,
  }
}
