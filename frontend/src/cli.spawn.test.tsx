/**
 * Tests for the --json spawnSync passthrough path in main().
 * Lives in a separate file so its vi.mock('node:child_process') doesn't
 * interfere with the existing cli.test.tsx mocks.
 */
import { describe, it, expect, vi } from 'vitest'
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

const { App } = await import('./cli.js')

describe('--json spawnSync passthrough', () => {
  it('App returns null (empty frame) when --json flag is present', () => {
    // App returns null for --json args; spawnSync is only called from main()
    // which is guarded by the entry-point check (process.argv[1] === __filename).
    // We verify App's side of the contract here.
    const { lastFrame } = render(React.createElement(App, { args: ['cost', '--json'] }))
    expect((lastFrame() ?? '').trim()).toBe('')
  })

  it('App returns null for flag-before-command style --json cost', () => {
    const { lastFrame } = render(React.createElement(App, { args: ['--json', 'cost'] }))
    expect((lastFrame() ?? '').trim()).toBe('')
  })
})
