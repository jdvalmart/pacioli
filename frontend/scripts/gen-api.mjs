#!/usr/bin/env node
/**
 * Regenerate src/lib/api-schema.ts from the backend's OpenAPI contract.
 *
 *   npm run gen:api
 *
 * The backend prints the contract without starting a server
 * (`python -m app.cli openapi`). openapi-typescript runs pinned and in
 * isolation through npx: it only supports TypeScript 5 while this project
 * uses TypeScript 6, and it is a generator, not an app dependency.
 * CI regenerates the file and fails if it differs from the committed one.
 */
import { execFileSync } from 'node:child_process'
import { existsSync, mkdtempSync, rmSync } from 'node:fs'
import { tmpdir } from 'node:os'
import path from 'node:path'

const OPENAPI_TYPESCRIPT = 'openapi-typescript@7.13.0'
const frontend = path.resolve(import.meta.dirname, '..')
const backend = path.resolve(frontend, '..', 'backend')
const venvPython = path.join(backend, '.venv', 'bin', 'python')
const python = process.env.PACIOLI_PYTHON ?? (existsSync(venvPython) ? venvPython : 'python')
const output = path.join(frontend, 'src', 'lib', 'api-schema.ts')

const workdir = mkdtempSync(path.join(tmpdir(), 'pacioli-openapi-'))
const spec = path.join(workdir, 'openapi.json')
try {
  execFileSync(python, ['-m', 'app.cli', 'openapi', '--output', spec], {
    cwd: backend,
    stdio: 'inherit',
    env: { ...process.env, DATABASE_URL: '' },
  })
  // Fields with a server-side default stay optional in request bodies.
  const args = ['--yes', OPENAPI_TYPESCRIPT, spec, '--output', output, '--default-non-nullable', 'false']
  execFileSync('npx', args, {
    cwd: frontend,
    stdio: 'inherit',
  })
} finally {
  rmSync(workdir, { recursive: true, force: true })
}
