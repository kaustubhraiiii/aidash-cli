/**
 * Tests for the --json spawnSync passthrough path in main().
 * Lives in a separate file so its vi.mock('node:child_process') doesn't
 * interfere with the existing cli.test.tsx mocks.
 */
import { describe, it, expect, vi, beforeEach, afterEach } from 'vitest'
import { render } from 'ink-testing-library'
import React from 'react'

// Mock child_process before any imports that might use it
vi.mock('node:child_process', () => ({
  spawnSync: vi.fn().mockReturnValue({ status: 0 }),
}))

// Mock engine so the module loads cleanly
vi.mock('./engine.js', () => ({
  runEngine: vi.fn(),
  runCost: vi.fn(),
  runReplay: vi.fn(),
  runScore: vi.fn(),
  runRates: vi.fn(),
  runSearch: vi.fn(),
  PYTHON_BIN: 'python3',
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

describe('--json spawnSync passthrough', () => {
  const origArgv = process.argv

  let mockExit: ReturnType<typeof vi.spyOn>

  beforeEach(() => {
    vi.resetModules()
    mockExit = vi.spyOn(process, 'exit').mockImplementation((_code?: number | string | null) => {
      throw new Error('process.exit called')
    })
  })

  afterEach(() => {
    process.argv = origArgv
    mockExit.mockRestore()
  })

  it('calls spawnSync with correct args when --json follows command', async () => {
    process.argv = ['node', '/path/cli.js', 'cost', '--json']
    const { spawnSync } = await import('node:child_process')
    const { main } = await import('./cli.js')
    try { main() } catch {}
    expect(spawnSync).toHaveBeenCalledWith(
      'python3',
      ['-m', 'aidash', 'cost', '--json'],
      { stdio: 'inherit' }
    )
  })

  it('calls spawnSync with correct args when --json precedes command', async () => {
    process.argv = ['node', '/path/cli.js', '--json', 'cost']
    const { spawnSync } = await import('node:child_process')
    const { main } = await import('./cli.js')
    try { main() } catch {}
    expect(spawnSync).toHaveBeenCalledWith(
      'python3',
      ['-m', 'aidash', 'cost', '--json'],
      { stdio: 'inherit' }
    )
  })

  it('App renders empty when --json is in args', async () => {
    const { App } = await import('./cli.js')
    const { lastFrame } = render(React.createElement(App, { args: ['cost', '--json'] }))
    expect((lastFrame() ?? '').trim()).toBe('')
  })
})
