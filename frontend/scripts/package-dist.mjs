// Package the deployable frontend, not its parent directory or source tree.
import { lstatSync, readdirSync, readFileSync, writeFileSync } from 'node:fs'
import { join } from 'node:path'
import { fileURLToPath } from 'node:url'
import { zipSync } from 'fflate'

const dist = fileURLToPath(new URL('../dist/', import.meta.url))
const archive = fileURLToPath(new URL('../dist.zip', import.meta.url))
const files = Object.create(null)

function collect(directory, prefix = '') {
  for (const name of readdirSync(directory).sort()) {
    const path = join(directory, name)
    const entry = prefix + name
    const stat = lstatSync(path)
    if (stat.isDirectory()) collect(path, `${entry}/`)
    else if (stat.isFile()) files[entry] = readFileSync(path)
    else throw new Error(`Unexpected non-regular build output: ${entry}`)
  }
}

collect(dist)
if (!files['index.html']) throw new Error('Missing dist/index.html; run the frontend build first.')
writeFileSync(archive, zipSync(files, { level: 6, mtime: new Date(2000, 0, 1) }))
console.log(`Packaged ${Object.keys(files).length} frontend files into dist.zip`)
