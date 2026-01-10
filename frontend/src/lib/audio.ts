/**
 * Audio utilities for Honeysuckle.
 */

/**
 * Create an audio player for PCM16 audio data.
 */
export function createAudioPlayer(sampleRate = 24000) {
  let audioContext: AudioContext | null = null
  let nextStartTime = 0

  const init = () => {
    if (!audioContext) {
      audioContext = new AudioContext({ sampleRate })
    }
    return audioContext
  }

  const play = async (pcm16Data: Int16Array) => {
    const ctx = init()

    // Resume if suspended (browsers require user interaction)
    if (ctx.state === 'suspended') {
      console.log('Resuming AudioContext...')
      await ctx.resume()
    }

    // Convert PCM16 to Float32
    const float32Data = new Float32Array(pcm16Data.length)
    for (let i = 0; i < pcm16Data.length; i++) {
      float32Data[i] = pcm16Data[i] / (pcm16Data[i] < 0 ? 0x8000 : 0x7fff)
    }

    // Create buffer
    const buffer = ctx.createBuffer(1, float32Data.length, sampleRate)
    buffer.copyToChannel(float32Data, 0)

    // Create and play source
    const source = ctx.createBufferSource()
    source.buffer = buffer
    source.connect(ctx.destination)

    // Schedule playback
    const startTime = Math.max(ctx.currentTime, nextStartTime)
    source.start(startTime)
    nextStartTime = startTime + buffer.duration
  }

  const clear = () => {
    nextStartTime = audioContext?.currentTime ?? 0
  }

  const close = () => {
    audioContext?.close()
    audioContext = null
    nextStartTime = 0
  }

  return {
    play,
    clear,
    close,
  }
}

/**
 * Merge multiple PCM16 chunks into a single buffer.
 */
export function mergeAudioChunks(chunks: Int16Array[]): Int16Array {
  const totalLength = chunks.reduce((sum, chunk) => sum + chunk.length, 0)
  const merged = new Int16Array(totalLength)

  let offset = 0
  for (const chunk of chunks) {
    merged.set(chunk, offset)
    offset += chunk.length
  }

  return merged
}

/**
 * Downsample audio from one sample rate to another.
 */
export function downsample(
  data: Float32Array,
  inputSampleRate: number,
  outputSampleRate: number
): Float32Array {
  if (inputSampleRate === outputSampleRate) {
    return data
  }

  const ratio = inputSampleRate / outputSampleRate
  const newLength = Math.round(data.length / ratio)
  const result = new Float32Array(newLength)

  for (let i = 0; i < newLength; i++) {
    const srcIndex = Math.round(i * ratio)
    result[i] = data[srcIndex]
  }

  return result
}
