import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from 'ink-testing-library'
import React from 'react'

// Mock the engine module BEFORE importing App
vi.mock('./engine.js', () => ({
  runEngine: vi.fn(),
  runCost: vi.fn(),
  runReplay: vi.fn(),
  runScore: vi.fn(),
  runRates: vi.fn(),
  runSearch: vi.fn(),
  EngineError: class EngineError extends Error {
    kind: string
    detail?: object
    suggestion: string
    constructor(kind: string, message: string, detail?: object) {
      super(message)
      this.name = 'EngineError'
      this.kind = kind
      this.detail = detail
      this.suggestion = 'Try running the command manually.'
    }
  },
}))

// Import App after mocking engine
const { App } = await import('./cli.js')
// Import mocked EngineError for use in tests
const { EngineError } = await import('./engine.js')

describe('cli App routing', () => {
  beforeEach(() => {
    vi.clearAllMocks()
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
    vi.clearAllTimers()
  })

  it('renders CostView when command is "cost"', async () => {
    const { runEngine } = await import('./engine.js')
    vi.mocked(runEngine).mockReturnValue(new Promise(() => {})) // never resolves = spinner stays
    const { lastFrame } = render(React.createElement(App, { args: ['cost'] }))
    // Advance timers to allow initial render
    vi.advanceTimersByTime(50)
    const frame = lastFrame() ?? ''
    expect(frame.toLowerCase()).toMatch(/loading cost/i)
  })

  it('renders ReplayView when command is "replay"', async () => {
    const { runReplay } = await import('./engine.js')
    vi.mocked(runReplay).mockReturnValue(new Promise(() => {}))
    const { lastFrame } = render(React.createElement(App, { args: ['replay', 'last'] }))
    vi.advanceTimersByTime(50)
    const frame = lastFrame() ?? ''
    expect(frame.toLowerCase()).toMatch(/loading replay/i)
  })

  it('renders ScoreView when command is "score"', async () => {
    const { runScore } = await import('./engine.js')
    vi.mocked(runScore).mockReturnValue(new Promise(() => {}))
    const { lastFrame } = render(React.createElement(App, { args: ['score'] }))
    vi.advanceTimersByTime(50)
    const frame = lastFrame() ?? ''
    expect(frame.toLowerCase()).toMatch(/loading score/i)
  })

  it('renders RatesView when command is "rates"', async () => {
    const { runRates } = await import('./engine.js')
    vi.mocked(runRates).mockReturnValue(new Promise(() => {}))
    const { lastFrame } = render(React.createElement(App, { args: ['rates'] }))
    vi.advanceTimersByTime(50)
    const frame = lastFrame() ?? ''
    expect(frame.toLowerCase()).toMatch(/loading rates/i)
  })

  it('renders SearchView when command is "search"', async () => {
    const { runSearch } = await import('./engine.js')
    vi.mocked(runSearch).mockReturnValue(new Promise(() => {}))
    const { lastFrame } = render(React.createElement(App, { args: ['search', 'foo'] }))
    vi.advanceTimersByTime(50)
    const frame = lastFrame() ?? ''
    expect(frame.toLowerCase()).toMatch(/search/i)
  })

  it('renders HelpView when no command given', async () => {
    const { lastFrame } = render(React.createElement(App, { args: [] }))
    vi.advanceTimersByTime(50)
    const frame = lastFrame() ?? ''
    expect(frame).toMatch(/cost/)
    expect(frame).toMatch(/replay/)
    expect(frame).toMatch(/search/)
  })

  it('renders HelpView when unknown command given', async () => {
    const { lastFrame } = render(React.createElement(App, { args: ['unknowncmd'] }))
    vi.advanceTimersByTime(50)
    const frame = lastFrame() ?? ''
    expect(frame).toMatch(/cost/)
  })

  it('renders Alert with error message when engine throws EngineError', async () => {
    const { runCost } = await import('./engine.js')
    vi.mocked(runCost).mockRejectedValue(
      new EngineError('python_not_found', 'Python not found', {})
    )
    const { runEngine } = await import('./engine.js')
    vi.mocked(runEngine).mockRejectedValue(
      new EngineError('python_not_found', 'Python not found', {})
    )
    const { lastFrame } = render(React.createElement(App, { args: ['cost'] }))
    // Let the rejected promise resolve and React update
    await vi.runAllTimersAsync()
    const frame = lastFrame() ?? ''
    expect(frame).toMatch(/Python not found/)
  })

  it('sets process.exitCode to 1 when engine throws EngineError (regression: was 0)', async () => {
    const origExitCode = process.exitCode
    process.exitCode = 0
    const { runEngine } = await import('./engine.js')
    vi.mocked(runEngine).mockRejectedValue(
      new EngineError('python_not_found', 'Python not found', {})
    )
    render(React.createElement(App, { args: ['cost'] }))
    await vi.runAllTimersAsync()
    expect(process.exitCode).toBe(1)
    process.exitCode = origExitCode as number | undefined
  })

  it('does not render Ink when --json flag is present', async () => {
    // App with --json in args returns null, so the frame is empty/null
    const { lastFrame } = render(React.createElement(App, { args: ['cost', '--json'] }))
    vi.advanceTimersByTime(50)
    const frame = lastFrame() ?? ''
    // When --json is passed, App returns null, so the frame should be empty
    expect(frame.trim()).toBe('')
  })
})
